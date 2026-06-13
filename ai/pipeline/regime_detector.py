#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/regime_detector.py
Market Regime Detector v2 — Data-Driven Dynamic Cutoff

5-regime classification calibrated on 4,672 backtested signals (2022-07 to 2026-05):

  recovery   vs_ma50 ∈ [-5%,-2%] AND vol ∈ [15%,28%]  → WR 92.3%, R/R 3.21  cutoff 0.50
  bull       vs_ma50 > +3% AND ret20 > +3%              → WR 81.2%, R/R 2.73  cutoff 0.50
  sideways   default (not recovery/bull/deep_bear/choppy)→ WR 83.9%, R/R 2.33  cutoff 0.53
  deep_bear  vs_ma50 < -5% OR (ret20 < -8% AND vol>28%) → WR 86.7%, R/R 1.05  cutoff 0.53
  choppy     |vs_ma50|<2% AND vol<12% AND RSI 45-60      → WR 51.6%, R/R 0.59  cutoff 0.56

Key findings from backtest:
  - Recovery zone is the sweet spot: market slightly below MA50, moderate vol
  - Choppy (2024-H2 pattern) is the only regime where model significantly underperforms
  - Deep bear has high WR but 21.3% trades hit -10% drawdown → smaller position size
  - Bull has lowest edge but safest drawdown profile

Usage:
    from pipeline.regime_detector import detect_regime, get_cutoff
    regime, cutoff, detail = detect_regime("2026-05-14")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

ROOT         = Path(__file__).resolve().parent.parent
OHLCV_DIR    = ROOT / "data" / "ohlcv"
VNINDEX_PATH = OHLCV_DIR / "VNINDEX.parquet"

# ── Regime → prob_cutoff  (calibrated on 43,146 signals, 2022-07→2026-04) ──────
# Cutoff sweep per-regime (v3a, T2+T3+T4+HC, OHLCV T+20 returns):
#   recovery : 0.53 → WR5=70.9%, Sharpe=4.12, SL=0.3%  (sweet spot, don't over-filter)
#   bull     : 0.55 → WR5=57.3%, Sharpe=2.47, SL=1.0%  (peaks at 0.55-0.56, drops above)
#   sideways : 0.58 → WR5=61.4%, Sharpe=2.97, SL=1.1%  (monotone improvement)
#   deep_bear: 0.58 → WR5=77.1%, Sharpe=2.40, SL=8.0%  (was SL=10.6% at 0.53 — critical)
#   choppy   : 0.58 → WR5=61.8%, Sharpe=3.52, SL=0.7%  (was 0.56, slight improvement)
REGIME_CUTOFFS: dict[str, float] = {
    "recovery":  0.53,  # n=626:   WR5=70.9%, avg=+9.71%, Sharpe=4.12, SL=0.3%
    "bull":      0.55,  # n=867:   WR5=57.3%, avg=+7.38%, Sharpe=2.47, SL=1.0%
    "sideways":  0.58,  # n=1,399: WR5=61.4%, avg=+7.47%, Sharpe=2.97, SL=1.1%
    "deep_bear": 0.58,  # n=687:   WR5=77.1%, avg=+10.82%, Sharpe=2.40, SL=8.0%
    "choppy":    0.58,  # n=136:   WR5=61.8%, avg=+8.32%, Sharpe=3.52, SL=0.7%
}

# ── Recommended position-size multipliers  (base=1.0) ─────────────────────────
REGIME_SIZE_MULT: dict[str, float] = {
    "recovery":  1.2,   # best risk-adjusted regime — size up
    "bull":      1.0,   # normal
    "sideways":  1.0,   # normal
    "deep_bear": 0.5,   # fat-tail risk (21% hit -10%) — size down
    "choppy":    0.4,   # worst regime — very small or skip
}

# ── Regime thresholds ─────────────────────────────────────────────────────────
RECOVERY_MA50_MIN  = -5.0    # vs_ma50 >= -5%
RECOVERY_MA50_MAX  = -2.0    # vs_ma50 <= -2%
RECOVERY_VOL_MIN   = 15.0    # vol_20d >= 15%
RECOVERY_VOL_MAX   = 28.0    # vol_20d <= 28%

