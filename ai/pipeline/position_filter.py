#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/position_filter.py
Position concentration filter — prevents any single stock from exceeding
MAX_CONCENTRATION of the total open portfolio.

Why concentration limit (not pyramid rules):
  Empirical data (OOS 2025-2026, 594 trades) shows:
    - Repeat entries have HIGHER win rate than first entries (64% vs 57%)
    - Entries after price DROP have the HIGHEST win rate (71.4%)
    - Entries after price > +7% have the LOWEST win rate (42.1%)
  → Blocking by entry order or price direction is empirically wrong.
  → The real risk is capital concentration in one stock, not entry count.

Rules:
  1. Block if adding this signal would put >MAX_CONCENTRATION of portfolio in one stock.
  2. Block if current price is >MAX_RUNUP above last entry for this symbol
     (empirically: >7% runup → 42% WR, well below 57% base rate).
  3. Block if symbol was already signaled within last COOLDOWN_DAYS calendar days
     (avoids re-entering the same trade before the holding period expires).
  4. Always allow the very first entry for any symbol (no open positions for it).

Source of truth: data/feedback/signal_log.csv (written by feedback_tracker.py)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

_ROOT       = Path(__file__).resolve().parent.parent
_SIGNAL_LOG = _ROOT / "data" / "feedback" / "signal_log.csv"

MAX_CONCENTRATION = 0.40   # max % of open portfolio in any single stock
MAX_RUNUP         = 0.07   # block if price already ran up >7% since last entry
MIN_PORTFOLIO     = 5      # don't apply concentration rule until portfolio has ≥5 positions
COOLDOWN_DAYS     = 28     # ~20 trading days: block re-entry within this calendar window


