#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/phase2_feature_pipeline.py
Phase 2 — Daily Feature Pipeline for Propensity-to-Buy Model

Input:   data/ohlcv/{SYMBOL}.parquet  (from Phase 1A)
Output:  data/features/{YYYY-MM-DD}.parquet

Feature groups (~93 technical + 11 fundamental + hardcheck):
  A/B  — Momentum + Trend position (RSI, MACD, EMA, ADX, BB)
  C    — Risk/Quality (Sharpe, Beta, Alpha, Vol)
  J    — Heikin-Ashi Trend Oscillator (buytrend)
  K    — Mean Reversion (RSI2, Price/RSI divergence 26-bar)
  L    — Ichimoku Kumo A, Supertrend
  M    — Divergences (RSI/MFI bear div, kqrsimf)
  I    — Candlestick patterns (bearish reversals)
  F    — Fundamentals (ROE, ROA, PE, PB, debt_equity, gross_margin, roe_yoy, earnings_growth, staleness)
  HC   — Hardcheck flags

Usage:
    python -m pipeline.phase2_feature_pipeline                    # today
    python -m pipeline.phase2_feature_pipeline --date 2025-12-31  # specific date
    python -m pipeline.phase2_feature_pipeline --check            # show stored dates
    python -m pipeline.phase2_feature_pipeline --backfill --start 2024-01-01  # range
