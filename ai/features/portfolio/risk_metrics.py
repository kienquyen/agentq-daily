# features.portfolio/risk_metrics.py
# -*- coding: utf-8 -*-

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import math

import numpy as np
import pandas as pd

from features.portfolio.storage import load_snapshots_nav
from features.portfolio.price_crypto import fetch_binance_returns
from features.portfolio.price_vn import fetch_vn_returns

TRADING_DAYS = 252
RF_ANNUAL = float(__import__("os").getenv("RF_ANNUAL", "0.07"))


# -------------------------
# helpers
# -------------------------

def _sanitize_ret_series(s: pd.Series, name: str = "") -> pd.Series:
    """Datetime index, sorted, unique (keep last)."""
    if s is None or len(s) == 0:
        return pd.Series(dtype=float, name=name or getattr(s, "name", None))

    s = s.copy()
    if name:
        s.name = name

    # ensure datetime index if possible
    if not isinstance(s.index, pd.DatetimeIndex):
        try:
            s.index = pd.to_datetime(s.index, errors="coerce")
        except Exception:
            pass

    if isinstance(s.index, pd.DatetimeIndex):
        s = s[~s.index.isna()]
        # convert tz-aware -> naive
        try:
            if s.index.tz is not None:
                s.index = s.index.tz_convert(None)
        except Exception:
            pass

        # normalize to date (calendar alignment)
        try:
            s.index = s.index.normalize()
        except Exception:
            pass

    s = s.sort_index()
    if isinstance(s.index, pd.DatetimeIndex) and s.index.has_duplicates:
        s = s[~s.index.duplicated(keep="last")]

    s = pd.to_numeric(s, errors="coerce").dropna()
    return s


def _ensure_daily_datetime_index(s: pd.Series, name: str) -> pd.Series:
    """
    If returns series has no DatetimeIndex (e.g., RangeIndex from Binance),
    create a synthetic daily DatetimeIndex ending today.
    """
    if s is None or len(s) == 0:
        return pd.Series(dtype=float, name=name)

    s = s.copy()
    s.name = name

    if isinstance(s.index, pd.DatetimeIndex):
        return _sanitize_ret_series(s, name=name)

    # fallback: assume daily spacing, most recent point is "today"
    end = pd.Timestamp(datetime.now().date())
    idx = pd.date_range(end=end, periods=len(s), freq="D")
    s.index = idx
    return _sanitize_ret_series(s, name=name)


def _align_two(port: pd.Series, bench: pd.Series) -> pd.DataFrame:
    port = _sanitize_ret_series(port, name="PORT")
    bench = _sanitize_ret_series(bench, name="BENCH")
    df = pd.concat([port, bench], axis=1).dropna()
    return df


def _beta(port: pd.Series, bench: pd.Series) -> Optional[float]:
    df = _align_two(port, bench)
    if df.shape[0] < 30:
        return None
    p = df["PORT"].values
    b = df["BENCH"].values
    var = float(np.var(b))
    if var == 0:
        return None
    cov = float(np.cov(p, b)[0, 1])
    return cov / var


def _downside_beta(port: pd.Series, bench: pd.Series) -> Optional[float]:
    """
    Downside beta: compute beta on subset where benchmark return < 0.
    """
    df = _align_two(port, bench)
    if df.shape[0] < 30:
        return None
    df = df[df["BENCH"] < 0]
    if df.shape[0] < 20:
        return None

    p = df["PORT"].values
    b = df["BENCH"].values
    var = float(np.var(b))
    if var == 0:
        return None
    cov = float(np.cov(p, b)[0, 1])
    return cov / var


def _pick_vn30_symbol() -> Optional[str]:
    """
    Fixed preference for VN30 benchmark (validate by trying to fetch returns).
    """
    candidates = ["VN30", "VN30INDEX", "VN30-INDEX", "^VN30", "VN30F1M"]  # keep simple
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")

    for sym in candidates:
        try:
            r = fetch_vn_returns(sym, start=start, end=end)
            if r is not None and len(r) >= 10:
                return sym
        except Exception:
            continue
    return None


def _portfolio_returns_from_snapshots(user_id: int) -> pd.Series:
    """
    Portfolio daily returns from snapshots NAV.
    Index normalized to date for calendar alignment.
    """
    snaps = load_snapshots_nav(user_id, limit=5000)
    if not snaps or len(snaps) < 10:
        return pd.Series(dtype=float, name="PORT")

    df = pd.DataFrame(snaps)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"])
    df = df.sort_values("ts")

    # normalize to date; keep last NAV per day
    df["d"] = df["ts"].dt.tz_convert(None).dt.normalize()
    df = df.drop_duplicates(subset=["d"], keep="last")

    nav = df.set_index("d")["nav_base"].astype(float)
    ret = nav.pct_change().dropna().rename("PORT")
    return _sanitize_ret_series(ret, name="PORT")


