#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
market_regime.py (v2.0 - Optimized)
────────────────────────────────────
AgentQ — Daily Market Regime Detection for VNINDEX

OPTIMIZED LOGIC based on Daily Recap input features:
  • Layer 1 — Trend (35%):      price_vs_ema200, vs_ma50_pct, change_pct, EMA cross
  • Layer 2 — Breadth (30%):    ad_de_ratio (VN100 real data), sector alignment, flow coherence
  • Layer 3 — Money Flow (25%): foreign_flow_bil, sector rotation, ticker flow quality
  • Layer 4 — Volatility (10%): BB width percentile, ATR spike (risk signal only)

  Hard Overrides:
    • Distribution days ≥ 5 + bull regime → downgrade
    • Sector rotation breakdown → reduce score
    • Foreign selling + breadth deterioration → force ranging/bear
    • MACD flip + bull_trending → downgrade ranging
    • ADX < 15 + fatigue → force ranging
"""

import os
import sys
import inspect
import numpy as np
import pandas as pd
import ta
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
VNSTOCK_API_KEY = os.getenv("VNSTOCK_API_KEY", "").strip()
if not VNSTOCK_API_KEY:
    VNSTOCK_API_KEY = os.getenv("XNO_API_KEY", "").strip()

VNSTOCK_SOURCE = os.getenv("VNSTOCK_SOURCE", "VCI").strip().upper()
FALLBACK_SOURCES = [
    s.strip().upper()
    for s in os.getenv("VNSTOCK_FALLBACK_SOURCES", "KBS,MAS,VND").split(",")
    if s.strip()
]
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

ALLOWED_SOURCES = {"VCI", "KBS", "VND", "MAS"}

# ─────────────────────────────────────────────
# SCORING WEIGHTS (Optimized)
# ─────────────────────────────────────────────
WEIGHTS = {
    "trend": 0.35,
    "breadth": 0.30,
    "flow": 0.25,
    "volatility": 0.10,
}

# Regime thresholds
REGIME_THRESHOLDS = {
    "strong_bull": 0.75,
    "bull": 0.60,
    "recovery": 0.45,
    "ranging": 0.30,
    # below 0.30 = bear_risk
}

# ─────────────────────────────────────────────
# IMPORTS — vnstock_data
# ─────────────────────────────────────────────
try:
    from vnstock_data import Quote
except ImportError:
    sys.path.append(os.getcwd())
    try:
        from vnstock_data import Quote
    except ImportError:

        class Quote:
            pass


# ═════════════════════════════════════════════
# INFRASTRUCTURE
# ═════════════════════════════════════════════


def _safe_source(src: str) -> str:
    s = (src or "VCI").strip().upper()
    return s if s in ALLOWED_SOURCES else "VCI"


def _create_quote(symbol: str, source: str | None = None):
    src = _safe_source(source or VNSTOCK_SOURCE)
    key = VNSTOCK_API_KEY or ""
    sig = inspect.signature(Quote)
    p = sig.parameters
    try:
        kwargs = {"source": src}
        ak_name_candidates = [k for k in ["api_key", "apikey", "key"] if k in p]
        if ak_name_candidates:
            kwargs[ak_name_candidates[0]] = key
        sym_name = [k for k in ["symbol", "ticker", "code"] if k in p]
        if sym_name:
            kwargs[sym_name[0]] = symbol
            return Quote(**kwargs)
        return Quote(symbol, **kwargs)
    except Exception:
        pass
    for args, kw in [
        ((symbol, src), {}),
        ((symbol,), {"source": src}),
        ((symbol,), {}),
    ]:
        try:
            return Quote(*args, **kw)
        except Exception:
            continue
    raise RuntimeError(f"Cannot init Quote for {symbol}")


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    d = df.copy()
    d.columns = [str(c).lower().strip() for c in d.columns]
    for tcol in ["time", "date", "tradingdate", "datetime"]:
        if tcol in d.columns:
            d["time"] = pd.to_datetime(d[tcol], errors="coerce")
            break
    else:
        return pd.DataFrame()
    aliases = {
        "open": ["open", "o", "openprice"],
        "high": ["high", "h", "highprice"],
        "low": ["low", "l", "lowprice"],
        "close": ["close", "c", "closeprice", "price"],
        "volume": ["volume", "v", "vol", "totalvolume"],
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
    for c in ["open", "high", "low", "close", "volume"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return (
        out.dropna(subset=["time", "close"]).sort_values("time").reset_index(drop=True)
    )


def _fetch_history_any_source(symbol: str, start: str, end: str, interval: str = "1D"):
    sources = [VNSTOCK_SOURCE] + [s for s in FALLBACK_SOURCES if s != VNSTOCK_SOURCE]
    for src in sources:
        try:
            q = _create_quote(symbol, source=src)
            try:
                df = q.history(start=start, end=end, interval=interval)
            except Exception:
                df = q.history(start=start, end=end)
            norm = _normalize_ohlcv(df)
            if not norm.empty:
                return norm, src
        except Exception:
            continue
    return pd.DataFrame(), None


def send_discord(message: str):
    if not DISCORD_WEBHOOK_URL or "discord.com/api/webhooks" not in DISCORD_WEBHOOK_URL:
        return
    for part in [message[i : i + 2000] for i in range(0, len(message), 2000)]:
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": part}, timeout=20)
        except Exception:
            pass


# ─────────────────────────────────────────────
# MATH HELPERS
# ─────────────────────────────────────────────


def _clip(x, lo=0.0, hi=1.0):
    return (
        max(lo, min(hi, float(x)))
        if not (isinstance(x, (float, np.float64)) and np.isnan(x))
        else lo
    )


def _linear(x, lo, hi):
    if hi == lo:
        return 0.0
    return _clip((float(x) - lo) / (hi - lo))


def _tri_ideal(x, center, half_width):
    return _clip(1.0 - abs(float(x) - center) / float(half_width))


def _safe_div(a, b, default=0.5):
    try:
        if b == 0:
            return default
        return a / b
    except (TypeError, ZeroDivisionError):
        return default


# ═════════════════════════════════════════════
# SECTOR ROTATION ANALYSIS (NEW)
# ═════════════════════════════════════════════


def analyze_sector_rotation(flow_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze sector rotation quality from Daily Recap flow data.

    Returns:
        sector_alignment: How coherent the sector flows are (0-1)
        rotation_breadth: Number of sectors with significant flow
        rotation_quality: Direction consistency of flows
    """
    inflow = flow_data.get("inflow", [])
    outflow = flow_data.get("outflow", [])

    if not inflow and not outflow:
        return {
            "sector_alignment": 0.5,
            "rotation_breadth": 0,
            "rotation_quality": 0.5,
            "inflow_sectors": set(),
            "outflow_sectors": set(),
        }

    inflow_sectors = set(item["sector"] for item in inflow if item.get("sector"))
    outflow_sectors = set(item["sector"] for item in outflow if item.get("sector"))

    # Sector alignment: overlap vs union (lower = more divergent)
    total_sectors = inflow_sectors | outflow_sectors
    overlap = inflow_sectors & outflow_sectors
    sector_alignment = 1.0 - _clip(len(overlap) / max(len(total_sectors), 1))

    # Rotation breadth: how many sectors have significant flows
    total_flowing = len(inflow) + len(outflow)
    rotation_breadth = _clip(total_flowing / 10)  # Normalize to max 10 sectors

    # Rotation quality: consistency of direction
    inflow_values = [abs(item.get("value_bil", 0)) for item in inflow]
    outflow_values = [abs(item.get("value_bil", 0)) for item in outflow]

    if inflow_values and outflow_values:
        avg_in = np.mean(inflow_values)
        avg_out = np.mean(outflow_values)
        # If both sides have similar magnitude, rotation is healthy
        ratio = min(avg_in, avg_out) / max(avg_in, avg_out, 1)
        rotation_quality = _clip(ratio)
    elif inflow_values:
        rotation_quality = 0.7
    elif outflow_values:
        rotation_quality = 0.3
    else:
        rotation_quality = 0.5

    return {
        "sector_alignment": round(sector_alignment, 3),
        "rotation_breadth": round(rotation_breadth, 3),
        "rotation_quality": round(rotation_quality, 3),
        "inflow_sectors": inflow_sectors,
        "outflow_sectors": outflow_sectors,
        "rotation_count": len(inflow) + len(outflow),
    }


