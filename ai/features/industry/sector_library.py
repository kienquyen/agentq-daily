"""Industry Sector Library"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(__file__)
CSV_PATH = os.path.join(BASE_DIR, "Industrymap_master.csv")

_industry_cache = None


def _detect_ticker_col(df: pd.DataFrame) -> str:
    cols = {c.lower(): c for c in df.columns}
    for cand in ["ticker", "symbol", "code", "stock_code", "ma", "ma_ck"]:
        if cand in cols:
            return cols[cand]
    return df.columns[0]


def load_industry_map():
    global _industry_cache
    if _industry_cache is not None:
        return _industry_cache

    try:
        df = pd.read_csv(CSV_PATH)
    except Exception:
        _industry_cache = {}
        return _industry_cache

    if df is None or df.empty:
        _industry_cache = {}
        return _industry_cache

    tcol = _detect_ticker_col(df)
    df[tcol] = df[tcol].astype(str).str.upper().str.strip()

    if "primary_sector" not in df.columns:
        df["primary_sector"] = "NA"
    if "model_type" not in df.columns:
        df["model_type"] = "NA"

    _industry_cache = {
        str(row[tcol]).upper().strip(): {
            "primary_sector": row.get("primary_sector", "NA") if pd.notna(row.get("primary_sector", None)) else "NA",
            "model_type": row.get("model_type", "NA") if pd.notna(row.get("model_type", None)) else "NA",
        }
        for _, row in df.iterrows()
        if str(row[tcol]).strip()
    }

    return _industry_cache


def get_sector_info(ticker: str):
    ticker = (ticker or "").upper().strip()
    data = load_industry_map()
    return data.get(ticker, {"primary_sector": "NA", "model_type": "NA"})
