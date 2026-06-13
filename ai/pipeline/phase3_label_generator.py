#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/phase3_label_generator.py
Phase 3 — Label Generation for Propensity-to-Buy Model

Label definition:
    label = 1  if  forward_ret_10d > +5%  AND  max_drawdown_10d > -7%
    label = 0  otherwise

Two-step process:
  Step 1: compute_raw_labels()
      Input:  data/ohlcv/{SYMBOL}.parquet
      Output: data/labels/raw_labels.parquet
              [symbol, date, forward_ret_10d, max_drawdown_10d, label]

  Step 2: build_training_set()
      Input:  data/labels/raw_labels.parquet
              data/features/{DATE}.parquet  (from Phase 2)
      Output: data/labels/training_set.parquet
              [symbol, date, <74 features>, label, forward_ret_10d, max_drawdown_10d]

Usage:
    python -m pipeline.phase3_label_generator                  # full pipeline
    python -m pipeline.phase3_label_generator --labels-only    # Step 1 only
    python -m pipeline.phase3_label_generator --join-only      # Step 2 only
    python -m pipeline.phase3_label_generator --stats          # class balance report
    python -m pipeline.phase3_label_generator --check          # file summary
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ─── Path setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _log in ("vnstock", "vnai", "urllib3"):
    logging.getLogger(_log).setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Paths ───────────────────────────────────────────────────────────────────
OHLCV_DIR    = ROOT / "data" / "ohlcv"
FEATURES_DIR = ROOT / "data" / "features"
LABELS_DIR   = ROOT / "data" / "labels"

RAW_LABELS_PATH  = LABELS_DIR / "raw_labels.parquet"
TRAINING_SET_PATH = LABELS_DIR / "training_set.parquet"
STATS_PATH       = LABELS_DIR / "label_stats.json"

# ─── Label config ─────────────────────────────────────────────────────────────
FORWARD_DAYS   = 5      # look-ahead window (trading days)
RET_THRESHOLD  = 0.03   # forward return > 3%
DD_THRESHOLD   = -0.07  # max drawdown within window > -7% (i.e. < 7% loss)


# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 — RAW LABEL COMPUTATION
# ═════════════════════════════════════════════════════════════════════════════


def _compute_symbol_labels(
    df: pd.DataFrame,
    forward_days: int = FORWARD_DAYS,
    ret_threshold: float = RET_THRESHOLD,
    dd_threshold: float = DD_THRESHOLD,
) -> pd.DataFrame:
    """
    Compute forward return and max drawdown for every row in df.

    Returns DataFrame indexed by date with columns:
        forward_ret_10d   — (close[t+N] - close[t]) / close[t]
        max_drawdown_10d  — (min(low[t+1:t+N+1]) - close[t]) / close[t]
        label             — 1 if ret > threshold AND drawdown > dd_threshold
        label_valid       — 0 if future data unavailable (last N rows)
    """
    if df is None or df.empty:
        return pd.DataFrame()

    d = df.copy()
    d["time"] = pd.to_datetime(d["time"])
    d = d.sort_values("time").reset_index(drop=True)

    close  = d["close"].values.astype(float)
    low    = d["low"].values.astype(float) if "low" in d.columns else close.copy()
    dates  = d["time"].values
    n      = len(d)

    forward_ret  = np.full(n, np.nan)
    max_drawdown = np.full(n, np.nan)
    label        = np.full(n, np.nan)
    label_valid  = np.zeros(n, dtype=int)

    for i in range(n - forward_days):
        c0    = close[i]
        if c0 <= 0:
            continue
        c_end = close[i + forward_days]
        lo_window = low[i + 1 : i + forward_days + 1]

        ret = (c_end - c0) / c0
        dd  = (lo_window.min() - c0) / c0

        forward_ret[i]  = ret
        max_drawdown[i] = dd
        label[i]        = int(ret > ret_threshold and dd > dd_threshold)
        label_valid[i]  = 1

    result = pd.DataFrame({
        "date":             pd.to_datetime(dates),
        "forward_ret_10d":  forward_ret,
        "max_drawdown_10d": max_drawdown,
        "label":            label,
        "label_valid":      label_valid,
    }).set_index("date")

    return result


