"""
Experiment v3b — Hướng 2: Better Foreign Flow Features

4 features mới thêm vào v3a base:
  foreign_trend_5_20    — acceleration (5d/20d normalized)
  foreign_cum_flow_63d  — 3-month cumulative flow
  foreign_flow_reversal — reversal signal (sign 5d != sign 20d)
  foreign_buy_pct_20d   — buy% 20d window

Pipeline:
  Step 1 — Rebuild feature files 2022→ với 4 features mới  (~15-20 phút)
  Step 2 — Rebuild training_set_20d  (~5 phút)
  Step 3 — Train LightGBM v3b (giữ TRAIN_START=2022-07, chỉ thêm features)  (~3-5 phút)
  Step 4 — Compare AUC + feature importance v3a vs v3b

Chạy:
    python -m pipeline.experiment_v3b_foreign_flow
    python -m pipeline.experiment_v3b_foreign_flow --step 2   # skip rebuild features
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
        logging.FileHandler(LOG_DIR / "experiment_v3b_foreign_flow.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

FEATURES_DIR = ROOT / "data" / "features"
MODELS_DIR   = ROOT / "data" / "models"
LABELS_DIR   = ROOT / "data" / "labels"

NEW_FOREIGN_FEATURES = [
    "foreign_trend_5_20",
    "foreign_cum_flow_63d",
    "foreign_flow_reversal",
    "foreign_buy_pct_20d",
]


# ══════════════════════════════════════════════════════════════════════════════
# Step 1: Rebuild feature files 2022→ với new foreign features
# ══════════════════════════════════════════════════════════════════════════════

def step1_rebuild_features() -> None:
    log.info("=" * 60)
    log.info("STEP 1: Rebuild feature files 2022→ với foreign features mới")
    log.info("  New features: %s", NEW_FOREIGN_FEATURES)
    log.info("  ETA: ~15-20 phút")
    log.info("=" * 60)

    import pandas as pd
    from pipeline.phase2_feature_pipeline import run as phase2_run

    # Lấy trading days từ VNINDEX
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

    # Check which files need rebuild (missing new features)
    need_rebuild = []
    already_ok   = 0
    for ds in trading_days:
        feat_path = FEATURES_DIR / f"{ds}.parquet"
        if not feat_path.exists():
            need_rebuild.append(ds)
            continue
        # Check nếu đã có new features
        try:
            cols = pd.read_parquet(feat_path).columns.tolist()
            if not all(f in cols for f in NEW_FOREIGN_FEATURES):
                need_rebuild.append(ds)
            else:
                already_ok += 1
        except Exception:
            need_rebuild.append(ds)

    log.info(
        "Already has new features: %d | Need rebuild: %d",
        already_ok, len(need_rebuild)
    )

    if not need_rebuild:
        log.info("  Tất cả files đã có new features — skip ✅")
        return

    t_start = time.time()
    success, failed = 0, []

    for i, ds in enumerate(need_rebuild, 1):
        elapsed = time.time() - t_start
        eta_str = ""
        if i > 1:
            avg = elapsed / (i - 1)
            remaining = avg * (len(need_rebuild) - i + 1)
            eta_str = f"  ETA {remaining / 60:.0f}m"

        if i % 100 == 0 or i == 1 or i == len(need_rebuild):
            log.info("  [%d/%d] %s%s", i, len(need_rebuild), ds, eta_str)

        try:
            phase2_run(target_date=ds, save=True)
            success += 1
        except Exception as exc:
            log.warning("  FAIL %s: %s", ds, exc)
            failed.append(ds)

    log.info(
        "Step 1 DONE ✅ — %d OK / %d failed (%.0fs)",
        success, len(failed), time.time() - t_start
    )
    if failed:
        log.warning("  Failed: %s", failed[:5])


# ══════════════════════════════════════════════════════════════════════════════
# Step 2: Rebuild training set
# ══════════════════════════════════════════════════════════════════════════════

def step2_rebuild_training_set() -> None:
    log.info("=" * 60)
    log.info("STEP 2: Rebuild training_set_20d  (~5 phút)")
    log.info("=" * 60)

    from pipeline.phase3b_label_generator_20d import (
        compute_raw_labels_20d, build_training_set_20d
    )

    log.info("  2a. Raw labels...")
    raw = compute_raw_labels_20d(save=True)
    log.info("  raw labels: %d rows", len(raw))

    log.info("  2b. Training set (features ⋈ labels)...")
    ts = build_training_set_20d(save=True)
    log.info("  training set: %d rows | label=%.1f%%",
             len(ts), ts["label"].mean() * 100)

    # Verify new features are in training set
    new_in_ts = [f for f in NEW_FOREIGN_FEATURES if f in ts.columns]
    log.info("  New features in training set: %d/%d — %s",
             len(new_in_ts), len(NEW_FOREIGN_FEATURES), new_in_ts)
    log.info("Step 2 DONE ✅")


# ══════════════════════════════════════════════════════════════════════════════
# Step 3: Train v3b
# ══════════════════════════════════════════════════════════════════════════════

def step3_train_v3b() -> dict:
    log.info("=" * 60)
    log.info("STEP 3: Train LightGBM v3b  (~3-5 phút)")
    log.info("  Same TRAIN_START=2022-07-01, thêm 4 foreign features")
    log.info("=" * 60)

    import pipeline.phase4b_ml_model_20d as p4b

    df = p4b.prepare_dataset()

    # Log new features presence
    new_in_df = [f for f in NEW_FOREIGN_FEATURES if f in df.columns]
    log.info("  New features in dataset: %d/%d", len(new_in_df), len(NEW_FOREIGN_FEATURES))
    if len(new_in_df) < len(NEW_FOREIGN_FEATURES):
        missing = [f for f in NEW_FOREIGN_FEATURES if f not in df.columns]
        log.warning("  Missing from dataset: %s", missing)

    log.info("  Dataset: %d rows | label=%.1f%%",
             len(df), df["label"].mean() * 100 if "label" in df.columns else 0)

    model, feat_cols, metrics = p4b.train(df)

    # Save to v3b/
    v3b_dir = MODELS_DIR / "v3b"
    v3b_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = v3b_dir / "lgbm_model_20d.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump({
            "model":         model,
            "feat_cols":     feat_cols,
            "horizon":       "20d",
            "ret_threshold": 0.05,
            "prob_cutoff":   0.50,
            "experiment":    "foreign_flow_v2",
        }, f)

    metrics_path = v3b_dir / "eval_metrics_20d.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    # Save feature importance
    import pandas as pd
    fi = pd.DataFrame({
        "feature":    feat_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    fi.to_csv(v3b_dir / "feature_importance_20d.csv", index=False)

    log.info("  v3b saved → %s", v3b_dir)
    log.info("Step 3 DONE ✅")
    return {"model": model, "feat_cols": feat_cols, "metrics": metrics, "fi": fi}


# ══════════════════════════════════════════════════════════════════════════════
# Step 4: Compare + register
# ══════════════════════════════════════════════════════════════════════════════

def step4_compare(v3b_result: dict) -> dict:
    log.info("=" * 60)
    log.info("STEP 4: Compare v3a vs v3b + feature importance")
    log.info("=" * 60)

    import pandas as pd
    from pipeline.model_registry import load_metrics, load_config

    v3a_m = load_metrics("v3a")
    v3b_m = v3b_result["metrics"]

    v3a_test = v3a_m.get("test", {}).get("roc_auc", 0.0)
    v3a_val  = v3a_m.get("val",  {}).get("roc_auc", 0.0)
    v3b_test = v3b_m.get("test", {}).get("roc_auc", 0.0)
    v3b_val  = v3b_m.get("val",  {}).get("roc_auc", 0.0)
    delta    = v3b_test - v3a_test

    log.info("")
    log.info("  ┌─────────────────────────────────────────────────────────┐")
    log.info("  │              v3a (base)    v3b (+foreign v2)   Δ       │")
    log.info("  ├─────────────────────────────────────────────────────────┤")
    log.info("  │  Test AUC:   %.4f          %.4f          %+.4f  │",
             v3a_test, v3b_test, delta)
    log.info("  │  Val  AUC:   %.4f          %.4f          %+.4f  │",
             v3a_val,  v3b_val,  v3b_val - v3a_val)
    log.info("  └─────────────────────────────────────────────────────────┘")
    log.info("")

    # Feature importance của new features
    fi = v3b_result["fi"]
    log.info("  New feature importance trong v3b:")
    for feat in NEW_FOREIGN_FEATURES:
        row = fi[fi["feature"] == feat]
        imp = int(row["importance"].iloc[0]) if not row.empty else 0
        log.info("    %-30s = %d", feat, imp)

    log.info("")
    log.info("  Top 10 features v3b:")
    for _, row in fi.head(10).iterrows():
        log.info("    %-30s = %d", row["feature"], int(row["importance"]))

    if delta >= 0.002:
        verdict = "✅ v3b TỐT HƠN — recommend shadow mode"
    elif delta >= -0.002:
        verdict = "🟡 v3b TƯƠNG ĐƯƠNG — check signal quality thực tế"
    else:
        verdict = "⚠️ v3b KÉM HƠN — features chưa đủ tốt"
    log.info("")
    log.info("  Kết luận: %s", verdict)

    # Update v3b config
    v3b_dir = MODELS_DIR / "v3b"
    v3a_cfg = load_config("v3a")
    v3b_cfg = v3a_cfg.copy()
    v3b_cfg.update({
        "_version":     "v3b",
        "_description": "v3b — foreign flow v2 (trend + cum + reversal + buy_pct_20d)",
        "_created":     datetime.now().strftime("%Y-%m-%d"),
        "_experiment":  "foreign_flow_v2",
        "_new_features": NEW_FOREIGN_FEATURES,
        "_auc_delta_vs_v3a": round(delta, 4),
    })
    (v3b_dir / "config.json").write_text(
        json.dumps(v3b_cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "v3a_test": v3a_test, "v3b_test": v3b_test,
        "delta": delta, "verdict": verdict,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main(start_step: int = 1) -> None:
    t_total = time.time()
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  Experiment v3b — Hướng 2: Better Foreign Flow      ║")
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
        result3 = step3_train_v3b()
    else:
        log.info("STEP 3: SKIPPED — loading existing v3b")
        import pandas as pd
        v3b_dir = MODELS_DIR / "v3b"
        with open(v3b_dir / "lgbm_model_20d.pkl", "rb") as f:
            payload = pickle.load(f)
        with open(v3b_dir / "eval_metrics_20d.json") as f:
            metrics = json.load(f)
        fi = pd.read_csv(v3b_dir / "feature_importance_20d.csv")
        result3 = {"model": payload["model"], "feat_cols": payload["feat_cols"],
                   "metrics": metrics, "fi": fi}

    comparison = step4_compare(result3)

    elapsed = time.time() - t_total
    log.info("")
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  EXPERIMENT COMPLETE  (%.0f phút)                    ║", elapsed / 60)
    log.info("║  v3a: %.4f  →  v3b: %.4f  Δ=%+.4f              ║",
             comparison["v3a_test"], comparison["v3b_test"], comparison["delta"])
    log.info("║  %s", comparison["verdict"])
    log.info("╚══════════════════════════════════════════════════════╝")
    log.info("")
    log.info("Bước tiếp theo nếu v3b tốt hơn:")
    log.info("  Discord → 🔧 Model Versions → 👁️ Shadow ON → v3b")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, default=1)
    args = parser.parse_args()
    main(start_step=args.step)
