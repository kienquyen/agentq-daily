#!/usr/bin/env python3
"""
Export weekly long-hold signals → longhold_data.json

Strategy (discord_ui.py + backtest_dynamic_exit.py):
  - Entry: Thứ Sáu, prob >= 0.60, top-8, không vào recovery
  - Exit:  re-score mỗi tuần, thoát khi prob < 0.40 OR T+120 ngày
  - Không có stop loss % cố định
"""
import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime, date, timedelta

import pandas as pd

REPO      = Path(__file__).resolve().parent.parent
OUT       = REPO / "longhold_data.json"
SHADOW    = REPO / "ai" / "data" / "shadow_signals" / "v3b"
OHLCV_DIR = REPO / "ai" / "data" / "ohlcv"

ENTRY_CUTOFF  = 0.60
EXIT_CUTOFF   = 0.40   # thoát khi re-score < 0.40
TOP_K         = 8
MAX_HOLD      = 120    # trading days hard cap
START_DATE    = "2026-01-01"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_friday(date_str: str) -> bool:
    return datetime.strptime(date_str, "%Y-%m-%d").weekday() == 4


def _trading_days_between(start: str, end: str, all_dates: list[str]) -> int:
    return sum(1 for d in all_dates if start < d <= end)


# ── Price cache ────────────────────────────────────────────────────────────────

def _build_price_cache() -> dict:
    cache = {}
    if not OHLCV_DIR.exists():
        return cache
    for pf in OHLCV_DIR.glob("*.parquet"):
        try:
            df = pd.read_parquet(pf)
            if "time" in df.columns and "close" in df.columns:
                df["time"] = pd.to_datetime(df["time"])
                cache[pf.stem] = df.set_index("time")["close"].sort_index()
        except Exception:
            pass
    return cache


def _current_price(sym: str, cache: dict) -> float | None:
    if sym not in cache:
        return None
    s = cache[sym]
    if s.empty:
        return None
    return float(s.iloc[-1])


def _price_on(sym: str, after_date: str, cache: dict, n_trading_days: int, all_trading_dates: list[str]) -> tuple[float | None, str | None]:
    """Return (price, date_str) after n_trading_days from after_date."""
    if sym not in cache:
        return None, None
    s = cache[sym]
    entry_ts = pd.Timestamp(after_date)
    fut = s[s.index > entry_ts]
    if len(fut) < n_trading_days:
        return None, None
    p = float(fut.iloc[n_trading_days - 1])
    d = str(fut.index[n_trading_days - 1])[:10]
    return p, d


# ── Re-score map from v3b shadow ───────────────────────────────────────────────

def _build_rescore_map() -> dict[str, dict[str, float]]:
    """rescore_map[symbol][date] = prob — from all v3b Friday files."""
    rescore: dict[str, dict[str, float]] = {}
    if not SHADOW.exists():
        return rescore
    for f in sorted(SHADOW.glob("*.json")):
        if not _is_friday(f.stem):
            continue
        d = json.loads(f.read_text())
        for s in d.get("signals", []):
            sym = s.get("symbol", "")
            prob = s.get("prob")
            if sym and prob is not None:
                rescore.setdefault(sym, {})[f.stem] = float(prob)
    return rescore


def _find_rescore_exit(sym: str, entry_date: str, rescore_map: dict, all_friday_dates: list[str]) -> tuple[str | None, float | None]:
    """Return (exit_friday, prob) if re-score < EXIT_CUTOFF on any subsequent Friday."""
    sym_rescores = rescore_map.get(sym, {})
    for fri in all_friday_dates:
        if fri <= entry_date:
            continue
        if fri in sym_rescores:
            p = sym_rescores[fri]
            if p < EXIT_CUTOFF:
                return fri, p
        # If symbol not present on a Friday, we can't confirm < 0.40 (may just be below sector cutoff ~0.55)
        # So we don't trigger exit unless we have explicit prob data
    return None, None


# ── Main export ────────────────────────────────────────────────────────────────

