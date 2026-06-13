#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/phase3b_label_generator_20d.py
Phase 3B — Label Generation for 20-Day Propensity-to-Buy Model

Label definition:
    label = 1  if  forward_ret_20d >= +5%  AND  max_drawdown_20d >= -10%
    label = 0  otherwise

Saves to separate paths (data/labels/*_20d.parquet) so the existing
5-day model is NOT touched.

Usage:
    python -m pipeline.phase3b_label_generator_20d              # full pipeline
    python -m pipeline.phase3b_label_generator_20d --labels-only
    python -m pipeline.phase3b_label_generator_20d --stats
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

# Import shared helpers from phase3
from pipeline.phase3_label_generator import (
    _compute_symbol_labels,
    _load_all_feature_files,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
OHLCV_DIR   = ROOT / "data" / "ohlcv"
LABELS_DIR  = ROOT / "data" / "labels"

RAW_LABELS_20D_PATH   = LABELS_DIR / "raw_labels_20d.parquet"
TRAINING_SET_20D_PATH = LABELS_DIR / "training_set_20d.parquet"
STATS_20D_PATH        = LABELS_DIR / "label_stats_20d.json"

# ── Label config ──────────────────────────────────────────────────────────────
FORWARD_DAYS  = 20      # hold for 1 month (~20 trading days)
RET_THRESHOLD = 0.05    # forward return >= +5%
DD_THRESHOLD  = -0.10   # max intraperiod drawdown must stay above -10%


# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 — RAW LABEL COMPUTATION
# ═════════════════════════════════════════════════════════════════════════════

def compute_raw_labels_20d(
    symbols: Optional[List[str]] = None,
    save: bool = True,
) -> pd.DataFrame:
    """
    Compute 20-day raw labels for all symbols from OHLCV parquet files.
    Saves to data/labels/raw_labels_20d.parquet.
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
    logger.info(
        "Step 1: 20D labels for %d symbols  (hold=%dd, ret>=%.0f%%, dd>=%.0f%%)",
        len(symbols), FORWARD_DAYS, RET_THRESHOLD * 100, DD_THRESHOLD * 100,
    )

    all_frames = []
    missing, skipped = [], []

    for sym in symbols:
        path = OHLCV_DIR / f"{sym}.parquet"
        if not path.exists():
            missing.append(sym)
            continue
        try:
            df = pd.read_parquet(path)
            lbl = _compute_symbol_labels(df, FORWARD_DAYS, RET_THRESHOLD, DD_THRESHOLD)
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

    valid = result[result["label_valid"] == 1]
    pos_rate = valid["label"].mean() if len(valid) > 0 else 0
    logger.info(
        "  Raw labels: %d total | %d labelable | positive rate = %.1f%%",
        len(result), len(valid), pos_rate * 100,
    )

    if missing:
        logger.warning("Missing OHLCV: %d symbols", len(missing))
    if skipped:
        logger.warning("Skipped (error/empty): %d symbols", len(skipped))

    if save:
        result.to_parquet(RAW_LABELS_20D_PATH, engine="pyarrow")
        logger.info("  Saved → %s", RAW_LABELS_20D_PATH)

    return result


# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 — JOIN FEATURES + LABELS → TRAINING SET
# ═════════════════════════════════════════════════════════════════════════════

def build_training_set_20d(
    symbols: Optional[List[str]] = None,
    hardcheck_only: bool = False,
    save: bool = True,
) -> pd.DataFrame:
    """
    Join Phase-2 features with 20-day raw labels.
    Saves to data/labels/training_set_20d.parquet.
    """
    if not RAW_LABELS_20D_PATH.exists():
        logger.info("raw_labels_20d.parquet not found — computing now...")
        raw = compute_raw_labels_20d(symbols=symbols, save=True)
    else:
        raw = pd.read_parquet(RAW_LABELS_20D_PATH)
        logger.info("Loaded 20d raw labels: %d rows", len(raw))

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
    merged = features[feat_cols].join(raw, how="inner")
    logger.info("After join: %d rows (feature × label overlap)", len(merged))

    if merged.empty:
        logger.warning("Join produced 0 rows.")
        return merged

    if hardcheck_only and "hardcheck_pass" in merged.columns:
        before = len(merged)
        merged = merged[merged["hardcheck_pass"] == 1]
        logger.info("  hardcheck_only: %d → %d rows", before, len(merged))

    valid_rows = merged[merged["label_valid"] == 1]
    total_valid = len(valid_rows)

    if total_valid > 0:
        pos_rate = valid_rows["label"].mean()
        n_pos = int(valid_rows["label"].sum())
        n_neg = total_valid - n_pos

        logger.info("=" * 60)
        logger.info("20D Training set summary:")
        logger.info("  Total rows:                %6d", len(merged))
        logger.info("  Label-valid rows:          %6d", total_valid)
        logger.info("  Positive (label=1):        %6d  (%.1f%%)", n_pos, pos_rate * 100)
        logger.info("  Negative (label=0):        %6d  (%.1f%%)", n_neg, (1 - pos_rate) * 100)
        logger.info("  scale_pos_weight for LGBM: %.2f", n_neg / max(n_pos, 1))
        logger.info("  Forward days:              %d", FORWARD_DAYS)
        logger.info("  Ret threshold:             +%.0f%%", RET_THRESHOLD * 100)
        logger.info("  DD threshold:              %.0f%%", DD_THRESHOLD * 100)
        logger.info("  Date range:                %s → %s",
                    merged.index.get_level_values("date").min().date(),
                    merged.index.get_level_values("date").max().date())
        logger.info("=" * 60)

        stats = {
            "generated_at":     datetime.utcnow().isoformat(timespec="seconds"),
            "total_rows":       len(merged),
            "label_valid_rows": total_valid,
            "positive_count":   n_pos,
            "negative_count":   n_neg,
            "positive_rate":    round(float(pos_rate), 4),
            "scale_pos_weight": round(n_neg / max(n_pos, 1), 2),
            "forward_days":     FORWARD_DAYS,
            "ret_threshold":    RET_THRESHOLD,
            "dd_threshold":     DD_THRESHOLD,
            "date_min":         str(merged.index.get_level_values("date").min().date()),
            "date_max":         str(merged.index.get_level_values("date").max().date()),
        }
        LABELS_DIR.mkdir(parents=True, exist_ok=True)
        STATS_20D_PATH.write_text(json.dumps(stats, indent=2, ensure_ascii=False))
        logger.info("Stats saved → %s", STATS_20D_PATH)

    if save:
        LABELS_DIR.mkdir(parents=True, exist_ok=True)
        merged.to_parquet(TRAINING_SET_20D_PATH, engine="pyarrow")
        logger.info("Training set saved → %s", TRAINING_SET_20D_PATH)

    return merged


# ═════════════════════════════════════════════════════════════════════════════
# FULL PIPELINE
# ═════════════════════════════════════════════════════════════════════════════

def run(
    symbols: Optional[List[str]] = None,
    hardcheck_only: bool = False,
    labels_only: bool = False,
    join_only: bool = False,
) -> pd.DataFrame:
    if join_only:
        return build_training_set_20d(symbols=symbols, hardcheck_only=hardcheck_only)

    raw = compute_raw_labels_20d(symbols=symbols, save=True)
    if labels_only:
        return raw

    return build_training_set_20d(symbols=symbols, hardcheck_only=hardcheck_only, save=True)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _show_stats() -> None:
    if not STATS_20D_PATH.exists():
        print("label_stats_20d.json not found. Run pipeline first.")
        return
    stats = json.loads(STATS_20D_PATH.read_text())
    print(f"\n{'='*55}")
    print("20D LABEL STATS")
    print(f"{'='*55}")
    for k, v in stats.items():
        print(f"  {k:<22}: {v}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Phase 3B — 20-Day Label Generator")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--labels-only", action="store_true")
    g.add_argument("--join-only",   action="store_true")
    g.add_argument("--stats",       action="store_true")
    p.add_argument("--hardcheck-only", action="store_true")
    p.add_argument("--symbols", type=str, default="")
    args = p.parse_args()

    syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()] or None

    if args.stats:
        _show_stats()
    else:
        run(
            symbols=syms,
            hardcheck_only=args.hardcheck_only,
            labels_only=args.labels_only,
            join_only=args.join_only,
        )