def analyze_ticker_flow_quality(ticker_flow: Dict[str, Any]) -> float:
    """
    Analyze ticker flow quality - look for institutional signatures.
    """
    inflow = ticker_flow.get("inflow", [])
    outflow = ticker_flow.get("outflow", [])

    if not inflow and not outflow:
        return 0.5

    # Check for concentration vs distribution
    inflow_values = [abs(t.get("value_bil", 0)) for t in inflow]
    outflow_values = [abs(t.get("value_bil", 0)) for t in outflow]

    if inflow_values:
        # If top 1 stock gets >50% of inflow, might be concentrated
        concentration = (
            max(inflow_values) / sum(inflow_values) if sum(inflow_values) > 0 else 0
        )
        inflow_quality = 1.0 - _clip(concentration - 0.5) * 0.5
    else:
        inflow_quality = 0.5

    if outflow_values:
        concentration = (
            max(outflow_values) / sum(outflow_values) if sum(outflow_values) > 0 else 0
        )
        outflow_quality = 1.0 - _clip(concentration - 0.5) * 0.5
    else:
        outflow_quality = 0.5

    return round((inflow_quality + outflow_quality) / 2, 3)


# ═════════════════════════════════════════════
# FEATURE ENGINEERING (Optimized)
# ═════════════════════════════════════════════


