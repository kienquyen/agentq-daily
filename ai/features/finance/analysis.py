#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Finance Analysis — updated for vnstock_data Unified UI (v3.0.0+).

Actual data format returned by Fundamental().equity(symbol).*:
  Each DataFrame has a 'period' column ("YYYY-QX") and a 'ticker' column,
  followed by financial metric columns named by their item_ids.
  One row per period (transposed vs. the old wide format).

  income_statement (bank):  period, ticker, i_net_interest_income,
                             x_provision_for_credit_losses, xiii_net_profit_after_tax, ...
  income_statement (non-bank): period, ticker, 3_net_revenue, 5_gross_profit,
                             11_operating_profit, 18_net_profit_after_tax, ...
  balance_sheet (bank):     period, ticker, total_assets, iii_deposits_from_customers,
                             1_loans_advances_and_finance_leases_to_customers, viii_capital_and_reserves, ...
  balance_sheet (non-bank): period, ticker, total_assets, b_owner_s_equity,
                             i_short_term_liabilities, ii_long_term_liabilities, ...
  cash_flow:                period, ticker, net_cash_flows_from_operating_activities,
                             net_cash_flows_from_investing_activities,
                             net_cash_flows_from_financing_activities,
                             net_cash_flows_during_the_period, ...
  ratio:                    period, ticker, p_e, p_b, trailing_eps,
                             roe, roe_trailling, roa, roa_trailling, ...
