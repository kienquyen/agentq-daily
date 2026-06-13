#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/phase1c_foreign_store.py
Phase 1C — Foreign Investor Flow Data Store

Fetches daily foreign buy/sell/net data per symbol via vnstock_data.
Stored as: data/foreign/{SYMBOL}.parquet
Columns: trading_date, buy_vol, buy_val, sell_vol, sell_val, net_vol, net_val

Usage:
    python -m pipeline.phase1c_foreign_store               # incremental update
    python -m pipeline.phase1c_foreign_store --backfill    # full history from 2022-01-01
    python -m pipeline.phase1c_foreign_store --check       # show status
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
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

DATA_DIR       = ROOT / "data" / "foreign"
OHLCV_MANIFEST = ROOT / "data" / "ohlcv" / "_manifest.json"
BACKFILL_START = "2022-01-01"
BATCH_SIZE     = 20
BATCH_PAUSE    = 8.0
SYMBOL_DELAY   = 0.5


def _universe() -> List[str]:
    if OHLCV_MANIFEST.exists():
        manifest = json.loads(OHLCV_MANIFEST.read_text(encoding="utf-8"))
        return [s for s in manifest if s not in ("VNINDEX", "E1VFVN30")]
    return []


def _fetch(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Fetch foreign flow data with automatic pagination.
    The API caps at 100 rows per request, so we chunk into 60-day windows
    to ensure full coverage without missing data.
    """
    from vnstock_data import Market

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt   = datetime.strptime(end, "%Y-%m-%d")
    chunk_days = 60   # safe margin under 100 trading-row cap

    all_frames = []
    cursor = start_dt
    while cursor <= end_dt:
        chunk_end = min(cursor + timedelta(days=chunk_days), end_dt)
        try:
            df = Market().equity(symbol).foreign_flow(
                start=cursor.strftime("%Y-%m-%d"),
                end=chunk_end.strftime("%Y-%m-%d"),
            )
            if df is not None and not df.empty:
                all_frames.append(df)
        except Exception:
            pass
        cursor = chunk_end + timedelta(days=1)
        time.sleep(0.2)   # light throttle between chunks

    if not all_frames:
        return pd.DataFrame()

    combined = pd.concat(all_frames, ignore_index=True)
    combined["trading_date"] = pd.to_datetime(combined["trading_date"])
    combined = combined.drop_duplicates("trading_date").sort_values("trading_date").reset_index(drop=True)
    return combined


def _last_date(symbol: str) -> Optional[str]:
    path = DATA_DIR / f"{symbol}.parquet"
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
        return str(df["trading_date"].max().date())
    except Exception:
        return None


def update_symbol(symbol: str, end_date: str, full: bool = False) -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{symbol}.parquet"

    last = _last_date(symbol)
    if full or last is None:
        start = BACKFILL_START
    else:
        # incremental: fetch from day after last stored
        next_day = (datetime.strptime(last, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        if next_day > end_date:
            return True  # already up to date
        start = next_day

    try:
        new_df = _fetch(symbol, start, end_date)
    except Exception as e:
        logger.warning("  ✗ %s: fetch failed — %s", symbol, e)
        return False

    if new_df.empty:
        logger.debug("  %s: no new data", symbol)
        return True

    if path.exists() and not full:
        existing = pd.read_parquet(path)
        combined = pd.concat([existing, new_df]).drop_duplicates("trading_date").sort_values("trading_date")
    else:
        combined = new_df

    combined.to_parquet(path, index=False)
    return True


def update_all(end_date: Optional[str] = None, full: bool = False) -> None:
    end_date = end_date or datetime.utcnow().strftime("%Y-%m-%d")
    symbols  = _universe()
    if not symbols:
        logger.error("No symbols found — run Phase 1A first.")
        return

    logger.info("=" * 60)
    logger.info("Phase 1C Foreign Flow  |  mode=%s  |  symbols=%d  |  end=%s",
                "backfill" if full else "incremental", len(symbols), end_date)
    logger.info("=" * 60)

    ok = fail = 0
    for i, sym in enumerate(symbols, 1):
        success = update_symbol(sym, end_date, full=full)
        if success:
            ok += 1
        else:
            fail += 1

        if i % BATCH_SIZE == 0 and i < len(symbols):
            logger.info("  ── batch pause %.0fs ──", BATCH_PAUSE)
            time.sleep(BATCH_PAUSE)
        else:
            time.sleep(SYMBOL_DELAY)

        if i % 20 == 0 or i == len(symbols):
            logger.info("  [%3d/%d]  ok=%d  fail=%d", i, len(symbols), ok, fail)

    logger.info("Done  ✓ %d  ✗ %d", ok, fail)


def load_foreign(symbol: str) -> pd.DataFrame:
    """Load stored foreign flow for a symbol. Returns empty DataFrame if not found."""
    path = DATA_DIR / f"{symbol}.parquet"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(path)
        df["trading_date"] = pd.to_datetime(df["trading_date"])
        return df.sort_values("trading_date").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def show_status() -> None:
    files = sorted(DATA_DIR.glob("*.parquet")) if DATA_DIR.exists() else []
    print(f"\n{'Symbol':<8}  {'Rows':>6}  {'First':>12}  {'Last':>12}")
    print("-" * 44)
    for f in files[:30]:
        try:
            df = pd.read_parquet(f)
            df["trading_date"] = pd.to_datetime(df["trading_date"])
            print(f"{f.stem:<8}  {len(df):>6}  {str(df['trading_date'].min().date()):>12}  {str(df['trading_date'].max().date()):>12}")
        except Exception as e:
            print(f"{f.stem:<8}  ERROR: {e}")
    print(f"\nTotal: {len(files)} symbols at {DATA_DIR}")


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 1C — Foreign Flow Store")
    p.add_argument("--backfill", action="store_true", help="Full backfill from 2022-01-01")
    p.add_argument("--check",    action="store_true", help="Show status")
    p.add_argument("--end",      type=str, default=None, help="End date YYYY-MM-DD")
    args = p.parse_args()

    if args.check:
        show_status()
    else:
        update_all(end_date=args.end, full=args.backfill)


if __name__ == "__main__":
    main()