def compute_regime_features(symbol: str = "VNINDEX", target_date: str = None) -> dict:
    """
    Fetch VNINDEX và tính toàn bộ features cho regime detection.
    """
    if target_date:
        from datetime import date as date_type

        if isinstance(target_date, (datetime, date_type)):
            target_date = target_date.strftime("%Y-%m-%d")
        end = target_date
        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            start = (target_dt - timedelta(days=700)).strftime("%Y-%m-%d")
        except:
            start = (datetime.utcnow() - timedelta(days=700)).strftime("%Y-%m-%d")
    else:
        end = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() - timedelta(days=700)).strftime("%Y-%m-%d")

    df, src = _fetch_history_any_source(symbol, start, end)
    if df.empty or len(df) < 210:
        print(f"⚠️  Regime: không đủ dữ liệu cho {symbol} (got {len(df)} rows)")
        return {}

    close = df["close"]
    high = df["high"]
    low = df["low"]

    # ── Trend Indicators ─────────────────────────────────────
    df["ema9"] = close.ewm(span=9, adjust=False).mean()
    df["ema26"] = close.ewm(span=26, adjust=False).mean()
    df["ema200"] = close.ewm(span=200, adjust=False).mean()

    df["ema9_vs_ema26_pct"] = (df["ema9"] - df["ema26"]) / df["ema26"] * 100
    df["price_vs_ema200"] = (close - df["ema200"]) / df["ema200"] * 100
    df["price_vs_ema50"] = (
        (close - close.rolling(50).mean()) / close.rolling(50).mean() * 100
    )

    # MACD histogram
    macd_line = df["ema9"] - df["ema26"]
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    df["macd_hist"] = macd_line - signal_line
    df["macd_hist_prev"] = df["macd_hist"].shift(1)

    df["adx14"] = ta.trend.adx(high, low, close, window=14)
    df["return_5d"] = close.pct_change(5) * 100
    df["return_20d"] = close.pct_change(20) * 100

    # EMA Cross signal
    df["ema_cross_signal"] = np.where(df["ema9"] > df["ema26"], 1, -1)
    df["ema_cross_prev"] = df["ema_cross_signal"].shift(1)
    df["ema_cross_flipped"] = (df["ema_cross_signal"] != df["ema_cross_prev"]) & (
        df["ema_cross_signal"] == 1
    )

    # ── Volatility ──────────────────────────────────────────
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    df["bb_width"] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()
    df["bb_width_pct"] = df["bb_width"].rolling(252).rank(pct=True)

    atr10 = ta.volatility.average_true_range(high, low, close, window=10)
    df["atr10"] = atr10
    df["atr10_median"] = atr10.rolling(60).median()

    # ── Breadth proxy ───────────────────────────────────────
    df["rsi14_idx"] = ta.momentum.rsi(close, window=14)

    avg_close = close.rolling(14).mean()
    avg_rsi = df["rsi14_idx"].rolling(14).mean()
    df["rsi_bear_div"] = (close >= avg_close) & (df["rsi14_idx"] < avg_rsi)
    df["rsi_superoverbought"] = df["rsi14_idx"].rolling(18).max() >= 85
    df["rsi_overbought"] = df["rsi14_idx"] >= 70
    df["rsi_oversold"] = df["rsi14_idx"] <= 30

    # Trend fatigue detection
    df["ema9_pct_change"] = df["ema9"].pct_change(20) * 100
    df["is_fatigue"] = df["ema9_pct_change"].abs() < 0.3

    # ── Distribution Days (Last 15 bars) ───────────────────
    df["dist_day"] = (df["close"] < df["close"].shift(1)).astype(int)
    df["dist_days_15"] = df["dist_day"].rolling(15).sum()

    # ── Slice to target_date to ensure correct anchor row ───
    if target_date:
        try:
            td = pd.Timestamp(target_date)
            df_slice = df[df["time"] <= td]
            if not df_slice.empty:
                df = df_slice
        except Exception:
            pass

    # ── Extract latest row ───────────────────────────────────
    L = df.iloc[-1]

    macd_flipped = (
        float(L["macd_hist"]) < 0
        and pd.notna(L["macd_hist_prev"])
        and float(L["macd_hist_prev"]) >= 0
    )

    atr_spike = (
        pd.notna(L["atr10"])
        and pd.notna(L["atr10_median"])
        and float(L["atr10"]) > 1.5 * float(L["atr10_median"])
    )

    return {
        "date": str(df["time"].iloc[-1])[:10],
        "source": src or "unknown",
        "close": round(float(L["close"]), 1),
        # Trend
        "ema9": round(float(L["ema9"]), 1),
        "ema26": round(float(L["ema26"]), 1),
        "ema200": round(float(L["ema200"]), 1),
        "ema9_vs_ema26_pct": round(float(L["ema9_vs_ema26_pct"]), 3),
        "price_vs_ema200": round(float(L["price_vs_ema200"]), 3),
        "price_vs_ema50": round(float(L["price_vs_ema50"]), 3),
        "macd_hist": round(float(L["macd_hist"]), 3),
        "macd_hist_flipped": macd_flipped,
        "adx14": round(float(L["adx14"]), 1),
        "return_5d": round(float(L["return_5d"]), 2),
        "return_20d": round(float(L["return_20d"]), 2),
        "ema_cross_up": bool(L["ema_cross_signal"]) == 1,
        # Volatility
        "bb_width_pct": round(float(L["bb_width_pct"]), 3),
        "atr_spike": atr_spike,
        # Breadth
        "is_fatigue": bool(L["is_fatigue"]),
        "rsi14_idx": round(float(L["rsi14_idx"]), 1),
        "rsi_bear_div": bool(L["rsi_bear_div"]),
        "rsi_superoverbought": bool(L["rsi_superoverbought"]),
        "rsi_overbought": bool(L["rsi_overbought"]),
        "rsi_oversold": bool(L["rsi_oversold"]),
        # Distribution Days
        "dist_days": int(L["dist_days_15"]) if pd.notna(L["dist_days_15"]) else 0,
    }