"""

from __future__ import annotations

import argparse
import logging
import math
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

for _log in ("vnstock", "vnai", "urllib3", "requests"):
    logging.getLogger(_log).setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────
FEATURES_DIR    = ROOT / "data" / "features"
OHLCV_DIR       = ROOT / "data" / "ohlcv"
RF_ANNUAL       = 0.07
MIN_ROWS_RISK   = 60    # minimum for Sharpe/Beta
MIN_ROWS_TECH   = 35    # minimum for MACD
MIN_ROWS_FULL   = 252   # preferred for 12m metrics
VNINDEX_SYMBOL  = "VNINDEX"

# ─── Safe math helpers ───────────────────────────────────────────────────────


def _sf(x) -> Optional[float]:
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def _nan(x) -> float:
    v = _sf(x)
    return v if v is not None else float("nan")


# ═════════════════════════════════════════════════════════════════════════════
# GROUP A/B — MOMENTUM + TREND POSITION
# ═════════════════════════════════════════════════════════════════════════════


def _rsi(close: pd.Series, period: int = 14) -> Optional[float]:
    if len(close) < period + 5:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    loss = (-delta).clip(lower=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return _sf((100 - 100 / (1 + rs)).iloc[-1])


def _rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    loss = (-delta).clip(lower=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _macd_hist(close: pd.Series) -> Optional[pd.Series]:
    if len(close) < 35:
        return None
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    sig = macd.ewm(span=9, adjust=False).mean()
    return macd - sig


def _mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> Optional[float]:
    if len(close) < period + 2:
        return None
    tp = (high + low + close) / 3
    mf = tp * volume
    prev_tp = tp.shift(1)
    pos = mf.where(tp > prev_tp, 0.0)
    neg = mf.where(tp < prev_tp, 0.0)
    mfr = pos.rolling(period).sum() / neg.rolling(period).sum().replace(0, np.nan)
    return _sf((100 - 100 / (1 + mfr)).iloc[-1])


def _mfi_series(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    tp = (high + low + close) / 3
    mf = tp * volume
    prev_tp = tp.shift(1)
    pos = mf.where(tp > prev_tp, 0.0)
    neg = mf.where(tp < prev_tp, 0.0)
    mfr = pos.rolling(period).sum() / neg.rolling(period).sum().replace(0, np.nan)
    return 100 - 100 / (1 + mfr)


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Optional[float]:
    if len(close) < period + 2:
        return None
    prev_c = close.shift(1)
    tr = pd.concat([high - low, (high - prev_c).abs(), (low - prev_c).abs()], axis=1).max(axis=1)
    return _sf(tr.rolling(period).mean().iloc[-1])


def _compute_trend_group(df: pd.DataFrame) -> dict:
    """Groups A + B: momentum + trend position features."""
    feat: dict = {}
    c = df["close"]
    h = df["high"]
    l = df["low"]
    v = df["volume"]
    n = len(df)

    # ── RSI 14 ──────────────────────────────────────────────────────────────
    feat["rsi_14"] = _nan(_rsi(c))

    # ── RSI 2 (Group K: mean reversion) ─────────────────────────────────────
    feat["rsi_2"] = _nan(_rsi(c, period=2))

    # ── MACD ────────────────────────────────────────────────────────────────
    hist = _macd_hist(c)
    if hist is not None:
        feat["macd_hist"]             = _nan(hist.iloc[-1])
        feat["macd_slope"]            = _nan(hist.iloc[-1] - hist.iloc[-3]) if len(hist) >= 3 else float("nan")
        feat["macd_consecutive_rising"] = float(
            len(hist) >= 3 and float(hist.iloc[-1]) > float(hist.iloc[-2]) > float(hist.iloc[-3])
        )
        feat["macd_hist_flipped"] = float(
            float(hist.iloc[-1]) < 0 and len(hist) >= 2 and float(hist.iloc[-2]) >= 0
        )
    else:
        for k in ("macd_hist", "macd_slope", "macd_consecutive_rising", "macd_hist_flipped"):
            feat[k] = float("nan")

    # ── MFI 14 ──────────────────────────────────────────────────────────────
    feat["mfi_14"] = _nan(_mfi(h, l, c, v))

    # ── Volume ratio (today / avg 20 days prior) ─────────────────────────────
    if n >= 22:
        avg20 = float(v.iloc[-21:-1].mean())
        feat["vol_ratio_20d"] = _nan(float(v.iloc[-1]) / avg20) if avg20 > 0 else float("nan")
    else:
        feat["vol_ratio_20d"] = float("nan")

    # ── ATR 14 ──────────────────────────────────────────────────────────────
    feat["atr_14"] = _nan(_atr(h, l, c, 14))

    # ── EMA positions ────────────────────────────────────────────────────────
    for span in [9, 26, 200]:
        ema = c.ewm(span=span, adjust=False).mean()
        feat[f"ema{span}"] = _nan(ema.iloc[-1])

    if n >= 26 and _sf(feat.get("ema9")) and _sf(feat.get("ema26")):
        e9, e26 = feat["ema9"], feat["ema26"]
        feat["ema9_vs_ema26_pct"] = _nan((e9 - e26) / e26 * 100) if e26 != 0 else float("nan")
        # EMA cross: today ema9 > ema26, yesterday ema9 <= ema26
        if n >= 27:
            e9s = c.ewm(span=9, adjust=False).mean()
            e26s = c.ewm(span=26, adjust=False).mean()
            feat["ema_cross_up"] = float(
                float(e9s.iloc[-1]) > float(e26s.iloc[-1]) and
                float(e9s.iloc[-2]) <= float(e26s.iloc[-2])
            )
        else:
            feat["ema_cross_up"] = float("nan")
    else:
        feat["ema9_vs_ema26_pct"] = float("nan")
        feat["ema_cross_up"] = float("nan")

    # ── MA50 position ────────────────────────────────────────────────────────
    ma50 = c.rolling(50).mean()
    feat["ma50"] = _nan(ma50.iloc[-1])
    if _sf(feat.get("ma50")) and _sf(c.iloc[-1]):
        feat["price_vs_ma50"]  = _nan((c.iloc[-1] - feat["ma50"]) / feat["ma50"] * 100)
        feat["above_ma50"]     = float(c.iloc[-1] > feat["ma50"])
    else:
        feat["price_vs_ma50"] = float("nan")
        feat["above_ma50"]    = float("nan")

    # ── EMA200 position ──────────────────────────────────────────────────────
    if n >= 200 and _sf(feat.get("ema200")):
        feat["price_vs_ema200"] = _nan((c.iloc[-1] - feat["ema200"]) / feat["ema200"] * 100)
    else:
        feat["price_vs_ema200"] = float("nan")

    # ── ADX 14 ───────────────────────────────────────────────────────────────
    try:
        import ta
        feat["adx_14"] = _nan(ta.trend.adx(h, l, c, window=14).iloc[-1])
    except Exception:
        feat["adx_14"] = float("nan")

    # ── Returns ──────────────────────────────────────────────────────────────
    for days, key in [(5, "return_5d"), (20, "return_20d"), (21, "ret_1m")]:
        feat[key] = _nan(c.pct_change(days).iloc[-1] * 100) if n > days else float("nan")

    # ── Bollinger Band width percentile ──────────────────────────────────────
    try:
        import ta
        bb_bnd = ta.volatility.BollingerBands(c, window=20, window_dev=2)
        bb_w = (bb_bnd.bollinger_hband() - bb_bnd.bollinger_lband()) / bb_bnd.bollinger_mavg()
        feat["bb_width_pct"] = _nan(bb_w.rolling(min(252, n)).rank(pct=True).iloc[-1])
    except Exception:
        feat["bb_width_pct"] = float("nan")

    # ── ATR spike ────────────────────────────────────────────────────────────
    try:
        import ta
        atr10 = ta.volatility.average_true_range(h, l, c, window=10)
        median60 = atr10.rolling(60).median()
        feat["atr_spike"] = float(
            _sf(atr10.iloc[-1]) is not None and
            _sf(median60.iloc[-1]) is not None and
            float(atr10.iloc[-1]) > 1.5 * float(median60.iloc[-1])
        )
    except Exception:
        feat["atr_spike"] = float("nan")

    # ── Distribution days (close < prev close, last 15 bars) ─────────────────
    if n >= 15:
        feat["dist_days_15"] = float((c.diff() < 0).tail(15).sum())
    else:
        feat["dist_days_15"] = float("nan")

    # ── Trend fatigue (EMA9 flat over 30 bars) ───────────────────────────────
    if n >= 30:
        ema9_s = c.ewm(span=9, adjust=False).mean()
        base = float(ema9_s.iloc[-30])
        if base != 0:
            dev = (ema9_s.iloc[-29:] - base).abs() / base * 100
            feat["is_fatigue"] = float(dev.mean() < 0.4)
        else:
            feat["is_fatigue"] = float("nan")
    else:
        feat["is_fatigue"] = float("nan")

    return feat


# ═════════════════════════════════════════════════════════════════════════════
# GROUP C — RISK / QUALITY (Sharpe, Beta, Alpha)
# ═════════════════════════════════════════════════════════════════════════════


def _compute_risk_group(
    close: pd.Series,
    vnindex_close: pd.Series,
    rf_annual: float = RF_ANNUAL,
) -> dict:
    """Compute Sharpe, Beta, Alpha, Correlation metrics."""
    feat: dict = {}
    rf_daily = (1 + rf_annual) ** (1 / 252) - 1

    stock_ret = close.pct_change().dropna()
    bench_ret = vnindex_close.reindex(stock_ret.index, method="ffill").pct_change().dropna()
    aligned = pd.concat(
        [stock_ret.rename("stock"), bench_ret.rename("bench")], axis=1
    ).dropna()

    if len(aligned) < MIN_ROWS_RISK:
        return feat  # not enough data, return empty

    # ── Sharpe 12m / 24m ────────────────────────────────────────────────────
    for months, key in [(12, "sharpe_12m"), (24, "sharpe_24m")]:
        window = months * 21
        s = aligned.tail(window)
        if len(s) >= MIN_ROWS_RISK:
            exc = s["stock"] - rf_daily
            std = exc.std()
            feat[key] = _nan(exc.mean() / std * math.sqrt(252)) if std > 0 else float("nan")

    # ── Bench Sharpe 12m (for comparison) ────────────────────────────────────
    s12 = aligned.tail(252)
    if len(s12) >= MIN_ROWS_RISK:
        exc_b = s12["bench"] - rf_daily
        std_b = exc_b.std()
        feat["bench_sharpe_12m"] = _nan(exc_b.mean() / std_b * math.sqrt(252)) if std_b > 0 else float("nan")

    # ── Beta 12m + asymmetric ────────────────────────────────────────────────
    if len(s12) >= MIN_ROWS_RISK:
        cov_m = np.cov(s12["stock"], s12["bench"])
        var_b = cov_m[1, 1]
        if var_b > 0:
            feat["beta_12m"]  = _nan(cov_m[0, 1] / var_b)
            feat["corr_24m"]  = _nan(s12["stock"].corr(s12["bench"]))
        for mask, key in [
            (s12["bench"] > 0, "beta_up_12m"),
            (s12["bench"] < 0, "beta_dn_12m"),
        ]:
            sub = s12[mask]
            if len(sub) >= 20:
                cv = np.cov(sub["stock"], sub["bench"])
                vb = cv[1, 1]
                feat[key] = _nan(cv[0, 1] / vb) if vb > 0 else float("nan")

    # ── Beta asymmetry ───────────────────────────────────────────────────────
    b_up = _sf(feat.get("beta_up_12m"))
    b_dn = _sf(feat.get("beta_dn_12m"))
    if b_up is not None and b_dn is not None:
        feat["beta_asymmetry"] = _nan(b_up - b_dn)

    # ── Excess returns (Alpha) ────────────────────────────────────────────────
    for days, key in [(63, "excess_ret_3m"), (126, "excess_ret_6m")]:
        s = aligned.tail(days)
        if len(s) >= max(10, days // 4):
            feat[key] = _nan((1 + s["stock"]).prod() - (1 + s["bench"]).prod())

    # ── Annualised volatility ─────────────────────────────────────────────────
    if len(aligned) >= 21:
        feat["vol_annual"] = _nan(aligned["stock"].std() * math.sqrt(252))

    # ── Vol spike ratio (1m vs 6m) ────────────────────────────────────────────
    v1m = aligned.tail(21)["stock"].std() if len(aligned) >= 21 else None
    v6m = aligned.tail(126)["stock"].std() if len(aligned) >= 60 else None
    if v1m and v6m and v6m > 0:
        feat["vol_spike_ratio"] = _nan(v1m / v6m)

    return feat


# ═════════════════════════════════════════════════════════════════════════════
# GROUP J — HEIKIN-ASHI TREND OSCILLATOR
# ═════════════════════════════════════════════════════════════════════════════


def _compute_ha_group(df: pd.DataFrame) -> dict:
    """Heikin-Ashi based trend oscillator (from buytrend script)."""
    feat: dict = {}
    if len(df) < 10:
        return feat

    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    ha_c = (o + h + l + c) / 4
    ha_o = c.shift(1)                        # simplified HA open
    ha_h = pd.concat([h, o, c], axis=1).max(axis=1)
    ha_l = pd.concat([l, o, c], axis=1).min(axis=1)

    ma_c = ha_c.ewm(span=9, adjust=False).mean()
    ma_o = ha_o.ewm(span=9, adjust=False).mean()
    ma_h = ha_h.ewm(span=9, adjust=False).mean()
    ma_l = ha_l.ewm(span=9, adjust=False).mean()

    denom = (ma_h - ma_l).replace(0, np.nan)
    trend = 100 * (ma_c - ma_o) / denom

    feat["ha_trend"]    = _nan(trend.iloc[-1])
    feat["ha_trend_t1"] = _nan(trend.iloc[-2]) if len(trend) >= 2 else float("nan")
    feat["ha_trend_t2"] = _nan(trend.iloc[-3]) if len(trend) >= 3 else float("nan")

    # Crossover: trend turned positive from negative (BUY1 signal)
    if len(trend) >= 3:
        feat["ha_trend_crossover"] = float(
            _sf(trend.iloc[-1]) is not None and _sf(trend.iloc[-2]) is not None and
            _sf(trend.iloc[-3]) is not None and
            float(trend.iloc[-1]) > 0 and float(trend.iloc[-2]) > 0 and float(trend.iloc[-3]) <= 0
        )
    else:
        feat["ha_trend_crossover"] = float("nan")

    return feat


# ═════════════════════════════════════════════════════════════════════════════
# GROUP K — MEAN REVERSION (RSI2 + 26-bar Price/RSI Divergence)
# ═════════════════════════════════════════════════════════════════════════════


def _compute_mean_reversion_group(df: pd.DataFrame) -> dict:
    feat: dict = {}
    c = df["close"]
    n = len(df)

    if n < 27:
        return feat

    rsi14 = _rsi_series(c, 14)
    low26 = c.rolling(26).min()
    rsi_low26 = rsi14.rolling(26).min()

    feat["lowest_close_26"]  = _nan(low26.iloc[-1])
    feat["lowest_rsi14_26"]  = _nan(rsi_low26.iloc[-1])

    if _sf(low26.iloc[-1]) and _sf(c.iloc[-1]) and low26.iloc[-1] > 0:
        feat["price_vs_low26_pct"] = _nan((c.iloc[-1] - low26.iloc[-1]) / low26.iloc[-1] * 100)

    rsi14_last    = _sf(rsi14.iloc[-1])
    rsi_low26_val = _sf(rsi_low26.iloc[-1])
    close_last    = _sf(c.iloc[-1])
    low26_val     = _sf(low26.iloc[-1])

    if rsi14_last is not None and rsi_low26_val is not None:
        feat["rsi_vs_low26_divergence"] = _nan(rsi14_last - rsi_low26_val)

    # BUY2 setup: price at/below 26-low, RSI making higher low, RSI was oversold
    feat["buy2_setup"] = float(
        close_last is not None and low26_val is not None and
        rsi14_last is not None and rsi_low26_val is not None and
        close_last <= low26_val and
        rsi14_last > rsi_low26_val and
        rsi_low26_val <= 30
    )

    # BUY3 setup: extreme capitulation
    rsi2_val = _sf(_rsi(c, period=2))
    mfi_val  = _mfi(df["high"], df["low"], c, df["volume"]) if "high" in df.columns else None
    feat["buy3_setup"] = float(
        rsi2_val is not None and mfi_val is not None and
        rsi14_last is not None and
        rsi2_val <= 4 and rsi14_last < 25 and mfi_val < 20
    )

    return feat


# ═════════════════════════════════════════════════════════════════════════════
# GROUP L — ICHIMOKU KUMO A + SUPERTREND
# ═════════════════════════════════════════════════════════════════════════════


def _compute_ichimoku_st_group(df: pd.DataFrame) -> dict:
    feat: dict = {}
    h, l, c = df["high"], df["low"], df["close"]
    n = len(df)

    # ── Ichimoku Kumo A (26-period shift) ────────────────────────────────────
    if n >= 52:
        tenkan = (h.rolling(9).max() + l.rolling(9).min()) / 2
        kijun  = (h.rolling(26).max() + l.rolling(26).min()) / 2
        kumo_a = ((tenkan + kijun) / 2).shift(25)
        feat["kumo_a"] = _nan(kumo_a.iloc[-1])
        v_kumo = _sf(kumo_a.iloc[-1])
        v_c    = _sf(c.iloc[-1])
        if v_kumo and v_c and v_kumo != 0:
            feat["kumo_a_dist_pct"] = _nan((v_c - v_kumo) / v_kumo * 100)
            feat["above_kumo_a"]    = float(v_c > v_kumo)
        else:
            feat["kumo_a_dist_pct"] = float("nan")
            feat["above_kumo_a"]    = float("nan")
    else:
        for k in ("kumo_a", "kumo_a_dist_pct", "above_kumo_a"):
            feat[k] = float("nan")

    # ── Supertrend (ATR10 × 3) ───────────────────────────────────────────────
    if n >= 12:
        try:
            import ta
            atr10 = ta.volatility.average_true_range(h, l, c, window=10)
            lower_band = (h + l) / 2 - 3 * atr10
            st_dir = pd.Series(
                np.where(c > lower_band, 1, -1),
                index=c.index,
            )
            feat["st_dir"] = float(st_dir.iloc[-1])

            # Detect recent bullish flip (bearish→bullish within last 9 bars)
            st_change = st_dir.diff()
            bullish_flips = st_change[st_change == 2]
            if len(bullish_flips) > 0:
                last_flip_pos = c.index.get_loc(bullish_flips.index[-1])
                bars_since_flip = (n - 1) - last_flip_pos
                feat["st_recently_flipped_bullish"] = float(bars_since_flip <= 9)
            else:
                feat["st_recently_flipped_bullish"] = 0.0
        except Exception:
            feat["st_dir"] = float("nan")
            feat["st_recently_flipped_bullish"] = float("nan")
    else:
        feat["st_dir"] = float("nan")
        feat["st_recently_flipped_bullish"] = float("nan")

    return feat


# ═════════════════════════════════════════════════════════════════════════════
# GROUP M — DIVERGENCES + QUALITY FLAGS
# ═════════════════════════════════════════════════════════════════════════════


def _compute_divergence_group(df: pd.DataFrame) -> dict:
    feat: dict = {}
    c = df["close"]
    h = df["high"]
    l = df["low"]
    v = df["volume"]
    n = len(df)

    if n < 14:
        return feat

    LB = 14
    avg_close = c.rolling(LB).mean()
    rsi14 = _rsi_series(c, 14)
    avg_rsi = rsi14.rolling(LB).mean()

    feat["rsi_bear_div"]       = float(bool(c.iloc[-1] >= avg_close.iloc[-1] and rsi14.iloc[-1] < avg_rsi.iloc[-1]))
    feat["rsi_superoverbought"] = float(rsi14.rolling(18).max().iloc[-1] >= 85 if n >= 18 else False)
    feat["rsi_overbought"]      = float(rsi14.iloc[-1] >= 70)
    feat["rsi_oversold"]        = float(rsi14.iloc[-1] <= 30)

    mfi14 = _mfi_series(h, l, c, v, 14)
    avg_mfi = mfi14.rolling(LB).mean()
    feat["mfi_bear_div"] = float(
        bool(c.iloc[-1] >= avg_close.iloc[-1] and mfi14.iloc[-1] < avg_mfi.iloc[-1])
    )

    rsi_val = _sf(rsi14.iloc[-1])
    mfi_val = _sf(mfi14.iloc[-1])
    feat["kqrsimf"] = float(
        rsi_val is not None and mfi_val is not None and
        rsi_val > mfi_val and mfi_val < 55
    )

    return feat


# ═════════════════════════════════════════════════════════════════════════════
# GROUP I — CANDLESTICK PATTERNS (bearish reversals)
# ═════════════════════════════════════════════════════════════════════════════


def _compute_candle_group(df: pd.DataFrame) -> dict:
    feat = {
        "candle_evening_star":         0.0,
        "candle_bearish_engulfing":    0.0,
        "candle_shooting_star":        0.0,
        "candle_doji_resistance":      0.0,
    }
    if len(df) < 3 or not all(c in df.columns for c in ["open", "high", "low", "close"]):
        return feat

    try:
        # Reuse existing signal_engine detection
        from features.quant.signal_engine import detect_candle_patterns
        flags = detect_candle_patterns(df)
        feat["candle_evening_star"]      = float(flags.get("evening_star", False))
        feat["candle_bearish_engulfing"] = float(flags.get("bearish_engulfing_top", False))
        feat["candle_shooting_star"]     = float(flags.get("shooting_star_ma50plus", False))
        feat["candle_doji_resistance"]   = float(flags.get("doji_resistance", False))
    except Exception:
        pass

    return feat


# ═════════════════════════════════════════════════════════════════════════════
# HARDCHECK LAYER
# ═════════════════════════════════════════════════════════════════════════════


def hardcheck(feat: dict, avg_val_21d: float = float("nan")) -> Tuple[bool, List[str]]:
    """
    Apply all hardcheck rules.
    Returns (pass_bool, list_of_failed_rules).
    pass=True means symbol passes and enters ML scoring.
    """
    failures: List[str] = []

    def _fail(rule: str):
        failures.append(rule)

    # H1: Thanh khoản < 3 tỷ/ngày (chỉ loại cổ phiếu gần như không có thanh khoản)
    if math.isfinite(avg_val_21d) and avg_val_21d < 3.0:
        _fail(f"H1:low_liquidity({avg_val_21d:.1f}B)")

    # H2: Giá < 10,000 VND
    close_ema200 = feat.get("ema200", float("nan"))
    # Use actual close from features — we store it separately
    close_vnd = feat.get("close_vnd", float("nan"))
    if math.isfinite(close_vnd) and close_vnd < 10_000:
        _fail(f"H2:price_below_10k({close_vnd:.0f})")

    # H4: Distribution days ≥ 12 (trong 15 ngày phải có ≥ 12 ngày phân phối mới loại)
    dd = feat.get("dist_days_15", float("nan"))
    if math.isfinite(dd) and dd >= 12:
        _fail(f"H4:dist_days({int(dd)})")

    # H6: ADX < 15 AND is_fatigue (siết: 13→15, tín hiệu tốt nhất +10% discrimination)
    adx = feat.get("adx_14", float("nan"))
    fatigue = feat.get("is_fatigue", float("nan"))
    if math.isfinite(adx) and math.isfinite(fatigue) and adx < 15 and fatigue == 1.0:
        _fail(f"H6:adx_fatigue(adx={adx:.1f})")

    # H8: bỏ — RSI overbought có discrimination âm (-3%), momentum VN có xu hướng continuation

    # H9: MACD declining 3 consecutive sessions
    hist = feat.get("macd_hist", float("nan"))
    slope = feat.get("macd_slope", float("nan"))
    if math.isfinite(hist) and math.isfinite(slope) and hist < 0 and slope < 0 and feat.get("macd_consecutive_rising", 1.0) == 0.0:
        _fail("H9:macd_consecutive_falling")

    # H10: Volume ratio < 0.6x (nới: 0.7→0.6, loại bớt false positive)
    vr = feat.get("vol_ratio_20d", float("nan"))
    if math.isfinite(vr) and vr < 0.6:
        _fail(f"H10:vol_dry({vr:.2f}x)")

    # H12: MFI bearish divergence + xác nhận RSI cũng overbought (nới: thêm điều kiện)
    rsi = feat.get("rsi_14", float("nan"))
    if feat.get("mfi_bear_div", 0.0) == 1.0 and math.isfinite(rsi) and rsi > 60:
        _fail("H12:mfi_bear_div")

    # H13: Supertrend recently flipped bullish (retest risk)
    if feat.get("st_recently_flipped_bullish", 0.0) == 1.0:
        _fail("H13:st_flip_recent")

    # H15: ADX < 13 only (no established trend)
    if math.isfinite(adx) and adx < 13 and not math.isfinite(fatigue):
        _fail(f"H15:adx_weak({adx:.1f})")

    # H17: bỏ — below_kumo_a có discrimination âm (-1.9%), loại nhầm winner trong 10d horizon

    # Bearish candle reversals (at top)
    for ckey, hkey in [
        ("candle_evening_star",      "HI:evening_star"),
        ("candle_bearish_engulfing", "HI:bearish_engulfing"),
        ("candle_shooting_star",     "HI:shooting_star"),
    ]:
        if feat.get(ckey, 0.0) == 1.0:
            _fail(hkey)

    passed = len(failures) == 0
    return passed, failures


# ═════════════════════════════════════════════════════════════════════════════
# MARKET REGIME (once per day, broadcast to all symbols)
# ═════════════════════════════════════════════════════════════════════════════


def _compute_market_regime(vnindex_df: pd.DataFrame) -> dict:
    """Run regime detection from market_regime.py on pre-loaded VNINDEX data."""
    if vnindex_df is None or vnindex_df.empty:
        return {}
    try:
        from features.daily_recap.market_regime import compute_regime_features, score_regime
        feat = compute_regime_features.__wrapped__(vnindex_df) if hasattr(
            compute_regime_features, "__wrapped__"
        ) else None
    except Exception:
        feat = None

    if feat:
        label, score, bd = score_regime(feat)
        result = {
            "regime_label":         label,
            "regime_score":         score,
            "regime_trend":         bd.get("trend", float("nan")),
            "regime_breadth":       bd.get("breadth", float("nan")),
            "regime_flow":          bd.get("flow", float("nan")),
            "regime_vol":           bd.get("vol", float("nan")),
        }
        result.update(_compute_vni_momentum(vnindex_df))
        return result

    # Minimal fallback: compute directly
    try:
        c = vnindex_df["close"]
        ema200 = c.ewm(span=200, adjust=False).mean()
        ema9   = c.ewm(span=9, adjust=False).mean()
        ema26  = c.ewm(span=26, adjust=False).mean()
        price_vs_ema200 = (c.iloc[-1] - ema200.iloc[-1]) / ema200.iloc[-1] * 100 if len(c) >= 200 else 0
        ema_cross_up    = float(ema9.iloc[-1] > ema26.iloc[-1])
        base = {
            "regime_label":     "unknown",
            "regime_score":     float("nan"),
            "regime_trend":     float(price_vs_ema200 > 0 and ema_cross_up),
            "regime_breadth":   float("nan"),
            "regime_flow":      float("nan"),
            "regime_vol":       float("nan"),
        }
        base.update(_compute_vni_momentum(vnindex_df))
        return base
    except Exception:
        return {}


def _compute_vni_momentum(vnindex_df: pd.DataFrame) -> dict:
    """
    Short-term VNINDEX momentum features — broadcast to all symbols for a given date.
    Captures near-term market tailwind/headwind missing from long-term regime features.
    """
    feat: dict = {}
    if vnindex_df is None or vnindex_df.empty:
        return feat
    try:
        df = vnindex_df.copy()
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").reset_index(drop=True)
        c = pd.to_numeric(df["close"], errors="coerce")
        n = len(c)

        # Short-term returns (market tailwind/headwind)
        for days, key in [(5, "vni_ret_5d"), (10, "vni_ret_10d"), (20, "vni_ret_20d")]:
            feat[key] = _nan(c.pct_change(days).iloc[-1] * 100) if n > days else float("nan")

        # RSI(14) on VNINDEX — is market overbought/oversold?
        feat["vni_rsi_14"] = _nan(_rsi(c, period=14))

        # MACD histogram sign — index momentum direction
        if n >= 35:
            ema9  = c.ewm(span=9,  adjust=False).mean()
            ema26 = c.ewm(span=26, adjust=False).mean()
            hist  = ema9 - ema26
            feat["vni_macd_hist"]     = _nan(hist.iloc[-1])
            feat["vni_macd_positive"] = float(hist.iloc[-1] > 0) if math.isfinite(_nan(hist.iloc[-1])) else float("nan")
        else:
            feat["vni_macd_hist"]     = float("nan")
            feat["vni_macd_positive"] = float("nan")

        # Distance from MA50 — medium-term trend position
        if n >= 50:
            ma50 = c.rolling(50).mean()
            feat["vni_vs_ma50_pct"] = _nan((c.iloc[-1] - ma50.iloc[-1]) / ma50.iloc[-1] * 100)
            feat["vni_above_ma50"]  = float(c.iloc[-1] > ma50.iloc[-1])
        else:
            feat["vni_vs_ma50_pct"] = float("nan")
            feat["vni_above_ma50"]  = float("nan")

        # 20-day realised volatility — high vol = risky environment
        if n >= 21:
            feat["vni_vol_20d"] = _nan(c.pct_change().tail(20).std() * (252 ** 0.5) * 100)
        else:
            feat["vni_vol_20d"] = float("nan")

        # Distance from 52-week high — market breadth proxy
        if n >= 252:
            high_52w = c.tail(252).max()
            feat["vni_vs_52w_high_pct"] = _nan((c.iloc[-1] - high_52w) / high_52w * 100)
        else:
            feat["vni_vs_52w_high_pct"] = float("nan")

    except Exception:
        pass
    return feat


# ═════════════════════════════════════════════════════════════════════════════
# GROUP W — MULTI-TIMEFRAME (Weekly)
# ═════════════════════════════════════════════════════════════════════════════

MIN_ROWS_WEEKLY = 80   # ~16 weeks minimum for reliable weekly indicators


def _to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample daily OHLCV to weekly bars.
    Week ends on the last trading day of the week (Saturday anchor → last available day).
    Returns DataFrame with columns: open, high, low, close, volume.
    """
    d = df.copy()
    d["time"] = pd.to_datetime(d["time"])
    d = d.set_index("time").sort_index()

    agg = {
        "open":   "first",
        "high":   "max",
        "low":    "min",
        "close":  "last",
        "volume": "sum",
    }
    # Only aggregate columns that exist
    agg = {k: v for k, v in agg.items() if k in d.columns}

    weekly = d.resample("W").agg(agg).dropna(subset=["close"])
    return weekly.reset_index()


