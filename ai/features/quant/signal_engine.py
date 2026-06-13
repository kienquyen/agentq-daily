# features/quant/signal_engine.py
"""
Signal Engine — Phân tích tín hiệu ngắn hạn và dynamic stop.

Functions:
  classify_signals(ticker, hist_df, metrics_dict) -> dict
    Phân loại tín hiệu tích cực/tiêu cực từ momentum và quality.
    hist_df: OHLCV DataFrame >= 60 rows (columns: time, open, high, low, close, volume)
    metrics_dict: dict chứa các chỉ số đã tính (sharpe_12m, bench_sharpe_12m,
                  excess_ret_3m, beta_up_12m, beta_dn_12m)
    Returns: { positive: [...], negative: [...], agreement: "N/M",
               rsi: float|None, macd_slope: float|None,
               mfi: float|None, vol_ratio: float|None, momentum_ok: bool }

  calc_dynamic_stop(close, hist_df) -> dict
    Tính trailing stop động theo ATR hoặc swing low.
    Returns: { stop_price, stop_pct, method, atr14 }

Edge cases:
  - Thiếu data → signal bỏ qua (không dùng giá trị mặc định giả)
  - Tất cả None → trả về empty lists
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def _sf(x: Any) -> Optional[float]:
    """Safe cast to float; returns None if not finite."""
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def _has_col(df: pd.DataFrame, *cols: str) -> bool:
    return all(c in df.columns for c in cols)


# ─────────────────────────────────────────────────────────────────────────────
# TECHNICAL INDICATOR HELPERS (no external lib dependency)
# ─────────────────────────────────────────────────────────────────────────────


def _rsi(close: pd.Series, period: int = 14) -> Optional[float]:
    """RSI using Wilder smoothing. Returns None if insufficient data."""
    if close is None or len(close) < period + 5:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    return _sf(rsi_series.iloc[-1])


def _macd_hist_series(close: pd.Series) -> Optional[pd.Series]:
    """MACD histogram (12/26/9). Returns None if < 35 bars."""
    if close is None or len(close) < 35:
        return None
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd - signal


def _macd_slope(close: pd.Series) -> Optional[float]:
    """Slope of MACD histogram: hist[-1] - hist[-3]. Positive = rising."""
    hist = _macd_hist_series(close)
    if hist is None or len(hist) < 3:
        return None
    slope = float(hist.iloc[-1]) - float(hist.iloc[-3])
    return slope if math.isfinite(slope) else None


def _macd_consecutive_rising(close: pd.Series) -> Optional[bool]:
    """True nếu MACD histogram tăng 3 phiên liên tiếp (last3[2] > last3[1] > last3[0])."""
    hist = _macd_hist_series(close)
    if hist is None or len(hist) < 3:
        return None
    v = hist.iloc[-3:].values
    return bool(v[-1] > v[-2] > v[-3])


def _mfi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    period: int = 14,
) -> Optional[float]:
    """Money Flow Index. Returns None if insufficient data or zero volume."""
    if any(x is None for x in [high, low, close, volume]):
        return None
    if len(close) < period + 2:
        return None
    typical = (high + low + close) / 3
    money_flow = typical * volume
    prev_typical = typical.shift(1)
    pos_flow = money_flow.where(typical > prev_typical, 0.0)
    neg_flow = money_flow.where(typical < prev_typical, 0.0)
    pos_sum = pos_flow.rolling(period).sum()
    neg_sum = neg_flow.rolling(period).sum()
    mfr = pos_sum / neg_sum.replace(0, np.nan)
    mfi_s = 100 - (100 / (1 + mfr))
    return _sf(mfi_s.iloc[-1])


def _volume_ratio(volume: pd.Series) -> Optional[float]:
    """volume[-1] / mean(volume[-21:-1]). None if < 21 bars or zero avg."""
    if volume is None or len(volume) < 22:
        return None
    avg20 = float(volume.iloc[-21:-1].mean())
    if avg20 == 0:
        return None
    ratio = float(volume.iloc[-1]) / avg20
    return ratio if math.isfinite(ratio) else None


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Optional[float]:
    """Average True Range. Returns None if insufficient data."""
    if any(x is None for x in [high, low, close]):
        return None
    if len(close) < period + 2:
        return None
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_val = _sf(tr.rolling(period).mean().iloc[-1])
    return atr_val


# ─────────────────────────────────────────────────────────────────────────────
# CANDLESTICK PATTERNS
# ─────────────────────────────────────────────────────────────────────────────


def detect_candle_patterns(hist_df: pd.DataFrame) -> Dict[str, bool]:
    """
    Phát hiện các mẫu nến đảo chiều giảm.

    Tự tính above_ma50 từ hist_df (MA50 của close[-50:]).

    Returns:
        {
            "evening_star":           bool,  # 3-nến đảo chiều tại đỉnh
            "bearish_engulfing_top":  bool,  # nến gấu nuốt nến tăng tại đỉnh
            "shooting_star_ma50plus": bool,  # đuôi trên dài, trên MA50
            "doji_resistance":        bool,  # doji tại vùng kháng cự
        }
    """
    flags: Dict[str, bool] = {
        "evening_star": False,
        "bearish_engulfing_top": False,
        "shooting_star_ma50plus": False,
        "doji_resistance": False,
    }

    if hist_df is None or len(hist_df) < 3:
        return flags
    if not _has_col(hist_df, "open", "high", "low", "close"):
        return flags

    o = hist_df["open"].values.astype(float)
    h = hist_df["high"].values.astype(float)
    l = hist_df["low"].values.astype(float)
    c = hist_df["close"].values.astype(float)

    price_ref = c[-1] if c[-1] > 0 else 1.0

    # above_ma50: tính từ hist_df
    above_ma50 = False
    if len(c) >= 50:
        above_ma50 = bool(c[-1] > float(np.mean(c[-50:])))

    # near_top: close trong 5% dưới đỉnh 20 phiên
    n_window = min(20, len(h))
    recent_high = float(h[-n_window:].max())
    near_top = (recent_high > 0) and ((recent_high - c[-1]) / recent_high <= 0.05)

    # ── Evening Star (3-nến) ──────────────────────────────────────────────────
    # Nến 1: tăng mạnh; Nến 2: thân nhỏ (star); Nến 3: giảm mạnh, đóng dưới midpoint nến 1
    try:
        large_body = price_ref * 0.01  # 1% giá
        body1 = c[-3] - o[-3]          # nến tăng
        body2 = abs(c[-2] - o[-2])     # thân nhỏ
        body3 = o[-1] - c[-1]          # nến giảm
        mid1 = (o[-3] + c[-3]) / 2
        if (
            body1 > large_body
            and body2 < large_body * 0.5
            and body3 > large_body
            and c[-1] < mid1
            and (above_ma50 or near_top)
        ):
            flags["evening_star"] = True
    except Exception:
        pass

    # ── Bearish Engulfing tại đỉnh ────────────────────────────────────────────
    # Nến [-2]: tăng; Nến [-1]: giảm, open >= close[-2], close <= open[-2]
    try:
        if (
            (above_ma50 or near_top)
            and c[-2] > o[-2]
            and c[-1] < o[-1]
            and o[-1] >= c[-2]
            and c[-1] <= o[-2]
        ):
            flags["bearish_engulfing_top"] = True
    except Exception:
        pass

    # ── Shooting Star trên MA50 ───────────────────────────────────────────────
    # Đuôi trên >= 2x thân, đuôi dưới <= thân, đuôi trên tối thiểu 0.5% giá
    try:
        if above_ma50:
            body_s = abs(c[-1] - o[-1])
            upper_shadow = h[-1] - max(c[-1], o[-1])
            lower_shadow = min(c[-1], o[-1]) - l[-1]
            if (
                body_s > 0
                and upper_shadow >= 2 * body_s
                and lower_shadow <= body_s
                and upper_shadow > price_ref * 0.005
            ):
                flags["shooting_star_ma50plus"] = True
    except Exception:
        pass

    # ── Doji tại kháng cự ─────────────────────────────────────────────────────
    # Thân cực nhỏ (< 0.3% giá) tại vùng near_top
    try:
        body_d = abs(c[-1] - o[-1])
        if near_top and body_d < price_ref * 0.003:
            flags["doji_resistance"] = True
    except Exception:
        pass

    return flags


# ─────────────────────────────────────────────────────────────────────────────
# CLASSIFY SIGNALS
# ─────────────────────────────────────────────────────────────────────────────


def classify_signals(
    ticker: str,
    hist_df: pd.DataFrame,
    metrics_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Phân loại tín hiệu tích cực/tiêu cực.

    Args:
        ticker: mã cổ phiếu (chỉ để log)
        hist_df: OHLCV DataFrame >= 35 rows (cần: close; tốt nhất: high, low, volume)
        metrics_dict: {
            sharpe_12m, bench_sharpe_12m, excess_ret_3m,
            beta_up_12m, beta_dn_12m
        }

    Returns:
        {
            "positive": [{"label": str, "value": str}, ...],  # max 3
            "negative": [{"label": str, "value": str}, ...],  # max 3
            "agreement": "N/M",           # momentum signals đồng thuận tích cực
            "rsi": float|None,
            "macd_slope": float|None,
            "mfi": float|None,
            "vol_ratio": float|None,
            "momentum_ok": bool,          # True nếu >= 2 momentum signals tích cực
        }
    """
    empty = {
        "positive": [],
        "negative": [],
        "agreement": "0/0",
        "rsi": None,
        "macd_slope": None,
        "mfi": None,
        "vol_ratio": None,
        "momentum_ok": False,
        "candle_flags": {},
    }

    if hist_df is None or hist_df.empty or not _has_col(hist_df, "close"):
        return empty

    candle_flags = detect_candle_patterns(hist_df)

    close = hist_df["close"]
    has_ohlcv = _has_col(hist_df, "open", "high", "low", "close", "volume")
    high = hist_df["high"] if has_ohlcv else None
    low = hist_df["low"] if has_ohlcv else None
    volume = hist_df["volume"] if has_ohlcv else None

    # (weight, label, value_str)
    pos_raw: List[Tuple[float, str, str]] = []
    neg_raw: List[Tuple[float, str, str]] = []

    # ── Momentum signals ──────────────────────────────────────────────────────
    momentum_total = 0
    momentum_positive = 0

    # 1. RSI 14
    rsi = _rsi(close)
    if rsi is not None:
        momentum_total += 1
        if 40 <= rsi <= 65:
            pos_raw.append((0.80, f"RSI {rsi:.0f} vùng lý tưởng (40–65)", f"{rsi:.0f}"))
            momentum_positive += 1
        elif rsi > 75:
            neg_raw.append((0.90, f"RSI quá mua: {rsi:.0f} > 75", "⚠"))
        elif rsi < 30:
            neg_raw.append((0.80, f"RSI quá bán: {rsi:.0f} < 30", "⚠"))
        else:
            # 65–75 hoặc 30–40: không thêm nhưng tính positive nếu 65-75 (momentum mạnh)
            if rsi > 65:
                momentum_positive += 1

    # 2. MACD slope (3 phiên)
    slope = _macd_slope(close)
    is_rising = _macd_consecutive_rising(close)
    if slope is not None:
        momentum_total += 1
        slope_str = f"{slope:+.3f}"
        if is_rising:
            pos_raw.append((0.90, "MACD tăng 3 phiên liên tiếp", slope_str))
            momentum_positive += 1
        elif slope > 0:
            pos_raw.append((0.65, "MACD histogram đang tăng", slope_str))
            momentum_positive += 1
        elif is_rising is False and slope < 0:
            hist_s = _macd_hist_series(close)
            if hist_s is not None and len(hist_s) >= 3:
                v = hist_s.iloc[-3:].values
                if v[-1] < v[-2] < v[-3]:
                    neg_raw.append((0.85, "MACD giảm 3 phiên liên tiếp", slope_str))
                else:
                    neg_raw.append((0.60, "MACD histogram đang giảm", slope_str))
            else:
                neg_raw.append((0.60, "MACD histogram đang giảm", slope_str))

    # 3. MFI 14
    mfi = _mfi(high, low, close, volume) if has_ohlcv else None
    if mfi is not None:
        momentum_total += 1
        if mfi > 50:
            pos_raw.append((0.70, f"MFI {mfi:.0f} — dòng tiền tích cực", f"{mfi:.0f}"))
            momentum_positive += 1
        elif mfi < 40:
            neg_raw.append((0.70, f"MFI {mfi:.0f} — dòng tiền yếu", "⚠"))

    # 4. Volume ratio
    vol_ratio = _volume_ratio(volume) if has_ohlcv else None
    if vol_ratio is not None:
        momentum_total += 1
        if vol_ratio > 1.2:
            pos_raw.append((0.75, f"Volume {vol_ratio:.1f}x TB20 — tích lũy mạnh", f"{vol_ratio:.1f}x"))
            momentum_positive += 1
        elif vol_ratio < 0.7:
            neg_raw.append((0.65, f"Volume {vol_ratio:.1f}x TB20 — thanh khoản thấp", "⚠"))

    # ── Quality / Risk signals ─────────────────────────────────────────────────

    # 5. Alpha 3M (dùng excess_ret_3m làm proxy)
    alpha_3m = _sf(metrics_dict.get("excess_ret_3m"))
    if alpha_3m is not None:
        pct = alpha_3m * 100
        if alpha_3m > 0:
            pos_raw.append((0.70, f"Alpha 3M dương: +{pct:.1f}% vs VNI", f"+{pct:.1f}%"))
        elif alpha_3m < -0.05:
            neg_raw.append((0.80, f"Alpha 3M âm: {pct:.1f}% vs VNI", "⚠"))

    # 6. Sharpe 12M vs benchmark
    sharpe_12m = _sf(metrics_dict.get("sharpe_12m"))
    bench_sharpe = _sf(metrics_dict.get("bench_sharpe_12m"))
    if sharpe_12m is not None:
        if bench_sharpe is not None and sharpe_12m > bench_sharpe:
            pos_raw.append((0.75, f"Sharpe 12M: {sharpe_12m:.2f} > VNI {bench_sharpe:.2f}", f"{sharpe_12m:.2f}"))
        elif sharpe_12m < 0.5:
            neg_raw.append((0.70, f"Sharpe 12M thấp: {sharpe_12m:.2f} < 0.5", "⚠"))

    # 7. Beta asymmetry
    b_up = _sf(metrics_dict.get("beta_up_12m"))
    b_dn = _sf(metrics_dict.get("beta_dn_12m"))
    if b_up is not None and b_dn is not None:
        if b_up > b_dn:
            pos_raw.append((0.65, f"Beta bất xứng tốt: βup={b_up:.2f} > βdn={b_dn:.2f}", f"βup={b_up:.2f}"))
        elif b_dn > b_up:
            neg_raw.append((0.85, f"Beta bất xứng: βdn={b_dn:.2f} > βup={b_up:.2f}", "⚠"))

    # ── Sort & limit ───────────────────────────────────────────────────────────
    pos_raw.sort(key=lambda x: x[0], reverse=True)
    neg_raw.sort(key=lambda x: x[0], reverse=True)

    positive = [{"label": p[1], "value": p[2]} for p in pos_raw[:3]]
    negative = [{"label": n[1], "value": n[2]} for n in neg_raw[:3]]

    agreement = f"{momentum_positive}/{momentum_total}"
    momentum_ok = momentum_total > 0 and momentum_positive >= 2

    return {
        "positive": positive,
        "negative": negative,
        "agreement": agreement,
        "rsi": rsi,
        "macd_slope": slope,
        "mfi": mfi,
        "vol_ratio": vol_ratio,
        "momentum_ok": momentum_ok,
        "candle_flags": candle_flags,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CALC DYNAMIC STOP
# ─────────────────────────────────────────────────────────────────────────────


def calc_dynamic_stop(close: float, hist_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Tính trailing stop động theo ATR-14 × 2.0 hoặc swing low 20 phiên × 0.99.
    Dùng cái nào cho stop_price cao hơn (chặt hơn).

    Args:
        close: giá đóng cửa hiện tại
        hist_df: OHLCV DataFrame (>= 20 rows; cần: high, low, close)

    Returns:
        {
            "stop_price": float|None,
            "stop_pct":   float|None,    # % khoảng cách stop so với close
            "method":     "ATR"|"Structure"|None,
            "atr14":      float|None,
        }
    """
    result: Dict[str, Any] = {
        "stop_price": None,
        "stop_pct": None,
        "method": None,
        "atr14": None,
    }

    close_val = _sf(close)
    if close_val is None or close_val <= 0:
        return result
    if hist_df is None or hist_df.empty:
        return result
    if not _has_col(hist_df, "high", "low", "close"):
        return result

    high = hist_df["high"]
    low = hist_df["low"]
    prev_close = hist_df["close"]

    # ATR 14
    atr14 = _atr(high, low, prev_close, period=14)
    result["atr14"] = round(atr14, 1) if atr14 is not None else None

    atr_stop: Optional[float] = None
    if atr14 is not None:
        stop_distance_atr = atr14 * 2.0
        atr_stop = close_val - stop_distance_atr

    # Structure stop: swing low 20 phiên × 0.99
    structure_stop: Optional[float] = None
    try:
        swing_low = float(low.tail(20).min())
        structure_stop = swing_low * 0.99
    except Exception:
        structure_stop = None

    # Chọn stop cao hơn (chặt hơn — giảm lỗ nhiều hơn)
    if atr_stop is not None and structure_stop is not None:
        if atr_stop >= structure_stop:
            stop_price = atr_stop
            method = "ATR"
        else:
            stop_price = structure_stop
            method = "Structure"
    elif atr_stop is not None:
        stop_price = atr_stop
        method = "ATR"
    elif structure_stop is not None:
        stop_price = structure_stop
        method = "Structure"
    else:
        return result

    if stop_price <= 0:
        return result

    stop_dist = close_val - stop_price
    stop_pct = round(stop_dist / close_val * 100, 1)

    result["stop_price"] = round(stop_price, 0)
    result["stop_pct"] = stop_pct
    result["method"] = method
    return result


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    import sys
    import os

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

    async def _test(symbol: str = "MSN"):
        print(f"\n{'=' * 60}")
        print(f"  signal_engine.py — Test với {symbol}")
        print(f"{'=' * 60}\n")

        from datetime import datetime, timedelta
        from app.vnstock_core.core import fetch_ohlcv

        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")

        print(f"Đang fetch OHLCV {symbol} từ {start} đến {end}...")
        df = await asyncio.to_thread(fetch_ohlcv, symbol, start, end)
        # Fallback: thử vài ngày trước nếu hôm nay không có data (cuối tuần)
        if df.empty:
            for days_back in range(1, 8):
                prev = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
                df = await asyncio.to_thread(fetch_ohlcv, symbol, start, prev)
                if not df.empty:
                    print(f"  → Fallback về ngày {prev}")
                    break

        if df.empty:
            print(f"[LỖI] Không fetch được dữ liệu cho {symbol}")
            return

        hist_df = df.tail(65).reset_index(drop=True)
        print(f"  → {len(hist_df)} phiên. Cột: {list(hist_df.columns)}")
        print(f"  → Close cuối: {hist_df['close'].iloc[-1]:.0f}")

        metrics_dict = {
            "sharpe_12m": 0.72,
            "bench_sharpe_12m": 0.55,
            "excess_ret_3m": 0.04,
            "beta_up_12m": 0.95,
            "beta_dn_12m": 1.10,
        }

        print("\n─── classify_signals ────────────────────────────────────")
        signals = classify_signals(symbol, hist_df, metrics_dict)

        print(f"  Agreement: {signals['agreement']}")
        print(f"  Momentum OK: {signals['momentum_ok']}")
        print(f"  RSI: {signals['rsi']}")
        print(f"  MACD slope: {signals['macd_slope']}")
        print(f"  MFI: {signals['mfi']}")
        print(f"  Vol ratio: {signals['vol_ratio']}")
        print(f"\n  🟢 Tích cực ({len(signals['positive'])}):")
        for p in signals["positive"]:
            print(f"    • {p['label']}: {p['value']}")
        print(f"\n  🔴 Tiêu cực ({len(signals['negative'])}):")
        for n in signals["negative"]:
            print(f"    • {n['label']}: {n['value']}")

        print("\n─── calc_dynamic_stop ───────────────────────────────────")
        close = float(hist_df["close"].iloc[-1])
        stop = calc_dynamic_stop(close, hist_df)
        print(f"  Close: {close:.0f}")
        print(f"  Stop price: {stop['stop_price']}")
        print(f"  Stop %: {stop['stop_pct']}%")
        print(f"  Method: {stop['method']}")
        print(f"  ATR14: {stop['atr14']}")
        print(f"\n{'=' * 60}")

    ticker = sys.argv[1] if len(sys.argv) > 1 else "MSN"
    asyncio.run(_test(ticker))
