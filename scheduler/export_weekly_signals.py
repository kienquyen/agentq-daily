#!/usr/bin/env python3
"""
Export weekly AI signals lên agentq-daily repo.
Chạy mỗi thứ 6 sau khi market đóng cửa.

Usage:
    python3 export_weekly_signals.py
    python3 export_weekly_signals.py --backfill  # Backfill 8 tuần gần nhất
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import date, timedelta, datetime

REPO = Path(__file__).resolve().parent.parent  # repo root
sys.path.insert(0, str(REPO / "ai"))           # ai/ pipeline modules

OUT_DIR = REPO  # JSON output goes to repo root


def last_friday(ref: date | None = None) -> str:
    d = ref or date.today()
    days_since_fri = (d.weekday() - 4) % 7
    return (d - timedelta(days=days_since_fri)).strftime("%Y-%m-%d")


def get_recent_fridays(n: int = 8) -> list[str]:
    fridays = []
    d = date.today()
    while len(fridays) < n:
        if d.weekday() == 4:
            fridays.append(d.strftime("%Y-%m-%d"))
        d -= timedelta(days=1)
    return fridays


def score_weekly_for_date(date_str: str) -> dict:
    try:
        from features.signal.discord_ui import _score_weekly
        return _score_weekly(date_str)
    except Exception as e:
        return {
            "date": date_str, "regime": "unknown",
            "prob_cutoff": 0.60, "signals": [], "near_misses": [],
            "error": str(e),
        }


def export_weekly():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill", action="store_true", help="Backfill 8 tuần gần nhất")
    args = parser.parse_args()

    if args.backfill:
        fridays = get_recent_fridays(8)
        print(f"Backfilling {len(fridays)} Fridays: {fridays[0]} → {fridays[-1]}")
    else:
        fridays = [last_friday()]
        print(f"Scoring Friday: {fridays[0]}")

    # Load existing data if any
    out_path = OUT_DIR / "weekly_data.json"
    existing = {}
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
            existing_signals = existing.get("weekly_signals", {})
        except Exception:
            existing_signals = {}
    else:
        existing_signals = {}

    # Score each Friday
    weekly_signals = dict(existing_signals)
    for friday in fridays:
        print(f"  Scoring {friday}...", end=" ", flush=True)
        result = score_weekly_for_date(friday)
        n = len(result.get("signals", []))
        err = result.get("error")
        print(f"{'❌ ' + err[:50] if err else f'✅ {n} signals'}")

        weekly_signals[friday] = {
            "date":        friday,
            "regime":      result.get("regime", "unknown"),
            "prob_cutoff": result.get("prob_cutoff", 0.60),
            "n_universe":  result.get("n_universe", 0),
            "n_hardcheck": result.get("n_hardcheck", 0),
            "signals": [
                {
                    "symbol":      s["symbol"],
                    "prob":        s["prob"],
                    "entry_price": s.get("close_price") or s.get("price"),
                    "hold_days":   120,
                    "exit_date":   s.get("exit_date"),
                }
                for s in result.get("signals", [])
            ],
            "near_misses": result.get("near_misses", [])[:5],
            "error":       result.get("error"),
        }

    # Sort by date descending
    weekly_signals = dict(sorted(weekly_signals.items(), reverse=True))

    # Compute stats (only completed weeks = signal date + 120d < today)
    today = date.today()
    completed = [
        sig
        for date_str, week in weekly_signals.items()
        for sig in week["signals"]
        if (today - datetime.strptime(date_str, "%Y-%m-%d").date()).days > 120
    ]
    stats = {
        "total_signals": sum(len(w["signals"]) for w in weekly_signals.values()),
        "weeks_with_signal": sum(1 for w in weekly_signals.values() if w["signals"]),
        "hold_days": 120,
        "cutoff": 0.60,
        "note": "Weekly model — hold up to 120d, exit khi prob < 0.40",
    }

    payload = {
        "model":          "weekly",
        "name":           "Weekly Shortlist — 120D Hold",
        "description":    "LightGBM weekly filter, cutoff 0.60, hold tối đa 120 phiên, thoát sớm khi re-score < 0.40",
        "generated_at":   datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats":          stats,
        "weekly_signals": weekly_signals,
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n✅ weekly_data.json exported ({len(weekly_signals)} weeks)")

    # Push to GitHub
    try:
        subprocess.run(["git", "add", "weekly_data.json"], cwd=OUT_DIR, capture_output=True)
        commit = subprocess.run(
            ["git", "commit", "-m", f"weekly-signals: {datetime.utcnow().strftime('%Y-%m-%d')}"],
            cwd=OUT_DIR, capture_output=True, text=True
        )
        if "nothing to commit" in (commit.stdout + commit.stderr):
            print("📁 No changes to push")
            return
        import os
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            subprocess.run(["git", "remote", "set-url", "origin",
                            f"https://{token}@github.com/kienquyen/agentq-daily.git"],
                           cwd=OUT_DIR, capture_output=True)
        push = subprocess.run(["git", "push", "origin", "main"], cwd=OUT_DIR, capture_output=True, text=True)
        if push.returncode == 0:
            print("🌐 Weekly signals pushed → https://kienquyen.github.io/agentq-daily/")
        else:
            print(f"⚠️ Push failed: {push.stderr[:100]}")
    except Exception as e:
        print(f"⚠️ Git error: {e}")


if __name__ == "__main__":
    export_weekly()
