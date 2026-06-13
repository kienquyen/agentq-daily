# features.portfolio/regime.py
# -*- coding: utf-8 -*-

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional

import numpy as np
import pandas as pd

from .risk_engine import WindowPack


@dataclass
class RegimeShift:
    score: int
    label: str  # Stable / Watch / Shift
    triggers: Dict[str, Any]


def _safe(x) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _corr_pair(corr: pd.DataFrame, a: str, b: str) -> float:
    if corr is None or corr.empty:
        return float("nan")
    if a not in corr.columns or b not in corr.columns:
        return float("nan")
    return _safe(corr.loc[a, b])


def compute_regime_shift(pack60: WindowPack, pack180: WindowPack) -> RegimeShift:
    """
    Regime shift score = rule-based, explainable.
    """
    triggers: Dict[str, Any] = {}
    score = 0

    vol60 = _safe(pack60.ann_vol)
    vol180 = _safe(pack180.ann_vol)
    if np.isfinite(vol60) and np.isfinite(vol180) and vol180 > 0:
        if vol60 > vol180 * 1.25:
            score += 25
            triggers["vol_spike"] = f"vol60 {vol60:.2%} > 1.25x vol180 {vol180:.2%}"
        elif vol60 < vol180 * 0.80:
            triggers["vol_cooldown"] = f"vol60 {vol60:.2%} < 0.8x vol180 {vol180:.2%}"

    # Tail worsening
    es60 = _safe(pack60.es95)
    es180 = _safe(pack180.es95)
    if np.isfinite(es60) and np.isfinite(es180) and es180 != 0:
        # ES is negative usually. "worse" means more negative.
        if es60 < es180 * 1.3:
            score += 20
            triggers["tail_worsen"] = f"ES95_60 {es60:.2%} worse vs ES95_180 {es180:.2%}"

    # Convexity loss (skew flips)
    sk60 = _safe(pack60.skew)
    sk180 = _safe(pack180.skew)
    if np.isfinite(sk60) and np.isfinite(sk180):
        if sk60 < 0 and sk180 > 0:
            score += 15
            triggers["skew_flip_neg"] = f"skew60 {sk60:.2f} < 0 while skew180 {sk180:.2f} > 0"

    # Risk concentration jump: max RC (largest contributor)
    if pack60.rc is not None and not pack60.rc.empty and pack180.rc is not None and not pack180.rc.empty:
        m60 = _safe(pack60.rc.iloc[0])
        m180 = _safe(pack180.rc.iloc[0])
        if np.isfinite(m60) and np.isfinite(m180):
            if (m60 - m180) > 0.15:
                score += 20
                triggers["risk_concentration_jump"] = f"maxRC60 {m60:.0%} - maxRC180 {m180:.0%} > 15%"

    # Correlation breakdown example (VN-BTC) if both exist
    # (We won't assume tickers; detect by prefixes in asset keys)
    # heuristic: one key contains "BTC", another contains "VN" or looks like VN ticker.
    assets60 = list(pack60.corr.columns) if pack60.corr is not None and not pack60.corr.empty else []
    a_btc = next((x for x in assets60 if "BTC" in x.upper()), None)
    a_vn = next((x for x in assets60 if x.upper().startswith("VN:")), None)

    if a_btc and a_vn:
        c60 = _corr_pair(pack60.corr, a_btc, a_vn)
        c180 = _corr_pair(pack180.corr, a_btc, a_vn)
        if np.isfinite(c60) and np.isfinite(c180):
            if (c60 - c180) > 0.20:
                score += 20
                triggers["corr_rise_vn_btc"] = f"corr60 {c60:.2f} - corr180 {c180:.2f} > +0.20"

    score = int(max(0, min(100, score)))

    if score < 30:
        label = "Stable"
    elif score < 60:
        label = "Watch"
    else:
        label = "Shift"

    return RegimeShift(score=score, label=label, triggers=triggers)