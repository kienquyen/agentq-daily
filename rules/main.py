#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import inspect
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytz
import requests
import ta
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# === VNSTOCK_DATA IMPORTS ===
# vnstock_data is a local module bundled in ai/vnstock_data/
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _p in [str(_REPO_ROOT / "ai"), str(_REPO_ROOT), os.getcwd()]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from vnstock_data import Quote
except ImportError as _e:
    raise ImportError(
        f"vnstock_data not found. Ensure ai/vnstock_data/ exists in repo. ({_e})"
    )

# =========================
# CONFIG
# =========================
VNSTOCK_API_KEY = os.getenv("VNSTOCK_API_KEY", "").strip()
if not VNSTOCK_API_KEY:
    # Fallback to older XNO_API_KEY if exists (for migration)
    VNSTOCK_API_KEY = os.getenv("XNO_API_KEY", "").strip()

if not VNSTOCK_API_KEY:
    print("❌ Missing VNSTOCK_API_KEY environment variable")
    # We don't raise error immediately to allow local debugging if needed, 
    # but the Quote init will likely fail.

VNSTOCK_SOURCE = os.getenv("VNSTOCK_SOURCE", "VCI").strip().upper()
FALLBACK_SOURCES = os.getenv("VNSTOCK_FALLBACK_SOURCES", "KBS,MAS,VND").split(",")
FALLBACK_SOURCES = [s.strip().upper() for s in FALLBACK_SOURCES if s.strip()]

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
if not DISCORD_WEBHOOK_URL:
    print("⚠️ DISCORD_WEBHOOK_URL missing -> bot will NOT send messages to Discord.")

DAILY_RUN_HOUR   = int(os.getenv("DAILY_RUN_HOUR", "19"))
DAILY_RUN_MINUTE = int(os.getenv("DAILY_RUN_MINUTE", "0"))
LOCAL_TZ = os.getenv("LOCAL_TZ", "Asia/Ho_Chi_Minh")

# Max symbols to scan (ranked by volume)
MAX_UNIVERSE = int(os.getenv("MAX_UNIVERSE", "100"))

# Web export config
WEB_EXPORT_ENABLED = os.getenv("WEB_EXPORT", "1").strip() == "1"
# Repo public riêng cho website (agentq-daily), để code repo giữ private
WEB_REPO_DIR    = Path(os.getenv("WEB_REPO_DIR",
                       str(Path(__file__).parent.parent)))  # monorepo root
WEB_SIGNALS_DIR = WEB_REPO_DIR / "signals"

# Deprecated: PRICE_IN_K = os.getenv("PRICE_IN_K", "1").strip() == "1"


# Universe
VN100_SYMBOLS = [
    "AAA", "AAM", "AAS", "ABB", "ABI", "ACB", "ACL", "ACV", "AFX", "AGG",
    "AGR", "AIG", "AMV", "AMS", "ANV", "APF", "APG", "APH", "APS", "AST",
    "BAB", "BCC", "BCM", "BFC", "BIC", "BID", "BMI", "BMP", "BNA", "BSI",
    "BSR", "BTS", "BVB", "BVH", "BWE", "C32", "C47", "C4G", "CEO", "CIG",
    "CMG", "CMX", "CNG", "CRE", "CSM", "CTD", "CTF", "CTG", "CTI", "CTR",
    "CTS", "D2D", "DAG", "DAH", "DBD", "DBC", "DCL", "DC4", "DCM", "DGC",
    "DGW", "DHG", "DHA", "DHC", "DHT", "DIG", "DMC", "DPM", "DPR", "DRC",
    "DRG", "DRI", "DSC", "DTD", "DXG", "DXP", "DXS", "EIB", "EVF", "EVS",
    "FCM", "FCN", "FMC", "FOC", "FOX", "FPT", "FRT", "FTS", "G36", "GAS",
    "GDT", "GEG", "GEX", "GMD", "GSP", "GVR", "HAG", "HAH", "HAX", "HBC",
    "HDC", "HDG", "HHS", "HHV", "HHG", "HII", "HLD", "HOM", "HQC", "HRC",
    "HT1", "HTI", "HTN", "HUT", "HVH", "HVN", "IDC", "IDI", "IJC", "ILB",
    "IMP", "ITA", "ITD", "JVC", "KBC", "KDC", "KDH", "KHG", "KHP", "KSB",
    "LAS", "L14", "LCG", "LDG", "LDP", "LHG", "LIG", "LIX", "LSS", "LTG",
    "MBB", "MBS", "MCM", "MIG", "MLS", "MSB", "MSN", "MWG", "NAB", "NCT",
    "NHA", "NHH", "NKG", "NLG", "NSH", "NT2", "NTC", "NTL", "NVB", "NTP",
    "NVL", "OCB", "ORS", "PAN", "PC1", "PDR", "PET", "PGI", "PGN", "PHR",
    "PLC", "PLP", "PMB", "PNJ", "POM", "POW", "PPC", "PRE", "PSH", "PSI",
    "PTB", "PTI", "PVB", "PVC", "PVD", "PVP", "PVS", "PVT", "PXS", "PXT",
    "PVG", "QCG", "QNS", "QTP", "REE", "RIC", "SAS", "SBT", "SBS", "SCS",
    "SD5", "SD6", "SGN", "SGP", "SHA", "SHB", "SHI", "SHS", "SIP", "SJD",
    "SJG", "SKG", "SLS", "SMC", "SPM", "SSI", "SSB", "STB", "STG", "SWC",
    "SZC", "SZL", "TAR", "TCD", "TCH", "TCL", "TCB", "TCI", "TCW", "THG",
    "TIP", "TLH", "TMS", "TNH", "TNC", "TRC", "TV2", "TVB", "TVN",
    "TVS", "TTF", "VAB", "VCA", "VCB", "VCG", "VCI", "VCS", "VDS", "VGC",
    "VGI", "VHC", "VHE", "VHM", "VIB", "VIC", "VIG", "VIP", "VIX", "VLC",
    "VNA", "VND", "VNE", "VNM", "VNP", "VNR", "VOS", "VPB", "VPI", "VRE",
    "VSC", "VSH", "VTD", "VTO", "VTP", "VGS", "WSS"
]

# =========================
# VNSTOCK DATA HELPERS
# =========================
ALLOWED_SOURCES = {"VCI", "KBS", "VND", "MAS"}

def _safe_source(src: str) -> str:
    s = (src or "VCI").strip().upper()
    return s if s in ALLOWED_SOURCES else "VCI"

