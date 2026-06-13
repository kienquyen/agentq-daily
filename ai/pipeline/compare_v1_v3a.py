#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/compare_v1_v3a.py

So sánh toàn diện model v1 vs v3a (model 20D mới nhất).

Phương pháp:
  - Áp dụng đúng live filters: T1(dynamic cutoff) + T2(vol) + T3(EMA) + T4(candle) + HC
  - Return thực từ OHLCV T+20 (không dùng label proxy)
  - Period: 2022-07-01 → 2026-04-13 (label_valid rows)
  - Phân tích: overall, by year, by regime, by sector, phân phối return

Output: ~/Desktop/compare_v1_v3a.xlsx + console

v1  = lgbm_model_20d_backup.pkl  (80 features, không có foreign flow)
v3a = lgbm_model_20d.pkl         (87 features, có foreign flow + market-regime interactions)
"""
from __future__ import annotations
import sys, pickle
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODEL_V1   = ROOT / "data/models/lgbm_model_20d_backup.pkl"
MODEL_V3A  = ROOT / "data/models/lgbm_model_20d.pkl"
TRAIN_SET  = ROOT / "data/labels/training_set_20d.parquet"
OHLCV_DIR  = ROOT / "data/ohlcv"
OUTPUT_XLS = Path.home() / "Desktop" / "compare_v1_v3a.xlsx"

TEST_START = "2022-07-01"
WIN_THRESH = 5.0   # %
HOLD_DAYS  = 20    # trading days
EMA_PCT    = 12.0  # T3 tolerance


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_model(path: Path):
    obj = pickle.load(open(path, "rb"))
    if isinstance(obj, dict):
        return obj["model"], obj.get("feat_cols", [])
    return obj, []


def _add_n_trading_days(date_str: str, n: int) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    count = 0
    while count < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            count += 1
    return d.strftime("%Y-%m-%d")


def _load_ohlcv_cache(symbols: list) -> dict:
    cache = {}
    for sym in symbols:
        p = OHLCV_DIR / f"{sym}.parquet"
        if not p.exists():
            continue
        try:
            df = pd.read_parquet(p, columns=["time", "close"])
            df["time"] = pd.to_datetime(df["time"])
            cache[sym] = df.set_index("time")["close"].sort_index().astype(float)
        except Exception:
            pass
    return cache


def _get_exit_price(cache: dict, symbol: str, exit_date: str) -> float | None:
    s = cache.get(symbol)
    if s is None:
        return None
    sub = s[s.index <= pd.Timestamp(exit_date)]
    return float(sub.iloc[-1]) if not sub.empty else None


def _load_sector_map(symbols: list) -> dict:
    try:
        from features.industry.sector_library import get_sector_info
        result = {}
        for sym in symbols:
            try:
                info = get_sector_info(sym)
                result[sym] = info.get("primary_sector", "Unknown") if info else "Unknown"
            except Exception:
                result[sym] = "Unknown"
        return result
    except ImportError:
        return {s: "Unknown" for s in symbols}


def _stats(returns: pd.Series) -> dict:
    n = len(returns)
    if n == 0:
        return dict(n=0, wr5=np.nan, wr0=np.nan, avg=np.nan, med=np.nan,
                    sharpe=np.nan, worst=np.nan, sl_rate=np.nan, p25=np.nan, p75=np.nan)
    wr5    = (returns >= WIN_THRESH).mean() * 100
    wr0    = (returns >= 0).mean() * 100
    avg    = returns.mean()
    med    = returns.median()
    std    = returns.std()
    sharpe = avg / std * np.sqrt(252 / HOLD_DAYS) if std > 0 else np.nan
    worst  = returns.min()
    sl_r   = (returns <= -10.0).mean() * 100
    return dict(
        n=n, wr5=round(wr5,1), wr0=round(wr0,1),
        avg=round(avg,2), med=round(med,2), std=round(std,2),
        sharpe=round(sharpe,2), worst=round(worst,2),
        sl_rate=round(sl_r,1),
        p25=round(returns.quantile(0.25),2),
        p75=round(returns.quantile(0.75),2),
    )


def _apply_filters(df: pd.DataFrame, probs: np.ndarray, cutoff_series: pd.Series) -> pd.Series:
    """Apply T1-T4+HC filters. Returns boolean mask."""
    # T1: dynamic cutoff per row
    t1 = pd.Series(probs >= cutoff_series.values, index=df.index)

    # T2: vol_ratio_20d >= 0.70
    vr = df.get("vol_ratio_20d", pd.Series(np.nan, index=df.index))
    t2 = vr.isna() | (vr >= 0.70)

    # T3: close within ±12% of EMA
    cl  = df.get("close_vnd", pd.Series(np.nan, index=df.index))
    ea  = df.get("ema20", df.get("ema9",  pd.Series(np.nan, index=df.index)))
    eb  = df.get("ema50", df.get("ema26", pd.Series(np.nan, index=df.index)))
    with np.errstate(invalid="ignore", divide="ignore"):
        na_a = ea.notna() & (ea > 0) & ((cl / ea.replace(0, np.nan) - 1).abs() * 100 <= EMA_PCT)
        na_b = eb.notna() & (eb > 0) & ((cl / eb.replace(0, np.nan) - 1).abs() * 100 <= EMA_PCT)
    t3 = na_a | na_b | cl.isna()

    # T4: no bearish candles
    ss = df.get("candle_shooting_star",     pd.Series(0, index=df.index))
    be = df.get("candle_bearish_engulfing", pd.Series(0, index=df.index))
    es = df.get("candle_evening_star",      pd.Series(0, index=df.index))
    t4 = (ss != 1) & (be != 1) & (es != 1)

    # HC
    hc = df.get("hardcheck_pass", pd.Series(1, index=df.index)).fillna(0).astype(bool)

    return t1 & t2.values & t3.values & t4.values & hc.values


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print("=" * 72)
    print("  SO SÁNH MODEL v1 vs v3a — BACKTEST THỰC TẾ (OHLCV T+20)")
    print(f"  Period: {TEST_START} → 2026-04-13  |  Filters: T1(dynamic)+T2+T3+T4+HC")
    print("=" * 72)

    # ── 1. Load data ──────────────────────────────────────────────────────────
    print("\nLoading training set …")
    df = pd.read_parquet(TRAIN_SET)
    if "label_valid" in df.columns:
        df = df[df["label_valid"] == 1]
    df = df.reset_index()
    df["_date"] = pd.to_datetime(df["date"])
    df = df[df["_date"] >= TEST_START].copy()
    print(f"  Rows: {len(df):,}  |  {df['_date'].min().date()} → {df['_date'].max().date()}")
    print(f"  Symbols: {df['symbol'].nunique()}  |  Dates: {df['_date'].nunique()}")

    # ── 2. Load models ────────────────────────────────────────────────────────
    print("\nLoading models …")
    m_v1,  feat_v1  = _load_model(MODEL_V1)
    m_v3a, feat_v3a = _load_model(MODEL_V3A)
    print(f"  v1  features: {len(feat_v1):>3}  |  n_estimators={m_v1.n_estimators}")
    print(f"  v3a features: {len(feat_v3a):>3}  |  n_estimators={m_v3a.n_estimators}")

    # ── 3. Score both models ─────────────────────────────────────────────────
    print("\nScoring …")
    tmp_v1  = df.copy()
    tmp_v3a = df.copy()
    for c in feat_v1:
        if c not in tmp_v1.columns: tmp_v1[c] = np.nan
    for c in feat_v3a:
        if c not in tmp_v3a.columns: tmp_v3a[c] = np.nan

    prob_v1  = m_v1.predict_proba(tmp_v1[feat_v1])[:, 1]
    prob_v3a = m_v3a.predict_proba(tmp_v3a[feat_v3a])[:, 1]
    df["prob_v1"]  = prob_v1
    df["prob_v3a"] = prob_v3a
    print(f"  v1  prob>=0.50: {(prob_v1>=0.50).sum():,}  |  prob>=0.53: {(prob_v1>=0.53).sum():,}")
    print(f"  v3a prob>=0.50: {(prob_v3a>=0.50).sum():,}  |  prob>=0.53: {(prob_v3a>=0.53).sum():,}")

    # ── 4. Detect regime → dynamic cutoff ────────────────────────────────────
    print("\nDetecting regime for each date …")
    from pipeline.regime_detector import detect_regime, REGIME_CUTOFFS

    dates_uniq = sorted(df["_date"].dt.strftime("%Y-%m-%d").unique())
    regime_map  = {}
    cutoff_map  = {}
    for d in dates_uniq:
        try:
            reg, cut, _ = detect_regime(d)
            regime_map[d] = reg
            cutoff_map[d] = cut
        except Exception:
            regime_map[d] = "sideways"
            cutoff_map[d] = 0.53

    df["date_str"]   = df["_date"].dt.strftime("%Y-%m-%d")
    df["regime"]     = df["date_str"].map(regime_map)
    df["dyn_cutoff"] = df["date_str"].map(cutoff_map)
    df["year"]       = df["_date"].dt.year

    print("\n  Regime distribution (days):")
    for r, cnt in df.groupby("regime")["date_str"].nunique().sort_values(ascending=False).items():
        print(f"    {r:<12} {cnt:>4} ngày")

    # ── 5. Apply filters ──────────────────────────────────────────────────────
    print("\nApplying filters …")
    cutoff_s = df["dyn_cutoff"]
    df["pass_v1"]  = _apply_filters(df, prob_v1,  cutoff_s)
    df["pass_v3a"] = _apply_filters(df, prob_v3a, cutoff_s)
    print(f"  v1  passed: {df['pass_v1'].sum():,} signals")
    print(f"  v3a passed: {df['pass_v3a'].sum():,} signals")

    # ── 6. Compute T+20 returns from OHLCV ───────────────────────────────────
    print("\nLoading OHLCV & computing T+20 returns …")
    all_syms = df["symbol"].unique().tolist()
    ohlcv    = _load_ohlcv_cache(all_syms)
    sector_map = _load_sector_map(all_syms)
    print(f"  Loaded {len(ohlcv):,} OHLCV files")

    def _compute_returns(mask: pd.Series) -> pd.DataFrame:
        sub = df[mask].copy()
        rows = []
        for _, row in sub.iterrows():
            sym      = row["symbol"]
            sig_date = row["date_str"]
            entry    = row.get("close_vnd", np.nan)
            if not np.isfinite(entry) or entry <= 0:
                continue
            exit_date = _add_n_trading_days(sig_date, HOLD_DAYS)
            exit_px   = _get_exit_price(ohlcv, sym, exit_date)
            if exit_px is None:
                continue
            ret = (exit_px - entry) / entry * 100
            rows.append({
                "signal_date": sig_date,
                "symbol":      sym,
                "regime":      row["regime"],
                "year":        row["year"],
                "sector":      sector_map.get(sym, "Unknown"),
                "prob":        round(row["prob_v1"] if "prob_v1" in row.index else row["prob_v3a"], 4),
                "entry":       entry,
                "exit_px":     exit_px,
                "ret_t20":     round(ret, 2),
                "is_win":      ret >= WIN_THRESH,
                "hit_sl":      ret <= -10.0,
            })
        return pd.DataFrame(rows)

    print("  Computing returns for v1 …")
    df["prob_v1_val"]  = df["prob_v1"]
    rdf_v1  = _compute_returns(df["pass_v1"])
    rdf_v1["prob"] = df.loc[df["pass_v1"], "prob_v1"].values[:len(rdf_v1)]

    print("  Computing returns for v3a …")
    rdf_v3a = _compute_returns(df["pass_v3a"])
    rdf_v3a["prob"] = df.loc[df["pass_v3a"], "prob_v3a"].values[:len(rdf_v3a)]

    print(f"  v1  valid signals: {len(rdf_v1):,}")
    print(f"  v3a valid signals: {len(rdf_v3a):,}")

    # ── 7. Comparison tables ──────────────────────────────────────────────────
    def _print_compare(label: str, s1: dict, s2: dict):
        def _fmt(d: dict) -> str:
            if d["n"] == 0: return f"{'n/a':^55}"
            return (f"n={d['n']:>5}  WR5={d['wr5']:>5.1f}%  WR0={d['wr0']:>5.1f}%  "
                    f"avg={d['avg']:>+6.2f}%  sharpe={d['sharpe']:>5.2f}  SL={d['sl_rate']:>4.1f}%")
        print(f"\n  ── {label} ──")
        print(f"  v1  : {_fmt(s1)}")
        print(f"  v3a : {_fmt(s2)}")
        if s1["n"] > 0 and s2["n"] > 0:
            dwr = s2["wr5"] - s1["wr5"]
            davg = s2["avg"] - s1["avg"]
            dsh  = s2["sharpe"] - s1["sharpe"]
            tag = "✅ v3a thắng" if dwr >= 2 and dsh >= 0 else ("⚠️ mixed" if dwr >= 0 else "❌ v3a tệ hơn")
            print(f"  Δ   : ΔWR5={dwr:+.1f}%  ΔAvg={davg:+.2f}%  ΔSharpe={dsh:+.2f}  {tag}")

    # Overall
    print("\n" + "=" * 72)
    print("  OVERALL")
    print("=" * 72)
    _print_compare("ALL", _stats(rdf_v1["ret_t20"]), _stats(rdf_v3a["ret_t20"]))

    # By year
    print("\n" + "=" * 72)
    print("  THEO NĂM")
    print("=" * 72)
    all_years = sorted(set(rdf_v1["year"].unique()) | set(rdf_v3a["year"].unique()))
    yr_rows = []
    for yr in all_years:
        s1 = _stats(rdf_v1[rdf_v1["year"] == yr]["ret_t20"])
        s2 = _stats(rdf_v3a[rdf_v3a["year"] == yr]["ret_t20"])
        _print_compare(str(yr), s1, s2)
        yr_rows.append({"year": yr,
            "v1_n": s1["n"], "v1_wr5": s1["wr5"], "v1_avg": s1["avg"], "v1_sharpe": s1["sharpe"],
            "v3a_n": s2["n"], "v3a_wr5": s2["wr5"], "v3a_avg": s2["avg"], "v3a_sharpe": s2["sharpe"],
            "delta_wr5": round(s2["wr5"] - s1["wr5"], 1) if s1["n"] > 0 and s2["n"] > 0 else np.nan,
            "delta_sharpe": round(s2["sharpe"] - s1["sharpe"], 2) if s1["n"] > 0 and s2["n"] > 0 else np.nan,
        })
    yr_df = pd.DataFrame(yr_rows)

    # By regime
    print("\n" + "=" * 72)
    print("  THEO REGIME")
    print("=" * 72)
    REGIMES = ["recovery", "bull", "sideways", "deep_bear", "choppy"]
    reg_rows = []
    for reg in REGIMES:
        s1 = _stats(rdf_v1[rdf_v1["regime"] == reg]["ret_t20"])
        s2 = _stats(rdf_v3a[rdf_v3a["regime"] == reg]["ret_t20"])
        _print_compare(reg.upper(), s1, s2)
        reg_rows.append({"regime": reg,
            "v1_n": s1["n"], "v1_wr5": s1["wr5"], "v1_avg": s1["avg"], "v1_sharpe": s1["sharpe"],
            "v3a_n": s2["n"], "v3a_wr5": s2["wr5"], "v3a_avg": s2["avg"], "v3a_sharpe": s2["sharpe"],
            "delta_wr5": round(s2["wr5"] - s1["wr5"], 1) if s1["n"] > 0 and s2["n"] > 0 else np.nan,
            "delta_sharpe": round(s2["sharpe"] - s1["sharpe"], 2) if s1["n"] > 0 and s2["n"] > 0 else np.nan,
        })
    reg_df = pd.DataFrame(reg_rows)

    # By sector (top 10 by v3a count)
    print("\n" + "=" * 72)
    print("  THEO SECTOR (top sectors)")
    print("=" * 72)
    top_sectors = rdf_v3a.groupby("sector")["ret_t20"].count().sort_values(ascending=False).head(12).index.tolist()
    sec_rows = []
    for sec in top_sectors:
        s1 = _stats(rdf_v1[rdf_v1["sector"] == sec]["ret_t20"])
        s2 = _stats(rdf_v3a[rdf_v3a["sector"] == sec]["ret_t20"])
        _print_compare(sec, s1, s2)
        sec_rows.append({"sector": sec,
            "v1_n": s1["n"], "v1_wr5": s1["wr5"], "v1_avg": s1["avg"], "v1_sharpe": s1["sharpe"],
            "v3a_n": s2["n"], "v3a_wr5": s2["wr5"], "v3a_avg": s2["avg"], "v3a_sharpe": s2["sharpe"],
            "delta_wr5": round(s2["wr5"] - s1["wr5"], 1) if s1["n"] > 0 and s2["n"] > 0 else np.nan,
            "delta_sharpe": round(s2["sharpe"] - s1["sharpe"], 2) if s1["n"] > 0 and s2["n"] > 0 else np.nan,
        })
    sec_df = pd.DataFrame(sec_rows)

    # Return distribution comparison
    print("\n" + "=" * 72)
    print("  PHÂN PHỐI RETURN")
    print("=" * 72)
    bins   = [-99, -15, -10, -5, 0, 5, 10, 15, 20, 999]
    blabels = ["<-15%", "-15~-10%", "-10~-5%", "-5~0%", "0~5%", "5~10%", "10~15%", "15~20%", ">20%"]
    rdf_v1["bucket"]  = pd.cut(rdf_v1["ret_t20"],  bins=bins, labels=blabels)
    rdf_v3a["bucket"] = pd.cut(rdf_v3a["ret_t20"], bins=bins, labels=blabels)
    d1  = rdf_v1.groupby("bucket",  observed=True).size()
    d2  = rdf_v3a.groupby("bucket", observed=True).size()
    n1, n2 = len(rdf_v1), len(rdf_v3a)
    print(f"\n  {'Bucket':<12}  {'v1':>7}  {'v3a':>7}  {'Δ':>7}")
    print(f"  {'─'*12}  {'─'*7}  {'─'*7}  {'─'*7}")
    for b in blabels:
        c1 = d1.get(b, 0); c2 = d2.get(b, 0)
        pct1 = c1/n1*100 if n1 > 0 else 0
        pct2 = c2/n2*100 if n2 > 0 else 0
        arrow = "▲" if pct2 > pct1 + 0.5 else ("▼" if pct2 < pct1 - 0.5 else " ")
        print(f"  {b:<12}  {c1:>4}({pct1:>4.1f}%)  {c2:>4}({pct2:>4.1f}%)  {arrow}{abs(pct2-pct1):>5.1f}%")

    # ── 8. Model metadata comparison ─────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  METADATA MODEL")
    print("=" * 72)
    import json
    m1_eval = json.loads((ROOT / "data/models/eval_metrics_20d_backup.json").read_text())
    m2_eval = json.loads((ROOT / "data/models/eval_metrics_20d.json").read_text())
    print(f"\n  {'Metric':<30} {'v1':>10} {'v3a':>10} {'Δ':>8}")
    print(f"  {'─'*30} {'─'*10} {'─'*10} {'─'*8}")
    metrics_to_show = [
        ("Features", len(feat_v1), len(feat_v3a)),
        ("n_estimators", m_v1.n_estimators, m_v3a.n_estimators),
        ("Train ROC-AUC", m1_eval["train"]["roc_auc"], m2_eval["train"]["roc_auc"]),
        ("Val ROC-AUC",   m1_eval["val"]["roc_auc"],   m2_eval["val"]["roc_auc"]),
        ("Test ROC-AUC",  m1_eval["test"]["roc_auc"],  m2_eval["test"]["roc_auc"]),
        ("Train PR-AUC",  m1_eval["train"]["pr_auc"],  m2_eval["train"]["pr_auc"]),
        ("Test PR-AUC",   m1_eval["test"]["pr_auc"],   m2_eval["test"]["pr_auc"]),
        ("Test Prec@50",  m1_eval["test"]["precision_at_50"], m2_eval["test"]["precision_at_50"]),
    ]
    for name, v1_val, v3a_val in metrics_to_show:
        try:
            delta = f"{v3a_val - v1_val:+.4f}"
        except Exception:
            delta = "─"
        print(f"  {name:<30} {str(v1_val):>10} {str(v3a_val):>10} {delta:>8}")

    # ── 9. Export Excel ───────────────────────────────────────────────────────
    print(f"\nExporting → {OUTPUT_XLS} …")
    overall_rows = []
    for label, rdf in [("v1", rdf_v1), ("v3a", rdf_v3a)]:
        s = _stats(rdf["ret_t20"])
        s["model"] = label
        overall_rows.append(s)
    overall_df = pd.DataFrame(overall_rows)

    with pd.ExcelWriter(OUTPUT_XLS, engine="openpyxl") as xw:
        overall_df.to_excel(xw, sheet_name="📊 Overall",    index=False)
        yr_df.to_excel(     xw, sheet_name="📅 By Year",    index=False)
        reg_df.to_excel(    xw, sheet_name="🗺️ By Regime",  index=False)
        sec_df.to_excel(    xw, sheet_name="🏭 By Sector",  index=False)
        rdf_v1.sort_values(["year","signal_date"]).to_excel(
            xw, sheet_name="📋 v1 Signals",  index=False)
        rdf_v3a.sort_values(["year","signal_date"]).to_excel(
            xw, sheet_name="📋 v3a Signals", index=False)

    print(f"✅ Done! Saved → {OUTPUT_XLS}")

    # ── 10. Final verdict ─────────────────────────────────────────────────────
    s1_all = _stats(rdf_v1["ret_t20"])
    s2_all = _stats(rdf_v3a["ret_t20"])
    print("\n" + "=" * 72)
    print("  KẾT LUẬN")
    print("=" * 72)
    print(f"""
  v1  (backup): WR5={s1_all['wr5']}%  avg={s1_all['avg']:+.2f}%  Sharpe={s1_all['sharpe']}  n={s1_all['n']:,}
  v3a (live)  : WR5={s2_all['wr5']}%  avg={s2_all['avg']:+.2f}%  Sharpe={s2_all['sharpe']}  n={s2_all['n']:,}
  Delta       : ΔWR5={s2_all['wr5']-s1_all['wr5']:+.1f}%  ΔAvg={s2_all['avg']-s1_all['avg']:+.2f}%  ΔSharpe={s2_all['sharpe']-s1_all['sharpe']:+.2f}
""")
    if s2_all["wr5"] > s1_all["wr5"] and s2_all["sharpe"] >= s1_all["sharpe"]:
        print("  ✅ v3a vượt trội v1 trên cả WR và Sharpe → Tiếp tục dùng v3a.")
    elif s2_all["sharpe"] > s1_all["sharpe"]:
        print("  ✅ v3a Sharpe cao hơn → risk-adjusted tốt hơn, dù WR có thể thấp hơn một chút.")
    else:
        print("  ⚠️  v3a không vượt trội rõ ràng → xem xét lại feature engineering hoặc training.")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    run()
