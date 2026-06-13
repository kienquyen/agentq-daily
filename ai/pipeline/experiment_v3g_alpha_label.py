"""
Experiment v3g — Alpha-Based Label

New label definition (replaces absolute return threshold):
    label = 1  if  alpha_20d > +2%   (outperform VNINDEX by 2%)
               AND return_20d > 0%   (absolute positive return)
    label = 0  otherwise

Rationale:
    Current label (ret >= 5%) is biased toward bull markets.
    In deep_bear, a stock returning +1% vs VNINDEX -6% is excellent (alpha=+7%).
    Alpha-based label is regime-neutral: rewards genuine stock-picking skill.

Pipeline:
    Step 1 — Compute alpha labels (saves to raw_labels_20d_alpha.parquet)  (~10 phút)
    Step 2 — Build training set with alpha labels  (~5 phút)
    Step 3 — Train LightGBM v3g  (~3-5 phút)
    Step 4 — Compare v3a / v3b / v3g

Chạy:
    python -m pipeline.experiment_v3g_alpha_label
    python -m pipeline.experiment_v3g_alpha_label --step 3   # skip to train only
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
        logging.FileHandler(LOG_DIR / "experiment_v3g_alpha_label.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

OHLCV_DIR  = ROOT / "data" / "ohlcv"
LABELS_DIR = ROOT / "data" / "labels"
MODELS_DIR = ROOT / "data" / "models"

# Separate paths — không overwrite labels hiện tại
RAW_LABELS_ALPHA_PATH      = LABELS_DIR / "raw_labels_20d_alpha.parquet"
TRAINING_SET_ALPHA_PATH    = LABELS_DIR / "training_set_20d_alpha.parquet"

# Label config
FORWARD_DAYS    = 20
ALPHA_THRESHOLD = 0.02    # outperform VNINDEX by >= +2%
RET_MIN         = 0.0     # absolute return must be > 0%


# ══════════════════════════════════════════════════════════════════════════════
# Step 1: Compute alpha labels
# ══════════════════════════════════════════════════════════════════════════════

def _load_vnindex_returns(forward_days: int = FORWARD_DAYS) -> pd.Series:
    """
    Compute VNINDEX forward return for each trading day.
    Returns: Series indexed by date (Timestamp), value = vnindex_ret_20d.
    """
    vni_path = OHLCV_DIR / "VNINDEX.parquet"
    df = pd.read_parquet(vni_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").set_index("time")["close"].astype(float)

    fwd_ret = {}
    closes = df.values
    dates  = df.index
    n = len(closes)
    for i in range(n - forward_days):
        ret = (closes[i + forward_days] - closes[i]) / closes[i]
        fwd_ret[dates[i]] = float(ret)

    return pd.Series(fwd_ret, name="vnindex_ret_20d")


def compute_alpha_labels(
    symbols: Optional[List[str]] = None,
    save: bool = True,
) -> pd.DataFrame:
    """
    Compute 20-day alpha labels for all symbols.
    label = 1 if alpha_20d > ALPHA_THRESHOLD AND return_20d > RET_MIN
    """
    LABELS_DIR.mkdir(parents=True, exist_ok=True)

    manifest_path = OHLCV_DIR / "_manifest.json"
    if symbols is None:
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            symbols = [s for s in manifest if s != "VNINDEX"]
        else:
            symbols = [p.stem for p in OHLCV_DIR.glob("*.parquet")
                       if p.stem not in ("_manifest", "VNINDEX")]

    symbols = [s.upper() for s in symbols]
    log.info("Computing alpha labels for %d symbols  (hold=%dd, alpha>%.0f%%, ret>%.0f%%)",
             len(symbols), FORWARD_DAYS, ALPHA_THRESHOLD * 100, RET_MIN * 100)

    # Load VNINDEX forward returns once
    log.info("  Loading VNINDEX forward returns...")
    vni_fwd = _load_vnindex_returns(FORWARD_DAYS)
    log.info("  VNINDEX fwd returns: %d days (%s → %s)",
             len(vni_fwd), vni_fwd.index.min().date(), vni_fwd.index.max().date())

    all_frames = []
    missing, skipped = [], []

    for sym in symbols:
        path = OHLCV_DIR / f"{sym}.parquet"
        if not path.exists():
            missing.append(sym)
            continue
        try:
            df = pd.read_parquet(path)
            df["time"] = pd.to_datetime(df["time"])
            df = df.sort_values("time").reset_index(drop=True)
            closes = df["close"].astype(float).values
            dates  = df["time"].values
            n = len(closes)

            rows = []
            for i in range(n - FORWARD_DAYS):
                d   = pd.Timestamp(dates[i])
                ret = (closes[i + FORWARD_DAYS] - closes[i]) / closes[i]
                dd  = float(
                    (df["low"].iloc[i+1:i+FORWARD_DAYS+1].min() - closes[i]) / closes[i]
                ) if "low" in df.columns else float("nan")

                vni_ret = vni_fwd.get(d, float("nan"))
                alpha   = ret - vni_ret if not np.isnan(vni_ret) else float("nan")

                label_valid = int(not np.isnan(alpha))
                label = int(
                    label_valid
                    and alpha > ALPHA_THRESHOLD
                    and ret > RET_MIN
                )

                rows.append({
                    "date":             d,
                    "forward_ret_10d":  ret,    # keep same col name for compatibility
                    "max_drawdown_10d": dd,
                    "vnindex_ret_20d":  vni_ret,
                    "alpha_20d":        alpha,
                    "label":            label if label_valid else float("nan"),
                    "label_valid":      label_valid,
                })

            lbl = pd.DataFrame(rows).set_index("date")
            if lbl.empty:
                skipped.append(sym)
                continue
            lbl.index = pd.MultiIndex.from_tuples(
                [(sym, d) for d in lbl.index], names=["symbol", "date"]
            )
            all_frames.append(lbl)
        except Exception as e:
            log.warning("  %s: error — %s", sym, e)
            skipped.append(sym)

    if not all_frames:
        log.error("No labels computed.")
        return pd.DataFrame()

    result = pd.concat(all_frames)
    valid = result[result["label_valid"] == 1]
    pos_rate = valid["label"].mean() if len(valid) > 0 else 0

    log.info("  Raw labels: %d total | %d labelable | positive rate = %.1f%%",
             len(result), len(valid), pos_rate * 100)

    # Stats by regime would be nice but skip for now
    if missing:
        log.warning("  Missing OHLCV: %d symbols", len(missing))
    if skipped:
        log.warning("  Skipped: %d symbols", len(skipped))

    if save:
        result.to_parquet(RAW_LABELS_ALPHA_PATH, engine="pyarrow")
        log.info("  Saved → %s", RAW_LABELS_ALPHA_PATH)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Step 2: Build training set
# ══════════════════════════════════════════════════════════════════════════════

def build_training_set_alpha(save: bool = True) -> pd.DataFrame:
    """
    Fast approach: reuse existing training_set_20d.parquet (features already joined),
    just replace the label column with alpha-based labels.
    Avoids reloading 2274 feature files (~38 minutes).
    """
    existing_ts_path = LABELS_DIR / "training_set_20d.parquet"
    if not existing_ts_path.exists():
        raise FileNotFoundError(f"training_set_20d.parquet not found — run phase3b first")

    if not RAW_LABELS_ALPHA_PATH.exists():
        log.info("Alpha labels not found — computing now...")
        compute_alpha_labels(save=True)

    log.info("Loading existing training set (features already joined)...")
    ts = pd.read_parquet(existing_ts_path)
    log.info("  Loaded: %d rows", len(ts))

    log.info("Loading alpha labels...")
    alpha = pd.read_parquet(RAW_LABELS_ALPHA_PATH)

    # Normalize index to (symbol, Timestamp)
    ts.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in ts.index], names=["symbol", "date"]
    )
    alpha.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in alpha.index], names=["symbol", "date"]
    )

    # Join alpha labels onto existing feature set
    alpha_sub = alpha[["alpha_20d", "vnindex_ret_20d", "label", "label_valid"]].rename(
        columns={"label": "label_alpha", "label_valid": "label_valid_alpha"}
    )
    merged = ts.join(alpha_sub, how="inner")
    log.info("After join: %d rows", len(merged))

    # Replace label with alpha label
    merged = merged[merged["label_valid_alpha"] == 1].copy()
    merged["label_orig"] = merged["label"]          # keep original label for reference
    merged["label"]      = merged["label_alpha"]    # use alpha label for training
    merged = merged.drop(columns=["label_alpha"])

    log.info("Label-valid rows: %d", len(merged))
    log.info("  Alpha label positive rate: %.1f%%", merged["label"].mean() * 100)
    log.info("  Original label positive rate: %.1f%%", merged["label_orig"].mean() * 100)

    if save:
        merged.to_parquet(TRAINING_SET_ALPHA_PATH, engine="pyarrow")
        log.info("  Saved → %s", TRAINING_SET_ALPHA_PATH)

    return merged


# ══════════════════════════════════════════════════════════════════════════════
# Step 3: Train v3g
# ══════════════════════════════════════════════════════════════════════════════

def step3_train_v3g() -> dict:
    log.info("=" * 60)
    log.info("STEP 3: Train LightGBM v3g  (~3-5 phút)")
    log.info("  Label: alpha_20d > +2%% AND ret_20d > 0%%")
    log.info("=" * 60)

    import pandas as pd
    import pipeline.phase4b_ml_model_20d as p4b

    # Override prepare_dataset to use alpha training set
    df = pd.read_parquet(TRAINING_SET_ALPHA_PATH)
    log.info("  Dataset: %d rows | label=%.1f%%",
             len(df), df["label"].mean() * 100)

    # Drop forward-looking columns before training (prevent data leakage)
    leakage_cols = ["vnindex_ret_20d", "alpha_20d", "label_orig",
                    "label_valid_alpha", "forward_ret_10d", "max_drawdown_10d"]
    df = df.drop(columns=[c for c in leakage_cols if c in df.columns])
    log.info("  Dropped leakage cols: %s", [c for c in leakage_cols if c in df.columns or True])

    model, feat_cols, metrics = p4b.train(df)

    v3g_dir = MODELS_DIR / "v3g"
    v3g_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = v3g_dir / "lgbm_model_20d.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump({
            "model":         model,
            "feat_cols":     feat_cols,
            "horizon":       "20d",
            "ret_threshold": 0.0,    # alpha-based, not absolute
            "prob_cutoff":   0.50,
            "experiment":    "alpha_label_v3g",
            "label_def":     "alpha_20d > 2% AND ret_20d > 0%",
        }, f)

    metrics_path = v3g_dir / "eval_metrics_20d.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    fi = pd.DataFrame({
        "feature":    feat_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    fi.to_csv(v3g_dir / "feature_importance_20d.csv", index=False)

    log.info("  v3g saved → %s", v3g_dir)
    log.info("Step 3 DONE ✅")
    return {"model": model, "feat_cols": feat_cols, "metrics": metrics, "fi": fi}


# ══════════════════════════════════════════════════════════════════════════════
# Step 4: Compare v3a / v3b / v3g
# ══════════════════════════════════════════════════════════════════════════════

def step4_compare(v3g_result: dict) -> dict:
    log.info("=" * 60)
    log.info("STEP 4: Compare v3a / v3b / v3g")
    log.info("=" * 60)

    import pandas as pd
    from pipeline.model_registry import load_metrics

    v3a_m = load_metrics("v3a")
    v3b_m = load_metrics("v3b")
    v3g_m = v3g_result["metrics"]

    v3a_test = v3a_m.get("test", {}).get("roc_auc", 0.0)
    v3b_test = v3b_m.get("test", {}).get("roc_auc", 0.0)
    v3g_test = v3g_m.get("test", {}).get("roc_auc", 0.0)
    v3g_val  = v3g_m.get("val",  {}).get("roc_auc", 0.0)

    log.info("")
    log.info("  ┌──────────────────────────────────────────────────────────────────┐")
    log.info("  │          v3a (ret≥5%)    v3b (ret≥5%)    v3g (alpha>2%+ret>0%)  │")
    log.info("  ├──────────────────────────────────────────────────────────────────┤")
    log.info("  │  Test AUC:  %.4f         %.4f          %.4f                │",
             v3a_test, v3b_test, v3g_test)
    log.info("  │  Val  AUC:  —             —              %.4f                │",
             v3g_val)
    log.info("  └──────────────────────────────────────────────────────────────────┘")

    # Note: AUC comparison across different labels is NOT apples-to-apples.
    # v3g's AUC is on alpha label; v3a/v3b's AUC is on ret>=5% label.
    log.info("")
    log.info("  ⚠️  NOTE: AUC values are NOT directly comparable across label definitions!")
    log.info("     v3a/v3b AUC = ability to predict ret>=5%")
    log.info("     v3g AUC     = ability to predict alpha>2% AND ret>0%")
    log.info("     Use backtest_compare for fair comparison.")

    fi = v3g_result["fi"]
    log.info("")
    log.info("  Top 15 features v3g:")
    for _, row in fi.head(15).iterrows():
        log.info("    %-30s = %d", row["feature"], int(row["importance"]))

    # Label stats comparison
    alpha_df = pd.read_parquet(RAW_LABELS_ALPHA_PATH)
    alpha_valid = alpha_df[alpha_df["label_valid"] == 1]
    alpha_pos_rate = alpha_valid["label"].mean()
    log.info("")
    log.info("  Label positive rates:")
    log.info("    v3a/v3b (ret>=5%% AND dd>=-10%%): ~27%%")
    log.info("    v3g     (alpha>+2%% AND ret>0%%):  %.1f%%", alpha_pos_rate * 100)

    # Save config
    v3g_dir = MODELS_DIR / "v3g"
    cfg = {
        "_version":      "v3g",
        "_description":  "v3g — alpha-based label: outperform VNINDEX by 2% AND ret > 0%",
        "_created":      datetime.now().strftime("%Y-%m-%d"),
        "_experiment":   "alpha_label_v3g",
        "_label_def":    f"alpha_20d > {ALPHA_THRESHOLD:.0%} AND return_20d > {RET_MIN:.0%}",
        "_auc_v3g_test": round(v3g_test, 4),
        "_auc_v3g_val":  round(v3g_val, 4),
        "prob_cutoff_default": 0.55,
    }
    (v3g_dir / "config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {"v3g_test": v3g_test, "v3g_val": v3g_val, "alpha_pos_rate": alpha_pos_rate}


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main(start_step: int = 1) -> None:
    t_total = time.time()
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  Experiment v3g — Alpha-Based Label                  ║")
    log.info("║  label = alpha_20d > +2%% AND return_20d > 0%%      ║")
    log.info("╚══════════════════════════════════════════════════════╝")

    if start_step <= 1:
        log.info("STEP 1: Compute alpha labels  (~10 phút)")
        t = time.time()
        raw = compute_alpha_labels(save=True)
        log.info("Step 1 DONE ✅ — %d rows (%.0fs)", len(raw), time.time() - t)
    else:
        log.info("STEP 1: SKIPPED")

    if start_step <= 2:
        log.info("STEP 2: Build training set  (~5 phút)")
        t = time.time()
        ts = build_training_set_alpha(save=True)
        log.info("Step 2 DONE ✅ — %d rows (%.0fs)", len(ts), time.time() - t)
    else:
        log.info("STEP 2: SKIPPED")

    if start_step <= 3:
        result3 = step3_train_v3g()
    else:
        log.info("STEP 3: SKIPPED — loading existing v3g")
        v3g_dir = MODELS_DIR / "v3g"
        with open(v3g_dir / "lgbm_model_20d.pkl", "rb") as f:
            payload = pickle.load(f)
        with open(v3g_dir / "eval_metrics_20d.json") as f:
            metrics = json.load(f)
        fi = pd.read_csv(v3g_dir / "feature_importance_20d.csv")
        result3 = {"model": payload["model"], "feat_cols": payload["feat_cols"],
                   "metrics": metrics, "fi": fi}

    comparison = step4_compare(result3)

    elapsed = time.time() - t_total
    log.info("")
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  EXPERIMENT v3g COMPLETE  (%.0f phút)               ║", elapsed / 60)
    log.info("║  v3g AUC (alpha label): %.4f                         ║", comparison["v3g_test"])
    log.info("║  Alpha positive rate: %.1f%%                          ║", comparison["alpha_pos_rate"] * 100)
    log.info("╚══════════════════════════════════════════════════════╝")
    log.info("")
    log.info("Bước tiếp theo:")
    log.info("  python -m pipeline.backtest_compare  # so sánh WR thực tế v3a vs v3b vs v3g")
    log.info("  (backtest sẽ dùng forward_ret_10d để đánh giá actual performance)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, default=1)
    args = parser.parse_args()
    main(start_step=args.step)
