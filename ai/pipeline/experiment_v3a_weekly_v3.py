"""
Experiment v3a with Weekly Timeframe - SIMPLIFIED
Test if weekly signals are cleaner than daily signals

Approach:
  1. Load test data (daily)
  2. Score daily + resample to weekly (take Friday signal)
  3. Compare: WR on 20-day vs WR on weekly
"""

import sys
import pickle
import logging
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

LABELS_DIR = ROOT / "data" / "labels"
MODELS_DIR = ROOT / "data" / "models"

TEST_START = "2025-01-01"
TEST_END = "2026-06-07"
TOP_K = 10


def load_v3a_model():
    """Load v3a model (trained on daily 20-day)."""
    pkl = MODELS_DIR / "v3a" / "lgbm_model_20d.pkl"
    with open(pkl, "rb") as f:
        payload = pickle.load(f)
    return payload["model"], payload["feat_cols"]


def main():
    log.info("=" * 80)
    log.info("EXPERIMENT: v3a Weekly Signals Test")
    log.info("=" * 80)

    # Load data
    ts = pd.read_parquet(LABELS_DIR / "training_set_20d.parquet")
    raw = pd.read_parquet(LABELS_DIR / "raw_labels_20d.parquet")

    raw.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in raw.index], names=["symbol", "date"]
    )
    raw = raw[["forward_ret_10d", "max_drawdown_10d"]].rename(
        columns={"forward_ret_10d": "fwd_ret_20d", "max_drawdown_10d": "max_dd_20d"}
    )
    ts = ts.join(raw, how="left")

    # Model
    model, feat_cols = load_v3a_model()
    log.info(f"Loaded v3a model with {len(feat_cols)} features")

    # Filter test period
    dates = ts.index.get_level_values("date")
    test_df = ts[(dates >= pd.Timestamp(TEST_START)) & (dates <= pd.Timestamp(TEST_END))].copy()
    log.info(f"Test set: {len(test_df)} rows, {test_df.index.get_level_values('date').nunique()} dates\n")

    # Score
    X = test_df[[c for c in feat_cols if c in test_df.columns]].copy()
    for c in [c for c in feat_cols if c not in test_df.columns]:
        X[c] = 0.0
    test_df["prob"] = model.predict_proba(X[feat_cols])[:, 1]

    # ─────────────────────────────────────────────────────────────
    # STRATEGY A: DAILY (baseline)
    # ─────────────────────────────────────────────────────────────

    test_df["date_"] = test_df.index.get_level_values("date")

    daily_signals = []
    for date, grp in test_df.groupby("date_"):
        if len(grp) < TOP_K:
            continue
        top = grp.nlargest(TOP_K, "prob")
        rets = top["fwd_ret_20d"].dropna().values

        if len(rets) == 0:
            continue

        wr = np.mean(rets >= 0.05)
        mean_ret = np.mean(rets)

        daily_signals.append({
            "date": date,
            "n_stocks": len(top),
            "wr": wr,
            "mean_ret": mean_ret,
            "max_ret": np.max(rets),
            "min_ret": np.min(rets),
        })

    df_daily = pd.DataFrame(daily_signals)

    print("\n" + "=" * 80)
    print("A. DAILY SIGNALS (Hold 20 days)")
    print("=" * 80)
    print(f"Total trading days: {len(df_daily)}")
    print(f"WR (ret >= 5%): {df_daily['wr'].mean():.1%}")
    print(f"Mean return: {df_daily['mean_ret'].mean():.2%}")
    print(f"Win rate range: {df_daily['wr'].min():.0%} to {df_daily['wr'].max():.0%}")
    print(f"\nDaily stats:\n{df_daily[['wr', 'mean_ret']].describe()}")

    # ─────────────────────────────────────────────────────────────
    # STRATEGY B: WEEKLY (resample - Friday only)
    # ─────────────────────────────────────────────────────────────

    # Get Friday signals only (end of week)
    test_df_weekly = test_df.copy().reset_index()
    test_df_weekly["weekday"] = test_df_weekly["date"].dt.dayofweek
    test_df_weekly["week"] = test_df_weekly["date"].dt.isocalendar().week
    test_df_weekly["year"] = test_df_weekly["date"].dt.isocalendar().year
    test_df_weekly = test_df_weekly.set_index(["symbol", "date"])

    weekly_signals = []
    for (year, week), grp in test_df_weekly.groupby(["year", "week"]):
        # Get last day of week in group (hopefully Friday)
        last_date = grp.index.get_level_values("date").max()
        grp_last = grp.xs(last_date, level="date")

        if len(grp_last) < TOP_K:
            continue

        top = grp_last.nlargest(TOP_K, "prob")
        rets = top["fwd_ret_20d"].dropna().values

        if len(rets) == 0:
            continue

        # For weekly, approximate 5-day return from 20-day
        rets_5d = rets / 4  # Rough approximation

        wr_5d = np.mean(rets_5d >= 0.01)  # 1% in 5 days
        mean_ret_5d = np.mean(rets_5d)

        weekly_signals.append({
            "date": last_date,
            "n_stocks": len(top),
            "wr_5d": wr_5d,
            "mean_ret_5d": mean_ret_5d,
            "wr_20d": np.mean(rets >= 0.05),  # Also track 20-day
            "mean_ret_20d": np.mean(rets),
        })

    df_weekly = pd.DataFrame(weekly_signals)

    print("\n" + "=" * 80)
    print("B. WEEKLY SIGNALS (Friday only)")
    print("=" * 80)
    print(f"Total weeks: {len(df_weekly)}")
    print(f"WR (ret >= 1% in 5d): {df_weekly['wr_5d'].mean():.1%}")
    print(f"Mean return (5d): {df_weekly['mean_ret_5d'].mean():.2%}")
    print(f"WR (ret >= 5% in 20d): {df_weekly['wr_20d'].mean():.1%}")
    print(f"Mean return (20d): {df_weekly['mean_ret_20d'].mean():.2%}")
    print(f"\nWeekly stats:\n{df_weekly[['wr_5d', 'mean_ret_5d']].describe()}")

    # ─────────────────────────────────────────────────────────────
    # COMPARISON
    # ─────────────────────────────────────────────────────────────

    print("\n" + "=" * 80)
    print("COMPARISON: Daily vs Weekly")
    print("=" * 80)
    print(f"Daily signals/week: {len(df_daily) / (len(df_daily.index) / 5):.1f}")
    print(f"Weekly signals/week: {len(df_weekly) / (len(df_weekly.index) / 5):.1f}")
    print()
    print(f"Daily WR (20d):      {df_daily['wr'].mean():.1%}  (avg {df_daily['wr'].std():.1%} σ)")
    print(f"Weekly WR (5d):      {df_weekly['wr_5d'].mean():.1%}  (avg {df_weekly['wr_5d'].std():.1%} σ)")
    print()
    print(f"Daily mean return:   {df_daily['mean_ret'].mean():+.2%}")
    print(f"Weekly mean return:  {df_weekly['mean_ret_5d'].mean():+.2%}")
    print()
    print("✅ WEEKLY ADVANTAGES:")
    print("   • Fewer signals = less rebalancing/fees")
    print("   • Noise reduction = fewer whipsaws")
    print("   • Longer conviction per position")
    print()
    print("❌ DAILY ADVANTAGES:")
    print("   • More trading opportunities")
    print("   • Faster reaction to market changes")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
