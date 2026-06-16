#!/usr/bin/env python3
"""
experiment_weekly_candle.py
────────────────────────────────────────────────────────────────────────────
Thí nghiệm: Rule-based vs ML trên Weekly OHLCV candle

Pipeline:
  1. Aggregate daily OHLCV → weekly candle (Mon open, week H/L, Fri close, sum vol)
  2. Compute weekly features (EMA, RSI, volume ratio, return momentum)
  3. Label: forward_ret_4w >= +5% AND max_drawdown_4w >= -10%
  4. Backtest Rule-based vs ML (LightGBM) trên 2025–2026
  5. In báo cáo so sánh

Universe : toàn bộ HOSE (data/ohlcv/*.parquet)
Backtest  : 2022–2026 (train 2022-2024, test 2025-2026)

Usage:
  python -m pipeline.experiment_weekly_candle
  python -m pipeline.experiment_weekly_candle --plot   # save charts
"""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import sys
from pathlib import Path
from datetime import timedelta

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OHLCV_DIR  = ROOT / "data" / "ohlcv"
OUT_DIR    = ROOT / "data" / "exports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BACKTEST_START = "2022-01-01"
BACKTEST_END   = "2026-06-13"
TRAIN_END      = "2024-12-31"   # walk-forward split
TEST_START     = "2025-01-01"

FORWARD_WEEKS  = 4
RET_THRESH     = 0.05    # +5%
DD_THRESH      = -0.10   # -10%
PROB_CUTOFF    = 0.55    # ML entry cutoff
TOP_K          = 8       # max signals per week


# ═══════════════════════════════════════════════════════════════════════════
# 1. AGGREGATE DAILY → WEEKLY
# ═══════════════════════════════════════════════════════════════════════════

