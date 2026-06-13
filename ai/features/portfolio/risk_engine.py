# features.portfolio/risk_engine.py
# -*- coding: utf-8 -*-

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _to_series(x) -> pd.Series:
    if isinstance(x, pd.Series):
        return x
    if isinstance(x, pd.DataFrame):
        # try common column
        for c in ["ret", "returns", "return"]:
            if c in x.columns:
                return x[c]
        raise ValueError("DataFrame missing returns column")
    return pd.Series(x)


def _sanitize_returns_series(s: pd.Series) -> pd.Series:
    """Ensure datetime index, sorted, unique (keep last)."""
    if s is None:
        return pd.Series(dtype=float)

    s = _to_series(s).copy()

    # coerce index to datetime if possible
    if not isinstance(s.index, pd.DatetimeIndex):
        try:
            s.index = pd.to_datetime(s.index, errors="coerce")
        except Exception:
            pass

    # drop NaT index
    if isinstance(s.index, pd.DatetimeIndex):
        s = s[~s.index.isna()]
        # normalize timezone to naive (avoid tz-mismatch)
        try:
            if s.index.tz is not None:
                s.index = s.index.tz_convert(None)
        except Exception:
            pass

    # sort & de-dup index
    s = s.sort_index()
    if s.index.has_duplicates:
        s = s[~s.index.duplicated(keep="last")]

    # force numeric
    s = pd.to_numeric(s, errors="coerce")
    s = s.dropna()
    return s


def _align_returns(ret_map: Dict[str, pd.Series]) -> pd.DataFrame:
    """Align returns by DATE (not timestamp), to make VN+Crypto overlap correctly."""
    cols = []
    for k, s in ret_map.items():
        s = _to_series(s).copy()
        s.name = k

        # force datetime index
        try:
            s.index = pd.to_datetime(s.index, utc=True, errors="coerce")
        except Exception:
            s.index = pd.to_datetime(s.index, errors="coerce")

        # drop bad index
        s = s[~s.index.isna()]

        # normalize to date, remove timezone
        try:
            # utc=True => tz-aware; drop tz then normalize
            s.index = s.index.tz_convert(None).normalize()
        except Exception:
            # already tz-naive
            s.index = pd.to_datetime(s.index).normalize()

        # numeric
        s = pd.to_numeric(s, errors="coerce")

        cols.append(s)

    df = pd.concat(cols, axis=1).sort_index()

    # if duplicate dates exist, keep last
    df = df.groupby(df.index).last()

    # drop rows that are all NaN
    df = df.dropna(how="all")
    return df


def annualize_return(daily_ret: pd.Series) -> float:
    if daily_ret is None or daily_ret.empty:
        return float("nan")
    mu = daily_ret.mean()
    return float(mu * TRADING_DAYS)


def annualize_vol(daily_ret: pd.Series) -> float:
    if daily_ret is None or daily_ret.empty:
        return float("nan")
    sig = daily_ret.std(ddof=1)
    return float(sig * np.sqrt(TRADING_DAYS))


def max_drawdown(daily_ret: pd.Series) -> float:
    """Max drawdown from returns series."""
    if daily_ret is None or daily_ret.empty:
        return float("nan")
    eq = (1.0 + daily_ret.fillna(0.0)).cumprod()
    peak = eq.cummax()
    dd = (eq / peak) - 1.0
    return float(dd.min())


def expected_shortfall(daily_ret: pd.Series, alpha: float = 0.05) -> float:
    """ES at alpha (e.g., 0.05 => 95% ES)."""
    if daily_ret is None or daily_ret.empty:
        return float("nan")
    r = daily_ret.dropna().values
    if len(r) < 20:
        return float("nan")
    var = np.percentile(r, alpha * 100.0)
    tail = r[r <= var]
    if len(tail) == 0:
        return float("nan")
    return float(np.mean(tail))


def sortino_ratio(daily_ret: pd.Series, rf_daily: float = 0.0) -> float:
    if daily_ret is None or daily_ret.empty:
        return float("nan")
    r = daily_ret.dropna()
    downside = (r[r < rf_daily] - rf_daily)
    dd = downside.std(ddof=1)
    if dd == 0 or np.isnan(dd):
        return float("nan")
    ann_excess = (r.mean() - rf_daily) * TRADING_DAYS
    return float(ann_excess / (dd * np.sqrt(TRADING_DAYS)))


