"""
VNStock External Service — thin proxy to app.vnstock_core.core.

Keeps the same public API (fetch_vn_last_prices, fetch_vn_returns,
fetch_vn_returns_map, fetch_vn_prices_map) so portfolio/ callers
require no changes. All data fetching goes through vnstock_data
Unified UI via core.py.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from typing import Dict, List
import pandas as pd

from app.vnstock_core.core import (
    fetch_last_prices as fetch_vn_last_prices,
    fetch_prices_map as fetch_vn_prices_map,
    fetch_returns_map as fetch_vn_returns_map,
    fetch_close_series as _fetch_close,
)


def fetch_vn_returns(symbol: str, start: str, end: str) -> pd.Series:
    """Daily return series for a single VN stock."""
    s = _fetch_close(symbol, start, end)
    if s.empty:
        return pd.Series(dtype=float, name=symbol)
    return s.pct_change().dropna().rename(symbol)