def _create_quote(symbol: str, source: str | None = None):
    """Create Quote object with dynamic signature handling."""
    src = _safe_source(source or VNSTOCK_SOURCE)
    key = (VNSTOCK_API_KEY or "").strip()

    sig = inspect.signature(Quote)
    p = sig.parameters
    
    # Try different initialization patterns
    # Thêm random_agent=True để rotate User-Agent, giúp bypass rate-limit/block
    # trên cloud server (Railway, Heroku, etc.)
    use_random_agent = "random_agent" in p

    try:
        # Pattern 1: Quote(source=..., symbol=..., random_agent=True)
        kwargs = {"source": src}
        if use_random_agent:
            kwargs["random_agent"] = True
        if "show_log" in p:
            kwargs["show_log"] = False
        if any(k in p for k in ["api_key", "apikey", "key"]):
            ak_name = [k for k in ["api_key", "apikey", "key"] if k in p][0]
            kwargs[ak_name] = key

        sym_name = [k for k in ["symbol", "ticker", "code"] if k in p]
        if sym_name:
            kwargs[sym_name[0]] = symbol
            return Quote(**kwargs)
        else:
            return Quote(symbol, **kwargs)
    except Exception:
        pass

    # Fallback brute force
    trials = [
        ((symbol, src), {"random_agent": True} if use_random_agent else {}),
        ((src, symbol), {}),
        ((symbol,), {"source": src}),
        ((symbol,), {}),
    ]
    for args, kwargs in trials:
        try:
            return Quote(*args, **kwargs)
        except Exception:
            continue
    
    raise RuntimeError(f"Could not initialize vnstock_data.Quote for {symbol}")

def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    d = df.copy()
    d.columns = [str(c).lower().strip() for c in d.columns]

    # Handle time/date
    found_time = False
    for tcol in ["time", "date", "tradingdate", "datetime"]:
        if tcol in d.columns:
            d["time"] = pd.to_datetime(d[tcol], errors="coerce")
            found_time = True
            break
    
    if not found_time:
        return pd.DataFrame()

    # Map OHLCV aliases
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

    out = out.dropna(subset=["time", "close"]).sort_values("time").reset_index(drop=True)
    return out

def _fetch_history_any_source(symbol: str, start: str, end: str, interval: str = "1D"):
    """Try main source then fallbacks to avoid device limits."""
    sources = [VNSTOCK_SOURCE] + [s for s in FALLBACK_SOURCES if s != VNSTOCK_SOURCE]
    
    for src in sources:
        try:
            q = _create_quote(symbol, source=src)
            # Some versions use start/end, others might use different names or just return all
            try:
                df = q.history(start=start, end=end, interval=interval)
            except Exception:
                df = q.history(start=start, end=end)
            
            df_norm = _normalize_ohlcv(df)
            if not df_norm.empty:
                return df_norm, src
        except Exception:
            continue
    return pd.DataFrame(), None

