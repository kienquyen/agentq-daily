"""
Market Data Adapter — delegates to app.vnstock_core.core (vnstock_data Unified UI).

Public API unchanged: fetch_history() and fetch_vnindex().
All data now flows through Market().equity(symbol).ohlcv() instead of
the legacy Quote(symbol).history() pattern.
"""

import os
import sys
from typing import Optional

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.vnstock_core.core import (
    fetch_close_series as _fetch_close,
    fetch_vnindex as _fetch_vnindex,
)


def _normalize_timestamp(series: pd.Series) -> pd.Series:
    """Normalize timestamps to date only (midnight) for proper alignment."""
    if isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index.date)
    return series


def fetch_history(symbol: str, start: str, end: str, interval: str = "1D") -> pd.Series:
    """Historical close prices via vnstock_data Unified UI (Market)."""
    px = _fetch_close(symbol, start, end, interval)
    return _normalize_timestamp(px)


def fetch_vnindex(start: str, end: str, interval: str = "1D") -> pd.Series:
    """VNIndex close series via Market().index('VNINDEX').ohlcv()."""
    px = _fetch_vnindex(start, end, interval)
    return _normalize_timestamp(px)
