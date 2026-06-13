#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/rebuild_features_with_foreign.py

Rebuild feature parquets for training/validation/test/live dates
after Phase 1C foreign data backfill.

Runs Phase 2 for every trading date in the specified range,
overwriting existing parquets with new versions that include foreign features.

Usage:
    python -m pipeline.rebuild_features_with_foreign              # all 2022-present
    python -m pipeline.rebuild_features_with_foreign --from 2022-07-01  # training start only
    python -m pipeline.rebuild_features_with_foreign --check      # show coverage
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _noisy in ("vnstock", "vnai", "urllib3", "requests"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

FEATURES_DIR = ROOT / "data" / "features"
OHLCV_DIR    = ROOT / "data" / "ohlcv"


def _all_trading_dates(start: str, end: str) -> List[str]:
    """Return list of dates that have feature parquets in [start, end]."""
    dates = []
    for p in sorted(FEATURES_DIR.glob("*.parquet")):
        d = p.stem
        if start <= d <= end:
            dates.append(d)
    return dates


def _check_coverage() -> None:
    """Show how many feature parquets have / lack foreign columns."""
    files = sorted(FEATURES_DIR.glob("*.parquet"))
    has_foreign = 0
    no_foreign  = 0
    for f in files:
        try:
            df = pd.read_parquet(f)
            foreign_cols = [c for c in df.columns if "foreign" in c]
            if foreign_cols:
                has_foreign += 1
            else:
                no_foreign += 1
        except Exception:
            pass
    print(f"\nFeature parquets: {len(files)} total")
    print(f"  ✅ Has foreign features : {has_foreign}")
    print(f"  ❌ Missing foreign       : {no_foreign}")


def rebuild(start: str, end: str) -> None:
    from pipeline.phase2_feature_pipeline import run as phase2_run
    from pipeline.phase1c_foreign_store   import load_foreign
    from pipeline.phase1a_ohlcv_store     import load_parquet, load_all

    import json
    manifest_path = OHLCV_DIR / "_manifest.json"
    symbols = [s for s in json.loads(manifest_path.read_text()).keys()
               if s not in ("VNINDEX", "E1VFVN30")]

    logger.info("Pre-loading OHLCV + foreign caches for %d symbols …", len(symbols))

    # Pre-load caches once (saves ~80% of I/O across all dates)
    ohlcv_cache: dict = load_all(symbols + ["VNINDEX"])

    foreign_cache: dict = {}
    for sym in symbols:
        df = load_foreign(sym)
        if not df.empty:
            foreign_cache[sym.upper()] = df

    logger.info("OHLCV cache: %d  |  Foreign cache: %d", len(ohlcv_cache), len(foreign_cache))

    dates = _all_trading_dates(start, end)
    logger.info("Rebuilding %d feature parquets from %s to %s …", len(dates), start, end)

    for i, date_str in enumerate(dates, 1):
        try:
            phase2_run(
                target_date=date_str,
                save=True,
                ohlcv_cache=ohlcv_cache,
                foreign_cache=foreign_cache,
            )
        except Exception as exc:
            logger.warning("  ✗ %s: %s", date_str, exc)
            continue

        if i % 50 == 0 or i == len(dates):
            logger.info("  [%4d/%d]  last=%s", i, len(dates), date_str)

    logger.info("Done. Rebuilt %d parquets.", len(dates))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--from",  dest="start", default="2022-07-01",
                   help="Start date YYYY-MM-DD (default: 2022-07-01 = training start)")
    p.add_argument("--to",    dest="end",   default="2099-12-31")
    p.add_argument("--check", action="store_true", help="Show coverage stats only")
    args = p.parse_args()

    if args.check:
        _check_coverage()
    else:
        rebuild(args.start, args.end)


if __name__ == "__main__":
    main()
