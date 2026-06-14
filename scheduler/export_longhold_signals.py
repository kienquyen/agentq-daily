#!/usr/bin/env python3
"""
Export v3b Long-hold signals → longhold_data.json
Đọc từ ai/data/shadow_signals/v3b/, tính return thực tế từ OHLCV.

Hold period: 60 trading days (≈ 3 tháng). SL: -10%.
"""
import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime

import pandas as pd

REPO      = Path(__file__).resolve().parent.parent
OUT       = REPO / "longhold_data.json"
SHADOW    = REPO / "ai" / "data" / "shadow_signals" / "v3b"
OHLCV_DIR = REPO / "ai" / "data" / "ohlcv"
HOLD_DAYS = 60   # trading days
SL_PCT    = -10  # stop loss %


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


def _ret(sym: str, entry_date: str, entry_price: float, cache: dict, n: int = HOLD_DAYS):
    """Tính return sau n phiên, stop loss nếu drawdown < SL_PCT."""
    if sym not in cache:
        return None, None, None, None
    prices = cache[sym]
    entry_ts = pd.Timestamp(entry_date)
    fut = prices[prices.index > entry_ts].head(n)
    if fut.empty:
        return None, None, None, None

    # Cả OHLCV parquet và signal close_price đều đơn vị VND tuyệt đối
    ep = float(entry_price)

    # Check stop loss
    for dt, p in fut.items():
        drawdown = (p - ep) / ep * 100
        if drawdown <= SL_PCT:
            return round(drawdown, 2), False, str(dt)[:10], float(p)

    # T+n return
    final_p = float(fut.iloc[-1])
    ret_pct  = (final_p - ep) / ep * 100
    exit_dt  = str(fut.index[-1])[:10]
    is_win   = ret_pct > 0
    status   = "completed" if len(fut) >= n else "pending"
    if status == "pending":
        return None, None, None, None
    return round(ret_pct, 2), is_win, exit_dt, round(final_p, 0)


# ── Main export ────────────────────────────────────────────────────────────────
def export_longhold():
    print("Building price cache...")
    cache = _build_price_cache()
    print(f"  → {len(cache)} symbols loaded")

    today = datetime.utcnow().strftime("%Y-%m-%d")

    all_signals = []   # flat list
    daily_map   = {}   # date → day summary

    files = sorted(SHADOW.glob("*.json"))
    for f in files:
        d = json.loads(f.read_text())
        date_str   = d.get("date", f.stem)
        regime     = d.get("regime", "")
        cutoff     = d.get("prob_cutoff", 0.60)
        raw_sigs   = d.get("signals", [])
        near_miss  = d.get("near_misses", [])

        day_sigs = []
        for s in raw_sigs:
            sym   = s.get("symbol", "")
            prob  = s.get("prob")
            price = s.get("close_price") or s.get("close_vnd")

            ret, is_win, exit_dt, exit_px = _ret(sym, date_str, float(price) if price else 0, cache)

            # Decide status
            if ret is not None:
                status = "completed"
            else:
                # Check if past hold period
                entry_ts = pd.Timestamp(date_str)
                prices_sym = cache.get(sym, pd.Series(dtype=float))
                fut_count  = len(prices_sym[prices_sym.index > entry_ts])
                status = "pending" if fut_count < HOLD_DAYS else "waiting"  # waiting = data gap

            rec = {
                "signal_date": date_str,
                "symbol":      sym,
                "entry_price": float(price) if price else None,
                "prob":        round(float(prob), 4) if prob else None,
                "cutoff":      round(float(cutoff), 3),
                "regime":      regime,
                "status":      status,
                "actual_return": ret,
                "is_win":      is_win,
                "exit_date":   exit_dt,
                "exit_price":  exit_px,
                "sl_pct":      SL_PCT,
                "hold_days":   HOLD_DAYS,
            }
            day_sigs.append(rec)
            all_signals.append(rec)

        daily_map[date_str] = {
            "date":       date_str,
            "regime":     regime,
            "prob_cutoff": cutoff,
            "n_signals":  len(raw_sigs),
            "signals":    day_sigs,
            "near_misses": near_miss,
        }

    # ── Stats ──────────────────────────────────────────────────────────────────
    completed = [s for s in all_signals if s["status"] == "completed" and s["actual_return"] is not None]
    active    = [s for s in all_signals if s["status"] == "pending"]

    if completed:
        wins     = sum(1 for s in completed if s["is_win"])
        wr       = round(wins / len(completed) * 100, 1)
        avg_ret  = round(sum(s["actual_return"] for s in completed) / len(completed), 2)
        best     = round(max(s["actual_return"] for s in completed), 2)
        worst    = round(min(s["actual_return"] for s in completed), 2)
    else:
        wr = avg_ret = best = worst = 0

    stats = {
        "total":       len(all_signals),
        "completed":   len(completed),
        "active":      len(active),
        "win_rate":    wr,
        "avg_return":  avg_ret,
        "best":        best,
        "worst":       worst,
        "note":        f"Hold {HOLD_DAYS} phiên | SL {SL_PCT}% | WIN = return > 0%"
    }

    payload = {
        "model":          "v3b",
        "name":           "Long-hold — V3b",
        "description":    f"LightGBM weekly momentum, giữ tối đa {HOLD_DAYS} phiên (~3 tháng). SL {SL_PCT}%.",
        "generated_at":   datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats":          stats,
        "active_signals": active,
        "recent_history": [s for s in reversed(all_signals) if s["status"] == "completed"][:30],
        "daily_signals":  daily_map,
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