def _compute_weekly_group(df: pd.DataFrame) -> dict:
    """
    Multi-timeframe features computed on weekly bars.

    Features:
        weekly_rsi_14           — RSI(14) on weekly close (14 weeks ≈ 3.5 months)
        weekly_rsi_7            — RSI(7) on weekly close (momentum faster signal)
        weekly_macd_hist        — MACD histogram on weekly close
        weekly_macd_slope       — MACD hist slope (current - 2 weeks ago)
        weekly_macd_cross_up    — 1 if MACD hist flipped positive this week
        weekly_vol_ratio_4w     — This week's volume / 4-week avg volume
        weekly_close_vs_ema20w  — close / EMA(20) on weekly (20 weeks ≈ 5 months)
        weekly_momentum_4w      — (close - close[4w ago]) / close[4w ago]
        weekly_momentum_13w     — (close - close[13w ago]) / close[13w ago]  (quarter)
        weekly_pos_in_52w       — position in 52-week high/low range [0, 1]
        weekly_consec_up        — consecutive weeks closing higher than previous
    """
    defaults = {
        "weekly_rsi_14":         float("nan"),
        "weekly_rsi_7":          float("nan"),
        "weekly_macd_hist":      float("nan"),
        "weekly_macd_slope":     float("nan"),
        "weekly_macd_cross_up":  float("nan"),
        "weekly_vol_ratio_4w":   float("nan"),
        "weekly_close_vs_ema20w": float("nan"),
        "weekly_momentum_4w":    float("nan"),
        "weekly_momentum_13w":   float("nan"),
        "weekly_pos_in_52w":     float("nan"),
        "weekly_consec_up":      float("nan"),
    }

    if df is None or len(df) < MIN_ROWS_WEEKLY:
        return defaults

    try:
        wdf = _to_weekly(df)
        if len(wdf) < 20:
            return defaults

        c = pd.to_numeric(wdf["close"], errors="coerce").ffill()
        v = pd.to_numeric(wdf["volume"], errors="coerce").fillna(0) if "volume" in wdf.columns else None

        feat = dict(defaults)

        # ── Weekly RSI ─────────────────────────────────────────────────────────
        if len(c) >= 15:
            feat["weekly_rsi_14"] = _nan(_rsi(c, period=14))
        if len(c) >= 8:
            feat["weekly_rsi_7"]  = _nan(_rsi(c, period=7))

        # ── Weekly MACD ────────────────────────────────────────────────────────
        if len(c) >= 35:  # need 26+9 = 35 weeks
            ema12  = c.ewm(span=12, adjust=False).mean()
            ema26  = c.ewm(span=26, adjust=False).mean()
            macd   = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            hist   = macd - signal

            feat["weekly_macd_hist"] = _nan(hist.iloc[-1])
            if len(hist) >= 3:
                feat["weekly_macd_slope"] = _nan(hist.iloc[-1] - hist.iloc[-3])
            if len(hist) >= 2:
                # Cross up: histogram was negative last week, positive this week
                feat["weekly_macd_cross_up"] = float(
                    hist.iloc[-1] > 0 and hist.iloc[-2] <= 0
                )

        # ── Weekly Volume ratio ────────────────────────────────────────────────
        if v is not None and len(v) >= 5:
            avg4w = v.iloc[-5:-1].mean()
            if avg4w > 0:
                feat["weekly_vol_ratio_4w"] = _nan(float(v.iloc[-1]) / avg4w)

        # ── Weekly EMA20 ───────────────────────────────────────────────────────
        if len(c) >= 21:
            ema20w = c.ewm(span=20, adjust=False).mean()
            if ema20w.iloc[-1] > 0:
                feat["weekly_close_vs_ema20w"] = _nan(c.iloc[-1] / ema20w.iloc[-1])

        # ── Weekly Momentum ────────────────────────────────────────────────────
        if len(c) >= 5:
            c0_4w = c.iloc[-5]
            if c0_4w > 0:
                feat["weekly_momentum_4w"] = _nan((c.iloc[-1] - c0_4w) / c0_4w)

        if len(c) >= 14:
            c0_13w = c.iloc[-14]
            if c0_13w > 0:
                feat["weekly_momentum_13w"] = _nan((c.iloc[-1] - c0_13w) / c0_13w)

        # ── 52-week position ───────────────────────────────────────────────────
        if len(c) >= 52:
            window52 = c.iloc[-52:]
            hi52 = window52.max()
            lo52 = window52.min()
            rng  = hi52 - lo52
            if rng > 0:
                feat["weekly_pos_in_52w"] = _nan((c.iloc[-1] - lo52) / rng)

        # ── Consecutive up-weeks ───────────────────────────────────────────────
        if len(c) >= 6:
            diff    = c.diff().iloc[-6:]
            consec  = 0
            for val in reversed(diff.values[1:]):  # skip NaN at start
                if val > 0:
                    consec += 1
                else:
                    break
            feat["weekly_consec_up"] = float(consec)

        return feat

    except Exception:
        return defaults