def sharpe_ratio(daily_ret: pd.Series, rf_daily: float = 0.0) -> float:
    if daily_ret is None or daily_ret.empty:
        return float("nan")
    r = daily_ret.dropna()
    sig = r.std(ddof=1)
    if sig == 0 or np.isnan(sig):
        return float("nan")
    ann_excess = (r.mean() - rf_daily) * TRADING_DAYS
    ann_vol = sig * np.sqrt(TRADING_DAYS)
    return float(ann_excess / ann_vol)


def skewness(daily_ret: pd.Series) -> float:
    if daily_ret is None or daily_ret.empty:
        return float("nan")
    r = daily_ret.dropna()
    if len(r) < 20:
        return float("nan")
    m = r.mean()
    s = r.std(ddof=1)
    if s == 0 or np.isnan(s):
        return float("nan")
    return float(((r - m) ** 3).mean() / (s ** 3))


def covariance_annualized(returns_df: pd.DataFrame) -> pd.DataFrame:
    if returns_df is None or returns_df.empty:
        return pd.DataFrame()
    df = returns_df.dropna(how="any")  # ✅ full-overlap rows only
    if df.empty or df.shape[0] < 30:
        return pd.DataFrame()
    return df.cov() * TRADING_DAYS


def correlation_matrix(returns_df: pd.DataFrame) -> pd.DataFrame:
    if returns_df is None or returns_df.empty:
        return pd.DataFrame()
    return returns_df.corr()


def portfolio_returns(returns_df: pd.DataFrame, weights: Dict[str, float]) -> pd.Series:
    """rp = R * w, weights keyed by columns in returns_df."""
    if returns_df is None or returns_df.empty:
        return pd.Series(dtype=float)
    w = pd.Series(weights).reindex(returns_df.columns).fillna(0.0)
    rp = returns_df.fillna(0.0).mul(w, axis=1).sum(axis=1)
    rp.name = "PORT"
    return rp


def portfolio_vol_from_cov(weights: Dict[str, float], cov: pd.DataFrame) -> float:
    if cov is None or cov.empty:
        return float("nan")
    cols = list(cov.columns)
    w = np.array([weights.get(c, 0.0) for c in cols], dtype=float)
    v = float(np.sqrt(w.T @ cov.values @ w))
    return v


def risk_contribution(weights: Dict[str, float], cov: pd.DataFrame) -> pd.Series:
    """
    Cov-based risk contribution:
    RC_i = w_i * (Sigma w)_i / sigma_p
    %RC = RC_i / sigma_p
    """
    if cov is None or cov.empty:
        return pd.Series(dtype=float)

    cols = list(cov.columns)
    w = np.array([weights.get(c, 0.0) for c in cols], dtype=float)
    sigma_p = np.sqrt(w.T @ cov.values @ w)
    if sigma_p == 0 or np.isnan(sigma_p):
        return pd.Series({c: np.nan for c in cols})

    m = cov.values @ w  # marginal contribution numerator part
    rc = (w * m) / sigma_p
    prc = rc / sigma_p
    return pd.Series(prc, index=cols).sort_values(ascending=False)


@dataclass
class WindowPack:
    window: int
    ann_ret: float
    ann_vol: float
    sharpe: float
    sortino: float
    mdd: float
    es95: float
    skew: float
    cov: pd.DataFrame
    corr: pd.DataFrame
    rc: pd.Series
    n_obs: int


