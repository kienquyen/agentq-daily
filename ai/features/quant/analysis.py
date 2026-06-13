# features/quant/analysis.py
# Task 1 (Quant) — Single Stock — Decision Engine V2 + Bloomberg-style table + Optional AI independent rating
# NOTE:
# - This is a "single-file" version so you can paste in and run immediately.
# - It does NOT depend on models/task1_models.py, task1/rules.py, task1/compute.py, task1/embed.py (they are embedded here).
# - You only need:
#   1) data.market_data.fetch_history(symbol,start,end) -> pd.Series (close series indexed by date/time)
#   2) data.market_data.fetch_vnindex(start,end) -> pd.Series
#   3) config.py must provide: RF_ANNUAL, TASK1_AI_ENABLED, AI_TIMEOUT_SEC, DEBUG_AI (optional), GEMINI_API_KEY/GEMINI_MODEL (optional)
#
# If your config fields differ, adjust "CONFIG IMPORT" section below.

from __future__ import annotations

import os
import re
import json
import math
import time
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional, Callable, Literal

from matplotlib import ticker
from features.industry.sector_library import (
    get_sector_info,
)  # <-- your existing industry map adapter

import numpy as np
import pandas as pd
import discord

# =========================
# CONFIG IMPORT (adjust if needed)
# =========================
try:
    from config import settings as _cfg
except Exception:
    _cfg = None  # type: ignore

RF_ANNUAL = float(getattr(_cfg, "RF_ANNUAL", 0.07))
TASK1_AI_ENABLED = bool(
    str(getattr(_cfg, "TASK1_AI_ENABLED", "1")).strip().lower()
    in ("1", "true", "yes", "on")
)
AI_TIMEOUT_SEC = int(getattr(_cfg, "AI_TIMEOUT_SEC", 60))
DEBUG_AI = bool(
    str(getattr(_cfg, "DEBUG_AI", "0")).strip().lower() in ("1", "true", "yes", "on")
)

GEMINI_API_KEY = str(
    getattr(_cfg, "GEMINI_API_KEY", "")
    or os.getenv("GEMINI_API_KEY", "")
    or os.getenv("GOOGLE_API_KEY", "")
).strip()
GEMINI_MODEL = (
    str(getattr(_cfg, "GEMINI_MODEL", "") or os.getenv("GEMINI_MODEL", "")).strip()
    or "gemini-1.5-flash"
)

# =========================
# MARKET DATA ADAPTER (must exist in your project)
# =========================
# Expected:
#   fetch_history(symbol, start, end) -> pd.Series (close), index datetime
#   fetch_vnindex(start, end) -> pd.Series (close), index datetime
from infrastructure.external.market_data import (
    fetch_history,
    fetch_vnindex,
)  # <-- your existing adapter
from features.ai.gemini import (
    GeminiService,
)  # hoặc đúng path bạn đang đặt file googleai.py
from features.quant.signal_engine import classify_signals, calc_dynamic_stop
from app.vnstock_core.core import fetch_ohlcv as _fetch_ohlcv_raw


# =========================
# DEBUG helper
# =========================
def _dbg(*args):
    if DEBUG_AI:
        print(*args)


def color_for_action(action: str) -> discord.Colour:
    return {
        "BUY": discord.Colour.green(),
        "WAIT": discord.Colour.gold(),
        "AVOID": discord.Colour.red(),
    }.get(action, discord.Colour.light_grey())


# =========================
# RULES (as you provided)
# =========================
AssetRole = Literal["CORE", "TACTICAL", "DEFENSIVE", "VOL_AMPLIFIER", "SPECULATIVE"]
ActionST = Literal["BUY", "WAIT", "AVOID"]


@dataclass
class RoleThresholds:
    sharpe_core: float = 0.80
    sharpe_ok: float = 0.50

    alpha_core: float = 0.00
    alpha_bad: float = 0.00

    beta_defensive_max: float = 0.90
    beta_volamp_min: float = 1.20

    beta_dn_defensive_max: float = 0.80
    beta_dn_ok_max: float = 1.2
    beta_dn_bad_min: float = 1.3

    corr_low_max: float = 0.35
    corr_high_min: float = 0.70

    vol_multiplier_high: float = 1.5


@dataclass
class ActionThresholds:
    require_above_ma50_for_buy: bool = True

    excess_ret_3m_buy_min: float = 0.00
    excess_ret_3m_avoid_max: float = -0.02

    corr_shift_down_avoid: float = -0.20

    beta6_buy_min: float = 0.60
    beta6_avoid_max: float = 0.20

    vol_spike_ratio_avoid: float = 1.50


@dataclass
class NarrativeText:
    # task1/rules.py (trong NarrativeText)
    role_name_vi: Dict[str, str] = field(
        default_factory=lambda: {
            "CORE": "🟩 CORE (Trụ cột)",
            "TACTICAL": "🟨 TACTICAL (Theo chu kỳ)",
            "DEFENSIVE": "🟦 DEFENSIVE (Phòng thủ)",
            "VOL_AMPLIFIER": "🟪 VOL AMPLIFIER (Khuếch đại biến động)",
            "SPECULATIVE": "🟥 SPECULATIVE (Đầu cơ)",
        }
    )

    # task1/rules.py (trong NarrativeText)
    # task1/rules.py (NarrativeText)
    action_name_vi: Dict[str, str] = field(
        default_factory=lambda: {
            "BUY": "🛒 MUA (có thể giải ngân)",
            "WAIT": "⏳ CHỜ (đợi xác nhận)",
            "AVOID": "⛔ TRÁNH (không mua lúc này)",
        }
    )

    role_one_liner: Dict[str, str] = field(
        default_factory=lambda: {
            "CORE": "Phù hợp làm trụ cột danh mục nếu bạn ưu tiên chất lượng lợi nhuận và độ bền rủi ro.",
            "TACTICAL": "Phù hợp đánh theo nhịp/chu kỳ; ưu tiên timing hơn là nắm giữ dài hạn.",
            "DEFENSIVE": "Phù hợp giảm drawdown; thường giữ tốt hơn khi thị trường xấu.",
            "VOL_AMPLIFIER": "Chỉ buy khi uptrend, giảm mạnh khi TT đảo chiều",
            "SPECULATIVE": "Không phù hợp portfolio core; chỉ trade ngắn hạn",
        }
    )

    action_one_liner: Dict[str, str] = field(
        default_factory=lambda: {
            "BUY": "Ngắn hạn đang có xác nhận: giá/nhịp và tương quan thị trường ủng hộ giải ngân.",
            "WAIT": "Timing chưa đẹp; ưu tiên chờ xác nhận.",
            "AVOID": "Ngắn hạn bất lợi (decouple/vol spike/trend gãy); tránh mở vị thế mới.",
        }
    )


@dataclass
class Task1V2RuleConfig:
    role: RoleThresholds = field(default_factory=RoleThresholds)
    action: ActionThresholds = field(default_factory=ActionThresholds)
    text: NarrativeText = field(default_factory=NarrativeText)


# =========================
# MODELS (updated to include Return6M, Sharpe12M, Alpha24M + table sections)
# =========================
@dataclass
class Task1MetricsV2:
    # RETURN
    ann_ret_24m: float
    ret_6m: float
    ret_1m: float

    # SHARPE
    sharpe_24m: float
    sharpe_12m: float

    # ALPHA
    alpha_36m: float
    alpha_24m: float

    # BETA
    beta_12m: float
    beta_up_12m: float
    beta_dn_12m: float
    convexity_12m: float
    beta_6m: float

    # CORR
    corr_24m: float
    corr_6m: float
    corr_shift: float

    # short-horizon context for rules
    ret_3m: float
    vni_ret_3m: float
    excess_ret_3m: float

    vol_1m: float
    vol_6m: float
    vol_spike_ratio: float

    ma20: float
    ma50: float
    last_close: float
    above_ma50: bool

    # bench long horizon
    bench_ret_24m: float
    bench_vol_24m: float
    bench_sharpe_24m: float

    # extra
    ann_vol_24m: float
    meta: Dict[str, Any]
    # additional metrics
    vni_ret_6m: float
    vni_ret_1m: float
    bench_sharpe_12m: float

    vol_1m: float
    vol_6m: float
    vol_spike_ratio: float

    # NEW: VNI volatility regime (to compare)
    vni_vol_1m: float
    vni_vol_6m: float
    vni_vol_spike_ratio: float

    # NEW: Enhanced metrics
    sortino_24m: float
    max_drawdown_24m: float
    calmar_24m: float
    momentum_score: float
    trailing_stop_pct: float
    regime_state: str

    # NEW: Red flag metrics
    trailing_stop_is_capped: bool = False
    high_52w: float = float("nan")
    monthly_vol_24m: float = float("nan")


@dataclass
class Task1DecisionV2:
    role: AssetRole
    action: ActionST
    role_notes: List[str]
    action_notes: List[str]
    risk_triggers: List[str]          # hard flags → chặn signal trong screener
    warn_triggers: List[str]          # soft warnings → chỉ cảnh báo, không chặn
    role_confidence: float = 0.0
    action_confidence: float = 0.0
    signals: Optional[Dict[str, Any]] = None
    stop_data: Optional[Dict[str, Any]] = None
    size_note: str = ""


# =========================
# COMPUTE (Decision Engine V2)
# =========================
TRADING_DAYS = 252


def to_returns(px: pd.Series) -> pd.Series:
    return px.pct_change().dropna()


def ann_return(r: pd.Series) -> float:
    if r.empty:
        return np.nan
    eq = (1 + r).cumprod()
    return float(eq.iloc[-1] ** (TRADING_DAYS / len(r)) - 1)


