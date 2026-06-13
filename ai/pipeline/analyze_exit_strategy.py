#!/usr/bin/env python3
"""
pipeline/analyze_exit_strategy.py
Analyze and compare exit strategies on historical 20D model signals.
Read-only — does NOT modify any existing files.

Usage:
    python -m pipeline.analyze_exit_strategy
"""

from __future__ import annotations

import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OHLCV_DIR = ROOT / "data" / "ohlcv"
HOLD = 20          # current exit: T+20
MAX_DAYS = 25      # scan a few days beyond T+20


# ─── exit strategy simulators ────────────────────────────────────────────────

def trailing_stop_exit(rets: list, trail_pct: float) -> tuple[int, float]:
    """Exit when price falls trail_pct below its peak during the hold period."""
    peak = 0.0
    for d, r in enumerate(rets[:HOLD]):
        if r > peak:
            peak = r
        if r < peak - trail_pct:
            return d + 1, r
    return HOLD, rets[HOLD - 1]


def profit_target_exit(rets: list, target: float) -> tuple[int, float]:
    """Exit on the first day the return hits the target, else T+20."""
    for d, r in enumerate(rets[:HOLD]):
        if r >= target:
            return d + 1, r
    return HOLD, rets[HOLD - 1]


def combo_exit(rets: list, target: float, trail: float,
               trail_activation: float = 0.03) -> tuple[int, float, str]:
    """
    Exit at whichever comes first:
      1. Price hits +target  (profit take)
      2. Price drops trail_pct from peak AFTER peak > trail_activation  (trailing stop)
    Else exit at T+20.
    """
    peak = 0.0
    for d, r in enumerate(rets[:HOLD]):
        if r >= target:
            return d + 1, r, "target"
        if r > peak:
            peak = r
        if peak >= trail_activation and r < peak - trail:
            return d + 1, r, "trail"
    return HOLD, rets[HOLD - 1], "t20"


def stop_loss_exit(rets: list, stop: float) -> tuple[int, float]:
    """Hard stop-loss: exit immediately if price drops below -stop from entry."""
    for d, r in enumerate(rets[:HOLD]):
        if r <= -stop:
            return d + 1, r
    return HOLD, rets[HOLD - 1]