# ═════════════════════════════════════════════════════════════════════════════
# GROUP N — FOREIGN INVESTOR FLOW
# ═════════════════════════════════════════════════════════════════════════════


def _compute_alpha158_group(df: pd.DataFrame) -> dict:
    """
    Alpha158-inspired features (Microsoft Qlib):

    KBAR — single-candle body/range stats:
      alpha158_kmid   = (close - open) / open          # body %
      alpha158_klen   = (high - low) / open             # range %

    RSQR{w} — R-squared of linear trend (trend quality):
      alpha158_rsqr_5/10/20  — 0=choppy, 1=clean trend

    CORR{w} — Rolling correlation: daily_return vs log(volume_change):
      alpha158_corr_5/10/20  — +1=price up on high vol (healthy), -1=weak move

    CORD{w} — Rolling correlation variant: daily_return vs volume_change%:
      alpha158_cord_5/10/20
    """
    feat: dict = {
        "alpha158_kmid":    float("nan"),
        "alpha158_klen":    float("nan"),
        "alpha158_rsqr_5":  float("nan"),
        "alpha158_rsqr_10": float("nan"),
        "alpha158_rsqr_20": float("nan"),
        "alpha158_corr_5":  float("nan"),
        "alpha158_corr_10": float("nan"),
        "alpha158_corr_20": float("nan"),
        "alpha158_cord_5":  float("nan"),
        "alpha158_cord_10": float("nan"),
        "alpha158_cord_20": float("nan"),
    }

    try:
        closes  = df["close"].astype(float).values
        opens   = df["open"].astype(float).values if "open" in df.columns else closes
        highs   = df["high"].astype(float).values if "high" in df.columns else closes
        lows    = df["low"].astype(float).values  if "low"  in df.columns else closes
        volumes = df["volume"].astype(float).values if "volume" in df.columns else None

        n = len(closes)

        # ── KBAR: last candle ─────────────────────────────────────────────────
        if n >= 1 and opens[-1] > 0:
            feat["alpha158_kmid"] = float((closes[-1] - opens[-1]) / opens[-1])
            feat["alpha158_klen"] = float((highs[-1]  - lows[-1])  / opens[-1])

        # ── RSQR{w}: R-squared of linear trend ───────────────────────────────
        from scipy.stats import linregress as _linreg
        for w in [5, 10, 20]:
            if n < w:
                continue
            tail = closes[-w:]
            x    = np.arange(w, dtype=float)
            try:
                _, _, r, _, _ = _linreg(x, tail)
                feat[f"alpha158_rsqr_{w}"] = float(r ** 2)
            except Exception:
                pass

        # ── CORR/CORD{w}: price-volume rolling correlation ────────────────────
        if volumes is not None and len(volumes) >= 22:
            daily_ret = np.diff(closes) / (closes[:-1] + 1e-9)   # (n-1,)
            log_vol_chg = np.log(volumes[1:] / (volumes[:-1] + 1e-9) + 1)  # (n-1,)
            vol_chg_pct = (volumes[1:] - volumes[:-1]) / (volumes[:-1] + 1e-9)

            for w in [5, 10, 20]:
                if len(daily_ret) < w:
                    continue
                r_tail  = daily_ret[-w:]
                lv_tail = log_vol_chg[-w:]
                vc_tail = vol_chg_pct[-w:]
                # Avoid constant arrays (corr undefined)
                if r_tail.std() > 1e-9 and lv_tail.std() > 1e-9:
                    feat[f"alpha158_corr_{w}"] = float(np.corrcoef(r_tail, lv_tail)[0, 1])
                if r_tail.std() > 1e-9 and vc_tail.std() > 1e-9:
                    feat[f"alpha158_cord_{w}"] = float(np.corrcoef(r_tail, vc_tail)[0, 1])

    except Exception:
        pass

    return feat


