# features/portfolio/price_vn.py
# -*- coding: utf-8 -*-
"""
VN price helpers — thin wrappers over app.vnstock_core.core (Unified UI).
Public API is unchanged so callers (service.py, risk_metrics.py) need no edits.
"""

from typing import Dict, List
import pandas as pd

from app.vnstock_core.core import (
    fetch_last_prices as _fetch_last_prices,
    fetch_close_series as _fetch_close,
    fetch_prices_map as _fetch_prices_map,
    fetch_returns_map as _fetch_returns_map,
)


def fetch_vn_last_prices(symbols: List[str]) -> Dict[str, float]:
    """Latest close price (VND, autoscaled) for each symbol."""
    return _fetch_last_prices(symbols)


def fetch_vn_returns(symbol: str, start: str, end: str) -> pd.Series:
    """Daily return series for a single VN stock."""
    s = _fetch_close(symbol, start, end)
    if s.empty:
        return pd.Series(dtype=float, name=symbol)
    return s.pct_change().dropna().rename(symbol)


def fetch_vn_prices_map(symbols: List[str], lookback_days: int = 420) -> Dict[str, pd.Series]:
    """Close price series for multiple symbols (time-indexed)."""
    return _fetch_prices_map(symbols, lookback_days=lookback_days)


def fetch_vn_returns_map(symbols: List[str], lookback_days: int = 420) -> Dict[str, pd.Series]:
    """Daily return series for multiple symbols."""
    return _fetch_returns_map(symbols, lookback_days=lookback_days)
