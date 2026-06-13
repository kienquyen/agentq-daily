"""
VNStock Core — Centralized data access layer using vnstock_data Unified UI (v3.0.0+).

All price data:     Market().equity(symbol).ohlcv(...)
                    Market().index(symbol).ohlcv(...)   ← for VNINDEX
All financials:     Fundamental().equity(symbol).income_statement(period="Q")
                                             .balance_sheet(period="Q")
                                             .cash_flow(period="Q")
                                             .ratio()
                    Falls back to free vnstock (VCI source) if KBS is unavailable.
Listing:            Reference().equity.list()
                    Reference().equity.list_by_group(group)
Price board:        Market().quote(symbols_list)

Single import point for the entire project — no feature module should import
vnstock_data directly. Go through here instead.

Normalized financial data format (source-agnostic):
    All financial DataFrames use standard column names regardless of source:
      income_statement: period, nii, fee_income, provision, net_profit,
                        revenue, gross_profit, op_profit
      balance_sheet:    period, total_assets, equity, deposits, loans,
                        current_liabilities, long_term_liabilities
      cash_flow:        period, operating_cf, investing_cf, financing_cf, net_cf
      ratio:            period, pe, pb, eps, roe, roa
    All monetary values are normalized to raw VND (÷ 1e12 = nghìn tỷ VND).
    Ratios (pe, pb, roe, roa) are in standard units (%, e.g. roe=17.5).
"""

import sys
import os

# Remove any rogue site-packages/asyncio that shadows the stdlib asyncio.
sys.path = [p for p in sys.path if not p.endswith("site-packages/asyncio")]

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)
logging.getLogger("vnstock").setLevel(logging.WARNING)
logging.getLogger("vnai").setLevel(logging.WARNING)


# ─── Import guard: project-local vnstock_data is used directly (vendored) ─────
def _fix_vnstock_path() -> None:
    pass


# ─── Config ──────────────────────────────────────────────────────────────────
VNINDEX_SYMBOL = "VNINDEX"

VN_PRICE_AUTOSCALE = os.environ.get("VN_PRICE_AUTOSCALE", "1").lower() not in (
    "0",
    "false",
)
VN_PRICE_SCALE = float(os.environ.get("VN_PRICE_THOUSAND_SCALE", "1000"))


# ─── Internal helpers ────────────────────────────────────────────────────────


def _default_dates(days_back: int = 30) -> Tuple[str, str]:
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    return start, end


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize any OHLCV DataFrame.
    Guarantees 'time' and 'close' columns; preserves other OHLCV columns
    (open, high, low, volume) when present.
    """
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]

    for col in ("time", "date", "tradingdate", "trading_date"):
        if col in df.columns:
            df["time"] = pd.to_datetime(df[col], errors="coerce").dt.normalize()
            break
    else:
        return pd.DataFrame()

    if "close" not in df.columns:
        if "closeprice" in df.columns:
            df["close"] = df["closeprice"]
        else:
            return pd.DataFrame()

    # Map volume aliases to 'volume'
    volume_aliases = ("volume", "matched_volume", "total_volume", "vol")
    for alias in volume_aliases:
        if alias in df.columns and "volume" not in df.columns:
            df["volume"] = df[alias]
            break

    # Keep all recognised OHLCV columns that exist
    keep = ["time", "close"]
    for extra in ("open", "high", "low", "volume"):
        if extra in df.columns:
            keep.append(extra)

    out = df[keep].copy()
    for num_col in keep[1:]:  # skip 'time'
        out[num_col] = pd.to_numeric(out[num_col], errors="coerce")
    out = (
        out.dropna(subset=["time", "close"])
        .drop_duplicates(subset=["time"], keep="last")
        .sort_values("time")
        .reset_index(drop=True)
    )
    return out


def _scale_vnd(price: float) -> float:
    """Auto-scale price from thousand-VND to VND when data is in 1–999 range."""
    if not VN_PRICE_AUTOSCALE:
        return float(price)
    p = float(price)
    if 1.0 <= p < 1000.0:
        return p * VN_PRICE_SCALE
    return p


# ─── Price Data  (Unified UI: Trading) ───────────────────────────────────────

_TRADING_API = None
_MARKET_API = None


def _get_market():
    """Return a vnstock_data Market instance."""
    global _MARKET_API
    if _MARKET_API is None:
        _fix_vnstock_path()
        from vnstock_data import Market

        _MARKET_API = Market()
    return _MARKET_API


def _get_trading():
    global _TRADING_API
    if _TRADING_API is None:
        _fix_vnstock_path()
        from vnstock_data import Trading

        _TRADING_API = Trading(source="vci", symbol="VND")
    return _TRADING_API


def fetch_ohlcv(
    symbol: str,
    start: str,
    end: str,
    interval: str = "1D",
) -> pd.DataFrame:
    """
    Fetch OHLCV via vnstock_data.
    Prioritizes stable mkt.history() then falls back to Unified UI equity().ohlcv().
    """
    symbol = (symbol or "").strip().upper()
    sources = [
        ("kbs", _fetch_ohlcv_kbs),
        ("vci", _fetch_ohlcv_vci),
        ("vnstock_vci", _fetch_ohlcv_vnstock_vci),
    ]

    try:
        for src_name, fetch_fn in sources:
            try:
                df = fetch_fn(symbol, start, end, interval)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    if _df_has_recent_data(df, end):
                        return df
            except Exception:
                pass
        return pd.DataFrame()
    except Exception as e:
        logger.warning("fetch_ohlcv(%s): %s", symbol, e)
        return pd.DataFrame()


def _df_has_recent_data(df: pd.DataFrame, end_date: str) -> bool:
    """Check if df's last date matches requested end_date (strict)."""
    if df.empty or "time" not in df.columns:
        return False
    last_date = pd.Timestamp(df["time"].iloc[-1])
    target = pd.Timestamp(end_date)
    return last_date == target


