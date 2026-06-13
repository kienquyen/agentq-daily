#!/usr/bin/env python3
"""
Step 1: Patch all feature parquets with 8 market-regime interaction features.

Run:
    python -m pipeline.patch_interaction_features
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FEATURES_DIR = ROOT / "data" / "features"

NEW_COLS = [
    "rel_strength_20d",
    "rel_strength_5d",
    "sharpe_x_mkt_vol",
    "momentum_in_bull",
    "bb_spread_vs_mkt",
    "price_pos_vs_mkt",
    "vol_spike_x_mkt",
    "bench_sharpe_x_trend",
]


def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute 8 interaction features.

    Units note: vni_ret_20d, vni_ret_5d, vni_vol_20d are stored as percentages
    (e.g. -2.1, not -0.021). Return/bb_width_pct etc. may be fractional depending
    on how they were computed. We keep units consistent with the existing columns.
    """
    out = df.copy()

    # Relative strength (stock vs market)
    out["rel_strength_20d"] = out["return_20d"] - out["vni_ret_20d"]
    out["rel_strength_5d"] = out["return_5d"] - out["vni_ret_5d"]

    # Quality × volatility environment
    out["sharpe_x_mkt_vol"] = out["sharpe_12m"] * out["vni_vol_20d"]

    # Momentum × market regime gate (RSI 0-100, vni_above_ma50 is 0/1)
    out["momentum_in_bull"] = out["rsi_14"] * out["vni_above_ma50"]

    # Stock vol spread vs market vol
    out["bb_spread_vs_mkt"] = out["bb_width_pct"] - out["vni_vol_20d"]

    # Price position: stock vs market
    out["price_pos_vs_mkt"] = out["price_vs_ema200"] - out["vni_vs_52w_high_pct"]

    # Volume spike in up vs down market context
    out["vol_spike_x_mkt"] = out["vol_spike_ratio"] * (1 + out["vni_ret_5d"] / 100)

    # Best feature (#1 by importance) × market trend gate
    out["bench_sharpe_x_trend"] = out["bench_sharpe_12m"] * out["vni_above_ma50"]

    return out


def check_required_columns(df: pd.DataFrame, filepath: Path) -> list[str]:
    """Return list of missing source columns."""
    required = [
        "return_20d", "return_5d", "rsi_14", "sharpe_12m",
        "bench_sharpe_12m", "bb_width_pct", "price_vs_ema200",
        "vol_spike_ratio", "vni_ret_20d", "vni_ret_5d",
        "vni_vol_20d", "vni_above_ma50", "vni_vs_52w_high_pct",
    ]
    missing = [c for c in required if c not in df.columns]
    return missing


def patch_all_parquets() -> None:
    files = sorted(FEATURES_DIR.glob("????-??-??.parquet"))
    print(f"Found {len(files)} feature parquet files in {FEATURES_DIR}")

    skipped_already_patched = 0
    skipped_missing_cols = 0
    patched = 0
    errors = 0

    for i, fpath in enumerate(files, 1):
        try:
            df = pd.read_parquet(fpath)

            # Skip if already patched
            if "rel_strength_20d" in df.columns:
                skipped_already_patched += 1
                if i % 100 == 0:
                    print(f"  [{i}/{len(files)}] {fpath.name} — already patched (skip)")
                continue

            # Check required source columns
            missing = check_required_columns(df, fpath)
            if missing:
                skipped_missing_cols += 1
                if i % 100 == 0 or i <= 3:
                    print(f"  [{i}/{len(files)}] {fpath.name} — SKIP (missing cols: {missing[:3]})")
                continue

            # Add interaction features
            df = add_interaction_features(df)

            # Save back
            df.to_parquet(fpath, engine="pyarrow", index=True)
            patched += 1

            if i % 100 == 0 or i == len(files):
                print(f"  [{i}/{len(files)}] {fpath.name} — patched OK")

        except Exception as e:
            errors += 1
            print(f"  [{i}/{len(files)}] {fpath.name} — ERROR: {e}")

    print(f"\nDone:")
    print(f"  Patched:               {patched}")
    print(f"  Already patched (skip): {skipped_already_patched}")
    print(f"  Missing cols (skip):    {skipped_missing_cols}")
    print(f"  Errors:                {errors}")


if __name__ == "__main__":
    patch_all_parquets()