"""

from typing import Optional, List, Tuple

import numpy as np
import pandas as pd
import discord

from dataclasses import dataclass

from app.utils.helpers import safe_ticker
from app.vnstock_core.core import (
    fetch_income_statement,
    fetch_balance_sheet,
    fetch_ratio,
    fetch_cash_flow,
)


@dataclass
class Task2Result:
    ticker: str
    company_type: str
    periods: List[str]
    income_snapshot: str
    balance_snapshot: str
    cash_snapshot: str
    valuation_snapshot: str


# ─── Value formatters ────────────────────────────────────────────────────────


def _to_float(x) -> Optional[float]:
    try:
        v = float(pd.to_numeric(x, errors="coerce"))
        return v if np.isfinite(v) else None
    except Exception:
        return None


def _to_ty_vnd(x: Optional[float]) -> Optional[float]:
    """Convert raw value (normalized VND) → tỷ VND for display."""
    return None if x is None else x / 1e9


def _fmt_ty(x: Optional[float], nd: int = 0) -> str:
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{x:,.{nd}f}"


def _fmt_pct(x: Optional[float], nd: int = 2) -> str:
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{x:.{nd}f}%"


def _fmt_num(x: Optional[float], nd: int = 2) -> str:
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{x:.{nd}f}"


# ─── DataFrame helpers (period-row format) ───────────────────────────────────


def _sort_key(p: str) -> Tuple[int, int]:
    """Convert 'YYYY-QX' to (year, quarter) for sorting."""
    try:
        y, q = p.split("-Q")
        return int(y), int(q)
    except Exception:
        return 0, 0


def _latest_rows(df: pd.DataFrame, n: int = 4) -> pd.DataFrame:
    """Return the last n rows sorted ascending by 'period' column/index."""
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    if "period" in df.columns:
        df["_sort"] = df["period"].apply(_sort_key)
        df = df.sort_values("_sort").drop(columns=["_sort"])
    elif df.index.name == "period":
        # period is the index name, extract and sort by it
        df = df.copy()
        df["_period_idx"] = df.index
        df["_sort"] = df["_period_idx"].apply(_sort_key)
        df = df.sort_values("_sort").drop(columns=["_sort", "_period_idx"])
        df = df.reset_index()
    return df.tail(n).reset_index(drop=True)


def _get_periods(df: pd.DataFrame, n: int = 4) -> List[str]:
    """Extract 'YYYY-QX' period labels from the last n rows."""
    rows = _latest_rows(df, n)
    if rows.empty or "period" not in rows.columns:
        return []
    return rows["period"].tolist()


def _col_val(row: pd.Series, col: str) -> Optional[float]:
    """Safely get a float from a DataFrame row by column name."""
    if col not in row.index:
        return None
    return _to_float(row[col])


# ─── Company type detection ───────────────────────────────────────────────────

_BANK_INCOME_COLS = {"nii"}
_BANK_BALANCE_COLS = {"deposits", "loans"}


def _detect_company_type(income: pd.DataFrame, balance: pd.DataFrame) -> str:
    for col in _BANK_INCOME_COLS:
        if income is not None and col in income.columns and income[col].notna().any():
            return "BANK"
    for col in _BANK_BALANCE_COLS:
        if (
            balance is not None
            and col in balance.columns
            and balance[col].notna().any()
        ):
            return "BANK"
    return "NON_BANK"


# ─── Snapshot builders ────────────────────────────────────────────────────────


def _snapshot_money(
    df: pd.DataFrame,
    col_map: List[Tuple[str, str]],  # [(display_label, column_name), ...]
    n: int = 4,
) -> str:
    rows = _latest_rows(df, n)
    if rows.empty:
        return "NA"
    lines = []
    for i in range(len(rows)):
        row = rows.iloc[i]
        period = row.get("period", "???") if "period" in row.index else "???"
        pairs = [
            (label, _fmt_ty(_to_ty_vnd(_col_val(row, col)))) for label, col in col_map
        ]
        lines.append(f"- {period}: " + " | ".join(f"{k} {v}" for k, v in pairs))
    return "\n".join(lines)


def _snapshot_bank_balance(balance: pd.DataFrame, n: int = 4) -> str:
    rows = _latest_rows(balance, n)
    if rows.empty:
        return "NA"
    lines = []
    for i in range(len(rows)):
        row = rows.iloc[i]
        period = row.get("period", "???") if "period" in row.index else "???"
        assets = _col_val(row, "total_assets")
        dep = _col_val(row, "deposits")
        loans = _col_val(row, "loans")
        ldr = (loans / dep) if loans and dep else None
        pairs = [
            ("Assets", _fmt_ty(_to_ty_vnd(assets))),
            ("Deposits", _fmt_ty(_to_ty_vnd(dep))),
            ("Loans", _fmt_ty(_to_ty_vnd(loans))),
            ("LDR", _fmt_pct(ldr * 100 if ldr else None)),
        ]
        lines.append(f"- {period}: " + " | ".join(f"{k} {v}" for k, v in pairs))
    return "\n".join(lines)


def _snapshot_valuation(
    ratio: pd.DataFrame, income: pd.DataFrame = None, n: int = 4
) -> str:
    rows = _latest_rows(ratio, n)
    if rows.empty:
        return "NA"

    # Get EPS from income statement if not in ratio
    eps_from_income = {}
    if income is not None and "eps" in income.columns:
        inc_rows = _latest_rows(income, n)
        for _, row in inc_rows.iterrows():
            period = row.get("period", "???") if "period" in row.index else "???"
            eps_from_income[period] = _col_val(row, "eps")

    lines = []
    for i in range(len(rows)):
        row = rows.iloc[i]
        period = row.get("period", "???") if "period" in row.index else "???"
        pe = _col_val(row, "pe")
        pb = _col_val(row, "pb")
        eps = _col_val(row, "eps") or eps_from_income.get(period)
        roe = _col_val(row, "roe")
        roa = _col_val(row, "roa")
        pairs = [
            ("P/E", _fmt_num(pe)),
            ("P/B", _fmt_num(pb)),
            ("EPS", _fmt_num(eps)),
            ("ROE", _fmt_pct(roe)),
            ("ROA", _fmt_pct(roa)),
        ]
        lines.append(f"- {period}: " + " | ".join(f"{k} {v}" for k, v in pairs))
    return "\n".join(lines)


# ─── Main compute ─────────────────────────────────────────────────────────────


async def compute_task2(ticker: str) -> Task2Result:
    income = fetch_income_statement(ticker, period="Q")
    balance = fetch_balance_sheet(ticker, period="Q")
    ratio = fetch_ratio(ticker, period="Q")
    cash = fetch_cash_flow(ticker, period="Q")

    ctype = _detect_company_type(income, balance)

    periods = _get_periods(income) or _get_periods(balance) or _get_periods(ratio)

    if ctype == "BANK":
        income_snap = _snapshot_money(
            income,
            [
                ("NII", "nii"),
                ("Fee", "fee_income"),
                ("Provision", "provision"),
                ("NPAT", "net_profit"),
            ],
        )
        balance_snap = _snapshot_bank_balance(balance)
    else:
        income_snap = _snapshot_money(
            income,
            [
                ("Revenue", "revenue"),
                ("Gross", "gross_profit"),
                ("Op", "op_profit"),
                ("NPAT", "net_profit"),
            ],
        )
        balance_snap = _snapshot_money(
            balance,
            [
                ("Assets", "total_assets"),
                ("Equity", "equity"),
                ("ST Liab", "current_liabilities"),
                ("LT Liab", "long_term_liabilities"),
            ],
        )

    cash_snap = _snapshot_money(
        cash,
        [
            ("CFO", "operating_cf"),
            ("CFI", "investing_cf"),
            ("CFF", "financing_cf"),
            ("NetCF", "net_cf"),
        ],
    )

    valuation_snap = _snapshot_valuation(ratio, income)

    return Task2Result(
        ticker=ticker,
        company_type=ctype,
        periods=periods,
        income_snapshot=income_snap,
        balance_snapshot=balance_snap,
        cash_snapshot=cash_snap,
        valuation_snapshot=valuation_snap,
    )


def build_task2_embed(res: Task2Result) -> discord.Embed:
    period_str = ", ".join(res.periods) if res.periods else "N/A"
    emb = discord.Embed(
        title=f"(2) Finance Analysis — {res.ticker} | {res.company_type}",
        description=f"Đơn vị tiền: **tỷ VND** | 4 quý gần nhất: **{period_str}**",
    )
    emb.add_field(
        name="1) Income (4Q snapshot)", value=res.income_snapshot or "NA", inline=False
    )
    emb.add_field(
        name="2) Balance (4Q snapshot)",
        value=res.balance_snapshot or "NA",
        inline=False,
    )
    emb.add_field(
        name="3) Cashflow (4Q snapshot)", value=res.cash_snapshot or "NA", inline=False
    )
    emb.add_field(
        name="4) Valuation & ratios (4Q)",
        value=res.valuation_snapshot or "NA",
        inline=False,
    )
    src = getattr(res, "_source", None) or "KBS→VCI fallback"
    emb.set_footer(
        text=f"Unified UI — Fundamental().equity(symbol) | Data source: {src}"
    )
    return emb


async def handle_task2(interaction, ticker: str) -> None:
    try:
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
        except Exception:
            pass

        ticker = safe_ticker(ticker)

        await interaction.followup.send("📊 Đang phân tích tài chính…", ephemeral=False)
        res = await compute_task2(ticker)
        emb = build_task2_embed(res)
        await interaction.followup.send(embed=emb, ephemeral=False)
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi phân tích: {e}", ephemeral=False)