def _compute_foreign_group(
    foreign_df: pd.DataFrame,
    target_date: Optional[str],
    avg_val_21d_b: float = float("nan"),
) -> dict:
    """
    Compute foreign investor flow features from pre-loaded per-symbol data.

    Original features (v3a):
      foreign_net_val_5d      — sum of net_val over last 5 trading days (VND)
      foreign_net_val_20d     — sum of net_val over last 20 trading days (VND)
      foreign_net_ratio_5d    — foreign_net_val_5d / avg_daily_value_21d (dimensionless)
      foreign_net_ratio_20d   — foreign_net_val_20d / avg_daily_value_21d
      foreign_buy_pct_5d      — buy_val / (buy_val + sell_val) rolling 5d (0–1)
      foreign_net_days_5d     — count of days with net_val > 0 in last 5 days (0–5)
      foreign_net_days_20d    — count of days with net_val > 0 in last 20 days (0–20)

    New features (v3b — foreign flow momentum):
      foreign_trend_5_20      — net_val_5d / net_val_20d: acceleration (>1 = accelerating)
      foreign_cum_flow_63d    — cumulative net_val over 63 trading days (~3 tháng)
      foreign_flow_reversal   — 1 nếu dấu 5d khác dấu 20d (reversal signal)
      foreign_buy_pct_20d     — buy_val / (buy_val + sell_val) rolling 20d

    New features (v3e — interaction / quality):
      foreign_alignment       — 1 nếu net_val_5d và cum_flow_63d cùng chiều (short/long aligned)
      foreign_selling_decel   — 1 nếu |flow_last21d| < |flow_prev42d| (selling slowing down)
      foreign_net_days_pct_20d — fraction of last 20 days with net_val > 0 (0–1)
    """
    feat: dict = {
        "foreign_net_val_5d":    float("nan"),
        "foreign_net_val_20d":   float("nan"),
        "foreign_net_ratio_5d":  float("nan"),
        "foreign_net_ratio_20d": float("nan"),
        "foreign_buy_pct_5d":    float("nan"),
        "foreign_net_days_5d":   float("nan"),
        "foreign_net_days_20d":  float("nan"),
        # New v3b features
        "foreign_trend_5_20":    float("nan"),
        "foreign_cum_flow_63d":  float("nan"),
        "foreign_flow_reversal": float("nan"),
        "foreign_buy_pct_20d":   float("nan"),
        # New v3e interaction features
        "foreign_alignment":          float("nan"),
        "foreign_selling_decel":      float("nan"),
        "foreign_net_days_pct_20d":   float("nan"),
    }

    if foreign_df is None or foreign_df.empty:
        return feat

    try:
        fdf = foreign_df.copy()
        fdf["trading_date"] = pd.to_datetime(fdf["trading_date"])
        if target_date:
            fdf = fdf[fdf["trading_date"] <= pd.Timestamp(target_date)]
        fdf = fdf.sort_values("trading_date").reset_index(drop=True)

        if len(fdf) < 3:
            return feat

        last5  = fdf.tail(5)
        last20 = fdf.tail(20)
        last63 = fdf.tail(63)

        net5  = float(last5["net_val"].sum())
        net20 = float(last20["net_val"].sum())
        net63 = float(last63["net_val"].sum())

        feat["foreign_net_val_5d"]  = net5
        feat["foreign_net_val_20d"] = net20

        # Normalize by avg daily value
        avg_val_vnd = avg_val_21d_b * 1e9 if math.isfinite(avg_val_21d_b) and avg_val_21d_b > 0 else None
        if avg_val_vnd:
            feat["foreign_net_ratio_5d"]  = _nan(net5  / (avg_val_vnd * 5))
            feat["foreign_net_ratio_20d"] = _nan(net20 / (avg_val_vnd * 20))

        # Buy % of total foreign turnover (5d)
        buy5   = float(last5["buy_val"].sum())
        sell5  = float(last5["sell_val"].sum())
        total5 = buy5 + sell5
        if total5 > 0:
            feat["foreign_buy_pct_5d"] = _nan(buy5 / total5)

        # Buy % of total foreign turnover (20d)
        buy20   = float(last20["buy_val"].sum())
        sell20  = float(last20["sell_val"].sum())
        total20 = buy20 + sell20
        if total20 > 0:
            feat["foreign_buy_pct_20d"] = _nan(buy20 / total20)

        # Count of net-positive days
        feat["foreign_net_days_5d"]  = float((last5["net_val"]  > 0).sum())
        feat["foreign_net_days_20d"] = float((last20["net_val"] > 0).sum())

        # ── New v3b features ─────────────────────────────────────────────────

        # Trend / acceleration: 5d vs 20d flow direction strength
        # >1 = flow accelerating, <1 = decelerating, sign change = reversal
        if abs(net20) > 1e6:  # tránh chia số quá nhỏ
            feat["foreign_trend_5_20"] = _nan(net5 / (net20 / 4.0))
            # Note: net20/4 normalise về cùng 5-day basis

        # Cumulative 63-day flow (3 tháng) — capture xu hướng trung hạn
        feat["foreign_cum_flow_63d"] = net63

        # Reversal signal: 1 nếu 5d và 20d flow ngược chiều nhau
        # Ví dụ: net20 > 0 (mua ròng 1 tháng) nhưng net5 < 0 (đang bán ra 1 tuần)
        if abs(net5) > 1e6 and abs(net20) > 1e6:
            feat["foreign_flow_reversal"] = float(
                (net5 > 0) != (net20 > 0)  # True=1 nếu ngược chiều
            )

        # ── New v3e interaction features ─────────────────────────────────────

        # Alignment: short-term (5d) và long-term (63d) cùng chiều không?
        # 1 = aligned (both buying or both selling) → consistent signal
        # 0 = contradicting (tactical buying in structural downtrend, or vice versa)
        if abs(net5) > 1e6 and abs(net63) > 1e6:
            feat["foreign_alignment"] = float((net5 > 0) == (net63 > 0))

        # Selling deceleration: bán ròng đang chậm lại không?
        # So sánh 21 ngày gần nhất vs 42 ngày trước đó (cùng trong 63d window)
        # 1 = selling is slowing (potential accumulation bottom forming)
        # 0 = selling accelerating or buying throughout
        if len(fdf) >= 63:
            flow_last21 = float(fdf.tail(21)["net_val"].sum())
            flow_prev42 = float(fdf.tail(63).head(42)["net_val"].sum())
            # Only meaningful when there IS selling (negative flows)
            if flow_last21 < 0 or flow_prev42 < 0:
                feat["foreign_selling_decel"] = float(
                    abs(flow_last21) < abs(flow_prev42)
                )

        # Net days pct 20d: fraction of last 20 days với net buying
        # Đo consistency của buying (cao hơn foreign_net_days_20d vì normalized)
        feat["foreign_net_days_pct_20d"] = float((last20["net_val"] > 0).mean())

    except Exception:
        pass

    return feat