def fetch_breadth_signals() -> dict:
    """
    Fetch gainer/loser count từ Insights.ranking().
    """
    try:
        from vnstock_data import Insights

        gainers = Insights().ranking().gainer()
        losers = Insights().ranking().loser()
        g = len(gainers) if gainers is not None and not gainers.empty else 0
        l = len(losers) if losers is not None and not losers.empty else 0
        total = g + l
        ratio = round(g / total, 3) if total > 0 else 0.5
        return {"gainer_loser_ratio": ratio, "gainer_count": g, "loser_count": l}
    except Exception as e:
        print(f"⚠️  fetch_breadth_signals failed: {e}")
        return {}


def fetch_foreign_flow(
    top_symbols: list | None = None, lookback_days: int = 20, target_date: str = None
) -> dict:
    """
    Tính foreign flow aggregated từ Trading.foreign_trade() (vnstock_data 3.0.0+).
    """
    DEFAULT_SYMBOLS = [
        "VCB",
        "BID",
        "CTG",
        "TCB",
        "MBB",
        "VPB",
        "ACB",
        "STB",
        "VIC",
        "VHM",
        "VRE",
        "MSN",
        "MWG",
        "FPT",
        "GAS",
        "SAB",
        "HPG",
        "VNM",
        "PLX",
        "POW",
        "GVR",
        "BVH",
        "SSI",
        "HDB",
        "VIX",
        "BCM",
        "VGC",
        "REE",
        "PNJ",
        "GMD",
    ]
    symbols = top_symbols or DEFAULT_SYMBOLS

    if target_date:
        end = target_date
        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            start = (target_dt - timedelta(days=lookback_days + 15)).strftime(
                "%Y-%m-%d"
            )
        except:
            end = datetime.utcnow().strftime("%Y-%m-%d")
            start = (datetime.utcnow() - timedelta(days=lookback_days + 15)).strftime(
                "%Y-%m-%d"
            )
    else:
        end = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() - timedelta(days=lookback_days + 15)).strftime(
            "%Y-%m-%d"
        )

    all_series = []

    try:
        from vnstock_data import Trading

        for sym in symbols:
            try:
                trd = Trading(source="vci", symbol=sym)
                raw = trd.foreign_trade(start=start, end=end)
                if raw is None or (hasattr(raw, "empty") and raw.empty):
                    continue
                df = raw.copy()
                df.columns = [str(c).lower().strip() for c in df.columns]

                # Find time column
                for tcol in ["time", "date", "trading_date", "tradingdate"]:
                    if tcol in df.columns:
                        df["time"] = pd.to_datetime(df[tcol], errors="coerce")
                        break
                else:
                    continue

                # Calculate net value: fr_buy_value_matched - fr_sell_value_matched
                buy_col = next(
                    (c for c in df.columns if "buy" in c and "matched" in c), None
                )
                sell_col = next(
                    (c for c in df.columns if "sell" in c and "matched" in c), None
                )

                if buy_col and sell_col:
                    df["net_value"] = pd.to_numeric(
                        df[buy_col], errors="coerce"
                    ) - pd.to_numeric(df[sell_col], errors="coerce")
                else:
                    continue

                if "time" not in df.columns or "net_value" not in df.columns:
                    continue

                s = (
                    df[["time", "net_value"]]
                    .dropna()
                    .sort_values("time")
                    .set_index("time")["net_value"]
                )
                if s.abs().median() > 1e9:
                    s = s / 1e9
                all_series.append(s)
            except Exception:
                continue

        if not all_series:
            print("⚠️  fetch_foreign_flow: không lấy được dữ liệu")
            return {}

        combined = (
            pd.concat(all_series, axis=1).sum(axis=1, min_count=1).sort_index().dropna()
        )
        if len(combined) < 5:
            return {}

        net_1d = float(combined.iloc[-1])
        net_10d = (
            float(combined.iloc[-10:].sum())
            if len(combined) >= 10
            else float(combined.sum())
        )
        avg_5d_prev = float(combined.iloc[-6:-1].mean()) if len(combined) >= 6 else 0.0
        acceleration = net_1d - avg_5d_prev
        pct_rank = float((combined <= net_1d).mean())

        direction = 1 if net_1d >= 0 else -1
        streak = 0
        for v in reversed(combined.values):
            if (v >= 0) == (direction > 0):
                streak += 1
            else:
                break
        streak *= direction

        return {
            "foreign_net_1d": round(net_1d, 1),
            "foreign_net_10d": round(net_10d, 1),
            "flow_streak": int(streak),
            "flow_acceleration": round(acceleration, 1),
            "foreign_net_pct_rank": round(pct_rank, 3),
        }
    except Exception as e:
        print(f"⚠️  fetch_foreign_flow error: {e}")
        return {}