BULL_MA50_MIN      =  3.0    # vs_ma50 > +3%
BULL_RET20_MIN     =  3.0    # ret_20d > +3%

DEEP_BEAR_MA50_MAX = -5.0    # vs_ma50 < -5%
DEEP_BEAR_RET20_MAX= -8.0    # ret_20d < -8%
DEEP_BEAR_VOL_MIN  = 28.0    # vol_20d > 28%

CHOPPY_MA50_ABS    =  2.0    # |vs_ma50| < 2%
CHOPPY_VOL_MAX     = 12.0    # vol_20d < 12%
CHOPPY_RSI_LO      = 45.0    # RSI in [45, 60]
CHOPPY_RSI_HI      = 60.0


# ═══════════════════════════════════════════════════════════════════════════════

def _load_vnindex(as_of_date: str) -> pd.Series:
    if not VNINDEX_PATH.exists():
        raise FileNotFoundError(f"VNINDEX parquet not found: {VNINDEX_PATH}")
    df = pd.read_parquet(VNINDEX_PATH)
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time")
    df = df[df["time"] <= pd.Timestamp(as_of_date)]
    return df.set_index("time")["close"].astype(float)


def _compute_indicators(c: pd.Series) -> dict:
    n = len(c)
    out = {}
    out["ret_20d"]  = float(c.iloc[-1] / c.iloc[-20]  - 1) * 100 if n > 20  else 0.0
    out["ret_60d"]  = float(c.iloc[-1] / c.iloc[-60]  - 1) * 100 if n > 60  else 0.0
    ma50  = c.rolling(50).mean()
    ma200 = c.rolling(200).mean()
    out["vs_ma50"]  = float((c.iloc[-1] / ma50.iloc[-1]  - 1) * 100) if n >= 50  else 0.0
    out["vs_ma200"] = float((c.iloc[-1] / ma200.iloc[-1] - 1) * 100) if n >= 200 else 0.0
    out["vol_20d"]  = float(c.pct_change().tail(20).std() * np.sqrt(252) * 100) if n > 20 else 15.0
    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    out["rsi_14"] = float(100 - 100 / (1 + float(gain.iloc[-1]) / max(float(loss.iloc[-1]), 1e-9))) if n > 14 else 50.0
    hi52 = float(c.tail(252).max()) if n >= 252 else float(c.max())
    out["vs_52w_high"] = float((c.iloc[-1] / hi52 - 1) * 100)
    return out


def _classify(ind: dict) -> str:
    """
    Classify market regime from VNINDEX indicators.

    Priority order (highest → lowest):
      1. choppy     — 2024-H2 style dead-calm sideways (worst for model)
      2. recovery   — sweet spot: slight pullback + moderate vol
      3. bull       — clear uptrend
      4. deep_bear  — crash/panic (fat-tail risk)
      5. sideways   — default
    """
    vs50  = ind["vs_ma50"]
    ret20 = ind["ret_20d"]
    vol   = ind["vol_20d"]
    rsi   = ind["rsi_14"]

    # 1. Choppy — low-vol sideways drift (worst regime, must filter first)
    if (abs(vs50) < CHOPPY_MA50_ABS
            and vol < CHOPPY_VOL_MAX
            and CHOPPY_RSI_LO <= rsi <= CHOPPY_RSI_HI):
        return "choppy"

    # 2. Recovery sweet spot — slight below MA50, moderate volatility
    if (RECOVERY_MA50_MIN <= vs50 <= RECOVERY_MA50_MAX
            and RECOVERY_VOL_MIN <= vol <= RECOVERY_VOL_MAX):
        return "recovery"

    # 3. Bull trend
    if vs50 >= BULL_MA50_MIN and ret20 >= BULL_RET20_MIN:
        return "bull"

    # 4. Deep bear — crash / panic selling
    if vs50 < DEEP_BEAR_MA50_MAX or (ret20 < DEEP_BEAR_RET20_MAX and vol > DEEP_BEAR_VOL_MIN):
        return "deep_bear"

    # 5. Default sideways
    return "sideways"