# ═════════════════════════════════════════════════════════════════════════════
# MAIN: COMPUTE ALL FEATURES FOR A SINGLE SYMBOL
# ═════════════════════════════════════════════════════════════════════════════


def compute_features(
    df: pd.DataFrame,
    vnindex_df: Optional[pd.DataFrame] = None,
    target_date: Optional[str] = None,
    foreign_df: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Compute all features for one symbol up to target_date.

    Args:
        df:           OHLCV DataFrame (full history)
        vnindex_df:   VNINDEX OHLCV (for Beta/Sharpe)
        target_date:  slice df to this date (inclusive); None = use all

    Returns flat dict of features. NaN where insufficient data.
    """
    if df is None or df.empty:
        return {}

    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)

    if target_date:
        df = df[df["time"] <= pd.Timestamp(target_date)]

    if len(df) < MIN_ROWS_TECH:
        return {}

    feat: dict = {}

    # Base price (for hardcheck H2)
    feat["close_vnd"]   = float(df["close"].iloc[-1])
    feat["date"]        = str(df["time"].iloc[-1].date())

    # Avg daily value (for hardcheck H1)
    if len(df) >= 21 and "volume" in df.columns:
        df21     = df.tail(21)
        vols     = pd.to_numeric(df21["volume"], errors="coerce").fillna(0)
        closes   = pd.to_numeric(df21["close"],  errors="coerce").fillna(0)
        feat["avg_val_21d_b"] = float((vols * closes).mean()) / 1e9  # tỷ VND
    else:
        feat["avg_val_21d_b"] = float("nan")

    # ── Feature groups ────────────────────────────────────────────────────────
    feat.update(_compute_trend_group(df))
    feat.update(_compute_ha_group(df))
    feat.update(_compute_mean_reversion_group(df))
    feat.update(_compute_ichimoku_st_group(df))
    feat.update(_compute_divergence_group(df))
    feat.update(_compute_candle_group(df))

    # ── Risk group (needs VNINDEX) ────────────────────────────────────────────
    if vnindex_df is not None and not vnindex_df.empty:
        vni = vnindex_df.copy()
        vni["time"] = pd.to_datetime(vni["time"])
        if target_date:
            vni = vni[vni["time"] <= pd.Timestamp(target_date)]
        if not vni.empty:
            feat.update(
                _compute_risk_group(
                    df.set_index("time")["close"],
                    vni.set_index("time")["close"],
                )
            )

    # ── Weekly multi-timeframe group ──────────────────────────────────────────
    feat.update(_compute_weekly_group(df))

    # ── Alpha158 group (Qlib-inspired: RSQR, CORR, CORD, KBAR) ───────────────
    feat.update(_compute_alpha158_group(df))

    # ── Foreign flow group (needs pre-loaded foreign data) ───────────────────
    feat.update(_compute_foreign_group(foreign_df, target_date, feat.get("avg_val_21d_b", float("nan"))))

    return feat


# ═════════════════════════════════════════════════════════════════════════════
# PIPELINE RUNNER
# ═════════════════════════════════════════════════════════════════════════════


def _load_parquet(symbol: str, cache: Optional[dict] = None) -> pd.DataFrame:
    if cache is not None and symbol.upper() in cache:
        return cache[symbol.upper()]
    path = OHLCV_DIR / f"{symbol.upper()}.parquet"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(path)
        df["time"] = pd.to_datetime(df["time"])
        return df.sort_values("time").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def _preload_ohlcv(symbols: List[str]) -> dict:
    """Load all OHLCV parquets into memory once for backfill."""
    cache: dict = {}
    for sym in symbols:
        df = _load_parquet(sym)
        if not df.empty:
            cache[sym.upper()] = df
    return cache


def _preload_fundamentals() -> pd.DataFrame:
    """Load all fundamental parquets into a single DataFrame for fast point-in-time lookup."""
    try:
        from pipeline.phase1b_fundamental_store import DATA_DIR as FUND_DIR
        frames = []
        for fp in FUND_DIR.glob("*.parquet"):
            if fp.name.startswith("_"):
                continue
            try:
                frames.append(pd.read_parquet(fp).reset_index())
            except Exception:
                pass
        if not frames:
            return pd.DataFrame()
        all_data = pd.concat(frames, ignore_index=True)
        all_data["release_date"] = pd.to_datetime(all_data["release_date"])
        return all_data.sort_values("release_date")
    except Exception:
        return pd.DataFrame()


def _fundamentals_as_of_cached(target_date: str, fund_cache: pd.DataFrame) -> pd.DataFrame:
    """Point-in-time lookup from pre-loaded fundamental DataFrame (avoids repeated disk reads)."""
    if fund_cache.empty:
        return pd.DataFrame()
    target = pd.Timestamp(target_date)
    available = fund_cache[fund_cache["release_date"] <= target]
    if available.empty:
        return pd.DataFrame()

    import numpy as np
    # Most recent quarter per symbol
    latest = available.sort_values("release_date").groupby("symbol").last()

    fund_cols = ["roe", "roa", "pe", "pb", "debt_equity",
                 "gross_margin", "asset_turnover", "net_interest_margin",
                 "roe_yoy", "earnings_growth"]
    result = pd.DataFrame(index=latest.index)
    for col in fund_cols:
        result[f"fund_{col}"] = latest[col] if col in latest.columns else np.nan
    result["fund_staleness_days"] = (target - latest["release_date"]).dt.days
    result.index.name = "symbol"
    return result


def _preload_foreign(symbols: List[str]) -> dict:
    """Load all foreign flow parquets into memory once for backfill."""
    try:
        from pipeline.phase1c_foreign_store import load_foreign
    except ImportError:
        return {}
    cache: dict = {}
    for sym in symbols:
        df = load_foreign(sym)
        if not df.empty:
            cache[sym.upper()] = df
    return cache


def run(
    target_date: Optional[str] = None,
    symbols: Optional[List[str]] = None,
    save: bool = True,
    ohlcv_cache: Optional[dict] = None,
    fund_cache: Optional[pd.DataFrame] = None,
    foreign_cache: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Compute feature matrix for all symbols on target_date.

    Args:
        target_date:   "YYYY-MM-DD"; default = latest trading day
        symbols:       list of symbols; default = all in data/ohlcv/
        save:          save to data/features/{date}.parquet
        ohlcv_cache:   pre-loaded {symbol: df} dict
        fund_cache:    pre-loaded fundamental DataFrame
        foreign_cache: pre-loaded {symbol: foreign_df} dict (phase 1C)

    Returns:
        DataFrame [symbol × feature] with hardcheck_pass column
    """
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    # Resolve target date
    if target_date is None:
        target_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Load universe from manifest if not specified
    if symbols is None:
        manifest_path = OHLCV_DIR / "_manifest.json"
        if manifest_path.exists():
            import json
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            symbols = [s for s in manifest if s != VNINDEX_SYMBOL]
        else:
            symbols = [p.stem for p in OHLCV_DIR.glob("*.parquet") if p.stem != "_manifest"]

    symbols = [s.upper() for s in symbols if s.upper() != VNINDEX_SYMBOL]

    logger.info("=" * 60)
    logger.info("Phase 2 Features  |  date=%s  |  symbols=%d", target_date, len(symbols))
    logger.info("=" * 60)

    # ── Auto-load foreign cache if not provided ───────────────────────────────
    if foreign_cache is None:
        foreign_cache = _preload_foreign(symbols)
        if foreign_cache:
            logger.info("Foreign cache: %d symbols loaded", len(foreign_cache))
        else:
            logger.info("Foreign cache: no data (run Phase 1C to enable foreign features)")

    # ── Load VNINDEX ──────────────────────────────────────────────────────────
    vnindex_df = _load_parquet(VNINDEX_SYMBOL, cache=ohlcv_cache)
    if vnindex_df.empty:
        # Try to fetch live
        logger.warning("VNINDEX not in parquet store, fetching live...")
        try:
            from pipeline.phase1a_ohlcv_store import fetch_ohlcv_lenient
            end   = target_date
            start = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=800)).strftime("%Y-%m-%d")
            vnindex_df, _ = fetch_ohlcv_lenient(VNINDEX_SYMBOL, start, end)
        except Exception as e:
            logger.warning("VNINDEX fetch failed: %s — risk features will be NaN", e)
            vnindex_df = pd.DataFrame()

    # ── Market regime (once per day) ──────────────────────────────────────────
    regime_feat = _compute_market_regime(vnindex_df)
    regime_label = regime_feat.get("regime_label", "unknown")
    logger.info("Market regime: %s  (score=%.2f)", regime_label, regime_feat.get("regime_score", float("nan")))

    # ── Per-symbol features ───────────────────────────────────────────────────
    rows: List[dict] = []
    t0 = time.time()

    for i, sym in enumerate(symbols, 1):
        df = _load_parquet(sym, cache=ohlcv_cache)
        if df.empty:
            logger.debug("  skip %s: no parquet data", sym)
            continue

        fgn_df = foreign_cache.get(sym.upper()) if foreign_cache else None
        feat = compute_features(df, vnindex_df, target_date, foreign_df=fgn_df)
        if not feat:
            logger.debug("  skip %s: insufficient rows", sym)
            continue

        # Add regime context
        feat.update(regime_feat)

        # Hardcheck
        avg_val = feat.get("avg_val_21d_b", float("nan"))
        passed, failures = hardcheck(feat, avg_val)
        feat["hardcheck_pass"]    = int(passed)
        feat["hardcheck_reasons"] = "|".join(failures) if failures else ""
        feat["symbol"]            = sym

        rows.append(feat)

        if i % 20 == 0 or i == len(symbols):
            elapsed = time.time() - t0
            eta = elapsed / i * (len(symbols) - i)
            passed_count = sum(1 for r in rows if r.get("hardcheck_pass") == 1)
            logger.info(
                "  [%3d/%d]  processed=%d  hardcheck_pass=%d  ETA %.0fs",
                i, len(symbols), len(rows), passed_count, eta,
            )

    if not rows:
        logger.warning("No features computed for any symbol on %s", target_date)
        return pd.DataFrame()

    result_df = pd.DataFrame(rows).set_index("symbol")

    # ── Join fundamental features (point-in-time correct) ────────────────────
    try:
        if fund_cache is not None:
            fund_df = _fundamentals_as_of_cached(target_date, fund_cache)
        else:
            from pipeline.phase1b_fundamental_store import get_fundamentals_as_of
            fund_df = get_fundamentals_as_of(target_date)
        if not fund_df.empty:
            result_df = result_df.join(fund_df, how="left")
            n_fund = fund_df.shape[1]
            n_joined = result_df[fund_df.columns].notna().any(axis=1).sum()
            logger.info("Fundamentals joined: %d columns, %d/%d symbols covered", n_fund, n_joined, len(result_df))
        else:
            logger.warning("No fundamental data available for %s — run Phase 1B first", target_date)
    except Exception as e:
        logger.warning("Fundamental join skipped: %s", e)

    # Cast boolean-like columns to int (0/1) for consistent storage
    bool_cols = [c for c in result_df.columns if result_df[c].dropna().isin([0.0, 1.0]).all()]
    for col in bool_cols:
        result_df[col] = result_df[col].fillna(0).astype(int)

    # ── Sector-relative foreign flow (v3f features) ───────────────────────────
    # Requires all symbols to be processed first → computed here at day level.
    # foreign_sector_share_20d: mã chiếm bao nhiêu % foreign net flow của sector
    # foreign_sector_rank:      xếp hạng percentile trong sector (0=lowest, 1=highest)
    try:
        from features.industry.sector_library import get_sector_info as _get_sector

        # Map symbol → primary_sector
        sector_map = {}
        for sym in result_df.index:
            try:
                info = _get_sector(sym)
                sector_map[sym] = info.get("primary_sector", "Unknown") if info else "Unknown"
            except Exception:
                sector_map[sym] = "Unknown"

        result_df["_primary_sector"] = pd.Series(sector_map)

        if "foreign_net_val_20d" in result_df.columns:
            flow_col = "foreign_net_val_20d"

            # Sector total net flow (sum of all symbols in sector)
            sector_totals = (
                result_df.groupby("_primary_sector")[flow_col]
                .transform("sum")
            )

            # Share: symbol flow / sector total (NaN if sector total ≈ 0)
            result_df["foreign_sector_share_20d"] = result_df[flow_col].where(
                sector_totals.abs() > 1e8,   # ignore sectors with near-zero total flow
                other=float("nan"),
            ) / sector_totals.where(sector_totals.abs() > 1e8)

            # Rank: percentile within sector (0–1), higher = more net buying vs peers
            result_df["foreign_sector_rank"] = (
                result_df.groupby("_primary_sector")[flow_col]
                .rank(pct=True, na_option="keep")
            )

        result_df = result_df.drop(columns=["_primary_sector"])

    except Exception as _e:
        logger.warning("Sector-relative foreign flow skipped: %s", _e)

    # ── Save ─────────────────────────────────────────────────────────────────
    if save:
        out_path = FEATURES_DIR / f"{target_date}.parquet"
        result_df.to_parquet(out_path, engine="pyarrow")
        logger.info("Saved → %s  (%d symbols × %d features)", out_path, len(result_df), len(result_df.columns))

    passed_total = int(result_df["hardcheck_pass"].sum())
    logger.info(
        "Done  |  %d symbols computed  |  %d passed hardcheck  |  %.1fs",
        len(result_df), passed_total, time.time() - t0,
    )
    logger.info("=" * 60)
    return result_df