def fetch_valuation(target_date: str = None) -> dict:
    """
    Lấy P/E và P/B thị trường từ Analytics.valuation().
    """
    try:
        from vnstock_data import Analytics

        val = Analytics().valuation()
        pe_df = None
        pb_df = None

        try:
            pe_df = val.pe()
        except Exception:
            pass
        try:
            pb_df = val.pb()
        except Exception:
            pass

        if pe_df is None or pb_df is None:
            try:
                ev = val.evaluation()
                if ev is not None and not (hasattr(ev, "empty") and ev.empty):
                    ev.columns = [str(c).lower().strip() for c in ev.columns]
                    pe_col = next((c for c in ev.columns if "pe" in c), None)
                    pb_col = next((c for c in ev.columns if "pb" in c), None)
                    time_col = next(
                        (c for c in ["time", "date", "tradingdate"] if c in ev.columns),
                        None,
                    )
                    base_cols = [time_col] if time_col else []
                    if pe_df is None and pe_col:
                        pe_df = ev[base_cols + [pe_col]].rename(columns={pe_col: "pe"})
                    if pb_df is None and pb_col:
                        pb_df = ev[base_cols + [pb_col]].rename(columns={pb_col: "pb"})
            except Exception:
                pass

        def _to_series(df, hints):
            if df is None or (hasattr(df, "empty") and df.empty):
                return pd.Series(dtype=float)
            d = df.copy()
            d.columns = [str(c).lower().strip() for c in d.columns]
            for tcol in ["time", "date", "tradingdate"]:
                if tcol in d.columns:
                    d["time"] = pd.to_datetime(d[tcol], errors="coerce")
                    break
            val_col = next((c for c in hints if c in d.columns), None)
            if val_col is None:
                num_cols = [
                    c
                    for c in d.columns
                    if c not in ("time", "date", "tradingdate")
                    and pd.api.types.is_numeric_dtype(d[c])
                ]
                val_col = num_cols[0] if num_cols else None
            if val_col is None or "time" not in d.columns:
                return pd.Series(dtype=float)
            return (
                d[["time", val_col]]
                .dropna()
                .sort_values("time")
                .set_index("time")[val_col]
            )

        pe_s = _to_series(pe_df, ["pe", "p/e", "pe_ratio"])
        pb_s = _to_series(pb_df, ["pb", "p/b", "pb_ratio"])

        # Slice to target_date
        if target_date:
            try:
                td = pd.Timestamp(target_date)
                pe_s = pe_s[pe_s.index <= td]
                pb_s = pb_s[pb_s.index <= td]
            except Exception:
                pass

        if pe_s.empty and pb_s.empty:
            print("⚠️  fetch_valuation: không lấy được PE/PB")
            return {}

        def _zscore_latest(series, window=756):
            if len(series) < 60:
                return None, None
            hist = series.iloc[-window:]
            curr = float(series.iloc[-1])
            z = (
                (curr - float(hist.mean())) / float(hist.std())
                if hist.std() > 0
                else 0.0
            )
            return round(curr, 2), round(z, 3)

        pe_curr, pe_z = _zscore_latest(pe_s) if not pe_s.empty else (None, None)
        pb_curr, pb_z = _zscore_latest(pb_s) if not pb_s.empty else (None, None)

        scores = []
        if pe_z is not None:
            scores.append(1.0 / (1.0 + np.exp(float(pe_z))))
        if pb_z is not None:
            scores.append(1.0 / (1.0 + np.exp(float(pb_z))))
        valuation_score = round(float(np.mean(scores)), 3) if scores else 0.5

        result = {"valuation_score": valuation_score}
        if pe_curr is not None:
            result.update({"pe_current": pe_curr, "pe_zscore": pe_z})
        if pb_curr is not None:
            result.update({"pb_current": pb_curr, "pb_zscore": pb_z})
        return result

    except Exception as e:
        print(f"⚠️  fetch_valuation error: {e}")
        return {}


# ═════════════════════════════════════════════
# SCORING ENGINE (Optimized v2)
# ═════════════════════════════════════════════