# -------------------------
# 1) MTD / YTD / Since inception (from snapshots)
# -------------------------
def compute_perf_mtd_ytd_si(user_id: int) -> Dict[str, Optional[float]]:
    """
    Return % based on snapshot NAV series:
      - SI: latest / first - 1
      - MTD: latest / first_in_month - 1
      - YTD: latest / first_in_year - 1
    """
    snaps = load_snapshots_nav(user_id, limit=5000)
    if not snaps or len(snaps) < 2:
        return {"ret_mtd": None, "ret_ytd": None, "ret_si": None}

    df = pd.DataFrame(snaps)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"]).sort_values("ts")

    # daily nav (last per day)
    df["d"] = df["ts"].dt.tz_convert(None).dt.normalize()
    df = df.drop_duplicates(subset=["d"], keep="last")

    nav = df.set_index("d")["nav_base"].astype(float)
    if nav.empty:
        return {"ret_mtd": None, "ret_ytd": None, "ret_si": None}

    latest = float(nav.iloc[-1])
    first = float(nav.iloc[0])

    if first <= 0 or latest <= 0:
        return {"ret_mtd": None, "ret_ytd": None, "ret_si": None}

    ret_si = (latest / first) - 1.0

    last_date = nav.index[-1]
    # MTD
    m_start = pd.Timestamp(year=last_date.year, month=last_date.month, day=1)
    nav_m = nav[nav.index >= m_start]
    ret_mtd = None
    if len(nav_m) >= 1 and float(nav_m.iloc[0]) > 0:
        ret_mtd = (latest / float(nav_m.iloc[0])) - 1.0

    # YTD
    y_start = pd.Timestamp(year=last_date.year, month=1, day=1)
    nav_y = nav[nav.index >= y_start]
    ret_ytd = None
    if len(nav_y) >= 1 and float(nav_y.iloc[0]) > 0:
        ret_ytd = (latest / float(nav_y.iloc[0])) - 1.0

    return {"ret_mtd": ret_mtd, "ret_ytd": ret_ytd, "ret_si": ret_si}


# -------------------------
# 2) Rolling Sharpe (from snapshots) - keep old
# -------------------------
def compute_rolling_sharpe(user_id: int) -> Dict[str, Optional[float]]:
    snaps = load_snapshots_nav(user_id, limit=800)
    if not snaps or len(snaps) < 35:
        return {"sharpe_30d": None, "sharpe_60d": None, "sharpe_90d": None}

    df = pd.DataFrame(snaps)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"]).sort_values("ts")
    df["d"] = df["ts"].dt.tz_convert(None).dt.normalize()
    df = df.drop_duplicates(subset=["d"], keep="last")

    nav = df.set_index("d")["nav_base"].astype(float)
    rets = nav.pct_change().dropna()

    rf_d = RF_ANNUAL / TRADING_DAYS
    ex = rets - rf_d

    def sr(w: int) -> Optional[float]:
        if len(ex) < w + 5:
            return None
        x = ex.iloc[-w:]
        sd = float(x.std(ddof=0))
        if sd == 0:
            return None
        return float((x.mean() / sd) * math.sqrt(TRADING_DAYS))

    return {"sharpe_30d": sr(30), "sharpe_60d": sr(60), "sharpe_90d": sr(90)}


