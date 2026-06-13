# features.portfolio/price_crypto.py
# -*- coding: utf-8 -*-

from typing import Dict, List
import pandas as pd
import requests


def _norm_symbol(sym: str) -> str:
    s = (sym or "").strip().upper()
    # If user inputs "ETH" -> treat as "ETHUSDT"
    if s and not s.endswith("USDT"):
        s = s + "USDT"
    return s


def fetch_binance_last_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Binance last price (spot).
    Returns dict keyed by ORIGINAL input symbol (e.g. "ETH" or "ETHUSDT")
    """
    out: Dict[str, float] = {}
    if not symbols:
        return out

    url = "https://api.binance.com/api/v3/ticker/price"
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
    """
    Daily returns from Binance klines.
    symbol should be like BTCUSDT/ETHUSDT
    """
    url = "https://api.binance.com/api/v3/klines"
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


# ===========================
# v2 wrappers (used by PM Grade Report v2)
# ===========================
# features.portfolio/price_crypto.py
# -*- coding: utf-8 -*-

from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd
import requests

# ... keep your _norm_symbol(), fetch_binance_last_prices(), fetch_binance_returns()

def fetch_crypto_last_prices(symbols: List[str]) -> Dict[str, float]:
    # alias for your current naming in service.py (if you used fetch_crypto_last_prices)
    return fetch_binance_last_prices(symbols)

def fetch_crypto_returns_map(symbols: List[str], lookback_days: int = 420) -> Dict[str, pd.Series]:
    out: Dict[str, pd.Series] = {}
    # Binance limit for 1d klines: we can approximate by min(1000, lookback_days+20)
    limit = min(1000, int(lookback_days) + 30)
    for raw in symbols:
        sym = (raw or "").strip().upper()
        sym_api = sym if sym.endswith("USDT") else (sym + "USDT")
        try:
            r = fetch_binance_returns(sym_api, interval="1d", limit=limit)
            # create a fake date index? your fetch_binance_returns currently returns no datetime index.
            # Better: use prices_map below for calendar NAV, and derive returns with pct_change.
            out[sym_api] = r
        except Exception:
            out[sym_api] = pd.Series(dtype=float, name=sym_api)
    return out

def fetch_crypto_prices_map(symbols: List[str], lookback_days: int = 420) -> Dict[str, pd.Series]:
    """
    Return daily close price series for crypto symbols (e.g., ETHUSDT).
    Index: DatetimeIndex (UTC-naive), values: close (float)
    """
    out: Dict[str, pd.Series] = {}
    if not symbols:
        return out

    url = "https://api.binance.com/api/v3/klines"
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
                columns=["open_time","open","high","low","close","volume","close_time","qv","ntr","tbb","tbq","ignore"],
            )
            df["time"] = pd.to_datetime(df["open_time"], unit="ms", errors="coerce")
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df = df.dropna(subset=["time","close"]).drop_duplicates(subset=["time"]).sort_values("time")

            s = df.set_index("time")["close"].astype(float).rename(sym_api)
            out[sym_api] = s
        except Exception:
            out[sym_api] = pd.Series(dtype=float, name=sym_api)

    return out

