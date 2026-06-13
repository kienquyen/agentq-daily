#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/regime_pnl_analysis.py

Full backtest comparison: v1 vs v3a
  - Enrich test rows with real regime labels via detect_regime()
  - Analyze WR and PnL by regime and by cutoff
  - Answer: does raising cutoff to 0.60 actually increase total PnL?

Assumptions:
  - Equal position size per signal (1 unit)
  - Return = return_20d (actual 20-day forward return %)
  - No transaction costs
"""
from __future__ import annotations
import sys, pickle
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODEL_V1  = ROOT / "data/models/lgbm_model_20d_backup.pkl"
MODEL_V3A = ROOT / "data/models/lgbm_model_20d.pkl"
TRAIN_SET = ROOT / "data/labels/training_set_20d.parquet"
TEST_START = "2025-01-01"

# ─── helpers ──────────────────────────────────────────────────────────────────

def _load_model(path):
    obj = pickle.load(open(path, "rb"))
    return (obj["model"], obj["feat_cols"]) if isinstance(obj, dict) else (obj, [])

def _score(model, df, feat_cols):
    tmp = df.copy()
    for c in feat_cols:
        if c not in tmp.columns:
            tmp[c] = np.nan
    return model.predict_proba(tmp[feat_cols])[:, 1]

def _stats(returns: pd.Series, label: str = "") -> dict:
    n    = len(returns)
    if n == 0:
        return dict(n=0, wr=np.nan, avg_ret=np.nan, total_ret=np.nan, sharpe=np.nan)
    wr        = (returns >= 5.0).mean() * 100
    avg_ret   = returns.mean()
    total_ret = returns.sum()
    sharpe    = returns.mean() / returns.std() * np.sqrt(252 / 20) if returns.std() > 0 else np.nan
    return dict(n=n, wr=round(wr,1), avg_ret=round(avg_ret,2),
                total_ret=round(total_ret,1), sharpe=round(sharpe,2))

# ─── main ─────────────────────────────────────────────────────────────────────

def run():
    # ── Load + filter ─────────────────────────────────────────────────────────
    print("Loading training set …")
    df = pd.read_parquet(TRAIN_SET)
    if "label_valid" in df.columns:
        df = df[df["label_valid"] == 1]

    if isinstance(df.index, pd.MultiIndex):
        df["_date"] = pd.to_datetime(df.index.get_level_values("date"))
    else:
        df["_date"] = pd.to_datetime(df.index)

    test = df[df["_date"] >= TEST_START].copy()
    print(f"Test rows: {len(test):,}  |  {test['_date'].min().date()} → {test['_date'].max().date()}")

    # ── Enrich regime ─────────────────────────────────────────────────────────
    print("Detecting regime for each date …")
    from pipeline.regime_detector import detect_regime

    dates = sorted(test["_date"].dt.strftime("%Y-%m-%d").unique())
    regime_map = {}
    for d in dates:
        try:
            regime, _, _ = detect_regime(d)
        except Exception:
            regime = "unknown"
        regime_map[d] = regime

    test["regime"] = test["_date"].dt.strftime("%Y-%m-%d").map(regime_map)
    test["year"]   = test["_date"].dt.year

    regime_dist = test.groupby("regime")["_date"].nunique().sort_values(ascending=False)
    print("Regime distribution (trading days):")
    for r, n in regime_dist.items():
        print(f"  {r:<12} {n:>4} days")

    # ── Load + score models ───────────────────────────────────────────────────
    print("\nLoading models & scoring …")
    m_v1,  fc_v1  = _load_model(MODEL_V1)
    m_v3a, fc_v3a = _load_model(MODEL_V3A)

    test["prob_v1"]  = _score(m_v1,  test, fc_v1)
    test["prob_v3a"] = _score(m_v3a, test, fc_v3a)
    test["ret20"]    = test["return_20d"].clip(-50, 100)

    print(f"v1 features: {len(fc_v1)} | v3a features: {len(fc_v3a)}")

    # ── Section 1: WR & PnL by cutoff ─────────────────────────────────────────
    print("\n" + "=" * 72)
    print("SECTION 1 — WR & PnL by cutoff  (equal-weight per signal)")
    print("=" * 72)
    fmt = f"{'Cutoff':>7}  {'v1 n':>6} {'v1 WR':>7} {'v1 AvgRet':>10} {'v1 TotalRet':>12}  │  {'v3a n':>6} {'v3a WR':>7} {'v3a AvgRet':>10} {'v3a TotalRet':>12}"
    print(fmt)
    print("─" * 72)
    for cut in [0.50, 0.52, 0.54, 0.55, 0.56, 0.58, 0.60, 0.62, 0.65]:
        s1  = _stats(test.loc[test["prob_v1"]  >= cut, "ret20"])
        s3a = _stats(test.loc[test["prob_v3a"] >= cut, "ret20"])
        wr1  = f"{s1['wr']:.1f}%" if not np.isnan(s1['wr']) else "—"
        wr3a = f"{s3a['wr']:.1f}%" if not np.isnan(s3a['wr']) else "—"
        ar1  = f"{s1['avg_ret']:+.2f}%" if not np.isnan(s1['avg_ret']) else "—"
        ar3a = f"{s3a['avg_ret']:+.2f}%" if not np.isnan(s3a['avg_ret']) else "—"
        tr1  = f"{s1['total_ret']:+,.0f}%" if not np.isnan(s1['total_ret']) else "—"
        tr3a = f"{s3a['total_ret']:+,.0f}%" if not np.isnan(s3a['total_ret']) else "—"
        print(f"  {cut:.2f}   {s1['n']:>6} {wr1:>7} {ar1:>10} {tr1:>12}  │  {s3a['n']:>6} {wr3a:>7} {ar3a:>10} {tr3a:>12}")

    # ── Section 2: By regime (cutoff = 0.58) ──────────────────────────────────
    print("\n" + "=" * 72)
    print("SECTION 2 — By regime  (cutoff = 0.58)")
    print("=" * 72)
    CUT = 0.58
    rows = []
    for regime in sorted(test["regime"].unique()):
        grp = test[test["regime"] == regime]
        days = grp["_date"].nunique()
        s1  = _stats(grp.loc[grp["prob_v1"]  >= CUT, "ret20"])
        s3a = _stats(grp.loc[grp["prob_v3a"] >= CUT, "ret20"])
        rows.append({
            "Regime": regime, "Days": days,
            "v1 n": s1["n"],   "v1 WR%": s1["wr"],   "v1 AvgRet%": s1["avg_ret"],
            "v3a n": s3a["n"], "v3a WR%": s3a["wr"], "v3a AvgRet%": s3a["avg_ret"],
            "ΔWR%": round(s3a["wr"] - s1["wr"], 1) if not np.isnan(s1["wr"]) and not np.isnan(s3a["wr"]) else np.nan,
        })
    reg_df = pd.DataFrame(rows)
    print(reg_df.to_string(index=False))

    # ── Section 3: PnL cutoff 0.58 vs 0.60 ──────────────────────────────────
    print("\n" + "=" * 72)
    print("SECTION 3 — Does raising cutoff 0.58 → 0.60 increase total PnL?")
    print("=" * 72)
    for model_name, prob_col in [("v1", "prob_v1"), ("v3a", "prob_v3a")]:
        print(f"\n  {model_name}:")
        for cut in [0.55, 0.58, 0.60, 0.62]:
            sigs = test[test[prob_col] >= cut]["ret20"]
            n    = len(sigs)
            wr   = (sigs >= 5.0).mean() * 100 if n > 0 else np.nan
            avg  = sigs.mean() if n > 0 else np.nan
            total = sigs.sum() if n > 0 else np.nan
            sh   = (sigs.mean() / sigs.std() * np.sqrt(252/20)) if n > 0 and sigs.std() > 0 else np.nan
            print(f"    cutoff={cut:.2f}  n={n:>5}  WR={wr:.1f}%  avg={avg:+.2f}%  total={total:+,.0f}%  sharpe={sh:.2f}")

    # ── Section 4: Year × Regime breakdown (v3a @0.58) ───────────────────────
    print("\n" + "=" * 72)
    print("SECTION 4 — Year × Regime  (v3a @ 0.58)")
    print("=" * 72)
    sub = test[test["prob_v3a"] >= 0.58].copy()
    pivot = sub.groupby(["year", "regime"]).agg(
        signals=("ret20", "count"),
        wr=("ret20", lambda x: round((x >= 5.0).mean() * 100, 1)),
        avg_ret=("ret20", lambda x: round(x.mean(), 2)),
    ).reset_index()
    print(pivot.to_string(index=False))


if __name__ == "__main__":
    run()