def _load_recent_signals(as_of_date: str, lookback_days: int = COOLDOWN_DAYS) -> dict[str, str]:
    """
    Returns {symbol: last_signal_date_str} for signals fired within the last
    `lookback_days` calendar days (any status — pending or closed).
    Used for cooldown check (Rule 3).
    """
    if not _SIGNAL_LOG.exists():
        return {}
    try:
        df = pd.read_csv(_SIGNAL_LOG, dtype=str)
    except Exception as exc:
        log.warning("[position_filter] Cannot read signal_log for cooldown: %s", exc)
        return {}

    cutoff = (datetime.strptime(as_of_date, "%Y-%m-%d") - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    # Keep signals fired within the lookback window (strictly before today)
    recent = df[(df["signal_date"] >= cutoff) & (df["signal_date"] < as_of_date)].copy()
    if recent.empty:
        return {}

    # For each symbol, keep the most recent signal date
    recent = recent.sort_values("signal_date", ascending=False)
    return recent.drop_duplicates("symbol").set_index("symbol")["signal_date"].to_dict()


def _load_open_positions(as_of_date: str) -> pd.DataFrame:
    """
    Returns pending signals whose exit_date > as_of_date.
    Columns: symbol, signal_date, entry_price.
    """
    if not _SIGNAL_LOG.exists():
        return pd.DataFrame(columns=["symbol", "signal_date", "entry_price"])
    try:
        df = pd.read_csv(_SIGNAL_LOG, dtype=str)
    except Exception as exc:
        log.warning("[position_filter] Cannot read signal_log: %s", exc)
        return pd.DataFrame(columns=["symbol", "signal_date", "entry_price"])

    df = df[df["status"] == "pending"].copy()
    df = df[df["exit_date"] > as_of_date].copy()
    df["entry_price"] = pd.to_numeric(df["entry_price"], errors="coerce").fillna(0)
    return df


def apply_position_filter(
    signals: list[dict],
    date_str: str,
    *,
    max_concentration: float = MAX_CONCENTRATION,
    max_runup: float = MAX_RUNUP,
    cooldown_days: int = COOLDOWN_DAYS,
) -> tuple[list[dict], list[dict]]:
    """
    Filter signals by portfolio concentration limit and cooldown window.

    Args:
        signals:           Signal dicts from _score_20d (need 'symbol', 'close_price').
        date_str:          Today's date string (YYYY-MM-DD).
        max_concentration: Max fraction of open portfolio per symbol (default 40%).
        max_runup:         Block if price moved > this % above last entry (default 7%).
        cooldown_days:     Block re-entry if symbol signaled within this many calendar
                           days (default 28 ≈ 20 trading days).

    Returns:
        (allowed, blocked) — blocked signals include a 'filter_reason' key.
    """
    open_df        = _load_open_positions(date_str)
    recent_signals = _load_recent_signals(date_str, lookback_days=cooldown_days)

    total_open = len(open_df)
    counts_by_symbol: dict[str, int] = (
        open_df.groupby("symbol").size().to_dict() if not open_df.empty else {}
    )
    last_price_by_symbol: dict[str, float] = {}
    if not open_df.empty:
        for sym, grp in open_df.groupby("symbol"):
            last_entry = grp.sort_values("signal_date", ascending=False).iloc[0]
            last_price_by_symbol[str(sym)] = float(last_entry["entry_price"])

    allowed: list[dict] = []
    blocked: list[dict] = []

    # Track signals we're adding today so concentration stays accurate
    # as we process multiple signals in the same batch.
    added_today: dict[str, int] = {}

    for sig in signals:
        sym           = sig["symbol"]
        current_price = float(sig.get("close_price") or 0)

        existing_count = counts_by_symbol.get(sym, 0)
        added_count    = added_today.get(sym, 0)
        symbol_total   = existing_count + added_count

        # Denominator: existing open + already-allowed today + this one
        # Use max(total_after, MIN_PORTFOLIO) so a small portfolio (e.g. 1 open
        # position) doesn't artificially inflate concentration percentages.
        total_after     = total_open + sum(added_today.values()) + 1
        symbol_after    = symbol_total + 1
        effective_total = max(total_after, MIN_PORTFOLIO)
        concentration_after = symbol_after / effective_total

        # ── Rule 1: concentration limit ───────────────────────────────────────
        if total_open > 0 and concentration_after > max_concentration:
            blocked.append({
                **sig,
                "filter_reason": (
                    f"concentration {concentration_after:.0%} > {max_concentration:.0%} limit "
                    f"({symbol_total} open + 1 / {effective_total} effective total)"
                ),
            })
            continue

        # ── Rule 2: excessive runup since last entry ───────────────────────────
        last_price = last_price_by_symbol.get(sym)
        if last_price and last_price > 0 and current_price > 0:
            runup = (current_price - last_price) / last_price
            if runup > max_runup:
                blocked.append({
                    **sig,
                    "filter_reason": (
                        f"price runup {runup:+.1%} > {max_runup:.0%} since last entry "
                        f"(WR ~42% empirically)"
                    ),
                })
                continue

        # ── Rule 3: cooldown window ───────────────────────────────────────────
        # Block if this symbol was already signaled within the cooldown window.
        # Prevents re-entering the same trade before the holding period expires.
        if sym in recent_signals:
            last_signal_date = recent_signals[sym]
            days_ago = (
                datetime.strptime(date_str, "%Y-%m-%d")
                - datetime.strptime(last_signal_date, "%Y-%m-%d")
            ).days
            days_left = max(0, cooldown_days - days_ago)
            blocked.append({
                **sig,
                "filter_reason": (
                    f"cooldown: đã signal ngày {last_signal_date} "
                    f"({days_ago} ngày trước), còn ~{days_left} ngày"
                ),
                "cooldown_last_date": last_signal_date,
                "cooldown_days_ago":  days_ago,
                "cooldown_days_left": days_left,
            })
            continue

        allowed.append(sig)
        added_today[sym] = added_today.get(sym, 0) + 1

    if blocked:
        log.info(
            "[position_filter] %d/%d blocked (date=%s). total_open=%d",
            len(blocked), len(signals), date_str, total_open,
        )

    return allowed, blocked


def get_concentration_summary(as_of_date: str) -> dict:
    """
    Returns current portfolio concentration stats for display.
    """
    open_df = _load_open_positions(as_of_date)
    if open_df.empty:
        return {"total_open": 0, "top_symbol": None, "top_count": 0, "top_pct": 0.0}

    total = len(open_df)
    counts = open_df.groupby("symbol").size().sort_values(ascending=False)
    top_sym = counts.index[0]
    top_n   = int(counts.iloc[0])
    return {
        "total_open": total,
        "top_symbol": top_sym,
        "top_count":  top_n,
        "top_pct":    top_n / total,
        "by_symbol":  counts.to_dict(),
    }