def combo_sl_exit(rets: list, target: float, trail: float,
                  stop_loss: float, trail_activation: float = 0.03) -> tuple[int, float, str]:
    """Full combo: profit target + trailing stop + hard stop loss."""
    peak = 0.0
    for d, r in enumerate(rets[:HOLD]):
        if r <= -stop_loss:
            return d + 1, r, "stop_loss"
        if r >= target:
            return d + 1, r, "target"
        if r > peak:
            peak = r
        if peak >= trail_activation and r < peak - trail:
            return d + 1, r, "trail"
    return HOLD, rets[HOLD - 1], "t20"


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Loading model and signals...")

    raw = pd.read_parquet(ROOT / "data" / "labels" / "raw_labels_20d.parquet")
    raw = raw.rename(columns={
        "forward_ret_10d":  "forward_ret_20d",
        "max_drawdown_10d": "max_drawdown_20d",
    })

    with open(ROOT / "data" / "models" / "lgbm_model_20d.pkl", "rb") as f:
        payload = pickle.load(f)
    model     = payload["model"]
    feat_cols = payload["feat_cols"]

    ts = pd.read_parquet(ROOT / "data" / "labels" / "training_set_20d.parquet")
    ts = ts[(ts["label_valid"] == 1) & (ts["hardcheck_pass"] == 1)].copy()

    for c in feat_cols:
        if c not in ts.columns:
            ts[c] = 0.0
    ts["prob"] = model.predict_proba(ts[feat_cols].fillna(0))[:, 1]

    signals = ts[ts["prob"] >= 0.50].join(
        raw[["forward_ret_20d", "max_drawdown_20d"]], how="left"
    )
    print(f"Signals at cutoff=0.50: {len(signals):,}")

    # ── build price paths ────────────────────────────────────────────────────
    print("Pre-loading OHLCV files...")
    needed = list({s for s, _ in signals.index})
    ohlcv: dict[str, pd.DataFrame] = {}
    for sym in needed:
        p = OHLCV_DIR / f"{sym}.parquet"
        if p.exists():
            df = pd.read_parquet(p)
            df["time"] = pd.to_datetime(df["time"])
            ohlcv[sym] = df.sort_values("time").reset_index(drop=True)

    print(f"  Loaded {len(ohlcv)} OHLCV files. Building price paths...")

    rows = []
    for sym, date in signals.index:
        df = ohlcv.get(sym)
        if df is None:
            continue
        idx_list = df[df["time"] == pd.Timestamp(date)].index
        if len(idx_list) == 0:
            continue
        i0 = idx_list[0]
        entry = df.loc[i0, "close"]
        future = df.loc[i0 + 1 : i0 + MAX_DAYS].reset_index(drop=True)
        if len(future) < HOLD:
            continue

        rets = [(r["close"] - entry) / entry for _, r in future.iterrows()]

        peak_ret = float(max(rets[:HOLD]))
        peak_day = int(np.argmax(rets[:HOLD])) + 1
        t20_ret  = rets[HOLD - 1]

        ts5_d,  ts5_r  = trailing_stop_exit(rets, 0.05)
        ts8_d,  ts8_r  = trailing_stop_exit(rets, 0.08)
        pt8_d,  pt8_r  = profit_target_exit(rets, 0.08)
        pt10_d, pt10_r = profit_target_exit(rets, 0.10)
        pt12_d, pt12_r = profit_target_exit(rets, 0.12)
        sl7_d,  sl7_r  = stop_loss_exit(rets, 0.07)
        c1_d, c1_r, c1_why = combo_exit(rets, target=0.10, trail=0.05)
        c2_d, c2_r, c2_why = combo_exit(rets, target=0.08, trail=0.05)
        c3_d, c3_r, c3_why = combo_sl_exit(rets, target=0.10, trail=0.05, stop_loss=0.07)
        c4_d, c4_r, c4_why = combo_sl_exit(rets, target=0.08, trail=0.05, stop_loss=0.07)

        rows.append({
            "symbol":   sym,
            "date":     date,
            "t20_ret":  t20_ret,
            "peak_ret": peak_ret,
            "peak_day": peak_day,
            "ts5_ret":  ts5_r,  "ts5_day":  ts5_d,
            "ts8_ret":  ts8_r,  "ts8_day":  ts8_d,
            "pt8_ret":  pt8_r,  "pt8_day":  pt8_d,
            "pt10_ret": pt10_r, "pt10_day": pt10_d,
            "pt12_ret": pt12_r, "pt12_day": pt12_d,
            "sl7_ret":  sl7_r,  "sl7_day":  sl7_d,
            "c1_ret":   c1_r,   "c1_why":   c1_why,
            "c2_ret":   c2_r,   "c2_why":   c2_why,
            "c3_ret":   c3_r,   "c3_why":   c3_why,
            "c4_ret":   c4_r,   "c4_why":   c4_why,
        })

    df = pd.DataFrame(rows)
    n = len(df)
    print(f"  Price paths: {n:,}\n")

    # ── comparison table ──────────────────────────────────────────────────────
    strategies = [
        ("T+20 cố định (hiện tại)",        "t20_ret",  None),
        ("Trailing stop -5% từ peak",       "ts5_ret",  "ts5_day"),
        ("Trailing stop -8% từ peak",       "ts8_ret",  "ts8_day"),
        ("Profit target +8%",              "pt8_ret",  "pt8_day"),
        ("Profit target +10%",             "pt10_ret", "pt10_day"),
        ("Profit target +12%",             "pt12_ret", "pt12_day"),
        ("Hard stop-loss -7%",             "sl7_ret",  "sl7_day"),
        ("Combo: +10% target / -5% trail", "c1_ret",   None),
        ("Combo: +8% target / -5% trail",  "c2_ret",   None),
        ("Combo+SL: +10%/trail-5%/SL-7%",  "c3_ret",   None),
        ("Combo+SL: +8%/trail-5%/SL-7%",   "c4_ret",   None),
    ]

    print("=" * 80)
    print(f"  EXIT STRATEGY COMPARISON  —  {n:,} signals  (cutoff=0.50, hardcheck=True)")
    print("=" * 80)
    print(f"  {'Strategy':<38} {'Avg ret':>8} {'Med ret':>8} {'>0%':>6} {'>+5%':>6} {'Avg day':>7}")
    print(f"  {'-'*38} {'-'*8} {'-'*8} {'-'*6} {'-'*6} {'-'*7}")

    for name, ret_col, day_col in strategies:
        s = df[ret_col]
        avg = s.mean()
        med = s.median()
        pos = (s > 0).mean()
        win5 = (s >= 0.05).mean()
        avg_day = df[day_col].mean() if day_col else HOLD
        marker = "  ◄ CURRENT" if name.startswith("T+20") else ""
        print(f"  {name:<38} {avg:>+7.2%}  {med:>+7.2%}  {pos:>5.1%}  {win5:>5.1%}  {avg_day:>6.1f}{marker}")

    # ── peak analysis ─────────────────────────────────────────────────────────
    print(f"\n{'─'*80}")
    print("  PEAK ANALYSIS (within T+20 window)")
    print(f"{'─'*80}")
    print(f"  Avg peak return:               {df['peak_ret'].mean():+.2%}")
    print(f"  Avg peak day:                  D{df['peak_day'].mean():.1f}")
    print(f"  % peaking ≤ D10:               {(df['peak_day'] <= 10).mean():.1%}")
    print(f"  % peaking ≤ D15:               {(df['peak_day'] <= 15).mean():.1%}")
    print(f"  % peak > +10%:                 {(df['peak_ret'] >= 0.10).mean():.1%}")
    print(f"  % peak > +15%:                 {(df['peak_ret'] >= 0.15).mean():.1%}")
    df["decay"] = df["t20_ret"] - df["peak_ret"]
    print(f"\n  Decay from peak → T+20:")
    print(f"  Avg decay:                     {df['decay'].mean():+.2%}")
    print(f"  % signals lose >3% from peak:  {(df['decay'] < -0.03).mean():.1%}")
    print(f"  % signals lose >5% from peak:  {(df['decay'] < -0.05).mean():.1%}")
    print(f"  % signals lose >8% from peak:  {(df['decay'] < -0.08).mean():.1%}")

    # ── return distribution for best combo vs current ─────────────────────────
    print(f"\n{'─'*80}")
    print("  RETURN DISTRIBUTION: T+20 (current) vs Combo +10%/trail-5%/SL-7% (proposed)")
    print(f"{'─'*80}")
    bins   = [-np.inf, -0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15, 0.20, np.inf]
    lbls   = ["<-15%", "-15~-10%", "-10~-5%", "-5~0%", "0~+5%", "+5~+10%", "+10~+15%", "+15~+20%", ">+20%"]
    t20_d  = pd.cut(df["t20_ret"], bins=bins, labels=lbls).value_counts().reindex(lbls, fill_value=0)
    c3_d   = pd.cut(df["c3_ret"],  bins=bins, labels=lbls).value_counts().reindex(lbls, fill_value=0)
    print(f"  {'Bucket':>12}  {'T+20 N':>7}  {'T+20 %':>7}  {'Combo N':>7}  {'Combo %':>7}")
    for b in lbls:
        t_n, c_n = t20_d[b], c3_d[b]
        print(f"  {b:>12}  {t_n:>7}  {t_n/n*100:>6.1f}%  {c_n:>7}  {c_n/n*100:>6.1f}%")

    # ── combo breakdown ───────────────────────────────────────────────────────
    print(f"\n{'─'*80}")
    print("  COMBO +10%/TRAIL-5%/SL-7% — exit reason breakdown")
    print(f"{'─'*80}")
    for reason, cnt in df["c3_why"].value_counts().items():
        pct = cnt / n * 100
        print(f"  {reason:<12}: {cnt:>5} ({pct:.1f}%)")
    print(f"  Avg day of exit:               D{df['c3_day' if 'c3_day' in df.columns else 'peak_day'].mean():.1f}")

    # ── OOS split ────────────────────────────────────────────────────────────
    df["year"] = pd.to_datetime(df["date"]).dt.year
    oos = df[df["year"] >= 2025]
    if not oos.empty:
        print(f"\n{'─'*80}")
        print(f"  OOS (2025+)  —  {len(oos)} signals")
        print(f"{'─'*80}")
        for name, ret_col, _ in strategies[:4] + strategies[-2:]:
            s = oos[ret_col]
            print(f"  {name:<38} avg={s.mean():+.2%}  >+5%={( s>=0.05).mean():.1%}  n={len(s)}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