def score_regime(feat: dict, recap_data: dict = None) -> Tuple[str, float, dict]:
    """
    Map feature dict → (regime_label, composite_score, breakdown).

    OPTIMIZED: Accepts optional recap_data for richer breadth/flow signals.
    """
    if not feat:
        return "unknown", 0.5, {}

    # ── Layer 1: Trend Score (35%) ───────────────────────────
    t_vs_ema200 = _linear(feat["price_vs_ema200"], -10, 10)
    t_vs_ema50 = _linear(feat["price_vs_ema50"], -5, 5)
    t_ema_cross = 1.0 if feat["ema_cross_up"] else 0.0
    t_macd = 1.0 if feat["macd_hist"] > 0 else 0.0
    t_mom_5d = _linear(feat["return_5d"], -3, 3)
    t_mom_20d = _linear(feat["return_20d"], -8, 8)

    trend_score = (
        t_vs_ema200 * 0.25
        + t_vs_ema50 * 0.20
        + t_ema_cross * 0.20
        + t_macd * 0.15
        + t_mom_5d * 0.12
        + t_mom_20d * 0.08
    )

    # ── Layer 2: Breadth Score (30%) — ENHANCED ─────────────
    breadth_score = 0.5

    # Use real data from Daily Recap if available
    if recap_data:
        snap = recap_data.get("snapshot", {})
        market_breadth = recap_data.get("market_breadth", {})

        ad_ratio = snap.get("ad_de_ratio")
        if ad_ratio:
            ad_ratio_score = _linear(ad_ratio, 0.5, 1.5)
            breadth_score = ad_ratio_score * 0.5

            # A/D strength
            advances = market_breadth.get("advances", 0)
            declines = market_breadth.get("declines", 0)
            if advances and declines:
                ad_strength = _linear(advances / (advances + declines), 0.3, 0.7)
                breadth_score = breadth_score * 0.6 + ad_strength * 0.4
    else:
        # Fallback to RSI-based proxy
        rsi_neutral = _tri_ideal(feat["rsi14_idx"], 50, 25)
        breadth_score = rsi_neutral

        glr = feat.get("gainer_loser_ratio")
        if glr is not None:
            glr_score = _linear(glr, 0.5, 1.5)
            breadth_score = 0.6 * breadth_score + 0.4 * glr_score

    # Adjust for divergences and overbought
    if feat.get("rsi_bear_div"):
        breadth_score *= 0.7
    if feat.get("rsi_overbought") and trend_score > 0.6:
        breadth_score *= 0.85  # Slight caution on overbought in bull trend

    # ── Layer 3: Money Flow Score (25%) — ENHANCED ─────────
    flow_score = 0.5

    if recap_data:
        snap = recap_data.get("snapshot", {})
        flow_data = recap_data.get("flow", {})
        ticker_flow = recap_data.get("ticker_flow", {})

        # Foreign flow from snapshot
        foreign_bil = snap.get("foreign_flow_bil", 0)
        foreign_score = _linear(foreign_bil, -500, 500)  # -500B sell to +500B buy
        flow_score = foreign_score * 0.4

        # Sector rotation analysis
        sector_rot = analyze_sector_rotation(flow_data)
        sector_score = (
            sector_rot["sector_alignment"] * 0.3
            + sector_rot["rotation_breadth"] * 0.3
            + sector_rot["rotation_quality"] * 0.4
        )
        flow_score = flow_score * 0.5 + sector_score * 0.3

        # Ticker flow quality
        ticker_quality = analyze_ticker_flow_quality(ticker_flow)
        flow_score = flow_score * 0.7 + ticker_quality * 0.2

        # Add streak bonus/penalty
        streak = feat.get("flow_streak", 0)
        streak_bonus = _linear(abs(streak), 0, 10) * 0.1 * (1 if streak > 0 else -1)
        flow_score = _clip(flow_score + streak_bonus)
    else:
        # Fallback to foreign flow from API
        if "foreign_net_pct_rank" in feat:
            base = float(feat["foreign_net_pct_rank"])
            streak = feat.get("flow_streak", 0)
            streak_bonus = (
                _linear(abs(streak), 0, 10) * 0.15 * (1 if streak > 0 else -1)
            )
            acc = feat.get("flow_acceleration", 0.0)
            acc_bonus = _linear(acc, -500, 500) * 0.10 - 0.05
            flow_score = float(_clip(base + streak_bonus + acc_bonus))

    # ── Layer 4: Volatility Score (10%) ──────────────────────
    vol_score = 1.0 - feat["bb_width_pct"]
    if feat.get("atr_spike"):
        vol_score *= 0.6  # Risk signal: high volatility reduces score
    if feat["rsi_oversold"]:
        vol_score *= 1.1  # Slight boost for oversold (potential reversal)

    # ── Composite ───────────────────────────────────────────
    composite = float(
        _clip(
            trend_score * WEIGHTS["trend"]
            + breadth_score * WEIGHTS["breadth"]
            + flow_score * WEIGHTS["flow"]
            + vol_score * WEIGHTS["volatility"],
            0.0,
            1.0,
        )
    )

    # ── Apply Recap-based Overrides ───────────────────────────
    overrides_applied = []

    if recap_data and composite > 0.5:
        snap = recap_data.get("snapshot", {})

        # Override 1: Distribution days warning
        # Scale: 0-2=Sạch, 3-4=Thận trọng, 5=Elevated, 6-7=High Risk, ≥8=Critical
        dist_days = snap.get("dist_days", 0)
        if dist_days >= 8:
            composite *= 0.70
            overrides_applied.append(f"dist_days={dist_days} (Critical) → score*0.70")
        elif dist_days >= 6:
            composite *= 0.80
            overrides_applied.append(f"dist_days={dist_days} (High Risk) → score*0.80")
        elif dist_days >= 5:
            composite *= 0.88
            overrides_applied.append(f"dist_days={dist_days} (Elevated) → score*0.88")
        elif dist_days >= 3 and composite > 0.65:
            composite *= 0.95
            overrides_applied.append(f"dist_days={dist_days} (Caution) → score*0.95")
        # 0-2: Thị trường sạch - no penalty

        # Override 2: Foreign selling + breadth deterioration
        foreign_bil = snap.get("foreign_flow_bil", 0)
        ad_ratio = snap.get("ad_de_ratio", 1.0)
        if foreign_bil < -300 and ad_ratio < 0.7:
            composite = min(composite, 0.35)
            overrides_applied.append("foreign_sell+bad_breadth → capped@0.35")
        elif foreign_bil < -200 and ad_ratio < 0.8:
            composite *= 0.85
            overrides_applied.append("foreign_sell+weak_breadth → score*0.85")

    # ── Hard Technical Overrides ─────────────────────────────
    if feat.get("macd_hist_flipped") and composite > 0.55:
        composite *= 0.88
        overrides_applied.append("MACD_flip → score*0.88")
    if feat.get("adx14", 99) < 15 and feat.get("is_fatigue"):
        composite = min(composite, 0.40)
        overrides_applied.append("ADX<15+fatigue → capped@0.40")

    # ── Classify ─────────────────────────────────────────────
    if composite > REGIME_THRESHOLDS["strong_bull"]:
        label = "strong_bull"
    elif composite > REGIME_THRESHOLDS["bull"]:
        label = "bull"
    elif composite > REGIME_THRESHOLDS["recovery"]:
        label = "recovery"
    elif composite > REGIME_THRESHOLDS["ranging"]:
        label = "ranging"
    else:
        label = "bear_risk"

    breakdown = {
        "trend": round(trend_score, 3),
        "breadth": round(breadth_score, 3),
        "flow": round(flow_score, 3),
        "vol": round(vol_score, 3),
        "composite": round(composite, 3),
        "overrides": overrides_applied,
    }
    return label, round(composite, 3), breakdown


