#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/compare_models_backtest.py

Compare v1 (no foreign) vs v3a (with foreign) 20D model on:
  - Full test period per year
  - Per market regime

Usage:
    python -m pipeline.compare_models_backtest
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODEL_V1   = ROOT / "data/models/lgbm_model_20d_backup.pkl"
MODEL_V3A  = ROOT / "data/models/lgbm_model_20d.pkl"
TRAIN_SET  = ROOT / "data/labels/training_set_20d.parquet"

PROB_CUTOFF = 0.50
WIN_THRESH  = 0.05   # +5%
TEST_START  = "2025-01-01"


def _load_model(path: Path):
    import pickle
    with open(path, "rb") as f:
        obj = pickle.load(f)
    # pkl is a dict: {"model": lgbm, "feat_cols": [...], ...}
    if isinstance(obj, dict):
        return obj["model"], obj.get("feat_cols", [])
    return obj, []


def _score(model, feat_df: pd.DataFrame, feat_cols: list[str]) -> np.ndarray:
    """Score rows — handle missing columns gracefully."""
    missing = [c for c in feat_cols if c not in feat_df.columns]
    for c in missing:
        feat_df[c] = np.nan
    return model.predict_proba(feat_df[feat_cols])[:, 1]


def _apply_tier3(df: pd.DataFrame, prob: np.ndarray, cutoff: float) -> pd.Series:
    """Vectorized tier3 filter — returns boolean mask."""
    t1 = prob >= cutoff

    # T2 — volume
    vr = df.get("vol_ratio_20d", pd.Series(np.nan, index=df.index))
    t2 = vr.isna() | (vr >= 0.70)

    # T3 — price near EMA
    close = df.get("close_vnd", pd.Series(np.nan, index=df.index))
    ema_a = df.get("ema20", df.get("ema9",  pd.Series(np.nan, index=df.index)))
    ema_b = df.get("ema50", df.get("ema26", pd.Series(np.nan, index=df.index)))
    with np.errstate(invalid="ignore", divide="ignore"):
        near_a = (ema_a.notna()) & ((close / ema_a.replace(0, np.nan) - 1).abs() * 100 <= 12.0)
        near_b = (ema_b.notna()) & ((close / ema_b.replace(0, np.nan) - 1).abs() * 100 <= 12.0)
    t3 = near_a | near_b | close.isna()

    # T4 — no bearish candles
    ss = df.get("candle_shooting_star",    pd.Series(0, index=df.index))
    be = df.get("candle_bearish_engulfing",pd.Series(0, index=df.index))
    es = df.get("candle_evening_star",     pd.Series(0, index=df.index))
    t4 = (ss != 1) & (be != 1) & (es != 1)

    # hardcheck
    hc = df.get("hardcheck_pass", pd.Series(1, index=df.index)).astype(bool)

    return pd.Series(t1 & t2.values & t3.values & t4.values & hc.values, index=df.index)


