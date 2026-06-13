"""Helper Utilities - Shared Functions"""

import json
import re
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd


def safe_ticker(t: str) -> str:
    """Sanitize and validate stock ticker symbol."""
    t = (t or "").strip().upper()
    t = re.sub(r"[^A-Z0-9\.\-\_]", "", t)
    return t[:20]


def pct_short(x: float) -> str:
    """Format percentage for display."""
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{x*100:.1f}%"


def num_short(x: float, nd: int = 2) -> str:
    """Format number for display."""
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{x:.{nd}f}"


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize history df to columns: time(datetime), close(float)."""
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.rename(columns={c: str(c).lower() for c in df.columns})

    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
    elif "date" in df.columns:
        df["time"] = pd.to_datetime(df["date"], errors="coerce")
    elif "tradingdate" in df.columns:
        df["time"] = pd.to_datetime(df["tradingdate"], errors="coerce")
    else:
        raise ValueError("History missing time/date column")

    if "close" not in df.columns:
        if "closeprice" in df.columns:
            df["close"] = df["closeprice"]
        else:
            raise ValueError("History missing close column")

    out = df[["time", "close"]].copy()
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    out = out.dropna(subset=["time", "close"]).sort_values("time").reset_index(drop=True)
    return out


def safe_json_extract(text: str) -> Optional[Dict[str, Any]]:
    """Extract dict JSON from text."""
    if not text:
        return None
    t = text.strip().replace("﻿", "")

    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", t, flags=re.IGNORECASE)
    if m:
        try:
            obj = json.loads(m.group(1))
            return obj if isinstance(obj, dict) else None
        except Exception:
            pass

    dec = json.JSONDecoder()
    for i in range(len(t)):
        if t[i] != "{":
            continue
        try:
            obj, _ = dec.raw_decode(t[i:])
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return None


def today_iso() -> str:
    """Get today's date in ISO format."""
    return pd.Timestamp.now(tz="UTC").date().isoformat()


def month_ago_iso(months: int) -> str:
    """Get date N months ago in ISO format."""
    d = pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=months)
    return d.date().isoformat()