def export_longhold():
    print("Building price cache...")
    cache = _build_price_cache()
    print(f"  → {len(cache)} symbols loaded")

    today = date.today().strftime("%Y-%m-%d")

    # All trading dates from OHLCV (approximate from cache)
    if cache:
        sample_sym = next(iter(cache))
        all_trading_dates = sorted(str(d)[:10] for d in cache[sample_sym].index if str(d)[:10] >= START_DATE)
    else:
        all_trading_dates = []

    all_friday_dates = [d for d in all_trading_dates if _is_friday(d)]

    rescore_map = _build_rescore_map()
    print(f"  → Re-score map: {sum(len(v) for v in rescore_map.values())} entries across {len(rescore_map)} symbols")

    all_signals = []
    weekly_log = {}  # Friday date → week summary

    if not SHADOW.exists():
        print("No shadow signals directory found")
        return

    # Process each Friday
    for f in sorted(SHADOW.glob("*.json")):
        date_str = f.stem
        if date_str < START_DATE:
            continue
        if not _is_friday(date_str):
            continue

        d = json.loads(f.read_text())
        regime = d.get("regime", "")
        raw_sigs = d.get("signals", [])

        # Skip recovery regime
        if regime == "recovery":
            weekly_log[date_str] = {
                "date": date_str, "regime": regime,
                "prob_cutoff": ENTRY_CUTOFF, "n_signals": 0, "signals": [],
                "note": "Bỏ qua — regime RECOVERY không hợp long-hold"
            }
            continue

        # Filter: prob >= 0.60, sort by prob desc, top-8
        eligible = sorted(
            [s for s in raw_sigs if float(s.get("prob", 0)) >= ENTRY_CUTOFF],
            key=lambda s: float(s["prob"]),
            reverse=True
        )[:TOP_K]

        day_sigs = []
        for s in eligible:
            sym   = s.get("symbol", "")
            prob  = float(s.get("prob", 0))
            price = s.get("close_price") or s.get("close_vnd")
            ep    = float(price) if price else None

            # Check T+120 exit
            exit_date_t120, exit_price_t120 = None, None
            t120_count = _trading_days_between(date_str, today, all_trading_dates)
            if t120_count >= MAX_HOLD:
                exit_price_t120, exit_date_t120 = _price_on(sym, date_str, cache, MAX_HOLD, all_trading_dates)

            # Check re-score exit (first Friday where prob < 0.40)
            rescore_exit_date, rescore_prob = _find_rescore_exit(sym, date_str, rescore_map, all_friday_dates)

            # Determine actual exit
            exit_date = exit_price = exit_reason = None
            actual_return = None
            status = "pending"

            if rescore_exit_date and (not exit_date_t120 or rescore_exit_date <= exit_date_t120):
                # Re-score triggered first
                exit_date = rescore_exit_date
                # Get price on that exit Friday
                sym_prices = cache.get(sym, pd.Series(dtype=float))
                exit_ts = pd.Timestamp(rescore_exit_date)
                fut_on_exit = sym_prices[sym_prices.index <= exit_ts]
                if not fut_on_exit.empty and ep:
                    exit_price = float(fut_on_exit.iloc[-1])
                    actual_return = round((exit_price - ep) / ep * 100, 2)
                exit_reason = f"re-score={rescore_prob:.2f}<{EXIT_CUTOFF}"
                status = "completed"
            elif exit_date_t120 and exit_price_t120 and ep:
                exit_date = exit_date_t120
                exit_price = exit_price_t120
                actual_return = round((exit_price_t120 - ep) / ep * 100, 2)
                exit_reason = f"T+{MAX_HOLD}"
                status = "completed"
            else:
                # Still holding — compute unrealized P&L
                cur_p = _current_price(sym, cache)
                if cur_p and ep:
                    actual_return = round((cur_p - ep) / ep * 100, 2)
                    exit_price = cur_p
                status = "pending"

            is_win = (actual_return > 0) if actual_return is not None else None

            rec = {
                "signal_date":   date_str,
                "symbol":        sym,
                "entry_price":   ep,
                "prob":          round(prob, 4),
                "regime":        regime,
                "status":        status,
                "actual_return": actual_return,
                "is_win":        is_win,
                "exit_date":     exit_date,
                "exit_price":    round(exit_price, 0) if exit_price else None,
                "exit_reason":   exit_reason,
            }
            day_sigs.append(rec)
            all_signals.append(rec)

        weekly_log[date_str] = {
            "date":        date_str,
            "regime":      regime,
            "prob_cutoff": ENTRY_CUTOFF,
            "n_signals":   len(day_sigs),
            "signals":     day_sigs,
        }

    # ── Stats ──────────────────────────────────────────────────────────────────
    completed = [s for s in all_signals if s["status"] == "completed"]
    active    = [s for s in all_signals if s["status"] == "pending"]

    if completed:
        wins    = sum(1 for s in completed if s["is_win"])
        wr      = round(wins / len(completed) * 100, 1)
        avg_ret = round(sum(s["actual_return"] for s in completed) / len(completed), 2)
        best    = round(max(s["actual_return"] for s in completed), 2)
        worst   = round(min(s["actual_return"] for s in completed), 2)
    else:
        wr = avg_ret = best = worst = 0

    stats = {
        "total":      len(all_signals),
        "completed":  len(completed),
        "active":     len(active),
        "win_rate":   wr,
        "avg_return": avg_ret,
        "best":       best,
        "worst":      worst,
        "note":       f"Cutoff {ENTRY_CUTOFF} | Exit re-score<{EXIT_CUTOFF} hoặc T+{MAX_HOLD} ngày | Top-{TOP_K}/tuần"
    }

    payload = {
        "model":          "weekly",
        "name":           "Long-hold — Weekly Model",
        "description":    f"LightGBM 20d, cutoff {ENTRY_CUTOFF}, thoát khi re-score < {EXIT_CUTOFF} hoặc T+{MAX_HOLD} ngày giao dịch. Top-{TOP_K}/tuần. Không vào regime recovery.",
        "generated_at":   datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats":          stats,
        "active_signals": sorted(active, key=lambda s: s["signal_date"], reverse=True),
        "recent_history": sorted(completed, key=lambda s: s["signal_date"] or "", reverse=True)[:30],
        "weekly_signals": dict(sorted(weekly_log.items(), reverse=True)),
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"✅ longhold exported → {OUT.name}")
    print(f"   {len(all_signals)} total | {len(active)} active | {len(completed)} completed | WR={wr}%")

    # ── Git push ───────────────────────────────────────────────────────────────
    try:
        subprocess.run(["git", "add", "longhold_data.json"], cwd=REPO, capture_output=True)
        commit = subprocess.run(
            ["git", "commit", "-m", f"longhold: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"],
            cwd=REPO, capture_output=True, text=True
        )
        if "nothing to commit" in (commit.stdout + commit.stderr):
            print("📁 No changes to push")
            return
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            subprocess.run(["git", "remote", "set-url", "origin",
                            f"https://{token}@github.com/kienquyen/agentq-daily.git"],
                           cwd=REPO, capture_output=True)
        push = subprocess.run(["git", "push", "origin", "main"],
                              cwd=REPO, capture_output=True, text=True)
        if push.returncode == 0:
            print("🌐 Pushed → kienquyen.github.io/agentq-daily/")
        else:
            print(f"⚠️ Push failed: {push.stderr[:100]}")
    except Exception as e:
        print(f"⚠️ Git error: {e}")


if __name__ == "__main__":
    export_longhold()