# ═════════════════════════════════════════════
# OUTPUT FORMATTER
# ═════════════════════════════════════════════

_REGIME_EMOJI = {
    "strong_bull": "🟢💪",
    "bull": "🟢",
    "recovery": "🔵",
    "ranging": "🟡",
    "bear_risk": "🔴",
    "unknown": "⚪",
}

_REGIME_BIAS = {
    "strong_bull": "Bias mua mạnh · Full size · Momentum stocks",
    "bull": "Bias mua · Normal size · Accumulate dips",
    "recovery": "Bias tích lũy · Giảm size nhẹ · Selective buys",
    "ranging": "Bias trung tính · Min size · Mean-reversion",
    "bear_risk": "Bias phòng thủ · Cash/short · Defensive",
    "unknown": "Không xác định · Không hành động",
}

_REGIME_VN = {
    "strong_bull": "TĂNG MẠNH",
    "bull": "TĂNG",
    "recovery": "HỒI PHỤC",
    "ranging": "ĐI NGANG",
    "bear_risk": "GIẢM",
    "unknown": "KHÔNG XÁC ĐỊNH",
}


def format_regime_message(
    feat: dict, label: str, score: float, bd: dict, recap_data: dict = None
) -> str:
    """Tạo Discord message block cho regime."""
    emoji = _REGIME_EMOJI.get(label, "⚪")
    bias = _REGIME_BIAS.get(label, "")
    vn_label = _REGIME_VN.get(label, label.upper())
    date = feat.get("date", "N/A")

    warnings = []

    # Standard warnings
    if feat.get("rsi_superoverbought"):
        warnings.append("⚠️  RSI overbought — Bull có thể sắp đảo chiều")
    if feat.get("atr_spike"):
        warnings.append("⚠️  ATR spike — Regime đang chuyển trạng thái")
    if feat.get("macd_hist_flipped"):
        warnings.append("⚠️  MACD flip — Momentum đổi chiều hôm nay")
    if feat.get("rsi_overbought"):
        warnings.append("⚠️  RSI overbought — Cẩn trọng với pullback")

    # Enhanced warnings from Recap data
    if recap_data:
        snap = recap_data.get("snapshot", {})
        dist_days = snap.get("dist_days", 0)
        # Distribution days scale: 0-2=Sạch, 3-4=Thận trọng, 5=Elevated, 6-7=High Risk, ≥8=Critical
        if dist_days >= 8:
            warnings.append(f"🚨 {dist_days} distribution days — NGUY HIỂM!")
        elif dist_days >= 6:
            warnings.append(f"🔴 {dist_days} distribution days — Rủi ro cao!")
        elif dist_days >= 5:
            warnings.append(f"🟠 {dist_days} distribution days — Nâng cao!")
        elif dist_days >= 3:
            warnings.append(f"🟡 {dist_days} distribution days — Thận trọng")
        # 0-2: Thị trường sạch - no warning

        flow_data = recap_data.get("flow", {})
        sector_rot = analyze_sector_rotation(flow_data)
        if sector_rot["rotation_count"] > 8:
            warnings.append(
                f"✅  Rotation healthy — {sector_rot['rotation_count']} sectors flowing"
            )

        foreign_bil = snap.get("foreign_flow_bil", 0)
        if foreign_bil > 300:
            warnings.append(f"✅  Foreign mua ròng {foreign_bil:.0f}B")
        elif foreign_bil < -300:
            warnings.append(f"🔴  Foreign bán ròng {abs(foreign_bil):.0f}B")

    streak = feat.get("flow_streak", 0)
    if streak <= -5:
        warnings.append(f"⚠️  Ngoại tệ bán ròng {abs(streak)} phiên liên tiếp")
    elif streak >= 5:
        warnings.append(f"✅  Ngoại tệ mua ròng {streak} phiên liên tiếp")

    # Breadth line from Recap
    breadth_line = ""
    if recap_data:
        snap = recap_data.get("snapshot", {})
        market_breadth = recap_data.get("market_breadth", {})
        ad_adv = market_breadth.get("advances", 0)
        ad_dec = market_breadth.get("declines", 0)
        ad_ratio = snap.get("ad_de_ratio", 0)
        breadth_line = f"\nBreadth   {ad_adv}↑ / {ad_dec}↓   A/D {ad_ratio:.2f}"
        foreign_bil = snap.get("foreign_flow_bil", 0)
        sign = "+" if foreign_bil >= 0 else ""
        breadth_line += f"   Foreign {sign}{foreign_bil:.0f}B"
    else:
        if "gainer_loser_ratio" in feat:
            breadth_line = f"\nG/L ratio  {feat['gainer_loser_ratio']:.2f}   ({feat.get('gainer_count', '?')}↑ / {feat.get('loser_count', '?')}↓)"

    ff_lines = ""
    if "foreign_net_1d" in feat:
        sign_1d = "+" if feat["foreign_net_1d"] >= 0 else ""
        sign_10d = "+" if feat["foreign_net_10d"] >= 0 else ""
        ff_lines = (
            f"\nForeign 1d  {sign_1d}{feat['foreign_net_1d']:>7.0f}B   "
            f"10d {sign_10d}{feat['foreign_net_10d']:>7.0f}B"
            f"\nStreak     {feat.get('flow_streak', 0):>+8}   "
            f"Accel {feat.get('flow_acceleration', 0.0):>+7.0f}B"
        )

    val_lines = ""
    if "pe_current" in feat or "pb_current" in feat:
        pe_str = (
            f"PE {feat['pe_current']:.1f} (z={feat.get('pe_zscore', 0):+.2f})"
            if "pe_current" in feat
            else ""
        )
        pb_str = (
            f"PB {feat['pb_current']:.1f} (z={feat.get('pb_zscore', 0):+.2f})"
            if "pb_current" in feat
            else ""
        )
        val_lines = f"\n{pe_str}   {pb_str}"

    override_lines = ""
    if bd.get("overrides"):
        override_lines = f"\nOverrides: {' | '.join(bd['overrides'])}"

    lines = [
        f"📊 **Market Regime — {date}**",
        f"{emoji} **{vn_label}**  (score: {score:.2f})",
        f"```",
        f"VNINDEX    {feat['close']:>8.1f}",
        f"EMA9       {feat['ema9']:>8.1f}   EMA26   {feat['ema26']:>8.1f}",
        f"EMA200     {feat['ema200']:>8.1f}   vs200   {feat['price_vs_ema200']:>+7.1f}%",
        f"ADX14      {feat['adx14']:>8.1f}   BBpct   {feat['bb_width_pct']:>7.0%}",
        f"MACD hist  {feat['macd_hist']:>8.3f}   RSI14   {feat['rsi14_idx']:>7.1f}",
        f"5d return  {feat['return_5d']:>+7.1f}%   DistD  {feat.get('dist_days', 0):>4}",
        breadth_line,
        ff_lines,
        val_lines,
        f"",
        f"Trend {bd['trend']:.2f} · Breadth {bd['breadth']:.2f} · Flow {bd['flow']:.2f}",
        f"Vol {bd['vol']:.2f} · Composite {bd['composite']:.2f}",
        override_lines,
        f"```",
        f"_{bias}_",
    ]
    if warnings:
        lines += [""] + warnings

    return "\n".join(l for l in lines if l is not None)