def compute_raw_labels(
    symbols: Optional[List[str]] = None,
    forward_days: int = FORWARD_DAYS,
    ret_threshold: float = RET_THRESHOLD,
    dd_threshold: float = DD_THRESHOLD,
    save: bool = True,
) -> pd.DataFrame:
    """
    Step 1: Compute raw labels for all symbols from OHLCV parquet files.

    Returns long-format DataFrame with MultiIndex (symbol, date).
    """
    LABELS_DIR.mkdir(parents=True, exist_ok=True)

    # Resolve symbol list
    if symbols is None:
        manifest_path = OHLCV_DIR / "_manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            symbols = [s for s in manifest if s != "VNINDEX"]
        else:
            symbols = [p.stem for p in OHLCV_DIR.glob("*.parquet")
                       if p.stem not in ("_manifest", "VNINDEX")]

    symbols = [s.upper() for s in symbols]
    logger.info("Step 1: Computing raw labels for %d symbols  (forward=%dd, ret>%.0f%%, dd>%.0f%%)",
                len(symbols), forward_days, ret_threshold * 100, dd_threshold * 100)

    all_frames: List[pd.DataFrame] = []
    missing, skipped = [], []

    for sym in symbols:
        path = OHLCV_DIR / f"{sym}.parquet"
        if not path.exists():
            missing.append(sym)
            continue

        try:
            df = pd.read_parquet(path)
            lbl = _compute_symbol_labels(df, forward_days, ret_threshold, dd_threshold)
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
        logger.error("No labels computed — check OHLCV store (Phase 1A).")
        return pd.DataFrame()

    result = pd.concat(all_frames)

    if missing:
        logger.warning("Missing OHLCV for %d symbols: %s", len(missing), missing[:10])
    if skipped:
        logger.warning("Skipped (error/empty): %d symbols", len(skipped))

    # Summary stats
    valid = result[result["label_valid"] == 1]
    total_valid = len(valid)
    positive_rate = valid["label"].mean() if total_valid > 0 else 0
    logger.info(
        "  Raw labels: %d total rows | %d labelable | positive rate = %.1f%%",
        len(result), total_valid, positive_rate * 100,
    )

    if save:
        result.to_parquet(RAW_LABELS_PATH, engine="pyarrow")
        logger.info("  Saved → %s", RAW_LABELS_PATH)

    return result


# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 — JOIN FEATURES + LABELS → TRAINING SET
# ═════════════════════════════════════════════════════════════════════════════


