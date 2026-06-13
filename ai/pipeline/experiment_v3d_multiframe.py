"""
Experiment v3d — Hướng 4: Multi-Timeframe Features (Weekly)

11 features mới thêm vào v3a base:
  weekly_rsi_14           — RSI(14) trên weekly bars (~3.5 tháng)
  weekly_rsi_7            — RSI(7) trên weekly bars (momentum nhanh hơn)
  weekly_macd_hist        — MACD histogram trên weekly
  weekly_macd_slope       — MACD slope weekly (hist[-1] - hist[-3])
  weekly_macd_cross_up    — MACD histogram flipped positive tuần này
  weekly_vol_ratio_4w     — Volume tuần này / avg 4 tuần
  weekly_close_vs_ema20w  — Close / EMA(20) weekly (20 tuần ≈ 5 tháng)
  weekly_momentum_4w      — Return 4 tuần
  weekly_momentum_13w     — Return 13 tuần (1 quý)
  weekly_pos_in_52w       — Vị trí trong range 52 tuần [0,1]
  weekly_consec_up        — Số tuần tăng liên tiếp

Pipeline:
  Step 1 — Rebuild feature files 2022→ với 11 weekly features  (~90-100 phút)
  Step 2 — Rebuild training_set_20d  (~20 phút)
  Step 3 — Train LightGBM v3d (TRAIN_START=2022-07, + weekly features)  (~3-5 phút)
  Step 4 — Compare AUC + feature importance v3a vs v3d

Chạy:
    python -m pipeline.experiment_v3d_multiframe
    python -m pipeline.experiment_v3d_multiframe --step 2   # skip rebuild features
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path

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
        logging.FileHandler(LOG_DIR / "experiment_v3d_multiframe.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

FEATURES_DIR = ROOT / "data" / "features"
MODELS_DIR   = ROOT / "data" / "models"
LABELS_DIR   = ROOT / "data" / "labels"

NEW_WEEKLY_FEATURES = [
    "weekly_rsi_14",
    "weekly_rsi_7",
    "weekly_macd_hist",
    "weekly_macd_slope",
    "weekly_macd_cross_up",
    "weekly_vol_ratio_4w",
    "weekly_close_vs_ema20w",
    "weekly_momentum_4w",
    "weekly_momentum_13w",
    "weekly_pos_in_52w",
    "weekly_consec_up",
]


# ══════════════════════════════════════════════════════════════════════════════
# Step 1: Rebuild feature files 2022→ với weekly features
# ══════════════════════════════════════════════════════════════════════════════

def step1_rebuild_features() -> None:
    log.info("=" * 60)
    log.info("STEP 1: Rebuild feature files 2022→ với weekly features")
    log.info("  New features (%d): %s", len(NEW_WEEKLY_FEATURES), NEW_WEEKLY_FEATURES)
    log.info("  ETA: ~90-100 phút")
    log.info("=" * 60)

    import pandas as pd
    from pipeline.phase2_feature_pipeline import run as phase2_run

    vnindex_path = ROOT / "data" / "ohlcv" / "VNINDEX.parquet"
    vni = pd.read_parquet(vnindex_path, columns=["time"])
    vni["time"] = pd.to_datetime(vni["time"])

    import datetime as dt
    start = dt.date(2022, 1, 1)
    trading_days = sorted(
        d.strftime("%Y-%m-%d")
        for d in vni["time"].dt.date
        if d >= start
    )
    log.info("Trading days 2022→: %d", len(trading_days))

    # Check which files need rebuild
    need_rebuild = []
    already_ok   = 0
    for ds in trading_days:
        feat_path = FEATURES_DIR / f"{ds}.parquet"
        if not feat_path.exists():
            need_rebuild.append(ds)
            continue
        try:
            cols = pd.read_parquet(feat_path).columns.tolist()
            if not all(f in cols for f in NEW_WEEKLY_FEATURES):
                need_rebuild.append(ds)
            else:
                already_ok += 1
        except Exception:
            need_rebuild.append(ds)

    log.info("Already has weekly features: %d | Need rebuild: %d", already_ok, len(need_rebuild))

    if not need_rebuild:
        log.info("  Tất cả files đã có weekly features — skip ✅")
        return

    t_start = time.time()
    success, failed = 0, []

    for i, ds in enumerate(need_rebuild, 1):
        elapsed = time.time() - t_start
        if i % 100 == 0 or i == 1 or i == len(need_rebuild):
            eta_str = ""
            if i > 1:
                avg = elapsed / (i - 1)
                remaining = avg * (len(need_rebuild) - i + 1)
                eta_str = f"  ETA {remaining / 60:.0f}m"
            log.info("  [%d/%d] %s%s", i, len(need_rebuild), ds, eta_str)

        try:
            phase2_run(target_date=ds, save=True)
            success += 1
        except Exception as exc:
            log.warning("  FAIL %s: %s", ds, exc)
            failed.append(ds)

    log.info(
        "Step 1 DONE ✅ — %d OK / %d failed (%.0fs)",
        success, len(failed), time.time() - t_start,
    )
    if failed:
        log.warning("  Failed: %s", failed[:5])


# ══════════════════════════════════════════════════════════════════════════════
# Step 2: Rebuild training set
# ══════════════════════════════════════════════════════════════════════════════

def step2_rebuild_training_set() -> None:
    log.info("=" * 60)
    log.info("STEP 2: Rebuild training_set_20d  (~20 phút)")
    log.info("=" * 60)

    from pipeline.phase3b_label_generator_20d import (
        compute_raw_labels_20d, build_training_set_20d,
    )

    log.info("  2a. Raw labels (reuse nếu đã có)...")
    raw = compute_raw_labels_20d(save=True)
    log.info("  raw labels: %d rows", len(raw))

    log.info("  2b. Training set (features ⋈ labels)...")
    ts = build_training_set_20d(save=True)
    log.info("  training set: %d rows | label=%.1f%%",
             len(ts), ts["label"].mean() * 100 if "label" in ts.columns else 0)

    new_in_ts = [f for f in NEW_WEEKLY_FEATURES if f in ts.columns]
    log.info("  Weekly features in training set: %d/%d",
             len(new_in_ts), len(NEW_WEEKLY_FEATURES))
    if len(new_in_ts) < len(NEW_WEEKLY_FEATURES):
        missing = [f for f in NEW_WEEKLY_FEATURES if f not in ts.columns]
        log.warning("  Missing: %s", missing)

    log.info("Step 2 DONE ✅")


# ══════════════════════════════════════════════════════════════════════════════
# Step 3: Train v3d
# ══════════════════════════════════════════════════════════════════════════════

def step3_train_v3d() -> dict:
    log.info("=" * 60)
    log.info("STEP 3: Train LightGBM v3d  (~3-5 phút)")
    log.info("  Same TRAIN_START=2022-07-01, thêm 11 weekly features")
    log.info("=" * 60)

    import pandas as pd
    import pipeline.phase4b_ml_model_20d as p4b

    df = p4b.prepare_dataset()

    new_in_df = [f for f in NEW_WEEKLY_FEATURES if f in df.columns]
    log.info("  Weekly features in dataset: %d/%d", len(new_in_df), len(NEW_WEEKLY_FEATURES))
    if len(new_in_df) < len(NEW_WEEKLY_FEATURES):
        missing = [f for f in NEW_WEEKLY_FEATURES if f not in df.columns]
        log.warning("  Missing from dataset: %s", missing)

    log.info("  Dataset: %d rows | label=%.1f%%",
             len(df), df["label"].mean() * 100 if "label" in df.columns else 0)

    model, feat_cols, metrics = p4b.train(df)

    # Save to v3d/
    v3d_dir = MODELS_DIR / "v3d"
    v3d_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = v3d_dir / "lgbm_model_20d.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump({
            "model":         model,
            "feat_cols":     feat_cols,
            "horizon":       "20d",
            "ret_threshold": 0.05,
            "prob_cutoff":   0.50,
            "experiment":    "multiframe_weekly_v3d",
        }, f)

    metrics_path = v3d_dir / "eval_metrics_20d.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    fi = pd.DataFrame({
        "feature":    feat_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    fi.to_csv(v3d_dir / "feature_importance_20d.csv", index=False)

    log.info("  v3d saved → %s", v3d_dir)
    log.info("Step 3 DONE ✅")
    return {"model": model, "feat_cols": feat_cols, "metrics": metrics, "fi": fi}


# ══════════════════════════════════════════════════════════════════════════════
# Step 4: Compare v3a vs v3d
# ══════════════════════════════════════════════════════════════════════════════

def step4_compare(v3d_result: dict) -> dict:
    log.info("=" * 60)
    log.info("STEP 4: Compare v3a vs v3d + weekly feature importance")
    log.info("=" * 60)

    import pandas as pd
    from pipeline.model_registry import load_metrics, load_config

    v3a_m = load_metrics("v3a")
    v3d_m = v3d_result["metrics"]

    v3a_test = v3a_m.get("test", {}).get("roc_auc", 0.0)
    v3a_val  = v3a_m.get("val",  {}).get("roc_auc", 0.0)
    v3d_test = v3d_m.get("test", {}).get("roc_auc", 0.0)
    v3d_val  = v3d_m.get("val",  {}).get("roc_auc", 0.0)
    delta    = v3d_test - v3a_test

    log.info("")
    log.info("  ┌──────────────────────────────────────────────────────────┐")
    log.info("  │             v3a (base)    v3d (+weekly MTF)   Δ        │")
    log.info("  ├──────────────────────────────────────────────────────────┤")
    log.info("  │  Test AUC:  %.4f         %.4f          %+.4f   │",
             v3a_test, v3d_test, delta)
    log.info("  │  Val  AUC:  %.4f         %.4f          %+.4f   │",
             v3a_val, v3d_val, v3d_val - v3a_val)
    log.info("  └──────────────────────────────────────────────────────────┘")

    fi = v3d_result["fi"]
    log.info("")
    log.info("  Weekly feature importance trong v3d:")
    for feat in NEW_WEEKLY_FEATURES:
        row = fi[fi["feature"] == feat]
        imp = int(row["importance"].iloc[0]) if not row.empty else 0
        log.info("    %-30s = %d", feat, imp)

    log.info("")
    log.info("  Top 15 features v3d:")
    for _, row in fi.head(15).iterrows():
        marker = " ◄ NEW" if row["feature"] in NEW_WEEKLY_FEATURES else ""
        log.info("    %-30s = %d%s", row["feature"], int(row["importance"]), marker)

    if delta >= 0.002:
        verdict = "✅ v3d TỐT HƠN — weekly MTF cải thiện signal"
    elif delta >= -0.002:
        verdict = "🟡 v3d TƯƠNG ĐƯƠNG — xem feature importance để quyết định"
    else:
        verdict = "⚠️ v3d KÉM HƠN — weekly features chưa đóng góp"

    log.info("")
    log.info("  Kết luận: %s  (Δ=%+.4f)", verdict, delta)

    # Save config
    v3d_dir = MODELS_DIR / "v3d"
    try:
        v3a_cfg = load_config("v3a")
        v3d_cfg = v3a_cfg.copy()
    except Exception:
        v3d_cfg = {}

    v3d_cfg.update({
        "_version":      "v3d",
        "_description":  "v3d — multi-timeframe: 11 weekly features added",
        "_created":      datetime.now().strftime("%Y-%m-%d"),
        "_experiment":   "multiframe_weekly_v3d",
        "_new_features": NEW_WEEKLY_FEATURES,
        "_auc_v3a":      round(v3a_test, 4),
        "_auc_v3d":      round(v3d_test, 4),
        "_auc_delta":    round(delta, 4),
    })
    (v3d_dir / "config.json").write_text(
        json.dumps(v3d_cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "v3a_test": v3a_test, "v3d_test": v3d_test,
        "delta": delta, "verdict": verdict,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main(start_step: int = 1) -> None:
    t_total = time.time()
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  Experiment v3d — Hướng 4: Multi-Timeframe Weekly   ║")
    log.info("╚══════════════════════════════════════════════════════╝")

    if start_step <= 1:
        step1_rebuild_features()
    else:
        log.info("STEP 1: SKIPPED")

    if start_step <= 2:
        step2_rebuild_training_set()
    else:
        log.info("STEP 2: SKIPPED")

    if start_step <= 3:
        result3 = step3_train_v3d()
    else:
        log.info("STEP 3: SKIPPED — loading existing v3d")
        import pandas as pd
        v3d_dir = MODELS_DIR / "v3d"
        with open(v3d_dir / "lgbm_model_20d.pkl", "rb") as f:
            payload = pickle.load(f)
        with open(v3d_dir / "eval_metrics_20d.json") as f:
            metrics = json.load(f)
        fi = pd.read_csv(v3d_dir / "feature_importance_20d.csv")
        result3 = {"model": payload["model"], "feat_cols": payload["feat_cols"],
                   "metrics": metrics, "fi": fi}

    comparison = step4_compare(result3)

    elapsed = time.time() - t_total
    log.info("")
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  EXPERIMENT v3d COMPLETE  (%.0f phút)               ║", elapsed / 60)
    log.info("║  v3a: %.4f  →  v3d: %.4f  Δ=%+.4f             ║",
             comparison["v3a_test"], comparison["v3d_test"], comparison["delta"])
    log.info("║  %s", comparison["verdict"])
    log.info("╚══════════════════════════════════════════════════════╝")
    log.info("")
    log.info("Bước tiếp theo nếu v3d tốt hơn:")
    log.info("  Discord → 🔧 Model Versions → 👁️ Shadow ON → v3d")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, default=1)
    args = parser.parse_args()
    main(start_step=args.step)