def fetch_top_vn100_data(start="2024-01-01", use_local: bool = False, as_of_date: str | None = None):
    """Fetch OHLCV universe data.

    When use_local=True, reads from ai/data/ohlcv/*.parquet (fast, no API calls).
    Falls back to API fetch when local files are missing.
    """
    end = as_of_date or datetime.utcnow().strftime("%Y-%m-%d")
    out = {}

    ohlcv_dir = _REPO_ROOT / "ai" / "data" / "ohlcv"

    if use_local and ohlcv_dir.exists():
        print(f"📂 Loading universe from local OHLCV store ({ohlcv_dir.name})...")
        all_data = []
        for sym in VN100_SYMBOLS:
            parquet = ohlcv_dir / f"{sym}.parquet"
            if not parquet.exists():
                continue
            try:
                df = pd.read_parquet(parquet)
                df = _normalize_ohlcv(df)
                if df.empty:
                    continue
                # Filter to as_of_date
                df["time"] = pd.to_datetime(df["time"])
                df = df[df["time"] <= pd.Timestamp(end)].copy()
                if len(df) < 60:
                    continue
                last_vol = float(df["volume"].iloc[-1]) if not pd.isna(df["volume"].iloc[-1]) else 0.0
                all_data.append({"symbol": sym, "volume": last_vol, "df": df})
            except Exception:
                continue

        if not all_data:
            print("⚠️  No local OHLCV data found — falling back to API fetch")
        else:
            df_vol = pd.DataFrame(all_data).sort_values("volume", ascending=False)
            top_syms = df_vol.head(MAX_UNIVERSE)["symbol"].tolist()
            for item in all_data:
                if item["symbol"] in top_syms:
                    out[item["symbol"]] = {"df": item["df"], "exchange": "HOSE"}
            print(f"✅ Loaded {len(out)} symbols from local store")
            return out

    print(f"🔍 Fetching universe data (up to {MAX_UNIVERSE} symbols)...")

    # First pass: Fetch recent volume to rank
    all_data = []
    for sym in VN100_SYMBOLS:
        try:
            df, src = _fetch_history_any_source(sym, (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"), end)
            if not df.empty:
                last_vol = float(df["volume"].iloc[-1]) if not pd.isna(df["volume"].iloc[-1]) else 0.0
                all_data.append({"symbol": sym, "volume": last_vol, "df": df})
            time.sleep(0.02)
        except Exception:
            continue

    if not all_data:
        return {}

    # Sort by volume and take top MAX_UNIVERSE
    df_vol = pd.DataFrame(all_data).sort_values("volume", ascending=False)
    top_syms = df_vol.head(MAX_UNIVERSE)["symbol"].tolist()

    # Second pass: Fetch full history for top symbols (if not already fetched)
    for sym in top_syms:
        existing = next((x for x in all_data if x["symbol"] == sym), None)
        if existing and len(existing["df"]) > 50:
            out[sym] = {"df": existing["df"], "exchange": "HOSE"}
            continue
        try:
            df, src = _fetch_history_any_source(sym, start, end)
            if not df.empty:
                out[sym] = {"df": df, "exchange": "HOSE"}
            time.sleep(0.02)
        except Exception:
            continue

    return out

def get_vnindex_latest():
    end = datetime.utcnow().strftime("%Y-%m-%d")
    for sym in ["VNINDEX", "VNI"]:
        df, src = _fetch_history_any_source(sym, "2025-01-01", end)
        if not df.empty:
            return float(df["close"].iloc[-1])
    return None

def _clip(x, lo=0.0, hi=1.0):
    """Clip value to range [lo, hi]."""
    if isinstance(x, float) and np.isnan(x):
        return lo
    return max(lo, min(hi, float(x)))

def _linear(x, lo, hi):
    """Linear interpolation from lo to hi."""
    if hi == lo:
        return 0.0
    return _clip((float(x) - lo) / (hi - lo))

def _tri_ideal(x, center, half_width):
    """Triangle ideal: peak at center, falls off by half_width."""
    return _clip(1.0 - abs(float(x) - center) / float(half_width))

def calculate_regime_score_agentq(feat: dict) -> dict:
    """
    AgentQ 4-Layer Market Regime Scoring (0.0-1.0).

    Weights:
      • Trend (35%):    Price position, MA crosses, momentum
      • Breadth (30%):  A/D ratio, RSI divergence, gainer/loser
      • Flow (25%):     Foreign flow, sector rotation quality
      • Vol (10%):      Volatility spike warning only

    Returns: {
        "score": 0.0-1.0 composite,
        "label": "strong_bull|bull|recovery|ranging|bear_risk",
        "icon": emoji,
        "breakdown": {trend, breadth, flow, vol, overrides}
    }
    """
    # ── LAYER 1: TREND (35%) ─────────────────────────────────────────
    # Indicators: price vs EMA200/50, EMA cross, MACD, returns

    price_vs_ema200_pct = feat.get("price_vs_ema200", 0)
    price_vs_ema50_pct = feat.get("price_vs_ema50", 0)

    t_vs_ema200 = _linear(price_vs_ema200_pct, -10, 10)       # -10% → +10%
    t_vs_ema50 = _linear(price_vs_ema50_pct, -5, 5)           # -5% → +5%
    t_ema_cross = 1.0 if feat.get("ema_cross_up") else 0.0    # Binary
    t_macd = 1.0 if feat.get("macd_hist", 0) > 0 else 0.0    # Binary
    t_return_5d = _linear(feat.get("return_5d", 0), -3, 3)    # -3% → +3%
    t_return_20d = _linear(feat.get("return_20d", 0), -8, 8)  # -8% → +8%

    trend_score = (
        t_vs_ema200 * 0.25
        + t_vs_ema50 * 0.20
        + t_ema_cross * 0.20
        + t_macd * 0.15
        + t_return_5d * 0.12
        + t_return_20d * 0.08
    )

    # ── LAYER 2: BREADTH (30%) ──────────────────────────────────────
    # Indicators: A/D ratio (real), RSI divergence, VNIndex RSI

    ad_ratio  = feat.get("ad_ratio", None)
    ad_5d_avg = feat.get("ad_5d_avg", None)
    rsi_neutral = _tri_ideal(feat.get("rsi14_idx", 50), 50, 25)

    if ad_ratio is not None:
        # Real A/D data available
        # ad_ratio: % cổ phiếu tăng hôm nay (0→1), ideal ≈ 0.55–0.65 (thị trường khoẻ)
        ad_today  = _linear(ad_ratio, 0.25, 0.75)    # 25%→75% tăng
        # Momentum: hôm nay so với TB 5 phiên
        ad_momentum = _linear(ad_ratio - ad_5d_avg, -0.15, 0.15)  # breadth đang cải thiện?
        breadth_score = ad_today * 0.55 + ad_momentum * 0.20 + rsi_neutral * 0.25
    else:
        # Fallback: chỉ dùng RSI của VNINDEX
        breadth_score = rsi_neutral * 0.6

    # Adjust for divergences and overbought
    if feat.get("rsi_bear_div"):
        breadth_score *= 0.7
    if feat.get("rsi_overbought") and trend_score > 0.6:
        breadth_score *= 0.85
    if feat.get("rsi_oversold"):
        breadth_score *= 1.1

    breadth_score = _clip(breadth_score)

    # ── LAYER 3: MONEY FLOW (25%) ───────────────────────────────────
    # Indicators: Foreign flow streak, flow acceleration

    flow_score = 0.5  # Neutral default

    # Foreign flow ranking (percentile 0-1)
    if "foreign_net_pct_rank" in feat:
        base = float(feat["foreign_net_pct_rank"])

        # Streak bonus: +5d buying = +0.15, -5d selling = -0.15
        streak = feat.get("flow_streak", 0)
        streak_bonus = _linear(abs(streak), 0, 10) * 0.15 * (1 if streak > 0 else -1)

        # Acceleration bonus: how much faster today vs last 5d avg
        acc = feat.get("flow_acceleration", 0.0)
        acc_bonus = _linear(acc, -500, 500) * 0.10 - 0.05

        flow_score = _clip(base + streak_bonus + acc_bonus)

    # ── LAYER 4: VOLATILITY (10%) ───────────────────────────────────
    # Indicators: BB width percentile, ATR spike (risk signal)

    vol_score = 1.0 - feat.get("bb_width_pct", 0.5)  # Inverted: low BB = low vol

    if feat.get("atr_spike"):
        vol_score *= 0.6  # Risk signal: high volatility

    vol_score = _clip(vol_score)

    # ── COMPOSITE SCORE ──────────────────────────────────────────────
    composite = _clip(
        trend_score * 0.35
        + breadth_score * 0.30
        + flow_score * 0.25
        + vol_score * 0.10
    )

    # ── HARD OVERRIDES ───────────────────────────────────────────────
    overrides_applied = []

    # Override 1: Distribution days (rally exhaustion)
    dist_days = feat.get("dist_days", 0)
    if dist_days >= 8:
        composite *= 0.70
        overrides_applied.append(f"dist_days={dist_days} (CRITICAL) ×0.70")
    elif dist_days >= 6:
        composite *= 0.80
        overrides_applied.append(f"dist_days={dist_days} (High Risk) ×0.80")
    elif dist_days >= 5:
        composite *= 0.88
        overrides_applied.append(f"dist_days={dist_days} (Elevated) ×0.88")
    elif dist_days >= 3 and composite > 0.65:
        composite *= 0.95
        overrides_applied.append(f"dist_days={dist_days} (Caution) ×0.95")

    # Override 2: MACD flip (momentum reversal)
    if feat.get("macd_hist_flipped") and composite > 0.55:
        composite *= 0.88
        overrides_applied.append("MACD_flip ×0.88")

    # Override 3: Weak trend + fatigue
    adx_val = feat.get("adx14", 99)
    if adx_val < 15 and feat.get("is_fatigue"):
        composite = min(composite, 0.40)
        overrides_applied.append("ADX<15+fatigue → capped@0.40")

    composite = _clip(composite)

    # ── CLASSIFY REGIME ──────────────────────────────────────────────
    if composite >= 0.75:
        label = "strong_bull"
        regime_icon = "🟢💪"
        regime_vn = "TĂNG MẠNH"
    elif composite >= 0.60:
        label = "bull"
        regime_icon = "🟢"
        regime_vn = "TĂNG"
    elif composite >= 0.45:
        label = "recovery"
        regime_icon = "🔵"
        regime_vn = "HỒI PHỤC"
    elif composite >= 0.30:
        label = "ranging"
        regime_icon = "🟡"
        regime_vn = "ĐI NGANG"
    else:
        label = "bear_risk"
        regime_icon = "🔴"
        regime_vn = "GIẢM"

    return {
        "score": round(composite * 100, 1),  # 0-100 for display
        "score_normalized": round(composite, 3),  # 0.0-1.0 for logic
        "label": label,
        "icon": regime_icon,
        "vn_label": regime_vn,
        "breakdown": {
            "trend": round(trend_score, 3),
            "breadth": round(breadth_score, 3),
            "flow": round(flow_score, 3),
            "vol": round(vol_score, 3),
            "composite": round(composite, 3),
            "overrides": overrides_applied
        }
    }

def compute_ad_ratio(data_map: dict, as_of_date: pd.Timestamp | None = None) -> dict:
    """
    Tính Advance/Decline ratio từ universe data.
    Returns: {ad_ratio, ad_5d_avg, advances, declines, unchanged}
    """
    target = (as_of_date or pd.Timestamp.today()).normalize()
    advances = declines = unchanged = 0
    ad_history = []  # ad_ratio theo từng ngày trong 5 phiên gần nhất

    daily_results: dict[str, list] = {}  # date → [ad_ratio per day]

    for sym, data in data_map.items():
        try:
            df = data["df"].copy()
            df["time"] = pd.to_datetime(df["time"])
            df = df[df["time"] <= target].sort_values("time")
            if len(df) < 2:
                continue
            c = df["close"]
            # 5 phiên gần nhất
            for i in range(max(1, len(df) - 5), len(df)):
                date_key = str(df["time"].iloc[i])[:10]
                prev_c = float(c.iloc[i - 1])
                curr_c = float(c.iloc[i])
                if prev_c == 0:
                    continue
                chg = curr_c - prev_c
                daily_results.setdefault(date_key, []).append(1 if chg > 0 else (-1 if chg < 0 else 0))
        except Exception:
            continue

    if not daily_results:
        return {"ad_ratio": 0.5, "ad_5d_avg": 0.5, "advances": 0, "declines": 0, "unchanged": 0}

    sorted_dates = sorted(daily_results.keys())
    # Today (last date)
    today_key = sorted_dates[-1]
    today_vals = daily_results[today_key]
    advances  = sum(1 for v in today_vals if v > 0)
    declines  = sum(1 for v in today_vals if v < 0)
    unchanged = sum(1 for v in today_vals if v == 0)
    total = advances + declines + unchanged
    ad_ratio = advances / total if total > 0 else 0.5

    # 5-day average
    ratios_5d = []
    for dk in sorted_dates[-5:]:
        vals = daily_results[dk]
        t = len(vals)
        if t > 0:
            ratios_5d.append(sum(1 for v in vals if v > 0) / t)
    ad_5d_avg = sum(ratios_5d) / len(ratios_5d) if ratios_5d else ad_ratio

    return {
        "ad_ratio": round(ad_ratio, 3),
        "ad_5d_avg": round(ad_5d_avg, 3),
        "advances": advances,
        "declines": declines,
        "unchanged": unchanged,
    }


def get_vnindex_regime(as_of_date: pd.Timestamp | None = None, universe_data: dict | None = None) -> dict:
    """
    Fetch VNINDEX & compute AgentQ 4-layer market regime.

    Returns:
      - regime_score (0-100): Composite market quality
      - regime_label: strong_bull|bull|recovery|ranging|bear_risk
      - regime_icon: Emoji
      - ok (bool): True if safe for BUY1 (legacy compatibility)
      - detail (str): Formatted message for logging/Discord
      - breakdown: {trend, breadth, flow, vol, overrides}
    """
    end = (as_of_date or pd.Timestamp.today()).strftime("%Y-%m-%d")
    start = (pd.Timestamp(end) - pd.Timedelta(days=700)).strftime("%Y-%m-%d")

    df_vni = pd.DataFrame()
    for sym in ["VNINDEX", "VNI"]:
        df_tmp, _ = _fetch_history_any_source(sym, start, end)
        if not df_tmp.empty:
            df_vni = df_tmp
            break

    # Không fetch được → fail-open
    if df_vni.empty or len(df_vni) < 210:
        return {
            "regime_score": 50,
            "regime_label": "unknown",
            "regime_icon": "❓",
            "ok": True,
            "reason": "VNIndex data unavailable",
            "detail": "⚠️ Regime: N/A (not enough data)",
            "breakdown": {}
        }

    df_vni = df_vni.sort_values("time").reset_index(drop=True)
    c = df_vni["close"]
    h = df_vni["high"]
    l = df_vni["low"]

    # ── Compute all indicators ──────────────────────────────────────
    ema9 = c.ewm(span=9, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    ema200 = c.ewm(span=200, adjust=False).mean()

    adx14 = ta.trend.adx(h, l, c, window=14)
    bb = ta.volatility.BollingerBands(c, window=20, window_dev=2)
    bb_width = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()
    bb_width_pct = bb_width.rolling(252).rank(pct=True)

    rsi14 = ta.momentum.rsi(c, window=14)

    # MACD
    macd_line = ema9 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - signal_line

    # Distribution days (last 15)
    dist_day = (c < c.shift(1)).astype(int)
    dist_days = dist_day.rolling(15).sum()

    # Returns
    ret_5d = c.pct_change(5) * 100
    ret_20d = c.pct_change(20) * 100

    # Foreign flow (if available)
    avg_5d_prev = 0.0  # Placeholder
    acceleration = 0.0

    # ── Extract latest row ──────────────────────────────────────────
    L_idx = len(df_vni) - 1
    feat = {
        "date": str(df_vni["time"].iloc[-1])[:10],
        "close": float(c.iloc[-1]),
        "price_vs_ema200": float((c.iloc[-1] - ema200.iloc[-1]) / ema200.iloc[-1] * 100),
        "price_vs_ema50": float((c.iloc[-1] - c.rolling(50).mean().iloc[-1]) / c.rolling(50).mean().iloc[-1] * 100),
        "ema_cross_up": float(ema9.iloc[-1]) > float(ema26.iloc[-1]),
        "macd_hist": float(macd_hist.iloc[-1]),
        "macd_hist_flipped": (
            float(macd_hist.iloc[-1]) < 0 and
            pd.notna(macd_hist.iloc[-2]) and
            float(macd_hist.iloc[-2]) >= 0
        ),
        "adx14": float(adx14.iloc[-1]),
        "return_5d": float(ret_5d.iloc[-1]) if pd.notna(ret_5d.iloc[-1]) else 0.0,
        "return_20d": float(ret_20d.iloc[-1]) if pd.notna(ret_20d.iloc[-1]) else 0.0,
        "rsi14_idx": float(rsi14.iloc[-1]),
        "rsi_bear_div": (
            float(c.iloc[-1]) >= float(c.rolling(14).mean().iloc[-1]) and
            float(rsi14.iloc[-1]) < float(rsi14.rolling(14).mean().iloc[-1])
        ),
        "rsi_overbought": float(rsi14.iloc[-1]) >= 70,
        "rsi_oversold": float(rsi14.iloc[-1]) <= 30,
        "bb_width_pct": float(bb_width_pct.iloc[-1]),
        "dist_days": int(dist_days.iloc[-1]) if pd.notna(dist_days.iloc[-1]) else 0,
        "atr_spike": False,  # Skip ATR for simplicity
        "is_fatigue": False,  # Simplified
        "foreign_net_pct_rank": 0.5,
        "flow_streak": 0,
        "flow_acceleration": 0.0,
        "ad_ratio": 0.5,
        "ad_5d_avg": 0.5,
    }

    # Inject real A/D ratio if universe data available
    if universe_data:
        ad = compute_ad_ratio(universe_data, as_of_date)
        feat["ad_ratio"]   = ad["ad_ratio"]
        feat["ad_5d_avg"]  = ad["ad_5d_avg"]
        feat["ad_advances"] = ad["advances"]
        feat["ad_declines"] = ad["declines"]

    # ── Calculate AgentQ regime ─────────────────────────────────────
    regime_info = calculate_regime_score_agentq(feat)

    # ── Legacy BUY1 filter (based on hard thresholds) ────────────────
    # BUY1 ON if: ADX >= 18 AND ROC5d >= -3% AND DD20d >= -8%
    adx_val = feat["adx14"]
    roc5_val = float((c.iloc[-1] / c.iloc[-6] - 1) * 100) if len(c) >= 6 else 0.0
    high20 = float(h.rolling(20).max().iloc[-1])
    dd20_val = float((c.iloc[-1] - high20) / high20 * 100)

    fail_adx = adx_val < 18
    fail_roc5 = roc5_val < -3.0
    fail_dd20 = dd20_val < -8.0
    ok = not (fail_adx or fail_roc5 or fail_dd20)

    reasons_fail = []
    if fail_adx: reasons_fail.append(f"ADX={adx_val:.1f}<18")
    if fail_roc5: reasons_fail.append(f"ROC5d={roc5_val:+.1f}%<-3%")
    if fail_dd20: reasons_fail.append(f"DD20d={dd20_val:.1f}%<-8%")

    regime_label = "🟢 TREND" if ok else "🔴 CHOP/RISK"

    # ── Format detail message ──────────────────────────────────────
    ad_str = ""
    if feat.get("ad_advances") is not None:
        ad_str = f"  A/D={feat['ad_advances']}↑/{feat['ad_declines']}↓"
    detail = (
        f"{regime_label}  ADX={adx_val:.1f}  ROC5d={roc5_val:+.1f}%  DD20d={dd20_val:.1f}%{ad_str}  →  BUY1={'ON' if ok else 'OFF'}\n"
        f"{regime_info['icon']} **{regime_info['vn_label']}** (Score {regime_info['score']:.0f}/100)\n"
        f"Trend {regime_info['breakdown']['trend']:.2f} · Breadth {regime_info['breakdown']['breadth']:.2f} · "
        f"Flow {regime_info['breakdown']['flow']:.2f} · Vol {regime_info['breakdown']['vol']:.2f}"
    )

    if regime_info['breakdown']['overrides']:
        detail += f"\nOverrides: {' | '.join(regime_info['breakdown']['overrides'])}"

    return {
        "regime_score": regime_info["score"],
        "regime_score_normalized": regime_info["score_normalized"],
        "regime_label": regime_info["label"],
        "regime_icon": regime_info["icon"],
        "regime_vn": regime_info["vn_label"],
        "ok": ok,
        "reason": "All conditions OK" if ok else " | ".join(reasons_fail),
        "adx": adx_val,
        "roc5": roc5_val,
        "dd20": dd20_val,
        "detail": detail,
        "breakdown": regime_info["breakdown"]
    }

# =========================
# INDICATORS
# =========================
def apply_custom_ma(series, ma_type="EMA", length=9, alma_offset=0.85, alma_sigma=6):
    if ma_type == "EMA":
        return ta.trend.ema_indicator(series, window=length)
    if ma_type == "SMA":
        return ta.trend.sma_indicator(series, window=length)
    if ma_type == "WMA":
        return ta.trend.wma_indicator(series, window=length)
    if ma_type == "HMA":
        half = int(length / 2)
        sqrt = int(np.sqrt(length))
        w1 = ta.trend.wma_indicator(series, window=half)
        w2 = ta.trend.wma_indicator(series, window=length)
        diff = 2 * w1 - w2
        return ta.trend.wma_indicator(diff, window=sqrt)
    if ma_type == "ALMA":
        weights = np.exp(-((np.arange(length) - alma_offset * (length - 1)) ** 2) / (2 * alma_sigma ** 2))
        weights /= weights.sum()
        return series.rolling(length).apply(lambda x: np.dot(x, weights), raw=True)
    return ta.trend.ema_indicator(series, window=length)

def compute_trend(df, ma_type="EMA", ma_period=9):
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open  = df["close"].shift(1)
    ha_high  = df[["high","open","close"]].max(axis=1)
    ha_low   = df[["low","open","close"]].min(axis=1)

    ma_c = apply_custom_ma(ha_close, ma_type, ma_period)
    ma_o = apply_custom_ma(ha_open,  ma_type, ma_period)
    ma_h = apply_custom_ma(ha_high,  ma_type, ma_period)
    ma_l = apply_custom_ma(ha_low,   ma_type, ma_period)

    denom = (ma_h - ma_l).replace(0, np.nan)
    return 100 * (ma_c - ma_o) / denom

def detect_trend_fatigue(df, ema_length=9, lookback=30, flat_threshold_pct=0.4):
    if "ema9" not in df.columns:
        df["ema9"] = ta.trend.ema_indicator(df["close"], window=ema_length)

    df["is_fatigue"] = False
    for i in range(lookback, len(df)):
        ema_check = df.iloc[i - lookback]["ema9"]
        if pd.isna(ema_check) or ema_check == 0:
            continue
        ema_window = df.iloc[i - lookback + 1 : i + 1]["ema9"]
        diff_pct = (ema_window - ema_check).abs() / ema_check * 100
        df.at[i, "is_fatigue"] = diff_pct.mean() < flat_threshold_pct
    return df

def build_features(df: pd.DataFrame, lookback_buy2: int = 26):
    if df is None or df.empty:
        return pd.DataFrame(), {}

    d = df.copy().reset_index(drop=True)
    d["ema9"]  = ta.trend.ema_indicator(d["close"], window=9)
    d["rsi14"] = ta.momentum.rsi(d["close"], window=14)
    d["rsi2"]  = ta.momentum.rsi(d["close"], window=2)
    d["mfi14"] = ta.volume.money_flow_index(d["high"], d["low"], d["close"], d["volume"], window=14)
    d["adx14"] = ta.trend.adx(d["high"], d["low"], d["close"], window=14)

    # Divergences helper
    LB = 14
    avg_close = d["close"].rolling(LB).mean()
    avg_rsi = d["rsi14"].rolling(LB).mean()
    avg_mfi = d["mfi14"].rolling(LB).mean()
    d["rsi_bear_div"] = (d["close"] >= avg_close) & (d["rsi14"] < avg_rsi)
    d["mfi_bear_div"] = (d["close"] >= avg_close) & (d["mfi14"] < avg_mfi)
    d["rsi_superoverbought"] = d["rsi14"].rolling(18).max() >= 85

    d["trend"] = compute_trend(d)
    
    # Ichimoku Kumo A
    high_9  = d["high"].rolling(9).max()
    low_9   = d["low"].rolling(9).min()
    high_26 = d["high"].rolling(26).max()
    low_26  = d["low"].rolling(26).min()
    tenkan  = (high_9 + low_9) / 2
    kijun   = (high_26 + low_26) / 2
    d["kumo_a"] = ((tenkan + kijun) / 2).shift(25)

    # Supertrend direction
    atr10 = ta.volatility.average_true_range(d["high"], d["low"], d["close"], window=10)
    basic_lowerband = (d["high"] + d["low"]) / 2 - 3 * atr10
    st_dir = np.where(d["close"] > basic_lowerband, 1, -1)
    d["st_dir"] = pd.Series(st_dir).astype(int)
    d["st_change"] = d["st_dir"].diff()
    
    last_bearish_idx = d[d["st_change"] == 2].index.max()
    bearish_not_recent = (d.index[-1] - last_bearish_idx) > 9 if pd.notna(last_bearish_idx) else True

    d = detect_trend_fatigue(d)
    d["lowest_close_26"] = d["close"].rolling(lookback_buy2).min()
    d["lowest_rsi14_26"] = d["rsi14"].rolling(lookback_buy2).min()

    meta = {
        "bearish_switch_not_recent": bool(bearish_not_recent),
        "kqrsimf": bool((d.iloc[-1]["rsi14"] > d.iloc[-1]["mfi14"]) and (d.iloc[-1]["mfi14"] < 55)) if not d.empty else False
    }

    return d, meta

# =========================
# SIGNAL LOGIC
# =========================
def is_buy1_signal(d: pd.DataFrame, meta: dict) -> bool:
    if d is None or d.empty or d.shape[0] < 60: return False
    L, P1, P2 = d.iloc[-1], d.iloc[-2], d.iloc[-3]
    return (
        L["close"] >= L["ema9"] and L["trend"] > 0 and P1["trend"] > 0 and P2["trend"] <= 0
        and L["close"] > L["kumo_a"] and L["adx14"] > 13 and L["mfi14"] < 85 and L["rsi14"] <= 70
        and meta.get("bearish_switch_not_recent", True)
        and (not L["rsi_bear_div"]) and (not L["mfi_bear_div"])
        and (not L["rsi_superoverbought"]) and (not L["is_fatigue"])
        and (not meta.get("kqrsimf", False))
    )

def is_buy2_signal(d: pd.DataFrame) -> bool:
    if d is None or d.empty or d.shape[0] < 27: return False
    L = d.iloc[-1]
    return (L["close"] <= L["lowest_close_26"] and L["rsi14"] > L["lowest_rsi14_26"] 
            and L["lowest_rsi14_26"] <= 30 and L["rsi2"] < 20 and L["rsi14"] < 33)

def is_buy3_signal(d: pd.DataFrame) -> bool:
    if d is None or d.empty or d.shape[0] < 15: return False
    L = d.iloc[-1]
    return (L["rsi2"] <= 4 and L["rsi14"] < 25 and L["mfi14"] < 20)

# =========================
# STRENGTH SCORING
# =========================
def _clip(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x))) if not (isinstance(x, float) and np.isnan(x)) else lo

def _linear(x, lo, hi):
    if hi == lo: return 0.0
    return _clip((float(x) - lo) / (hi - lo), 0.0, 1.0)

def _tri_ideal(x, center, half_width):
    return _clip(1.0 - abs(float(x) - center) / float(half_width), 0.0, 1.0)

def _top_reasons(pos, pen):
    pos_s = sorted(pos.items(), key=lambda kv: kv[1], reverse=True)[:2]
    pen_s = sorted(pen.items(), key=lambda kv: kv[1], reverse=True)[:1]
    res = [f"+{k} ({v:.1f})" for k, v in pos_s if v > 0]
    res += [f"-{k} ({v:.1f})" for k, v in pen_s if v > 0]
    return res

def get_signal_parameters(regime_label: str, signal_type: str) -> dict:
    """
    Get adaptive parameters based on market regime + signal type.

    Returns:
      - strength_adj: Strength adjustment (±points)
      - threshold: Min strength to show signal
      - hold_days: Recommended hold period (days)
    """
    params = {
        "strong_bull": {
            "BUY1": {"strength_adj": 10, "threshold": 40, "hold_days": 20},
            "BUY2": {"strength_adj": 0,  "threshold": 50, "hold_days": 10},
            "BUY3": {"strength_adj": -12, "threshold": 100, "hold_days": 0},
        },
        "bull": {
            "BUY1": {"strength_adj": 5,  "threshold": 55, "hold_days": 20},
            "BUY2": {"strength_adj": 2,  "threshold": 48, "hold_days": 12},
            "BUY3": {"strength_adj": -6, "threshold": 85, "hold_days": 5},
        },
        "recovery": {
            "BUY1": {"strength_adj": 0,  "threshold": 65, "hold_days": 15},
            "BUY2": {"strength_adj": 4,  "threshold": 46, "hold_days": 15},
            "BUY3": {"strength_adj": -2, "threshold": 70, "hold_days": 10},
        },
        "ranging": {
            "BUY1": {"strength_adj": -8, "threshold": 80, "hold_days": 10},
            "BUY2": {"strength_adj": 6,  "threshold": 44, "hold_days": 18},
            "BUY3": {"strength_adj": 2,  "threshold": 55, "hold_days": 15},
        },
        "bear_risk": {
            "BUY1": {"strength_adj": -10, "threshold": 90, "hold_days": 5},
            "BUY2": {"strength_adj": 6,   "threshold": 42, "hold_days": 20},
            "BUY3": {"strength_adj": 10,  "threshold": 40, "hold_days": 20},
        },
    }
    return params.get(regime_label, {}).get(signal_type, {"strength_adj": 0, "threshold": 60, "hold_days": 15})

def score_buy1_strength(d: pd.DataFrame, meta: dict, regime_label: str = "recovery", regime_score_norm: float = 0.5) -> dict:
    """
    BUY1 Strength with AgentQ Regime Matrix.

    regime_label: strong_bull|bull|recovery|ranging|bear_risk
    regime_score_norm: 0.0-1.0 (for backward compat)

    Uses matrix from get_signal_parameters() for adaptive adjustment.
    """
    L = d.iloc[-1]
    comp = {
        "Trend": 20 * _linear(L["trend"], 0, 25),
        "ADX": 12 * _linear(L["adx14"], 13, 25),
        "EMA9 break": 10 * _linear((L["close"]-L["ema9"])/L["ema9"]*100, 0, 4),
        "Kumo": 8 * _linear((L["close"]-L["kumo_a"])/L["kumo_a"]*100, 0, 6),
        "RSI": 8 * _tri_ideal(L["rsi14"], 55, 20),
        "MFI": 7 * _tri_ideal(L["mfi14"], 52.5, 17.5)
    }
    pnl = {
        "Overheat": 12 if L["rsi_superoverbought"] else (6 + 6 * _linear(L["rsi14"], 70, 80) if L["rsi14"] > 70 else 0),
        "Div": min((6 if L["rsi_bear_div"] else 0) + (6 if L["mfi_bear_div"] else 0), 10),
        "Fatigue": 10 if L["is_fatigue"] else 0,
        "ST Bear": 0 if meta.get("bearish_switch_not_recent") else 8,
        "KQ": 6 if meta.get("kqrsimf") else 0
    }

    # Get adaptive parameters from matrix
    params = get_signal_parameters(regime_label, "BUY1")
    regime_boost = params["strength_adj"]

    strength = int(round(_clip(45 + sum(comp.values()) - sum(pnl.values()) + regime_boost)))
    return {"strength": strength, "reasons": _top_reasons(comp, pnl), "hold_days": params["hold_days"]}

def score_buy2_strength(d: pd.DataFrame, regime_label: str = "recovery", regime_score_norm: float = 0.5) -> dict:
    """
    BUY2 Strength (Oversold Recovery) with AgentQ Regime Matrix.

    In weak regimes (ranging/risk/bear), BUY2 becomes MORE attractive (mean reversion).
    In strong trends, BUY2 is less relevant (already in BUY1).
    """
    L = d.iloc[-1]
    comp = {
        "Break": 18 * _linear(max(0, (L["lowest_close_26"]-L["close"])/L["lowest_close_26"]*100), 0, 3),
        "RSI Div": 18 * _linear(max(0, L["rsi14"]-L["lowest_rsi14_26"]), 0, 10),
        "RSI2 OS": 12 * _linear(20-L["rsi2"], 0, 15),
        "RSI14 Pocket": 10 * _tri_ideal(L["rsi14"], 26, 10),
        "MFI Pocket": 7 * _tri_ideal(L["mfi14"], 26.5, 8.5)
    }
    pnl = {
        "Knife": 12 * _linear(-L["trend"], 0, 10) if L["trend"] < 0 else 0,
        "RSI14 High": 8 * _linear(L["rsi14"], 33, 40) if L["rsi14"] > 33 else 0,
        "EMA9 Gap": 7 * _linear((L["ema9"]-L["close"])/L["ema9"]*100, 4, 10)
    }

    # Get adaptive parameters from matrix
    params = get_signal_parameters(regime_label, "BUY2")
    regime_boost = params["strength_adj"]

    strength = int(round(_clip(40 + sum(comp.values()) - sum(pnl.values()) + regime_boost)))
    return {"strength": strength, "reasons": _top_reasons(comp, pnl), "hold_days": params["hold_days"]}

def score_buy3_strength(d: pd.DataFrame, regime_label: str = "recovery", regime_score_norm: float = 0.5) -> dict:
    """
    BUY3 Strength (Extreme Panic Reversal) with AgentQ Regime Matrix.

    BUY3 is ONLY attractive when market is panicking (capitulation reversal).
    """
    L = d.iloc[-1]
    comp = {
        "RSI2 Ex": 25 * _linear(4-L["rsi2"], 0, 4),
        "RSI14 Dep": 20 * _linear(25-L["rsi14"], 0, 15),
        "MFI Wash": 15 * _linear(20-L["mfi14"], 0, 15)
    }
    pnl = {
        "Downtrend": 18 * _linear(-L["trend"], 0, 15) if L["trend"] < 0 else 0,
        "EMA9 Gap": 15 * _linear((L["ema9"]-L["close"])/L["ema9"]*100, 6, 15)
    }

    # Get adaptive parameters from matrix
    params = get_signal_parameters(regime_label, "BUY3")
    regime_boost = params["strength_adj"]

    strength = int(round(_clip(35 + sum(comp.values()) - sum(pnl.values()) + regime_boost)))
    return {"strength": strength, "reasons": _top_reasons(comp, pnl), "hold_days": params["hold_days"]}

def get_strength_icon(score: int) -> str:
    if score >= 75: return "🔥"
    if score >= 60: return "🟢"
    if score >= 45: return "🟡"
    return "⚪"

# =========================
# DISCORD & OUTPUT
# =========================
def send_discord(message: str):
    if not DISCORD_WEBHOOK_URL or "discord.com/api/webhooks" not in DISCORD_WEBHOOK_URL:
        return
    for part in [message[i:i+2000] for i in range(0, len(message), 2000)]:
        try: requests.post(DISCORD_WEBHOOK_URL, json={"content": part}, timeout=20)
        except Exception: pass

def export_signal_json(date_str: str, results: list, regime: dict) -> Path | None:
    """
    Lưu kết quả signal ra file JSON trong web/signals/YYYY-MM-DD.json
    để website AgentQ.Daily đọc.
    """
    if not WEB_EXPORT_ENABLED:
        return None

    WEB_SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = WEB_SIGNALS_DIR / f"{date_str}.json"

    payload = {
        "date":         date_str,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regime": {
            "ok":     regime.get("ok"),
            "adx":    regime.get("adx"),
            "roc5":   regime.get("roc5"),
            "dd20":   regime.get("dd20"),
            "detail": regime.get("detail", ""),
        },
        "signals": [
            {
                "symbol":      r["symbol"],
                "signal_type": r["signal_type"],
                "entry_price": r["entry_price"],
                "strength":    r["strength"],
                "reasons":     r["reasons"],
                "hold_days":   r.get("hold_days", 15),  # Regime-aware hold period
            }
            for r in sorted(results, key=lambda x: (x["signal_type"], -x["strength"]))
        ],
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"📁 Signal saved: {out_path.name}")

    # Cập nhật data.json — 1 file duy nhất chứa toàn bộ lịch sử
    # Website chỉ fetch file này, không cần manifest + nhiều file riêng lẻ
    data_path = WEB_REPO_DIR / "data.json"
    all_data = {}
    if data_path.exists():
        try:
            all_data = json.loads(data_path.read_text())
        except Exception:
            all_data = {}
    all_data[date_str] = payload
    # Chỉ giữ 90 ngày gần nhất
    dates_sorted = sorted(all_data.keys(), reverse=True)[:90]
    all_data = {d: all_data[d] for d in dates_sorted}
    data_path.write_text(json.dumps(all_data, ensure_ascii=False, separators=(",", ":")))

    return out_path


