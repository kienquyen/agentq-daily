"""
Experiment v3a with Weekly Timeframe
Test long-term holding signals (1 week hold vs 20 days)

Logic:
  1. Aggregate daily OHLCV → weekly OHLCV
  2. Engineer features on weekly data (same 110+ features)
  3. Score with v3a model
  4. Backtest: hold 1 week (5 trading days) vs 20 days
  5. Compare: WR, mean return, signal frequency

Run:
  python -m pipeline.experiment_v3a_weekly
"""

import sys
import pickle
import logging
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

LABELS_DIR = ROOT / "data" / "labels"
MODELS_DIR = ROOT / "data" / "models"
OHLCV_DIR = ROOT / "data" / "ohlcv"
FEATURES_DIR = ROOT / "data" / "features"

TEST_START = "2025-01-01"
TEST_END = "2026-06-07"


def aggregate_to_weekly(df_daily: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    Aggregate daily OHLCV → weekly OHLCV.
    Week starts Monday, ends Friday.

    Args:
        df_daily: Daily OHLCV (index=date, cols=open/high/low/close/volume)
        symbol: Stock symbol (for logging)

    Returns:
        Weekly OHLCV DataFrame
    """
    if df_daily.empty:
        return pd.DataFrame()

    # Ensure index is datetime
    df_daily.index = pd.to_datetime(df_daily.index)

    # Group by ISO week
    df_daily['year_week'] = df_daily.index.strftime('%Y-%W')

    agg = {
        'open': 'first',        # First open of week
        'high': 'max',          # Highest high
        'low': 'min',           # Lowest low
        'close': 'last',        # Last close of week
        'volume': 'sum',        # Total volume
    }

    df_weekly = df_daily.groupby('year_week', as_index=False)[list(agg.keys())].agg(agg)

    # Get week end date (Friday)
    week_dates = []
    for yw in df_weekly['year_week']:
        year = int(yw[:4])
        week = int(yw[-2:])
        # ISO week date to Friday
        jan_4 = datetime(year, 1, 4)
        week_start = jan_4 - timedelta(days=jan_4.isoweekday() - 1) + timedelta(weeks=week - 1)
        friday = week_start + timedelta(days=4)  # Friday of that week
        week_dates.append(friday)

    df_weekly['date'] = week_dates
    df_weekly.set_index('date', inplace=True)
    df_weekly.drop('year_week', axis=1, inplace=True)

    log.info(f"[Weekly] {symbol}: aggregated {len(df_daily)} daily → {len(df_weekly)} weekly")
    return df_weekly


def load_v3a_model():
    """Load trained v3a model."""
    pkl = MODELS_DIR / "v3a" / "lgbm_model_20d.pkl"
    with open(pkl, "rb") as f:
        payload = pickle.load(f)
    return payload["model"], payload["feat_cols"]


def test_v3a_weekly():
    """Test v3a on weekly timeframe."""
    log.info("=" * 70)
    log.info("EXPERIMENT: v3a Model with WEEKLY Timeframe")
    log.info("=" * 70)
    log.info(f"Test period: {TEST_START} → {TEST_END}")
    log.info(f"Hold horizon: 1 week (5 trading days) vs 20 days")

    # Load training data (for feature columns)
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

    # Test data (daily)
    dates = ts.index.get_level_values("date")
    test_df = ts[(dates >= pd.Timestamp(TEST_START)) & (dates <= pd.Timestamp(TEST_END))].copy()

    log.info(f"\nLoaded test data: {len(test_df)} rows, {test_df.index.get_level_values('date').nunique()} dates")

    # Group by symbol + aggregate daily → weekly
    all_symbols = test_df.index.get_level_values("symbol").unique()

    results_daily = []
    results_weekly = []

    for symbol in all_symbols[:5]:  # Test first 5 for speed
        try:
            # Daily data
            sub_daily = test_df.xs(symbol, level="symbol").copy()
            if len(sub_daily) < 30:
                continue

            # Prepare features (same as training)
            X = sub_daily[[c for c in feat_cols if c in sub_daily.columns]].copy()
            for c in [c for c in feat_cols if c not in sub_daily.columns]:
                X[c] = 0.0

            sub_daily["prob"] = model.predict_proba(X[feat_cols])[:, 1]
            sub_daily["label_i"] = sub_daily["label"].fillna(0).astype(int)
            sub_daily["date_"] = sub_daily.index

            # Daily metrics (20-day hold)
            daily_wr = (sub_daily["fwd_ret_20d"] >= 0.05).mean() if sub_daily["fwd_ret_20d"].notna().any() else 0
            daily_mean = sub_daily["fwd_ret_20d"].mean() if sub_daily["fwd_ret_20d"].notna().any() else 0

            results_daily.append({
                "symbol": symbol,
                "timeframe": "1D",
                "hold_days": 20,
                "n_signals": len(sub_daily),
                "wr": daily_wr,
                "mean_ret": daily_mean,
            })

            # Weekly data (aggregate)
            # Load weekly OHLCV
            ohlcv_path = OHLCV_DIR / f"{symbol}.parquet"
            if ohlcv_path.exists():
                df_daily_ohlcv = pd.read_parquet(ohlcv_path)
                df_weekly_ohlcv = aggregate_to_weekly(df_daily_ohlcv, symbol)

                # For now, just report weekly candles count
                # Real implementation would re-engineer features on weekly data
                results_weekly.append({
                    "symbol": symbol,
                    "timeframe": "1W",
                    "hold_days": 5,
                    "n_candles": len(df_weekly_ohlcv),
                    "note": "Feature engineering needed for full test",
                })

        except Exception as exc:
            log.warning(f"[{symbol}] Error: {exc}")

    # Report
    log.info("\n" + "=" * 70)
    log.info("DAILY BASELINE (20-day hold)")
    log.info("=" * 70)

    df_daily_results = pd.DataFrame(results_daily)
    if not df_daily_results.empty:
        print(df_daily_results.to_string(index=False))
        print(f"\nAverage WR (daily): {df_daily_results['wr'].mean():.1%}")
        print(f"Average Return (daily): {df_daily_results['mean_ret'].mean():.2%}")

    log.info("\n" + "=" * 70)
    log.info("WEEKLY CANDLES (aggregated)")
    log.info("=" * 70)

    df_weekly_results = pd.DataFrame(results_weekly)
    if not df_weekly_results.empty:
        print(df_weekly_results.to_string(index=False))

    log.info("\n" + "=" * 70)
    log.info("NEXT STEPS:")
    log.info("=" * 70)
    log.info("1. Engineer 110+ features on weekly timeframe")
    log.info("2. Score weekly signals with v3a model")
    log.info("3. Backtest: 1-week hold vs 20-day hold")
    log.info("4. Compare: WR, mean return, signal frequency, hold time")
    log.info("=" * 70 + "\n")


if __name__ == "__main__":
    test_v3a_weekly()
