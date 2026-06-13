"""
Experiment v3i — Per-Regime Model (v2: thêm model_bull)

Architecture:
  model_deep_bear.pkl  — deep_bear + choppy samples only  (~63K)
  model_bull.pkl       — bull + recovery samples only     (~144K)
  model_other (= v3b)  — sideways (default)

Routing at inference:
  if regime in [deep_bear, choppy]   → model_deep_bear
  if regime in [bull, recovery]      → model_bull
  else (sideways)                    → v3b

Motivation:
  - Foreign flow features có ý nghĩa NGƯỢC CHIỀU giữa bull và deep_bear
  - 1 model chung bị "trung bình hóa" weights → sub-optimal cả 2
  - Regime-specific model tự học đúng relationship cho từng context

Pipeline:
  Step 1 — Compute regime labels for all training dates  (~5 phút, cached)
  Step 3 — Train model_deep_bear  (~3-5 phút)
  Step 5 — Train model_bull       (~3-5 phút)
  Step 4 — Backtest: v3b only vs v3i full hybrid (deep_bear + bull)

Chạy:
    python -m pipeline.experiment_v3i_regime_model
    python -m pipeline.experiment_v3i_regime_model --step 5   # train bull only
    python -m pipeline.experiment_v3i_regime_model --step 4   # backtest only
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
import sys
import time
from pathlib import Path
from typing import Optional

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
        logging.FileHandler(LOG_DIR / "experiment_v3i_regime_model.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

import numpy as np
import pandas as pd

LABELS_DIR = ROOT / "data" / "labels"
MODELS_DIR = ROOT / "data" / "models"

DEEP_BEAR_REGIMES = {"deep_bear", "choppy"}
BULL_REGIMES      = {"bull", "recovery"}
REGIME_LABELS_CACHE = ROOT / "data" / "labels" / "training_regime_labels.parquet"

# ══════════════════════════════════════════════════════════════════════════════
# Step 1: Compute regime for all training dates
# ══════════════════════════════════════════════════════════════════════════════

def step1_compute_regime_labels() -> pd.Series:
    """
    Compute regime for each unique date in training set.
    Caches result to avoid recomputing (~5 min for 2228 dates).
    Returns Series: date → regime string.
    """
    from pipeline.regime_detector import detect_regime

    ts = pd.read_parquet(LABELS_DIR / "training_set_20d.parquet")
    all_dates = sorted(ts.index.get_level_values("date").unique())

    if REGIME_LABELS_CACHE.exists():
        cached = pd.read_parquet(REGIME_LABELS_CACHE)["regime"]
        cached.index = pd.to_datetime(cached.index)
        # Check coverage
        missing = [d for d in all_dates if pd.Timestamp(d) not in cached.index]
        if not missing:
            log.info("Regime labels loaded from cache: %d dates", len(cached))
            return cached
        log.info("Cache incomplete (%d missing) — recomputing...", len(missing))

    log.info("Computing regime for %d dates...", len(all_dates))
    t0 = time.time()
    regime_map = {}
    for i, d in enumerate(all_dates, 1):
        try:
            regime, _, _ = detect_regime(d.strftime("%Y-%m-%d"))
            regime_map[d] = regime
        except Exception:
            regime_map[d] = "sideways"
        if i % 200 == 0:
            log.info("  [%d/%d] %.0fs elapsed", i, len(all_dates), time.time()-t0)

    series = pd.Series(regime_map, name="regime")
    series.index = pd.DatetimeIndex(series.index)
    pd.DataFrame({"regime": series}).to_parquet(REGIME_LABELS_CACHE)
    log.info("Regime labels computed and cached: %d dates (%.0fs)",
             len(series), time.time()-t0)

    dist = series.value_counts()
    for r, n in dist.items():
        log.info("  %-12s %4d dates (%4.1f%%)", r, n, n/len(series)*100)

    return series


# ══════════════════════════════════════════════════════════════════════════════
# Step 2+3: Train deep_bear model
# ══════════════════════════════════════════════════════════════════════════════

def step3_train_deep_bear(regime_labels: pd.Series) -> dict:
    log.info("=" * 60)
    log.info("STEP 3: Train model_deep_bear (deep_bear + choppy only)")
    log.info("  Feature set: v3h (v3b base + Alpha158)")
    log.info("=" * 60)

    import pipeline.phase4b_ml_model_20d as p4b

    # Load full training set
    ts = pd.read_parquet(LABELS_DIR / "training_set_20d.parquet")
    log.info("  Full training set: %d rows", len(ts))

    # Map regime to each row
    ts_dates = ts.index.get_level_values("date")
    ts_dates_ts = pd.DatetimeIndex(ts_dates)
    regime_series = regime_labels.reindex(ts_dates_ts).fillna("sideways")
    ts["regime_computed"] = regime_series.values

    # Filter deep_bear + choppy
    mask = ts["regime_computed"].isin(DEEP_BEAR_REGIMES)
    df_bear = ts[mask].copy()
    log.info("  deep_bear + choppy samples: %d (%.1f%% of total)",
             len(df_bear), len(df_bear)/len(ts)*100)
    log.info("  Positive rate in deep_bear: %.1f%%",
             df_bear["label"].mean()*100 if "label" in df_bear.columns else 0)

    if len(df_bear) < 5000:
        log.warning("  Too few samples (%d) — aborting", len(df_bear))
        return {}

    # Remove regime_computed before training (it's target leakage)
    df_bear = df_bear.drop(columns=["regime_computed"])

    # Drop rows where label is NaN (recent dates without forward returns)
    n_before = len(df_bear)
    df_bear = df_bear.dropna(subset=["label"])
    if len(df_bear) < n_before:
        log.info("  Dropped %d NaN-label rows → %d remaining", n_before-len(df_bear), len(df_bear))

    model, feat_cols, metrics = p4b.train(df_bear)

    # Save
    v3i_dir = MODELS_DIR / "v3i"
    v3i_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = v3i_dir / "model_deep_bear.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump({
            "model":      model,
            "feat_cols":  feat_cols,
            "horizon":    "20d",
            "experiment": "per_regime_v3i",
            "trained_on": "deep_bear+choppy",
        }, f)

    metrics_path = v3i_dir / "eval_metrics_deep_bear.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    fi = pd.DataFrame({
        "feature":    feat_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    fi.to_csv(v3i_dir / "feature_importance_deep_bear.csv", index=False)

    log.info("  model_deep_bear saved → %s", pkl_path)

    # Show Alpha158 importance
    alpha158_fi = fi[fi["feature"].str.startswith("alpha158_")]
    if not alpha158_fi.empty:
        log.info("  Alpha158 feature importance in deep_bear model:")
        for _, row in alpha158_fi.iterrows():
            log.info("    %-30s = %d", row["feature"], int(row["importance"]))

    log.info("  Top 15 features:")
    for _, row in fi.head(15).iterrows():
        marker = " ◄ Alpha158" if row["feature"].startswith("alpha158_") else ""
        log.info("    %-30s = %d%s", row["feature"], int(row["importance"]), marker)

    return {"model": model, "feat_cols": feat_cols, "metrics": metrics, "fi": fi}


# ══════════════════════════════════════════════════════════════════════════════
# Step 5: Train model_bull (bull + recovery samples)
# ══════════════════════════════════════════════════════════════════════════════

def step5_train_bull(regime_labels: pd.Series) -> dict:
    log.info("=" * 60)
    log.info("STEP 5: Train model_bull (bull + recovery only)")
    log.info("  Feature set: all features (v3b base + Alpha158)")
    log.info("  Val split: chronological within bull samples (last 20%%)")
    log.info("=" * 60)

    import pipeline.phase4b_ml_model_20d as p4b

    ts = pd.read_parquet(LABELS_DIR / "training_set_20d.parquet")
    log.info("  Full training set: %d rows", len(ts))

    ts_dates = ts.index.get_level_values("date")
    regime_series = regime_labels.reindex(pd.DatetimeIndex(ts_dates)).fillna("sideways")
    ts["regime_computed"] = regime_series.values

    # Filter bull + recovery
    mask = ts["regime_computed"].isin(BULL_REGIMES)
    df_bull = ts[mask].copy()
    log.info("  bull + recovery samples: %d (%.1f%% of total)",
             len(df_bull), len(df_bull)/len(ts)*100)
    log.info("  Positive rate: %.1f%%",
             df_bull["label"].mean()*100 if "label" in df_bull.columns else 0)

    df_bull = df_bull.drop(columns=["regime_computed"])
    n_before = len(df_bull)
    df_bull = df_bull.dropna(subset=["label"])
    if len(df_bull) < n_before:
        log.info("  Dropped %d NaN-label rows → %d remaining",
                 n_before-len(df_bull), len(df_bull))

    if len(df_bull) < 5000:
        log.warning("  Too few samples (%d) — aborting", len(df_bull))
        return {}

    # ── Regime-aware val split: last 20% of bull samples chronologically ─────
    # This ensures val set contains bull regime data, not sideways 2024-H2
    df_bull_sorted = df_bull.sort_index(level="date")
    split_n = int(len(df_bull_sorted) * 0.80)
    dates_sorted = sorted(df_bull_sorted.index.get_level_values("date").unique())
    split_date = dates_sorted[int(len(dates_sorted) * 0.80)]

    log.info("  Train/Val split date: %s (80/20 within bull samples)", split_date.date())

    # Override TRAIN_START/VAL_START for this training run
    original_train_start = p4b.TRAIN_START
    original_train_end   = p4b.TRAIN_END
    original_val_start   = p4b.VAL_START
    original_val_end     = p4b.VAL_END

    p4b.TRAIN_START = "2017-01-01"  # include all bull samples
    p4b.TRAIN_END   = split_date.strftime("%Y-%m-%d")
    p4b.VAL_START   = split_date.strftime("%Y-%m-%d")
    p4b.VAL_END     = "2099-12-31"

    try:
        model, feat_cols, metrics = p4b.train(df_bull)
    finally:
        # Restore original dates
        p4b.TRAIN_START = original_train_start
        p4b.TRAIN_END   = original_train_end
        p4b.VAL_START   = original_val_start
        p4b.VAL_END     = original_val_end

    # Save
    v3i_dir = MODELS_DIR / "v3i"
    v3i_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = v3i_dir / "model_bull.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump({
            "model":      model,
            "feat_cols":  feat_cols,
            "horizon":    "20d",
            "experiment": "per_regime_v3i",
            "trained_on": "bull+recovery",
        }, f)

    metrics_path = v3i_dir / "eval_metrics_bull.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    fi = pd.DataFrame({
        "feature":    feat_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    fi.to_csv(v3i_dir / "feature_importance_bull.csv", index=False)

    log.info("  model_bull saved → %s", pkl_path)
    val_auc = metrics.get("val", {}).get("roc_auc", 0)
    test_auc = metrics.get("test", {}).get("roc_auc", 0)
    log.info("  Val AUC: %.4f  |  Test AUC: %.4f", val_auc, test_auc)

    # Show Alpha158 importance
    log.info("  Top 15 features in model_bull:")
    alpha158_feats = set()
    for _, row in fi.head(15).iterrows():
        is_a158 = row["feature"].startswith("alpha158_")
        marker = " ◄ Alpha158" if is_a158 else ""
        if is_a158: alpha158_feats.add(row["feature"])
        log.info("    %-30s = %d%s", row["feature"], int(row["importance"]), marker)

    # Foreign flow importance
    ff_fi = fi[fi["feature"].str.startswith("foreign_")]
    log.info("  Foreign flow features in model_bull:")
    for _, row in ff_fi.head(8).iterrows():
        log.info("    %-30s = %d", row["feature"], int(row["importance"]))

    return {"model": model, "feat_cols": feat_cols, "metrics": metrics, "fi": fi}


# ══════════════════════════════════════════════════════════════════════════════
# Step 4: Backtest — v3b only vs v3i hybrid
# ══════════════════════════════════════════════════════════════════════════════

def step4_backtest(regime_labels: pd.Series) -> None:
    log.info("=" * 60)
    log.info("STEP 4: Backtest — v3b only vs v3i hybrid routing")
    log.info("=" * 60)

    from pipeline.phase4b_ml_model_20d import tier3_filter_20d
    from pipeline.regime_detector import REGIME_CUTOFFS

    TEST_START = "2025-01-01"
    TOP_K = 10

    # Load test data
    ts = pd.read_parquet(LABELS_DIR / "training_set_20d.parquet")
    raw = pd.read_parquet(LABELS_DIR / "raw_labels_20d.parquet")
    raw.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in raw.index], names=["symbol","date"])
    raw = raw[["forward_ret_10d","max_drawdown_10d"]].rename(
        columns={"forward_ret_10d":"fwd_ret","max_drawdown_10d":"max_dd"})
    ts = ts.join(raw, how="left")
    test = ts[ts.index.get_level_values("date") >= TEST_START].copy()

    test_dates = sorted(test.index.get_level_values("date").unique())
    test_regime_map = {}
    for d in test_dates:
        test_regime_map[d] = regime_labels.get(pd.Timestamp(d), "sideways")

    # Load models
    def load_model(name):
        try:
            with open(MODELS_DIR / name / "lgbm_model_20d.pkl","rb") as f:
                p = pickle.load(f)
            cfg = {}
            try: cfg = json.loads((MODELS_DIR/name/"config.json").read_text())
            except: pass
            return p["model"], p["feat_cols"], cfg.get("regime_cutoffs", REGIME_CUTOFFS)
        except Exception as e:
            log.warning("Cannot load %s: %s", name, e)
            return None, None, None

    def load_regime_model(filename):
        try:
            with open(MODELS_DIR/"v3i"/filename,"rb") as f:
                p = pickle.load(f)
            return p["model"], p["feat_cols"]
        except Exception as e:
            log.warning("%s not found: %s", filename, e)
            return None, None

    v3b_model, v3b_cols, v3b_cuts = load_model("v3b")
    db_model,  db_cols  = load_regime_model("model_deep_bear.pkl")
    bull_model,bull_cols= load_regime_model("model_bull.pkl")

    if v3b_model is None:
        log.error("v3b not found, cannot backtest")
        return

    def score(model, feat_cols, df):
        X = df[[c for c in feat_cols if c in df.columns]].copy()
        for c in [c for c in feat_cols if c not in df.columns]: X[c]=0.0
        return model.predict_proba(X[feat_cols])[:,1]

    # Pre-score all models
    log.info("  Scoring v3b on test set...")
    test["prob_v3b"] = score(v3b_model, v3b_cols, test)
    if db_model:
        log.info("  Scoring model_deep_bear on test set...")
        test["prob_db"] = score(db_model, db_cols, test)
    if bull_model:
        log.info("  Scoring model_bull on test set...")
        test["prob_bull"] = score(bull_model, bull_cols, test)
    test["date_"]  = test.index.get_level_values("date")
    test["symbol"] = test.index.get_level_values("symbol")

    base_wr = (test["fwd_ret"]>=0.05).mean()
    log.info("  Base WR: %.1f%%", base_wr*100)

    scenarios = {"v3b only": ("prob_v3b", v3b_cuts, None, None)}
    if db_model:
        scenarios["v3i (+deep_bear)"] = ("prob_v3b", v3b_cuts, "prob_db", None)
    if bull_model:
        scenarios["v3i (+bull)"]      = ("prob_v3b", v3b_cuts, None, "prob_bull")
    if db_model and bull_model:
        scenarios["v3i full hybrid"]  = ("prob_v3b", v3b_cuts, "prob_db", "prob_bull")

    results = {}
    for sc_name, (prob_col, cutoffs, bear_col, bull_col) in scenarios.items():
        day_rows = []
        for date, grp in test.groupby("date_"):
            regime = test_regime_map.get(date, "sideways")
            cutoff = cutoffs.get(regime, 0.55)

            # Routing: deep_bear model for deep_bear/choppy, bull model for bull/recovery
            active_prob = prob_col
            if bear_col and regime in DEEP_BEAR_REGIMES and bear_col in grp.columns:
                active_prob = bear_col
            elif bull_col and regime in BULL_REGIMES and bull_col in grp.columns:
                active_prob = bull_col

            grp2 = grp.copy()
            grp2["raw_prob"] = grp2[active_prob]
            grp2["hardcheck_pass"] = grp2["hardcheck_pass"]

            scores_df = grp2[["symbol","raw_prob","hardcheck_pass"]].copy()
            scores_df["score_1000"]=(scores_df["raw_prob"]*1000).round().astype(int)
            scores_df["rank"]=scores_df["raw_prob"].rank(ascending=False).astype(int)

            try:
                t3 = tier3_filter_20d(scores_df, grp2.set_index("symbol"),
                                      prob_cutoff=cutoff, regime=regime)
                passed = t3[t3["tier3_pass"].astype(bool)].sort_values("raw_prob",ascending=False)
            except: continue
            if len(passed)==0: continue

            top_syms = passed.head(TOP_K)["symbol"].tolist()
            day_rets = []
            for sym in top_syms:
                r = grp[grp["symbol"]==sym]
                if not r.empty and pd.notna(r["fwd_ret"].iloc[0]):
                    day_rets.append({"fwd_ret":r["fwd_ret"].iloc[0],
                                     "max_dd":r["max_dd"].iloc[0],"regime":regime})
            if day_rets:
                ddf = pd.DataFrame(day_rets)
                day_rows.append({
                    "date":date,"regime":regime,
                    "wr5":(ddf["fwd_ret"]>=0.05).mean(),
                    "mean_ret":ddf["fwd_ret"].mean(),
                    "label_wr":((ddf["fwd_ret"]>=0.05)&(ddf["max_dd"]>=-0.10)).mean(),
                })

        if day_rows:
            results[sc_name] = pd.DataFrame(day_rows)
            log.info("  %s: %d days", sc_name, len(day_rows))

    # Print comparison
    log.info("")
    log.info("  ┌─────────────────────────────────────────────────────────┐")
    log.info("  │  PRECISION@%d — v3b only vs v3i hybrid                  │", TOP_K)
    log.info("  │  Base WR: %.1f%%                                         │", base_wr*100)
    log.info("  ├─────────────────────────────────────────────────────────┤")
    mods = list(results.keys())
    for label, fn in [
        ("Days có signal", lambda d: f"{len(d):>5}"),
        ("WR (ret≥5%)",    lambda d: f"{d['wr5'].mean():>5.1%}"),
        ("Mean return",    lambda d: f"{d['mean_ret'].mean():>5.2%}"),
        ("Sharpe",         lambda d: f"{d['mean_ret'].mean()/d['mean_ret'].std():>5.3f}" if d['mean_ret'].std()>0 else "    —"),
        ("Lift vs base",   lambda d: f"{d['wr5'].mean()/base_wr:>5.2f}x"),
    ]:
        row = f"  │  {label:<20}"
        for m in mods:
            row += f"  {fn(results[m]):>12}"
        log.info("%s  │", row)
    log.info("  └─────────────────────────────────────────────────────────┘")

    # Regime breakdown
    log.info("")
    log.info("  Regime WR (ret≥5%):")
    for reg in ["bull","sideways","deep_bear","choppy","recovery"]:
        row = f"    {reg:<12}"
        for m in mods:
            s = results[m][results[m]["regime"]==reg]
            row += f"  {s['wr5'].mean():.1%}(n={len(s):3d})" if len(s)>=3 else f"  {'—':>14}"
        log.info("%s", row)

    # Save v3i config
    v3i_dir = MODELS_DIR / "v3i"
    if results:
        best = max(results, key=lambda m: results[m]["wr5"].mean())
        best_wr = results[best]["wr5"].mean()
        improvement = best_wr - results["v3b only"]["wr5"].mean() if "v3b only" in results else 0
        log.info("")
        log.info("  Best: %s  WR@%d=%.1f%%  Improvement: %+.1f%%", best, TOP_K, best_wr*100, improvement*100)

        cfg = {
            "_version":     "v3i",
            "_description": "v3i — per-regime hybrid routing",
            "_architecture": "hybrid_routing",
            "_routing": {
                "deep_bear": "v3i/model_deep_bear.pkl",
                "choppy":    "v3i/model_deep_bear.pkl",
                "bull":      "v3i/model_bull.pkl",
                "recovery":  "v3i/model_bull.pkl",
                "sideways":  "v3b/lgbm_model_20d.pkl",
                "default":   "v3b/lgbm_model_20d.pkl",
            },
            "_backtest_wr": {
                m: round(results[m]["wr5"].mean(), 4) for m in results
            },
            "_best_scenario": best,
        }
        (v3i_dir / "config.json").write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log.info("  Config saved → %s", v3i_dir / "config.json")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main(start_step: int = 1) -> None:
    t_total = time.time()
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  Experiment v3i — Per-Regime Model (v2: +model_bull) ║")
    log.info("║  deep_bear/choppy → model_deep_bear                  ║")
    log.info("║  bull/recovery    → model_bull                       ║")
    log.info("║  sideways         → v3b                              ║")
    log.info("╚══════════════════════════════════════════════════════╝")

    # Step 1: Always needed — regime labels are shared across steps
    if start_step <= 1:
        regime_labels = step1_compute_regime_labels()
    else:
        log.info("STEP 1: Loading cached regime labels...")
        if REGIME_LABELS_CACHE.exists():
            regime_labels = pd.read_parquet(REGIME_LABELS_CACHE)["regime"]
            regime_labels.index = pd.to_datetime(regime_labels.index)
        else:
            log.warning("Cache not found, recomputing...")
            regime_labels = step1_compute_regime_labels()

    # Step 3: train deep_bear model
    if start_step <= 3:
        result = step3_train_deep_bear(regime_labels)
        if not result:
            log.error("Deep_bear training failed.")
            return
    else:
        log.info("STEP 3 (deep_bear): SKIPPED")

    # Step 5: train bull model (step 4 = backtest-only skips this)
    if start_step <= 5 and start_step != 4:
        result_bull = step5_train_bull(regime_labels)
        if not result_bull:
            log.error("Bull training failed.")
            return
    else:
        log.info("STEP 5 (bull): SKIPPED")

    # Step 4: backtest (always)
    step4_backtest(regime_labels)

    log.info("")
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  EXPERIMENT v3i COMPLETE  (%.0f phút)               ║", (time.time()-t_total)/60)
    log.info("╚══════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, default=1,
                        help="1=full, 3=skip labels, 5=bull only, 4=backtest only")
    args = parser.parse_args()
    main(start_step=args.step)