def _fetch_ohlcv_kbs(symbol, start, end, interval):
    from vnstock import Quote

    q = Quote(symbol=symbol, source="kbs")
    df = q.history(start=start, end=end, interval=interval)
    return _normalize_ohlcv(df)


def _fetch_ohlcv_vci(symbol, start, end, interval):
    from vnstock import Quote

    q = Quote(symbol=symbol, source="vci")
    df = q.history(start=start, end=end, interval=interval)
    return _normalize_ohlcv(df)


def _fetch_ohlcv_vnstock_vci(symbol, start, end, interval):
    from vnstock_data import Trading

    td = Trading(source="vci", symbol=symbol)
    df = td.price_history(start=start, end=end)
    return _normalize_ohlcv(df)


def fetch_close_series(
    symbol: str,
    start: str,
    end: str,
    interval: str = "1D",
) -> pd.Series:
    """Return close price as a time-indexed pd.Series."""
    df = fetch_ohlcv(symbol, start, end, interval)
    if df.empty:
        for days_back in range(1, 8):
            prev = (pd.Timestamp(end) - pd.Timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )
            df = fetch_ohlcv(symbol, start, prev, interval)
            if not df.empty:
                break
    if df.empty:
        return pd.Series(dtype=float, name=symbol)
    return df.set_index("time")["close"].rename(symbol)


