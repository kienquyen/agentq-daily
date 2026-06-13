# features.portfolio/service.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import os
import math

import numpy as np
import pandas as pd

from .storage import load_portfolio_state

# --- VN pricing/returns
from .price_vn import fetch_vn_last_prices, fetch_vn_returns_map
try:
    from .price_vn import fetch_vn_prices_map  # type: ignore
except Exception:
    fetch_vn_prices_map = None  # type: ignore

# --- Crypto pricing/returns
from .price_crypto import fetch_crypto_last_prices, fetch_crypto_returns_map
try:
    from .price_crypto import fetch_crypto_prices_map  # type: ignore
except Exception:
    fetch_crypto_prices_map = None  # type: ignore

# --- Risk engines
from .risk_engine import (
    TRADING_DAYS,
    annualize_return,
    annualize_vol,
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    expected_shortfall,
    skewness,
    covariance_annualized,
    correlation_matrix,
    risk_contribution,
)

from .regime import compute_regime_shift, RegimeShift


RF_ANNUAL = float(os.getenv("RF_ANNUAL", "0.07"))
RF_DAILY = RF_ANNUAL / TRADING_DAYS

CASH_BAND_DEFAULT = (0.10, 0.40)  # 10–40%
DEBUG = str(os.getenv("TASK3_DEBUG", "0")).strip() in ("1", "true", "True", "YES", "yes")


# =========================
# Small dataclasses
# =========================
@dataclass
class WindowStats:
    window: int
    ann_ret: float
    ann_vol: float
    sharpe: float
    sortino: float
    mdd: float
    es95: float
    skew: float
    n_obs: int


# =========================
# Helpers
# =========================
def _safe_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _fx_usdt_vnd() -> float:
    return float(os.getenv("USDT_VND", "26630"))


def _asset_key(asset_type: str, symbol: str) -> str:
    return f"{asset_type.upper()}:{(symbol or '').upper().strip()}"


def _sanitize_date_index(s: pd.Series, name: str = "") -> pd.Series:
    """Ensure DatetimeIndex (naive, normalized day), sorted, unique keep last."""
    if s is None or len(s) == 0:
        return pd.Series(dtype=float, name=name)

    s = s.copy()
    if name:
        s.name = name

    if not isinstance(s.index, pd.DatetimeIndex):
        s.index = pd.to_datetime(s.index, errors="coerce")

    s = s[~s.index.isna()]
    try:
        if getattr(s.index, "tz", None) is not None:
            s.index = s.index.tz_convert(None)
    except Exception:
        pass

    s.index = s.index.normalize()
    s = s.sort_index()
    if s.index.has_duplicates:
        s = s[~s.index.duplicated(keep="last")]

    s = pd.to_numeric(s, errors="coerce").dropna()
    return s

def _maybe_scale_vn_series(sym: str, s: pd.Series, last_vn: Dict[str, float]) -> pd.Series:
    """
    Fix unit mismatch between:
      - last_vn price (often VND)
      - history price series (sometimes thousand-VND)
    If detected ~1000x mismatch, auto-scale.
    """
    try:
        s2 = pd.to_numeric(s, errors="coerce").dropna()
        if s2.empty:
            return s

        px_now = float(last_vn.get(sym, np.nan))
        px_hist = float(s2.iloc[-1])

        if (not np.isfinite(px_now)) or px_now <= 0 or (not np.isfinite(px_hist)) or px_hist <= 0:
            return s

        ratio = px_now / px_hist

        # hist missing 3 zeros (e.g., 90 vs 90,000)
        if 500 <= ratio <= 2000:
            return s * 1000.0

        # opposite direction
        if 0.0005 <= ratio <= 0.002:
            return s / 1000.0

        return s
    except Exception:
        return s

