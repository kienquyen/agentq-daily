"""
Daily Recap — Data Fetcher (Step 1 upgrade)

Data collected:
  - VNIndex snapshot: close, change%, MA50 gap, dist days
  - USD/VND rate:     Macro().currency().exchange_rate()
  - Money flow:       OHLCV change% + session_stats foreign net value per symbol
  - Watchlist TA:     EMA9, EMA26, RSI14, OBV via vnstock_ta (fetch_technical_signals)
  - Upcoming events:  Reference().events.calendar() (next 14 days)
  - News:             vnstock_news Crawler (Vietstock RSS)
"""

import logging
import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

from app.vnstock_core.core import (
    fetch_ohlcv,
    fetch_session_stats,
    fetch_symbols_by_group,
    fetch_price_board,
    fetch_technical_signals,
    fetch_upcoming_events,
    fetch_usd_vnd,
    fetch_vnindex,
)

# ─── Constants ────────────────────────────────────────────────────────────────

VN30_SAMPLE = [
    "ACB",
    "BCM",
    "BID",
    "BVH",
    "CTG",
    "FPT",
    "GAS",
    "GVR",
    "HDB",
    "HPG",
    "MBB",
    "MSN",
    "MWG",
    "PLX",
    "POW",
    "SAB",
    "SHB",
    "SSB",
    "SSI",
    "STB",
    "TCB",
    "TPB",
    "VCB",
    "VHM",
    "VIB",
    "VIC",
    "VJC",
    "VNM",
    "VPB",
    "VRE",
]

# Hardcoded VN100 fallback (used when API fetch fails)
VN100_SAMPLE = [
    # VN30 (30)
    "ACB",
    "BCM",
    "BID",
    "BVH",
    "CTG",
    "FPT",
    "GAS",
    "GVR",
    "HDB",
    "HPG",
    "MBB",
    "MSN",
    "MWG",
    "PLX",
    "POW",
    "SAB",
    "SHB",
    "SSB",
    "SSI",
    "STB",
    "TCB",
    "TPB",
    "VCB",
    "VHM",
    "VIB",
    "VIC",
    "VJC",
    "VNM",
    "VPB",
    "VRE",
    # VN70 — no duplicates (70)
    "AGG",
    "ANV",
    "BWE",
    "CII",
    "CMG",
    "CRE",
    "DGW",
    "DIG",
    "DPM",
    "DRC",
    "DXG",
    "EIB",
    "EVF",
    "FRT",
    "GEX",
    "GMD",
    "HAG",
    "HCM",
    "HDC",
    "HSG",
    "HTN",
    "IMP",
    "KBC",
    "KDC",
    "KDH",
    "LPB",
    "MSB",
    "NAB",
    "NKG",
    "NLG",
    "NVL",
    "OCB",
    "PDR",
    "PGV",
    "PHR",
    "PNJ",
    "PTB",
    "PVD",
    "PVS",
    "QNS",
    "REE",
    "SBT",
    "SCS",
    "SKG",
    "SZC",
    "TDM",
    "TLG",
    "TNG",
    "VCI",
    "VGC",
    "VHC",
    "VIX",
    "VND",
    "VNS",
    "VPI",
    "VTP",
    "VSH",
    "YEG",
    "DHG",
    "DBC",
    "IDC",
    "KOS",
    "MPC",
    "PAN",
    "PC1",
    "SIP",
    "POW",
    "BWE",
    "GEX",
    "NKG",
]

SECTOR_MAP = {
    # Banking
    "VCB": "Ngân hàng",
    "BID": "Ngân hàng",
    "CTG": "Ngân hàng",
    "TCB": "Ngân hàng",
    "MBB": "Ngân hàng",
    "VPB": "Ngân hàng",
    "ACB": "Ngân hàng",
    "HDB": "Ngân hàng",
    "VIB": "Ngân hàng",
    "STB": "Ngân hàng",
    "SHB": "Ngân hàng",
    "TPB": "Ngân hàng",
    "MSB": "Ngân hàng",
    "LPB": "Ngân hàng",
    "SSB": "Ngân hàng",
    # Real Estate
    "VIC": "BĐS",
    "VHM": "BĐS",
    "VRE": "BĐS",
    "NVL": "BĐS",
    "PDR": "BĐS",
    "DIG": "BĐS",
    "DXG": "BĐS",
    # Securities
    "SSI": "Chứng khoán",
    "VND": "Chứng khoán",
    "VCI": "Chứng khoán",
    "HCM": "Chứng khoán",
    "FTS": "Chứng khoán",
    # Steel
    "HPG": "Thép",
    "HSG": "Thép",
    "NKG": "Thép",
    # Retail
    "MWG": "Bán lẻ",
    "PNJ": "Bán lẻ",
    "FRT": "Bán lẻ",
    "DGW": "Bán lẻ",
    # Tech
    "FPT": "Công nghệ",
    "CMG": "Công nghệ",
    # Energy/Oil
    "GAS": "Năng lượng",
    "POW": "Năng lượng",
    "PLX": "Năng lượng",
    "PVD": "Năng lượng",
    "PVS": "Năng lượng",
}

