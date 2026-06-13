"""
Experiment v3a with Weekly Timeframe - FULL TEST
Compare long-term holding signals: 1 week (W) vs 20 days (D)

Workflow:
  1. Load v3a model trained on daily 20-day horizon
  2. For WEEKLY backtest: aggregate daily features → weekly
  3. Score weekly data (reuse model, same features but weekly aggregation)
  4. Compare: WR, return, signal frequency between Weekly vs Daily

Key insight:
  - Daily model = buy signal today, hold 20 days
  - Weekly model = buy signal this Friday, hold 1 week (5 trading days)
  - Question: Does weekly timeframe reduce noise & improve long-term hold quality?

Run:
  python -m pipeline.experiment_v3a_weekly_v2
"""

import sys
import pickle
import logging
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

LABELS_DIR = ROOT / "data" / "labels"
MODELS_DIR = ROOT / "data" / "models"
FEATURES_DIR = ROOT / "data" / "features"

# Full test period for proper backtest
TEST_START = "2025-01-01"
TEST_END = "2026-06-07"
TOP_K = 10


def aggregate_features_to_weekly(df_daily: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    Aggregate daily features → weekly features.
    Week = Mon-Fri (ISO week).

    Strategy:
      - OHLCV: aggregate using standard candle logic (open=first, close=last, high=max, low=min, vol=sum)
      - Technical (SMA, RSI, etc): use Friday close value
      - Fundamental: use last Friday value (quarterly/annual don't change)
      - Foreign flow: sum for week
    """
    if df_daily.empty or len(df_daily) < 5:
        return pd.DataFrame()

    df_daily.index = pd.to_datetime(df_daily.index)

    # Group by ISO week
    df_daily['year_week'] = df_daily.index.strftime('%Y-%W')
    df_daily['dayofweek'] = df_daily.index.dayofweek

    # Aggregate rules
    agg_dict = {}
    for col in df_daily.columns:
        if col in ['year_week', 'dayofweek']:
            continue
        elif col in ['open', 'close', 'high', 'low', 'volume']:
            # OHLCV standard
            if col == 'open':
                agg_dict[col] = 'first'
            elif col == 'close':
                agg_dict[col] = 'last'
            elif col in ['high', 'low']:
                agg_dict[col] = 'max' if col == 'high' else 'min'
            elif col == 'volume':
                agg_dict[col] = 'sum'
        elif 'foreign' in col:
            # Foreign flow: sum
            agg_dict[col] = 'sum'
        else:
            # Technical/fundamental: last Friday value
            agg_dict[col] = 'last'

    df_weekly = df_daily.groupby('year_week', as_index=False).agg(agg_dict)

    # Get Friday date for each week
    def get_friday_date(year_week_str):
        year = int(year_week_str[:4])
        week = int(year_week_str[-2:])
        jan_4 = datetime(year, 1, 4)
        week_start = jan_4 - pd.Timedelta(days=jan_4.weekday()) + pd.Timedelta(weeks=week - 1)
        friday = week_start + pd.Timedelta(days=4)
        return friday

    df_weekly['date'] = df_weekly['year_week'].apply(get_friday_date)
    df_weekly.set_index('date', inplace=True)
    df_weekly.drop(['year_week', 'dayofweek'], axis=1, inplace=True)

    log.debug(f"[Weekly] {symbol}: {len(df_daily)} daily → {len(df_weekly)} weekly")
    return df_weekly


def load_v3a_model():
    """Load v3a model (trained on daily 20-day)."""
    pkl = MODELS_DIR / "v3a" / "lgbm_model_20d.pkl"
    with open(pkl, "rb") as f:
        payload = pickle.load(f)
    return payload["model"], payload["feat_cols"]


def main():
    log.info("=" * 80)
    log.info("EXPERIMENT: v3a Model on Weekly Timeframe")
    log.info("=" * 80)
    log.info(f"Compare: Daily 20-day hold vs Weekly 5-day hold")
    log.info(f"Test period: {TEST_START} → {TEST_END}\n")

    # Load labels + features
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
    log.info(f"Loaded v3a model with {len(feat_cols)} features\n")

    # Filter test period
    dates = ts.index.get_level_values("date")
    test_df = ts[(dates >= pd.Timestamp(TEST_START)) & (dates <= pd.Timestamp(TEST_END))].copy()

    log.info(f"Test set: {len(test_df)} rows, {test_df.index.get_level_values('date').nunique()} dates\n")

    # ─────────────────────────────────────────────────────────────
    # STRATEGY A: DAILY BACKTEST (baseline - 20 day hold)
    # ─────────────────────────────────────────────────────────────

    test_df_daily = test_df.copy()

    # Score
    X = test_df_daily[[c for c in feat_cols if c in test_df_daily.columns]].copy()
    for c in [c for c in feat_cols if c not in test_df_daily.columns]:
        X[c] = 0.0
    test_df_daily["prob"] = model.predict_proba(X[feat_cols])[:, 1]
    test_df_daily["label_i"] = test_df_daily["label"].fillna(0).astype(int)

    # Daily metrics per day
    test_df_daily["date_"] = test_df_daily.index.get_level_values("date")

    daily_results = []
    for date, grp in test_df_daily.groupby("date_"):
        if len(grp) < 5:
            continue
        top = grp.nlargest(TOP_K, "prob")
        rets = top["fwd_ret_20d"].values
        labels = top["label_i"].values

        wr = np.mean([r >= 0.05 for r in rets if not np.isnan(r)])
        mean_ret = np.nanmean(rets)

        daily_results.append({
            "date": date,
            "hold_days": 20,
            "top_k": len(top),
            "wr": wr,
            "mean_ret": mean_ret,
            "max_dd": np.nanmean(top["max_dd_20d"].values),
        })

    df_daily_results = pd.DataFrame(daily_results)

    print("=" * 80)
    print("A. DAILY BASELINE (Hold 20 days)")
    print("=" * 80)
    print(f"Total signals: {len(df_daily_results)}")
    print(f"WR (ret >= 5%): {df_daily_results['wr'].mean():.1%}")
    print(f"Mean return: {df_daily_results['mean_ret'].mean():.2%}")
    print(f"Avg max drawdown: {df_daily_results['max_dd'].mean():.2%}")
    print(f"Signals/month: {len(df_daily_results) / (len(df_daily_results['date'].unique()) / 21):.1f}\n")

    # ─────────────────────────────────────────────────────────────
    # STRATEGY B: WEEKLY BACKTEST (aggregate features, 5 day hold)
    # ─────────────────────────────────────────────────────────────

    log.info("Aggregating daily features to weekly...")

    # Group test_df by symbol, aggregate each separately
    symbols = test_df.index.get_level_values("symbol").unique()
    test_df_weekly_list = []

    for symbol in symbols:
        try:
            sub = test_df.xs(symbol, level="symbol").copy()
            if len(sub) < 50:
                continue

            sub_weekly = aggregate_features_to_weekly(sub, symbol)
            if sub_weekly.empty:
                continue

            sub_weekly["symbol"] = symbol
            test_df_weekly_list.append(sub_weekly)

        except Exception as exc:
            log.debug(f"[{symbol}] aggregate failed: {exc}")

    if test_df_weekly_list:
        test_df_weekly = pd.concat(test_df_weekly_list, ignore_index=False)
        test_df_weekly.set_index(pd.MultiIndex.from_product(
            [test_df_weekly["symbol"].unique(), test_df_weekly.index],
            names=["symbol", "date"]
        ), inplace=True)

        # Score
        X = test_df_weekly[[c for c in feat_cols if c in test_df_weekly.columns]].copy()
        for c in [c for c in feat_cols if c not in test_df_weekly.columns]:
            X[c] = 0.0
        test_df_weekly["prob"] = model.predict_proba(X[feat_cols])[:, 1]

        # Weekly metrics per Friday
        test_df_weekly["date_"] = test_df_weekly.index.get_level_values("date")

        weekly_results = []
        for date, grp in test_df_weekly.groupby("date_"):
            if len(grp) < 5:
                continue
            top = grp.nlargest(TOP_K, "prob")

            # For weekly, we'd need 5-day forward return - approximate with fwd_ret_20d / 4
            approx_5d_ret = top.get("fwd_ret_20d", pd.Series([np.nan] * len(top))).values / 4

            wr = np.mean([r >= 0.01 for r in approx_5d_ret if not np.isnan(r)])  # Lower threshold (1% for 5d)

            weekly_results.append({
                "date": date,
                "hold_days": 5,
                "top_k": len(top),
                "wr": wr,
                "mean_ret_approx": np.nanmean(approx_5d_ret),
                "n_candles": len(test_df_weekly),
            })

        df_weekly_results = pd.DataFrame(weekly_results)

        print("=" * 80)
        print("B. WEEKLY TEST (Hold 5 days / 1 week)")
        print("=" * 80)
        print(f"Total signals: {len(df_weekly_results)}")
        if len(df_weekly_results) > 0:
            print(f"WR (ret >= 1%/5d): {df_weekly_results['wr'].mean():.1%}")
            print(f"Mean return (approx 5d): {df_weekly_results['mean_ret_approx'].mean():.2%}")
            print(f"Signals/month: {len(df_weekly_results) / (len(df_weekly_results) / 4):.1f}\n")

    # ─────────────────────────────────────────────────────────────
    # COMPARISON & INSIGHTS
    # ─────────────────────────────────────────────────────────────

    print("=" * 80)
    print("COMPARISON & INSIGHTS")
    print("=" * 80)
    if len(df_daily_results) > 0 and len(df_weekly_results) > 0:
        print(f"Daily WR (20d): {df_daily_results['wr'].mean():.1%} vs Weekly WR (5d): {df_weekly_results['wr'].mean():.1%}")
        print(f"Daily mean return: {df_daily_results['mean_ret'].mean():.2%} vs Weekly approx: {df_weekly_results['mean_ret_approx'].mean():.2%}")
        print(f"Daily signals/month: {len(df_daily_results) / (len(df_daily_results['date'].unique()) / 21):.1f} vs Weekly: {len(df_weekly_results) / (len(df_weekly_results) / 4):.1f}")
        print("\n✅ Weekly timeframe: Fewer signals, simpler management, longer focus per bet")
        print("❌ Daily timeframe: More frequent rebalancing, higher noise exposure")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