def push_web_to_github(date_str: str) -> bool:
    """
    Commit và push signals vào repo PUBLIC agentq-daily để website cập nhật.
    Repo code (vnstock_xno_prod) vẫn giữ private.
    """
    if not WEB_REPO_DIR.exists():
        print(f"⚠️ Web repo không tìm thấy: {WEB_REPO_DIR}")
        return False
    try:
        # Kiểm tra git repo
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=WEB_REPO_DIR, capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"⚠️ {WEB_REPO_DIR} không phải git repo")
            return False

        # Stage data.json (file duy nhất chứa toàn bộ lịch sử)
        subprocess.run(
            ["git", "add", "data.json"],
            cwd=WEB_REPO_DIR, capture_output=True
        )

        # Commit
        commit = subprocess.run(
            ["git", "commit", "-m", f"signal: {date_str}"],
            cwd=WEB_REPO_DIR, capture_output=True, text=True
        )
        if "nothing to commit" in (commit.stdout + commit.stderr):
            print("📁 No changes to push")
            return True

        # Push lên GitHub Pages repo
        push = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=WEB_REPO_DIR, capture_output=True, text=True
        )
        if push.returncode == 0:
            github_user = os.getenv("GITHUB_USER", "kienquyen")
            print(f"🌐 Website updated → https://{github_user}.github.io/agentq-daily/")
            return True
        else:
            print(f"⚠️ Git push failed: {push.stderr[:200]}")
            return False
    except Exception as e:
        print(f"⚠️ Git push error: {e}")
        return False


