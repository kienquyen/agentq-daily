"""
Experiment v4 — Long-Term Position Model (6 months / +30%)

NEW MODEL FAMILY (independent from v3x 20-day models).

Label definition (touch-based, no stop-loss):
    label = 1  if  max(high[t+1 : t+120]) / close[t] - 1 >= 0.30
    i.e. stock touches +30% at ANY point within ~6 months (120 trading days)

Positive rate ~34% (validated). Highly regime-dependent (17% bear → 68% bull).

Purged time split (120-day forward window requires gaps to avoid label leakage):
    Train: 2017-01-01 → 2023-06-30   (labels see data up to ~2023-12)
    [purge ~6 months]
    Val:   2024-01-01 → 2024-06-30   (labels see data up to ~2024-12)
    [purge ~6 months]
    Test:  2025-01-01 → 2025-11-28   (last labelable date)

Pipeline:
    Step 1 — Compute 6-month touch labels  (~3 phút)
    Step 2 — Build training set (reuse existing features)  (~1 phút)
    Step 3 — Train v4 LightGBM  (~3-5 phút)
    Step 4 — Evaluate: AUC, Precision@K, by-year breakdown

Chạy:
    python -m pipeline.experiment_v4_longterm
    python -m pipeline.experiment_v4_longterm --step 3   # skip to train
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
import sys
import time
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "experiment_v4_longterm.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

OHLCV_DIR  = ROOT / "data" / "ohlcv"
LABELS_DIR = ROOT / "data" / "labels"
MODELS_DIR = ROOT / "data" / "models"

# Label config
FORWARD_DAYS = 120     # ~6 months trading days
TARGET       = 0.30    # +30% touch

RAW_LABELS_PATH   = LABELS_DIR / "raw_labels_6m.parquet"
TRAINING_SET_PATH = LABELS_DIR / "training_set_6m.parquet"

# Purged time split
TRAIN_START = "2017-01-01"
TRAIN_END   = "2023-06-30"
VAL_START   = "2024-01-01"
VAL_END     = "2024-06-30"
TEST_START  = "2025-01-01"
TEST_END    = "2025-11-28"

# LightGBM params — tuned for longer horizon (more trees, deeper, more reg)
LGBM_PARAMS = {
    "objective":         "binary",
    "metric":            "auc",
    "n_estimators":      800,
    "learning_rate":     0.03,
    "max_depth":         7,
    "num_leaves":        47,
    "min_child_samples": 40,
    "subsample":         0.8,
    "colsample_bytree":  0.7,
    "reg_alpha":         0.2,
    "reg_lambda":        0.3,
    "random_state":      42,
    "n_jobs":            -1,
    "verbose":           -1,
}
EARLY_STOPPING = 80


# ══════════════════════════════════════════════════════════════════════════════
# Step 1: Compute 6-month touch labels
# ══════════════════════════════════════════════════════════════════════════════

def step1_compute_labels() -> pd.DataFrame:
    log.info("=" * 60)
    log.info("STEP 1: Compute 6-month touch labels (+%.0f%% within %d days)",
             TARGET*100, FORWARD_DAYS)
    log.info("=" * 60)

    manifest = json.loads((OHLCV_DIR / "_manifest.json").read_text())
    symbols = [s for s in manifest if s != "VNINDEX"]
    log.info("  Symbols: %d", len(symbols))

    frames = []
    t0 = time.time()
    for sym in symbols:
        path = OHLCV_DIR / f"{sym}.parquet"
        if not path.exists():
            continue
        try:
            df = pd.read_parquet(path)
            df["time"] = pd.to_datetime(df["time"])
            df = df.sort_values("time").reset_index(drop=True)
            closes = df["close"].astype(float).values
            highs  = df["high"].astype(float).values if "high" in df.columns else closes
            lows   = df["low"].astype(float).values  if "low"  in df.columns else closes
            dates  = df["time"].values
            n = len(closes)

            rows = []
            for i in range(n - FORWARD_DAYS):
                entry = closes[i]
                if entry <= 0:
                    continue
                window_high = highs[i+1:i+FORWARD_DAYS+1]
                window_low  = lows[i+1:i+FORWARD_DAYS+1]
                max_ret = float(window_high.max() / entry - 1)
                min_ret = float(window_low.min()  / entry - 1)
                # Days to first touch +30% (if any)
                touch_idx = np.where(window_high / entry - 1 >= TARGET)[0]
                days_to_touch = int(touch_idx[0]) + 1 if len(touch_idx) > 0 else -1
                rows.append({
                    "symbol":        sym,
                    "date":          pd.Timestamp(dates[i]),
                    "max_ret_6m":    max_ret,
                    "min_ret_6m":    min_ret,
                    "days_to_touch": days_to_touch,
                    "label":         int(max_ret >= TARGET),
                    "label_valid":   1,
                })
            if rows:
                frames.append(pd.DataFrame(rows))
        except Exception as e:
            log.warning("  %s: %s", sym, e)

    result = pd.concat(frames, ignore_index=True)
    result = result.set_index(["symbol", "date"])

    log.info("  Labelable samples: %d | positive rate = %.1f%% (%.0fs)",
             len(result), result["label"].mean()*100, time.time()-t0)
    log.info("  Date range: %s → %s",
             result.index.get_level_values("date").min().date(),
             result.index.get_level_values("date").max().date())

    result.to_parquet(RAW_LABELS_PATH)
    log.info("  Saved → %s", RAW_LABELS_PATH)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Step 2: Build training set (reuse existing features)
# ══════════════════════════════════════════════════════════════════════════════

def step2_build_training_set() -> pd.DataFrame:
    log.info("=" * 60)
    log.info("STEP 2: Build training set (reuse existing feature columns)")
    log.info("=" * 60)

    if not RAW_LABELS_PATH.exists():
        step1_compute_labels()
    labels = pd.read_parquet(RAW_LABELS_PATH)

    # Reuse features from existing training_set_20d (avoids reloading 2274 files)
    existing = pd.read_parquet(LABELS_DIR / "training_set_20d.parquet")
    log.info("  Loaded existing feature set: %d rows", len(existing))

    # Drop 20d-specific label columns, keep only features
    drop_cols = {"label", "label_valid", "forward_ret_10d", "max_drawdown_10d"}
    feat_cols = [c for c in existing.columns if c not in drop_cols]
    feats = existing[feat_cols].copy()

    # Normalize indices
    feats.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in feats.index], names=["symbol","date"])
    labels.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in labels.index], names=["symbol","date"])

    merged = feats.join(labels[["label","max_ret_6m","min_ret_6m","days_to_touch","label_valid"]],
                        how="inner")
    merged = merged[merged["label_valid"] == 1].copy()

    log.info("  Merged training set: %d rows | positive rate = %.1f%%",
             len(merged), merged["label"].mean()*100)
    merged.to_parquet(TRAINING_SET_PATH)
    log.info("  Saved → %s", TRAINING_SET_PATH)
    return merged


# ══════════════════════════════════════════════════════════════════════════════
# Step 3: Train v4
# ══════════════════════════════════════════════════════════════════════════════

def _get_feature_cols(df: pd.DataFrame) -> List[str]:
    """Feature columns: numeric, exclude labels and metadata."""
    exclude = {
        "label","label_valid","max_ret_6m","min_ret_6m","days_to_touch",
        "forward_ret_10d","max_drawdown_10d","close_vnd","avg_val_21d_b",
        "hardcheck_reasons","hardcheck_pass","date","regime_label",
        "regime_score","symbol",
    }
    cols = []
    for c in df.columns:
        if c in exclude:
            continue
        if df[c].dtype.kind in "biufc":   # numeric
            cols.append(c)
    return cols


def step3_train() -> dict:
    log.info("=" * 60)
    log.info("STEP 3: Train v4 LightGBM (6-month / +30%% touch)")
    log.info("  Purged split: train→%s | val %s→%s | test %s→%s",
             TRAIN_END, VAL_START, VAL_END, TEST_START, TEST_END)
    log.info("=" * 60)

    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score

    df = pd.read_parquet(TRAINING_SET_PATH)
    df = df.dropna(subset=["label"])
    dates = df.index.get_level_values("date")

    feat_cols = _get_feature_cols(df)
    log.info("  Feature count: %d", len(feat_cols))

    train = df[(dates >= TRAIN_START) & (dates <= TRAIN_END)]
    val   = df[(dates >= VAL_START)   & (dates <= VAL_END)]
    test  = df[(dates >= TEST_START)  & (dates <= TEST_END)]
    log.info("  Split → train=%d  val=%d  test=%d", len(train), len(val), len(test))
    log.info("  Pos rate → train=%.1f%%  val=%.1f%%  test=%.1f%%",
             train["label"].mean()*100, val["label"].mean()*100, test["label"].mean()*100)

    X_tr, y_tr = train[feat_cols], train["label"].astype(int)
    X_va, y_va = val[feat_cols],   val["label"].astype(int)
    X_te, y_te = test[feat_cols],  test["label"].astype(int)

    neg, pos = (y_tr==0).sum(), (y_tr==1).sum()
    spw = round(neg/pos, 4) if pos > 0 else 1.0
    log.info("  Class balance: pos=%d neg=%d  scale_pos_weight=%.2f", pos, neg, spw)

    params = dict(LGBM_PARAMS); params["scale_pos_weight"] = spw
    model = lgb.LGBMClassifier(**params)
    model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)],
              callbacks=[lgb.early_stopping(EARLY_STOPPING, verbose=False),
                         lgb.log_evaluation(period=100)])

    # Metrics
    metrics = {}
    for split_name, X, y in [("train",X_tr,y_tr),("val",X_va,y_va),("test",X_te,y_te)]:
        if len(np.unique(y)) > 1:
            auc = roc_auc_score(y, model.predict_proba(X)[:,1])
        else:
            auc = float("nan")
        metrics[split_name] = {"roc_auc": float(auc), "n": int(len(y)),
                               "pos_rate": float(y.mean())}
    log.info("  AUC → train=%.4f  val=%.4f  test=%.4f",
             metrics["train"]["roc_auc"], metrics["val"]["roc_auc"], metrics["test"]["roc_auc"])

    # Save
    v4_dir = MODELS_DIR / "v4"
    v4_dir.mkdir(parents=True, exist_ok=True)
    with open(v4_dir / "lgbm_model_6m.pkl", "wb") as f:
        pickle.dump({"model":model,"feat_cols":feat_cols,"horizon":"6m",
                     "target":TARGET,"forward_days":FORWARD_DAYS,
                     "experiment":"longterm_v4"}, f)
    with open(v4_dir / "eval_metrics_6m.json","w") as f:
        json.dump(metrics, f, indent=2)
    fi = pd.DataFrame({"feature":feat_cols,"importance":model.feature_importances_}
                      ).sort_values("importance", ascending=False)
    fi.to_csv(v4_dir / "feature_importance_6m.csv", index=False)
    log.info("  Saved → %s", v4_dir)

    return {"model":model,"feat_cols":feat_cols,"metrics":metrics,"fi":fi,
            "test":test, "X_te":X_te, "y_te":y_te}


# ══════════════════════════════════════════════════════════════════════════════
# Step 4: Evaluate
# ══════════════════════════════════════════════════════════════════════════════

def step4_evaluate(res: dict) -> None:
    log.info("=" * 60)
    log.info("STEP 4: Evaluate v4 — Precision@K + by-year")
    log.info("=" * 60)

    model, feat_cols = res["model"], res["feat_cols"]
    test = res["test"].copy()
    test["prob"]    = model.predict_proba(res["X_te"][feat_cols])[:,1]
    test["label_i"] = res["y_te"].values
    test["date_"]   = test.index.get_level_values("date")

    base_rate = test["label_i"].mean()
    log.info("  Test base positive rate: %.1f%%", base_rate*100)

    # Precision@K per day
    log.info("")
    log.info("  Precision@K (daily top-K by prob):")
    for k in [5, 10, 20]:
        precs, rets = [], []
        for d, g in test.groupby("date_"):
            if len(g) < k: continue
            top = g.nlargest(k, "prob")
            precs.append(top["label_i"].mean())
            rets.append(top["max_ret_6m"].mean())
        if precs:
            log.info("    P@%-2d = %.1f%%  (lift %.2fx)  |  mean max_ret_6m = %.1f%%",
                     k, np.mean(precs)*100, np.mean(precs)/base_rate, np.mean(rets)*100)

    # Feature importance top 20
    log.info("")
    log.info("  Top 20 features:")
    for _, row in res["fi"].head(20).iterrows():
        log.info("    %-30s = %d", row["feature"], int(row["importance"]))

    # Save config
    v4_dir = MODELS_DIR / "v4"
    cfg = {
        "_version":     "v4",
        "_description": "v4 — long-term position model: +30% touch within 6 months",
        "_horizon":     "6m (120 trading days)",
        "_label":       f"max(high[t+1:t+{FORWARD_DAYS}])/close[t]-1 >= {TARGET}",
        "_stop_loss":   "none (touch-based)",
        "_auc_test":    round(res["metrics"]["test"]["roc_auc"], 4),
        "_purged_split": {"train_end":TRAIN_END,"val":f"{VAL_START}→{VAL_END}","test":f"{TEST_START}→{TEST_END}"},
    }
    (v4_dir / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("  Config saved → %s", v4_dir / "config.json")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main(start_step: int = 1) -> None:
    t0 = time.time()
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  Experiment v4 — Long-Term Model (6mo / +30%% touch) ║")
    log.info("╚══════════════════════════════════════════════════════╝")

    if start_step <= 1:
        step1_compute_labels()
    else:
        log.info("STEP 1: SKIPPED")
    if start_step <= 2:
        step2_build_training_set()
    else:
        log.info("STEP 2: SKIPPED")

    res = step3_train()
    step4_evaluate(res)

    log.info("")
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  EXPERIMENT v4 COMPLETE  (%.0f phút)                 ║", (time.time()-t0)/60)
    log.info("║  Test AUC: %.4f                                      ║", res["metrics"]["test"]["roc_auc"])
    log.info("╚══════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, default=1)
    args = parser.parse_args()
    main(start_step=args.step)