def fetch_last_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Fetch the latest closing price (in VND) for each symbol.
    Used by portfolio tracker.
    """
    out: Dict[str, float] = {}
    if not symbols:
        return out

    start, end = _default_dates(days_back=25)
    for raw in symbols:
        sym = (raw or "").strip().upper()
        out[sym] = 0.0
        try:
            df = fetch_ohlcv(sym, start, end)
            if df.empty:
                for days_back in range(1, 8):
                    prev = (pd.Timestamp(end) - pd.Timedelta(days=days_back)).strftime(
                        "%Y-%m-%d"
                    )
                    df = fetch_ohlcv(sym, start, prev)
                    if not df.empty:
                        break
            if not df.empty:
                out[sym] = _scale_vnd(float(df["close"].iloc[-1]))
        except Exception:
            pass
    return out


def fetch_prices_map(
    symbols: List[str],
    lookback_days: int = 420,
) -> Dict[str, pd.Series]:
    """Return {symbol: close_series} for multiple symbols."""
    start, end = _default_dates(days_back=lookback_days + 30)
    out: Dict[str, pd.Series] = {}
    for raw in symbols:
        sym = (raw or "").strip().upper()
        s = fetch_close_series(sym, start, end)
        if not s.empty:
            out[sym] = s
    return out


def fetch_returns_map(
    symbols: List[str],
    lookback_days: int = 420,
) -> Dict[str, pd.Series]:
    """Return {symbol: daily_returns_series} for multiple symbols."""
    prices = fetch_prices_map(symbols, lookback_days)
    return {sym: s.pct_change().dropna() for sym, s in prices.items()}


# ─── VNIndex ─────────────────────────────────────────────────────────────────


def fetch_vnindex(start: str, end: str, interval: str = "1D") -> pd.Series:
    """
    Fetch VNIndex close series.
    Prioritizes stable mkt.history() then various fallbacks.
    """
    try:
        # 1. Try free vnstock (VCI source) — HIGH PRECISION for indices
        try:
            from vnstock import Quote

            q = Quote(symbol=VNINDEX_SYMBOL, source="vci")
            df = q.history(start=start, end=end, interval=interval)
            if isinstance(df, pd.DataFrame) and not df.empty:
                dfn = _normalize_ohlcv(df)
                if not dfn.empty and dfn["close"].iloc[-1] > 100:
                    return dfn.set_index("time")["close"].rename(VNINDEX_SYMBOL)
        except:
            pass

        mkt = _get_market()
        # 2. Try stable history()
        try:
            df = mkt.history(symbol=VNINDEX_SYMBOL, start=start, end=end)
            if isinstance(df, pd.DataFrame) and not df.empty:
                dfn = _normalize_ohlcv(df)
                if not dfn.empty:
                    return dfn.set_index("time")["close"].rename(VNINDEX_SYMBOL)
        except:
            pass

        # 3. Try index().ohlcv()
        try:
            df = mkt.index(VNINDEX_SYMBOL).ohlcv(
                start=start, end=end, interval=interval
            )
            if isinstance(df, pd.DataFrame) and not df.empty:
                dfn = _normalize_ohlcv(df)
                if not dfn.empty:
                    return dfn.set_index("time")["close"].rename(VNINDEX_SYMBOL)
        except:
            pass

        # 3. Try free vnstock (VCI source) — Often higher precision for indices
        try:
            from vnstock import Quote

            q = Quote(symbol=VNINDEX_SYMBOL, source="vci")
            df = q.history(start=start, end=end, interval=interval)
            if isinstance(df, pd.DataFrame) and not df.empty:
                dfn = _normalize_ohlcv(df)
                if not dfn.empty:
                    # If this gives high precision (> 100), it's probably better than the rounded 1.x version
                    if dfn["close"].iloc[-1] > 100:
                        return dfn.set_index("time")["close"].rename(VNINDEX_SYMBOL)
        except:
            pass

        # 4. Final fallback to free vnstock (KBS source)
        try:
            from vnstock import Quote

            q = Quote(symbol=VNINDEX_SYMBOL, source="kbs")
            df = q.history(start=start, end=end, interval=interval)
            if isinstance(df, pd.DataFrame) and not df.empty:
                dfn = _normalize_ohlcv(df)
                if not dfn.empty:
                    return dfn.set_index("time")["close"].rename(VNINDEX_SYMBOL)
        except:
            pass

    except Exception as e:
        logger.warning(f"fetch_vnindex error: {e}")

    raise RuntimeError(f"Cannot fetch VNIndex ({VNINDEX_SYMBOL})")


# ─── Financial Data  (Unified UI: Fundamental) ────────────────────────────────

_FUNDAMENTAL_API = None


def _get_fundamental():
    global _FUNDAMENTAL_API
    if _FUNDAMENTAL_API is None:
        from vnstock_data import Fundamental

        _FUNDAMENTAL_API = Fundamental()
    return _FUNDAMENTAL_API


_PERIOD_MAP = {"Q": "quarter", "Y": "year", "quarter": "quarter", "year": "year"}


# ── Normalization helpers ─────────────────────────────────────────────────────


def _normalize_fundamental_income(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Fundamental().equity() income statement to short column names."""
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    rename = {
        "net_interest_income": "nii",
        "net_fee_and_commission_income": "fee_income",
        "provision_for_credit_losses": "provision",
        "net_profit_after_tax": "net_profit",
        "revenue": "revenue",
        "gross_profit": "gross_profit",
        "operating_profit": "op_profit",
        "profit_before_tax": "pbt",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    # Fallback for securities companies (net_revenue instead of revenue)
    if "revenue" not in df.columns and "net_revenue" in df.columns:
        df["revenue"] = df["net_revenue"]
    if "op_profit" not in df.columns:
        if "profit_before_tax" in df.columns:
            df["op_profit"] = df["profit_before_tax"]
        elif "pbt" in df.columns:
            df["op_profit"] = df["pbt"]
    df["_source"] = "FUNDAMENTAL"
    return df


def _normalize_fundamental_balance(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    dep_col = next((c for c in ["customer_deposits", "deposits_from_customers", "deposits_at_other_credit_institutions"] if c in df.columns), None)
    loan_col = next((c for c in ["customer_loans", "net_customer_loans", "loans_and_advances_to_customers"] if c in df.columns), None)
    rename = {
        "total_assets": "total_assets",
        "owners_equity": "equity",
    }
    if dep_col:
        rename[dep_col] = "deposits"
    if loan_col:
        rename[loan_col] = "loans"
    if "short_term_liabilities" in df.columns:
        rename["short_term_liabilities"] = "current_liabilities"
    if "long_term_liabilities" in df.columns:
        rename["long_term_liabilities"] = "long_term_liabilities"
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if "equity" not in df.columns and "total_assets" in df.columns:
        if "liabilities" in df.columns:
            df["equity"] = pd.to_numeric(df["total_assets"], errors="coerce") - pd.to_numeric(df["liabilities"], errors="coerce")
        elif "a_liabilities" in df.columns:
            df["equity"] = pd.to_numeric(df["total_assets"], errors="coerce") - pd.to_numeric(df["a_liabilities"], errors="coerce")
    df["_source"] = "FUNDAMENTAL"
    return df


def _pivot_kbs_long(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot KBS long-format (rows=metrics, cols=periods) to wide-format (rows=periods, cols=metrics)."""
    if df is None or df.empty or "item_id" not in df.columns:
        return pd.DataFrame()
    # Deduplicate period columns (KBS ratio often has duplicate quarter columns)
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    period_cols = [c for c in df.columns if str(c)[:4].isdigit()]
    if not period_cols:
        return pd.DataFrame()
    pivoted = df.set_index("item_id")[period_cols].transpose().reset_index()
    pivoted = pivoted.rename(columns={"index": "period"})
    pivoted = pivoted.sort_values("period").reset_index(drop=True)
    return pivoted


def _normalize_kbs_cashflow(df: pd.DataFrame) -> pd.DataFrame:
    """KBS cash flow: pivot long→wide then rename columns.
    KBS API returns values in thousands of VND (unit=1000).
    Scale all numeric period columns by ×1000 to get raw VND.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    wide = _pivot_kbs_long(df)
    if wide.empty:
        return pd.DataFrame()
    # Scale numeric period columns from thousands VND → raw VND
    for c in wide.columns:
        if c == "period" or c == "_source":
            continue
        wide[c] = pd.to_numeric(wide[c], errors="coerce") * 1000
    rename = {
        "net_cash_flows_from_operating_activities": "operating_cf",
        "net_cash_flows_from_investing_activities": "investing_cf",
        "net_cash_flows_from_financing_activities": "financing_cf",
        "net_cash_flows_during_the_period": "net_cf",
    }
    wide = wide.rename(columns={k: v for k, v in rename.items() if k in wide.columns})
    wide["_source"] = "KBS"
    return wide


def _normalize_kbs_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """KBS ratio: pivot long→wide then rename columns."""
    if df is None or df.empty:
        return pd.DataFrame()
    wide = _pivot_kbs_long(df)
    if wide.empty:
        return pd.DataFrame()
    rename = {
        "p_e": "pe",
        "p_b": "pb",
        "trailing_eps": "eps",
        "roe_trailling": "roe",
        "roa_trailling": "roa",
    }
    wide = wide.rename(columns={k: v for k, v in rename.items() if k in wide.columns})
    # Deduplicate columns: keep last occurrence (roe_trailling→roe wins over plain roe)
    wide = wide.loc[:, ~wide.columns.duplicated(keep="last")]
    wide["_source"] = "KBS"
    return wide


def _normalize_vci_cashflow(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize VCI cash flow to standard format.
    VCI returns wide-format with period as index, metrics as columns.
    Values are in raw VND (correct scale, no scaling needed).
    Only quarter rows are used (report_period=='quarter').
    """
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    if "report_period" in df.columns:
        df = df[df["report_period"] == "quarter"]
    if df.empty:
        return pd.DataFrame()
    if df.index.name == "period" or "period" not in df.columns:
        df = df.reset_index()
    if "period" not in df.columns:
        return pd.DataFrame()
    rename = {}
    for c in df.columns:
        low = c.lower()
        if "net cash inflows" in low and "operating" in low:
            rename[c] = "operating_cf"
        elif "net cash from operating" in low:
            rename[c] = "operating_cf"
        elif "net cash inflows" in low and "investing" in low:
            rename[c] = "investing_cf"
        elif "net cash from investing" in low:
            rename[c] = "investing_cf"
        elif "net cash inflows" in low and "financing" in low:
            rename[c] = "financing_cf"
        elif "net increase" in low or "net decrease" in low:
            rename[c] = "net_cf"
        elif "net cash inflows" in low and not any(w in low for w in ("operating", "investing", "financing", "brokerage", "trust")):
            rename[c] = "net_cf"
        elif "net cash outflows" in low and not any(w in low for w in ("operating", "investing", "financing", "brokerage", "trust")):
            rename[c] = "net_cf"
    df = df.rename(columns=rename)
    # Deduplicate columns (keep first occurrence)
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    keep = ["period", "operating_cf", "investing_cf", "financing_cf", "net_cf"]
    keep = [c for c in keep if c in df.columns]
    df = df[keep]
    # Fix: VCI net_cf is often zero for banks. If >50% are zero, recompute.
    if "net_cf" in df.columns:
        zero_frac = (df["net_cf"].fillna(0) == 0).mean()
        if zero_frac > 0.5:
            df["net_cf"] = (
                df["operating_cf"].fillna(0)
                + df["investing_cf"].fillna(0)
                + df.get("financing_cf", pd.Series(0, index=df.index)).fillna(0)
            )
    df["_source"] = "VCI"
    return df


def fetch_income_statement(symbol: str, period: str = "Q") -> pd.DataFrame:
    symbol = (symbol or "").strip().upper()
    try:
        p = _PERIOD_MAP.get(period, "quarter")
        df = _get_fundamental().equity(symbol).income_statement(period=p, limit=8)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return _normalize_fundamental_income(df)
    except Exception as e:
        logger.warning("fetch_income_statement(%s) failed: %s", symbol, e)
    return pd.DataFrame()


def fetch_balance_sheet(symbol: str, period: str = "Q") -> pd.DataFrame:
    symbol = (symbol or "").strip().upper()
    try:
        p = _PERIOD_MAP.get(period, "quarter")
        df = _get_fundamental().equity(symbol).balance_sheet(period=p, limit=8)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return _normalize_fundamental_balance(df)
    except Exception as e:
        logger.warning("fetch_balance_sheet(%s) failed: %s", symbol, e)
    return pd.DataFrame()


def fetch_ratio(symbol: str, period: str = "Q") -> pd.DataFrame:
    symbol = (symbol or "").strip().upper()
    try:
        p = _PERIOD_MAP.get(period, "quarter")
        from vnstock_data import Finance as _Finance
        f = _Finance(source="kbs", symbol=symbol, period=p)
        df = f.ratio(limit=8, show_log=False)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return _normalize_kbs_ratio(df)
    except Exception as e:
        logger.warning("fetch_ratio(%s) failed: %s", symbol, e)
    return pd.DataFrame()


def fetch_cash_flow(symbol: str, period: str = "Q") -> pd.DataFrame:
    symbol = (symbol or "").strip().upper()
    # Strategy: try sources in priority order until we get >= 4 quarters.
    # 1. KBS quarterly (fast, 2 periods, needs ×1000 scaling)
    # 2. VCI (33 quarters, correct VND values)
    # 3. KBS annual (4 complete years)
    sources = [
        ("KBS quarterly", _try_kbs_quarterly_cf),
        ("VCI", _try_vci_cf),
        ("KBS annual", _try_kbs_annual_cf),
    ]
    for label, fn in sources:
        try:
            result = fn(symbol)
            if isinstance(result, pd.DataFrame) and not result.empty and len(result) >= 4:
                return result
        except Exception as e:
            logger.warning("fetch_cash_flow(%s) %s: %s", symbol, label, e)
    return pd.DataFrame()


def _try_kbs_quarterly_cf(symbol: str) -> pd.DataFrame:
    from vnstock_data import Finance as _Finance
    p = _PERIOD_MAP.get("Q", "quarter")
    f = _Finance(source="kbs", symbol=symbol, period=p)
    df = f.cash_flow(show_log=False)
    if isinstance(df, pd.DataFrame) and not df.empty:
        return _normalize_kbs_cashflow(df)
    return pd.DataFrame()


def _try_vci_cf(symbol: str) -> pd.DataFrame:
    from vnstock_data import Finance as _Finance
    f = _Finance(source="vci", symbol=symbol, period="quarter")
    df = f.cash_flow(show_log=False)
    if isinstance(df, pd.DataFrame) and not df.empty:
        return _normalize_vci_cashflow(df)
    return pd.DataFrame()


def _try_kbs_annual_cf(symbol: str) -> pd.DataFrame:
    from vnstock_data import Finance as _Finance
    f = _Finance(source="kbs", symbol=symbol, period="year")
    df = f.cash_flow(show_log=False)
    if isinstance(df, pd.DataFrame) and not df.empty:
        return _normalize_kbs_cashflow(df)
    return pd.DataFrame()


def fetch_cash_flow_with_fallback(symbol: str) -> Tuple[pd.DataFrame, str]:
    """Backward-compatible wrapper. Returns (DataFrame, source_label)."""
    df = fetch_cash_flow(symbol, period="Q")
    src = "NONE"
    if not df.empty and "_source" in df.columns:
        src = df["_source"].iloc[0]
    elif not df.empty:
        src = "OK"
    return df, src


# ─── Macro Data  (Unified UI: Macro) ─────────────────────────────────────────


def fetch_usd_vnd() -> Optional[float]:
    """
    Fetch latest USD/VND SBV central rate (Tỷ giá trung tâm) via Macro().exchange_rate().
    Returns the rate as a float, or None on failure.
    """
    try:
        from vnstock_data.api.macro import Macro

        m = Macro()
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        df = m.exchange_rate(start=start, end=end)

        if df is not None and not df.empty and "value" in df.columns:
            # Prefer "Tỷ giá trung tâm" (SBV central rate) row, drop NaN
            if "name" in df.columns:
                central = df[df["name"].str.contains("Tỷ giá trung tâm", na=False)]
                if not central.empty:
                    df = central
            df = df.dropna(subset=["value"]).sort_index()
            if df.empty:
                return None
            val = df["value"].iloc[-1]
            if isinstance(val, str):
                val = float(val.replace(",", ""))
            return float(val)
        return None
    except Exception as e:
        logger.warning("fetch_usd_vnd: %s", e)
        return None


def fetch_session_stats(symbol: str) -> pd.DataFrame:
    """
    Fetch session stats for a symbol via Market().equity(symbol).session_stats().
    """
    symbol = (symbol or "").strip().upper()
    try:
        td = _get_trading()
        df = td.foreign_trade(symbol=symbol)
        return df if isinstance(df, pd.DataFrame) else pd.DataFrame()
    except Exception as e:
        logger.warning("fetch_session_stats(%s): %s", symbol, e)
        return pd.DataFrame()


def fetch_upcoming_events(days_ahead: int = 14) -> pd.DataFrame:
    """
    Fetch upcoming corporate events (dividends, AGM, etc.)
    via Company().events().
    """
    try:
        # vnstock_data v3.5.0 removed global Company().events()
        # To fetch market wide events, we need a different approach or it's deprecated.
        # Fallback cleanly to empty DataFrame to not block the pipeline.
        return pd.DataFrame()
    except Exception as e:
        logger.warning("fetch_upcoming_events: %s", e)
        return pd.DataFrame()


def fetch_technical_signals(
    symbol: str,
    lookback_days: int = 80,
    target_date: str = None,
) -> Dict[str, Optional[float]]:
    """
    Compute EMA9, EMA26, RSI14, OBV for a symbol using vnstock_ta.
    """
    symbol = (symbol or "").strip().upper()
    result: Dict[str, Optional[float]] = {
        "ema9": None,
        "ema26": None,
        "rsi14": None,
        "obv": None,
        "ema_cross": None,
    }
    try:
        if target_date:
            end = target_date
            try:
                target_dt = datetime.strptime(target_date, "%Y-%m-%d")
                start = (target_dt - timedelta(days=lookback_days + 20)).strftime(
                    "%Y-%m-%d"
                )
            except:
                start, end = _default_dates(days_back=lookback_days + 20)
        else:
            start, end = _default_dates(days_back=lookback_days + 20)

        df = fetch_ohlcv(symbol, start, end)
        if df.empty or len(df) < 30:
            return result
        # vnstock_ta expects columns: time, open, high, low, close, volume
        import vnstock_ta

        ind = vnstock_ta.Indicator(df)
        ema9 = ind.ema(9)
        ema26 = ind.ema(26)
        rsi14 = ind.rsi(14)
        obv = ind.obv()
        result["ema9"] = (
            float(ema9.iloc[-1]) if ema9 is not None and len(ema9) else None
        )
        result["ema26"] = (
            float(ema26.iloc[-1]) if ema26 is not None and len(ema26) else None
        )
        result["rsi14"] = (
            float(rsi14.iloc[-1]) if rsi14 is not None and len(rsi14) else None
        )
        result["obv"] = float(obv.iloc[-1]) if obv is not None and len(obv) else None
        if result["ema9"] is not None and result["ema26"] is not None:
            diff = result["ema9"] - result["ema26"]
            result["ema_cross"] = 1 if diff > 0 else (-1 if diff < 0 else 0)
    except Exception as e:
        logger.warning("fetch_technical_signals(%s): %s", symbol, e)
    return result


# ─── Listing  (Unified UI: Listing) ──────────────────────────────────────────


def _get_listing():
    from vnstock import Listing

    return Listing(source="kbs")


def fetch_all_symbols() -> pd.DataFrame:
    """All listed VN stock symbols via Listing().symbols()."""
    try:
        df = _get_listing().symbols()
        return df if isinstance(df, pd.DataFrame) else pd.DataFrame()
    except Exception as e:
        logger.warning("fetch_all_symbols: %s", e)
        return pd.DataFrame()


def fetch_symbols_by_group(group: str = "VN30") -> List[str]:
    """
    Symbol list for a market group (VN30, VN100, HOSE, etc.).
    Supported indices: VN30, VN100, VNMID, VNSML, VNALL, VNXALL, VNSI
    """
    try:
        ls = _get_listing()
        # Indices and Groups are unified into symbols_by_group in v3.5.0
        result = ls.symbols_by_group(group.upper())

        if result is None:
            return []

        # Handle DataFrame or Series/List
        if hasattr(result, "symbol"):  # If it's a DataFrame with 'symbol' col
            return result["symbol"].dropna().tolist()
        if isinstance(result, pd.DataFrame):
            col = result.columns[0] if len(result.columns) else None
            return result[col].dropna().tolist() if col else []

        return [s for s in list(result) if isinstance(s, str)]
    except Exception as e:
        logger.warning("fetch_symbols_by_group(%s): %s", group, e)
        return []


# ─── Price Board  (Unified UI: Trading.price_board) ───────────────────────────


def fetch_price_board(symbols: List[str]) -> pd.DataFrame:
    """Real-time price board for a list of symbols via Trading().price_board()."""
    if not symbols:
        return pd.DataFrame()
    try:
        td = _get_trading()
        # get_all=True is required to fetch foreign transaction fields in v3.5.0
        df = td.price_board(symbols, get_all=True)

        if df is None or df.empty:
            return pd.DataFrame()

        # ⚡ FIX: Foreign Flow Calculation (KBS data mapping)
        # KBS mapping: foreign_buy_volume (Buy), foreign_sell_count (Sell Volume)
        # Note: In KBS, foreign_sell_volume is actually the Transaction Count.
        if "foreign_buy_volume" in df.columns and "foreign_sell_count" in df.columns:
            # We calculate Net Value (net_val) in RAW VND
            # Formula: (Buy Vol - Sell Vol) * Close Price
            df["net_val"] = (
                pd.to_numeric(df["foreign_buy_volume"], errors="coerce").fillna(0)
                - pd.to_numeric(df["foreign_sell_count"], errors="coerce").fillna(0)
            ) * pd.to_numeric(df["close_price"], errors="coerce").fillna(0)

        return df
    except Exception as e:
        logger.warning("fetch_price_board: %s", e)
        return pd.DataFrame()