def detect_regime(
    date_str: str,
    cutoff_map: dict | None = None,
    size_map:   dict | None = None,
) -> Tuple[str, float, dict]:
    """
    Detect market regime and return matching prob_cutoff.

    Args:
        cutoff_map: override REGIME_CUTOFFS (dùng khi load từ version config)
        size_map:   override REGIME_SIZE_MULT

    Returns:
        regime   : "recovery" | "bull" | "sideways" | "deep_bear" | "choppy"
        cutoff   : float  prob_cutoff for 20d model
        detail   : dict   all indicator values + regime + cutoff + size_mult
    """
    _cutoffs = cutoff_map or REGIME_CUTOFFS
    _sizes   = size_map   or REGIME_SIZE_MULT

    try:
        c = _load_vnindex(date_str)
        if len(c) < 30:
            return "sideways", _cutoffs.get("sideways", REGIME_CUTOFFS["sideways"]), {}

        ind    = _compute_indicators(c)
        regime = _classify(ind)
        cutoff = _cutoffs.get(regime, REGIME_CUTOFFS.get(regime, 0.55))
        size   = _sizes.get(regime, REGIME_SIZE_MULT.get(regime, 1.0))

        ind.update({"regime": regime, "cutoff": cutoff, "size_mult": size})

        log.debug(
            "[regime v2] %s → %s (cutoff=%.2f, size=%.1fx) | "
            "ret20=%+.1f%% vs_ma50=%+.1f%% vol=%.1f%% rsi=%.0f",
            date_str, regime, cutoff, size,
            ind["ret_20d"], ind["vs_ma50"], ind["vol_20d"], ind["rsi_14"],
        )
        return regime, cutoff, ind

    except Exception as exc:
        log.warning("[regime v2] detect_regime(%s) failed: %s", date_str, exc)
        return "sideways", REGIME_CUTOFFS["sideways"], {}


def get_cutoff(date_str: str) -> Tuple[str, float]:
    """Convenience wrapper — returns (regime, cutoff) only."""
    regime, cutoff, _ = detect_regime(date_str)
    return regime, cutoff


def get_size_multiplier(date_str: str) -> float:
    """Return position-size multiplier for the current regime."""
    _, _, detail = detect_regime(date_str)
    return detail.get("size_mult", 1.0)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, datetime

    p = argparse.ArgumentParser(description="Regime Detector v2")
    p.add_argument("--from", dest="start", default="2026-01-01")
    p.add_argument("--to",   dest="end",   default=datetime.date.today().strftime("%Y-%m-%d"))
    args = p.parse_args()

    df = pd.read_parquet(VNINDEX_PATH)
    df["time"] = pd.to_datetime(df["time"])
    df = df[(df["time"] >= args.start) & (df["time"] <= args.end)].sort_values("time")

    prev = None
    rows = []
    for _, row in df.iterrows():
        d = row["time"].strftime("%Y-%m-%d")
        regime, cutoff, ind = detect_regime(d)
        rows.append(regime)
        if regime != prev:
            print(
                f"  {d}  →  {regime:<10}  cutoff={cutoff:.2f}  size={REGIME_SIZE_MULT[regime]:.1f}x"
                f"  | ret20={ind.get('ret_20d',0):+.1f}%"
                f"  vs_ma50={ind.get('vs_ma50',0):+.1f}%"
                f"  vol={ind.get('vol_20d',0):.1f}%"
                f"  rsi={ind.get('rsi_14',0):.0f}"
            )
            prev = regime

    from collections import Counter
    print(f"\nRegime distribution ({args.start} → {args.end}):")
    for r, n in Counter(rows).most_common():
        print(f"  {r:<10} {n:>4} days  cutoff={REGIME_CUTOFFS[r]:.2f}  size={REGIME_SIZE_MULT[r]:.1f}x")