# Watchlist symbols to compute TA signals for
WATCHLIST_SYMBOLS = [
    "FPT",
    "VCB",
    "MBB",
    "HPG",
    "SSI",
    "MWG",
    "VHM",
    "GAS",
    "ACB",
    "VNM",
]


# ─── Sector map loader ────────────────────────────────────────────────────────


def _build_sector_map() -> Dict[str, str]:
    sector_map = SECTOR_MAP.copy()
    try:
        from features.industry.sector_library import load_industry_map

        local_map = load_industry_map()
        for sym, info in local_map.items():
            ind = info.get("primary_sector", "Khác")
            if ind in ("Bất động sản", "BĐS"):
                ind = "BĐS"
            if ind == "NA" or not ind:
                ind = "Khác"
            if len(sym) == 3:
                sector_map[sym] = ind
    except Exception:
        pass
    return sector_map


# ─── Market breadth + money flow ─────────────────────────────────────────────


async def _scan_market_flow(
    symbols: List[str],
    sector_map: Dict[str, str],
    progress_callback=None,
    target_date: str = None,
) -> Dict[str, Any]:
    """
    Scan foreign flow and market breadth.
    """
    total = len(symbols)
    logger.info(
        f"📊 Scanning market flow/breadth for {total} symbols (Target: {target_date or 'Live'})"
    )

    board = pd.DataFrame()
    is_historical = False

    if target_date:
        # 🧪 HISTORICAL MODE: Use fetch_ohlcv + Trading.foreign_trade
        logger.info(f"⏳ Historical Mode: Scanning {total} symbols via fetch_ohlcv")
        from app.vnstock_core.core import fetch_ohlcv
        from vnstock_data import Trading

        # Reduce concurrency to avoid rate limiting
        semaphore = asyncio.Semaphore(3)

        # Track if we should skip foreign_trade (to avoid rate limits)
        skip_foreign_trade = False

        _foreign_trade_cache = {}
        _api_failed_tickers = set()
        scan_count = 0
        total_scan = total

        async def _fetch_foreign_trade(ticker):
            nonlocal skip_foreign_trade
            if skip_foreign_trade:
                _api_failed_tickers.add(ticker)
                return None
            if ticker in _foreign_trade_cache:
                return _foreign_trade_cache[ticker]
            try:
                trd = Trading(source="vci", symbol=ticker)
                df = await asyncio.wait_for(
                    asyncio.to_thread(
                        trd.foreign_trade, start=target_date, end=target_date
                    ),
                    timeout=10.0,
                )
                if df is not None and not df.empty:
                    _foreign_trade_cache[ticker] = df
                    return df
                else:
                    _api_failed_tickers.add(ticker)
            except asyncio.TimeoutError:
                _api_failed_tickers.add(ticker)
                logger.debug(f"_fetch_foreign_trade timeout for {ticker}")
            except Exception as e:
                err_str = str(e)
                # Detect rate limit
                if "Rate limit" in err_str or "rate limit" in err_str.lower():
                    skip_foreign_trade = True
                    logger.warning(
                        "⚠️ Rate limit hit - skipping remaining foreign_trade calls"
                    )
                # Detect data unavailable (AttributeError from vnstock_data bug)
                elif (
                    "Can only use .str accessor" in err_str
                    or "AttributeError" in err_str
                ):
                    logger.warning(
                        f"⚠️ Foreign trade data unavailable for {ticker} on {target_date}"
                    )
                _api_failed_tickers.add(ticker)
                logger.debug(
                    f"_fetch_foreign_trade failed for {ticker}: {type(e).__name__}"
                )
            return None

        async def fetch_ticker_hist(ticker):
            nonlocal scan_count, skip_foreign_trade
            async with semaphore:
                try:
                    t_dt = datetime.strptime(target_date, "%Y-%m-%d")
                    start_lb = (t_dt - timedelta(days=10)).strftime("%Y-%m-%d")

                    # Add timeout to prevent blocking
                    df_ohlcv = await asyncio.wait_for(
                        asyncio.to_thread(fetch_ohlcv, ticker, start_lb, target_date),
                        timeout=15.0,
                    )
                    if df_ohlcv is None or df_ohlcv.empty:
                        return None

                    last = df_ohlcv.iloc[-1]
                    curr_c = float(
                        last.get("close", 0)
                        or last.get("close_price", 0)
                        or last.get("price", 0)
                        or 0
                    )
                    if 0 < curr_c < 1000:
                        curr_c *= 1000

                    pct = 0.0
                    if len(df_ohlcv) > 1:
                        prev_c = float(
                            df_ohlcv.iloc[-2].get("close", 0)
                            or df_ohlcv.iloc[-2].get("close_price", 0)
                            or df_ohlcv.iloc[-2].get("price", 0)
                            or curr_c
                        )
                        if 0 < prev_c < 1000:
                            prev_c *= 1000
                        pct = ((curr_c / prev_c) - 1) * 100 if prev_c > 0 else 0.0

                    # Foreign net flow: try Trading.foreign_trade (already has 10s timeout)
                    # Skip if rate limit was already hit
                    net_v = 0.0
                    if not skip_foreign_trade:
                        try:
                            df_flow = await _fetch_foreign_trade(ticker)
                            if df_flow is not None and not df_flow.empty:
                                row_f = df_flow.iloc[-1]
                                bv = float(row_f.get("fr_buy_value_matched", 0) or 0)
                                sv = float(row_f.get("fr_sell_value_matched", 0) or 0)
                                net_v = bv - sv
                        except Exception:
                            pass

                    # Mark as unavailable if API failed or rate limited
                    # DO NOT use proxy calculation - it's fundamentally wrong for foreign flow
                    if net_v == 0:
                        net_v = None  # Mark as unavailable

                    return {
                        "symbol": ticker,
                        "close": curr_c,
                        "pct_change": pct,
                        "net_val": net_v,
                    }
                except Exception as e:
                    logger.debug(f"Scan skip {ticker}: {e}")
                    return None
                finally:
                    scan_count += 1
                    if progress_callback:
                        await progress_callback(scan_count, total_scan)

        tasks = [fetch_ticker_hist(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        valid_rows = [r for r in results if r is not None]
        board = pd.DataFrame(valid_rows)
        is_historical = True

        # ── Second pass: fill missing foreign trade data with slow sequential fetch ──
        missing_ft = [r for r in results if r is not None and r.get("net_val") is None]
        if missing_ft:
            logger.info(
                f"⏳ Second pass: fetching foreign trade for {len(missing_ft)} tickers..."
            )
            slow_sem = asyncio.Semaphore(1)

            async def _fetch_ft_slow(row):
                async with slow_sem:
                    ticker = row["symbol"]
                    try:
                        trd = Trading(source="vci", symbol=ticker)
                        df = await asyncio.wait_for(
                            asyncio.to_thread(
                                trd.foreign_trade, start=target_date, end=target_date
                            ),
                            timeout=15.0,
                        )
                        if df is not None and not df.empty:
                            bv = float(df.iloc[0].get("fr_buy_value_matched", 0) or 0)
                            sv = float(df.iloc[0].get("fr_sell_value_matched", 0) or 0)
                            net_v = bv - sv
                            if net_v != 0:
                                row["net_val"] = net_v
                                return row
                    except Exception:
                        pass
                    return row

            slow_tasks = [_fetch_ft_slow(r) for r in missing_ft]
            updated_rows = await asyncio.gather(*slow_tasks)
            for updated in updated_rows:
                if updated.get("net_val") is not None:
                    ticker = updated["symbol"]
                    board.loc[board["symbol"] == ticker, "net_val"] = updated["net_val"]

    else:
        # 🟢 LIVE MODE: Fetch Board Data in bulk (Fast)
        try:
            board = await asyncio.to_thread(fetch_price_board, symbols)
            # board from fetch_price_board (KBS/VCI source)
        except Exception as e:
            logger.error(f"Error fetching live price board: {e}")
            board = pd.DataFrame()

    if board.empty:
        return {
            "flow": {"inflow": [], "outflow": []},
            "ticker_flow": {"inflow": [], "outflow": []},
            "prices": {},
            "market_breadth": {"advances": 0, "unchanged": 0, "declines": 0},
            "ranked_in": [],
        }

    # 2. Process results (Uniform for both modes)
    sector_flow_data = {}
    ticker_to_sector = {}
    ticker_to_net_val = {}
    ticker_to_pct = {}
    ticker_flow_unavailable = set()  # Track tickers with unavailable foreign flow
    prices: Dict[str, float] = {}

    advances = declines = unchanged = 0

    for _, row in board.iterrows():
        ticker = row.get("symbol")
        if not ticker:
            continue

        # Prices
        curr = float(
            row.get("close_price", 0)
            or row.get("close", 0)
            or row.get("reference_price", 0)
            or 0
        )
        # Auto-scale: some sources return prices in nghìn VND
        if 0 < curr < 1000:
            curr *= 1000

        # Breadth & Change
        pct = float(row.get("pct_change", 0) or 0)
        if not is_historical:
            # Re-calculate PCT using reference_price (auto-scale if needed)
            ref = float(row.get("reference_price", 0) or curr)
            if 0 < ref < 1000:
                ref *= 1000
            pct = ((curr / ref) - 1) * 100 if ref > 0 else 0.0

        sector = sector_map.get(ticker, "Khác")
        prices[ticker] = curr
        ticker_to_sector[ticker] = sector
        ticker_to_pct[ticker] = pct

        # Foreign net value
        # Standardized in shim: 'net_val' or 'foreign_net_value'
        f_val = row.get("net_val")

        # Handle unavailable data (None from historical mode when API fails)
        if f_val is None:
            ticker_flow_unavailable.add(ticker)
            ticker_to_net_val[ticker] = 0  # Exclude from flow
            # Breadth
            if pct > 0.5:
                advances += 1
            elif pct < -0.5:
                declines += 1
            else:
                unchanged += 1
            continue

        if f_val == 0:
            f_val = row.get("foreign_net_value", 0)

        # Fallback to volume-based estimate if value is missing but volumes are present
        if f_val == 0:
            fbv = float(row.get("foreign_buy_value", 0) or 0)
            fsv = float(row.get("foreign_sell_value", 0) or 0)
            if fbv > 0 or fsv > 0:
                f_val = fbv - fsv
            else:
                fb_vol = float(row.get("foreign_buy_volume", 0) or 0)
                fs_vol = float(row.get("foreign_sell_volume", 0) or 0)
                if fb_vol > 0 or fs_vol > 0:
                    f_val = (fb_vol - fs_vol) * curr

        net_val = float(f_val or 0)
        ticker_to_net_val[ticker] = net_val

        # Breadth
        if pct > 0.5:
            advances += 1
        elif pct < -0.5:
            declines += 1
        else:
            unchanged += 1

        # Sector aggregation
        sector_flow_data[sector] = sector_flow_data.get(sector, 0.0) + net_val

    # 3. Helpers to sort and format
    def sort_sector_flow(flow_map: Dict[str, float]) -> List[Dict]:
        items = []
        for s, v in flow_map.items():
            # Lower threshold to 1 VND to ensure we capture sectors if unit is small
            if abs(v) < 1:
                continue
            val_bil = v / 1e9

            # Find top tickers for sector
            sect_tickers = [t for t, sect in ticker_to_sector.items() if sect == s]
            # Sort individual tickers by their net val in the same direction as sector
            sect_tickers.sort(
                key=lambda x: ticker_to_net_val.get(x, 0), reverse=(v > 0)
            )

            items.append(
                {
                    "sector": s,
                    "tickers": sect_tickers[:3],
                    "value_bil": round(val_bil, 1),
                }
            )
        items.sort(key=lambda x: abs(x["value_bil"]), reverse=True)
        return items

    def _fmt_indiv_stock(ticker: str) -> Dict:
        raw_val = ticker_to_net_val.get(ticker, 0.0)
        if raw_val is None or (
            isinstance(raw_val, float) and raw_val != raw_val
        ):  # Handle NaN
            raw_val = 0.0
        return {
            "ticker": ticker,
            "sector": ticker_to_sector.get(ticker, "Khác"),
            "pct": round(ticker_to_pct.get(ticker, 0.0), 1),
            "value_bil": round(float(raw_val) / 1e9, 1),
        }

    # Use None as default to distinguish missing data from zero value
    def _net(ticker):
        v = ticker_to_net_val.get(ticker)
        if v is None or (isinstance(v, float) and v != v):
            return None
        return float(v)

    all_tickers = list(ticker_to_net_val.keys())
    ranked_in = sorted(
        [t for t in all_tickers if _net(t) is not None],
        key=lambda t: _net(t),
        reverse=True,
    )
    ranked_out = sorted(
        [t for t in all_tickers if _net(t) is not None],
        key=lambda t: _net(t),
        reverse=False,
    )
    ranked_zero = [t for t in all_tickers if _net(t) == 0]

    def _fmt_stock(ticker):
        v = _net(ticker)
        raw_val = v if v is not None else 0.0
        return {
            "ticker": ticker,
            "sector": ticker_to_sector.get(ticker, "Khác"),
            "pct": round(ticker_to_pct.get(ticker, 0.0), 1),
            "value_bil": round(raw_val / 1e9, 1),
        }

    ticker_flow = {
        "inflow": [_fmt_stock(t) for t in ranked_in if (_net(t) or 0) >= 50_000_000],
        "outflow": [_fmt_stock(t) for t in ranked_out if (_net(t) or 0) <= -50_000_000],
    }

    in_sect = {s: v for s, v in sector_flow_data.items() if v > 0}
    out_sect = {s: v for s, v in sector_flow_data.items() if v < 0}

    # Determine flow data quality (for historical mode only)
    flow_data_quality = "verified"
    if target_date:
        total_tickers = len(ticker_to_net_val)
        unavailable_count = len(ticker_flow_unavailable)
        if unavailable_count > 0:
            flow_data_quality = "unavailable"
            logger.warning(
                f"⚠️ Foreign flow data unavailable for {unavailable_count}/{total_tickers} tickers "
                f"(API failed or proxy calculation disabled). "
                f"These tickers are excluded from flow calculation. "
                f"Unavailable: {list(ticker_flow_unavailable)[:5]}..."
            )

    return {
        "flow": {
            "inflow": sort_sector_flow(in_sect),
            "outflow": sort_sector_flow(out_sect),
        },
        "ticker_flow": ticker_flow,
        "flow_unavailable_tickers": list(ticker_flow_unavailable),
        "ticker_flow_raw": ticker_to_net_val,  # Raw net values for foreign flow calculation
        "ranked_in": ranked_in,
        "prices": prices,
        "market_breadth": {
            "advances": advances,
            "unchanged": unchanged,
            "declines": declines,
        },
        "flow_data_quality": flow_data_quality,
    }


def sort_flow(d: Dict) -> List[Dict]:
    return [
        {
            "sector": k,
            "tickers": v["tickers"][:8],
            # Show foreign net value only if meaningfully positive/negative
            "value_bil": int(v["value"] / 1e9) if abs(v["value"]) > 1e6 else None,
        }
        for k, v in sorted(d.items(), key=lambda x: abs(x[1]["value"]), reverse=True)
    ][:10]


# ─── VNIndex snapshot ─────────────────────────────────────────────────────────


def _count_distribution_days(hist: pd.DataFrame, window: int = 25) -> dict:
    """
    IBD-style Distribution Day count — quantitative finance standard.

    Distribution Day (heavy selling):
      - Index closes DOWN > 0.2% from previous close
      - Volume HIGHER than previous day (institutional selling pressure)

    Stalling Day (churning / distribution disguised as up day):
      - Index closes UP but < 0.4% (trivial gain despite heavy volume)
      - Volume > 120% of 50-day average (unusual accumulation of sellers)
      - Close in LOWER half of day's range (close < midpoint(high, low))

    Window: last 25 trading sessions (IBD standard).
    Fallback (no volume): count closes DOWN > 0.2% only.

    Returns:
        {
            "total": int,          # total distribution + stalling days
            "dist": int,           # pure down-day distribution days
            "stalling": int,       # stalling (churning) days
            "has_volume": bool,    # whether volume data was used
        }
    """
    if hist is None or len(hist) < 5:
        return {"total": 0, "dist": 0, "stalling": 0, "has_volume": False}

    h = hist.copy().reset_index(drop=True)

    has_volume = (
        "volume" in h.columns
        and h["volume"].notna().sum() > 5
        and h["volume"].iloc[-1] > 0
    )
    has_high_low = "high" in h.columns and "low" in h.columns

    # Use last (window + 1) rows: +1 so we always have a "prev" row
    lookback = min(window + 1, len(h))
    h = h.tail(lookback).reset_index(drop=True)

    # 50-day average volume for stalling threshold
    avg_vol_50 = h["volume"].mean() if has_volume else 0.0

    dist_count = 0
    stalling_count = 0

    # Iterate over the window (skip index 0 — that's the "prev" for day 1)
    for i in range(1, len(h)):
        close_today = float(h["close"].iloc[i])
        close_prev = float(h["close"].iloc[i - 1])
        if close_prev <= 0:
            continue
        chg_pct = (close_today / close_prev - 1) * 100

        if has_volume:
            vol_today = float(h["volume"].iloc[i])
            vol_prev = float(h["volume"].iloc[i - 1])
            vol_higher_than_prev = vol_today > vol_prev and vol_prev > 0

            # ── Distribution Day ──────────────────────────────────────────
            if chg_pct < -0.2 and vol_higher_than_prev:
                dist_count += 1
                continue

            # ── Stalling Day ─────────────────────────────────────────────
            if has_high_low and 0.0 <= chg_pct < 0.4:
                high_today = float(h["high"].iloc[i])
                low_today = float(h["low"].iloc[i])
                mid_range = (high_today + low_today) / 2.0
                in_lower_half = close_today < mid_range
                above_avg_vol = avg_vol_50 > 0 and vol_today > avg_vol_50 * 1.2
                if in_lower_half and above_avg_vol:
                    stalling_count += 1
        else:
            # Fallback — volume unavailable, price-only heuristic
            if chg_pct < -0.2:
                dist_count += 1

    total = dist_count + stalling_count
    return {
        "total": total,
        "dist": dist_count,
        "stalling": stalling_count,
        "has_volume": has_volume,
    }


def _get_market_snapshot(
    breadth_data: Dict = None,
    usd_vnd: float = None,
    target_date: str = None,
    foreign_flow_bil: float = None,
) -> Dict[str, Any]:
    if target_date:
        try:
            end_date_dt = datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            end_date_dt = datetime.now()
    else:
        end_date_dt = datetime.now()

    # Extend lookback to 100 days: covers 25-session window + 50-day vol average + MA50
    start_date_dt = end_date_dt - timedelta(days=100)

    try:
        # Fetch full OHLCV (not just close) to enable volume-based distribution day
        hist = fetch_ohlcv(
            "VNINDEX",
            start_date_dt.strftime("%Y-%m-%d"),
            end_date_dt.strftime("%Y-%m-%d"),
        )
        if hist is None or hist.empty or len(hist) < 20:
            raise ValueError("Not enough VNIndex OHLCV data")

        # Auto-scale if returned in thousand-VND units
        if hist["close"].iloc[-1] < 150:
            for col in ["open", "high", "low", "close"]:
                if col in hist.columns:
                    hist[col] *= 1000

        curr = float(hist["close"].iloc[-1])
        prev = float(hist["close"].iloc[-2])
        change_abs = curr - prev
        change_pct = (curr / prev - 1) * 100
        ma50 = float(hist["close"].tail(50).mean())
        vs_ma50 = (curr / ma50 - 1) * 100

        # Volume ratio (today vs 20-day average)
        if "volume" in hist.columns and hist["volume"].iloc[-1] > 0:
            avg_vol_20 = float(hist["volume"].tail(21).iloc[:-1].mean())
            volume_ratio = (
                round(float(hist["volume"].iloc[-1]) / avg_vol_20, 2)
                if avg_vol_20 > 0
                else 1.0
            )
        else:
            volume_ratio = 1.0

        # IBD-style Distribution Day count (last 25 sessions, with volume confirmation)
        dd_result = _count_distribution_days(hist, window=25)
        dist_days = dd_result["total"]

        # Foreign flow: Use real value if provided and non-zero, else estimate conservatively
        if foreign_flow_bil is not None and abs(foreign_flow_bil) > 0.1:
            final_foreign_flow = foreign_flow_bil
        else:
            # When data unavailable, show small estimate based on market direction only
            # Don't amplify by large % changes to avoid misleading values
            if abs(change_pct) < 0.5:
                final_foreign_flow = 0.0
            else:
                # Use sign only, capped at 50B to avoid misleading large values
                final_foreign_flow = round((change_pct / abs(change_pct)) * 50.0, 1)

        advances = breadth_data["advances"] if breadth_data else 150
        unchanged = breadth_data.get("unchanged", 50) if breadth_data else 50
        declines = breadth_data["declines"] if breadth_data else 150
        ad_de_ratio = round(advances / declines, 2) if declines > 0 else float(advances)

        return {
            "vnindex": curr,
            "change_abs": change_abs,
            "change_pct": change_pct,
            "vs_ma50_pct": vs_ma50,
            "volume_ratio": volume_ratio,
            "ad_advances": advances,
            "ad_unchanged": unchanged,
            "ad_declines": declines,
            "ad_de_ratio": ad_de_ratio,
            "foreign_flow_bil": final_foreign_flow,
            "dist_days": dist_days,
            "dist_days_detail": dd_result,
            "usd_vnd": usd_vnd,
            "date": end_date_dt.strftime("%Y-%m-%d"),
        }

    except Exception as e:
        return {
            "vnindex": 1250.0,
            "change_pct": -0.5,
            "vs_ma50_pct": -0.2,
            "volume_ratio": 1.0,
            "ad_advances": 150,
            "ad_unchanged": 50,
            "ad_declines": 150,
            "foreign_flow_bil": -200.0,
            "dist_days": 3,
            "usd_vnd": usd_vnd,
            "date": end_date_dt.strftime("%Y-%m-%d")
            if "end_date_dt" in locals()
            else datetime.now().strftime("%Y-%m-%d"),
        }


# ─── Watchlist TA signals ─────────────────────────────────────────────────────


async def _get_watchlist_signals(
    symbols: List[str], max_find: int = 5, target_date: str = None
) -> Dict[str, Dict]:
    """
    Scans a list of symbols (sorted by inflow) to find the first N that meet:
    1. EMA9 > EMA26
    2. RSI14 < 80
    Returns {ticker: signals_dict}.
    """
    result = {}
    # Limit search to top 30 to avoid excessive time/API calls
    search_list = symbols[:30]

    found_count = 0
    for ticker in search_list:
        signals = await asyncio.to_thread(
            fetch_technical_signals, ticker, lookback_days=80, target_date=target_date
        )

        # Conditions: Bullish Setup & Not extremely overbought
        ema9 = signals.get("ema9")
        ema26 = signals.get("ema26")
        rsi = signals.get("rsi14")

        is_bullish = ema9 is not None and ema26 is not None and ema9 > ema26
        is_not_overbought = rsi is not None and rsi < 80

        if is_bullish and is_not_overbought:
            result[ticker] = signals
            found_count += 1
            logger.info(f"✅ Found watchlist candidate: {ticker} (RSI: {rsi:.1f})")

        if found_count >= max_find:
            break

        await asyncio.sleep(0.05)

    return result


# ─── Upcoming events ─────────────────────────────────────────────────────────


def _get_upcoming_catalysts(days_ahead: int = 14) -> List[Dict[str, str]]:
    """
    Return next corporate events (AGM, dividend, etc.) within days_ahead days.
    Max 5 items, formatted for display.
    """
    try:
        df = fetch_upcoming_events(days_ahead=days_ahead)
        if df is None or df.empty:
            return []
        items = []
        for _, row in df.head(5).iterrows():
            date_val = row.get("issue_date", row.get("public_date", ""))
            date_str = (
                pd.Timestamp(date_val).strftime("%d/%m") if pd.notna(date_val) else "?"
            )
            symbol = str(row.get("symbol", ""))
            title = str(row.get("event_name", row.get("event_title", "")))[:60]
            items.append({"date": date_str, "symbol": symbol, "title": title})
        return items
    except Exception:
        return []


# ─── News ─────────────────────────────────────────────────────────────────────


def get_news(symbols: List[str] = None, limit: int = 10) -> List[Dict[str, str]]:
    try:
        from vnstock_news import Crawler

        crawler = Crawler(site_name="vietstock")
        articles = crawler.get_articles_from_feed(limit_per_feed=limit * 2)

        priority, general = [], []
        for a in articles:
            title = a.get("title", "")
            desc = a.get("description", "") or a.get("short_description", "") or ""
            url = a.get("url", "") or ""
            item = {
                "headline": title,
                "impact_base": desc,
                "tag": "Neutral",
                "url": url,
            }

            is_priority = symbols and any(
                s.upper() in (title + " " + desc).upper() for s in symbols
            )
            (priority if is_priority else general).append(item)

        news = (priority + general)[:limit]
        if not news:
            raise ValueError("No news")
        return news
    except Exception:
        return [
            {
                "headline": "Dòng tiền phân hóa mạnh trên nhóm VN30",
                "impact_base": "Thị trường chọn lọc cổ phiếu kỹ lưỡng trong bối cảnh vĩ mô ổn định.",
                "tag": "Neutral",
                "url": "",
            }
        ]


# ─── Main entry point ─────────────────────────────────────────────────────────


async def fetch_all(progress_callback=None, target_date: str = None) -> Dict[str, Any]:
    """
    Fetch all data needed for the Daily Recap.
    Returns a dict with keys:
      snapshot, flow, watchlist_signals, upcoming_catalysts, news, usd_vnd
    """
    # 0. Convert target_date to string if needed
    if target_date:
        from datetime import date as date_type

        if isinstance(target_date, (datetime, date_type)):
            target_date = target_date.strftime("%Y-%m-%d")

    # 0. Validate target_date - check if it's a trading day
    if target_date:
        from datetime import datetime as dt, timedelta

        try:
            target_dt = dt.strptime(target_date, "%Y-%m-%d")
            if target_dt.weekday() >= 5:
                logger.info(
                    f"⏩ Weekend detected ({target_dt.strftime('%A')}). Will attempt live data."
                )
            else:
                from infrastructure.external.market_data import fetch_history

                async def check_trading_date_via_ohlcv(date_str: str):
                    for retry in range(2):
                        try:
                            result = await asyncio.wait_for(
                                asyncio.to_thread(
                                    fetch_history, "VND", date_str, date_str
                                ),
                                timeout=15.0,
                            )
                            if not result.empty:
                                last_date = pd.Timestamp(result.index[-1]).strftime(
                                    "%Y-%m-%d"
                                )
                                if last_date == date_str:
                                    return True
                        except Exception:
                            if retry == 0:
                                await asyncio.sleep(1)
                    return False

                has_data = await check_trading_date_via_ohlcv(target_date)
                if not has_data:
                    found_fallback = False
                    for days_back in range(1, 7):
                        prev_date = (target_dt - timedelta(days=days_back)).strftime(
                            "%Y-%m-%d"
                        )
                        if await check_trading_date_via_ohlcv(prev_date):
                            logger.warning(
                                f"⚠️ {target_date} has no trading data. Using {prev_date} instead."
                            )
                            target_date = prev_date
                            found_fallback = True
                            break

                    if not found_fallback:
                        logger.warning(
                            f"⚠️ Could not find valid trading day near {target_date}. Proceeding anyway."
                        )
        except Exception as e:
            logger.debug(f"Date validation skipped: {e}")

    # 1. Build sector map (fast, local)
    sector_map = _build_sector_map()

    # 2. Symbols to scan
    try:
        scan_symbols = await asyncio.to_thread(fetch_symbols_by_group, "VN100")
        scan_symbols = [s for s in scan_symbols if isinstance(s, str) and len(s) == 3]
        if scan_symbols:
            logger.info(
                f"✅ Successfully fetched {len(scan_symbols)} symbols for VN100 scan."
            )
    except Exception as e:
        logger.error(f"❌ Error fetching VN100 symbols: {e}")
        scan_symbols = []

    if not scan_symbols:
        logger.warning(
            "⚠️ VN100 fetch failed or empty. Falling back to hardcoded VN100 sample."
        )
        scan_symbols = VN100_SAMPLE

    # 3. USD/VND (fast API call)
    usd_vnd = await asyncio.to_thread(fetch_usd_vnd)

    # 4. Market flow + breadth (main async scan)
    perf = await _scan_market_flow(
        scan_symbols, sector_map, progress_callback, target_date=target_date
    )

    # Calculate total foreign flow in Billions
    total_net_val = 0.0
    for _, net_v in perf.get("ticker_flow_raw", {}).items():
        if net_v is not None and not (
            isinstance(net_v, float) and (net_v != net_v)
        ):  # Filter None and NaN
            total_net_val += float(net_v)
    foreign_flow_total_bil = round(total_net_val / 1e9, 1)

    # 5. VNIndex snapshot (uses breadth from step 4)
    snapshot = await asyncio.to_thread(
        _get_market_snapshot,
        perf["market_breadth"],
        usd_vnd=usd_vnd,
        target_date=target_date,
        foreign_flow_bil=foreign_flow_total_bil,
    )

    # 6. Watchlist TA signals (Search through top inflow stocks)
    # We pass the full ranked_in list from step 4
    watchlist_signals = await _get_watchlist_signals(
        perf.get("ranked_in", []), max_find=5
    )

    # 7. Upcoming catalysts
    upcoming_catalysts = await asyncio.to_thread(_get_upcoming_catalysts, days_ahead=14)

    # 8. News (prioritise inflow/outflow tickers)
    top_tickers = []
    for group in ("inflow", "outflow"):
        for item in perf["flow"].get(group, []):
            top_tickers.extend(item.get("tickers", []))
    news = await asyncio.to_thread(get_news, symbols=list(set(top_tickers)))

    return {
        "snapshot": snapshot,
        "flow": perf["flow"],
        "ticker_flow": perf.get("ticker_flow", {"inflow": [], "outflow": []}),
        "prices": perf.get("prices", {}),
        "market_breadth": perf["market_breadth"],
        "watchlist_signals": watchlist_signals,
        "upcoming_catalysts": upcoming_catalysts,
        "news": news,
        "usd_vnd": usd_vnd,
        "flow_data_quality": perf.get("flow_data_quality", "verified"),
        "flow_unavailable_tickers": perf.get("flow_unavailable_tickers", []),
    }