def _backfill_worker(args):
    """Worker function for parallel backfill — each process handles a date chunk."""
    start_chunk, end_chunk, symbols, force = args
    # Workers load their own caches independently (no shared memory needed)
    run_backfill(start=start_chunk, end=end_chunk, symbols=symbols, force=force, _workers=1)


def run_backfill(
    start: str,
    end: Optional[str] = None,
    symbols: Optional[List[str]] = None,
    force: bool = False,
    _workers: int = 1,
) -> None:
    """
    Compute features for every trading day from start to end.
    Skips dates that already have a parquet file unless force=True.

    Set _workers > 1 via CLI --workers to parallelize across date chunks.
    """
    if end is None:
        end = datetime.utcnow().strftime("%Y-%m-%d")

    dates = pd.bdate_range(start=start, end=end)  # business days only
    if force:
        pending = [d.strftime("%Y-%m-%d") for d in dates]
    else:
        existing = {p.stem for p in FEATURES_DIR.glob("*.parquet")}
        pending = [d.strftime("%Y-%m-%d") for d in dates if d.strftime("%Y-%m-%d") not in existing]
    logger.info("Backfill: %d dates pending (%s → %s)%s", len(pending), start, end, " [FORCE]" if force else "")

    # ── Parallel dispatch: split date list into N chunks ─────────────────────
    if _workers > 1 and len(pending) > _workers:
        import multiprocessing
        chunk_size = math.ceil(len(pending) / _workers)
        chunks = [pending[i:i + chunk_size] for i in range(0, len(pending), chunk_size)]
        args_list = [(c[0], c[-1], symbols, force) for c in chunks]
        logger.info("Parallel backfill: %d workers × ~%d dates each", len(chunks), chunk_size)
        with multiprocessing.Pool(processes=len(chunks)) as pool:
            pool.map(_backfill_worker, args_list)
        logger.info("Parallel backfill complete.")
        return
    # ─────────────────────────────────────────────────────────────────────────

    if not pending:
        logger.info("Nothing to do.")
        return

    # ── Pre-load caches once to avoid 225k disk reads ────────────────────────
    all_symbols = symbols or []
    if not all_symbols:
        import json
        manifest_path = OHLCV_DIR / "_manifest.json"
        if manifest_path.exists():
            all_symbols = list(json.loads(manifest_path.read_text(encoding="utf-8")).keys())

    logger.info("Pre-loading OHLCV into memory for %d symbols + VNINDEX ...", len(all_symbols))
    ohlcv_cache = _preload_ohlcv(all_symbols + [VNINDEX_SYMBOL])
    logger.info("  OHLCV cache: %d symbols loaded (%.0f MB est.)",
                len(ohlcv_cache),
                sum(df.memory_usage(deep=True).sum() for df in ohlcv_cache.values()) / 1e6)

    logger.info("Pre-loading fundamental data into memory ...")
    fund_cache = _preload_fundamentals()
    if not fund_cache.empty:
        logger.info("  Fundamental cache: %d rows, %d symbols",
                    len(fund_cache), fund_cache["symbol"].nunique())
    else:
        logger.warning("  No fundamental data found — run Phase 1B first")

    logger.info("Pre-loading foreign flow data into memory ...")
    foreign_cache = _preload_foreign(all_symbols)
    logger.info("  Foreign cache: %d symbols loaded", len(foreign_cache))
    # ─────────────────────────────────────────────────────────────────────────

    for i, date in enumerate(pending, 1):
        logger.info("[%d/%d] Computing features for %s", i, len(pending), date)
        run(target_date=date, symbols=symbols, save=True,
            ohlcv_cache=ohlcv_cache, fund_cache=fund_cache, foreign_cache=foreign_cache)