def run():
    print("Loading training set …")
    df = pd.read_parquet(TRAIN_SET)

    # Keep only label-valid rows in test period
    if "label_valid" in df.columns:
        df = df[df["label_valid"] == 1]

    # Parse date index
    if isinstance(df.index, pd.MultiIndex):
        dates = df.index.get_level_values("date")
    else:
        dates = pd.to_datetime(df.index)
    df = df.copy()
    df["_date"] = pd.to_datetime(dates)

    test_df = df[df["_date"] >= TEST_START].copy()
    print(f"Test rows: {len(test_df)} | dates: {test_df['_date'].min().date()} → {test_df['_date'].max().date()}")

    # Load models
    print("Loading models …")
    m_v1,  feat_v1_saved  = _load_model(MODEL_V1)
    m_v3a, feat_v3a_saved = _load_model(MODEL_V3A)

    # Use saved feat_cols from pkl (most accurate)
    feat_v1  = feat_v1_saved  if feat_v1_saved  else []
    feat_v3a = feat_v3a_saved if feat_v3a_saved else []

    # Fallback: derive from current DROP_COLS if pkl has no feat_cols
    if not feat_v1:
        from pipeline.phase4b_ml_model_20d import DROP_COLS
        DROP_V1 = DROP_COLS | {
            "foreign_net_val_5d", "foreign_net_val_20d",
            "foreign_net_ratio_5d", "foreign_net_ratio_20d",
            "foreign_buy_pct_5d", "foreign_net_days_5d", "foreign_net_days_20d",
        }
        feat_v1 = [c for c in test_df.columns if c not in DROP_V1
                   and not c.startswith("fund_") and not c.startswith("_")
                   and test_df[c].dtype != object]
    if not feat_v3a:
        from pipeline.phase4b_ml_model_20d import get_feature_cols
        feat_v3a = [c for c in get_feature_cols(test_df) if not c.startswith("_")]

    print(f"v1 features: {len(feat_v1)} | v3a features: {len(feat_v3a)}")

    # Score
    print("Scoring …")
    prob_v1  = _score(m_v1,  test_df, feat_v1)
    prob_v3a = _score(m_v3a, test_df, feat_v3a)

    # Apply tier3
    mask_v1  = _apply_tier3(test_df, prob_v1,  PROB_CUTOFF)
    mask_v3a = _apply_tier3(test_df, prob_v3a, PROB_CUTOFF)

    test_df["prob_v1"]   = prob_v1
    test_df["prob_v3a"]  = prob_v3a
    test_df["sig_v1"]    = mask_v1
    test_df["sig_v3a"]   = mask_v3a
    test_df["win"]       = (test_df.get("forward_ret_20d", test_df.get("label", 0)) >= WIN_THRESH).astype(int) \
                           if "forward_ret_20d" in test_df.columns \
                           else test_df.get("label", 0).astype(int)
    test_df["year"]      = test_df["_date"].dt.year

    # Regime — use regime_label if available else from regime_detector
    if "regime_label" in test_df.columns:
        test_df["regime"] = test_df["regime_label"]
    elif "market_regime" in test_df.columns:
        test_df["regime"] = test_df["market_regime"]
    else:
        test_df["regime"] = "unknown"

    def _stats(sub: pd.DataFrame, sig_col: str) -> dict:
        sigs = sub[sub[sig_col]]
        n = len(sigs)
        if n == 0:
            return {"signals": 0, "wr_%": np.nan, "avg_ret_%": np.nan}
        wr  = sigs["win"].mean() * 100
        ret = sigs["win"].mean() * 100   # using label as proxy
        return {"signals": n, "wr_%": round(wr, 1)}

    # ── By Year ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("BACKTEST BY YEAR")
    print("=" * 65)
    rows = []
    for yr, grp in test_df.groupby("year"):
        v1  = _stats(grp, "sig_v1")
        v3a = _stats(grp, "sig_v3a")
        rows.append({
            "Year": yr,
            "v1 signals": v1["signals"],
            "v1 WR%": v1["wr_%"],
            "v3a signals": v3a["signals"],
            "v3a WR%": v3a["wr_%"],
            "ΔWR%": round(v3a["wr_%"] - v1["wr_%"], 1) if not np.isnan(v1["wr_%"]) else np.nan,
            "Δsignals": v3a["signals"] - v1["signals"],
        })
    yr_df = pd.DataFrame(rows)
    print(yr_df.to_string(index=False))

    # ── By Regime ────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("BACKTEST BY REGIME")
    print("=" * 65)
    rows = []
    for regime, grp in test_df.groupby("regime"):
        v1  = _stats(grp, "sig_v1")
        v3a = _stats(grp, "sig_v3a")
        rows.append({
            "Regime": regime,
            "v1 signals": v1["signals"],
            "v1 WR%": v1["wr_%"],
            "v3a signals": v3a["signals"],
            "v3a WR%": v3a["wr_%"],
            "ΔWR%": round(v3a["wr_%"] - v1["wr_%"], 1) if not np.isnan(v1["wr_%"]) else np.nan,
            "Δsignals": v3a["signals"] - v1["signals"],
        })
    reg_df = pd.DataFrame(rows)
    print(reg_df.to_string(index=False))

    # ── Overall ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("OVERALL SUMMARY")
    print("=" * 65)
    for name, sig_col in [("v1 (no foreign)", "sig_v1"), ("v3a (with foreign)", "sig_v3a")]:
        sigs = test_df[test_df[sig_col]]
        n  = len(sigs)
        wr = sigs["win"].mean() * 100 if n > 0 else np.nan
        days = sigs["_date"].nunique()
        print(f"  {name:<22}: {n:>5} signals | {days:>4} signal days | WR = {wr:.1f}%")

    # ── High-confidence signals ───────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("HIGH-CONFIDENCE (prob ≥ 0.60)")
    print("=" * 65)
    for name, prob_col, sig_col in [
        ("v1",  "prob_v1",  "sig_v1"),
        ("v3a", "prob_v3a", "sig_v3a"),
    ]:
        hc = test_df[test_df[sig_col] & (test_df[prob_col] >= 0.60)]
        n  = len(hc)
        wr = hc["win"].mean() * 100 if n > 0 else np.nan
        print(f"  {name}: {n:>4} signals | WR = {wr:.1f}%")


if __name__ == "__main__":
    run()
