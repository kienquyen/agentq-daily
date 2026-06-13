"""
Experiment v3e — Foreign Flow Interaction Features

3 features mới thêm vào v3b base (v3b = v3a + 4 foreign flow features):
  foreign_alignment        — 1 nếu net_val_5d và cum_flow_63d cùng chiều (short/long aligned)
  foreign_selling_decel    — 1 nếu |flow_last21d| < |flow_prev42d| (selling đang chậm lại)
  foreign_net_days_pct_20d — fraction of last 20 days với net buying (0–1), normalized

Motivation:
  v3b treats foreign flow features independently. The model cannot detect when
  short-term buying (buy_pct_20d=0.47) contradicts structural selling (cum_flow_63d<0).
  CII Jan 2026 edge case: foreign doing tactical buying in structural downtrend.
  These interaction features capture the relationship between timeframes explicitly.

Pipeline:
  Step 1 — Rebuild feature files 2020→ với 3 new interaction features  (~30-40 phút)
  Step 2 — Rebuild training_set_20d  (~5 phút)
  Step 3 — Train LightGBM v3e (v3b base + 3 interaction features, TRAIN_START=2020-01-01)  (~3-5 phút)
  Step 4 — Compare AUC + feature importance v3a / v3b / v3e

Chạy:
    python -m pipeline.experiment_v3e_interaction
    python -m pipeline.experiment_v3e_interaction --step 2   # skip rebuild features
    python -m pipeline.experiment_v3e_interaction --step 3   # skip to train only
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
        logging.FileHandler(LOG_DIR / "experiment_v3e_interaction.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

FEATURES_DIR = ROOT / "data" / "features"
MODELS_DIR   = ROOT / "data" / "models"
LABELS_DIR   = ROOT / "data" / "labels"

# v3b base features (must already be in feature files)
V3B_FEATURES = [
    "foreign_trend_5_20",
    "foreign_cum_flow_63d",
    "foreign_flow_reversal",
    "foreign_buy_pct_20d",
]

# New v3e interaction features
NEW_INTERACTION_FEATURES = [
    "foreign_alignment",
    "foreign_selling_decel",
    "foreign_net_days_pct_20d",
]

ALL_NEW_FEATURES = V3B_FEATURES + NEW_INTERACTION_FEATURES


# ══════════════════════════════════════════════════════════════════════════════
# Step 1: Rebuild feature files 2022→ với 3 interaction features mới
# ══════════════════════════════════════════════════════════════════════════════

def step1_rebuild_features() -> None:
    log.info("=" * 60)
    log.info("STEP 1: Rebuild feature files 2022→ với interaction features")
    log.info("  New features (%d): %s", len(NEW_INTERACTION_FEATURES), NEW_INTERACTION_FEATURES)
    log.info("  ETA: ~30-40 phút (2020→ includes COVID crash + recovery regime)")
    log.info("=" * 60)

    import pandas as pd
    from pipeline.phase2_feature_pipeline import run as phase2_run

    vnindex_path = ROOT / "data" / "ohlcv" / "VNINDEX.parquet"
    vni = pd.read_parquet(vnindex_path, columns=["time"])
    vni["time"] = pd.to_datetime(vni["time"])

    import datetime as dt
    start = dt.date(2020, 1, 1)
    trading_days = sorted(
        d.strftime("%Y-%m-%d")
        for d in vni["time"].dt.date
        if d >= start
    )
    log.info("Trading days 2020→: %d", len(trading_days))

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
            if not all(f in cols for f in NEW_INTERACTION_FEATURES):
                need_rebuild.append(ds)
            else:
                already_ok += 1
        except Exception:
            need_rebuild.append(ds)

    log.info("Already has interaction features: %d | Need rebuild: %d",
             already_ok, len(need_rebuild))

    if not need_rebuild:
        log.info("  Tất cả files đã có interaction features — skip ✅")
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
        success, len(failed), time.time() - t_start,
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
        compute_raw_labels_20d, build_training_set_20d,
    )

    log.info("  2a. Raw labels (reuse nếu đã có)...")
    raw = compute_raw_labels_20d(save=True)
    log.info("  raw labels: %d rows", len(raw))

    log.info("  2b. Training set (features ⋈ labels)...")
    ts = build_training_set_20d(save=True)
    log.info("  training set: %d rows | label=%.1f%%",
             len(ts), ts["label"].mean() * 100 if "label" in ts.columns else 0)

    new_in_ts = [f for f in NEW_INTERACTION_FEATURES if f in ts.columns]
    log.info("  Interaction features in training set: %d/%d — %s",
             len(new_in_ts), len(NEW_INTERACTION_FEATURES), new_in_ts)
    if len(new_in_ts) < len(NEW_INTERACTION_FEATURES):
        missing = [f for f in NEW_INTERACTION_FEATURES if f not in ts.columns]
        log.warning("  Missing: %s", missing)

    log.info("Step 2 DONE ✅")


# ══════════════════════════════════════════════════════════════════════════════
# Step 3: Train v3e
# ══════════════════════════════════════════════════════════════════════════════

def step3_train_v3e() -> dict:
    log.info("=" * 60)
    log.info("STEP 3: Train LightGBM v3e  (~3-5 phút)")
    log.info("  Base: v3b features + 3 interaction features")
    log.info("=" * 60)

    import pandas as pd
    import pipeline.phase4b_ml_model_20d as p4b

    df = p4b.prepare_dataset()

    # Log feature presence
    new_in_df = [f for f in NEW_INTERACTION_FEATURES if f in df.columns]
    log.info("  Interaction features in dataset: %d/%d",
             len(new_in_df), len(NEW_INTERACTION_FEATURES))
    if len(new_in_df) < len(NEW_INTERACTION_FEATURES):
        missing = [f for f in NEW_INTERACTION_FEATURES if f not in df.columns]
        log.warning("  Missing from dataset: %s", missing)

    v3b_in_df = [f for f in V3B_FEATURES if f in df.columns]
    log.info("  v3b base features in dataset: %d/%d", len(v3b_in_df), len(V3B_FEATURES))

    log.info("  Dataset: %d rows | label=%.1f%%",
             len(df), df["label"].mean() * 100 if "label" in df.columns else 0)

    model, feat_cols, metrics = p4b.train(df)

    # Save to v3e/
    v3e_dir = MODELS_DIR / "v3e"
    v3e_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = v3e_dir / "lgbm_model_20d.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump({
            "model":         model,
            "feat_cols":     feat_cols,
            "horizon":       "20d",
            "ret_threshold": 0.05,
            "prob_cutoff":   0.50,
            "experiment":    "interaction_features_v3e",
        }, f)

    metrics_path = v3e_dir / "eval_metrics_20d.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    fi = pd.DataFrame({
        "feature":    feat_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    fi.to_csv(v3e_dir / "feature_importance_20d.csv", index=False)

    log.info("  v3e saved → %s", v3e_dir)
    log.info("Step 3 DONE ✅")
    return {"model": model, "feat_cols": feat_cols, "metrics": metrics, "fi": fi}


# ══════════════════════════════════════════════════════════════════════════════
# Step 4: Compare v3a / v3b / v3e
# ══════════════════════════════════════════════════════════════════════════════

def step4_compare(v3e_result: dict) -> dict:
    log.info("=" * 60)
    log.info("STEP 4: Compare v3a / v3b / v3e + feature importance")
    log.info("=" * 60)

    import pandas as pd
    from pipeline.model_registry import load_metrics, load_config

    v3a_m  = load_metrics("v3a")
    v3b_m  = load_metrics("v3b")
    v3e_m  = v3e_result["metrics"]

    v3a_test = v3a_m.get("test", {}).get("roc_auc", 0.0)
    v3a_val  = v3a_m.get("val",  {}).get("roc_auc", 0.0)
    v3b_test = v3b_m.get("test", {}).get("roc_auc", 0.0)
    v3b_val  = v3b_m.get("val",  {}).get("roc_auc", 0.0)
    v3e_test = v3e_m.get("test", {}).get("roc_auc", 0.0)
    v3e_val  = v3e_m.get("val",  {}).get("roc_auc", 0.0)

    delta_vs_v3a = v3e_test - v3a_test
    delta_vs_v3b = v3e_test - v3b_test

    log.info("")
    log.info("  ┌──────────────────────────────────────────────────────────────────┐")
    log.info("  │          v3a (prod)    v3b (shadow)    v3e (+interaction)      │")
    log.info("  ├──────────────────────────────────────────────────────────────────┤")
    log.info("  │  Test AUC:  %.4f       %.4f          %.4f                │",
             v3a_test, v3b_test, v3e_test)
    log.info("  │  Val  AUC:  %.4f       %.4f          %.4f                │",
             v3a_val,  v3b_val,  v3e_val)
    log.info("  │  Δ vs v3a:                             %+.4f               │",
             delta_vs_v3a)
    log.info("  │  Δ vs v3b:                             %+.4f               │",
             delta_vs_v3b)
    log.info("  └──────────────────────────────────────────────────────────────────┘")

    fi = v3e_result["fi"]

    log.info("")
    log.info("  New interaction feature importance trong v3e:")
    for feat in NEW_INTERACTION_FEATURES:
        row = fi[fi["feature"] == feat]
        imp = int(row["importance"].iloc[0]) if not row.empty else 0
        rank = fi.index[fi["feature"] == feat].tolist()
        rank_str = f"rank #{rank[0]+1}" if rank else "not found"
        log.info("    %-30s = %d  (%s)", feat, imp, rank_str)

    log.info("")
    log.info("  All foreign features importance trong v3e:")
    all_foreign = [c for c in fi["feature"] if "foreign" in c]
    for feat in all_foreign:
        row = fi[fi["feature"] == feat]
        imp = int(row["importance"].iloc[0]) if not row.empty else 0
        rank = fi.index[fi["feature"] == feat].tolist()
        rank_str = f"rank #{rank[0]+1}" if rank else "not found"
        marker = " ◄ NEW" if feat in NEW_INTERACTION_FEATURES else ""
        log.info("    %-30s = %d  (%s)%s", feat, imp, rank_str, marker)

    log.info("")
    log.info("  Top 15 features v3e:")
    for _, row in fi.head(15).iterrows():
        marker = " ◄ NEW" if row["feature"] in NEW_INTERACTION_FEATURES else ""
        log.info("    %-30s = %d%s", row["feature"], int(row["importance"]), marker)

    # Verdict
    if delta_vs_v3b >= 0.002:
        verdict = "✅ v3e TỐT HƠN v3b — interaction features cải thiện signal quality"
    elif delta_vs_v3b >= -0.002:
        verdict = "🟡 v3e TƯƠNG ĐƯƠNG v3b — xem feature importance để quyết định"
    else:
        verdict = "⚠️ v3e KÉM HƠN v3b — interaction features chưa đóng góp thêm"

    log.info("")
    log.info("  Kết luận: %s", verdict)
    log.info("  Δ v3e vs v3b: %+.4f  |  Δ v3e vs v3a: %+.4f", delta_vs_v3b, delta_vs_v3a)

    # Save config (inherit from v3b)
    v3e_dir = MODELS_DIR / "v3e"
    try:
        v3b_cfg = load_config("v3b")
        v3e_cfg = v3b_cfg.copy()
    except Exception:
        v3e_cfg = {}

    v3e_cfg.update({
        "_version":      "v3e",
        "_description":  "v3e — foreign flow interaction features (alignment + decel + consistency)",
        "_created":      datetime.now().strftime("%Y-%m-%d"),
        "_experiment":   "interaction_features_v3e",
        "_base_version": "v3b",
        "_new_features": NEW_INTERACTION_FEATURES,
        "_auc_v3a":      round(v3a_test, 4),
        "_auc_v3b":      round(v3b_test, 4),
        "_auc_v3e":      round(v3e_test, 4),
        "_auc_delta_vs_v3b": round(delta_vs_v3b, 4),
        "_auc_delta_vs_v3a": round(delta_vs_v3a, 4),
    })
    (v3e_dir / "config.json").write_text(
        json.dumps(v3e_cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("  Config saved → %s", v3e_dir / "config.json")

    return {
        "v3a_test": v3a_test, "v3b_test": v3b_test, "v3e_test": v3e_test,
        "delta_vs_v3b": delta_vs_v3b, "delta_vs_v3a": delta_vs_v3a,
        "verdict": verdict,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main(start_step: int = 1) -> None:
    t_total = time.time()
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  Experiment v3e — Foreign Flow Interaction Features  ║")
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
        result3 = step3_train_v3e()
    else:
        log.info("STEP 3: SKIPPED — loading existing v3e")
        import pandas as pd
        v3e_dir = MODELS_DIR / "v3e"
        with open(v3e_dir / "lgbm_model_20d.pkl", "rb") as f:
            payload = pickle.load(f)
        with open(v3e_dir / "eval_metrics_20d.json") as f:
            metrics = json.load(f)
        fi = pd.read_csv(v3e_dir / "feature_importance_20d.csv")
        result3 = {
            "model":     payload["model"],
            "feat_cols": payload["feat_cols"],
            "metrics":   metrics,
            "fi":        fi,
        }

    comparison = step4_compare(result3)

    elapsed = time.time() - t_total
    log.info("")
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  EXPERIMENT v3e COMPLETE  (%.0f phút)               ║", elapsed / 60)
    log.info("║  v3a: %.4f → v3b: %.4f → v3e: %.4f          ║",
             comparison["v3a_test"], comparison["v3b_test"], comparison["v3e_test"])
    log.info("║  %s", comparison["verdict"])
    log.info("╚══════════════════════════════════════════════════════╝")
    log.info("")
    log.info("Bước tiếp theo nếu v3e tốt hơn hoặc tương đương v3b:")
    log.info("  1. Chạy backtest_compare để xem WR và mean_ret thực tế")
    log.info("  2. python -m pipeline.backtest_compare (v3e sẽ tự detect nếu có pkl)")
    log.info("  3. Nếu backtest tốt hơn v3b → replace shadow: echo v3e > data/models/shadow_version.txt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, default=1,
                        help="Start from step N (1=rebuild features, 2=rebuild training set, 3=train, 4=compare)")
    args = parser.parse_args()
    main(start_step=args.step)