def run_screener_latest(run_date: pd.Timestamp | None = None, use_local: bool = False):
    if run_date is None: run_date = pd.Timestamp.today().normalize()
    date_str = run_date.strftime("%Y-%m-%d")
    print(f"📊 Running screener for {date_str}")

    idx_val = get_vnindex_latest()
    print(f"VNIndex: {idx_val if idx_val else 'N/A'}")

    # ── Regime check ──────────────────────────────────────────────────────────
    data_map = fetch_top_vn100_data(use_local=use_local, as_of_date=date_str)
    regime = get_vnindex_regime(as_of_date=run_date, universe_data=data_map)
    print(regime["detail"])
    # Khi regime xấu: nâng ngưỡng strength tối thiểu lên 75 (chỉ lấy signal mạnh)
    buy1_min_strength = 75 if not regime["ok"] else 60
    results = []

    for sym, data in data_map.items():
        try:
            df = data["df"].copy()
            df["time"] = pd.to_datetime(df["time"])
            df = df[df["time"] <= run_date].copy()
            if len(df) < 60: continue

            feat, meta = build_features(df)
            price = float(feat.iloc[-1]["close"])
            is_price_in_k = price < 1000
            actual_price = price * 1000.0 if is_price_in_k else price

            if actual_price < 10000: continue  # Skip if < 10k VND

            entry = price / 1000.0 if not is_price_in_k else price

            for b_func, s_func, label in [
                (is_buy1_signal, score_buy1_strength, "BUY1"),
                (is_buy2_signal, score_buy2_strength, "BUY2"),
                (is_buy3_signal, score_buy3_strength, "BUY3")
            ]:
                if (b_func(feat, meta) if label == "BUY1" else b_func(feat)):
                    # Pass AgentQ regime_label and regime_score_normalized to scoring functions
                    regime_label = regime.get("regime_label", "recovery")
                    regime_norm = regime.get("regime_score_normalized", 0.5)
                    params = get_signal_parameters(regime_label, label)

                    if label == "BUY1":
                        s = s_func(feat, meta, regime_label, regime_norm)
                    else:
                        s = s_func(feat, regime_label, regime_norm)

                    # Apply threshold filter from matrix
                    if s["strength"] < params["threshold"]:
                        continue
                    # Khi regime xấu: chỉ giữ BUY1 có strength đủ mạnh
                    if label == "BUY1" and s["strength"] < buy1_min_strength:
                        continue
                    results.append({"symbol": sym, "entry_price": round(entry, 1), "signal_type": label,
                                    "strength": s["strength"], "reasons": s["reasons"],
                                    "hold_days": s.get("hold_days", 15),
                                    "is_price_in_k": is_price_in_k})
        except Exception as e:
            print(f"❌ Error {sym}: {e}")

    # ── Format output ──────────────────────────────────────────────────────────
    # AgentQ 4-layer regime scoring is included in regime['detail']
    regime_line = f"📡 {regime['detail']}"

    if results:
        df_res = pd.DataFrame(results).sort_values(by=["signal_type", "strength"], ascending=[True, False])
        unit = "k" if results[0]["is_price_in_k"] else "VND"
        regime_warn = "" if regime["ok"] else f"\n⚠️ Regime xấu — chỉ hiển thị BUY1 strength ≥ {buy1_min_strength}"
        msg = (f"📅 **Signal Date: {date_str}**\n"
               f"{regime_line}{regime_warn}\n"
               f"```\n{'Symbol':<8} {'Price('+unit+')':<10} {'Signal':<6} {'Str':<3}\n" + "-"*45 + "\n")
        for _, r in df_res.iterrows():
            icon = get_strength_icon(r["strength"])
            msg += f"{r['symbol']:<8} {r['entry_price']:<10.1f} {r['signal_type']:<6} {r['strength']:<3} {icon}\n"
        msg += "```"
        for _, r in df_res.sort_values("strength", ascending=False).head(5).iterrows():
            msg += f"\n- {r['symbol']} {r['signal_type']}: {', '.join(r['reasons'])}"
    else:
        msg = f"📅 {date_str}: No BUY signals found today.\n{regime_line}"

    print(msg)
    send_discord(msg)

    # ── Export JSON cho website AgentQ.Daily ──────────────────────────────────
    export_signal_json(date_str, results, regime)
    push_web_to_github(date_str)

