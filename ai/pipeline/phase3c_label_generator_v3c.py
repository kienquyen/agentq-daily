#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/phase3c_label_generator_v3c.py
Phase 3C — Hybrid Label Generator for v3c Experiment

Label definition (Hybrid):
    label = 1  if  forward_ret_20d >= +5%          (absolute floor, không lỗ tiền thật)
               AND (ret_20d - vnindex_ret_20d) >= +1%  (alpha: beat VNINDEX ít nhất 1%)
               AND rr >= 1.2                           (trade quality: ret / abs(max_dd))
               AND max_drawdown_20d >= -10%            (DD condition giữ nguyên từ v3a)

Rationale:
  - ret_20d >= 5% + max_dd >= -10%: giữ nguyên v3a condition
  - Alpha >= 1%: lọc "tất cả lên vì thị trường lên" → model học pure alpha
  - RR >= 1.2: lọc "spike rồi sập" → trade chất lượng

Saves to:
  data/labels/raw_labels_v3c.parquet
  data/labels/training_set_v3c.parquet
  data/labels/label_stats_v3c.json

Usage:
    python -m pipeline.phase3c_label_generator_v3c
    python -m pipeline.phase3c_label_generator_v3c --labels-only
    python -m pipeline.phase3c_label_generator_v3c --stats
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.phase3_label_generator import _load_all_feature_files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
OHLCV_DIR  = ROOT / "data" / "ohlcv"
LABELS_DIR = ROOT / "data" / "labels"

RAW_LABELS_V3C_PATH   = LABELS_DIR / "raw_labels_v3c.parquet"
TRAINING_SET_V3C_PATH = LABELS_DIR / "training_set_v3c.parquet"
STATS_V3C_PATH        = LABELS_DIR / "label_stats_v3c.json"

# ── Label config ──────────────────────────────────────────────────────────────
FORWARD_DAYS    = 20     # hold for 1 month (~20 trading days)
RET_THRESHOLD   = 0.05   # forward return >= +5%
DD_THRESHOLD    = -0.10  # max drawdown >= -10%
ALPHA_THRESHOLD = 0.01   # beat VNINDEX by >= +1%
RR_THRESHOLD    = 1.2    # ret / abs(max_dd) >= 1.2
RR_DD_FLOOR     = 0.005  # floor denominator tránh chia 0 (0.5% min)


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _load_vnindex() -> pd.Series:
    """Load VNINDEX close prices indexed by date (pd.Timestamp)."""
    path = OHLCV_DIR / "VNINDEX.parquet"
    if not path.exists():
        raise FileNotFoundError(f"VNINDEX.parquet not found at {path}")
    df = pd.read_parquet(path, columns=["time", "close"])
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").set_index("time")["close"]
    return df


def _compute_vnindex_forward_ret(vni_close: pd.Series, forward_days: int) -> pd.Series:
    """
    Compute VNINDEX forward return for every date.
    forward_ret[t] = (close[t+N] - close[t]) / close[t]
    Returns Series indexed by date.
    """
    close = vni_close.values.astype(float)
    dates = vni_close.index
    n = len(close)
    fwd = np.full(n, np.nan)

    for i in range(n - forward_days):
        c0 = close[i]
        if c0 > 0:
            fwd[i] = (close[i + forward_days] - c0) / c0

    return pd.Series(fwd, index=dates, name="vnindex_fwd_ret")