def ann_vol(r: pd.Series) -> float:
    if r.empty:
        return np.nan
    return float(r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def sharpe(r: pd.Series, rf_annual: float) -> float:
    if r.empty:
        return np.nan
    rf_daily = (1 + rf_annual) ** (1 / TRADING_DAYS) - 1
    ex = r - rf_daily
    d = ex.std(ddof=1)
    if not np.isfinite(d) or d == 0:
        return np.nan
    return float((ex.mean() / d) * math.sqrt(TRADING_DAYS))


def sortino(r: pd.Series, rf_annual: float) -> float:
    if r.empty or len(r) < 20:
        return np.nan
    rf_daily = (1 + rf_annual) ** (1 / TRADING_DAYS) - 1
    ex = r - rf_daily
    downside = ex[ex < 0]
    if len(downside) < 5:
        return np.nan
    d = downside.std(ddof=1)
    if not np.isfinite(d) or d == 0:
        return np.nan
    return float((ex.mean() / d) * math.sqrt(TRADING_DAYS))


def max_drawdown(r: pd.Series) -> float:
    if r.empty or len(r) < 5:
        return np.nan
    eq = (1 + r).cumprod()
    peak = eq.cummax()
    dd = (eq - peak) / peak
    return float(dd.min())


def calmar(r: pd.Series) -> float:
    if r.empty or len(r) < 60:
        return np.nan
    ann_ret = ann_return(r)
    mdd = max_drawdown(r)
    if not np.isfinite(mdd) or mdd == 0:
        return np.nan
    return float(ann_ret / abs(mdd))


def momentum_score(m: Task1MetricsV2) -> float:
    score = 0.0
    weights = 0.0

    # Return vs benchmark (6M, 3M, 1M) — 30%
    for ret, bench_ret, w in [
        (m.ret_6m, m.vni_ret_6m, 0.10),
        (m.ret_3m, m.vni_ret_3m, 0.12),
        (m.ret_1m, m.vni_ret_1m, 0.08),
    ]:
        if np.isfinite(ret) and np.isfinite(bench_ret):
            excess = ret - bench_ret
            score += _score_contrib(excess, -0.20, 0.20) * w
            weights += w

    # Sharpe quality — 25%
    if np.isfinite(m.sharpe_24m):
        score += _score_contrib(m.sharpe_24m, -1.0, 2.0) * 0.25
        weights += 0.25

    # Trend (MA) — 20%
    if np.isfinite(m.last_close) and np.isfinite(m.ma50):
        ma_ratio = m.last_close / m.ma50 - 1
        score += _score_contrib(ma_ratio, -0.30, 0.30) * 0.20
        weights += 0.20
    if np.isfinite(m.last_close) and np.isfinite(m.ma20):
        ma20_ratio = m.last_close / m.ma20 - 1
        score += _score_contrib(ma20_ratio, -0.20, 0.20) * 0.10
        weights += 0.10

    # Relative strength (3M) — 15%
    if np.isfinite(m.excess_ret_3m):
        score += _score_contrib(m.excess_ret_3m, -0.30, 0.30) * 0.15
        weights += 0.15

    if weights == 0:
        return np.nan
    raw = score / weights
    return float(max(0.0, min(100.0, raw * 100)))


def _score_contrib(value: float, lo: float, hi: float) -> float:
    norm = (value - lo) / (hi - lo)
    return float(max(0.0, min(1.0, norm)))


def trailing_stop_metrics(sr24, rf_annual, ann_vol_s) -> Tuple[float, bool]:
    """Returns (stop_pct, is_capped). is_capped=True when true ATR-based stop exceeds cap."""
    vol_6m = ann_vol(sr24.iloc[-126:]) if len(sr24) >= 126 else np.nan
    if np.isfinite(vol_6m):
        atr_pct = vol_6m * 1.5
        capped = atr_pct > 0.25
        return float(min(atr_pct, 0.25)), capped
    elif np.isfinite(ann_vol_s):
        atr_pct = ann_vol_s * 1.0
        capped = atr_pct > 0.20
        return float(min(atr_pct, 0.20)), capped
    return 0.15, False


def detect_regime(bench_ret_24m: float, bench_vol_24m: float) -> str:
    if np.isfinite(bench_ret_24m):
        if bench_ret_24m > 0.15:
            return "Bull"
        elif bench_ret_24m < -0.05:
            return "Bear"
    return "Neutral"


# =========================
# RED FLAG DETECTION FUNCTIONS
# =========================

def detect_momentum_concentration(m: "Task1MetricsV2") -> Optional[str]:
    """Flag 8: 1M return chiếm >65% của 3M return → blow-off burst."""
    if not (np.isfinite(m.ret_1m) and np.isfinite(m.ret_3m)):
        return None
    if m.ret_3m <= 0.02:
        return None
    concentration = m.ret_1m / m.ret_3m
    if concentration > 0.65 and m.ret_1m > 0.10:
        return (
            f"Momentum tập trung: {m.ret_1m*100:.0f}% trong 1M chiếm "
            f"{concentration*100:.0f}% đà 3M — rủi ro hồi kỹ thuật tăng cao."
        )
    return None


def detect_zscore_ret1m(m: "Task1MetricsV2") -> Optional[str]:
    """Flag 3: Ret 1M là outlier thống kê (Z > 2.0σ dựa trên vol 24M)."""
    if not (np.isfinite(m.ret_1m) and np.isfinite(m.monthly_vol_24m)):
        return None
    if m.monthly_vol_24m <= 0:
        return None
    zscore = m.ret_1m / m.monthly_vol_24m
    if zscore > 2.5:
        return (
            f"Z-score Ret 1M = {zscore:.1f}σ (>{m.ret_1m*100:.0f}%): "
            f"sự kiện thống kê cực hiếm — xác suất hồi kỹ thuật rất cao."
        )
    if zscore > 2.0:
        return (
            f"Z-score Ret 1M = {zscore:.1f}σ ({m.ret_1m*100:.0f}%): "
            f"tăng bất thường so với vol lịch sử — cẩn trọng với đà tiếp diễn."
        )
    return None


def detect_vol_spike_uptrend(m: "Task1MetricsV2") -> Optional[str]:
    """Flag 4: Vol spike trong bối cảnh giá tăng mạnh → exhaustion buying."""
    if not (np.isfinite(m.vol_spike_ratio) and np.isfinite(m.ret_1m)):
        return None
    if m.vol_spike_ratio >= 1.30 and m.ret_1m > 0.15:
        return (
            f"Vol spike {m.vol_spike_ratio:.2f}x trong uptrend mạnh "
            f"({m.ret_1m*100:.0f}% 1M) → dấu hiệu mua kiệt sức (exhaustion buying)."
        )
    return None


def detect_near_52w_high(m: "Task1MetricsV2") -> Optional[str]:
    """Flag 6: Giá tiếp cận đỉnh 52W trong bối cảnh vol spike → vùng kháng cự nguy hiểm."""
    if not (np.isfinite(m.high_52w) and np.isfinite(m.last_close) and np.isfinite(m.vol_spike_ratio)):
        return None
    if m.high_52w <= 0:
        return None
    proximity = m.last_close / m.high_52w
    if proximity >= 0.97 and m.vol_spike_ratio >= 1.20 and m.ret_1m > 0.08:
        return (
            f"Giá ({m.last_close:.2f}) tiếp cận đỉnh 52W ({m.high_52w:.2f}, "
            f"cách {(1-proximity)*100:.1f}%) với vol spike {m.vol_spike_ratio:.2f}x "
            f"→ vùng kháng cự lịch sử — rủi ro bị chặn/đảo chiều."
        )
    return None


def reg_alpha_beta(sr: pd.Series, br: pd.Series) -> Tuple[float, float]:
    df = pd.concat([sr.rename("s"), br.rename("b")], axis=1).dropna()
    if df.shape[0] < 60:
        return np.nan, np.nan
    s = df["s"].values
    b = df["b"].values
    var_b = np.var(b)
    if var_b <= 0:
        return np.nan, np.nan
    cov = np.mean((s - s.mean()) * (b - b.mean()))
    beta = cov / var_b
    alpha = s.mean() - beta * b.mean()
    return float(alpha), float(beta)


def annualize_alpha(alpha_daily: float) -> float:
    if alpha_daily is None or not np.isfinite(alpha_daily):
        return np.nan
    return float((1 + alpha_daily) ** TRADING_DAYS - 1)


def corr(sr: pd.Series, br: pd.Series) -> float:
    df = pd.concat([sr.rename("s"), br.rename("b")], axis=1).dropna()
    if df.shape[0] < 60:
        return np.nan
    return float(df["s"].corr(df["b"]))


def upside_downside_beta(sr: pd.Series, br: pd.Series) -> Tuple[float, float]:
    df = pd.concat([sr.rename("s"), br.rename("b")], axis=1).dropna()
    if df.shape[0] < 60:
        return np.nan, np.nan

    def _beta(sub: pd.DataFrame) -> float:
        if sub.shape[0] < 30:
            return np.nan
        s = sub["s"].values
        b = sub["b"].values
        var_b = np.var(b)
        if var_b <= 0:
            return np.nan
        cov = np.mean((s - s.mean()) * (b - b.mean()))
        return float(cov / var_b)

    beta_up = _beta(df[df["b"] > 0])
    beta_dn = _beta(df[df["b"] < 0])
    return beta_up, beta_dn


def window_slice(px: pd.Series, days: int) -> pd.Series:
    if px.empty:
        return px
    return px.iloc[-days:] if len(px) >= days else px


def ma(px: pd.Series, n: int) -> float:
    if px.empty:
        return np.nan
    return float(px.rolling(n).mean().iloc[-1])


def simple_return(px: pd.Series) -> float:
    if px is None or px.empty or len(px) < 2:
        return np.nan
    return float(px.iloc[-1] / px.iloc[0] - 1)


def classify_role(
    m: Task1MetricsV2, cfg: Task1V2RuleConfig
) -> Tuple[AssetRole, List[str], float]:
    T = cfg.role
    notes: List[str] = []

    vol_high = (
        np.isfinite(m.ann_vol_24m)
        and np.isfinite(m.bench_vol_24m)
        and (m.ann_vol_24m > m.bench_vol_24m * T.vol_multiplier_high)
    )
    corr_high = np.isfinite(m.corr_24m) and (m.corr_24m >= T.corr_high_min)
    corr_low = np.isfinite(m.corr_24m) and (m.corr_24m <= T.corr_low_max)

    # Compute role scores
    scores = _compute_role_scores(m, cfg, vol_high, corr_high, corr_low)
    best_role = max(scores, key=lambda k: scores[k]["score"])
    best = scores[best_role]
    confidence = best["score"]

    # Map to role + notes
    role, notes = _build_role_result(best_role, m, cfg, vol_high, corr_low)

    return role, notes, confidence


def _compute_role_scores(
    m: Task1MetricsV2,
    cfg: Task1V2RuleConfig,
    vol_high: bool,
    corr_high: bool,
    corr_low: bool,
) -> Dict[str, Dict[str, float]]:
    T = cfg.role
    scores: Dict[str, Dict[str, float]] = {}

    # === SPECULATIVE score ===
    spec_score = 0.0
    spec_w = 0.0
    if np.isfinite(m.sharpe_24m):
        if m.sharpe_24m < T.sharpe_ok:
            spec_score += (T.sharpe_ok - m.sharpe_24m) / T.sharpe_ok * 0.40
        else:
            spec_score -= 0.20
        spec_w += 0.40
    if np.isfinite(m.alpha_24m) and np.isfinite(m.beta_dn_12m):
        if m.alpha_24m < T.alpha_bad and m.beta_dn_12m >= T.beta_dn_bad_min:
            spec_score += 0.35
        spec_w += 0.35
    if vol_high:
        spec_score += 0.15
        spec_w += 0.15
    if np.isfinite(m.max_drawdown_24m) and m.max_drawdown_24m < -0.30:
        spec_score += 0.10
        spec_w += 0.10
    scores["SPECULATIVE"] = {"score": min(spec_score, 1.0), "w": spec_w}

    # === DEFENSIVE score ===
    def_score = 0.0
    def_w = 0.0
    if np.isfinite(m.beta_12m) and m.beta_12m <= T.beta_defensive_max:
        def_score += (T.beta_defensive_max - m.beta_12m) / T.beta_defensive_max * 0.30
        def_w += 0.30
    if np.isfinite(m.beta_dn_12m) and m.beta_dn_12m <= T.beta_dn_defensive_max:
        def_score += (
            (T.beta_dn_defensive_max - m.beta_dn_12m) / T.beta_dn_defensive_max * 0.30
        )
        def_w += 0.30
    if not vol_high:
        def_score += 0.25
        def_w += 0.25
    if corr_low:
        def_score += 0.15
        def_w += 0.15
    scores["DEFENSIVE"] = {"score": min(def_score, 1.0), "w": def_w}

    # === VOL AMPLIFIER score ===
    vol_score = 0.0
    vol_w = 0.0
    if np.isfinite(m.beta_12m) and m.beta_12m >= T.beta_volamp_min:
        vol_score += (m.beta_12m - T.beta_volamp_min) / T.beta_volamp_min * 0.25
        vol_w += 0.25
    if vol_high:
        vol_score += 0.35
        vol_w += 0.35
    if corr_high:
        vol_score += 0.25
        vol_w += 0.25
    if np.isfinite(m.beta_dn_12m) and m.beta_dn_12m > T.beta_dn_ok_max:
        vol_score += 0.15
        vol_w += 0.15
    scores["VOL_AMPLIFIER"] = {"score": min(vol_score, 1.0), "w": vol_w}

    # Hard gate: β ≥ 1.2 AND vol > 1.5× market → VOL_AMP wins regardless of TACTICAL baseline
    # TACTICAL max ≈ 0.75 (base 0.30 + vol 0.20 + corr 0.25), so gate must be > 0.75
    if (np.isfinite(m.beta_12m) and m.beta_12m >= T.beta_volamp_min and vol_high):
        scores["VOL_AMPLIFIER"]["score"] = max(scores["VOL_AMPLIFIER"]["score"], 0.82)

    # === CORE score ===
    core_score = 0.0
    core_w = 0.0
    if np.isfinite(m.sharpe_24m):
        if m.sharpe_24m >= T.sharpe_core:
            core_score += (m.sharpe_24m - T.sharpe_core) / T.sharpe_core * 0.25
            core_w += 0.25
        else:
            core_score -= 0.10
            core_w += 0.25
    alpha_ok = (np.isfinite(m.alpha_36m) and m.alpha_36m >= T.alpha_core) or (
        np.isfinite(m.alpha_24m) and m.alpha_24m >= T.alpha_core
    )
    if alpha_ok:
        core_score += 0.30
        core_w += 0.30
    if np.isfinite(m.beta_dn_12m) and m.beta_dn_12m <= T.beta_dn_ok_max:
        core_score += (T.beta_dn_ok_max - m.beta_dn_12m) / T.beta_dn_ok_max * 0.20
        core_w += 0.20
    if not vol_high:
        core_score += 0.15
        core_w += 0.15
    if np.isfinite(m.calmar_24m) and m.calmar_24m > 0.5:
        core_score += 0.10
        core_w += 0.10
    scores["CORE"] = {"score": max(core_score, 0.0), "w": core_w}

    # === TACTICAL score ===
    tac_score = 0.30
    if vol_high:
        tac_score += 0.20
    if np.isfinite(m.corr_24m) and 0.35 <= m.corr_24m <= 0.70:
        tac_score += 0.25
    if np.isfinite(m.sharpe_24m) and 0.20 <= m.sharpe_24m < T.sharpe_core:
        tac_score += 0.25
    scores["TACTICAL"] = {"score": min(tac_score, 1.0), "w": 1.0}

    return scores


def _build_role_result(
    role: str, m: Task1MetricsV2, cfg: Task1V2RuleConfig, vol_high: bool, corr_low: bool
) -> Tuple[str, List[str]]:
    T = cfg.role
    notes: List[str] = []

    if role == "SPECULATIVE":
        notes.append("Chất lượng lợi nhuận/alpha không đủ tốt để giữ dài hạn.")
        if vol_high:
            notes.append("Biến động cao hơn thị trường.")
        if np.isfinite(m.max_drawdown_24m) and m.max_drawdown_24m < -0.25:
            notes.append(f"Drawdown lớn: {m.max_drawdown_24m * 100:.0f}% → rủi ro cao.")
        if np.isfinite(m.sharpe_24m) and m.sharpe_24m < -0.20:
            notes.append("Sharpe âm sâu → hiệu suất điều chỉnh rủi ro kém.")

    elif role == "DEFENSIVE":
        notes.append("Độ nhạy thị trường thấp và downside beta được kiểm soát.")
        if corr_low:
            notes.append("Tương quan thị trường thấp → hỗ trợ giảm drawdown danh mục.")
        if np.isfinite(m.sortino_24m) and m.sortino_24m > 0.5:
            notes.append(f"Sortino {m.sortino_24m:.2f} → downside protection tốt.")

    elif role == "VOL_AMPLIFIER":
        notes.append("Beta cao/biến động cao → khuếch đại hiệu suất khi uptrend.")
        if np.isfinite(m.beta_dn_12m) and m.beta_dn_12m > T.beta_dn_ok_max:
            notes.append(
                f"Downside beta {m.beta_dn_12m:.2f} → giảm mạnh hơn thị trường khi đảo chiều."
            )
        if np.isfinite(m.beta_up_12m) and np.isfinite(m.beta_dn_12m) and m.beta_dn_12m > 0:
            conv_ratio = m.beta_up_12m / m.beta_dn_12m
            if conv_ratio < 1.30:
                notes.append(
                    f"Convexity ratio thấp ({conv_ratio:.2f}x) → amplifies cả 2 hướng gần bằng nhau."
                )
            else:
                notes.append(
                    f"Convexity ratio {conv_ratio:.2f}x → ưu thế upside rõ hơn downside."
                )
        elif np.isfinite(m.ann_vol_24m) and np.isfinite(m.bench_vol_24m):
            rel_vol = m.ann_vol_24m / m.bench_vol_24m
            notes.append(f"Biến động {rel_vol:.1f}x VNI → volatility amplifier.")

    elif role == "CORE":
        notes.append("Chất lượng lợi nhuận tốt và alpha dài hạn dương/không âm.")
        notes.append("Downside beta ổn → phù hợp làm trụ cột danh mục.")
        if np.isfinite(m.calmar_24m) and m.calmar_24m > 0.5:
            notes.append(f"Calmar {m.calmar_24m:.2f} → return/risk tốt.")

    else:  # TACTICAL
        notes.append(
            "Phù hợp vai trò tactical: ưu tiên theo nhịp/chu kỳ hơn là core dài hạn."
        )
        if vol_high:
            notes.append("Biến động cao: cần kỷ luật vị thế.")

    return role, notes[:3]


def decide_action_short_term(
    m: Task1MetricsV2, cfg: Task1V2RuleConfig
) -> Tuple[ActionST, List[str], List[str], List[str], float]:
    """
    Returns: (action, notes, hard_triggers, warn_triggers, confidence)
      hard_triggers → chặn signal trong screener (zscore, vol spike, blow-off...)
      warn_triggers → chỉ cảnh báo, không chặn (MaxDD, Shp12M degradation)
    """
    A = cfg.action
    notes: List[str] = []
    triggers: List[str] = []       # hard flags
    warn_triggers: List[str] = []  # soft warnings
    confidence = 0.50

    # ─── FLAG 3: Z-score Ret 1M > 2.5σ → hard AVOID ───
    zscore_flag = detect_zscore_ret1m(m)
    if zscore_flag and np.isfinite(m.monthly_vol_24m) and m.monthly_vol_24m > 0:
        zscore = m.ret_1m / m.monthly_vol_24m
        if zscore > 2.5:
            severity = min((zscore - 2.5) / 1.0, 1.0)
            confidence = 0.78 + severity * 0.17
            triggers.append(zscore_flag)
            return "AVOID", [
                f"Ret 1M = {m.ret_1m*100:.0f}% là sự kiện {zscore:.1f}σ — xác suất hồi kỹ thuật rất cao.",
            ], triggers, warn_triggers, confidence

    # ─── FLAG 4: Vol spike trong uptrend mạnh → hard AVOID ───
    vol_uptrend_flag = detect_vol_spike_uptrend(m)
    if vol_uptrend_flag:
        severity = min((m.vol_spike_ratio - 1.30) / 0.70, 1.0)
        confidence = 0.72 + severity * 0.18
        triggers.append(vol_uptrend_flag)
        return "AVOID", [
            f"Vol spike {m.vol_spike_ratio:.2f}x khi giá tăng {m.ret_1m*100:.0f}% (1M) — dấu hiệu mua kiệt sức.",
        ], triggers, warn_triggers, confidence

    # ─── FLAG 6: Near 52W high + vol spike → hard AVOID ───
    near_high_flag = detect_near_52w_high(m)
    if near_high_flag:
        confidence = 0.75
        triggers.append(near_high_flag)
        prox = (1 - m.last_close / m.high_52w) * 100 if np.isfinite(m.high_52w) and m.high_52w > 0 else float("nan")
        return "AVOID", [
            f"Giá cách đỉnh 52W {prox:.1f}% + vol spike {m.vol_spike_ratio:.2f}x — kháng cự lịch sử mạnh.",
        ], triggers, warn_triggers, confidence

    # ─── Existing hard avoids ───
    if (
        np.isfinite(m.vol_spike_ratio)
        and np.isfinite(m.vol_6m)
        and m.vol_spike_ratio >= A.vol_spike_ratio_avoid
    ):
        severity = min((m.vol_spike_ratio - 1.50) / 1.00, 1.0)
        confidence = 0.70 + severity * 0.25
        triggers.append(
            f"Vol spike {m.vol_spike_ratio:.2f}x: biến động 1M tăng mạnh → ưu tiên phòng thủ."
        )
        return "AVOID", [
            f"Vol 1M = {m.vol_1m*100:.0f}% so với vol 6M = {m.vol_6m*100:.0f}% (spike {m.vol_spike_ratio:.2f}x) — rủi ro rung lắc.",
        ], triggers, warn_triggers, confidence

    if np.isfinite(m.corr_shift) and m.corr_shift <= A.corr_shift_down_avoid:
        confidence = 0.80
        triggers.append(
            "Correlation shift down: cổ phiếu đang decouple khỏi VNIndex (ngắn hạn)."
        )
        return "AVOID", [
            f"Tương quan giảm từ {m.corr_24m:.2f} (24M) → {m.corr_6m:.2f} (6M), shift = {m.corr_shift:.2f} — cổ phiếu tách khỏi thị trường.",
        ], triggers, warn_triggers, confidence

    if np.isfinite(m.beta_6m) and m.beta_6m <= A.beta6_avoid_max:
        confidence = 0.75
        triggers.append(
            "Beta compression mạnh: beta 6M rất thấp → khó hưởng lợi khi market lên."
        )
        return "AVOID", [
            f"Beta 6M = {m.beta_6m:.2f} — quá thấp để ăn theo thị trường khi tích cực.",
        ], triggers, warn_triggers, confidence

    # ─── FIX 2: MaxDD < -40% → soft warning only, không chặn signal ───
    if np.isfinite(m.max_drawdown_24m) and m.max_drawdown_24m < -0.40:
        warn_triggers.append(
            f"MaxDD 24M = {m.max_drawdown_24m*100:.0f}%: drawdown nghiêm trọng — "
            f"sizing tối đa 50% so với bình thường, trailing stop bắt buộc."
        )

    # ─── Collect warning triggers (Flags 3 warning-level, 8) ───
    if zscore_flag:
        triggers.append(zscore_flag)

    conc_flag = detect_momentum_concentration(m)
    if conc_flag:
        triggers.append(conc_flag)

    # ─── BUY conditions ───
    buy_ok = True
    buy_score = 0.0
    buy_w = 0.0

    # FIX 6: Sharpe 12M degradation → block BUY + soft warning
    if np.isfinite(m.sharpe_12m) and np.isfinite(m.bench_sharpe_12m):
        if (m.bench_sharpe_12m - m.sharpe_12m) >= 0.50:
            buy_ok = False
            _shp_note = (
                f"Sharpe 12M = {m.sharpe_12m:.2f} < VNI {m.bench_sharpe_12m:.2f} — alpha gần đây đang suy giảm."
            )
            notes.append(_shp_note)
            warn_triggers.append(_shp_note)

    # FLAG 8: Momentum concentration → block BUY
    if conc_flag:
        buy_ok = False
        if np.isfinite(m.ret_1m) and np.isfinite(m.ret_3m) and m.ret_3m > 0:
            notes.append(
                f"Ret 1M = {m.ret_1m*100:.0f}% chiếm {m.ret_1m/m.ret_3m*100:.0f}% đà 3M — momentum tập trung, chờ xác nhận."
            )
        else:
            notes.append("Momentum tập trung vào 1 tháng duy nhất — chờ xác nhận tiếp diễn.")

    # Trend check (MA50)
    if A.require_above_ma50_for_buy and (not m.above_ma50):
        buy_ok = False
        notes.append(
            f"Giá {m.last_close:.2f} < MA50 {m.ma50:.2f} — xu hướng chưa xác nhận."
        )
    elif m.above_ma50:
        buy_score += 0.25
        buy_w += 0.25

    # Relative strength 3M — NaN = cannot confirm outperformance → block BUY
    if np.isfinite(m.excess_ret_3m):
        if m.excess_ret_3m < A.excess_ret_3m_buy_min:
            buy_ok = False
            notes.append(
                f"Excess 3M = {m.excess_ret_3m*100:.1f}% — chưa outperform VNIndex ngắn hạn."
            )
        else:
            buy_score += min(m.excess_ret_3m / 0.10, 1.0) * 0.25
            buy_w += 0.25
    else:
        buy_ok = False
        notes.append("Excess 3M: không đủ dữ liệu — chưa xác nhận tương quan VNIndex.")

    # Beta 6M — NaN = cannot assess market sensitivity → block BUY
    if np.isfinite(m.beta_6m):
        if m.beta_6m < A.beta6_buy_min:
            buy_ok = False
            notes.append(
                f"Beta 6M = {m.beta_6m:.2f} < {A.beta6_buy_min:.2f} — lực ăn theo thị trường yếu."
            )
        else:
            buy_score += min(m.beta_6m / 1.0, 1.0) * 0.20
            buy_w += 0.20
    else:
        buy_ok = False
        notes.append("Beta 6M: không đủ dữ liệu — chưa xác nhận beta.")

    # Momentum score bonus — NaN = all inputs missing → block BUY
    if np.isfinite(m.momentum_score):
        if m.momentum_score >= 55:
            buy_score += 0.15
        elif m.momentum_score < 35:
            buy_ok = False
            notes.append(f"Momentum = {m.momentum_score:.0f}/100 — đà quá yếu để giải ngân.")
        buy_w += 0.15
    else:
        buy_ok = False
        notes.append("Momentum score: không đủ dữ liệu để tính — chưa xác nhận.")

    # Sortino bonus
    if np.isfinite(m.sortino_24m) and m.sortino_24m > 0.3:
        buy_score += 0.15
        buy_w += 0.15

    if buy_ok:
        confidence = min(buy_score / max(buy_w, 0.01), 1.0)
        if np.isfinite(m.excess_ret_3m) and m.excess_ret_3m > 0.05 and m.above_ma50:
            confidence = min(confidence + 0.10, 1.0)
        # Build data-driven BUY notes with real numbers
        buy_notes = []
        if m.above_ma50 and np.isfinite(m.last_close) and np.isfinite(m.ma50):
            buy_notes.append(
                f"Giá {m.last_close:.2f} > MA50 {m.ma50:.2f} (+{(m.last_close/m.ma50-1)*100:.0f}%) — uptrend xác nhận."
            )
        if np.isfinite(m.excess_ret_3m) and m.excess_ret_3m >= 0:
            buy_notes.append(
                f"Excess 3M = +{m.excess_ret_3m*100:.1f}% — outperform VNIndex ngắn hạn."
            )
        if np.isfinite(m.beta_6m):
            buy_notes.append(
                f"Beta 6M = {m.beta_6m:.2f} — ăn theo thị trường tốt khi tích cực."
            )
        return "BUY", buy_notes or ["Các điều kiện kỹ thuật đều đạt."], triggers, warn_triggers, confidence

    # WAIT default
    if np.isfinite(m.excess_ret_3m) and m.excess_ret_3m <= A.excess_ret_3m_avoid_max:
        triggers.append(
            f"Excess 3M = {m.excess_ret_3m*100:.1f}% — underperform VNIndex đáng kể, chờ hồi phục tương đối."
        )
        confidence = 0.60
    elif buy_w > 0:
        confidence = min(buy_score / buy_w * 0.8, 0.75)
    else:
        confidence = 0.50
    return (
        "WAIT",
        (notes if notes else [f"Chưa đủ điều kiện giải ngân — timing chưa đẹp."]),
        triggers,
        warn_triggers,
        confidence,
    )


def decide_action_layered(
    m: "Task1MetricsV2",
    signals: Dict[str, Any],
    cfg: Task1V2RuleConfig,
) -> Tuple[ActionST, List[str], List[str], float, str]:
    """
    3-layer decision engine.

    Layer 1 — Regime filter: Bear → CHỜ.
    Layer 2 — Momentum timing: RSI, MACD, Vol, MFI từ signal engine.
      >= 2 tín hiệu tích cực → tiếp tục; ngược lại → CHỜ/TRÁNH.
    Layer 3 — Quality confirm: chỉ điều chỉnh size_note, không block entry.

    Matrix:
      Momentum OK + Quality OK → MUA full size
      Momentum OK + Quality kém → MUA giảm size
      Momentum kém + Quality OK → CHỜ
      Momentum kém + Quality kém → TRÁNH

    Returns: (action, action_notes, risk_triggers, confidence, size_note)
    """
    notes: List[str] = []
    triggers: List[str] = []
    size_note: str = ""

    candle_flags = signals.get("candle_flags", {}) if signals else {}
    mfi = signals.get("mfi") if signals else None
    vol_ratio = signals.get("vol_ratio") if signals else None

    # ── Hard risk overrides ────────────────────────────────────────────────────
    if (
        np.isfinite(m.vol_spike_ratio)
        and np.isfinite(m.vol_6m)
        and m.vol_spike_ratio >= cfg.action.vol_spike_ratio_avoid
    ):
        triggers.append("Vol spike ngắn hạn — biến động 1M tăng mạnh → phòng thủ.")
        return "AVOID", ["Rủi ro rung lắc ngắn hạn đang cao."], triggers, 0.85, ""

    if np.isfinite(m.corr_shift) and m.corr_shift <= cfg.action.corr_shift_down_avoid:
        triggers.append("Correlation shift down — cổ phiếu decouple khỏi VNIndex.")
        return "AVOID", ["Ngắn hạn cổ phiếu không còn đi theo thị trường."], triggers, 0.80, ""

    # ── Pre-regime candle hard AVOID (items 1, 2, 7) ─────────────────────────
    if candle_flags.get("evening_star"):
        triggers.append("Evening Star 3-nến tại đỉnh — tín hiệu đảo chiều mạnh.")
        return "AVOID", ["Mẫu nến Evening Star — đảo chiều giảm xác suất cao."], triggers, 0.85, ""

    if candle_flags.get("bearish_engulfing_top"):
        triggers.append("Bearish Engulfing tại vùng đỉnh — áp lực bán đột ngột.")
        return "AVOID", ["Nến gấu nuốt toàn bộ nến tăng trước tại đỉnh."], triggers, 0.85, ""

    if candle_flags.get("shooting_star_ma50plus"):
        triggers.append("Shooting Star trên MA50 — đuôi trên dài, từ chối vùng giá cao.")
        return "AVOID", ["Shooting Star trên MA50 — dễ pullback ngắn hạn."], triggers, 0.80, ""

    # ── Statistical hard AVOID (items 3, 6) ───────────────────────────────────
    # Item 3: Z-score Ret1M > 2.5σ
    if np.isfinite(m.ret_1m) and np.isfinite(m.monthly_vol_24m) and m.monthly_vol_24m > 0:
        z_score_1m = m.ret_1m / m.monthly_vol_24m
        if z_score_1m > 2.5:
            triggers.append(f"Z-score 1M = {z_score_1m:.1f}σ — tăng bất thường, rủi ro mean-reversion.")
            return (
                "AVOID",
                [f"Ret1M ({m.ret_1m * 100:.1f}%) / Vol tháng = {z_score_1m:.1f}σ > 2.5 — reversion risk cao."],
                triggers, 0.85, "",
            )

    # Item 6: Near 52W high (trong 5%) + vol spike >= 1.5x
    _near_52w = (
        np.isfinite(m.high_52w) and np.isfinite(m.last_close) and m.high_52w > 0
        and (m.high_52w - m.last_close) / m.high_52w <= 0.05
    )
    if _near_52w and np.isfinite(m.vol_spike_ratio) and m.vol_spike_ratio >= 1.5:
        triggers.append(
            f"Gần đỉnh 52W ({(1 - m.last_close / m.high_52w) * 100:.1f}% dưới đỉnh)"
            f" + vol {m.vol_spike_ratio:.1f}x — phân phối."
        )
        return (
            "AVOID",
            ["Giá tiếp cận đỉnh 52 tuần + khối lượng đột biến — dấu hiệu phân phối."],
            triggers, 0.80, "",
        )

    # ── Layer 1: Regime filter ─────────────────────────────────────────────────
    regime = getattr(m, "regime_state", "Neutral")
    if regime == "Bear":
        return (
            "WAIT",
            ["Regime thị trường đang Bear — chờ xác nhận phục hồi trước khi vào vị thế."],
            triggers,
            0.85,
            "",
        )

    # ── Item 8: Momentum concentration > 65% → WAIT ──────────────────────────
    if np.isfinite(m.ret_1m) and np.isfinite(m.ret_3m) and m.ret_3m > 0.01 and m.ret_1m > 0:
        mom_conc = m.ret_1m / m.ret_3m
        if mom_conc > 0.65:
            notes.append(
                f"Momentum tập trung: 1M/3M = {mom_conc:.0%} — {m.ret_1m * 100:.1f}% tăng dồn trong 1 tháng."
            )
            return "WAIT", notes[:3], triggers, 0.65, ""

    # ── Layer 2: Momentum timing ───────────────────────────────────────────────
    momentum_ok = signals.get("momentum_ok", False) if signals else False
    rsi = signals.get("rsi") if signals else None
    agreement = signals.get("agreement", "0/0") if signals else "0/0"

    if not momentum_ok:
        quality_bad = (
            (np.isfinite(m.sharpe_12m) and m.sharpe_12m < 0.5)
            and (np.isfinite(m.excess_ret_3m) and m.excess_ret_3m < -0.05)
        )
        if rsi is not None and rsi > 70:
            notes.append(f"RSI {rsi:.0f} — overbought, dễ pullback.")
        elif rsi is not None and rsi < 35:
            notes.append(f"RSI {rsi:.0f} — áp lực bán còn mạnh.")
        notes.append(f"Momentum chưa đủ xác nhận ({agreement} tín hiệu tích cực).")
        if quality_bad:
            return "AVOID", notes[:3], triggers, 0.65, ""
        return "WAIT", notes[:3], triggers, 0.60, ""

    # ── Overbought → WAIT (momentum ok nhưng quá nhiệt) ──────────────────────
    if rsi is not None and rsi > 80:
        notes.append(f"RSI {rsi:.0f} > 80 — quá mua nghiêm trọng, chờ pullback về 60–70.")
        return "WAIT", notes[:3], triggers, 0.70, ""

    if mfi is not None and mfi > 80:
        notes.append(f"MFI {mfi:.0f} > 80 — dòng tiền cực kỳ nóng, chờ hạ nhiệt.")
        return "WAIT", notes[:3], triggers, 0.70, ""

    if rsi is not None and rsi > 70 and vol_ratio is not None and vol_ratio > 3.0:
        notes.append(f"RSI {rsi:.0f} + Vol {vol_ratio:.1f}x TB20 — đột biến kép, rủi ro đảo chiều.")
        return "WAIT", notes[:3], triggers, 0.70, ""

    # ── Layer 3: Quality confirm ───────────────────────────────────────────────
    quality_issues: List[str] = []

    sharpe_ok = np.isfinite(m.sharpe_12m) and m.sharpe_12m >= 0.5
    if not sharpe_ok and np.isfinite(m.sharpe_12m):
        quality_issues.append(f"Sharpe 12M = {m.sharpe_12m:.2f} < 0.5 → giảm size.")
        size_note = "Giảm size"

    alpha_ok = np.isfinite(m.excess_ret_3m) and m.excess_ret_3m >= 0
    if not alpha_ok and np.isfinite(m.excess_ret_3m):
        quality_issues.append(f"Alpha 3M âm ({m.excess_ret_3m * 100:.1f}%) → giảm confidence.")

    beta_sym_ok = True
    if np.isfinite(m.beta_up_12m) and np.isfinite(m.beta_dn_12m):
        beta_sym_ok = m.beta_up_12m >= m.beta_dn_12m
        if not beta_sym_ok:
            quality_issues.append(
                f"Beta bất xứng (βdn={m.beta_dn_12m:.2f} > βup={m.beta_up_12m:.2f}) → nới stop."
            )
            if not size_note:
                size_note = "Nới stop"

    # RSI > 75: timing risk — pullback probability cao → giảm size
    rsi_ok = rsi is None or rsi <= 75
    if not rsi_ok:
        quality_issues.append(f"RSI {rsi:.0f} quá mua — dễ pullback, chờ về vùng 60–65 để vào an toàn hơn.")
        if not size_note:
            size_note = "Giảm size"

    # Item 5: MaxDD 24M < -50% → structural WARNING
    if np.isfinite(m.max_drawdown_24m) and m.max_drawdown_24m < -0.50:
        quality_issues.append(
            f"MaxDD 24M = {m.max_drawdown_24m * 100:.1f}% — rủi ro sụt giảm cấu trúc cao."
        )
        if not size_note:
            size_note = "Giảm size"

    # Item 9: Alpha decay > 50% (36M → 24M)
    if np.isfinite(m.alpha_36m) and np.isfinite(m.alpha_24m) and m.alpha_36m > 0.02:
        alpha_decay = (m.alpha_36m - m.alpha_24m) / m.alpha_36m
        if alpha_decay > 0.50:
            quality_issues.append(
                f"Alpha suy giảm {alpha_decay * 100:.0f}% (36M→24M) — động lực tăng yếu dần."
            )
            if not size_note:
                size_note = "Giảm size"

    # Item 11: Shp12M < VNI Sharpe - 0.5
    if np.isfinite(m.sharpe_12m) and np.isfinite(m.bench_sharpe_12m):
        if m.sharpe_12m < m.bench_sharpe_12m - 0.5:
            quality_issues.append(
                f"Shp12M {m.sharpe_12m:.2f} kém VNI {m.bench_sharpe_12m:.2f} rõ rệt — underperform thị trường."
            )
            if not size_note:
                size_note = "Giảm size"

    quality_good = sharpe_ok and alpha_ok and beta_sym_ok and rsi_ok

    # Item 10: Doji tại kháng cự → WAIT (override BUY)
    if candle_flags.get("doji_resistance"):
        notes.append("Doji tại vùng kháng cự — thị trường lưỡng lự, chờ breakout xác nhận.")
        return "WAIT", notes[:3], triggers, 0.65, ""

    # Item 12: Convexity âm → WAIT (βdn > βup, mất bất đối xứng thuận lợi)
    if np.isfinite(m.convexity_12m) and m.convexity_12m < 0:
        notes.append(
            f"Convexity âm ({m.convexity_12m:.2f}) — βdn > βup, thua nhiều hơn thắng khi thị trường biến động."
        )
        return "WAIT", notes[:3], triggers, 0.65, ""

    if m.above_ma50:
        notes.append("Giá trên MA50 — xu hướng ngắn hạn xác nhận.")
    else:
        notes.append("Giá chưa vượt MA50 — uptrend chưa hoàn toàn xác nhận.")

    if quality_good:
        notes.append("Momentum tốt + Quality tốt → có thể giải ngân full size.")
        confidence = 0.80
    else:
        notes.extend(quality_issues[:2])
        notes.append("Momentum tốt nhưng có yếu tố rủi ro → MUA giảm size / stop chặt hơn.")
        confidence = 0.65

    return "BUY", notes[:3], triggers, confidence, size_note


async def compute_task1_v2(
    ticker: str,
    rf_annual: float,
    cfg: Task1V2RuleConfig,
    vnindex_cache: Optional[Dict[str, Any]] = None,
) -> Tuple[Task1MetricsV2, Task1DecisionV2]:
    now = pd.Timestamp.now(tz="UTC")
    end = now.date().isoformat()
    start_24m = (now - pd.DateOffset(months=24)).date().isoformat()
    start_36m = (now - pd.DateOffset(months=36)).date().isoformat()

    async def _fetch_with_fallback(symbol, start, end):
        """Fetch history with fallback to earlier date (runs in thread to avoid blocking)."""
        s = await asyncio.to_thread(fetch_history, symbol, start, end)
        if not s.empty:
            return s
        for days_back in range(1, 7):
            prev = (pd.Timestamp(end) - pd.Timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )
            s = await asyncio.to_thread(fetch_history, symbol, start, prev)
            if not s.empty:
                return s
        return s

    async def _vnindex_with_fallback(start, end):
        """Fetch VNIndex with fallback dates. Checks vnindex_cache before fetching."""
        cache_key = f"{start}|{end}"
        if vnindex_cache is not None and cache_key in vnindex_cache:
            return vnindex_cache[cache_key]
        try:
            s = await asyncio.to_thread(fetch_vnindex, start, end)
            if not s.empty:
                if vnindex_cache is not None:
                    vnindex_cache[cache_key] = s
                return s
        except RuntimeError:
            pass
        for days_back in range(1, 7):
            prev = (pd.Timestamp(end) - pd.Timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )
            try:
                s = await asyncio.to_thread(fetch_vnindex, start, prev)
                if not s.empty:
                    if vnindex_cache is not None:
                        vnindex_cache[cache_key] = s
                    return s
            except RuntimeError:
                pass
        return pd.Series(dtype=float)

    px_s_24 = await _fetch_with_fallback(ticker, start_24m, end)
    px_b_24 = await _vnindex_with_fallback(start_24m, end)

    df24 = pd.concat([px_s_24.rename("s"), px_b_24.rename("b")], axis=1).dropna()
    sr24 = to_returns(df24["s"])
    br24 = to_returns(df24["b"])

    # Return/Vol/Sharpe 24M
    ann_ret_s = ann_return(sr24)
    ann_vol_s = ann_vol(sr24)
    shp_24 = sharpe(sr24, rf_annual)

    ann_ret_b = ann_return(br24)
    ann_vol_b = ann_vol(br24)
    shp_b = sharpe(br24, rf_annual)

    # Sharpe 12M
    sr12 = sr24.iloc[-252:] if len(sr24) >= 252 else sr24
    shp_12 = sharpe(sr12, rf_annual)
    br12 = br24.iloc[-252:] if len(br24) >= 252 else br24
    shp_b_12 = sharpe(br12, rf_annual)

    # Return 6M/1M
    s_6m_px = window_slice(df24["s"], 126)
    s_1m_px = window_slice(df24["s"], 21)
    ret_6m = simple_return(s_6m_px)
    ret_1m = simple_return(s_1m_px)
    b_6m_px = window_slice(df24["b"], 126)
    b_1m_px = window_slice(df24["b"], 21)
    vni_ret_6m = simple_return(b_6m_px)
    vni_ret_1m = simple_return(b_1m_px)

    # betas 12M/6M from returns regression
    def beta_last(n: int) -> float:
        if len(sr24) < n:
            return np.nan
        _, b = reg_alpha_beta(sr24.iloc[-n:], br24.iloc[-n:])
        return b

    beta12 = beta_last(252)
    beta6 = beta_last(126)

    br12 = br24.iloc[-252:] if len(br24) >= 252 else br24
    beta_up, beta_dn = upside_downside_beta(sr12, br12)
    convexity = (
        (beta_up - beta_dn)
        if (np.isfinite(beta_up) and np.isfinite(beta_dn))
        else np.nan
    )

    # correlations
    corr24 = corr(sr24, br24)
    sr6 = sr24.iloc[-126:] if len(sr24) >= 126 else sr24
    br6 = br24.iloc[-126:] if len(br24) >= 126 else br24
    corr6 = corr(sr6, br6)
    corr_shift = (
        (corr6 - corr24) if (np.isfinite(corr6) and np.isfinite(corr24)) else np.nan
    )

    # Alpha 24M
    a24_d, _ = reg_alpha_beta(sr24, br24)
    alpha24 = annualize_alpha(a24_d)

    # Alpha 36M
    px_s_36 = await _fetch_with_fallback(ticker, start_36m, end)
    px_b_36 = await _vnindex_with_fallback(start_36m, end)
    df36 = pd.concat([px_s_36.rename("s"), px_b_36.rename("b")], axis=1).dropna()

    alpha36 = np.nan
    if df36.shape[0] >= 180:
        sr36 = to_returns(df36["s"])
        br36 = to_returns(df36["b"])
        a_d, _ = reg_alpha_beta(sr36, br36)
        alpha36 = annualize_alpha(a_d)

    # short horizon context: 3M excess + vols + MA
    s_3m_px = window_slice(df24["s"], 63)
    b_3m_px = window_slice(df24["b"], 63)

    # Bench Return 6M/1M
    b_6m_px = window_slice(df24["b"], 126)
    b_1m_px = window_slice(df24["b"], 21)
    vni_ret_6m = simple_return(b_6m_px)
    vni_ret_1m = simple_return(b_1m_px)

    # Bench Sharpe 12M
    br12 = br24.iloc[-252:] if len(br24) >= 252 else br24
    shp_b_12 = sharpe(br12, rf_annual)

    ret_3m = simple_return(s_3m_px)
    vni_ret_3m = simple_return(b_3m_px)
    excess_3m = (
        (ret_3m - vni_ret_3m)
        if (np.isfinite(ret_3m) and np.isfinite(vni_ret_3m))
        else np.nan
    )

    vol_1m = ann_vol(to_returns(s_1m_px)) if len(s_1m_px) >= 10 else np.nan
    vol_6m = ann_vol(to_returns(s_6m_px)) if len(s_6m_px) >= 50 else np.nan
    vol_spike_ratio = (
        (vol_1m / vol_6m)
        if (np.isfinite(vol_1m) and np.isfinite(vol_6m) and vol_6m > 0)
        else np.nan
    )

    last_close = float(df24["s"].iloc[-1]) if not df24.empty else np.nan
    ma20 = ma(df24["s"], 20)
    ma50 = ma(df24["s"], 50)
    above_ma50 = bool(
        np.isfinite(last_close) and np.isfinite(ma50) and last_close > ma50
    )

    # VNI vol 1M/6M + spike
    vni_1m = window_slice(df24["b"], 21)
    vni_6m = window_slice(df24["b"], 126)

    # --- VNI volatility regime ---
    vni_1m_px = window_slice(df24["b"], 21)
    vni_6m_px = window_slice(df24["b"], 126)

    vni_vol_1m = ann_vol(to_returns(vni_1m_px)) if len(vni_1m_px) >= 10 else np.nan
    vni_vol_6m = ann_vol(to_returns(vni_6m_px)) if len(vni_6m_px) >= 50 else np.nan
    vni_vol_spike_ratio = (
        (vni_vol_1m / vni_vol_6m)
        if (np.isfinite(vni_vol_1m) and np.isfinite(vni_vol_6m) and vni_vol_6m > 0)
        else np.nan
    )

    sortino_24m = sortino(sr24, rf_annual)
    max_dd_24m = max_drawdown(sr24)
    calmar_24m = calmar(sr24)
    regime_state = detect_regime(ann_ret_b, ann_vol_b)
    trailing_stop_pct, trailing_stop_is_capped = trailing_stop_metrics(sr24, rf_annual, ann_vol_s)

    # 52-week high (for Flag 6)
    s_52w = window_slice(df24["s"], 252)
    high_52w = float(s_52w.max()) if not s_52w.empty else float("nan")

    # Monthly vol (for Flag 3 Z-score)
    monthly_vol_24m = ann_vol_s / math.sqrt(12) if np.isfinite(ann_vol_s) else float("nan")

    metrics = Task1MetricsV2(
        ann_ret_24m=ann_ret_s,
        ret_6m=ret_6m,
        ret_1m=ret_1m,
        vni_ret_6m=vni_ret_6m,
        vni_ret_1m=vni_ret_1m,
        bench_sharpe_12m=shp_b_12,
        sharpe_24m=shp_24,
        sharpe_12m=shp_12,
        alpha_36m=alpha36,
        alpha_24m=alpha24,
        beta_12m=beta12,
        beta_up_12m=beta_up,
        beta_dn_12m=beta_dn,
        convexity_12m=convexity,
        beta_6m=beta6,
        corr_24m=corr24,
        corr_6m=corr6,
        corr_shift=corr_shift,
        ret_3m=ret_3m,
        vni_ret_3m=vni_ret_3m,
        excess_ret_3m=excess_3m,
        vol_1m=vol_1m,
        vol_6m=vol_6m,
        vol_spike_ratio=vol_spike_ratio,
        vni_vol_1m=vni_vol_1m,
        vni_vol_6m=vni_vol_6m,
        vni_vol_spike_ratio=vni_vol_spike_ratio,
        ma20=ma20,
        ma50=ma50,
        last_close=last_close,
        above_ma50=above_ma50,
        bench_ret_24m=ann_ret_b,
        bench_vol_24m=ann_vol_b,
        bench_sharpe_24m=shp_b,
        ann_vol_24m=ann_vol_s,
        sortino_24m=sortino_24m,
        max_drawdown_24m=max_dd_24m,
        calmar_24m=calmar_24m,
        momentum_score=np.nan,
        trailing_stop_pct=trailing_stop_pct,
        regime_state=regime_state,
        trailing_stop_is_capped=trailing_stop_is_capped,
        high_52w=high_52w,
        monthly_vol_24m=monthly_vol_24m,
        meta={
            "ticker": ticker,
            "points_24m": int(len(sr24)),
            "points_36m": int(df36.shape[0]),
        },
    )

    metrics.momentum_score = momentum_score(metrics)

    role, role_notes, role_confidence = classify_role(metrics, cfg)

    # ── Signal engine: fetch OHLCV 65 phiên gần nhất ─────────────────────────
    hist_df_60: pd.DataFrame = pd.DataFrame()
    try:
        start_60d = (now - pd.DateOffset(days=100)).date().isoformat()
        raw_ohlcv = await asyncio.to_thread(_fetch_ohlcv_raw, ticker, start_60d, end)
        if not isinstance(raw_ohlcv, pd.DataFrame) or raw_ohlcv.empty:
            for _days_back in range(1, 8):
                _prev = (pd.Timestamp(end) - pd.Timedelta(days=_days_back)).strftime("%Y-%m-%d")
                raw_ohlcv = await asyncio.to_thread(_fetch_ohlcv_raw, ticker, start_60d, _prev)
                if isinstance(raw_ohlcv, pd.DataFrame) and not raw_ohlcv.empty:
                    break
        if isinstance(raw_ohlcv, pd.DataFrame) and not raw_ohlcv.empty:
            hist_df_60 = raw_ohlcv.tail(65).reset_index(drop=True)
    except Exception as _e:
        print(f"[signal_engine] OHLCV fetch failed for {ticker}: {_e}")

    _metrics_dict = {
        "sharpe_12m": metrics.sharpe_12m,
        "bench_sharpe_12m": metrics.bench_sharpe_12m,
        "excess_ret_3m": metrics.excess_ret_3m,
        "beta_up_12m": metrics.beta_up_12m,
        "beta_dn_12m": metrics.beta_dn_12m,
    }
    signals = classify_signals(ticker, hist_df_60, _metrics_dict)
    stop_data = calc_dynamic_stop(metrics.last_close, hist_df_60)

    # ── 3-layer decision ──────────────────────────────────────────────────────
    action, action_notes, triggers, action_confidence, size_note = decide_action_layered(
        metrics, signals, cfg
    )

    decision = Task1DecisionV2(
        role=role,
        action=action,
        role_notes=role_notes[:3],
        action_notes=action_notes[:3],
        risk_triggers=triggers[:4],
        warn_triggers=[],
        role_confidence=role_confidence,
        action_confidence=action_confidence,
        signals=signals,
        stop_data=stop_data,
        size_note=size_note,
    )
    return metrics, decision


# =========================
# EMBED (Bloomberg line-by-line table like screenshot)
# =========================
# task1/embed.py (table-only patch)

GREEN = "🟢"
RED = "🔴"
NEU = "⚪"


def _p(x: float, nd: int = 1) -> str:
    return "NA" if (x is None or not np.isfinite(x)) else f"{x * 100:.{nd}f}%"


def _n(x: float, nd: int = 2) -> str:
    return "NA" if (x is None or not np.isfinite(x)) else f"{x:.{nd}f}"


def _flag_compare(a: float, b: float, higher_is_better: bool = True) -> str:
    if (a is None or b is None) or (not np.isfinite(a)) or (not np.isfinite(b)):
        return NEU
    if higher_is_better:
        return GREEN if a >= b else RED
    return GREEN if a <= b else RED


def _conf_bar(confidence: float) -> str:
    if not np.isfinite(confidence):
        return "⚪"
    pct = max(0.0, min(1.0, confidence))
    bars = int(pct * 10)
    return "🟢" * max(1, bars) + "⚪" * (10 - bars)


def _mini_bar(confidence: float, n: int = 5) -> str:
    """Compact confidence bar. e.g. '▓▓▓▓░ 78%'"""
    if not np.isfinite(confidence):
        return "░░░░░ N/A"
    pct = max(0.0, min(1.0, confidence))
    filled = round(pct * n)
    return "▓" * filled + "░" * (n - filled) + f" {int(pct * 100)}%"


def _row(label: str, a: str, b: str, f: str, w1=12, w2=8, w3=8) -> str:
    # fixed width => no column shift on mobile
    return f"{label:<{w1}} {a:>{w2}} {b:>{w3}} {f}"


def build_task1_table(m) -> str:
    """
    Same table for desktop + mobile.
    Width ~ 12 + 1 + 8 + 1 + 8 + 2 => fits most phones in code block.
    """
    tkr = str(m.meta.get("ticker", "TICK"))

    lines = []
    lines.append(_row("METRIC", tkr, "VNI", NEU))
    lines.append("-" * 34)

    # ===== RETURN =====
    lines.append("RETURN")
    lines.append(
        _row(
            "Ret 24M",
            _p(m.ann_ret_24m),
            _p(m.bench_ret_24m),
            _flag_compare(m.ann_ret_24m, m.bench_ret_24m, True),
        )
    )
    lines.append(
        _row(
            "Ret 6M",
            _p(m.ret_6m),
            _p(m.vni_ret_6m),
            _flag_compare(m.ret_6m, m.vni_ret_6m, True),
        )
    )
    lines.append(
        _row(
            "Ret 1M",
            _p(m.ret_1m),
            _p(m.vni_ret_1m),
            _flag_compare(m.ret_1m, m.vni_ret_1m, True),
        )
    )
    lines.append("")

    # ===== SHARPE =====
    lines.append("SHARPE")
    lines.append(
        _row(
            "Shp 24M",
            _n(m.sharpe_24m, 2),
            _n(m.bench_sharpe_24m, 2),
            _flag_compare(m.sharpe_24m, m.bench_sharpe_24m, True),
        )
    )
    lines.append(
        _row(
            "Shp 12M",
            _n(m.sharpe_12m, 2),
            _n(m.bench_sharpe_12m, 2),
            _flag_compare(m.sharpe_12m, m.bench_sharpe_12m, True),
        )
    )
    lines.append("")

    # ===== ALPHA =====
    lines.append("ALPHA")
    # VNI alpha vs itself = 0 by definition
    lines.append(
        _row(
            "Alp 36M",
            _p(m.alpha_36m),
            _p(0.0),
            GREEN if (np.isfinite(m.alpha_36m) and m.alpha_36m >= 0) else RED,
        )
    )
    lines.append(
        _row(
            "Alp 24M",
            _p(m.alpha_24m),
            _p(0.0),
            GREEN if (np.isfinite(m.alpha_24m) and m.alpha_24m >= 0) else RED,
        )
    )
    lines.append("")

    # ===== BETA =====
    lines.append("BETA")
    # VNI beta vs itself = 1; fix NA by forcing bench values
    lines.append(
        _row(
            "β12M",
            _n(m.beta_12m),
            _n(1.00),
            _flag_compare(abs(m.beta_12m - 1.0), 0.0, higher_is_better=False),
        )
    )
    lines.append(
        _row("βup12M", _n(m.beta_up_12m), _n(1.00), NEU)
    )  # benchmark forced 1.00
    lines.append(
        _row(
            "βdn12M",
            _n(m.beta_dn_12m),
            _n(1.00),
            _flag_compare(m.beta_dn_12m, 1.0, higher_is_better=False),
        )
    )
    # Conv: show ratio (βup/βdn) instead of raw diff for clearer interpretation
    if np.isfinite(m.beta_up_12m) and np.isfinite(m.beta_dn_12m) and m.beta_dn_12m > 0:
        conv_ratio = m.beta_up_12m / m.beta_dn_12m
        conv_flag = GREEN if conv_ratio >= 1.30 else (RED if conv_ratio < 1.10 else NEU)
        lines.append(_row("Conv(ratio)", f"{conv_ratio:.2f}x", "1.00x", conv_flag))
    else:
        lines.append(_row("Conv", _n(m.convexity_12m), _n(0.00), NEU))
    lines.append(_row("β6M", _n(m.beta_6m), _n(1.00), NEU))
    lines.append("")

    # ===== VOLATILITY (replace CORR) =====
    lines.append("VOLATILITY")
    lines.append(
        _row(
            "Volat 24M",
            _p(m.ann_vol_24m),
            _p(m.bench_vol_24m),
            _flag_compare(m.ann_vol_24m, m.bench_vol_24m, higher_is_better=False),
        )
    )
    lines.append(
        _row(
            "Volat 1M",
            _p(m.vol_1m),
            _p(m.vni_vol_1m),
            NEU
            if not np.isfinite(m.vni_vol_1m)
            else _flag_compare(m.vol_1m, m.vni_vol_1m, False),
        )
    )
    lines.append(
        _row(
            "Volat 6M",
            _p(m.vol_6m),
            _p(m.vni_vol_6m),
            NEU
            if not np.isfinite(m.vni_vol_6m)
            else _flag_compare(m.vol_6m, m.vni_vol_6m, False),
        )
    )
    lines.append(
        _row(
            "Spike 1M/6M",
            _n(m.vol_spike_ratio, 2) + "x",
            _n(m.vni_vol_spike_ratio, 2) + "x",
            NEU
            if not np.isfinite(m.vni_vol_spike_ratio)
            else _flag_compare(m.vol_spike_ratio, m.vni_vol_spike_ratio, False),
        )
    )

    # ===== QUALITY =====
    lines.append("")
    lines.append("QUALITY")
    lines.append(
        _row(
            "Sortino",
            _n(m.sortino_24m, 2),
            _n(m.bench_sharpe_24m, 2),
            _flag_compare(m.sortino_24m, m.bench_sharpe_24m, True),
        )
    )
    lines.append(
        _row(
            "MaxDD 24M",
            _p(m.max_drawdown_24m),
            "NA",
            NEU if not np.isfinite(m.max_drawdown_24m) else RED,
        )
    )
    lines.append(
        _row(
            "Calmar",
            _n(m.calmar_24m, 2),
            "NA",
            NEU
            if not np.isfinite(m.calmar_24m)
            else _flag_compare(m.calmar_24m, 0.5, True),
        )
    )
    lines.append(
        _row(
            "Momentum",
            f"{_n(m.momentum_score, 0)}/100",
            "NA",
            NEU
            if not np.isfinite(m.momentum_score)
            else (
                GREEN
                if m.momentum_score >= 55
                else (RED if m.momentum_score < 35 else NEU)
            ),
        )
    )

    lines.append("")
    lines.append("🟢 tốt hơn  🔴 kém hơn  ⚪ NA")

    return "```\n" + "\n".join(lines) + "\n```"


def build_task1_v2_embed(
    m: Task1MetricsV2,
    d: Task1DecisionV2,
    cfg: Task1V2RuleConfig,
    mobile_first: bool = False,
) -> discord.Embed:
    """
    Discord embed format mới:
      - Header: ticker | sector | role
      - Description: quyết định + score + tín hiệu đồng thuận
      - 🟢 Tích cực block (signal_engine)
      - 🔴 Tiêu cực block (signal_engine)
      - Trailing Stop & Indicators (ATR-dynamic)
      - Vai trò tài sản
      - CTA: button "📋 Xem số liệu chi tiết" (qua MetricsTableView)
    """
    t = cfg.text
    ticker = m.meta.get("ticker", "TICKER")
    sector_info = get_sector_info(ticker) or {}
    primary_sector = sector_info.get("primary_sector", "NA")
    model_type = sector_info.get("model_type", "NA")
    role = (d.role or "TACTICAL").upper()
    action = (d.action or "WAIT").upper()

    signals = d.signals or {}
    stop_data = d.stop_data or {}
    size_note = d.size_note or ""

    agreement = signals.get("agreement", "—")
    rsi = signals.get("rsi")
    slope = signals.get("macd_slope")
    mfi = signals.get("mfi")

    score_str = _n(m.momentum_score, 0) + "/100" if np.isfinite(m.momentum_score) else "—/100"
    size_tag = f" | **{size_note}**" if size_note else ""

    # ── Description: action + score + action notes (no role, no bars) ──
    desc_lines = [
        f"**{t.action_name_vi.get(action, action)}**{size_tag}",
        f"Score: **{score_str}** | Tín hiệu: **{agreement}**",
    ]
    if d.action_notes:
        desc_lines.append("")
        desc_lines.extend([f"• {n}" for n in d.action_notes[:2]])

    emb = discord.Embed(
        title=f"📊 {ticker}  |  {primary_sector}  |  {model_type}",
        description="\n".join(desc_lines),
        colour=color_for_action(action),
    )

    # ── 🟢 Tích cực block ─────────────────────────────────────────────
    pos_list = signals.get("positive", [])
    if pos_list:
        pos_text = "\n".join([f"• {p['label']}: **{p['value']}**" for p in pos_list[:3]])
        emb.add_field(name="🟢 Tích cực", value=pos_text, inline=False)

    # ── 🔴 Tiêu cực block ─────────────────────────────────────────────
    neg_list = signals.get("negative", [])
    if neg_list:
        neg_text = "\n".join([f"• {n['label']}: {n['value']}" for n in neg_list[:3]])
        emb.add_field(name="🔴 Tiêu cực", value=neg_text, inline=False)

    # ── Trailing Stop & Indicators ─────────────────────────────────────
    stop_price = stop_data.get("stop_price")
    stop_pct = stop_data.get("stop_pct")
    stop_method = stop_data.get("stop_method") or stop_data.get("method")

    if stop_price is not None and stop_pct is not None:
        stop_str = f"**{stop_price:,.0f}** ({stop_pct}% | {stop_method}-based)"
    elif np.isfinite(m.trailing_stop_pct):
        capped = " ⚠️*" if m.trailing_stop_is_capped else ""
        stop_str = f"{m.trailing_stop_pct * 100:.0f}%{capped} (vol-based)"
    else:
        stop_str = "15% (vol-based)"

    ind_parts = []
    if rsi is not None:
        ind_parts.append(f"RSI {rsi:.0f}")
    if slope is not None:
        ind_parts.append(f"MACD {slope:+.2f}")
    if mfi is not None:
        ind_parts.append(f"MFI {mfi:.0f}")
    indicators_str = " | ".join(ind_parts) if ind_parts else "—"

    ma50_tag = "✅ trên MA50" if m.above_ma50 else "⚠ dưới MA50"
    stop_field_val = (
        f"🛑 Stop: {stop_str}\n"
        f"📈 {indicators_str}\n"
        f"Giá: **{_n(m.last_close, 0)}** | MA50: {_n(m.ma50, 0)} | {ma50_tag}"
    )
    emb.add_field(name="Trailing Stop & Indicators", value=stop_field_val, inline=False)

    # ── Vai trò tài sản ───────────────────────────────────────────────
    role_val = (
        f"{t.role_name_vi.get(role, role)} {_conf_bar(d.role_confidence)}\n"
        f"{t.role_one_liner.get(role, '')}"
    )
    if d.role_notes:
        role_val += "\n" + "\n".join([f"• {x}" for x in d.role_notes[:2]])
    emb.add_field(name="Vai trò tài sản", value=role_val, inline=False)

    # ── CTA bảng chi tiết ─────────────────────────────────────────────
    emb.add_field(
        name="📋 Bảng metrics chi tiết",
        value=f"_(Dùng `/quant_detail {ticker}` để xem Return / Sharpe / Alpha / Beta / Volatility đầy đủ)_",
        inline=False,
    )

    # ── Footer ────────────────────────────────────────────────────────
    mom_score = m.momentum_score
    mom_str = f"{_n(mom_score, 0)}/100" if np.isfinite(mom_score) else "N/A"
    emb.set_footer(
        text=(
            f"Regime: {m.regime_state} | "
            f"Momentum: {mom_str} | "
            f"24M pts: {m.meta.get('points_24m', 'NA')} | "
            f"rf={RF_ANNUAL:.0%}"
        )
    )
    return emb


def build_task1_v2_embed_with_table(
    m: Task1MetricsV2,
    d: Task1DecisionV2,
    cfg: Task1V2RuleConfig,
) -> discord.Embed:
    """Bảng chi tiết đầy đủ — gọi khi user click button hoặc /quant_detail."""
    emb = discord.Embed(
        title=f"📋 Chi tiết metrics — {m.meta.get('ticker', 'TICKER')}",
        colour=discord.Colour.light_grey(),
    )
    table = build_task1_table(m)
    emb.add_field(name="Bảng số liệu", value=table, inline=False)
    emb.set_footer(text=f"Regime: {m.regime_state} | rf={RF_ANNUAL:.0%}")
    return emb


# =========================
# DISCORD BUTTON VIEW — Metrics Table on demand
# =========================


class MetricsTableView(discord.ui.View):
    """
    View chứa button "📋 Xem số liệu chi tiết".
    Khi click → gửi embed bảng metrics dạng ephemeral. Timeout 5 phút.
    """

    def __init__(self, m: Task1MetricsV2, d: Task1DecisionV2, cfg: Task1V2RuleConfig):
        super().__init__(timeout=300)
        self.m = m
        self.d = d
        self.cfg = cfg

    @discord.ui.button(
        label="📋 Xem số liệu chi tiết",
        style=discord.ButtonStyle.secondary,
    )
    async def show_table(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        table_emb = build_task1_v2_embed_with_table(self.m, self.d, self.cfg)
        await interaction.response.send_message(embed=table_emb, ephemeral=True)


# =========================
# AI Independent Rating (reads compute inputs, independent of rules)
# =========================
def _clean_text(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


_GS: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    global _GS
    if _GS is None:
        _GS = GeminiService()
        _dbg(
            "[AI] GeminiService init | ready=",
            _GS.is_ready(),
            "| model=",
            _GS.model_name(),
            "| err=",
            getattr(_GS, "last_error", lambda: "")(),
        )
    return _GS


async def ai_independent_assessment(
    ticker: str,
    m: Task1MetricsV2,
    timeout_sec: int = AI_TIMEOUT_SEC,
) -> Optional[dict]:
    if not TASK1_AI_ENABLED:
        return None

    gs = get_gemini_service()
    if not gs.is_ready():
        _dbg("[AI] not ready:", getattr(gs, "last_error", lambda: "")())
        return None

    # Prompt: bạn có thể đổi sang tiếng Việt hoàn toàn (mình giữ cấu trúc y như bạn)
    prompt = f"""
Bạn là Quant Portfolio Manager.

Nhiệm vụ: đưa ra ĐÁNH GIÁ ĐỘC LẬP chỉ dựa trên các metrics bên dưới.
TUYỆT ĐỐI KHÔNG tham chiếu / suy đoán / căn chỉnh theo bất kỳ rule engine hay quyết định sẵn có nào.

QUY TẮC OUTPUT (BẮT BUỘC):
- Chỉ trả về JSON hợp lệ, không markdown, không thêm chữ khác.
- Không bọc JSON trong backticks.
- Viết tiếng Việt dễ hiểu, không emoji.

FIELDS:
- role: 1 trong ["CORE","TACTICAL","DEFENSIVE","VOL_AMPLIFIER","SPECULATIVE"]
- action_st: 1 trong ["BUY","WAIT","AVOID"]
- confidence: số nguyên 0-100
- rationale: mảng 3-5 câu ngắn (tiếng Việt, practical)
- Trong rationale phải có ít nhất 4 câu có chứa số cụ thể từ INPUT (ví dụ: "Sharpe 12M=1.23", "Beta 6M=0.85", "Vol spike=1.40x", "Ret 1M=-0.02").
- Nếu không có số cụ thể → coi như output KHÔNG HỢP LỆ.
- risk_triggers: giải thích rủi ro ngắn hạn là gì, vì sao

INPUT METRICS:
Ticker: {ticker}

Return: 24M={m.ann_ret_24m:.6f}, 6M={m.ret_6m:.6f}, 1M={m.ret_1m:.6f}
Sharpe: 24M={m.sharpe_24m:.6f}, 12M={m.sharpe_12m:.6f}
Alpha: 36M={m.alpha_36m:.6f}, 24M={m.alpha_24m:.6f}
Beta: 12M={m.beta_12m:.6f}, up12M={m.beta_up_12m:.6f}, dn12M={m.beta_dn_12m:.6f}, convex={m.convexity_12m:.6f}, beta6M={m.beta_6m:.6f}
Corr: 24M={m.corr_24m:.6f}, 6M={m.corr_6m:.6f}, shift={m.corr_shift:.6f}
Short context: excess3M={m.excess_ret_3m:.6f}, above_ma50={int(m.above_ma50)}
Vol: ann24M={m.ann_vol_24m:.6f}, vol1M={m.vol_1m:.6f}, vol6M={m.vol_6m:.6f}, spike={m.vol_spike_ratio:.6f}

Schema:
{{
  "role": "TACTICAL",
  "action_st": "WAIT",
  "confidence": 60,
  "rationale": ["...", "...", "..."],
  "risk_triggers": ["...", "..."]
}}
""".strip()

    # _GEMINI = GeminiService()

    # if not _GEMINI.is_ready():
    #     return None
    data = await gs.generate_json(prompt, timeout_sec)
    if not data:
        return None

    # Validate + normalize
    role = str(data.get("role", "")).upper().strip()
    action = str(data.get("action_st", "")).upper().strip()
    conf = data.get("confidence", None)
    rationale = data.get("rationale", [])
    triggers = data.get("risk_triggers", [])

    if role not in {"CORE", "TACTICAL", "DEFENSIVE", "VOL_AMPLIFIER", "SPECULATIVE"}:
        return None
    if action not in {"BUY", "WAIT", "AVOID"}:
        return None

    try:
        conf_i = int(conf)
    except Exception:
        conf_i = 50
    conf_i = max(0, min(100, conf_i))

    if not isinstance(rationale, list):
        return None
    rationale = [_clean_text(str(x)) for x in rationale if _clean_text(str(x))][:5]
    if len(rationale) < 3:
        return None

    if not isinstance(triggers, list):
        triggers = []
    triggers = [_clean_text(str(x)) for x in triggers if _clean_text(str(x))][:3]

    return {
        "model": gs.model_name(),
        "role": role,
        "action_st": action,
        "confidence": conf_i,
        "rationale": rationale,
        "risk_triggers": triggers,
    }


# =========================
# PUBLIC HANDLER (called by menu)
# =========================
async def handle_task1(
    interaction: discord.Interaction, ticker: str, mobile_first: bool = True
) -> None:
    """
    Usage from menu:
        await handle_task1(interaction, ticker)
    Sends:
      1) Main embed (rule-engine decision + Bloomberg metrics table)
      2) Optional AI independent assessment message (no table)
    """
    cfg = Task1V2RuleConfig()

    await interaction.followup.send("🧠 AgentQ đang phân tích…", ephemeral=True)

    m, d = await compute_task1_v2(ticker=ticker, rf_annual=RF_ANNUAL, cfg=cfg)

    emb = build_task1_v2_embed(m, d, cfg, mobile_first=mobile_first)
    await interaction.followup.send(embed=emb, ephemeral=False)

    # AI independent message (optional)
    if not TASK1_AI_ENABLED:
        await interaction.followup.send("✅ Hoàn tất. (AI đang tắt)", ephemeral=True)
        return

    ai = await ai_independent_assessment(ticker, m, timeout_sec=AI_TIMEOUT_SEC)
    if not ai:
        gs = get_gemini_service()
        reason = getattr(gs, "last_error", lambda: "")()
        more = f" | model={gs.model_name()}" if gs else ""
        await interaction.followup.send(
            f"✅ Hoàn tất. (AI fail: {reason or 'timeout/parse'}){more}", ephemeral=True
        )
        return

    msg = (
        f"**Phần 2 — Đánh giá độc lập của AI**\n"
        f"- 🤖 Model: **{ai.get('model', 'AI')}**\n"
        f"- Role: **{ai['role']}**\n"
        f"- Ngắn hạn: **{ai['action_st']}** | Confidence: **{ai['confidence']}%**\n"
        f"- Lý do:\n"
        + "\n".join([f"  • {x}" for x in ai["rationale"]])
        + (
            ("\n- Triggers:\n" + "\n".join([f"  • {x}" for x in ai["risk_triggers"]]))
            if ai.get("risk_triggers")
            else ""
        )
    )
    await interaction.followup.send(msg, ephemeral=False)
    await interaction.followup.send("✅ AgentQ đã hoàn tất phân tích.", ephemeral=True)


# =========================
# ENTRY POINT FOR NEW ROUTER
# =========================
async def handle_task1(interaction, ticker: str) -> None:
    """Handle Task 1 - Quantitative analysis using V2 Decision Engine."""
    try:
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
        except Exception:
            pass

        # from app.utils.helpers import safe_ticker # Assuming safe_ticker is still there
        # ticker = safe_ticker(ticker)
        ticker = ticker.strip().upper()

        cfg = Task1V2RuleConfig()

        metrics, decision = await compute_task1_v2(ticker, RF_ANNUAL, cfg)

        embed = build_task1_v2_embed(metrics, decision, cfg)
        view = MetricsTableView(metrics, decision, cfg)

        # Optional AI assessment
        if TASK1_AI_ENABLED:
            try:
                ai_data = await ai_independent_assessment(ticker, metrics)
                if ai_data:
                    role_ai = ai_data.get("role", "")
                    action_ai = ai_data.get("action_st", "")
                    conf = ai_data.get("confidence", 0)
                    emb_ai = discord.Embed(
                        title="🤖 Gemini AI Assessment (Independent)",
                        color=discord.Color.purple(),
                    )
                    emb_ai.add_field(
                        name="AI Role & Action",
                        value=f"**{role_ai}** | **{action_ai}** (Confidence: {conf}%)",
                        inline=False,
                    )

                    rats = ai_data.get("rationale", [])
                    if rats:
                        emb_ai.add_field(
                            name="Rationale",
                            value="\n".join([f"- {r}" for r in rats]),
                            inline=False,
                        )

                    risks = ai_data.get("risk_triggers", [])
                    if risks:
                        emb_ai.add_field(
                            name="Risk Triggers",
                            value="\n".join([f"- {r}" for r in risks]),
                            inline=False,
                        )

                    await interaction.followup.send(
                        embeds=[embed, emb_ai], view=view, ephemeral=False
                    )
                    return
            except Exception as e:
                print(f"[AI] Rating error: {e}")

        await interaction.followup.send(embed=embed, view=view, ephemeral=False)

    except Exception as e:
        await interaction.followup.send(f"Lỗi phân tích: {e}", ephemeral=True)