def _compute_nav_weights_and_values(
    base: str,
    holdings: List[Dict[str, Any]],
    last_vn: Dict[str, float],
    last_crypto: Dict[str, float],
    fx_usdt_vnd: float,
) -> Tuple[
    float,
    Dict[str, float],
    Dict[str, float],
    float,
    float,
    Dict[str, float],
    Dict[str, float],
    Dict[str, float],
]:
    base = (base or "VND").upper().strip()
    last_prices: Dict[str, float] = {}
    pos_value: Dict[str, float] = {}
    cost_value: Dict[str, float] = {}

    for h in holdings:
        at = (h.get("asset_type") or "").upper().strip()
        sym = (h.get("symbol") or "").upper().strip()
        qty = _safe_float(h.get("qty"), 0.0)
        avg = _safe_float(h.get("avg_cost"), 0.0)
        ccy = (h.get("cost_ccy") or "VND").upper().strip()

        if at == "VN":
            k = _asset_key("VN", sym)
            px = _safe_float(last_vn.get(sym), np.nan)
            last_prices[k] = px
            if np.isfinite(px) and px > 0:
                pos_value[k] = float(qty * px)
                cost_value[k] = float(qty * avg)

        elif at == "CRYPTO":
            sym_usdt = sym if sym.endswith("USDT") else (sym + "USDT")
            k = _asset_key("CRYPTO", sym_usdt)
            px = _safe_float(last_crypto.get(sym_usdt), np.nan)
            last_prices[k] = px
            if np.isfinite(px) and px > 0:
                v_usdt = qty * px
                c_usdt = qty * avg
                if base == "VND":
                    pos_value[k] = float(v_usdt * fx_usdt_vnd)
                    cost_value[k] = float(c_usdt * fx_usdt_vnd)
                else:
                    pos_value[k] = float(v_usdt)
                    cost_value[k] = float(c_usdt)

        elif at == "CASH":
            cash_ccy = sym or ccy or "VND"
            k = _asset_key("CASH", cash_ccy)
            last_prices[k] = 1.0
            if base == "VND":
                v = qty if cash_ccy == "VND" else qty * fx_usdt_vnd
            else:
                v = qty if cash_ccy == "USDT" else qty / fx_usdt_vnd
            pos_value[k] = float(v)
            cost_value[k] = float(v)

        elif at == "GOLD":
            k = _asset_key("GOLD", sym or "XAU")
            last_prices[k] = float("nan")

    nav = float(sum(pos_value.values())) if pos_value else 0.0

    weights_all: Dict[str, float] = {}
    if nav > 0:
        for k, v in pos_value.items():
            weights_all[k] = float(v / nav)

    alloc = {"VN": 0.0, "CRYPTO": 0.0, "CASH": 0.0, "GOLD": 0.0}
    for k, w in weights_all.items():
        if k.startswith("VN:"):
            alloc["VN"] += w
        elif k.startswith("CRYPTO:"):
            alloc["CRYPTO"] += w
        elif k.startswith("CASH:"):
            alloc["CASH"] += w
        elif k.startswith("GOLD:"):
            alloc["GOLD"] += w

    pnl = float(sum(pos_value.get(k, 0.0) - cost_value.get(k, 0.0) for k in pos_value.keys()))
    pnl_pct = float(pnl / nav) if nav > 0 else 0.0

    return nav, weights_all, alloc, pnl, pnl_pct, last_prices, pos_value, cost_value