def _compute_symbol_labels_v3c(
    df: pd.DataFrame,
    vni_fwd: pd.Series,
    forward_days: int = FORWARD_DAYS,
    ret_threshold: float = RET_THRESHOLD,
    dd_threshold: float = DD_THRESHOLD,
    alpha_threshold: float = ALPHA_THRESHOLD,
    rr_threshold: float = RR_THRESHOLD,
    rr_dd_floor: float = RR_DD_FLOOR,
) -> pd.DataFrame:
    """
    Compute hybrid labels for one symbol.

    Columns returned (indexed by date):
        forward_ret_20d    — (close[t+20] - close[t]) / close[t]
        max_drawdown_20d   — (min(low[t+1:t+21]) - close[t]) / close[t]
        vnindex_ret_20d    — VNINDEX forward return same window
        alpha_20d          — forward_ret_20d - vnindex_ret_20d
        rr_20d             — forward_ret_20d / max(abs(max_drawdown_20d), floor)
        label              — 1 if ALL hybrid conditions met
        label_v3a          — 1 if original v3a conditions met (for comparison)
        label_valid        — 0 if future data unavailable
    """
    if df is None or df.empty:
        return pd.DataFrame()

    d = df.copy()
    d["time"] = pd.to_datetime(d["time"])
    d = d.sort_values("time").reset_index(drop=True)

    close  = d["close"].values.astype(float)
    low    = d["low"].values.astype(float) if "low" in d.columns else close.copy()
    dates  = pd.to_datetime(d["time"].values)
    n      = len(d)

    forward_ret   = np.full(n, np.nan)
    max_drawdown  = np.full(n, np.nan)
    vnindex_ret   = np.full(n, np.nan)
    alpha_arr     = np.full(n, np.nan)
    rr_arr        = np.full(n, np.nan)
    label         = np.full(n, np.nan)
    label_v3a     = np.full(n, np.nan)
    label_valid   = np.zeros(n, dtype=int)

    for i in range(n - forward_days):
        c0 = close[i]
        if c0 <= 0:
            continue
        c_end     = close[i + forward_days]
        lo_window = low[i + 1 : i + forward_days + 1]

        ret = (c_end - c0) / c0
        dd  = (lo_window.min() - c0) / c0

        # VNINDEX forward return for same date
        date_i   = dates[i]
        vni_val  = float(vni_fwd.get(date_i, np.nan))

        # Alpha
        alpha = ret - vni_val if not np.isnan(vni_val) else np.nan

        # Risk/Reward
        rr = ret / max(abs(dd), rr_dd_floor) if not np.isnan(dd) else np.nan

        forward_ret[i]  = ret
        max_drawdown[i] = dd
        vnindex_ret[i]  = vni_val
        alpha_arr[i]    = alpha
        rr_arr[i]       = rr
        label_valid[i]  = 1

        # v3a original label
        label_v3a[i] = int(ret >= ret_threshold and dd >= dd_threshold)

        # Hybrid label
        base_ok    = (ret >= ret_threshold) and (dd >= dd_threshold)
        alpha_ok   = (not np.isnan(alpha)) and (alpha >= alpha_threshold)
        rr_ok      = (not np.isnan(rr)) and (rr >= rr_threshold)
        label[i]   = int(base_ok and alpha_ok and rr_ok)

    return pd.DataFrame({
        "date":             dates,
        "forward_ret_20d":  forward_ret,
        "max_drawdown_20d": max_drawdown,
        "vnindex_ret_20d":  vnindex_ret,
        "alpha_20d":        alpha_arr,
        "rr_20d":           rr_arr,
        "label":            label,
        "label_v3a":        label_v3a,
        "label_valid":      label_valid,
    }).set_index("date")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 — RAW LABEL COMPUTATION
# ═════════════════════════════════════════════════════════════════════════════