def wait_until_next():
    tz = pytz.timezone(LOCAL_TZ)
    now = datetime.now(tz)
    nxt = now.replace(hour=DAILY_RUN_HOUR, minute=DAILY_RUN_MINUTE, second=0, microsecond=0)
    if now >= nxt: nxt += timedelta(days=1)
    wait = int((nxt - now).total_seconds())
    print(f"⏳ Waiting {wait}s until {nxt.strftime('%H:%M')}")
    return wait

if __name__ == "__main__":
    import argparse as _argparse
    _parser = _argparse.ArgumentParser()
    _parser.add_argument("--date", default=None, help="Run date YYYY-MM-DD")
    _parser.add_argument("--use-local", action="store_true", help="Load OHLCV from local parquet store (fast, no API)")
    _args, _ = _parser.parse_known_args()

    if _args.date:
        run_screener_latest(pd.Timestamp(_args.date), use_local=_args.use_local)
    elif os.getenv("RUN_ONCE", "0") == "1":
        run_screener_latest(pd.Timestamp(datetime.now(pytz.timezone(LOCAL_TZ)).date()), use_local=_args.use_local)
    else:
        while True:
            time.sleep(wait_until_next())
            run_screener_latest(pd.Timestamp(datetime.now(pytz.timezone(LOCAL_TZ)).date()))
