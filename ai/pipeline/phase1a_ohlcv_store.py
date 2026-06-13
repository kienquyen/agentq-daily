#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/phase1a_ohlcv_store.py
Phase 1A — Incremental OHLCV Data Store for Top 200 VN Stocks

Modes:
    python -m pipeline.phase1a_ohlcv_store              # auto (backfill mới, incremental cũ)
    python -m pipeline.phase1a_ohlcv_store --backfill   # force full backfill từ BACKFILL_START
    python -m pipeline.phase1a_ohlcv_store --update     # incremental update hôm nay
    python -m pipeline.phase1a_ohlcv_store --check      # hiển thị trạng thái manifest

Storage layout:
    data/ohlcv/{SYMBOL}.parquet   — OHLCV daily, columns: time, open, high, low, close, volume
    data/ohlcv/_manifest.json     — {symbol: {last_date, rows, updated_at}}

Rate limit (vnstock_data Golden: 500 req/min):
    Batch size 20 × delay 0.3s/symbol + 8s pause giữa batch
    → ~200 mã hoàn thành trong ~3–4 phút
"""

from __future__ import annotations

import argparse
import inspect
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ─── Path setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Suppress vnstock noise
for _noisy in ("vnstock", "vnai", "urllib3", "requests"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────
DATA_DIR        = ROOT / "data" / "ohlcv"
MANIFEST_PATH   = DATA_DIR / "_manifest.json"
BACKFILL_START  = "2022-01-01"
TOP_N           = 200
BATCH_SIZE      = 20      # symbols per batch
BATCH_PAUSE     = 8.0     # seconds between batches
SYMBOL_DELAY    = 0.3     # seconds between each symbol fetch
MAX_RETRIES     = 2
ALLOWED_SOURCES = ["kbs", "vci", "vnd", "mas"]

# ─── Universe (VN200+, ordered roughly by liquidity) ─────────────────────────
VN200_UNIVERSE: List[str] = [
    # ETF
    "E1VFVN30",
    # VN30 — blue chips
    "VCB", "BID", "CTG", "TCB", "MBB", "VPB", "ACB", "HDB", "STB", "VIB",
    "FPT", "VIC", "VHM", "MSN", "MWG", "VNM", "GAS", "HPG", "PLX", "SAB",
    "POW", "GVR", "BVH", "BCM", "SSI", "VRE", "NVL", "TPB", "VJC", "PDR",
    # VN70
    "VCI", "SHS", "MBS", "HCM", "SSB", "NAB", "OCB", "LPB", "VIX", "EIB",
    "DGC", "DGW", "GMD", "REE", "PNJ", "PVS", "PVD", "PVT", "HAH", "SCS",
    "KBC", "KDH", "NLG", "IDC", "DIG", "DXG", "HDG", "AGR", "ANV", "CMG",
    "BWE", "C4G", "DPM", "DCM", "QNS", "PHR", "PC1", "NKG", "HSG", "HUT",
    "IMP", "MSB", "THG", "TV2", "VGC", "VGI", "VHC", "VSC", "VGS", "DHC",
    "PAN", "SBT", "TCH", "TLG", "PVB", "GTN", "LHG", "DBC", "KDC", "VTP",
    "VND", "SKG", "VCS",
    # Mid-cap mở rộng
    "ACV", "AGG", "AMD", "APH", "BSR", "CHP", "CSM", "DHA", "DHG", "DRC",
    "DXS", "EVE", "FCN", "GEG", "GIL", "HAG", "HBC", "HDC", "HNG", "HPX",
    "HQC", "HVN", "IJC", "ITA", "KHG", "LCG", "LDG", "LSS", "MIG", "MSH",
    "NAF", "NBB", "NHH", "NSC", "NVT", "PDN", "PET", "PGI", "PNG", "PPC",
    "PTB", "PVE", "PVG", "RAL", "SAP", "SCI", "SGN", "SHA", "SHI", "SHN",
    "SHP", "SIP", "SJD", "SMC", "SPM", "SRC", "SRF", "SSC", "STG", "STP",
    "SVT", "TBC", "TCL", "TDM", "TDN", "TDW", "TIX", "TLH", "TLX", "TMP",
    "TNT", "TPC", "TRA", "TRC", "TSC", "TTC", "TV3", "UIC", "VCF", "VDS",
    "VGP", "VHL", "VID", "VLC", "VNA", "VNE", "VNR", "VNS", "VOS", "VRC",
    "VRG", "VSH", "VSN", "VTA", "VTC", "VTO", "WCS", "DCL", "AAA", "CII",
    "GEX", "HHV", "NTC", "NTP", "PLC", "PLP", "PMB", "PRE", "PSH", "PSI",
    "PTI", "PVC", "PVP", "PXS", "QCG", "QTP", "RIC", "SAS", "SBS", "SD5",
    "SGP", "SHB", "SJG", "SLS", "SWC", "SZC", "TAR", "TCD", "TCI", "TCW",
]


# ─── Manifest helpers ─────────────────────────────────────────────────────────


def _load_manifest() -> Dict[str, dict]:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_manifest(manifest: Dict[str, dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _parquet_path(symbol: str) -> Path:
    return DATA_DIR / f"{symbol.upper()}.parquet"


# ─── Parquet read / write ─────────────────────────────────────────────────────


def load_parquet(symbol: str) -> pd.DataFrame:
    path = _parquet_path(symbol)
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(path)
        df["time"] = pd.to_datetime(df["time"])
        return df.sort_values("time").reset_index(drop=True)
    except Exception as e:
        logger.warning("load_parquet(%s): %s", symbol, e)
        return pd.DataFrame()


def save_parquet(symbol: str, df: pd.DataFrame) -> int:
    """Merge with existing data, deduplicate by time, save. Returns final row count."""
    if df is None or df.empty:
        return 0

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_parquet(symbol)

    if not existing.empty:
        combined = pd.concat([existing, df], ignore_index=True)
    else:
        combined = df.copy()

    combined["time"] = pd.to_datetime(combined["time"])
    combined = (
        combined
        .drop_duplicates(subset=["time"], keep="last")
        .sort_values("time")
        .reset_index(drop=True)
    )

    combined.to_parquet(_parquet_path(symbol), index=False, engine="pyarrow")
    return len(combined)


# ─── OHLCV fetch (lenient — no strict last-date requirement) ─────────────────


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize columns to: time, open, high, low, close, volume."""
    if df is None or df.empty:
        return pd.DataFrame()

    d = df.copy()
    d.columns = [str(c).lower().strip() for c in d.columns]

    # time column
    for tcol in ["time", "date", "tradingdate", "trading_date", "datetime"]:
        if tcol in d.columns:
            d["time"] = pd.to_datetime(d[tcol], errors="coerce").dt.normalize()
            break
    else:
        return pd.DataFrame()

    # OHLCV aliases
    aliases = {
        "open":   ["open", "openprice", "o"],
        "high":   ["high", "highprice", "h"],
        "low":    ["low",  "lowprice",  "l"],
        "close":  ["close", "closeprice", "price", "c"],
        "volume": ["volume", "vol", "totalvolume", "matched_volume"],
    }
    for std, cands in aliases.items():
        if std not in d.columns:
            for c in cands:
                if c in d.columns:
                    d[std] = d[c]
                    break
        if std not in d.columns:
            d[std] = np.nan

    out = d[["time", "open", "high", "low", "close", "volume"]].copy()
    for col in ["open", "high", "low", "close", "volume"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = (
        out.dropna(subset=["time", "close"])
        .drop_duplicates(subset=["time"], keep="last")
        .sort_values("time")
        .reset_index(drop=True)
    )

    # Auto-scale prices in 1–999 range (thousand-VND → VND)
    if not out.empty:
        sample = out["close"].dropna()
        if len(sample) > 0 and float(sample.median()) < 1000:
            for col in ["open", "high", "low", "close"]:
                out[col] = out[col] * 1000

    return out


def _fetch_one_source(symbol: str, source: str, start: str, end: str) -> pd.DataFrame:
    """Single-source fetch via vnstock.Quote."""
    try:
        # Use vnstock (free) Quote which is more battle-tested for history
        from vnstock import Quote
        q = Quote(symbol=symbol, source=source)
        df = q.history(start=start, end=end, interval="1D")
        return _normalize(df)
    except Exception:
        pass

    # Fallback: vnstock_data Market Unified UI
    try:
        from app.vnstock_core.core import _fix_vnstock_path
        _fix_vnstock_path()
        from vnstock_data import Market
        mkt = Market()
        df = mkt.equity(symbol).ohlcv(start=start, end=end)
        return _normalize(df)
    except Exception:
        pass

    return pd.DataFrame()


def _prev_trading_day(date_str: str) -> str:
    """Return the most recent trading day (Mon–Fri) strictly before date_str."""
    d = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)
    while d.weekday() >= 5:          # skip Sat/Sun
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def fetch_ohlcv_lenient(
    symbol: str,
    start: str,
    end: str,
    sources: List[str] = ALLOWED_SOURCES,
) -> Tuple[pd.DataFrame, str]:
    """
    Try sources in order with freshness fallback.

    Logic:
    - Lấy kết quả từ source đầu tiên có data (first-found).
    - Nếu last_date của kết quả < prev_trading_day(end), source đó bị stale
      → thử source tiếp theo, giữ kết quả mới nhất tìm được.
    - Nếu không source nào fresh hơn → trả về kết quả first-found.
    - Giới hạn 1 retry thêm mỗi source (không thử all 4 cho mọi symbol).

    Returns (df, source_used) or (empty_df, "").
    """
    freshness_threshold = _prev_trading_day(end)   # e.g. end=2026-05-22 → threshold=2026-05-21

    best_df:  pd.DataFrame = pd.DataFrame()
    best_src: str          = ""
    best_last: str         = ""

    for src in sources:
        try:
            df = _fetch_one_source(symbol, src, start, end)
            if df.empty or len(df) < 1:
                time.sleep(0.05)
                continue

            last_date = str(df["time"].iloc[-1].date()) if "time" in df.columns else ""

            # First result: always keep as fallback
            if best_df.empty:
                best_df, best_src, best_last = df, src, last_date

            # Fresh enough → use immediately, no need to try more sources
            if last_date >= freshness_threshold:
                return df, src

            # Stale but better than what we have → update best
            if last_date > best_last:
                best_df, best_src, best_last = df, src, last_date

        except Exception:
            pass
        time.sleep(0.05)

    # No fresh source found → return best available (first-found or newest)
    return best_df, best_src