def compute_raw_labels_v3c(
    symbols: Optional[List[str]] = None,
    save: bool = True,
) -> pd.DataFrame:
    """
    Compute hybrid v3c labels for all symbols.
    Saves to data/labels/raw_labels_v3c.parquet.
    """
    LABELS_DIR.mkdir(parents=True, exist_ok=True)

    # Load VNINDEX
    logger.info("Loading VNINDEX for alpha computation...")
    vni_close = _load_vnindex()
    vni_fwd   = _compute_vnindex_forward_ret(vni_close, FORWARD_DAYS)
    logger.info("  VNINDEX: %d trading days  (%s → %s)",
                len(vni_close),
                str(vni_close.index.min().date()),
                str(vni_close.index.max().date()))

    # Resolve symbols
    manifest_path = OHLCV_DIR / "_manifest.json"
    if symbols is None:
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            symbols = [s for s in manifest if s != "VNINDEX"]
        else:
            symbols = [p.stem for p in OHLCV_DIR.glob("*.parquet")
                       if p.stem not in ("_manifest", "VNINDEX")]

    symbols = [s.upper() for s in symbols]
    logger.info(
        "Step 1 v3c: Hybrid labels for %d symbols  "
        "(ret>=%.0f%%  dd>=%.0f%%  alpha>=%.0f%%  RR>=%.1f)",
        len(symbols),
        RET_THRESHOLD * 100, abs(DD_THRESHOLD) * 100,
        ALPHA_THRESHOLD * 100, RR_THRESHOLD,
    )

    all_frames = []
    missing, skipped = [], []

    for sym in symbols:
        path = OHLCV_DIR / f"{sym}.parquet"
        if not path.exists():
            missing.append(sym)
            continue
        try:
            df  = pd.read_parquet(path)
            lbl = _compute_symbol_labels_v3c(df, vni_fwd)
            if lbl.empty:
                skipped.append(sym)
                continue
            lbl.index = pd.MultiIndex.from_tuples(
                [(sym, d) for d in lbl.index], names=["symbol", "date"]
            )
            all_frames.append(lbl)
        except Exception as e:
            logger.warning("  %s: error — %s", sym, e)
            skipped.append(sym)

    if not all_frames:
        logger.error("No labels computed.")
        return pd.DataFrame()

    result = pd.concat(all_frames)
    valid  = result[result["label_valid"] == 1]

    pos_hybrid = valid["label"].mean() if len(valid) > 0 else 0
    pos_v3a    = valid["label_v3a"].mean() if len(valid) > 0 else 0

    logger.info("  Raw labels: %d total | %d labelable", len(result), len(valid))
    logger.info("  v3a  positive rate: %.1f%%", pos_v3a * 100)
    logger.info("  v3c  positive rate: %.1f%%  (%.1f%% of v3a signals kept)",
                pos_hybrid * 100,
                (pos_hybrid / max(pos_v3a, 1e-9)) * 100)

    if missing:
        logger.warning("Missing OHLCV: %d symbols", len(missing))
    if skipped:
        logger.warning("Skipped: %d symbols", len(skipped))

    if save:
        result.to_parquet(RAW_LABELS_V3C_PATH, engine="pyarrow")
        logger.info("  Saved → %s", RAW_LABELS_V3C_PATH)

    return result


# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 — JOIN FEATURES + LABELS → TRAINING SET
# ═════════════════════════════════════════════════════════════════════════════