def load_weekly_ohlcv(symbols: list[str] | None = None) -> pd.DataFrame:
    """
    Load tất cả symbols, aggregate thành weekly candle.
    Returns: MultiIndex DataFrame (date, symbol) với cột OHLCV.
    """
    files = list(OHLCV_DIR.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files in {OHLCV_DIR}")

    frames = []
    for f in files:
        sym = f.stem
        if symbols and sym not in symbols:
            continue
        try:
            df = pd.read_parquet(f)
            df["time"] = pd.to_datetime(df["time"])
            df = df.set_index("time").sort_index()
            df = df[["open", "high", "low", "close", "volume"]].copy()
            df = df[df.index >= BACKTEST_START]
            if len(df) < 100:
                continue

            # Resample to weekly (anchor = Friday close)
            wk = df.resample("W-FRI").agg({
                "open":   "first",
                "high":   "max",
                "low":    "min",
                "close":  "last",
                "volume": "sum",
            }).dropna(subset=["close"])

            wk["symbol"] = sym
            wk.index.name = "date"
            frames.append(wk.reset_index())
        except Exception as e:
            print(f"  ⚠ {sym}: {e}")

    if not frames:
        raise ValueError("No data loaded")

    df_all = pd.concat(frames, ignore_index=True)
    df_all["date"] = pd.to_datetime(df_all["date"])
    df_all = df_all.sort_values(["symbol", "date"]).reset_index(drop=True)
    print(f"  Loaded {df_all['symbol'].nunique()} symbols, "
          f"{df_all['date'].nunique()} weekly bars "
          f"({df_all['date'].min().date()} → {df_all['date'].max().date()})")
    return df_all


# ═══════════════════════════════════════════════════════════════════════════
# 2. WEEKLY FEATURES
# ═══════════════════════════════════════════════════════════════════════════

def add_weekly_features(df: pd.DataFrame) -> pd.DataFrame:
    """Thêm technical features tính trên weekly bars, per symbol."""
    results = []
    for sym, g in df.groupby("symbol"):
        g = g.sort_values("date").copy()
        c = g["close"]
        v = g["volume"]

        # Returns
        g["ret_1w"]  = c.pct_change(1)
        g["ret_4w"]  = c.pct_change(4)
        g["ret_13w"] = c.pct_change(13)

        # EMAs
        g["ema9"]  = c.ewm(span=9,  adjust=False).mean()
        g["ema26"] = c.ewm(span=26, adjust=False).mean()
        g["ema52"] = c.ewm(span=52, adjust=False).mean()

        # EMA cross signals
        g["ema9_above_26"] = (g["ema9"] > g["ema26"]).astype(float)
        g["ema9_cross_up"] = (
            (g["ema9"] > g["ema26"]) & (g["ema9"].shift(1) <= g["ema26"].shift(1))
        ).astype(float)

        # Price vs EMAs
        g["vs_ema9"]  = (c / g["ema9"]  - 1).clip(-0.5, 0.5)
        g["vs_ema26"] = (c / g["ema26"] - 1).clip(-0.5, 0.5)
        g["vs_ema52"] = (c / g["ema52"] - 1).clip(-0.5, 0.5)

        # RSI (14-week)
        delta = c.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, 1e-9)
        g["rsi14"] = (100 - 100 / (1 + rs)).clip(0, 100)

        # Volume features
        g["vol_ma10"]   = v.rolling(10).mean()
        g["vol_ratio"]  = (v / g["vol_ma10"].replace(0, 1)).clip(0, 10)
        g["vol_expand"] = (g["vol_ratio"] > 1.5).astype(float)

        # MACD
        macd_line   = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        g["macd"]         = macd_line
        g["macd_signal"]  = signal_line
        g["macd_hist"]    = macd_line - signal_line
        g["macd_above"]   = (macd_line > signal_line).astype(float)
        g["macd_cross_up"]= (
            (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
        ).astype(float)

        # Volatility (weekly ATR proxy)
        tr = pd.concat([
            g["high"] - g["low"],
            (g["high"] - g["close"].shift(1)).abs(),
            (g["low"]  - g["close"].shift(1)).abs(),
        ], axis=1).max(axis=1)
        g["atr10"] = tr.rolling(10).mean()
        g["atr_pct"] = (g["atr10"] / c).clip(0, 1)

        # Trend strength: % of last 13 weeks closing above ema26
        g["trend_strength"] = (c > g["ema26"]).rolling(13).mean()

        results.append(g)

    out = pd.concat(results, ignore_index=True)
    return out.sort_values(["date", "symbol"]).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════
# 3. LABELS
# ═══════════════════════════════════════════════════════════════════════════

def add_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    label = 1 nếu forward_ret_4w >= +5% AND max_drawdown_4w >= -10%
    """
    results = []
    for sym, g in df.groupby("symbol"):
        g = g.sort_values("date").copy()
        c = g["close"].values
        n = len(c)
        fwd_ret = np.full(n, np.nan)
        fwd_dd  = np.full(n, np.nan)

        for i in range(n - FORWARD_WEEKS):
            ep = c[i]
            window = c[i+1 : i+1+FORWARD_WEEKS]
            if len(window) == 0 or ep <= 0:
                continue
            fwd_ret[i] = (window[-1] - ep) / ep
            fwd_dd[i]  = (window.min() - ep) / ep

        g["forward_ret_4w"] = fwd_ret
        g["max_dd_4w"]      = fwd_dd
        g["label"] = (
            (g["forward_ret_4w"] >= RET_THRESH) &
            (g["max_dd_4w"] >= DD_THRESH)
        ).astype(float)
        g.loc[g["forward_ret_4w"].isna(), "label"] = np.nan
        results.append(g)

    return pd.concat(results, ignore_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# 4A. RULE-BASED SIGNALS (weekly)
# ═══════════════════════════════════════════════════════════════════════════

def rule_signal(row) -> bool:
    """
    Rule-based entry signal trên weekly candle.
    Cần pass tất cả điều kiện:
      R1: EMA9 > EMA26 (uptrend)
      R2: Price trong -5% đến +10% so với EMA9 (không overextend)
      R3: RSI14 trong 45–70 (momentum tốt, không overbought)
      R4: Volume ratio >= 1.2× (volume xác nhận)
      R5: MACD histogram dương (momentum)
      R6: Trend strength >= 0.55 (phần lớn 13 tuần trước đều trên EMA26)
    """
    try:
        r1 = row["ema9_above_26"] == 1
        r2 = -0.05 <= row["vs_ema9"] <= 0.10
        r3 = 45 <= row["rsi14"] <= 70
        r4 = row["vol_ratio"] >= 1.2
        r5 = row["macd_hist"] > 0
        r6 = row["trend_strength"] >= 0.55
        return bool(r1 and r2 and r3 and r4 and r5 and r6)
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# 4B. ML MODEL (LightGBM trên weekly features)
# ═══════════════════════════════════════════════════════════════════════════

FEAT_COLS = [
    "ret_1w", "ret_4w", "ret_13w",
    "ema9_above_26", "ema9_cross_up",
    "vs_ema9", "vs_ema26", "vs_ema52",
    "rsi14",
    "vol_ratio", "vol_expand",
    "macd_above", "macd_cross_up", "macd_hist",
    "atr_pct", "trend_strength",
]


def train_ml_model(train_df: pd.DataFrame):
    try:
        import lightgbm as lgb
    except ImportError:
        print("  ⚠ lightgbm not installed, skipping ML branch")
        return None

    sub = train_df.dropna(subset=FEAT_COLS + ["label"])
    sub = sub[sub["label"].isin([0, 1])]

    X = sub[FEAT_COLS].fillna(0)
    y = sub["label"].astype(int)

    if len(y) < 200:
        print(f"  ⚠ Not enough training samples: {len(y)}")
        return None

    pos_rate = y.mean()
    model = lgb.LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        scale_pos_weight=(1 - pos_rate) / max(pos_rate, 1e-6),
        random_state=42,
        verbose=-1,
    )
    model.fit(X, y)
    print(f"  Trained on {len(y)} samples | pos_rate={pos_rate:.1%}")
    return model


# ═══════════════════════════════════════════════════════════════════════════
# 5. BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def backtest(signals_by_week: dict[str, list[dict]], df: pd.DataFrame, strategy_name: str) -> pd.DataFrame:
    """
    Simulate trades:
    - Enter at close ngày T6 signal
    - Hold 4 weeks (exit at close T+4w)
    - Check max drawdown trong window
    Returns DataFrame of trades.
    """
    # Build price lookup: symbol → date → close
    price_map: dict[str, pd.Series] = {}
    for sym, g in df.groupby("symbol"):
        price_map[sym] = g.set_index("date")["close"]

    all_dates = sorted(df["date"].unique())

    trades = []
    for entry_date_str, sigs in sorted(signals_by_week.items()):
        entry_date = pd.Timestamp(entry_date_str)

        for sig in sigs:
            sym = sig["symbol"]
            if sym not in price_map:
                continue
            prices = price_map[sym]

            ep_series = prices[prices.index == entry_date]
            if ep_series.empty:
                continue
            ep = float(ep_series.iloc[0])

            # Get next FORWARD_WEEKS prices
            fut = prices[prices.index > entry_date].head(FORWARD_WEEKS)
            if len(fut) < FORWARD_WEEKS:
                # Incomplete — compute partial if at least 1 bar
                if fut.empty:
                    continue
                # Mark as pending — skip for completed-only stats
                continue

            exit_p   = float(fut.iloc[-1])
            exit_date = fut.index[-1]
            ret_pct  = (exit_p - ep) / ep * 100
            max_dd   = (fut.min() - ep) / ep * 100

            trades.append({
                "strategy":   strategy_name,
                "symbol":     sym,
                "entry_date": entry_date,
                "exit_date":  exit_date,
                "entry_price": ep,
                "exit_price":  exit_p,
                "return_pct":  round(ret_pct, 2),
                "max_dd_pct":  round(max_dd, 2),
                "is_win":      ret_pct > 0,
                "hit_target":  ret_pct >= 5.0 and max_dd >= -10.0,
                "prob":        sig.get("prob"),
            })

    return pd.DataFrame(trades)


# ═══════════════════════════════════════════════════════════════════════════
# 6. MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot", action="store_true", help="Save comparison chart")
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols (default: all)")
    args = parser.parse_args()

    top_k = args.top_k
    syms = args.symbols.split(",") if args.symbols else None

    print("=" * 60)
    print("Weekly Candle Experiment — Rule-based vs ML")
    print("=" * 60)

    # ── 1. Load & aggregate ──────────────────────────────────────────────
    print("\n[1] Loading & aggregating to weekly OHLCV...")
    df = load_weekly_ohlcv(syms)

    # ── 2. Features ──────────────────────────────────────────────────────
    print("\n[2] Computing weekly features...")
    df = add_weekly_features(df)

    # ── 3. Labels ────────────────────────────────────────────────────────
    print("\n[3] Computing labels (forward_ret_4w >= +5%, dd >= -10%)...")
    df = add_labels(df)

    label_sub = df.dropna(subset=["label"])
    overall_pos = label_sub["label"].mean()
    print(f"  Label positive rate: {overall_pos:.1%}  ({int(label_sub['label'].sum())} / {len(label_sub)} samples)")

    # ── 4. Split ─────────────────────────────────────────────────────────
    train_df = df[df["date"] <= TRAIN_END].copy()
    test_df  = df[(df["date"] >= TEST_START) & (df["date"] <= BACKTEST_END)].copy()
    print(f"\n  Train: {BACKTEST_START} → {TRAIN_END}  ({train_df['date'].nunique()} weeks)")
    print(f"  Test : {TEST_START} → {BACKTEST_END}  ({test_df['date'].nunique()} weeks)")

    # ── 4A. Rule-based signals ───────────────────────────────────────────
    print("\n[4A] Generating rule-based signals on test set...")
    rule_signals_by_week: dict[str, list[dict]] = {}
    for date, g in test_df.groupby("date"):
        valid = g.dropna(subset=FEAT_COLS)
        hits = valid[valid.apply(rule_signal, axis=1)].copy()
        # Sort by RSI proximity to 55 (sweet spot) + volume
        hits["_score"] = hits["vol_ratio"] * hits["trend_strength"]
        hits = hits.nlargest(top_k, "_score")
        if not hits.empty:
            date_str = str(date)[:10]
            rule_signals_by_week[date_str] = hits[["symbol"]].assign(prob=None).to_dict("records")

    total_rule_sigs = sum(len(v) for v in rule_signals_by_week.values())
    print(f"  Rule signals: {total_rule_sigs} total across {len(rule_signals_by_week)} weeks "
          f"(avg {total_rule_sigs/max(len(rule_signals_by_week),1):.1f}/week)")

    # ── 4B. ML signals ───────────────────────────────────────────────────
    print("\n[4B] Training ML model (LightGBM)...")
    model = train_ml_model(train_df)

    ml_signals_by_week: dict[str, list[dict]] = {}
    if model is not None:
        print("  Generating ML signals on test set...")
        for date, g in test_df.groupby("date"):
            valid = g.dropna(subset=FEAT_COLS).copy()
            if valid.empty:
                continue
            X = valid[FEAT_COLS].fillna(0)
            probs = model.predict_proba(X)[:, 1]
            valid = valid.copy()
            valid["prob"] = probs
            hits = valid[valid["prob"] >= PROB_CUTOFF].nlargest(top_k, "prob")
            if not hits.empty:
                date_str = str(date)[:10]
                ml_signals_by_week[date_str] = hits[["symbol", "prob"]].to_dict("records")

        total_ml_sigs = sum(len(v) for v in ml_signals_by_week.values())
        print(f"  ML signals: {total_ml_sigs} total across {len(ml_signals_by_week)} weeks "
              f"(avg {total_ml_sigs/max(len(ml_signals_by_week),1):.1f}/week)")

    # ── 5. Backtest ──────────────────────────────────────────────────────
    print("\n[5] Running backtests...")
    trades_rule = backtest(rule_signals_by_week, test_df, "Rule-based")
    trades_ml   = backtest(ml_signals_by_week,   test_df, "ML (LightGBM)") if model else pd.DataFrame()

    # ── 6. Report ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESULTS — Test period: 2025–2026")
    print("=" * 60)

    def report(trades: pd.DataFrame, name: str):
        if trades.empty:
            print(f"\n{name}: No trades")
            return
        n          = len(trades)
        wr         = trades["is_win"].mean() * 100
        avg_ret    = trades["return_pct"].mean()
        med_ret    = trades["return_pct"].median()
        hit_target = trades["hit_target"].mean() * 100
        best       = trades["return_pct"].max()
        worst      = trades["return_pct"].min()
        avg_dd     = trades["max_dd_pct"].mean()

        # Sharpe (weekly returns, annualize × sqrt(52))
        std = trades["return_pct"].std()
        sharpe = (avg_ret / std * (52 ** 0.5)) if std > 0 else 0

        # By year
        trades["year"] = pd.to_datetime(trades["entry_date"]).dt.year
        by_year = trades.groupby("year").agg(
            n=("return_pct", "count"),
            wr=("is_win", lambda x: f"{x.mean()*100:.0f}%"),
            avg=("return_pct", lambda x: f"{x.mean():+.1f}%"),
        )

        print(f"\n{'─'*40}")
        print(f"  {name}")
        print(f"{'─'*40}")
        print(f"  Trades         : {n}")
        print(f"  Win rate       : {wr:.1f}%")
        print(f"  Hit target(+5%): {hit_target:.1f}%")
        print(f"  Avg return     : {avg_ret:+.2f}%")
        print(f"  Median return  : {med_ret:+.2f}%")
        print(f"  Best / Worst   : {best:+.1f}% / {worst:+.1f}%")
        print(f"  Avg drawdown   : {avg_dd:.1f}%")
        print(f"  Sharpe (ann.)  : {sharpe:.2f}")
        print(f"\n  By year:")
        print(by_year.to_string())

        # Top 10 winners
        top10 = trades.nlargest(5, "return_pct")[["symbol","entry_date","return_pct","max_dd_pct"]]
        print(f"\n  Top 5 wins:")
        print(top10.to_string(index=False))

    report(trades_rule, "Rule-based (Weekly)")
    report(trades_ml,   "ML — LightGBM (Weekly)")

    # ── Compare side by side ─────────────────────────────────────────────
    if not trades_rule.empty and not trades_ml.empty:
        print(f"\n{'═'*60}")
        print("COMPARISON SUMMARY")
        print(f"{'═'*60}")
        print(f"  {'Metric':<20} {'Rule-based':>14} {'ML (LightGBM)':>15}")
        print(f"  {'-'*49}")

        def fmt(t, col, fn=None):
            if t.empty: return "N/A"
            return fn(t[col]) if fn else str(t[col])

        rows = [
            ("Trades",         len(trades_rule),                    len(trades_ml)),
            ("Win rate",       f"{trades_rule['is_win'].mean()*100:.1f}%",
                               f"{trades_ml['is_win'].mean()*100:.1f}%"),
            ("Hit +5% target", f"{trades_rule['hit_target'].mean()*100:.1f}%",
                               f"{trades_ml['hit_target'].mean()*100:.1f}%"),
            ("Avg return",     f"{trades_rule['return_pct'].mean():+.2f}%",
                               f"{trades_ml['return_pct'].mean():+.2f}%"),
            ("Median return",  f"{trades_rule['return_pct'].median():+.2f}%",
                               f"{trades_ml['return_pct'].median():+.2f}%"),
            ("Avg drawdown",   f"{trades_rule['max_dd_pct'].mean():.1f}%",
                               f"{trades_ml['max_dd_pct'].mean():.1f}%"),
        ]
        for label, rv, mv in rows:
            print(f"  {label:<20} {str(rv):>14} {str(mv):>15}")

    # ── Save trades ──────────────────────────────────────────────────────
    out_path = OUT_DIR / "weekly_experiment_results.csv"
    pd.concat([trades_rule, trades_ml]).to_csv(out_path, index=False)
    print(f"\n✅ Results saved → {out_path.name}")

    if args.plot:
        _plot_results(trades_rule, trades_ml)


def _plot_results(trades_rule: pd.DataFrame, trades_ml: pd.DataFrame):
    try:
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mtick

        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle("Weekly Candle Experiment — Rule-based vs ML (2025–2026)", fontsize=13)

        # 1. Return distribution
        ax = axes[0]
        bins = np.linspace(-30, 30, 31)
        ax.hist(trades_rule["return_pct"], bins=bins, alpha=0.6, label="Rule-based", color="#3B82F6")
        ax.hist(trades_ml["return_pct"],   bins=bins, alpha=0.6, label="ML",         color="#22C55E")
        ax.axvline(0, color="gray", linestyle="--", linewidth=0.8)
        ax.set_title("Return Distribution")
        ax.set_xlabel("Return %")
        ax.legend()

        # 2. Cumulative P&L (equal-weight per signal)
        ax = axes[1]
        for trades, label, color in [
            (trades_rule, "Rule-based", "#3B82F6"),
            (trades_ml,   "ML",         "#22C55E"),
        ]:
            t = trades.sort_values("entry_date").copy()
            t["cumret"] = (1 + t["return_pct"] / 100).cumprod()
            ax.plot(range(len(t)), t["cumret"], label=label, color=color)
        ax.axhline(1, color="gray", linestyle="--", linewidth=0.8)
        ax.set_title("Cumulative Return (equal-weight)")
        ax.set_xlabel("Trade #")
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1))
        ax.legend()

        # 3. Win rate by year
        ax = axes[2]
        years = sorted(set(
            pd.to_datetime(trades_rule["entry_date"]).dt.year.tolist() +
            pd.to_datetime(trades_ml["entry_date"]).dt.year.tolist()
        ))
        x = np.arange(len(years))
        w = 0.35
        wr_rule = [trades_rule[pd.to_datetime(trades_rule["entry_date"]).dt.year == y]["is_win"].mean() * 100
                   if y in pd.to_datetime(trades_rule["entry_date"]).dt.year.values else 0 for y in years]
        wr_ml   = [trades_ml[pd.to_datetime(trades_ml["entry_date"]).dt.year == y]["is_win"].mean() * 100
                   if y in pd.to_datetime(trades_ml["entry_date"]).dt.year.values else 0 for y in years]
        ax.bar(x - w/2, wr_rule, w, label="Rule-based", color="#3B82F6", alpha=0.8)
        ax.bar(x + w/2, wr_ml,   w, label="ML",         color="#22C55E", alpha=0.8)
        ax.axhline(50, color="gray", linestyle="--", linewidth=0.8)
        ax.set_xticks(x); ax.set_xticklabels(years)
        ax.set_title("Win Rate by Year")
        ax.set_ylabel("%")
        ax.legend()

        plt.tight_layout()
        chart_path = OUT_DIR / "weekly_experiment_chart.png"
        plt.savefig(chart_path, dpi=150, bbox_inches="tight")
        print(f"📊 Chart saved → {chart_path.name}")

    except ImportError:
        print("  ⚠ matplotlib not installed, skipping chart")


if __name__ == "__main__":
    main()