def compute_window_pack(
    returns_df_full: pd.DataFrame,
    weights: Dict[str, float],
    window: int,
    rf_daily: float = 0.0,
) -> WindowPack:
    """
    returns_df_full: aligned daily returns with columns = assets
    weights: NAV weights across assets (sum ~1.0)
    """
    if returns_df_full is None or returns_df_full.empty:
        return WindowPack(
            window=window,
            ann_ret=float("nan"),
            ann_vol=float("nan"),
            sharpe=float("nan"),
            sortino=float("nan"),
            mdd=float("nan"),
            es95=float("nan"),
            skew=float("nan"),
            cov=pd.DataFrame(),
            corr=pd.DataFrame(),
            rc=pd.Series(dtype=float),
            n_obs=0,
        )

    df = returns_df_full.dropna(how="all").copy()

    # lấy dư dữ liệu trước, rồi mới dropna(any) để giữ đủ window trading days
    df = df.tail(window * 3)

    # chỉ giữ các ngày có return cho TẤT CẢ assets (VN bỏ weekend/holiday, crypto vẫn có weekday)
    df = df.dropna(how="any")

    # cuối cùng lấy đúng window
    df = df.tail(window)

    if df.shape[0] < max(30, int(window * 0.6)):

        # quá ít overlap => trả pack n_obs thấp, rc NaN
        rp = portfolio_returns(df, weights)
        cov = covariance_annualized(df)
        corr = correlation_matrix(df)
        rc = risk_contribution(weights, cov)

    rp = portfolio_returns(df, weights)

    cov = covariance_annualized(df)
    corr = correlation_matrix(df)
    rc = risk_contribution(weights, cov)

    pack = WindowPack(
        window=window,
        ann_ret=annualize_return(rp),
        ann_vol=annualize_vol(rp),
        sharpe=sharpe_ratio(rp, rf_daily=rf_daily),
        sortino=sortino_ratio(rp, rf_daily=rf_daily),
        mdd=max_drawdown(rp),
        es95=expected_shortfall(rp, alpha=0.05),
        skew=skewness(rp),
        cov=cov,
        corr=corr,
        rc=rc,
        n_obs=int(rp.dropna().shape[0]),
    )
    return pack


def build_returns_df_from_map(ret_map: Dict[str, pd.Series]) -> pd.DataFrame:
    return _align_returns(ret_map)

# features.portfolio/risk_engine.py
# add to bottom (or suitable place)

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import math

CAL_DAYS = 365  # calendar annualization for multi-asset NAV

@dataclass
class NavPerfPack:
    window: int
    n_obs: int
    ann_ret: float
    ann_vol: float
    sharpe: float
    mdd: float
    es95: float
    skew: float

def _nav_max_drawdown(nav: pd.Series) -> float:
    if nav is None or nav.empty:
        return float("nan")
    nav = nav.dropna()
    if nav.empty:
        return float("nan")
    peak = nav.cummax()
    dd = (nav / peak) - 1.0
    return float(dd.min())

def _expected_shortfall_from_returns(r: pd.Series, alpha: float = 0.05) -> float:
    r = r.dropna()
    if len(r) < 20:
        return float("nan")
    var = np.percentile(r.values, alpha * 100.0)
    tail = r.values[r.values <= var]
    if len(tail) == 0:
        return float("nan")
    return float(np.mean(tail))

