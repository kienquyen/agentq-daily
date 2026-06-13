"""
Experiment v3c — Hướng 3: Hybrid Label

Label mới (thay vì chỉ ret>=5% + dd>=-10%):
  ret_20d >= +5%                       (absolute floor — không lỗ tiền thật)
  (ret_20d - vnindex_ret_20d) >= +1%   (alpha: beat VNINDEX ít nhất 1%)
  rr_20d = ret / abs(max_dd) >= 1.2    (trade quality)
  max_drawdown_20d >= -10%             (giữ nguyên v3a)

So sánh positive rate:
  v3a: ~27.3% (ret>=5% + dd>=-10%)
  v3c: dự kiến ~18-22% (thêm alpha + RR filter)

Pipeline:
  Step 1 — Compute v3c hybrid labels  (~5-10 phút)
  Step 2 — Build training_set_v3c     (~5 phút)
  Step 3 — Train LightGBM v3c         (~3-5 phút)
  Step 4 — Compare v3a vs v3b vs v3c AUC

Chạy:
    python -m pipeline.experiment_v3c_hybrid_label
    python -m pipeline.experiment_v3c_hybrid_label --step 3   # skip labels rebuild
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
        logging.FileHandler(LOG_DIR / "experiment_v3c_hybrid_label.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

MODELS_DIR = ROOT / "data" / "models"
LABELS_DIR = ROOT / "data" / "labels"


# ══════════════════════════════════════════════════════════════════════════════
# Step 1: Compute v3c hybrid labels
# ══════════════════════════════════════════════════════════════════════════════

def step1_compute_labels() -> None:
    log.info("=" * 60)
    log.info("STEP 1: Compute v3c Hybrid Labels  (~5-10 phút)")
    log.info("  Conditions:")
    log.info("    ret_20d  >= +5%%")
    log.info("    max_dd   >= -10%%")
    log.info("    alpha    >= +1%%  (beat VNINDEX)")
    log.info("    RR       >= 1.2  (ret / abs(max_dd))")
    log.info("=" * 60)

    from pipeline.phase3c_label_generator_v3c import compute_raw_labels_v3c

    t = time.time()
    raw = compute_raw_labels_v3c(save=True)

    valid    = raw[raw["label_valid"] == 1] if not raw.empty else raw
    pos_v3c  = float(valid["label"].mean())    if len(valid) > 0 else 0
    pos_v3a  = float(valid["label_v3a"].mean()) if len(valid) > 0 else 0

    log.info("Step 1 DONE ✅  (%.0fs)", time.time() - t)
    log.info("  v3a positive rate: %.1f%%", pos_v3a * 100)
    log.info("  v3c positive rate: %.1f%%  (%.0f%% của v3a signals còn lại)",
             pos_v3c * 100, (pos_v3c / max(pos_v3a, 1e-9)) * 100)


# ══════════════════════════════════════════════════════════════════════════════
# Step 2: Build training set
# ══════════════════════════════════════════════════════════════════════════════

def step2_build_training_set() -> None:
    log.info("=" * 60)
    log.info("STEP 2: Build training_set_v3c  (~5 phút)")
    log.info("=" * 60)

    from pipeline.phase3c_label_generator_v3c import build_training_set_v3c

    t  = time.time()
    ts = build_training_set_v3c(save=True)

    log.info("  Training set v3c: %d rows | label=%.1f%%",
             len(ts), ts["label"].mean() * 100 if "label" in ts.columns else 0)
    log.info("Step 2 DONE ✅  (%.0fs)", time.time() - t)


# ══════════════════════════════════════════════════════════════════════════════
# Step 3: Train v3c
# ══════════════════════════════════════════════════════════════════════════════

def step3_train_v3c() -> dict:
    log.info("=" * 60)
    log.info("STEP 3: Train LightGBM v3c  (~3-5 phút)")
    log.info("  Same features as v3a/v3b, NEW hybrid label")
    log.info("=" * 60)

    import pandas as pd
    import pipeline.phase4b_ml_model_20d as p4b

    # Override training set path to use v3c labels
    training_set_path_orig = p4b.TRAINING_SET_20D_PATH
    p4b.TRAINING_SET_20D_PATH = LABELS_DIR / "training_set_v3c.parquet"

    try:
        df = p4b.prepare_dataset()
        log.info("  Dataset: %d rows | label=%.1f%%",
                 len(df), df["label"].mean() * 100 if "label" in df.columns else 0)

        model, feat_cols, metrics = p4b.train(df)
    finally:
        # Restore original path
        p4b.TRAINING_SET_20D_PATH = training_set_path_orig

    # Save to v3c/
    v3c_dir = MODELS_DIR / "v3c"
    v3c_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = v3c_dir / "lgbm_model_20d.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump({
            "model":         model,
            "feat_cols":     feat_cols,
            "horizon":       "20d",
            "ret_threshold": 0.05,
            "prob_cutoff":   0.50,
            "experiment":    "hybrid_label_v3c",
            "label_version": "v3c_hybrid",
        }, f)

    metrics_path = v3c_dir / "eval_metrics_20d.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    # Feature importance
    fi = pd.DataFrame({
        "feature":    feat_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    fi.to_csv(v3c_dir / "feature_importance_20d.csv", index=False)

    log.info("  v3c saved → %s", v3c_dir)
    log.info("Step 3 DONE ✅")
    return {"model": model, "feat_cols": feat_cols, "metrics": metrics, "fi": fi}


# ══════════════════════════════════════════════════════════════════════════════
# Step 4: Compare v3a vs v3b vs v3c
# ══════════════════════════════════════════════════════════════════════════════

def step4_compare(v3c_result: dict) -> dict:
    log.info("=" * 60)
    log.info("STEP 4: Compare v3a vs v3b vs v3c")
    log.info("=" * 60)

    import pandas as pd
    from pipeline.model_registry import load_metrics

    v3a_m = load_metrics("v3a")

    # Load v3b metrics nếu có
    v3b_metrics_path = MODELS_DIR / "v3b" / "eval_metrics_20d.json"
    v3b_m = {}
    if v3b_metrics_path.exists():
        with open(v3b_metrics_path) as f:
            v3b_m = json.load(f)

    v3c_m = v3c_result["metrics"]

    def _auc(m, split="test"):
        return m.get(split, {}).get("roc_auc", float("nan"))

    v3a_test = _auc(v3a_m)
    v3b_test = _auc(v3b_m) if v3b_m else float("nan")
    v3c_test = _auc(v3c_m)

    v3a_val  = _auc(v3a_m, "val")
    v3b_val  = _auc(v3b_m, "val") if v3b_m else float("nan")
    v3c_val  = _auc(v3c_m, "val")

    log.info("")
    log.info("  ┌─────────────────────────────────────────────────────────────────┐")
    log.info("  │           v3a (base)   v3b (+foreign)  v3c (+hybrid_label)     │")
    log.info("  ├─────────────────────────────────────────────────────────────────┤")
    if not all(v != v for v in [v3a_test, v3b_test, v3c_test]):  # has non-nan
        log.info("  │  Test AUC:  %.4f       %.4f          %.4f  (Δ=%+.4f)  │",
                 v3a_test,
                 v3b_test if v3b_test == v3b_test else 0,
                 v3c_test,
                 v3c_test - v3a_test)
        log.info("  │  Val  AUC:  %.4f       %.4f          %.4f  (Δ=%+.4f)  │",
                 v3a_val,
                 v3b_val if v3b_val == v3b_val else 0,
                 v3c_val,
                 v3c_val - v3a_val)
    log.info("  └─────────────────────────────────────────────────────────────────┘")

    delta = v3c_test - v3a_test
    if delta >= 0.003:
        verdict = "✅ v3c TỐT HƠN v3a — Hybrid label cải thiện signal quality"
    elif delta >= -0.002:
        verdict = "🟡 v3c TƯƠNG ĐƯƠNG — Xem xét precision/recall trên backtest thực tế"
    else:
        verdict = "⚠️ v3c AUC thấp hơn — Hybrid label có thể quá strict (positive rate thấp)"

    log.info("")
    log.info("  Kết luận: %s", verdict)

    # Feature importance
    fi = v3c_result["fi"]
    log.info("")
    log.info("  Top 10 features v3c (label thay đổi nhưng features giữ nguyên):")
    for _, row in fi.head(10).iterrows():
        log.info("    %-30s = %d", row["feature"], int(row["importance"]))

    # Load v3c label stats for context
    stats_path = LABELS_DIR / "label_stats_v3c.json"
    if stats_path.exists():
        stats = json.loads(stats_path.read_text())
        log.info("")
        log.info("  Label stats v3c:")
        log.info("    v3a positive rate: %.1f%%", stats.get("positive_rate_v3a", 0) * 100)
        log.info("    v3c positive rate: %.1f%%", stats.get("positive_rate", 0) * 100)
        log.info("    scale_pos_weight:  %.2f", stats.get("scale_pos_weight", 0))

    # Save v3c config
    v3c_dir = MODELS_DIR / "v3c"
    try:
        from pipeline.model_registry import load_config
        v3a_cfg = load_config("v3a")
        v3c_cfg = v3a_cfg.copy()
    except Exception:
        v3c_cfg = {}

    v3c_cfg.update({
        "_version":          "v3c",
        "_description":      "v3c — Hybrid label (ret>=5% + alpha>=1% + RR>=1.2 + dd>=-10%)",
        "_created":          datetime.now().strftime("%Y-%m-%d"),
        "_experiment":       "hybrid_label_v3c",
        "_label_version":    "v3c_hybrid",
        "_label_conditions": {
            "ret_20d":        ">= 5%",
            "max_dd":         ">= -10%",
            "alpha_vs_vni":   ">= 1%",
            "rr":             ">= 1.2",
        },
        "_auc_v3a":          round(v3a_test, 4),
        "_auc_v3c":          round(v3c_test, 4),
        "_auc_delta_vs_v3a": round(delta, 4),
    })
    (v3c_dir / "config.json").write_text(
        json.dumps(v3c_cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "v3a_test": v3a_test, "v3b_test": v3b_test, "v3c_test": v3c_test,
        "delta": delta, "verdict": verdict,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main(start_step: int = 1) -> None:
    t_total = time.time()
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  Experiment v3c — Hướng 3: Hybrid Label             ║")
    log.info("║  ret>=5% + alpha>=1% + RR>=1.2 + dd>=-10%          ║")
    log.info("╚══════════════════════════════════════════════════════╝")

    if start_step <= 1:
        step1_compute_labels()
    else:
        log.info("STEP 1: SKIPPED")

    if start_step <= 2:
        step2_build_training_set()
    else:
        log.info("STEP 2: SKIPPED")

    if start_step <= 3:
        result3 = step3_train_v3c()
    else:
        log.info("STEP 3: SKIPPED — loading existing v3c")
        import pandas as pd
        v3c_dir = MODELS_DIR / "v3c"
        with open(v3c_dir / "lgbm_model_20d.pkl", "rb") as f:
            payload = pickle.load(f)
        with open(v3c_dir / "eval_metrics_20d.json") as f:
            metrics = json.load(f)
        fi = pd.read_csv(v3c_dir / "feature_importance_20d.csv")
        result3 = {"model": payload["model"], "feat_cols": payload["feat_cols"],
                   "metrics": metrics, "fi": fi}

    comparison = step4_compare(result3)

    elapsed = time.time() - t_total
    log.info("")
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  EXPERIMENT v3c COMPLETE  (%.0f phút)               ║", elapsed / 60)
    log.info("║  v3a: %.4f  →  v3c: %.4f  Δ=%+.4f              ║",
             comparison["v3a_test"], comparison["v3c_test"], comparison["delta"])
    log.info("║  %s", comparison["verdict"])
    log.info("╚══════════════════════════════════════════════════════╝")
    log.info("")
    log.info("Tiếp theo:")
    log.info("  Nếu v3c tốt hơn → shadow mode: Discord → 🔧 Model Versions → 👁️ Shadow ON → v3c")
    log.info("  Nếu không → kết hợp v3b + v3c features (Hướng 4)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, default=1,
                        help="Bắt đầu từ step nào (1-4). Mặc định: 1")
    args = parser.parse_args()
    main(start_step=args.step)
