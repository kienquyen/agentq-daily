"""
Experiment v3b — Hướng 1: Mở rộng dữ liệu lịch sử từ 2017

Mục tiêu: kiểm tra xem training với 2017→ có cải thiện AUC và signal quality so với v3a (2022→)

Pipeline:
  Step 1 — OHLCV backfill 2017-01-01 → hiện tại   (~30-60 phút)
  Step 2 — Build phase2 features cho 2017-07 → 2021-12   (~60-120 phút)
  Step 3 — Rebuild raw_labels_20d + training_set_20d   (~5-10 phút)
  Step 4 — Train LightGBM v3b (TRAIN_START=2017-07-01)  (~3-5 phút)
  Step 5 — So sánh v3a vs v3b AUC + lưu v3b vào registry

Chạy:
    python -m pipeline.experiment_v3b_history2017
    python -m pipeline.experiment_v3b_history2017 --step 2   # chỉ chạy từ step 2
    python -m pipeline.experiment_v3b_history2017 --skip-ohlcv  # bỏ qua step 1

Kết quả:
    data/models/v3b/   (lgbm_model_20d.pkl, eval_metrics_20d.json, config.json)
    logs/experiment_v3b_history2017.log
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

# ── Setup paths ───────────────────────────────────────────────────────────────
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
        logging.FileHandler(LOG_DIR / "experiment_v3b_history2017.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BACKFILL_START_V3B = "2017-01-01"   # OHLCV start (cần 6 tháng buffer trước train start)
TRAIN_START_V3B    = "2017-07-01"   # buffer 6 tháng cho sharpe_12m, beta_12m
TRAIN_END_V3B      = "2024-06-30"   # giữ nguyên như v3a
VAL_START_V3B      = "2024-07-01"
VAL_END_V3B        = "2024-12-31"
TEST_START_V3B     = "2025-01-01"

FEATURES_DIR = ROOT / "data" / "features"
LABELS_DIR   = ROOT / "data" / "labels"
MODELS_DIR   = ROOT / "data" / "models"

# Thời gian mỗi bước (ước tính, để ETA)
STEP_ETA = {
    1: "30–60 phút (fetch OHLCV 2017–2021 cho 200+ symbols)",
    2: "60–120 phút (compute features ~1,200 ngày × 200 symbols)",
    3: "5–10 phút (rebuild labels + training set)",
    4: "3–5 phút (train LightGBM)",
    5: "< 1 phút (compare + save v3b)",
}


# ══════════════════════════════════════════════════════════════════════════════
# Step 1: OHLCV backfill
# ══════════════════════════════════════════════════════════════════════════════

def step1_ohlcv_backfill() -> None:
    log.info("=" * 60)
    log.info("STEP 1: OHLCV backfill từ %s  (ETA: %s)", BACKFILL_START_V3B, STEP_ETA[1])
    log.info("=" * 60)

    from pipeline.phase1a_ohlcv_store import run as phase1a_run

    # Backfill mode: fetch từ BACKFILL_START_V3B đến hiện tại
    # Các ngày 2022+ đã có → mode=auto sẽ chỉ fetch phần thiếu
    phase1a_run(
        mode="backfill",
        backfill_start=BACKFILL_START_V3B,
    )
    log.info("Step 1 DONE ✅")


# ══════════════════════════════════════════════════════════════════════════════
# Step 2: Build phase2 features cho ngày 2017-07-01 → 2021-12-31
# ══════════════════════════════════════════════════════════════════════════════

def step2_build_features() -> None:
    log.info("=" * 60)
    log.info("STEP 2: Build phase2 features cho 2017-07 → 2021-12  (ETA: %s)", STEP_ETA[2])
    log.info("=" * 60)

    import datetime as dt
    from pipeline.phase2_feature_pipeline import run as phase2_run

    start = dt.date(2017, 7, 1)
    end   = dt.date(2021, 12, 31)

    # Lấy danh sách ngày trading từ VNINDEX OHLCV
    import pandas as pd
    vnindex_path = ROOT / "data" / "ohlcv" / "VNINDEX.parquet"
    if vnindex_path.exists():
        vni = pd.read_parquet(vnindex_path, columns=["time"])
        vni["time"] = pd.to_datetime(vni["time"])
        trading_days = sorted(
            d.strftime("%Y-%m-%d")
            for d in vni["time"].dt.date
            if start <= d <= end
        )
    else:
        # Fallback: weekdays only
        trading_days = []
        d = start
        while d <= end:
            if d.weekday() < 5:
                trading_days.append(d.strftime("%Y-%m-%d"))
            d += dt.timedelta(days=1)

    # Lọc bỏ ngày đã có feature file
    missing_days = [
        ds for ds in trading_days
        if not (FEATURES_DIR / f"{ds}.parquet").exists()
    ]

    log.info(
        "Trading days 2017-07→2021-12: %d | Đã có: %d | Cần build: %d",
        len(trading_days), len(trading_days) - len(missing_days), len(missing_days)
    )

    if not missing_days:
        log.info("  Tất cả feature files đã có — skip step 2 ✅")
        return

    t_start = time.time()
    success, failed = 0, []

    for i, ds in enumerate(missing_days, 1):
        elapsed = time.time() - t_start
        eta_str = ""
        if i > 1:
            avg = elapsed / (i - 1)
            remaining = avg * (len(missing_days) - i + 1)
            eta_str = f"  ETA {remaining / 60:.0f}m"

        if i % 50 == 0 or i == 1:
            log.info("  [%d/%d] %s%s", i, len(missing_days), ds, eta_str)

        try:
            phase2_run(target_date=ds, save=True)
            success += 1
        except Exception as exc:
            log.warning("  FAIL %s: %s", ds, exc)
            failed.append(ds)

    log.info(
        "Step 2 DONE ✅ — %d OK / %d failed (%.0fs)",
        success, len(failed), time.time() - t_start
    )
    if failed:
        log.warning("  Failed dates: %s", failed[:10])


# ══════════════════════════════════════════════════════════════════════════════
# Step 3: Rebuild raw labels + training set
# ══════════════════════════════════════════════════════════════════════════════

def step3_rebuild_labels() -> None:
    log.info("=" * 60)
    log.info("STEP 3: Rebuild raw_labels_20d + training_set_20d  (ETA: %s)", STEP_ETA[3])
    log.info("=" * 60)

    from pipeline.phase3b_label_generator_20d import (
        compute_raw_labels_20d, build_training_set_20d
    )

    log.info("  3a. Computing raw labels 20d (toàn bộ lịch sử)...")
    raw = compute_raw_labels_20d(save=True)
    log.info("  raw labels: %d rows", len(raw))

    log.info("  3b. Building training set (features ⋈ labels)...")
    ts = build_training_set_20d(save=True)
    log.info("  training set: %d rows", len(ts))

    import pandas as pd
    ts_reset = ts.reset_index()
    date_col = "date" if "date" in ts_reset.columns else ts_reset.columns[1]
    ts_reset[date_col] = pd.to_datetime(ts_reset[date_col])
    log.info(
        "  Range: %s → %s | label=%.1f%%",
        ts_reset[date_col].min().date(),
        ts_reset[date_col].max().date(),
        ts["label"].mean() * 100,
    )
    log.info("Step 3 DONE ✅")


# ══════════════════════════════════════════════════════════════════════════════
# Step 4: Train LightGBM v3b
# ══════════════════════════════════════════════════════════════════════════════

def step4_train_v3b() -> dict:
    log.info("=" * 60)
    log.info("STEP 4: Train LightGBM v3b  (ETA: %s)", STEP_ETA[4])
    log.info("  TRAIN_START = %s  (v3a: 2022-07-01)", TRAIN_START_V3B)
    log.info("=" * 60)

    import pandas as pd

    # Patch TRAIN_START trong phase4b tạm thời
    import pipeline.phase4b_ml_model_20d as p4b
    _orig_train_start = p4b.TRAIN_START
    _orig_train_end   = p4b.TRAIN_END
    _orig_val_start   = p4b.VAL_START
    _orig_val_end     = p4b.VAL_END
    _orig_test_start  = p4b.TEST_START

    p4b.TRAIN_START = TRAIN_START_V3B
    p4b.TRAIN_END   = TRAIN_END_V3B
    p4b.VAL_START   = VAL_START_V3B
    p4b.VAL_END     = VAL_END_V3B
    p4b.TEST_START  = TEST_START_V3B

    try:
        df = p4b.prepare_dataset()
        log.info(
            "  Dataset: %d rows | label=%.1f%% | symbols=%d",
            len(df),
            df["label"].mean() * 100 if "label" in df.columns else 0,
            df.index.get_level_values("symbol").nunique() if "symbol" in df.index.names else 0,
        )

        # Log split sizes
        dates = df.index.get_level_values("date") if "date" in df.index.names \
                else pd.to_datetime(df["date"])
        n_train = ((dates >= TRAIN_START_V3B) & (dates <= TRAIN_END_V3B)).sum()
        n_val   = ((dates >= VAL_START_V3B)   & (dates <= VAL_END_V3B)).sum()
        n_test  = (dates >= TEST_START_V3B).sum()
        log.info("  Train: %d  Val: %d  Test: %d", n_train, n_val, n_test)

        model, feat_cols, metrics = p4b.train(df)

        # Save to v3b/
        v3b_dir = MODELS_DIR / "v3b"
        v3b_dir.mkdir(parents=True, exist_ok=True)

        pkl_path = v3b_dir / "lgbm_model_20d.pkl"
        with open(pkl_path, "wb") as f:
            pickle.dump({
                "model":          model,
                "feat_cols":      feat_cols,
                "horizon":        "20d",
                "ret_threshold":  0.05,
                "prob_cutoff":    0.50,
                "train_start":    TRAIN_START_V3B,
            }, f)
        log.info("  Model saved → %s", pkl_path)

        metrics_path = v3b_dir / "eval_metrics_20d.json"
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)

        return {"model": model, "feat_cols": feat_cols, "metrics": metrics}

    finally:
        # Restore original constants
        p4b.TRAIN_START = _orig_train_start
        p4b.TRAIN_END   = _orig_train_end
        p4b.VAL_START   = _orig_val_start
        p4b.VAL_END     = _orig_val_end
        p4b.TEST_START  = _orig_test_start


# ══════════════════════════════════════════════════════════════════════════════
# Step 5: Compare v3a vs v3b + register v3b
# ══════════════════════════════════════════════════════════════════════════════

def step5_compare_and_register(v3b_metrics: dict) -> None:
    log.info("=" * 60)
    log.info("STEP 5: Compare v3a vs v3b + register")
    log.info("=" * 60)

    from pipeline.model_registry import load_metrics, load_config, create_version, registry

    v3a_metrics = load_metrics("v3a")
    v3a_test_auc = v3a_metrics.get("test", {}).get("roc_auc", 0.0)
    v3a_val_auc  = v3a_metrics.get("val",  {}).get("roc_auc", 0.0)

    v3b_test_auc = v3b_metrics.get("test", {}).get("roc_auc", 0.0)
    v3b_val_auc  = v3b_metrics.get("val",  {}).get("roc_auc", 0.0)

    delta_test = v3b_test_auc - v3a_test_auc
    delta_val  = v3b_val_auc  - v3a_val_auc

    log.info("")
    log.info("  ┌─────────────────────────────────────────────────┐")
    log.info("  │           v3a (2022→)      v3b (2017→)  Δ      │")
    log.info("  ├─────────────────────────────────────────────────┤")
    log.info("  │  Test AUC:  %.4f           %.4f     %+.4f  │",
             v3a_test_auc, v3b_test_auc, delta_test)
    log.info("  │  Val  AUC:  %.4f           %.4f     %+.4f  │",
             v3a_val_auc,  v3b_val_auc,  delta_val)
    log.info("  └─────────────────────────────────────────────────┘")
    log.info("")

    if delta_test >= 0:
        verdict = "✅ v3b TỐT HƠN v3a — recommend shadow mode → promote"
    elif delta_test >= -0.005:
        verdict = "🟡 v3b TƯƠNG ĐƯƠNG — cần backtest thêm trên signal quality"
    else:
        verdict = "⚠️ v3b KÉM HƠN — cần điều chỉnh hyperparams hoặc feature set"
    log.info("  Kết luận: %s", verdict)

    # Register v3b config (inherit từ v3a, update training period)
    v3b_dir  = MODELS_DIR / "v3b"
    v3b_cfg_path = v3b_dir / "config.json"

    v3a_cfg = load_config("v3a")
    v3b_cfg = v3a_cfg.copy()
    v3b_cfg.update({
        "_version":      "v3b",
        "_description":  f"v3b — lịch sử 2017→ (train={TRAIN_START_V3B})",
        "_created":      datetime.now().strftime("%Y-%m-%d"),
        "_train_start":  TRAIN_START_V3B,
        "_train_end":    TRAIN_END_V3B,
        "_experiment":   "history2017",
        "_auc_delta_vs_v3a": round(delta_test, 4),
    })
    v3b_cfg_path.write_text(
        json.dumps(v3b_cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("  v3b config saved → %s", v3b_cfg_path)
    log.info("Step 5 DONE ✅")

    return {
        "v3a_test_auc": v3a_test_auc,
        "v3b_test_auc": v3b_test_auc,
        "delta_test":   delta_test,
        "verdict":      verdict,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Main orchestrator
# ══════════════════════════════════════════════════════════════════════════════

def main(start_step: int = 1, skip_ohlcv: bool = False) -> None:
    t_total = time.time()
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║   Experiment v3b — Hướng 1: Lịch sử 2017→           ║")
    log.info("╚══════════════════════════════════════════════════════╝")
    log.info("Start step: %d | Skip OHLCV: %s", start_step, skip_ohlcv)
    log.info("")

    if start_step <= 1 and not skip_ohlcv:
        step1_ohlcv_backfill()
    else:
        log.info("STEP 1: SKIPPED")

    if start_step <= 2:
        step2_build_features()
    else:
        log.info("STEP 2: SKIPPED")

    if start_step <= 3:
        step3_rebuild_labels()
    else:
        log.info("STEP 3: SKIPPED")

    if start_step <= 4:
        result4 = step4_train_v3b()
    else:
        log.info("STEP 4: SKIPPED — loading existing v3b metrics")
        import json as _json
        v3b_metrics_path = MODELS_DIR / "v3b" / "eval_metrics_20d.json"
        if v3b_metrics_path.exists():
            result4 = {"metrics": _json.loads(v3b_metrics_path.read_text())}
        else:
            log.error("No v3b metrics found. Run from step 4.")
            return

    comparison = step5_compare_and_register(result4["metrics"])

    elapsed = time.time() - t_total
    log.info("")
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  EXPERIMENT COMPLETE  (%.0f phút)                     ║", elapsed / 60)
    log.info("║  v3a AUC: %.4f  →  v3b AUC: %.4f  Δ=%+.4f   ║",
             comparison["v3a_test_auc"], comparison["v3b_test_auc"], comparison["delta_test"])
    log.info("║  %s", comparison["verdict"])
    log.info("╚══════════════════════════════════════════════════════╝")
    log.info("")
    log.info("Bước tiếp theo:")
    log.info("  1. Xem log đầy đủ: logs/experiment_v3b_history2017.log")
    log.info("  2. Bật shadow mode: discord → 🔧 Model Versions → 👁️ Shadow ON → v3b")
    log.info("  3. Sau 30 ngày so sánh win rate thực tế qua 📊 So sánh Versions")
    log.info("  4. Nếu tốt hơn: 🚀 Promote v3b → production")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Experiment v3b: History 2017→")
    parser.add_argument(
        "--step", type=int, default=1,
        help="Bắt đầu từ step N (1-5). Dùng khi step trước đã xong."
    )
    parser.add_argument(
        "--skip-ohlcv", action="store_true",
        help="Bỏ qua step 1 (OHLCV backfill). Dùng khi data đã có."
    )
    args = parser.parse_args()
    main(start_step=args.step, skip_ohlcv=args.skip_ohlcv)
