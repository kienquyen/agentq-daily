"""
Phase 1B — Fundamental Data Store

Fetches quarterly financial ratios for all symbols and stores as Parquet.
Point-in-time correct: each quarterly report is assigned a release date
(45 days after quarter end) to prevent look-ahead bias in Phase 2.

Storage:
    data/fundamentals/{SYMBOL}.parquet
        columns: release_date, period, roe, roa, pe, pb,
                 debt_equity, gross_margin, asset_turnover,
                 net_interest_margin, roe_yoy, earnings_growth

Usage:
    python -m pipeline.phase1b_fundamental_store            # fetch all
    python -m pipeline.phase1b_fundamental_store --check    # show status
    python -m pipeline.phase1b_fundamental_store --symbol VCB  # single symbol
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _log in ("vnstock", "vnai", "urllib3", "requests"):
    logging.getLogger(_log).setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DATA_DIR    = ROOT / "data" / "fundamentals"
OHLCV_DIR   = ROOT / "data" / "ohlcv"
MANIFEST    = DATA_DIR / "_manifest.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOURCE        = "vci"
BATCH_SIZE    = 20
SYMBOL_DELAY  = 0.5   # seconds between symbols
BATCH_PAUSE   = 8.0   # seconds between batches

# Quarters are released ~45 days after quarter end
# Q1 end Mar 31 → available May 15
# Q2 end Jun 30 → available Aug 14
# Q3 end Sep 30 → available Nov 14
# Q4 end Dec 31 → available Feb 14 (next year)
RELEASE_LAG_DAYS = 45


# ── quarter → release date ──────────────────────────────────────────────────

def _quarter_end(period_str: str) -> Optional[pd.Timestamp]:
    """'2024-Q3' → Timestamp('2024-09-30')"""
    try:
        year, q = period_str.split("-Q")
        year = int(year)
        q    = int(q)
        month_end = {1: 3, 2: 6, 3: 9, 4: 12}[q]
        return pd.Timestamp(year=year, month=month_end, day=1) + pd.offsets.MonthEnd(0)
    except Exception:
        return None


def _release_date(period_str: str) -> Optional[pd.Timestamp]:
    """Quarter end + 45 days = earliest date this data is usable."""
    end = _quarter_end(period_str)
    if end is None:
        return None
    return end + pd.Timedelta(days=RELEASE_LAG_DAYS)


# ── fetch one symbol ────────────────────────────────────────────────────────

_RENAME = {
    "ROE (%)":            "roe",
    "ROA (%)":            "roa",
    "P/E":                "pe",
    "P/B":                "pb",
    "Debt/Equity":        "debt_equity",
    "Gross Margin (%)":   "gross_margin",
    "Asset Turnover":     "asset_turnover",
    "Net Interest Margin":"net_interest_margin",
}

def _fetch_ratio(symbol: str) -> pd.DataFrame:
    from vnstock_data import Finance
    f = Finance(symbol=symbol, source=SOURCE)
    df = f.ratio(period="quarter", limit=40)
    return df


def _process_ratio(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    Clean and enrich raw ratio DataFrame.
    Returns rows: [symbol, period, release_date, roe, roa, pe, pb,
                   debt_equity, gross_margin, asset_turnover,
                   net_interest_margin, roe_yoy, earnings_growth]
    """
    df = df.copy()
    df.index.name = "period"
    df = df.reset_index()

    # Rename columns
    df = df.rename(columns=_RENAME)

    # Keep only columns we care about
    keep = ["period"] + [c for c in _RENAME.values() if c in df.columns]
    df = df[keep].copy()

    # Assign release_date per quarter
    df["release_date"] = df["period"].apply(_release_date)
    df = df.dropna(subset=["release_date"])
    df["release_date"] = pd.to_datetime(df["release_date"])

    # Convert numerics
    for col in _RENAME.values():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # YoY growth features (compare to same quarter last year)
    df = df.sort_values("release_date").reset_index(drop=True)
    if "roe" in df.columns:
        df["roe_yoy"] = df["roe"].diff(4)           # 4 quarters back = same quarter YoY
    if "pe" in df.columns:
        df["earnings_growth"] = -df["pe"].diff(4)   # PE drops when earnings grow

    df["symbol"] = symbol
    df = df.set_index(["symbol", "release_date"])
    return df


def fetch_symbol(symbol: str) -> Optional[pd.DataFrame]:
    try:
        raw = _fetch_ratio(symbol)
        if raw is None or raw.empty:
            log.warning("  %s: empty ratio data", symbol)
            return None
        processed = _process_ratio(raw, symbol)
        return processed
    except Exception as e:
        log.warning("  %s: %s — %s", symbol, type(e).__name__, str(e)[:100])
        return None


# ── storage ─────────────────────────────────────────────────────────────────

def _parquet_path(symbol: str) -> Path:
    return DATA_DIR / f"{symbol.upper()}.parquet"


