#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/export_2026_new_cutoffs.py

Signal list 2026 với cutoff mới (calibrated 2026-05-23):
  recovery=0.53 | bull=0.55 | sideways=0.58 | deep_bear=0.58 | choppy=0.58

Nguồn dữ liệu:
  - 2026-01-01 → 2026-04-13 : training_set_20d.parquet (label_valid=1)
  - 2026-04-14 → 2026-05-21 : data/features/<date>.parquet (supplement)

Filters: T1(dynamic cutoff) + T2(vol≥0.70) + T3(EMA±12%) + T4(candle) + HC
Dedup: FIRST_ONLY (20d cooldown per symbol)

Output: ~/Desktop/signals_2026_new_cutoffs.xlsx
"""
from __future__ import annotations
import sys, pickle
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODEL_PATH = ROOT / "data/models/lgbm_model_20d.pkl"
TRAIN_SET  = ROOT / "data/labels/training_set_20d.parquet"
FEAT_DIR   = ROOT / "data/features"
OHLCV_DIR  = ROOT / "data/ohlcv"
OUTPUT_XLS = Path.home() / "Desktop" / "signals_2026_new_cutoffs.xlsx"

WIN_THRESH = 5.0
HOLD_DAYS  = 20
EMA_PCT    = 12.0
TODAY_STR  = "2026-05-23"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _add_n_td(date_str: str, n: int) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    c = 0
    while c < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            c += 1
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


def _get_price(cache: dict, symbol: str, as_of: str) -> float | None:
    s = cache.get(symbol)
    if s is None:
        return None
    sub = s[s.index <= pd.Timestamp(as_of)]
    return float(sub.iloc[-1]) if not sub.empty else None


def _load_sector(symbols: list) -> dict:
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


# ── Build unified dataset ─────────────────────────────────────────────────────

def build_dataset() -> pd.DataFrame:
    print("Loading training set (2026-01 → 2026-04-13) …")
    df_train = pd.read_parquet(TRAIN_SET)
    if "label_valid" in df_train.columns:
        df_train = df_train[df_train["label_valid"] == 1]
    df_train = df_train.reset_index()
    df_train["_date"] = pd.to_datetime(df_train["date"])
    df_train = df_train[df_train["_date"] >= "2026-01-01"].copy()
    df_train["source"] = "training"
    print(f"  {len(df_train):,} rows  |  {df_train['_date'].min().date()} → {df_train['_date'].max().date()}")

    max_train_date = df_train["_date"].max()

    # Feature files supplement
    feat_dates = sorted([
        f.stem for f in FEAT_DIR.glob("2026-*.parquet")
        if pd.Timestamp(f.stem) > max_train_date
    ])
    print(f"\nSupplement feature files: {len(feat_dates)}  ({feat_dates[0] if feat_dates else 'none'} → {feat_dates[-1] if feat_dates else 'none'})")

    obj = pickle.load(open(MODEL_PATH, "rb"))
    model, feat_cols = obj["model"], obj.get("feat_cols", [])

    sup_frames = []
    for date_str in feat_dates:
        p = FEAT_DIR / f"{date_str}.parquet"
        try:
            fdf = pd.read_parquet(p)
            if fdf.index.name == "symbol":
                fdf = fdf.reset_index()
            fdf["date"]   = date_str
            fdf["_date"]  = pd.Timestamp(date_str)
            fdf["source"] = "feature"
            sup_frames.append(fdf)
        except Exception as e:
            print(f"  ⚠️  {date_str}: {e}")

    if sup_frames:
        df_sup = pd.concat(sup_frames, ignore_index=True)
        print(f"  Supplement rows: {len(df_sup):,}")

        # Score supplement
        tmp = df_sup.copy()
        for c in feat_cols:
            if c not in tmp.columns:
                tmp[c] = np.nan
        df_sup["prob"] = model.predict_proba(tmp[feat_cols])[:, 1]
        df = pd.concat([df_train, df_sup], ignore_index=True)
    else:
        df = df_train.copy()

    # Score training rows too
    mask_train = df["source"] == "training"
    tmp2 = df[mask_train].copy()
    for c in feat_cols:
        if c not in tmp2.columns:
            tmp2[c] = np.nan
    df.loc[mask_train, "prob"] = model.predict_proba(tmp2[feat_cols])[:, 1]

    df["date_str"] = df["_date"].dt.strftime("%Y-%m-%d")
    print(f"\nCombined: {len(df):,} rows  |  {df['_date'].min().date()} → {df['_date'].max().date()}")
    return df


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print("=" * 68)
    print("  SIGNAL LIST 2026 — CUTOFF MỚI")
    print("  recovery=0.53 | bull=0.55 | sideways=0.58 | deep_bear=0.58 | choppy=0.58")
    print("=" * 68)

    # ── 1. Data ───────────────────────────────────────────────────────────────
    df = build_dataset()

    # ── 2. Regime detection ───────────────────────────────────────────────────
    print("\nDetecting regime …")
    from pipeline.regime_detector import detect_regime, REGIME_CUTOFFS, REGIME_SIZE_MULT
    from pipeline.phase4b_ml_model_20d import HOLD_DAYS_REGIME, HOLD_DAYS_DEFAULT

    dates_uniq = sorted(df["date_str"].unique())
    regime_map  = {}
    cutoff_map  = {}
    detail_map  = {}
    for d in dates_uniq:
        try:
            reg, cut, det = detect_regime(d)
            regime_map[d]  = reg
            cutoff_map[d]  = cut
            detail_map[d]  = det
        except Exception:
            regime_map[d]  = "sideways"
            cutoff_map[d]  = 0.58
            detail_map[d]  = {}

    df["regime"]     = df["date_str"].map(regime_map)
    df["dyn_cutoff"] = df["date_str"].map(cutoff_map)

    print("\n  Regime distribution (unique days):")
    for reg, cnt in df.groupby("regime")["date_str"].nunique().sort_values(ascending=False).items():
        cut = REGIME_CUTOFFS.get(reg, 0.58)
        print(f"    {reg:<12} {cnt:>3} ngày  cutoff={cut:.2f}")

    # ── 3. Apply T2/T3/T4/HC filters ─────────────────────────────────────────
    print("\nApplying filters …")
    EMA_COLS = [c for c in ["ema20","ema9","ema50","ema26"] if c in df.columns]
    cl = df.get("close_vnd", pd.Series(np.nan, index=df.index))

    near = pd.Series(False, index=df.index)
    for ec in EMA_COLS[:2]:  # short EMA
        e = df[ec]
        near |= e.notna() & (e > 0) & ((cl / e.replace(0, np.nan) - 1).abs() * 100 <= EMA_PCT)
    for ec in EMA_COLS[2:]:  # long EMA fallback
        e = df[ec]
        near |= e.notna() & (e > 0) & ((cl / e.replace(0, np.nan) - 1).abs() * 100 <= EMA_PCT)
    has_ema = df[EMA_COLS].notna().any(axis=1) if EMA_COLS else pd.Series(False, index=df.index)
    t3 = ~has_ema | near

    vr = df.get("vol_ratio_20d", pd.Series(np.nan, index=df.index))
    t2 = vr.isna() | (vr >= 0.70)

    candle_cols = [c for c in ["candle_shooting_star","candle_bearish_engulfing","candle_evening_star"] if c in df.columns]
    t4 = ~(df[candle_cols] == 1).any(axis=1) if candle_cols else pd.Series(True, index=df.index)

    hc = df.get("hardcheck_pass", pd.Series(1, index=df.index)).fillna(0).astype(bool)

    # T1: dynamic cutoff
    t1 = df["prob"] >= df["dyn_cutoff"]

    df["all_pass"] = t1 & t2.values & t3.values & t4.values & hc.values
    passed = df[df["all_pass"]].copy()
    print(f"  Passed all filters: {len(passed):,}")

    filter_breakdown = {
        "T1 fail (prob < cutoff)":  int((~t1).sum()),
        "T2 fail (vol < 0.70)":     int((t1 & ~t2).sum()),
        "T3 fail (EMA distance)":   int((t1 & t2 & ~t3).sum()),
        "T4 fail (bearish candle)": int((t1 & t2 & t3 & ~t4).sum()),
        "HC fail":                  int((t1 & t2 & t3 & t4 & ~hc).sum()),
    }
    for k, v in filter_breakdown.items():
        print(f"    {k:<30}: {v:,}")

    # ── 4. FIRST_ONLY dedup (20d cooldown) ────────────────────────────────────
    print("\nApplying FIRST_ONLY dedup (20d cooldown) …")
    passed = passed.sort_values("date_str").copy()
    last_signal: dict[str, str] = {}
    keep = []
    for _, row in passed.iterrows():
        sym  = row["symbol"]
        dstr = row["date_str"]
        last = last_signal.get(sym)
        if last is None or dstr > _add_n_td(last, HOLD_DAYS):
            keep.append(True)
            last_signal[sym] = dstr
        else:
            keep.append(False)
    passed = passed[keep].copy()
    print(f"  After FIRST_ONLY: {len(passed):,} signals")

    # ── 5. OHLCV & sector ─────────────────────────────────────────────────────
    print("\nLoading OHLCV …")
    all_syms = passed["symbol"].unique().tolist()
    ohlcv    = _load_ohlcv_cache(all_syms)
    sectors  = _load_sector(all_syms)
    print(f"  {len(ohlcv)} symbols loaded")

    # ── 6. Build result rows ──────────────────────────────────────────────────
    today_ts = pd.Timestamp(TODAY_STR)
    rows = []
    for _, row in passed.iterrows():
        sym      = row["symbol"]
        sig_date = row["date_str"]
        regime   = row["regime"]
        hold_d   = HOLD_DAYS_REGIME.get(regime, HOLD_DAYS_DEFAULT)
        cutoff   = row["dyn_cutoff"]
        entry    = row.get("close_vnd", np.nan)
        prob     = round(float(row["prob"]), 4)
        sector   = sectors.get(sym, "Unknown")

        exit_date_td = _add_n_td(sig_date, hold_d)
        is_matured   = exit_date_td <= TODAY_STR

        # Get prices
        exit_px    = _get_price(ohlcv, sym, exit_date_td) if is_matured else None
        current_px = _get_price(ohlcv, sym, TODAY_STR)

        # Returns
        ret_t20     = (exit_px    - entry) / entry * 100 if (exit_px    and np.isfinite(entry) and entry > 0) else None
        ret_current = (current_px - entry) / entry * 100 if (current_px and np.isfinite(entry) and entry > 0) else None

        if is_matured and exit_px:
            status = "✅ WIN (+5%)" if (ret_t20 or 0) >= WIN_THRESH else (
                     "⚠️ Hòa vốn"  if (ret_t20 or 0) >= 0 else "❌ Lỗ")
            result_label = status
        elif is_matured:
            status = "❓ No price"
            result_label = status
        else:
            status = "🔄 Đang mở"
            result_label = status

        rows.append({
            "Tháng":          sig_date[:7],
            "Mã CP":          sym,
            "Sector":         sector,
            "Regime":         regime,
            "Ngày vào":       sig_date,
            "Ngày thoát":     exit_date_td,
            "Hold":           f"T+{hold_d}",
            "Giá vào (VND)":  int(entry) if np.isfinite(entry) else None,
            "Giá thoát (VND)": int(exit_px) if exit_px else None,
            "Giá hiện tại":   int(current_px) if current_px else None,
            "% T+hold":       round(ret_t20, 2)     if ret_t20     is not None else None,
            "% Hiện tại":     round(ret_current, 2) if ret_current is not None else None,
            "Kết quả":        result_label,
            "Prob":           prob,
            "Cutoff":         cutoff,
            "Status":         "closed" if is_matured and exit_px else ("open" if not is_matured else "no_price"),
        })

    rdf = pd.DataFrame(rows)
    print(f"\nTotal signals: {len(rdf):,}")

    # ── 7. Stats ──────────────────────────────────────────────────────────────
    closed = rdf[rdf["Status"] == "closed"].copy()
    open_  = rdf[rdf["Status"] == "open"].copy()
    closed["ret"] = pd.to_numeric(closed["% T+hold"], errors="coerce")

    print("\n" + "=" * 68)
    print("  TỔNG KẾT 2026 — CÁC TÍN HIỆU ĐÃ ĐÓNG")
    print("=" * 68)

    def _pstats(grp: pd.DataFrame, label: str):
        r = pd.to_numeric(grp["% T+hold"], errors="coerce").dropna()
        if len(r) == 0:
            print(f"  {label}: 0 signals")
            return
        wr5 = (r >= WIN_THRESH).mean() * 100
        wr0 = (r >= 0).mean() * 100
        avg = r.mean()
        sh  = avg / r.std() * np.sqrt(252 / HOLD_DAYS) if r.std() > 0 else 0
        sl  = (r <= -10).mean() * 100
        pnl = r.sum() * 100  # 100M/lệnh
        print(f"  {label:<14}  n={len(r):>3}  WR5={wr5:>5.1f}%  WR0={wr0:>5.1f}%  "
              f"avg={avg:>+6.2f}%  Sharpe={sh:>5.2f}  SL={sl:>4.1f}%  "
              f"P&L={pnl:>+8.1f}M VND")

    _pstats(closed, "ALL")
    print()
    for reg in ["recovery","bull","sideways","deep_bear","choppy"]:
        grp = closed[closed["Regime"] == reg]
        if len(grp): _pstats(grp, reg)

    print(f"\n  🔄 Đang mở: {len(open_)} lệnh")
    if not open_.empty:
        for _, r in open_.iterrows():
            pct = f"{r['% Hiện tại']:+.1f}%" if r['% Hiện tại'] is not None else "N/A"
            print(f"    {r['Mã CP']:<5}  {r['Regime']:<12}  vào={r['Ngày vào']}  "
                  f"thoát={r['Ngày thoát']}  hiện tại={pct}")

    # ── 8. By Month ───────────────────────────────────────────────────────────
    print("\n  Theo tháng (đã đóng):")
    for m, g in closed.groupby("Tháng"):
        r = pd.to_numeric(g["% T+hold"], errors="coerce").dropna()
        if len(r) == 0: continue
        wr5 = (r >= WIN_THRESH).mean() * 100
        avg = r.mean()
        print(f"    {m}  n={len(r):>3}  WR5={wr5:>5.1f}%  avg={avg:>+6.2f}%")

    # ── 9. Export Excel ───────────────────────────────────────────────────────
    print(f"\nExporting → {OUTPUT_XLS} …")

    # Summary stats df
    summary_rows = []
    for label, grp in [("ALL", closed)] + [(r, closed[closed["Regime"]==r]) for r in ["recovery","bull","sideways","deep_bear","choppy"]]:
        ret = pd.to_numeric(grp["% T+hold"], errors="coerce").dropna()
        n = len(ret)
        if n == 0:
            summary_rows.append({"Nhóm": label, "N": 0})
            continue
        wr5 = round((ret >= WIN_THRESH).mean() * 100, 1)
        wr0 = round((ret >= 0).mean() * 100, 1)
        avg = round(ret.mean(), 2)
        med = round(ret.median(), 2)
        std = round(ret.std(), 2)
        sh  = round(avg / std * np.sqrt(252 / HOLD_DAYS), 2) if std > 0 else 0
        sl  = round((ret <= -10).mean() * 100, 1)
        pnl = round(ret.sum() * 100, 1)
        summary_rows.append({"Nhóm": label, "N": n,
            "WR≥+5%": wr5, "WR≥0%": wr0, "Avg%": avg, "Median%": med,
            "Sharpe": sh, "SL%": sl, "P&L(M VND)": pnl})
    summary_df = pd.DataFrame(summary_rows)

    # Monthly detail
    monthly_rows = []
    for (month, reg), g in closed.groupby(["Tháng","Regime"]):
        ret = pd.to_numeric(g["% T+hold"], errors="coerce").dropna()
        n = len(ret)
        if n == 0: continue
        monthly_rows.append({"Tháng": month, "Regime": reg, "N": n,
            "WR≥+5%": round((ret>=WIN_THRESH).mean()*100,1),
            "Avg%": round(ret.mean(),2),
            "Sharpe": round(ret.mean()/ret.std()*np.sqrt(252/HOLD_DAYS),2) if ret.std()>0 else 0,
        })
    monthly_df = pd.DataFrame(monthly_rows)

    # Sector summary
    sec_rows = []
    for sec, g in closed.groupby("Sector"):
        ret = pd.to_numeric(g["% T+hold"], errors="coerce").dropna()
        n = len(ret)
        if n < 2: continue
        sec_rows.append({"Sector": sec, "N": n,
            "WR≥+5%": round((ret>=WIN_THRESH).mean()*100,1),
            "WR≥0%": round((ret>=0).mean()*100,1),
            "Avg%": round(ret.mean(),2),
            "Sharpe": round(ret.mean()/ret.std()*np.sqrt(252/HOLD_DAYS),2) if ret.std()>0 else 0,
            "P&L(M VND)": round(ret.sum()*100,1),
        })
    sec_df = pd.DataFrame(sec_rows).sort_values("P&L(M VND)", ascending=False)

    # Cutoff info
    from pipeline.regime_detector import REGIME_CUTOFFS as RC
    cutoff_info = pd.DataFrame([
        {"Regime": k, "Cutoff": v,
         "WR5%(backtest)": {"recovery":71,"bull":57,"sideways":61,"deep_bear":77,"choppy":62}.get(k,"?"),
         "Sharpe(backtest)": {"recovery":4.12,"bull":2.47,"sideways":2.97,"deep_bear":2.40,"choppy":3.52}.get(k,"?"),
         "SL%(backtest)": {"recovery":0.3,"bull":1.0,"sideways":1.1,"deep_bear":8.0,"choppy":0.7}.get(k,"?"),
        } for k,v in RC.items()
    ])

    with pd.ExcelWriter(OUTPUT_XLS, engine="openpyxl") as xw:
        summary_df.to_excel(xw, sheet_name="📊 Tổng kết",     index=False)
        monthly_df.to_excel(xw, sheet_name="📅 Theo tháng",   index=False)
        sec_df.to_excel(    xw, sheet_name="🏭 Theo Sector",  index=False)
        cutoff_info.to_excel(xw,sheet_name="⚙️ Cutoff Config", index=False)
        rdf.sort_values(["Tháng","Ngày vào","Mã CP"]).to_excel(
            xw, sheet_name="📋 All Signals",  index=False)
        if not closed.empty:
            closed.sort_values("Ngày vào").to_excel(
                xw, sheet_name="✅ Đã đóng", index=False)
        if not open_.empty:
            open_.sort_values("Ngày vào").to_excel(
                xw, sheet_name="🔄 Đang mở", index=False)

        # Per-month sheets
        for month, g in rdf.groupby("Tháng"):
            sheet = f"T{month[5:7]}-{month[:4]}"
            g.sort_values("Ngày vào").to_excel(xw, sheet_name=sheet, index=False)

    print(f"\n✅ Saved → {OUTPUT_XLS}")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    run()