def _build_calendar_nav_series(
    risk_pos_value_now: Dict[str, float],
    last_prices_by_key: Dict[str, float],
    vn_prices: Dict[str, pd.Series],
    cr_prices: Dict[str, pd.Series],
    cash_value: float,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> Tuple[pd.Series, Dict[str, pd.Series], pd.DataFrame]:
    idx = pd.date_range(start=start_date.normalize(), end=end_date.normalize(), freq="D")
    prices = pd.DataFrame(index=idx)

    for k, s in (vn_prices or {}).items():
        s = _sanitize_date_index(s, name=k)
        if not s.empty:
            prices[k] = s.reindex(idx)

    for k, s in (cr_prices or {}).items():
        s = _sanitize_date_index(s, name=k)
        if not s.empty:
            prices[k] = s.reindex(idx)

    prices = prices.ffill()

    value_map: Dict[str, pd.Series] = {}
    for k in prices.columns:
        px_now = float(last_prices_by_key.get(k, np.nan))
        v_now = float(risk_pos_value_now.get(k, 0.0))
        if (not np.isfinite(px_now)) or px_now <= 0 or v_now == 0:
            continue
        value_map[k] = (v_now * (prices[k] / px_now)).rename(k)

    if value_map:
        dfv = pd.concat(list(value_map.values()), axis=1).fillna(0.0)
        nav = dfv.sum(axis=1) + float(cash_value)
    else:
        nav = pd.Series([float(cash_value)] * len(idx), index=idx, name="NAV")

    nav = _sanitize_date_index(nav, name="NAV")
    return nav, value_map, prices


def _window_stats_from_nav(nav: pd.Series, window: int, rf_daily: float) -> WindowStats:
    nav = _sanitize_date_index(nav, name="NAV")
    if nav.empty or len(nav) < max(10, window + 2):
        return WindowStats(window, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 0)

    nav_w = nav.tail(window + 1)
    r = nav_w.pct_change().dropna()
    r = pd.to_numeric(r, errors="coerce").dropna()
    if len(r) < 10:
        return WindowStats(window, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, int(len(r)))

    ann_ret = annualize_return(r)
    ann_vol = annualize_vol(r)
    sh = sharpe_ratio(r, rf_daily=rf_daily)
    so = sortino_ratio(r, rf_daily=rf_daily)
    mdd = max_drawdown(r)
    es = expected_shortfall(r, alpha=0.05)
    sk = skewness(r)

    return WindowStats(window, ann_ret, ann_vol, sh, so, mdd, es, sk, int(r.shape[0]))


def _overlap_cov_pack(
    returns_df: pd.DataFrame,
    weights: Dict[str, float],
    window: int,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, int]:
    if returns_df is None or returns_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.Series(dtype=float), 0

    df = returns_df.sort_index().tail(window)
    df = df.replace([np.inf, -np.inf], np.nan).dropna(how="any")

    if df.empty or df.shape[0] < 20:
        return pd.DataFrame(), pd.DataFrame(), pd.Series(dtype=float), int(df.shape[0])

    cov = covariance_annualized(df)
    corr = correlation_matrix(df)
    w = pd.Series(weights).reindex(df.columns).fillna(0.0).to_dict()
    rc = risk_contribution(w, cov)
    return cov, corr, rc, int(df.shape[0])


def _contrib_to_return(
    nav: pd.Series,
    value_map: Dict[str, pd.Series],
    window: int,
) -> List[Dict[str, Any]]:
    nav = _sanitize_date_index(nav, name="NAV")
    if nav.empty or len(nav) < window + 1:
        return []

    nav_w = nav.tail(window + 1)
    nav0 = float(nav_w.iloc[0])
    if nav0 <= 0:
        return []

    out: List[Dict[str, Any]] = []
    idx = nav_w.index

    for k, vs in (value_map or {}).items():
        vs = _sanitize_date_index(vs, name=k).reindex(idx).ffill()
        if vs.isna().all():
            continue
        v0 = float(vs.iloc[0])
        v1 = float(vs.iloc[-1])
        pnl = v1 - v0
        contrib = pnl / nav0
        out.append({"asset": k, "contrib": float(contrib), "pnl": float(pnl)})

    out.sort(key=lambda x: x["contrib"], reverse=True)
    return out

def _compute_beta_pack(port_ret: pd.Series, bench_ret: pd.Series) -> Dict[str, float]:
    """
    Return: beta, beta_down (only market-down days), corr
    """
    port_ret = _sanitize_date_index(port_ret, name="PORT_RET")
    bench_ret = _sanitize_date_index(bench_ret, name="BENCH_RET")

    df = pd.concat([port_ret, bench_ret], axis=1).dropna()
    if df.shape[0] < 30:
        return {"beta": float("nan"), "beta_down": float("nan"), "corr": float("nan"), "n": float(df.shape[0])}

    p = df.iloc[:, 0].values
    b = df.iloc[:, 1].values

    var_b = float(np.var(b))
    beta = float(np.cov(p, b)[0, 1] / var_b) if var_b > 0 else float("nan")
    corr = float(np.corrcoef(p, b)[0, 1]) if (np.std(p) > 0 and np.std(b) > 0) else float("nan")

    # downside beta: only days when benchmark < 0
    mask = b < 0
    if np.sum(mask) >= 20:
        p2 = p[mask]
        b2 = b[mask]
        var_b2 = float(np.var(b2))
        beta_down = float(np.cov(p2, b2)[0, 1] / var_b2) if var_b2 > 0 else float("nan")
    else:
        beta_down = float("nan")

    return {"beta": beta, "beta_down": beta_down, "corr": corr, "n": float(df.shape[0])}


def _build_riskonly_portfolio_returns(
    prices_ffill: pd.DataFrame,
    weights_risk: Dict[str, float],
    risk_keys: List[str],
) -> pd.Series:
    """
    RiskOnly daily return = sum_i w_i * r_i  (weights_risk already normalized to 1)
    """
    if prices_ffill is None or prices_ffill.empty:
        return pd.Series(dtype=float, name="RISKONLY_RET")

    cols = [c for c in prices_ffill.columns if c in risk_keys]
    if not cols:
        return pd.Series(dtype=float, name="RISKONLY_RET")

    px = prices_ffill[cols].copy().replace([np.inf, -np.inf], np.nan).ffill()
    rets = px.pct_change().replace([np.inf, -np.inf], np.nan)

    w = pd.Series(weights_risk).reindex(cols).fillna(0.0)
    if float(w.sum()) <= 0:
        return pd.Series(dtype=float, name="RISKONLY_RET")

    # weighted sum; keep NaN rows if any NaN => then dropna later when align with benchmark
    port = rets.mul(w, axis=1).sum(axis=1)
    port.name = "RISKONLY_RET"
    return port


# =========================
# Tactical (Breadth/MA50 + Momentum)
# =========================
def _compute_tactical(
    nav_cal: pd.Series,
    prices_ffill: pd.DataFrame,
    weights_all: Dict[str, float],
    alloc: Dict[str, float],
    risk_keys: List[str],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    # ---- Cash band
    cash_w = float(alloc.get("CASH", 0.0) or 0.0)
    lo, hi = CASH_BAND_DEFAULT
    if cash_w < lo:
        cash_state = "BELOW_BAND"
    elif cash_w > hi:
        cash_state = "ABOVE_BAND"
    else:
        cash_state = "IN_BAND"

    out["cash"] = {"cash_weight": cash_w, "band": [lo, hi], "state": cash_state}

    # ---- Momentum from NAV calendar
    nav_cal = _sanitize_date_index(nav_cal, name="NAV")
    mom = {"mom_5d": None, "mom_10d": None, "mom_30d": None, "mom_90d": None}
    if len(nav_cal) >= 95:
        def _mom(k: int) -> Optional[float]:
            if len(nav_cal) < k + 1:
                return None
            a = float(nav_cal.iloc[-(k + 1)])
            b = float(nav_cal.iloc[-1])
            if a <= 0:
                return None
            return (b / a) - 1.0

        mom["mom_5d"] = _mom(5)
        mom["mom_10d"] = _mom(10)
        mom["mom_30d"] = _mom(30)
        mom["mom_90d"] = _mom(90)
    out["momentum"] = mom

    # ---- Breadth / MA50
    breadth: Dict[str, Any] = {"n_positions": 0, "pct_above_ma50": None, "w_pct_above_ma50": None, "per_asset": []}

    if prices_ffill is None or prices_ffill.empty:
        out["breadth"] = breadth
    else:
        cols = [c for c in prices_ffill.columns if c in risk_keys]
        px = prices_ffill[cols].copy() if cols else pd.DataFrame()
        px = px.replace([np.inf, -np.inf], np.nan).ffill()

        per_asset = []
        npos = 0
        above_cnt = 0
        w_above = 0.0
        w_sum = 0.0

        for k in cols:
            s = pd.to_numeric(px[k], errors="coerce").dropna()
            if s.empty or len(s) < 55:
                continue
            ma50 = s.rolling(50).mean()
            last = float(s.iloc[-1])
            ma = float(ma50.iloc[-1]) if not math.isnan(float(ma50.iloc[-1])) else float("nan")
            if (not np.isfinite(last)) or (not np.isfinite(ma)) or ma <= 0:
                continue

            above = bool(last > ma)
            dist = (last / ma) - 1.0

            w = float(weights_all.get(k, 0.0) or 0.0)
            # breadth is usually on positions only (exclude tiny weights)
            if w <= 0:
                continue

            npos += 1
            if above:
                above_cnt += 1
                w_above += w
            w_sum += w

            per_asset.append({"asset": k, "w": w, "above": above, "dist": float(dist)})

        pct_above = (above_cnt / npos) if npos > 0 else None
        w_pct_above = (w_above / w_sum) if w_sum > 0 else None

        breadth["n_positions"] = int(npos)
        breadth["pct_above_ma50"] = float(pct_above) if pct_above is not None else None
        breadth["w_pct_above_ma50"] = float(w_pct_above) if w_pct_above is not None else None

        per_asset.sort(key=lambda r: float(r.get("w", 0.0)), reverse=True)
        breadth["per_asset"] = per_asset

        out["breadth"] = breadth

    # ---- Signals (simple, explainable)
    sig: Dict[str, str] = {}

    p = out.get("breadth", {}).get("pct_above_ma50", None)
    if isinstance(p, (int, float)):
        if p >= 0.60:
            sig["breadth_state"] = "Bullish breadth"
        elif p <= 0.40:
            sig["breadth_state"] = "Weak breadth"
        else:
            sig["breadth_state"] = "Mixed breadth"
    else:
        sig["breadth_state"] = "N/A"

    m5 = out.get("momentum", {}).get("mom_5d", None)
    m10 = out.get("momentum", {}).get("mom_10d", None)
    if isinstance(m5, (int, float)) and isinstance(m10, (int, float)):
        if (m5 > 0) and (m10 > 0):
            sig["momentum_state"] = "Positive"
        elif (m5 < 0) and (m10 < 0):
            sig["momentum_state"] = "Negative"
        else:
            sig["momentum_state"] = "Mixed"
    else:
        sig["momentum_state"] = "N/A"

    out["signals"] = sig

    # ---- Decision (placeholder; final decision should also incorporate regime + RC)
    # Keep it conservative to avoid noise.
    rules = []
    if out["cash"]["state"] == "BELOW_BAND":
        rules.append("Cash < 10%: pause adds unless highest-confidence setup.")
    if out["cash"]["state"] == "ABOVE_BAND":
        rules.append("Cash > 40%: consider deploying 5–10% NAV only if regime is Stable.")

    # breadth based
    if sig.get("breadth_state") == "Weak breadth":
        action = "REDUCE / DEFENSIVE"
        bias = "risk-off"
        rules.append("Breadth weak: trim high-RC names first; avoid adding.")
    elif sig.get("breadth_state") == "Bullish breadth" and sig.get("momentum_state") == "Positive":
        action = "HOLD / SELECTIVE ADD"
        bias = "risk-on selective"
        rules.append("Breadth + momentum supportive: add only into best setups; respect max_pos.")
    else:
        action = "HOLD"
        bias = "neutral"
        rules.append("Mixed signals: hold core; only tactical add with confirmation.")

    out["decision"] = {"action": action, "bias": bias, "rules": rules, "notes": ""}

    return out


# =========================
# Main API v3
# =========================
async def generate_pm_grade_report_v3(user_id: int, mode: str = "compact") -> Dict[str, Any]:
    state = load_portfolio_state(user_id)
    base = (state.get("base") or "VND").upper().strip()
    holdings: List[Dict[str, Any]] = state.get("holdings") or []
    if not holdings:
        return {"ok": False, "error": "Chưa có holdings trong DB. Hãy nhập danh mục trước."}

    fx = _fx_usdt_vnd()

    vn_syms = [h["symbol"].upper().strip() for h in holdings if (h.get("asset_type") or "").upper().strip() == "VN" and h.get("symbol")]
    cr_syms_raw = [h["symbol"].upper().strip() for h in holdings if (h.get("asset_type") or "").upper().strip() == "CRYPTO" and h.get("symbol")]
    cr_syms = [(s if s.endswith("USDT") else s + "USDT") for s in cr_syms_raw]

    last_vn = fetch_vn_last_prices(vn_syms) if vn_syms else {}
    last_crypto = fetch_crypto_last_prices(cr_syms) if cr_syms else {}

    nav, weights_all, alloc, pnl, pnl_pct, last_prices, pos_value, cost_value = _compute_nav_weights_and_values(
        base=base,
        holdings=holdings,
        last_vn=last_vn,
        last_crypto=last_crypto,
        fx_usdt_vnd=fx,
    )

    cash_value = float(sum(v for k, v in pos_value.items() if k.startswith("CASH:")))
    risk_keys = [k for k in pos_value.keys() if (k.startswith("VN:") or k.startswith("CRYPTO:"))]

    weights_risk = {k: float(weights_all.get(k, 0.0)) for k in risk_keys}
    ssum = float(sum(weights_risk.values()))
    if ssum > 0:
        weights_risk = {k: v / ssum for k, v in weights_risk.items()}

    end_dt = pd.Timestamp(datetime.now().date())
    start_dt = end_dt - pd.Timedelta(days=420)

    # ---- Price history maps
    warn: List[str] = []

    vn_prices_map: Dict[str, pd.Series] = {}
    if fetch_vn_prices_map and vn_syms:
        raw = fetch_vn_prices_map(vn_syms, lookback_days=450)  # type: ignore
        for sym, obj in (raw or {}).items():
            sym_u = str(sym).upper().strip()
            k = _asset_key("VN", sym_u)

            s: Optional[pd.Series] = None
            if isinstance(obj, pd.Series):
                s = obj
            elif isinstance(obj, pd.DataFrame):
                for c in ["close", "Close", "closeprice", "close_price"]:
                    if c in obj.columns:
                        s = obj[c]
                        break

            if s is not None:
                s = _sanitize_date_index(s, name=k)
                s = _maybe_scale_vn_series(sym_u, s, last_vn)   # ✅ FIX 1000x ở đây
                vn_prices_map[k] = s
    elif vn_syms:
        warn.append("fetch_vn_prices_map missing => MA50/Breadth may be limited for VN.")

    cr_prices_map: Dict[str, pd.Series] = {}
    if fetch_crypto_prices_map and cr_syms:
        rawc = fetch_crypto_prices_map(cr_syms, lookback_days=450)  # type: ignore
        for sym, obj in (rawc or {}).items():
            k = _asset_key("CRYPTO", sym)
            if isinstance(obj, pd.Series):
                cr_prices_map[k] = obj
            elif isinstance(obj, pd.DataFrame):
                for c in ["close", "Close", "c", "close_price"]:
                    if c in obj.columns:
                        cr_prices_map[k] = obj[c]
                        break
    elif cr_syms:
        warn.append("fetch_crypto_prices_map missing => MA50/Breadth may be limited for Crypto.")

    # ---- Calendar NAV
    nav_cal, value_map, prices_ffill = _build_calendar_nav_series(
        risk_pos_value_now={k: float(pos_value.get(k, 0.0)) for k in risk_keys},
        last_prices_by_key=last_prices,
        vn_prices=vn_prices_map,
        cr_prices=cr_prices_map,
        cash_value=cash_value,
        start_date=start_dt,
        end_date=end_dt,
    )

    perf60 = _window_stats_from_nav(nav_cal, window=60, rf_daily=RF_DAILY)
    perf180 = _window_stats_from_nav(nav_cal, window=180, rf_daily=RF_DAILY)

    # ---- Fetch VNIndex return series
    vnindex_prices = {}
    vnindex_series = None

    try:
        raw_index = fetch_vn_prices_map(["VNINDEX"], lookback_days=450)
        if raw_index and "VNINDEX" in raw_index:
            obj = raw_index["VNINDEX"]
            if isinstance(obj, pd.Series):
                vnindex_series = obj
            elif isinstance(obj, pd.DataFrame):
                for c in ["close", "Close"]:
                    if c in obj.columns:
                        vnindex_series = obj[c]
                        break
    except Exception:
        vnindex_series = None

    
        # ---- Overlap covariance: daily returns from prices_ffill (risk assets only)
    asset_prices = prices_ffill.copy()
    if not asset_prices.empty:
        cols = [c for c in asset_prices.columns if c in risk_keys]
        asset_prices = asset_prices[cols] if cols else asset_prices

    returns_assets = asset_prices.pct_change() if not asset_prices.empty else pd.DataFrame()
    returns_assets = returns_assets.replace([np.inf, -np.inf], np.nan)

    cov60, corr60, rc60, obs60 = _overlap_cov_pack(returns_assets, weights_risk, window=60)
    cov180, corr180, rc180, obs180 = _overlap_cov_pack(returns_assets, weights_risk, window=180)
    
    # ---- Regime
    class _Pack:
        def __init__(self, ann_vol, es95, skew, corr, rc):
            self.ann_vol = ann_vol
            self.es95 = es95
            self.skew = skew
            self.corr = corr
            self.rc = rc

    pack60_for_regime = _Pack(perf60.ann_vol, perf60.es95, perf60.skew, corr60, rc60)
    pack180_for_regime = _Pack(perf180.ann_vol, perf180.es95, perf180.skew, corr180, rc180)
    regime: RegimeShift = compute_regime_shift(pack60_for_regime, pack180_for_regime)

    contrib60 = _contrib_to_return(nav_cal, value_map, window=60)
    contrib180 = _contrib_to_return(nav_cal, value_map, window=180)

    #Beta is only meaningful if we have a valid benchmark series (e.g., VNIndex) and sufficient NAV history
    beta60 = {"beta": np.nan, "beta_down": np.nan, "corr": np.nan}
    beta180 = {"beta": np.nan, "beta_down": np.nan, "corr": np.nan}

    if vnindex_series is not None:
        vnindex_series = _sanitize_date_index(vnindex_series, name="VNINDEX")

        vnindex_ret = vnindex_series.pct_change().dropna()
        nav_ret = nav_cal.pct_change().dropna()

        beta60 = _compute_beta_pack(nav_ret.tail(60), vnindex_ret.tail(60))
        beta180 = _compute_beta_pack(nav_ret.tail(180), vnindex_ret.tail(180))

        # =========================
    # Beta_RiskOnly vs VNINDEX
    # =========================
    beta_riskonly_60 = {"beta": np.nan, "beta_down": np.nan, "corr": np.nan, "n": np.nan}
    beta_riskonly_180 = {"beta": np.nan, "beta_down": np.nan, "corr": np.nan, "n": np.nan}

    # build risk-only portfolio return series
    riskonly_ret = _build_riskonly_portfolio_returns(prices_ffill, weights_risk, risk_keys)

    # fetch VNINDEX price series (prefer prices_map)
    vnindex_series = None
    if fetch_vn_prices_map:
        try:
            raw_b = fetch_vn_prices_map(["VNINDEX"], lookback_days=450)  # type: ignore
            obj = (raw_b or {}).get("VNINDEX")
            if isinstance(obj, pd.Series):
                vnindex_series = obj
            elif isinstance(obj, pd.DataFrame):
                for c in ["close", "Close", "closeprice", "close_price"]:
                    if c in obj.columns:
                        vnindex_series = obj[c]
                        break
        except Exception:
            vnindex_series = None

    if vnindex_series is not None:
        vnindex_series = _sanitize_date_index(vnindex_series, name="VNINDEX")
        vnindex_ret = vnindex_series.pct_change().replace([np.inf, -np.inf], np.nan)

        beta_riskonly_60 = _compute_beta_pack(riskonly_ret.tail(60), vnindex_ret.tail(60))
        beta_riskonly_180 = _compute_beta_pack(riskonly_ret.tail(180), vnindex_ret.tail(180))
    else:
        warn.append("VNINDEX prices missing => cannot compute Beta_RiskOnly.")

    # ---- Tactical (Breadth/MA50 + Momentum + Cash band)
    tactical = _compute_tactical(
        nav_cal=nav_cal,
        prices_ffill=prices_ffill,
        weights_all=weights_all,
        alloc=alloc,
        risk_keys=risk_keys,
    )

    # Optional: adjust tactical decision with regime signal (light touch)
    try:
        if regime and getattr(regime, "label", "") in ("Watch", "Shift"):
            tactical_dec = tactical.get("decision", {}) or {}
            tactical_rules = tactical_dec.get("rules", []) or []
            tactical_rules.insert(0, f"Regime={regime.label}: prioritize risk control; avoid adding into rising corr/vol.")
            tactical_dec["rules"] = tactical_rules[:6]
            if regime.label == "Shift":
                tactical_dec["action"] = "REDUCE / DEFENSIVE"
                tactical_dec["bias"] = "risk-off"
            tactical["decision"] = tactical_dec
    except Exception:
        pass

    if DEBUG:
        try:
            print("[Task3] nav=", nav, "cash_w=", alloc.get("CASH"))
            print("[Task3] nav_cal tail:", nav_cal.tail(3).to_dict())
            print("[Task3] perf60 obs=", perf60.n_obs, "perf180 obs=", perf180.n_obs)
            print("[Task3] overlap obs60=", obs60, "obs180=", obs180)
            print("[Task3] breadth:", tactical.get("breadth"))
        except Exception:
            pass

    return {
        "ok": True,
        "base": base,
        "fx_usdt_vnd": fx,
        "nav": float(nav),
        "nav_calendar": nav_cal,  # optional debug
        "allocation": alloc,
        "weights": weights_all,
        "weights_risk": weights_risk,
        "last_prices": last_prices,
        "pos_value": pos_value,
        "cost_value": cost_value,
        "pnl_unreal": float(pnl),
        "pnl_unreal_pct": float(pnl_pct),

        "perf60": perf60,
        "perf180": perf180,

        "cov60": cov60,
        "corr60": corr60,
        "rc60": rc60,
        "obs60_overlap": obs60,
        "cov180": cov180,
        "corr180": corr180,
        "rc180": rc180,
        "obs180_overlap": obs180,

        "contrib60": contrib60,
        "contrib180": contrib180,
        "beta60": beta60,
        "beta180": beta180,
        "beta_riskonly_60": beta_riskonly_60,
        "beta_riskonly_180": beta_riskonly_180,

        "tactical": tactical,

        "regime": regime,
        "gold_status": "N/A",
        "meta_policy": {
            "risk": state.get("risk"),
            "max_pos": state.get("max_pos"),
            "crypto_cap": state.get("crypto_cap"),
            "min_cash": state.get("min_cash"),
            "cash_band_default": "10–40%",
        },
        "warnings": warn,
    }


# ============================================================
# Backward-compatible wrapper (UI expects this)
# ============================================================
async def generate_full_portfolio_report(user_id: int, mode: str = "compact"):
    """
    UI expects: List[discord.Embed]
    """
    report = await generate_pm_grade_report_v3(user_id=user_id, mode=mode)

    import discord

    if not report.get("ok", False):
        e = discord.Embed(title="❌ Portfolio report error", description=str(report.get("error", "Unknown error")))
        return [e]

    try:
        from features.portfolio import formatter as F
        if mode == "details":
            return list(F.build_details_embeds(report))
        return list(F.build_compact_embeds(report))
    except Exception as ex:
        e = discord.Embed(title="📊 PM Dashboard (v3)", description=f"Formatter error: {ex}")
        return [e]