def show_status() -> None:
    """List all stored feature files."""
    files = sorted(FEATURES_DIR.glob("*.parquet"))
    if not files:
        print("No feature files found. Run pipeline first.")
        return

    print(f"\n{'Date':<14}  {'Symbols':>8}  {'Features':>10}  {'Passed HC':>10}")
    print("-" * 50)
    for f in files[-20:]:  # show last 20
        try:
            df = pd.read_parquet(f)
            n_feat  = len(df.columns)
            n_pass  = int(df["hardcheck_pass"].sum()) if "hardcheck_pass" in df.columns else "?"
            print(f"{f.stem:<14}  {len(df):>8}  {n_feat:>10}  {str(n_pass):>10}")
        except Exception as e:
            print(f"{f.stem:<14}  ERROR: {e}")

    print(f"\nTotal: {len(files)} dates stored at {FEATURES_DIR}")


# ─── CLI ─────────────────────────────────────────────────────────────────────


def _parse_args():
    p = argparse.ArgumentParser(description="Phase 2 — Feature Pipeline")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--check",     action="store_true", help="Show stored feature files")
    group.add_argument("--backfill",  action="store_true", help="Backfill date range")
    p.add_argument("--date",    type=str, default=None, help="Target date YYYY-MM-DD (default: today)")
    p.add_argument("--start",   type=str, default=None, help="Backfill start date")
    p.add_argument("--end",     type=str, default=None, help="Backfill end date")
    p.add_argument("--symbols", type=str, default="",   help="Comma-separated symbols override")
    p.add_argument("--force",   action="store_true",    help="Overwrite existing feature files")
    p.add_argument("--workers", type=int, default=1,    help="Parallel processes for backfill (default: 1)")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()] or None

    if args.check:
        show_status()
    elif args.backfill:
        if not args.start:
            print("--backfill requires --start YYYY-MM-DD")
            sys.exit(1)
        run_backfill(start=args.start, end=args.end, symbols=syms, force=getattr(args, "force", False), _workers=args.workers)
    else:
        run(target_date=args.date, symbols=syms)