# ═════════════════════════════════════════════
# MAIN ENTRY POINTS
# ═════════════════════════════════════════════


def run_regime_detection(
    symbol: str = "VNINDEX", recap_data: dict = None, target_date: str = None
) -> Tuple[dict, str, float, dict]:
    """
    Entry point chính. Trả về (feat, label, score, bd).
    """
    print(
        f"📡 Fetching regime features for {symbol} (Target: {target_date or 'Today'})..."
    )

    feat = compute_regime_features(symbol, target_date=target_date)
    if not feat:
        return {}, "unknown", 0.5, {}

    # Only fetch additional data if no recap_data provided
    if recap_data is None:
        print("📡 Fetching gainer/loser ratio (breadth fallback)...")
        # Breadth signals from API don't support history well, fallback to trend

        print("📡 Fetching foreign flow...")
        feat.update(fetch_foreign_flow(target_date=target_date))

        print("📡 Fetching market valuation (PE/PB)...")
        feat.update(fetch_valuation(target_date=target_date))

    label, score, bd = score_regime(feat, recap_data)
    return feat, label, score, bd


def run_regime_from_recap(
    recap_data: dict, target_date: str = None
) -> Tuple[dict, str, float, dict]:
    """
    NEW: Compute regime directly from pre-fetched Daily Recap data.
    """
    print(
        f"📡 Computing regime from Daily Recap data (Target: {target_date or 'Latest'})..."
    )

    # Compute trend indicators
    feat = compute_regime_features("VNINDEX", target_date=target_date)
    if not feat:
        return {}, "unknown", 0.5, {}

    # Add foreign flow data (proxy)
    feat.update(fetch_foreign_flow(target_date=target_date))

    # Score with full recap data
    label, score, bd = score_regime(feat, recap_data)
    return feat, label, score, bd


# ─────────────────────────────────────────────
# Standalone run
# ─────────────────────────────────────────────
if __name__ == "__main__":
    feat, label, score, bd = run_regime_detection("VNINDEX")
    msg = format_regime_message(feat, label, score, bd)
    print(msg)
    send_discord(msg)