# ─── Universe loader ──────────────────────────────────────────────────────────


def load_universe(top_n: int = TOP_N, include_vnindex: bool = True) -> List[str]:
    """
    Return top_n symbols + VNINDEX (always prepended for Phase 2 risk features).

    Uses VN200_UNIVERSE static list as the sole source.
    Reference().equity.list() was removed because it returns ~700+ symbols in
    reverse-alphabetical order — [:200] would exclude blue-chips like BVH, CTG,
    HPG, MBB, SSI (B/C/H/M/S prefix) in favour of Y/X/W/V stocks.
    """
    universe = list(dict.fromkeys(VN200_UNIVERSE))  # deduplicate, preserve order
    logger.info("Universe: %d symbols (requesting %d)", len(universe), top_n)
    result = universe[:top_n]
    if include_vnindex and "VNINDEX" not in result:
        result = ["VNINDEX"] + result
    return result


# ─── Core fetch-and-store logic ───────────────────────────────────────────────


def _last_stored_date(symbol: str, manifest: Dict[str, dict]) -> Optional[str]:
    entry = manifest.get(symbol.upper())
    if entry:
        return entry.get("last_date")
    # Also check parquet directly
    df = load_parquet(symbol)
    if not df.empty:
        return str(df["time"].iloc[-1].date())
    return None