def save(symbol: str, df: pd.DataFrame) -> None:
    path = _parquet_path(symbol)
    df.to_parquet(path, engine="pyarrow")


def load(symbol: str) -> pd.DataFrame:
    path = _parquet_path(symbol)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def _load_manifest() -> Dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_manifest(m: Dict) -> None:
    MANIFEST.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")


# ── main fetch loop ──────────────────────────────────────────────────────────

def _load_universe() -> List[str]:
    """Load symbol list from OHLCV manifest."""
    ohlcv_manifest = OHLCV_DIR / "_manifest.json"
    if ohlcv_manifest.exists():
        try:
            m = json.loads(ohlcv_manifest.read_text(encoding="utf-8"))
            syms = [s for s in m if s != "VNINDEX"]
            log.info("Universe from OHLCV manifest: %d symbols", len(syms))
            return syms
        except Exception:
            pass
    log.warning("OHLCV manifest not found — run Phase 1A first")
    return []


def run(symbols: Optional[List[str]] = None, force: bool = False) -> None:
    universe = symbols or _load_universe()
    if not universe:
        log.error("No symbols to fetch. Run Phase 1A first.")
        return

    manifest = _load_manifest()
    ok = err = skip = 0

    log.info("=" * 60)
    log.info("Phase 1B Fundamental Store  |  symbols=%d  |  source=%s", len(universe), SOURCE)
    log.info("=" * 60)

    for i, sym in enumerate(universe, 1):
        if not force and sym in manifest:
            skip += 1
            continue

        df = fetch_symbol(sym)
        eta_sym = (len(universe) - i) * (SYMBOL_DELAY + 0.3)

        if df is not None and not df.empty:
            save(sym, df)
            manifest[sym] = {
                "quarters": len(df),
                "latest_period": df.reset_index()["release_date"].max().strftime("%Y-%m-%d") if len(df) else "?",
            }
            ok += 1
            log.info("  [%3d/%d] %-8s ✓  %d quarters  ETA %.0fm",
                     i, len(universe), sym, len(df), eta_sym / 60)
        else:
            err += 1
            log.warning("  [%3d/%d] %-8s ✗  FAILED", i, len(universe), sym)

        time.sleep(SYMBOL_DELAY)
        if i % BATCH_SIZE == 0:
            log.info("  ── batch pause %.0fs ──", BATCH_PAUSE)
            _save_manifest(manifest)
            time.sleep(BATCH_PAUSE)

    _save_manifest(manifest)
    log.info("=" * 60)
    log.info("Done  ✓ %d  ✗ %d  skip %d", ok, err, skip)
    log.info("=" * 60)


# ── point-in-time lookup (used by Phase 2) ──────────────────────────────────

def get_fundamentals_as_of(target_date: str) -> pd.DataFrame:
    """
    For each symbol, return the most recent quarterly fundamental data
    whose release_date <= target_date (point-in-time correct).

    Returns DataFrame indexed by symbol with fundamental feature columns.
    """
    target = pd.Timestamp(target_date)
    rows = []

    for fp in DATA_DIR.glob("*.parquet"):
        if fp.name.startswith("_"):
            continue
        sym = fp.stem
        try:
            df = pd.read_parquet(fp)
            df = df.reset_index()
            # Only use data released on or before target_date
            available = df[df["release_date"] <= target]
            if available.empty:
                continue
            # Most recent available quarter
            latest = available.sort_values("release_date").iloc[-1]
            row = {"symbol": sym}
            for col in ["roe", "roa", "pe", "pb", "debt_equity",
                        "gross_margin", "asset_turnover", "net_interest_margin",
                        "roe_yoy", "earnings_growth"]:
                row[f"fund_{col}"] = latest.get(col, np.nan)
            # Staleness: how many days since this data was released
            row["fund_staleness_days"] = (target - latest["release_date"]).days
            rows.append(row)
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows).set_index("symbol")
    return result


# ── status ───────────────────────────────────────────────────────────────────

def show_status() -> None:
    manifest = _load_manifest()
    files = list(DATA_DIR.glob("*.parquet"))
    print(f"\nFundamental store: {len(files)} symbols")
    print(f"{'Symbol':<10} {'Quarters':>9} {'Latest release':>16}")
    print("-" * 40)
    for sym, info in sorted(manifest.items()):
        print(f"{sym:<10} {info.get('quarters','?'):>9} {info.get('latest_period','?'):>16}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description="Phase 1B: Fundamental data store")
    p.add_argument("--check",  action="store_true", help="Show status")
    p.add_argument("--symbol", type=str, default="", help="Fetch single symbol")
    p.add_argument("--force",  action="store_true", help="Re-fetch even if cached")
    args = p.parse_args()

    if args.check:
        show_status()
    elif args.symbol:
        sym = args.symbol.upper()
        df = fetch_symbol(sym)
        if df is not None:
            save(sym, df)
            print(df.to_string())
            log.info("Saved %d quarters for %s", len(df), sym)
    else:
        run(force=args.force)


if __name__ == "__main__":
    main()
