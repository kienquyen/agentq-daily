"""
Experiment v5 — Alpha-10 Model (outperform VNINDEX >= 10% in 1 month)

Label (pure relative alpha, fixed horizon):
    alpha_20d = stock_ret_20d - vnindex_ret_20d
    label = 1  if  alpha_20d >= 0.10   (beat VNINDEX by >= 10% over ~20 trading days)

Properties:
    - Positive rate ~13.3% (selective)
    - Regime-NEUTRAL: alpha removes market beta → stable 8.5-20.3% across years
      (unlike v4 6-month +30% which was 17-68% macro-driven)

Reuses alpha_20d already computed in raw_labels_20d_alpha.parquet (from v3g).

LEAKAGE GUARD: vnindex_ret_20d, alpha_20d, forward_ret_10d, max_drawdown_10d
must be DROPPED before training (they encode the future / the label).

Purged split (20-day forward window → ~1 month gap between splits):
    Train: 2017-01-01 → 2024-06-30
    Val:   2024-08-01 → 2024-12-31   (1-month purge gap)
    Test:  2025-02-01 → 2026-04-29   (1-month purge gap)

Chạy:
    python -m pipeline.experiment_v5_alpha10
    python -m pipeline.experiment_v5_alpha10 --step 3   # skip to train
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / "logs"; LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(),
              logging.FileHandler(LOG_DIR / "experiment_v5_alpha10.log", mode="w")],
)
log = logging.getLogger(__name__)

LABELS_DIR = ROOT / "data" / "labels"
MODELS_DIR = ROOT / "data" / "models"

ALPHA_THRESHOLD = 0.10
ALPHA_LABELS_PATH    = LABELS_DIR / "raw_labels_20d_alpha.parquet"
TRAINING_SET_PATH    = LABELS_DIR / "training_set_20d_alpha10.parquet"

TRAIN_START="2017-01-01"; TRAIN_END="2024-06-30"
VAL_START="2024-08-01";   VAL_END="2024-12-31"
TEST_START="2025-02-01";  TEST_END="2026-04-29"

# Columns that leak the label/future — MUST drop before training
LEAKAGE_COLS = ["vnindex_ret_20d","alpha_20d","forward_ret_10d","max_drawdown_10d",
                "label_alpha","label_orig","label_valid","label_valid_alpha"]

LGBM_PARAMS = dict(objective="binary",metric="auc",n_estimators=700,learning_rate=0.04,
                   max_depth=6,num_leaves=31,min_child_samples=30,subsample=0.8,
                   colsample_bytree=0.8,reg_alpha=0.1,reg_lambda=0.2,random_state=42,
                   n_jobs=-1,verbose=-1)
EARLY_STOP = 80


def _feat_cols(df):
    exclude = set(LEAKAGE_COLS) | {
        "label","close_vnd","avg_val_21d_b","hardcheck_reasons","hardcheck_pass",
        "date","regime_label","regime_score","symbol","max_ret_6m","min_ret_6m",
        "days_to_touch","regime_computed",
    }
    return [c for c in df.columns if c not in exclude and df[c].dtype.kind in "biufc"]


# ── Step 2: Build training set (relabel alpha>=10%, join features) ─────────────

def step2_build() -> pd.DataFrame:
    log.info("="*60); log.info("STEP 2: Build training set (alpha >= %.0f%%)", ALPHA_THRESHOLD*100); log.info("="*60)

    alpha = pd.read_parquet(ALPHA_LABELS_PATH)
    alpha = alpha[alpha["label_valid"]==1].copy()
    alpha["label_a10"] = (alpha["alpha_20d"] >= ALPHA_THRESHOLD).astype(int)
    log.info("  Alpha labels: %d | pos rate(alpha>=10%%) = %.1f%%",
             len(alpha), alpha["label_a10"].mean()*100)

    existing = pd.read_parquet(LABELS_DIR / "training_set_20d.parquet")
    feat_keep = [c for c in existing.columns
                 if c not in {"label","label_valid","forward_ret_10d","max_drawdown_10d"}]
    feats = existing[feat_keep].copy()

    feats.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s,d in feats.index], names=["symbol","date"])
    alpha.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s,d in alpha.index], names=["symbol","date"])

    merged = feats.join(alpha[["label_a10","alpha_20d","vnindex_ret_20d"]], how="inner")
    merged = merged.rename(columns={"label_a10":"label"})
    merged = merged.dropna(subset=["label"])
    log.info("  Merged: %d rows | pos rate = %.1f%%", len(merged), merged["label"].mean()*100)
    merged.to_parquet(TRAINING_SET_PATH)
    log.info("  Saved → %s", TRAINING_SET_PATH)
    return merged


# ── Step 3: Train ──────────────────────────────────────────────────────────────

def step3_train() -> dict:
    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score
    log.info("="*60); log.info("STEP 3: Train v5 (alpha>=10%%, purged split)"); log.info("="*60)

    df = pd.read_parquet(TRAINING_SET_PATH).dropna(subset=["label"])
    dates = df.index.get_level_values("date")
    fc = _feat_cols(df)
    log.info("  Feature count: %d (leakage cols dropped: %s)",
             len(fc), [c for c in LEAKAGE_COLS if c in df.columns])

    tr = df[(dates>=TRAIN_START)&(dates<=TRAIN_END)]
    va = df[(dates>=VAL_START)&(dates<=VAL_END)]
    te = df[(dates>=TEST_START)&(dates<=TEST_END)]
    log.info("  Split → train=%d val=%d test=%d", len(tr),len(va),len(te))
    log.info("  Pos rate → train=%.1f%% val=%.1f%% test=%.1f%%",
             tr["label"].mean()*100, va["label"].mean()*100, te["label"].mean()*100)

    ytr,yva,yte = tr["label"].astype(int),va["label"].astype(int),te["label"].astype(int)
    spw = round((ytr==0).sum()/(ytr==1).sum(),4)
    log.info("  scale_pos_weight=%.2f", spw)
    pr=dict(LGBM_PARAMS); pr["scale_pos_weight"]=spw
    m=lgb.LGBMClassifier(**pr)
    m.fit(tr[fc],ytr,eval_set=[(va[fc],yva)],
          callbacks=[lgb.early_stopping(EARLY_STOP,verbose=False),lgb.log_evaluation(100)])

    metrics={}
    for s,X,y in [("train",tr,ytr),("val",va,yva),("test",te,yte)]:
        auc=roc_auc_score(y,m.predict_proba(X[fc])[:,1]) if y.nunique()>1 else float("nan")
        metrics[s]={"roc_auc":float(auc),"n":int(len(y)),"pos_rate":float(y.mean())}
    log.info("  AUC → train=%.4f val=%.4f test=%.4f gap=%.3f",
             metrics["train"]["roc_auc"],metrics["val"]["roc_auc"],
             metrics["test"]["roc_auc"],metrics["train"]["roc_auc"]-metrics["test"]["roc_auc"])

    v5=MODELS_DIR/"v5"; v5.mkdir(parents=True,exist_ok=True)
    with open(v5/"lgbm_model_alpha10.pkl","wb") as f:
        pickle.dump({"model":m,"feat_cols":fc,"horizon":"20d","label":"alpha>=10%",
                     "experiment":"alpha10_v5"},f)
    json.dump(metrics,open(v5/"eval_metrics_alpha10.json","w"),indent=2)
    fi=pd.DataFrame({"feature":fc,"importance":m.feature_importances_}).sort_values("importance",ascending=False)
    fi.to_csv(v5/"feature_importance_alpha10.csv",index=False)
    log.info("  Saved → %s", v5)
    return {"model":m,"feat_cols":fc,"metrics":metrics,"fi":fi,"test":te}


# ── Step 4: Evaluate (with hardcheck) ──────────────────────────────────────────

def step4_eval(res: dict) -> None:
    log.info("="*60); log.info("STEP 4: Evaluate v5 — Precision@K (raw + hardcheck)"); log.info("="*60)
    m,fc = res["model"],res["feat_cols"]
    te = res["test"].copy()
    te["prob"]=m.predict_proba(te[fc])[:,1]
    te["label_i"]=te["label"].astype(int)
    te["date_"]=te.index.get_level_values("date")

    base=te["label_i"].mean()
    base_hc=te[te["hardcheck_pass"]==1]["label_i"].mean() if "hardcheck_pass" in te.columns else base
    log.info("  Test base pos rate: %.1f%% (all) | %.1f%% (hardcheck)", base*100, base_hc*100)

    for use_hc in [False, True]:
        sub = te[te["hardcheck_pass"]==1] if use_hc else te
        b = base_hc if use_hc else base
        log.info("  %s:", "WITH hardcheck" if use_hc else "RAW (no filter)")
        for k in [5,10,20]:
            precs=[]
            for d,g in sub.groupby("date_"):
                if len(g)<k: continue
                precs.append(g.nlargest(k,"prob")["label_i"].mean())
            if precs:
                log.info("    P@%-2d = %.1f%%  (lift %.2fx)", k, np.mean(precs)*100, np.mean(precs)/b)

    log.info("  Top 20 features:")
    for _,r in res["fi"].head(20).iterrows():
        log.info("    %-30s = %d", r["feature"], int(r["importance"]))

    v5=MODELS_DIR/"v5"
    cfg={"_version":"v5","_description":"v5 — outperform VNINDEX >= 10% in 1 month (alpha label)",
         "_label":f"alpha_20d >= {ALPHA_THRESHOLD}","_horizon":"20d",
         "_auc_test":round(res["metrics"]["test"]["roc_auc"],4),
         "_pos_rate":round(res["metrics"]["test"]["pos_rate"],4)}
    (v5/"config.json").write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding="utf-8")
    log.info("  Config saved → %s", v5/"config.json")


def main(start_step:int=1)->None:
    t0=time.time()
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  Experiment v5 — Alpha-10 (beat VNINDEX +10%% / 1mo) ║")
    log.info("╚══════════════════════════════════════════════════════╝")
    if start_step<=2: step2_build()
    else: log.info("STEP 2: SKIPPED")
    res=step3_train()
    step4_eval(res)
    log.info("")
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  v5 COMPLETE (%.0f phút) — Test AUC %.4f            ║",
             (time.time()-t0)/60, res["metrics"]["test"]["roc_auc"])
    log.info("╚══════════════════════════════════════════════════════╝")


if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--step",type=int,default=1)
    main(start_step=p.parse_args().step)