def fetch_and_store(
    symbol: str,
    start: str,
    end: str,
    manifest: Dict[str, dict],
    mode: str = "auto",
) -> bool:
    """
    Fetch [start, end] OHLCV for symbol and persist to parquet.
    Returns True on success.

    mode:
        "backfill"   — always fetch full range
        "incremental"— fetch only from (last_stored + 1 day) to end
        "auto"       — backfill if no data, else incremental
    """
    symbol = symbol.upper()
    last_date = _last_stored_date(symbol, manifest)

    if mode == "auto":
        effective_start = start if last_date is None else (
            datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)
        ).strftime("%Y-%m-%d")
    elif mode == "incremental":
        if last_date is None:
            logger.debug("%s: no existing data, running backfill instead", symbol)
            effective_start = start
        else:
            next_day = (datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            if next_day > end:
                logger.debug("%s: already up to date (%s)", symbol, last_date)
                return True
            effective_start = next_day
    else:  # backfill
        effective_start = start

    if effective_start > end:
        logger.debug("%s: already up to date (%s)", symbol, last_date)
        # Ensure manifest entry exists even when skipping fetch
        if symbol not in manifest and last_date:
            df_existing = load_parquet(symbol)
            manifest[symbol] = {
                "last_date":  last_date,
                "rows":       len(df_existing),
                "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
                "source":     manifest.get(symbol, {}).get("source", "cached"),
            }
        return True

    for attempt in range(1, MAX_RETRIES + 1):
        df, src = fetch_ohlcv_lenient(symbol, effective_start, end)
        if not df.empty:
            break
        if attempt < MAX_RETRIES:
            time.sleep(2.0 * attempt)  # back-off

    if df.empty:
        logger.warning("  ✗ %s: no data fetched (%s → %s)", symbol, effective_start, end)
        return False

    final_rows = save_parquet(symbol, df)
    last_stored = str(df["time"].iloc[-1].date())
    manifest[symbol] = {
        "last_date":  last_stored,
        "rows":       final_rows,
        "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
        "source":     src,
    }
    return True


# ─── Batch runner ─────────────────────────────────────────────────────────────


def run(
    mode: str = "auto",
    top_n: int = TOP_N,
    backfill_start: str = BACKFILL_START,
    symbols_override: Optional[List[str]] = None,
) -> None:
    """
    Main entry point.

    Args:
        mode:              "auto" | "backfill" | "incremental"
        top_n:             number of top symbols to process
        backfill_start:    historical start date for full backfill
        symbols_override:  if set, skip universe loading and use this list
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest()

    symbols = symbols_override or load_universe(top_n)
    end = datetime.utcnow().strftime("%Y-%m-%d")

    logger.info("=" * 60)
    logger.info("Phase 1A OHLCV Store  |  mode=%s  |  symbols=%d  |  end=%s", mode, len(symbols), end)
    logger.info("=" * 60)

    success, failed, skipped = 0, [], []
    total = len(symbols)
    t_start = time.time()

    for i, symbol in enumerate(symbols, 1):
        # Progress + ETA
        elapsed = time.time() - t_start
        eta_str = ""
        if i > 1:
            avg_per = elapsed / (i - 1)
            remaining = avg_per * (total - i + 1)
            eta_str = f"  ETA {remaining/60:.1f}m"

        print(f"  [{i:>3}/{total}] {symbol:<6}", end="", flush=True)

        ok = fetch_and_store(symbol, backfill_start, end, manifest, mode=mode)
        if ok:
            entry = manifest.get(symbol, {})
            rows = entry.get("rows", "?")
            last = entry.get("last_date", "?")
            src  = entry.get("source", "?")
            print(f"  ✓  {rows} rows  last={last}  src={src}{eta_str}")
            success += 1
        else:
            print(f"  ✗  FAILED{eta_str}")
            failed.append(symbol)

        # Save manifest after every symbol (safe against interruption)
        _save_manifest(manifest)

        time.sleep(SYMBOL_DELAY)

        # Batch pause
        if i % BATCH_SIZE == 0 and i < total:
            logger.info("  ── batch pause %.0fs ──", BATCH_PAUSE)
            time.sleep(BATCH_PAUSE)

    # ── Summary ────────────────────────────────────────────────────────────────
    elapsed_total = time.time() - t_start
    print()
    logger.info("=" * 60)
    logger.info("Done  ✓ %d  ✗ %d  |  %.1fs", success, len(failed), elapsed_total)
    if failed:
        logger.warning("Failed symbols: %s", ", ".join(failed))
    logger.info("Manifest saved → %s", MANIFEST_PATH)
    logger.info("=" * 60)


# ─── Status / check ──────────────────────────────────────────────────────────


def show_status() -> None:
    """Print manifest summary table."""
    manifest = _load_manifest()
    if not manifest:
        print("No manifest found. Run --backfill first.")
        return

    print(f"\n{'Symbol':<8}  {'Last Date':<12}  {'Rows':>6}  {'Source':<6}  Updated")
    print("-" * 60)
    for sym, info in sorted(manifest.items()):
        print(
            f"{sym:<8}  {info.get('last_date','?'):<12}  "
            f"{info.get('rows',0):>6}  {info.get('source','?'):<6}  "
            f"{info.get('updated_at','?')[:16]}"
        )
    print(f"\nTotal: {len(manifest)} symbols stored at {DATA_DIR}")

    # Staleness check
    today = datetime.utcnow().strftime("%Y-%m-%d")
    stale = [s for s, v in manifest.items() if v.get("last_date", "") < today]
    if stale:
        print(f"\n⚠  {len(stale)} symbols may need update (last_date < today): {', '.join(stale[:10])}{'...' if len(stale) > 10 else ''}")
    else:
        print("\n✓  All symbols are up to date.")


# ─── Convenience: load stored data for downstream use ────────────────────────


def load_all(symbols: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
    """
    Load all stored parquet files into a dict {symbol: DataFrame}.
    Used by Phase 2 feature pipeline.
    """
    manifest = _load_manifest()
    target = symbols or list(manifest.keys())
    out: Dict[str, pd.DataFrame] = {}
    for sym in target:
        df = load_parquet(sym)
        if not df.empty:
            out[sym] = df
    return out


# ─── CLI ─────────────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 1A — OHLCV Data Store for Top 200 VN Stocks"
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument("--backfill",  action="store_true", help=f"Full backfill from {BACKFILL_START}")
    group.add_argument("--update",    action="store_true", help="Incremental update only")
    group.add_argument("--check",     action="store_true", help="Show manifest status, no fetch")
    p.add_argument("--top",     type=int, default=TOP_N,           help=f"Number of symbols (default {TOP_N})")
    p.add_argument("--start",   type=str, default=BACKFILL_START,  help="Backfill start date (YYYY-MM-DD)")
    p.add_argument("--symbols", type=str, default="",              help="Comma-separated symbol override")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.check:
        show_status()
        sys.exit(0)

    symbols_override = None
    if args.symbols:
        symbols_override = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    if args.backfill:
        mode = "backfill"
    elif args.update:
        mode = "incremental"
    else:
        mode = "auto"

    run(
        mode=mode,
        top_n=args.top,
        backfill_start=args.start,
        symbols_override=symbols_override,
    )