def build_training_set_v3c(
    symbols: Optional[List[str]] = None,
    save: bool = True,
) -> pd.DataFrame:
    """
    Join Phase-2 features with v3c hybrid labels.
    Uses the same feature files as v3a/v3b (features don't change).
    Saves to data/labels/training_set_v3c.parquet.
    """
    if not RAW_LABELS_V3C_PATH.exists():
        logger.info("raw_labels_v3c.parquet not found — computing now...")
        raw = compute_raw_labels_v3c(symbols=symbols, save=True)
    else:
        raw = pd.read_parquet(RAW_LABELS_V3C_PATH)
        logger.info("Loaded v3c raw labels: %d rows", len(raw))

    if raw.empty:
        return pd.DataFrame()

    features = _load_all_feature_files(symbols=symbols)
    if features.empty:
        logger.warning("No features found.")
        return raw

    # Align MultiIndex (symbol, date)
    raw.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in raw.index], names=["symbol", "date"]
    )
    features.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in features.index], names=["symbol", "date"]
    )

    feat_cols = [c for c in features.columns if c != "date"]
    merged    = features[feat_cols].join(raw, how="inner")

    # ── Drop forward-looking label columns to prevent data leakage ────────────
    # These are derived from future prices → must NOT be used as features.
    # Keep only: label, label_v3a (for comparison), label_valid
    LEAKY_COLS = [
        "forward_ret_20d",   # future return
        "max_drawdown_20d",  # future drawdown
        "vnindex_ret_20d",   # future VNINDEX return
        "alpha_20d",         # = forward_ret_20d - vnindex_ret_20d
        "rr_20d",            # = forward_ret_20d / abs(max_drawdown_20d)
        "label_v3a",         # encodes forward_ret>=5% — direct leakage for v3c label
        "forward_ret_10d",   # 5d model column if present
        "max_drawdown_10d",  # 5d model column if present
    ]
    leaky_present = [c for c in LEAKY_COLS if c in merged.columns]
    if leaky_present:
        merged = merged.drop(columns=leaky_present)
        logger.info("  Dropped %d leaky forward-looking cols: %s",
                    len(leaky_present), leaky_present)
    logger.info("After join: %d rows (feature × label overlap)", len(merged))

    if merged.empty:
        logger.warning("Join produced 0 rows.")
        return merged

    valid_rows = merged[merged["label_valid"] == 1]
    total_valid = len(valid_rows)

    if total_valid > 0:
        pos_rate   = valid_rows["label"].mean()
        pos_v3a    = valid_rows["label_v3a"].mean() if "label_v3a" in valid_rows.columns else float("nan")
        n_pos      = int(valid_rows["label"].sum())
        n_neg      = total_valid - n_pos

        logger.info("=" * 60)
        logger.info("v3c Hybrid Training set summary:")
        logger.info("  Total rows:                %6d", len(merged))
        logger.info("  Label-valid rows:          %6d", total_valid)
        logger.info("  v3a positive rate:         %.1f%%", pos_v3a * 100)
        logger.info("  v3c positive (label=1):    %6d  (%.1f%%)", n_pos, pos_rate * 100)
        logger.info("  v3c negative (label=0):    %6d  (%.1f%%)", n_neg, (1 - pos_rate) * 100)
        logger.info("  scale_pos_weight for LGBM: %.2f", n_neg / max(n_pos, 1))
        logger.info("  Label conditions:")
        logger.info("    ret_20d >= +5%%")
        logger.info("    max_dd  >= -10%%")
        logger.info("    alpha   >= +1%%  (beat VNINDEX)")
        logger.info("    RR      >= 1.2  (ret / abs(max_dd))")
        logger.info("  Date range: %s → %s",
                    merged.index.get_level_values("date").min().date(),
                    merged.index.get_level_values("date").max().date())
        logger.info("=" * 60)

        stats = {
            "generated_at":     datetime.utcnow().isoformat(timespec="seconds"),
            "label_version":    "v3c_hybrid",
            "total_rows":       len(merged),
            "label_valid_rows": total_valid,
            "positive_count":   n_pos,
            "negative_count":   n_neg,
            "positive_rate":    round(float(pos_rate), 4),
            "positive_rate_v3a": round(float(pos_v3a), 4) if not np.isnan(pos_v3a) else None,
            "scale_pos_weight": round(n_neg / max(n_pos, 1), 2),
            "forward_days":     FORWARD_DAYS,
            "ret_threshold":    RET_THRESHOLD,
            "dd_threshold":     DD_THRESHOLD,
            "alpha_threshold":  ALPHA_THRESHOLD,
            "rr_threshold":     RR_THRESHOLD,
            "date_min":         str(merged.index.get_level_values("date").min().date()),
            "date_max":         str(merged.index.get_level_values("date").max().date()),
        }
        LABELS_DIR.mkdir(parents=True, exist_ok=True)
        STATS_V3C_PATH.write_text(json.dumps(stats, indent=2, ensure_ascii=False))
        logger.info("Stats saved → %s", STATS_V3C_PATH)

    if save:
        LABELS_DIR.mkdir(parents=True, exist_ok=True)
        merged.to_parquet(TRAINING_SET_V3C_PATH, engine="pyarrow")
        logger.info("Training set saved → %s", TRAINING_SET_V3C_PATH)

    return merged


# ═════════════════════════════════════════════════════════════════════════════
# FULL PIPELINE
# ═════════════════════════════════════════════════════════════════════════════

def run_v3c_labels(save: bool = True) -> pd.DataFrame:
    """Full pipeline: compute raw labels → build training set."""
    raw = compute_raw_labels_v3c(save=save)
    if raw.empty:
        return pd.DataFrame()
    return build_training_set_v3c(save=save)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="v3c Hybrid Label Generator")
    parser.add_argument("--labels-only", action="store_true",
                        help="Only compute raw labels (Step 1)")
    parser.add_argument("--training-set", action="store_true",
                        help="Only build training set (Step 2, needs raw labels)")
    parser.add_argument("--stats", action="store_true",
                        help="Print existing stats file")
    args = parser.parse_args()

    if args.stats:
        if STATS_V3C_PATH.exists():
            print(STATS_V3C_PATH.read_text())
        else:
            print("No stats file found. Run without --stats to generate.")
    elif args.labels_only:
        compute_raw_labels_v3c(save=True)
    elif args.training_set:
        build_training_set_v3c(save=True)
    else:
        run_v3c_labels(save=True)
