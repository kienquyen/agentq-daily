"""
Crypto External Service - Binance API Integration
Handles cryptocurrency price data fetching.
"""

from typing import Dict, List, Optional
import pandas as pd
import requests
import os

BINANCE_API_BASE = "https://api.binance.com/api/v3"


def _norm_symbol(sym: str) -> str:
    s = (sym or "").strip().upper()
    if s and not s.endswith("USDT"):
        s = s + "USDT"
    return s


def fetch_crypto_last_prices(symbols: List[str]) -> Dict[str, float]:
    """Fetch last prices from Binance. Returns dict keyed by original symbol."""
    out: Dict[str, float] = {}
    if not symbols:
        return out

    url = f"{BINANCE_API_BASE}/ticker/price"
    for sym in symbols:
        sym_in = (sym or "").strip().upper()
        sym_api = _norm_symbol(sym_in)

        try:
            r = requests.get(url, params={"symbol": sym_api}, timeout=10)
            r.raise_for_status()
            out[sym_in] = float(r.json()["price"])
        except Exception:
            out[sym_in] = 0.0

    return out


def fetch_binance_returns(symbol: str, interval: str = "1d", limit: int = 240) -> pd.Series:
    """Fetch daily returns from Binance klines."""
    url = f"{BINANCE_API_BASE}/klines"
    sym = _norm_symbol(symbol)
    params = {"symbol": sym.upper(), "interval": interval, "limit": int(limit)}

    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame(
        data,
        columns=["time", "open", "high", "low", "close", "volume", "ct", "qv", "ntr", "tbb", "tbq", "ignore"],
    )
    df["time"] = pd.to_datetime(df["time"], unit="ms", errors="coerce")
    df["close"] = df["close"].astype(float)
    df = df.dropna(subset=["time", "close"]).sort_values("time")

    s = df.set_index("time")["close"]
    rets = s.pct_change().dropna().rename(sym.upper())
    return rets


def fetch_crypto_returns_map(symbols: List[str], lookback_days: int = 420) -> Dict[str, pd.Series]:
    """Fetch returns for multiple crypto symbols."""
    out: Dict[str, pd.Series] = {}
    if not symbols:
        return out

    limit = min(1000, int(lookback_days) + 30)

    for raw in symbols:
        sym = (raw or "").strip().upper()
        sym_api = sym if sym.endswith("USDT") else (sym + "USDT")
        try:
            r = fetch_binance_returns(sym_api, interval="1d", limit=limit)
            if not r.empty:
                out[sym_api] = r
        except Exception:
            out[sym_api] = pd.Series(dtype=float, name=sym_api)

    return out


def fetch_crypto_prices_map(symbols: List[str], lookback_days: int = 420) -> Dict[str, pd.Series]:
    """Fetch daily close price series for crypto symbols."""
    out: Dict[str, pd.Series] = {}
    if not symbols:
        return out

    url = f"{BINANCE_API_BASE}/klines"
    limit = min(1000, int(lookback_days) + 30)

    for raw in symbols:
        sym = (raw or "").strip().upper()
        sym_api = sym if sym.endswith("USDT") else (sym + "USDT")
        try:
            params = {"symbol": sym_api, "interval": "1d", "limit": limit}
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()

            df = pd.DataFrame(
                data,
                columns=["time", "open", "high", "low", "close", "volume"] + [f"extra_{i}" for i in range(6)],
            )
            df["time"] = pd.to_datetime(df["time"], unit="ms", errors="coerce")
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df = df.dropna(subset=["time", "close"]).sort_values("time")
            
            s = df.set_index("time")["close"].rename(sym_api)
            out[sym_api] = s
        except Exception:
            out[sym_api] = pd.Series(dtype=float, name=sym_api)

    return out