def _skew(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 20:
        return float("nan")
    m = r.mean()
    s = r.std(ddof=1)
    if s == 0 or np.isnan(s):
        return float("nan")
    return float(((r - m) ** 3).mean() / (s ** 3))

def build_calendar_nav_series(
    base: str,
    holdings: List[Dict[str, Any]],
    vn_px_map: Dict[str, pd.Series],
    cr_px_map: Dict[str, pd.Series],
    fx_usdt_vnd: float,
) -> pd.Series:
    """
    ✅ Calendar NAV from real price series:
    - VN forward-fill across calendar days (weekend/holiday => flat)
    - Crypto already daily
    - Cash constant
    - Gold: skip for now
    Returns: NAV series indexed by daily calendar (D)
    """
    base = (base or "VND").upper().strip()

    # collect all price indices
    idxs = []
    for s in vn_px_map.values():
        if isinstance(s, pd.Series) and not s.empty:
            idxs.append(s.index)
    for s in cr_px_map.values():
        if isinstance(s, pd.Series) and not s.empty:
            idxs.append(s.index)

    if not idxs:
        return pd.Series(dtype=float, name="NAV")

    start = min(i.min() for i in idxs)
    end = max(i.max() for i in idxs)
    cal = pd.date_range(start=start.normalize(), end=end.normalize(), freq="D")

    # prebuild filled price frames
    vn_filled: Dict[str, pd.Series] = {}
    for sym, s in vn_px_map.items():
        if s is None or s.empty:
            continue
        ss = s.copy()
        ss.index = pd.to_datetime(ss.index)
        ss = ss[~ss.index.duplicated(keep="last")].sort_index()
        ss = ss.reindex(cal).ffill()  # ✅ forward fill VN close on calendar
        vn_filled[sym] = ss

    cr_filled: Dict[str, pd.Series] = {}
    for sym, s in cr_px_map.items():
        if s is None or s.empty:
            continue
        ss = s.copy()
        ss.index = pd.to_datetime(ss.index)
        ss = ss[~ss.index.duplicated(keep="last")].sort_index()
        ss = ss.reindex(cal).ffill()  # crypto daily already, ffill is safe if small gaps
        cr_filled[sym] = ss

    # cash
    cash_vnd = 0.0
    cash_usdt = 0.0

    # build NAV by summing position values each day
    nav = pd.Series(0.0, index=cal, name="NAV")

    for h in holdings:
        at = (h.get("asset_type") or "").upper().strip()
        sym = (h.get("symbol") or "").upper().strip()
        qty = float(h.get("qty") or 0.0)

        if at == "CASH":
            ccy = (sym or (h.get("cost_ccy") or "VND")).upper().strip()
            if ccy == "VND":
                cash_vnd += qty
            else:
                cash_usdt += qty

        elif at == "VN":
            s = vn_filled.get(sym)
            if s is None or s.empty:
                continue
            nav = nav.add(s * qty, fill_value=0.0)

        elif at == "CRYPTO":
            sym_usdt = sym if sym.endswith("USDT") else (sym + "USDT")
            s = cr_filled.get(sym_usdt)
            if s is None or s.empty:
                continue
            v = s * qty  # in USDT
            if base == "VND":
                v = v * fx_usdt_vnd
            nav = nav.add(v, fill_value=0.0)

        elif at == "GOLD":
            # N/A now
            continue

    # add cash
    if base == "VND":
        nav = nav + cash_vnd + cash_usdt * fx_usdt_vnd
    else:
        nav = nav + cash_usdt + cash_vnd / fx_usdt_vnd

    nav = nav.replace([np.inf, -np.inf], np.nan).dropna()
    return nav


def compute_nav_perf_pack(nav: pd.Series, window: int, rf_daily: float = 0.0) -> NavPerfPack:
    if nav is None or nav.empty:
        return NavPerfPack(window=window, n_obs=0, ann_ret=float("nan"), ann_vol=float("nan"),
                           sharpe=float("nan"), mdd=float("nan"), es95=float("nan"), skew=float("nan"))

    nav = nav.sort_index()
    nav_w = nav.tail(window + 5)  # small buffer
    r = nav_w.pct_change().dropna()
    r = r.tail(window)

    n = int(r.shape[0])
    if n < max(20, int(window * 0.7)):
        return NavPerfPack(window=window, n_obs=n, ann_ret=float("nan"), ann_vol=float("nan"),
                           sharpe=float("nan"), mdd=float("nan"), es95=float("nan"), skew=float("nan"))

    mu = float(r.mean())
    sig = float(r.std(ddof=1))
    ann_ret = mu * CAL_DAYS
    ann_vol = sig * math.sqrt(CAL_DAYS) if sig and not math.isnan(sig) else float("nan")
    sharpe = (ann_ret - rf_daily * CAL_DAYS) / ann_vol if ann_vol and not math.isnan(ann_vol) else float("nan")

    return NavPerfPack(
        window=window,
        n_obs=n,
        ann_ret=float(ann_ret),
        ann_vol=float(ann_vol),
        sharpe=float(sharpe),
        mdd=_nav_max_drawdown(nav.tail(window)),
        es95=_expected_shortfall_from_returns(r, alpha=0.05),
        skew=_skew(r),
    )

def compute_return_contribution(
    returns_df: pd.DataFrame,
    weights: Dict[str, float],
    window: int
) -> pd.DataFrame:
    """
    Return contribution table:
    columns = ['weight', 'mean_ret', 'abs_contribution', 'pct_contribution']
    """

    if returns_df is None or returns_df.empty:
        return pd.DataFrame()

    df = returns_df.tail(window)
    if df.empty:
        return pd.DataFrame()

    # mean return per asset
    mu = df.mean()

    rows = []
    port_ret = 0.0

    for k in df.columns:
        w = float(weights.get(k, 0.0))
        m = float(mu.get(k, 0.0))
        contrib = w * m
        port_ret += contrib
        rows.append((k, w, m, contrib))

    out = pd.DataFrame(rows, columns=["asset", "weight", "mean_ret", "abs_contribution"])

    if port_ret != 0:
        out["pct_contribution"] = out["abs_contribution"] / port_ret
    else:
        out["pct_contribution"] = 0.0

    out = out.sort_values("abs_contribution", ascending=False)
    return out