def _load_all_feature_files(
    symbols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Load all Phase 2 feature parquet files into a single DataFrame.
    Returns MultiIndex (symbol, date) DataFrame.
    """
    feature_files = sorted(FEATURES_DIR.glob("*.parquet"))
    if not feature_files:
        logger.error("No feature files found in %s — run Phase 2 first.", FEATURES_DIR)
        return pd.DataFrame()

    logger.info("Loading %d feature files from %s ...", len(feature_files), FEATURES_DIR)
    frames: List[pd.DataFrame] = []

    for fp in feature_files:
        try:
            df = pd.read_parquet(fp)
            # df has index=symbol, column 'date' is the trading date
            if "date" not in df.columns:
                continue

            df = df.reset_index()  # symbol → column
            df = df.rename(columns={"index": "symbol"}) if "index" in df.columns else df

            # Ensure 'symbol' column exists
            if "symbol" not in df.columns:
                continue

            df["date"] = pd.to_datetime(df["date"])

            if symbols:
                df = df[df["symbol"].isin([s.upper() for s in symbols])]

            if not df.empty:
                frames.append(df)
        except Exception as e:
            logger.warning("  Failed to load %s: %s", fp.name, e)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.set_index(["symbol", "date"])
    combined = combined[~combined.index.duplicated(keep="last")]
    logger.info("  Features: %d rows × %d cols", len(combined), len(combined.columns))
    return combined


def build_training_set(
    symbols: Optional[List[str]] = None,
    hardcheck_only: bool = False,
    save: bool = True,
) -> pd.DataFrame:
    """
    Step 2: Join Phase 2 features with raw labels.

    Args:
        symbols:        restrict to subset; None = all
        hardcheck_only: if True, drop rows where hardcheck_pass == 0
        save:           save to data/labels/training_set.parquet

    Returns:
        MultiIndex (symbol, date) DataFrame with features + label columns.
        Rows where label_valid=0 (future data unavailable) are kept but
        label=NaN — useful for identifying "live" inference rows.
    """
    # Load raw labels
    if not RAW_LABELS_PATH.exists():
        logger.info("raw_labels.parquet not found — computing now...")
        raw = compute_raw_labels(symbols=symbols, save=True)
    else:
        raw = pd.read_parquet(RAW_LABELS_PATH)
        logger.info("Loaded raw labels: %d rows", len(raw))

    if raw.empty:
        return pd.DataFrame()

    # Load features
    features = _load_all_feature_files(symbols=symbols)
    if features.empty:
        logger.warning("No features found — training set will be labels-only.")
        return raw

    # ── Inner join on (symbol, date) ─────────────────────────────────────────
    # raw index = (symbol, date as Timestamp)
    # features index = (symbol, date as Timestamp)
    raw.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in raw.index], names=["symbol", "date"]
    )
    features.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in features.index], names=["symbol", "date"]
    )

    # Drop raw 'date' column if it leaked into features
    feat_cols = [c for c in features.columns if c != "date"]
    features = features[feat_cols]

    merged = features.join(raw, how="inner")
    logger.info("After join: %d rows (feature × label overlap)", len(merged))

    if merged.empty:
        logger.warning(
            "Join produced 0 rows — ensure Phase 2 feature dates overlap with OHLCV dates."
        )
        return merged

    # ── Optionally filter to hardcheck_pass only ──────────────────────────────
    if hardcheck_only and "hardcheck_pass" in merged.columns:
        before = len(merged)
        merged = merged[merged["hardcheck_pass"] == 1]
        logger.info("  hardcheck_only: %d → %d rows", before, len(merged))

    # ── Report class balance ──────────────────────────────────────────────────
    valid_rows = merged[merged["label_valid"] == 1]
    total_valid = len(valid_rows)

    if total_valid > 0:
        pos_rate = valid_rows["label"].mean()
        n_pos = int(valid_rows["label"].sum())
        n_neg = total_valid - n_pos

        logger.info("=" * 60)
        logger.info("Training set summary:")
        logger.info("  Total rows (all):          %6d", len(merged))
        logger.info("  Label-valid rows:          %6d", total_valid)
        logger.info("  Positive (label=1):        %6d  (%.1f%%)", n_pos, pos_rate * 100)
        logger.info("  Negative (label=0):        %6d  (%.1f%%)", n_neg, (1 - pos_rate) * 100)
        logger.info("  scale_pos_weight for LGBM: %.2f  (neg/pos)", n_neg / max(n_pos, 1))
        logger.info("  Features:                  %6d", len(feat_cols))
        logger.info("  Date range:                %s → %s",
                    merged.index.get_level_values("date").min().date(),
                    merged.index.get_level_values("date").max().date())
        logger.info("=" * 60)

        # Save stats
        stats = {
            "generated_at":       datetime.utcnow().isoformat(timespec="seconds"),
            "total_rows":         len(merged),
            "label_valid_rows":   total_valid,
            "positive_count":     n_pos,
            "negative_count":     n_neg,
            "positive_rate":      round(float(pos_rate), 4),
            "scale_pos_weight":   round(n_neg / max(n_pos, 1), 2),
            "n_features":         len(feat_cols),
            "forward_days":       FORWARD_DAYS,
            "ret_threshold":      RET_THRESHOLD,
            "dd_threshold":       DD_THRESHOLD,
            "date_min":           str(merged.index.get_level_values("date").min().date()),
            "date_max":           str(merged.index.get_level_values("date").max().date()),
            "symbols":            sorted(merged.index.get_level_values("symbol").unique().tolist()),
        }

        LABELS_DIR.mkdir(parents=True, exist_ok=True)
        STATS_PATH.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Stats saved → %s", STATS_PATH)

    if save:
        LABELS_DIR.mkdir(parents=True, exist_ok=True)
        merged.to_parquet(TRAINING_SET_PATH, engine="pyarrow")
        logger.info("Training set saved → %s", TRAINING_SET_PATH)

    return merged


# ═════════════════════════════════════════════════════════════════════════════
# STATS & INSPECTION
# ═════════════════════════════════════════════════════════════════════════════


def show_stats() -> None:
    """Print detailed class balance and distribution analysis."""
    if not TRAINING_SET_PATH.exists():
        print("training_set.parquet not found. Run pipeline first.")
        return

    df = pd.read_parquet(TRAINING_SET_PATH)
    valid = df[df["label_valid"] == 1].copy()

    if valid.empty:
        print("No labeled rows found.")
        return

    valid["year"] = valid.index.get_level_values("date").year
    symbols = valid.index.get_level_values("symbol")

    print(f"\n{'='*60}")
    print("LABEL STATISTICS")
    print(f"{'='*60}")
    print(f"Total rows (label-valid):  {len(valid):,}")
    print(f"Symbols:                   {symbols.nunique()}")
    date_idx = valid.index.get_level_values("date")
    print(f"Date range:                {date_idx.min().date()} → {date_idx.max().date()}")
    print(f"Forward window:            {FORWARD_DAYS} trading days")
    print(f"Return threshold:          > {RET_THRESHOLD*100:.0f}%")
    print(f"Drawdown threshold:        > {DD_THRESHOLD*100:.0f}%")
    print()

    # Overall balance
    pos = int(valid["label"].sum())
    neg = len(valid) - pos
    pos_rate = pos / len(valid)
    print(f"Positive (label=1):  {pos:6,}  ({pos_rate*100:.1f}%)")
    print(f"Negative (label=0):  {neg:6,}  ({(1-pos_rate)*100:.1f}%)")
    print(f"scale_pos_weight:    {neg/max(pos,1):.2f}  (use in LightGBM)")

    # Positive rate by year
    print(f"\n{'─'*40}")
    print("Positive rate by year:")
    by_year = valid.groupby("year")["label"].agg(["mean", "count"])
    for yr, row in by_year.iterrows():
        bar = "█" * int(row["mean"] * 40)
        print(f"  {yr}  {row['mean']*100:5.1f}%  ({int(row['count']):5,} rows)  {bar}")

    # Positive rate by symbol (top 10 and bottom 10)
    by_sym = valid.groupby(level="symbol")["label"].agg(["mean", "count"])
    by_sym = by_sym[by_sym["count"] >= 50]  # only symbols with enough data
    print(f"\n{'─'*40}")
    print("Top 10 symbols (highest positive rate):")
    for sym, row in by_sym.nlargest(10, "mean").iterrows():
        print(f"  {sym:<6}  {row['mean']*100:5.1f}%  ({int(row['count'])} rows)")
    print("Bottom 10 symbols (lowest positive rate):")
    for sym, row in by_sym.nsmallest(10, "mean").iterrows():
        print(f"  {sym:<6}  {row['mean']*100:5.1f}%  ({int(row['count'])} rows)")

    # Forward return distribution
    print(f"\n{'─'*40}")
    print("Forward return distribution (label=1 rows):")
    pos_rets = valid[valid["label"] == 1]["forward_ret_10d"].dropna() * 100
    if not pos_rets.empty:
        for pct in [25, 50, 75, 90, 95]:
            print(f"  p{pct:02d}: {pos_rets.quantile(pct/100):+.1f}%")

    print(f"\n{'='*60}")


def show_check() -> None:
    """Show file summary."""
    print(f"\n{'File':<35}  {'Size':>10}  {'Rows':>8}")
    print("-" * 55)
    for path in [RAW_LABELS_PATH, TRAINING_SET_PATH, STATS_PATH]:
        if path.exists():
            size_kb = path.stat().st_size / 1024
            try:
                if path.suffix == ".parquet":
                    rows = len(pd.read_parquet(path))
                    print(f"{path.name:<35}  {size_kb:>8.0f}KB  {rows:>8,}")
                else:
                    print(f"{path.name:<35}  {size_kb:>8.0f}KB  {'(json)':>8}")
            except Exception:
                print(f"{path.name:<35}  {size_kb:>8.0f}KB  {'?':>8}")
        else:
            print(f"{path.name:<35}  {'not found':>10}")

    if STATS_PATH.exists():
        stats = json.loads(STATS_PATH.read_text(encoding="utf-8"))
        print(f"\nLabel stats (last run {stats.get('generated_at','?')}):")
        print(f"  positive_rate:    {stats.get('positive_rate', 0)*100:.1f}%")
        print(f"  scale_pos_weight: {stats.get('scale_pos_weight', '?')}")
        print(f"  n_features:       {stats.get('n_features', '?')}")
        print(f"  date_range:       {stats.get('date_min','?')} → {stats.get('date_max','?')}")


# ═════════════════════════════════════════════════════════════════════════════
# FULL PIPELINE
# ═════════════════════════════════════════════════════════════════════════════


def run(
    symbols: Optional[List[str]] = None,
    hardcheck_only: bool = False,
    labels_only: bool = False,
    join_only: bool = False,
) -> pd.DataFrame:
    """
    Full Phase 3 pipeline: Step 1 (labels) + Step 2 (join with features).

    Args:
        symbols:        restrict to subset; None = all
        hardcheck_only: only keep hardcheck_pass=1 rows in training set
        labels_only:    run Step 1 only (compute raw labels)
        join_only:      run Step 2 only (assumes raw_labels.parquet exists)

    Returns training set DataFrame.
    """
    if join_only:
        return build_training_set(symbols=symbols, hardcheck_only=hardcheck_only, save=True)

    raw = compute_raw_labels(symbols=symbols, save=True)

    if labels_only:
        return raw

    return build_training_set(symbols=symbols, hardcheck_only=hardcheck_only, save=True)


# ─── CLI ─────────────────────────────────────────────────────────────────────


def _parse_args():
    p = argparse.ArgumentParser(description="Phase 3 — Label Generation")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--labels-only",  action="store_true", help="Step 1 only: compute raw labels")
    group.add_argument("--join-only",    action="store_true", help="Step 2 only: join features + labels")
    group.add_argument("--stats",        action="store_true", help="Show class balance stats")
    group.add_argument("--check",        action="store_true", help="Show file summary")
    p.add_argument("--hardcheck-only",   action="store_true", help="Keep only hardcheck_pass=1 rows")
    p.add_argument("--symbols", type=str, default="",         help="Comma-separated symbols override")
    p.add_argument("--ret",     type=float, default=RET_THRESHOLD,  help=f"Return threshold (default {RET_THRESHOLD})")
    p.add_argument("--dd",      type=float, default=DD_THRESHOLD,   help=f"Drawdown threshold (default {DD_THRESHOLD})")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()] or None

    # Override thresholds via module-level assignment
    import pipeline.phase3_label_generator as _m
    _m.RET_THRESHOLD = args.ret
    _m.DD_THRESHOLD  = args.dd

    if args.check:
        show_check()
    elif args.stats:
        show_stats()
    else:
        run(
            symbols=syms,
            hardcheck_only=args.hardcheck_only,
            labels_only=args.labels_only,
            join_only=args.join_only,
        )