# -------------------------
# 3) Beta pack (Calendar-aligned) vs VN30 & BTC + downside beta
# -------------------------
def compute_beta_pack_calendar(user_id: int, lookback_days: int = 420) -> Dict[str, Any]:
    """
    Returns:
      {
        "bench_vn": "VN30" (resolved symbol),
        "beta_vn_180d": ...,
        "dbeta_vn_180d": ...,
        "beta_btc_180d": ...,
        "dbeta_btc_180d": ...,
        "n_obs_vn": int,
        "n_obs_btc": int
      }
    """
    port = _portfolio_returns_from_snapshots(user_id)
    if port is None or port.empty:
        return {
            "bench_vn": None,
            "beta_vn_180d": None,
            "dbeta_vn_180d": None,
            "beta_btc_180d": None,
            "dbeta_btc_180d": None,
            "n_obs_vn": 0,
            "n_obs_btc": 0,
        }

    # --- VN30 bench
    vn_sym = _pick_vn30_symbol()
    beta_vn = dbeta_vn = None
    n_obs_vn = 0

    if vn_sym:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=int(lookback_days))).strftime("%Y-%m-%d")
        vnr = fetch_vn_returns(vn_sym, start=start, end=end)
        vnr = _sanitize_ret_series(vnr, name="VN30")
        # use last 180 trading-ish observations from aligned df
        df_vn = _align_two(port, vnr).tail(180)
        n_obs_vn = int(df_vn.shape[0])
        if n_obs_vn >= 30:
            beta_vn = _beta(df_vn["PORT"], df_vn["BENCH"])
            dbeta_vn = _downside_beta(df_vn["PORT"], df_vn["BENCH"])

    # --- BTC bench (Binance)
    # fetch more then cut last 180 calendar days (after sanitize)
    try:
        btc = fetch_binance_returns("BTCUSDT", interval="1d", limit=300)
    except Exception:
        btc = pd.Series(dtype=float, name="BTCUSDT")

    btc = _ensure_daily_datetime_index(btc, name="BTCUSDT")
    df_btc = _align_two(port, btc).tail(180)
    n_obs_btc = int(df_btc.shape[0])
    beta_btc = dbeta_btc = None
    if n_obs_btc >= 30:
        beta_btc = _beta(df_btc["PORT"], df_btc["BENCH"])
        dbeta_btc = _downside_beta(df_btc["PORT"], df_btc["BENCH"])

    return {
        "bench_vn": vn_sym,
        "beta_vn_180d": beta_vn,
        "dbeta_vn_180d": dbeta_vn,
        "beta_btc_180d": beta_btc,
        "dbeta_btc_180d": dbeta_btc,
        "n_obs_vn": n_obs_vn,
        "n_obs_btc": n_obs_btc,
    }


# -------------------------
# Backward-compatible old APIs (keep)
# -------------------------
def compute_beta_vs_btc(user_id: int) -> Dict[str, Optional[float]]:
    snaps = load_snapshots_nav(user_id, limit=900)
    if not snaps or len(snaps) < 60:
        return {"beta_btc_3m": None, "beta_btc_6m": None}

    port = _portfolio_returns_from_snapshots(user_id)
    if port.empty:
        return {"beta_btc_3m": None, "beta_btc_6m": None}

    btc3 = _ensure_daily_datetime_index(fetch_binance_returns("BTCUSDT", interval="1d", limit=140), "BTCUSDT").tail(90)
    btc6 = _ensure_daily_datetime_index(fetch_binance_returns("BTCUSDT", interval="1d", limit=260), "BTCUSDT").tail(180)

    b3 = _beta(port.tail(90), btc3)
    b6 = _beta(port.tail(180), btc6)
    return {"beta_btc_3m": b3, "beta_btc_6m": b6}


def compute_beta_vs_vnindex(user_id: int) -> Dict[str, Optional[float]]:
    """
    Keep legacy name but now prefer VN30 (to match your requirement).
    """
    snaps = load_snapshots_nav(user_id, limit=1000)
    if not snaps or len(snaps) < 80:
        return {"beta_vni_6m": None, "beta_vni_12m": None, "vni_symbol": None}

    port = _portfolio_returns_from_snapshots(user_id)
    if port.empty:
        return {"beta_vni_6m": None, "beta_vni_12m": None, "vni_symbol": None}

    vni_symbol = _pick_vn30_symbol()
    if not vni_symbol:
        return {"beta_vni_6m": None, "beta_vni_12m": None, "vni_symbol": None}

    end = datetime.now().strftime("%Y-%m-%d")
    start_6m = (datetime.now() - timedelta(days=220)).strftime("%Y-%m-%d")
    start_12m = (datetime.now() - timedelta(days=420)).strftime("%Y-%m-%d")

    try:
        vni6 = fetch_vn_returns(vni_symbol, start=start_6m, end=end).tail(180)
        vni12 = fetch_vn_returns(vni_symbol, start=start_12m, end=end).tail(252)
    except Exception:
        return {"beta_vni_6m": None, "beta_vni_12m": None, "vni_symbol": vni_symbol}

    b6 = _beta(port.tail(180), vni6)
    b12 = _beta(port.tail(252), vni12)

    return {"beta_vni_6m": b6, "beta_vni_12m": b12, "vni_symbol": vni_symbol}