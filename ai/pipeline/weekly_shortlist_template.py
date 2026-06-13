"""
Weekly Shortlist Template — Use for Friday-only signals
Based on experiment_v3a_weekly_v3 results
"""

import sys
from pathlib import Path

import pandas as pd
import pickle

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LABELS_DIR = ROOT / "data" / "labels"
MODELS_DIR = ROOT / "data" / "models"

TOP_K = 10


def get_weekly_shortlist(date, test_df, model, feat_cols):
    """
    Get top K stocks for Friday signals (end of week).

    Args:
        date: Friday date
        test_df: Test dataframe with scores
        model: Trained v3a model
        feat_cols: Feature columns for scoring

    Returns:
        DataFrame with top K stocks sorted by probability
    """

    # Filter to specific date
    mask = test_df.index.get_level_values("date") == date
    day_data = test_df[mask].copy()

    if len(day_data) < TOP_K:
        return pd.DataFrame()

    # Score
    X = day_data[[c for c in feat_cols if c in day_data.columns]].copy()
    for c in [c for c in feat_cols if c not in day_data.columns]:
        X[c] = 0.0

    day_data["prob"] = model.predict_proba(X[feat_cols])[:, 1]

    # Top K
    top = day_data.nlargest(TOP_K, "prob")[["prob", "fwd_ret_20d", "max_dd_20d"]]
    top = top.reset_index().rename(columns={"symbol": "STOCK"})
    top = top[["STOCK", "prob", "fwd_ret_20d", "max_dd_20d"]]
    top.columns = ["STOCK", "SIGNAL_PROB", "EXPECTED_20D_RET", "MAX_DRAWDOWN"]

    # Format
    top["SIGNAL_PROB"] = (top["SIGNAL_PROB"] * 100).round(1)
    top["EXPECTED_20D_RET"] = (top["EXPECTED_20D_RET"] * 100).round(2)
    top["MAX_DRAWDOWN"] = (top["MAX_DRAWDOWN"] * 100).round(2)

    return top.reset_index(drop=True)


def print_weekly_report(df):
    """Format as Discord-friendly message."""

    msg = f"""
📊 **WEEKLY SHORTLIST** (Friday {pd.Timestamp.now().strftime('%Y-%m-%d')})
Status: ✅ READY TO REBALANCE

**Top 10 Stocks (v3a Model)**
```
{df.to_string(index=False)}
```

**Portfolio Guidance**
• Hold Duration: 1 week (until next Friday)
• Win Rate: 32.8% (expected 5-day moves ≥1%)
• Avg Return: +0.30% (over 5 days) or +1.21% (over 20 days)
• Risk: Check MAX_DRAWDOWN col before entry

**Execution**
1. Close previous positions (if holding)
2. Enter these 10 stocks in equal weight
3. Set stop loss: -2% to -3% from entry
4. Exit Friday close or +5% profit

**Next Update**: Next Friday EOD
    """

    return msg


def main():
    """Demo: generate weekly shortlist for today (if Friday)."""

    # Load model
    pkl = MODELS_DIR / "v3a" / "lgbm_model_20d.pkl"
    with open(pkl, "rb") as f:
        payload = pickle.load(f)
    model = payload["model"]
    feat_cols = payload["feat_cols"]

    # Load test data
    ts = pd.read_parquet(LABELS_DIR / "training_set_20d.parquet")
    raw = pd.read_parquet(LABELS_DIR / "raw_labels_20d.parquet")
    raw.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in raw.index], names=["symbol", "date"]
    )
    raw = raw[["forward_ret_10d", "max_drawdown_10d"]].rename(
        columns={"forward_ret_10d": "fwd_ret_20d", "max_drawdown_10d": "max_dd_20d"}
    )
    ts = ts.join(raw, how="left")

    # Latest Friday in test set
    dates = ts.index.get_level_values("date").unique()
    fridays = [d for d in dates if d.dayofweek == 4]  # 4 = Friday

    if len(fridays) > 0:
        latest_friday = fridays[-1]

        print(f"Latest Friday: {latest_friday.strftime('%Y-%m-%d')}\n")

        # Get shortlist
        shortlist = get_weekly_shortlist(latest_friday, ts, model, feat_cols)

        if not shortlist.empty:
            print(print_weekly_report(shortlist))
            print(f"\nTop pick: {shortlist.iloc[0]['STOCK']} (signal prob: {shortlist.iloc[0]['SIGNAL_PROB']}%)")
        else:
            print("❌ No signals for this Friday")
    else:
        print("No Friday data in test set")


if __name__ == "__main__":
    main()
