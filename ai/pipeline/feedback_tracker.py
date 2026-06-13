#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/feedback_tracker.py
Feedback Loop — Log AI Shortlist signals và record kết quả thực tế T+20.

Flow:
  1. Mỗi lần tạo shortlist → log_signals() ghi pending records
  2. Hàng ngày 19:00 → collect_matured() tự động resolve các tín hiệu đã đủ T+20
  3. Discord button → get_stats() trả về summary performance

Storage: data/feedback/signal_log.csv
Schema:
  signal_date  | symbol | entry_price | prob | regime | cutoff
  exit_date    | exit_price | actual_return | is_win | status (pending/completed)
"""

from __future__ import annotations

import csv
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

_ROOT         = Path(__file__).resolve().parent.parent
_FEEDBACK_DIR = _ROOT / "data" / "feedback"
_SIGNAL_LOG   = _FEEDBACK_DIR / "signal_log.csv"
_OHLCV_DIR    = _ROOT / "data" / "ohlcv"

_COLUMNS = [
    "signal_date", "symbol", "entry_price", "prob", "regime", "cutoff",
    "exit_date", "exit_price", "actual_return", "is_win", "status",
    "exit_reason",   # "t20" | "stop_loss" | "" (legacy rows)
]

WIN_THRESHOLD  = 0.0    # % — is_win nếu actual_return > 0% (thắng = PnL>0, thua = PnL<=0)
STOP_LOSS_PCT  = 0.10   # hard stop-loss: exit if price drops -10% from entry
HOLD_DAYS      = 25     # trading days to hold (T+25); model trained on T+20 labels


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ensure_log() -> None:
    _FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    if not _SIGNAL_LOG.exists():
        with open(_SIGNAL_LOG, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=_COLUMNS).writeheader()


def _add_n_trading_days(date_str: str, n: int) -> str:
    """Return YYYY-MM-DD that is n trading days (Mon–Fri) after date_str."""
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    count = 0
    while count < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            count += 1
    return d.strftime("%Y-%m-%d")


def _get_close_on_date(symbol: str, as_of: str) -> Optional[float]:
    """Return close price (VND) on or before as_of from data/ohlcv/{symbol}.parquet."""
    path = _OHLCV_DIR / f"{symbol}.parquet"
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path, columns=["time", "close"])
        df["time"] = pd.to_datetime(df["time"])
        df = df[df["time"] <= pd.Timestamp(as_of)].sort_values("time")
        return float(df.iloc[-1]["close"]) if not df.empty else None
    except Exception:
        return None


def _find_sl_trigger(symbol: str, signal_date: str, sl_threshold: float,
                     end_date: str) -> Optional[tuple]:
    """
    Scan lịch sử từ signal_date+1 đến end_date.
    Trả về (first_trigger_date, exit_price) nếu close <= sl_threshold,
    trong đó exit_price = sl_threshold (SL order đặt sẵn, không phải close thực).
    Trả về None nếu không có ngày nào trigger.
    """
    path = _OHLCV_DIR / f"{symbol}.parquet"
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path, columns=["time", "close"])
        df["time"] = pd.to_datetime(df["time"])
        df = df[
            (df["time"] > pd.Timestamp(signal_date)) &
            (df["time"] <= pd.Timestamp(end_date))
        ].sort_values("time")
        triggered = df[df["close"] <= sl_threshold]
        if triggered.empty:
            return None
        first_row  = triggered.iloc[0]
        trigger_dt = first_row["time"].strftime("%Y-%m-%d")
        # SL order đặt tại threshold → exit_price = sl_threshold (cap tối đa -10%)
        # Gap-down chỉ ảnh hưởng intraday, daily close dùng SL price làm chuẩn
        exit_price = sl_threshold
        return trigger_dt, exit_price
    except Exception:
        return None


# ── Core API ───────────────────────────────────────────────────────────────────

def log_signals(
    signal_date: str,
    signals: list[dict],
    regime: str,
    cutoff: float,
    hold_days: Optional[int] = None,
) -> int:
    """
    Ghi pending records cho các tín hiệu mới. Bỏ qua duplicate (cùng date+symbol).

    Args:
        hold_days: số ngày giữ lệnh (regime-aware). Nếu None → dùng HOLD_DAYS (25).
    Returns: số rows mới được ghi.
    """
    if not signals:
        return 0
    _ensure_log()

    # Load existing để check duplicate
    try:
        existing = pd.read_csv(_SIGNAL_LOG, dtype=str)
        existing_keys = set(zip(existing["signal_date"], existing["symbol"]))
    except Exception:
        existing_keys = set()

    effective_hold = hold_days if hold_days is not None else HOLD_DAYS
    exit_date = _add_n_trading_days(signal_date, effective_hold)
    rows = []
    for s in signals:
        key = (signal_date, s["symbol"])
        if key in existing_keys:
            continue
        rows.append({
            "signal_date":   signal_date,
            "symbol":        s["symbol"],
            "entry_price":   s.get("close_price") or 0,
            "prob":          round(float(s.get("prob", 0)), 4),
            "regime":        regime,
            "cutoff":        cutoff,
            "exit_date":     exit_date,
            "exit_price":    "",
            "actual_return": "",
            "is_win":        "",
            "status":        "pending",
        })

    if rows:
        with open(_SIGNAL_LOG, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=_COLUMNS).writerows(rows)
        log.info("[feedback] Logged %d new signal(s) for %s (regime=%s)", len(rows), signal_date, regime)

    return len(rows)


def _ensure_exit_reason_col(df: pd.DataFrame) -> pd.DataFrame:
    """Add exit_reason column if missing (backward compat with old CSV files)."""
    if "exit_reason" not in df.columns:
        df["exit_reason"] = ""
    return df


def collect_matured(as_of_date: Optional[str] = None) -> int:
    """
    Kiểm tra tất cả pending signals:
      1. Stop-loss -10%: nếu giá hôm nay <= entry * 0.90 → exit sớm (exit_reason="stop_loss")
      2. T+20 matured: nếu exit_date <= as_of_date → exit bình thường (exit_reason="t20")
    Returns: tổng số signals đã resolve.
    """
    _ensure_log()
    today_str = as_of_date or date.today().strftime("%Y-%m-%d")

    try:
        df = pd.read_csv(_SIGNAL_LOG, dtype=str)
    except Exception:
        return 0

    df = _ensure_exit_reason_col(df)

    all_pending = df[df["status"] == "pending"]
    if all_pending.empty:
        return 0

    resolved = 0

    for idx, row in all_pending.iterrows():
        entry_price = float(row["entry_price"]) if row["entry_price"] else None
        if not entry_price:
            continue

        sl_threshold = entry_price * (1 - STOP_LOSS_PCT)

        # ── Check stop-loss: scan lịch sử từ signal_date → today ─────────
        # Dùng _find_sl_trigger để tìm ngày đầu tiên giá chạm -10%
        # → exit_price = entry * 0.90 (SL order), không dùng giá hôm nay
        sl_end = min(row["exit_date"], today_str)  # không check quá exit_date
        sl_result = _find_sl_trigger(row["symbol"], row["signal_date"], sl_threshold, sl_end)
        if sl_result is not None:
            trigger_date, exit_price = sl_result
            ret = (exit_price - entry_price) / entry_price * 100
            df.at[idx, "exit_date"]     = trigger_date
            df.at[idx, "exit_price"]    = round(exit_price, 2)
            df.at[idx, "actual_return"] = round(ret, 2)
            df.at[idx, "is_win"]        = ret > WIN_THRESHOLD
            df.at[idx, "status"]        = "completed"
            df.at[idx, "exit_reason"]   = "stop_loss"
            resolved += 1
            log.info(
                "[feedback] SL -%.0f%% triggered: %s  entry=%.0f  sl_price=%.0f  ret=%.1f%%  (date=%s)",
                STOP_LOSS_PCT * 100, row["symbol"], entry_price, exit_price, ret, trigger_date,
            )
            continue

        # ── Check T+20 maturity ───────────────────────────────────────────
        if row["exit_date"] <= today_str:
            exit_price = _get_close_on_date(row["symbol"], row["exit_date"])
            if exit_price is None:
                continue
            ret = (exit_price - entry_price) / entry_price * 100
            df.at[idx, "exit_price"]    = round(exit_price, 2)
            df.at[idx, "actual_return"] = round(ret, 2)
            df.at[idx, "is_win"]        = ret > WIN_THRESHOLD
            df.at[idx, "status"]        = "completed"
            df.at[idx, "exit_reason"]   = "t20"
            resolved += 1

    if resolved:
        df.to_csv(_SIGNAL_LOG, index=False)
        log.info("[feedback] Resolved %d signal(s) as of %s", resolved, today_str)

    return resolved


def get_stats() -> dict:
    """
    Trả về summary stats từ completed signals.
    Dùng để hiển thị trên Discord.
    """
    _ensure_log()
    try:
        df = pd.read_csv(_SIGNAL_LOG, dtype=str)
    except Exception:
        return {"total_completed": 0, "total_pending": 0, "error": "Không đọc được log"}

    df = _ensure_exit_reason_col(df)
    completed = df[df["status"] == "completed"].copy()
    pending   = df[df["status"] == "pending"]

    n_pending = len(pending)

    if completed.empty:
        return {
            "total_completed": 0,
            "total_pending":   n_pending,
            "message":         "Chưa có tín hiệu nào hoàn thành T+20",
        }

    completed["actual_return"] = pd.to_numeric(completed["actual_return"], errors="coerce")
    completed["is_win"]        = completed["is_win"].map(
        {"True": True, "False": False, True: True, False: False}
    )
    completed["entry_price"]   = pd.to_numeric(completed["entry_price"],   errors="coerce")
    completed["prob"]          = pd.to_numeric(completed["prob"],           errors="coerce")

    total   = len(completed)
    wins    = int(completed["is_win"].sum())
    wr      = wins / total * 100
    avg_ret = float(completed["actual_return"].mean())
    med_ret = float(completed["actual_return"].median())

    # By regime
    regime_stats: dict = {}
    for regime, grp in completed.groupby("regime"):
        n = len(grp)
        w = int(grp["is_win"].sum())
        regime_stats[str(regime)] = {
            "n":       n,
            "wr":      round(w / n * 100, 1),
            "avg_ret": round(float(grp["actual_return"].mean()), 2),
        }

    # By month (last 6 months)
    completed["month"] = completed["signal_date"].str[:7]
    monthly: dict = {}
    for m, grp in completed.groupby("month"):
        n = len(grp)
        w = int(grp["is_win"].sum())
        monthly[str(m)] = {
            "n":  n,
            "wr": round(w / n * 100, 1),
            "avg_ret": round(float(grp["actual_return"].mean()), 2),
        }

    # Exit reason breakdown
    sl_count  = int((completed["exit_reason"] == "stop_loss").sum())
    t20_count = int((completed["exit_reason"] == "t20").sum())

    # Recent 10 signals
    recent = (
        completed.sort_values("signal_date", ascending=False)
        .head(10)[["signal_date", "symbol", "actual_return", "is_win", "regime", "exit_reason"]]
        .to_dict("records")
    )

    return {
        "total_completed": total,
        "total_pending":   n_pending,
        "win_rate":        round(wr, 1),
        "avg_return":      round(avg_ret, 2),
        "median_return":   round(med_ret, 2),
        "regime_stats":    regime_stats,
        "monthly":         dict(sorted(monthly.items())[-6:]),   # last 6 months
        "recent":          recent,
        "sl_count":        sl_count,
        "t20_count":       t20_count,
    }


def format_stats_discord(stats: dict) -> str:
    """Format feedback stats as Discord message."""
    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📊  **KẾT QUẢ THỰC TẾ — AI SHORTLIST 20D**")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if stats.get("error") or stats.get("message"):
        lines.append(f"ℹ️ {stats.get('message') or stats.get('error')}")
        if stats.get("total_pending", 0):
            lines.append(f"⏳ Đang chờ T+20: **{stats['total_pending']}** tín hiệu")
        lines.append("")
        lines.append("⚠️ *Kết quả thực tế từ giao dịch của bot. Không phải khuyến nghị đầu tư.*")
        return "\n".join(lines)

    total = stats["total_completed"]
    pend  = stats["total_pending"]
    wr    = stats["win_rate"]
    avg   = stats["avg_return"]
    med   = stats["median_return"]

    sl_count  = stats.get("sl_count", 0)
    t20_count = stats.get("t20_count", 0)
    exit_str  = f"T+20: {t20_count}  |  🛑 SL: {sl_count}" if (sl_count + t20_count) > 0 else ""

    lines.append(
        f"✅ **{total}** tín hiệu đã hoàn thành  |  ⏳ **{pend}** đang chờ"
        + (f"\n📤 Exit: {exit_str}" if exit_str else "")
    )
    lines.append(
        f"🎯 Win rate: **{wr:.1f}%**  |  Avg return: **{avg:+.2f}%**  |  Median: **{med:+.2f}%**"
    )
    lines.append("")

    # By regime
    if stats.get("regime_stats"):
        lines.append("**Theo regime:**")
        lines.append("```")
        lines.append(f"{'Regime':<10} {'N':>4} {'WR':>6} {'Avg':>7}")
        lines.append(f"{'─'*10} {'─'*4} {'─'*6} {'─'*7}")
        for regime, rs in sorted(stats["regime_stats"].items()):
            lines.append(
                f"{regime:<10} {rs['n']:>4} {rs['wr']:>5.1f}% {rs['avg_ret']:>+6.2f}%"
            )
        lines.append("```")

    # By month (last 6)
    if stats.get("monthly"):
        lines.append("**Theo tháng (6 tháng gần nhất):**")
        lines.append("```")
        lines.append(f"{'Tháng':<7} {'N':>4} {'WR':>6} {'Avg':>7}")
        lines.append(f"{'─'*7} {'─'*4} {'─'*6} {'─'*7}")
        for month, ms in stats["monthly"].items():
            lines.append(
                f"{month:<7} {ms['n']:>4} {ms['wr']:>5.1f}% {ms['avg_ret']:>+6.2f}%"
            )
        lines.append("```")

    # Recent 10
    if stats.get("recent"):
        lines.append("**10 tín hiệu gần nhất:**")
        lines.append("```")
        lines.append(f"{'Mã':<5} {'Ngày':>8} {'Kết quả':>8} {'Exit':<5} {'Regime':<10}")
        lines.append(f"{'─'*5} {'─'*8} {'─'*8} {'─'*5} {'─'*10}")
        for r in stats["recent"]:
            ret    = float(r["actual_return"]) if r["actual_return"] else 0
            win    = "✓" if r["is_win"] in (True, "True") else "✗"
            reason = r.get("exit_reason") or ""
            tag    = "SL🛑" if reason == "stop_loss" else "T20"
            lines.append(
                f"{str(r['symbol']):<5} {str(r['signal_date'])[5:]:>8} "
                f"{win} {ret:>+5.1f}%  {tag:<5} {str(r['regime']):<10}"
            )
        lines.append("```")

    lines.append("")
    lines.append("⚠️ *Kết quả thực tế của model. Không phải khuyến nghị đầu tư.*")
    return "\n".join(lines)


# ── CLI (backfill / inspect) ───────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    p = argparse.ArgumentParser(description="Feedback Tracker")
    p.add_argument("--collect", action="store_true", help="Collect matured signals")
    p.add_argument("--stats",   action="store_true", help="Show stats")
    p.add_argument("--as-of",   default=None,        help="Override today's date (YYYY-MM-DD)")
    args = p.parse_args()

    if args.collect:
        n = collect_matured(args.as_of)
        print(f"Resolved {n} matured signal(s).")

    if args.stats:
        stats = get_stats()
        print(format_stats_discord(stats))
