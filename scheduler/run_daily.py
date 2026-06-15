#!/usr/bin/env python3
"""
AgentQ Daily Scheduler — chạy sau khi thị trường đóng cửa (16:05 ICT = 09:05 UTC).
Pipeline:
  1. Update OHLCV data (phase1a)
  2. Build features (phase2)
  3. Score AI signals (phase6 = v3a + v5)
  4. Score rule-based signals (rules/main.py)
  5. Export JSONs + git push to GitHub Pages

Usage:
  python scheduler/run_daily.py              # tự detect ngày hôm nay
  python scheduler/run_daily.py --date 2026-06-13
  python scheduler/run_daily.py --skip-rules # chỉ chạy AI
  python scheduler/run_daily.py --skip-ai   # chỉ chạy rule-based
"""
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Repo layout ──────────────────────────────────────────────────────────────
REPO       = Path(__file__).resolve().parent.parent  # agentq-daily/
AI_DIR     = REPO / "ai"
RULES_DIR  = REPO / "rules"
SCHED_DIR  = REPO / "scheduler"

sys.path.insert(0, str(AI_DIR))
sys.path.insert(0, str(RULES_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_trading_day(d: date) -> bool:
    return d.weekday() < 5  # Mon–Fri only (rough check, no holiday table)


def _last_trading_day() -> str:
    d = date.today()
    while not _is_trading_day(d):
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _run(cmd: list[str], cwd: Path, desc: str) -> bool:
    log.info("▶ %s", desc)
    result = subprocess.run(cmd, cwd=cwd, text=True,
                            capture_output=False)  # stream output live
    if result.returncode != 0:
        log.error("✗ %s failed (exit %d)", desc, result.returncode)
        return False
    log.info("✓ %s done", desc)
    return True


# ── Pipeline steps ───────────────────────────────────────────────────────────

def step_update_ohlcv(run_date: str) -> bool:
    """Phase 1a: Update OHLCV data for today."""
    script = AI_DIR / "pipeline" / "phase1a_ohlcv_store.py"
    if not script.exists():
        log.warning("phase1a_ohlcv_store.py not found, skipping OHLCV update")
        return True
    # phase1a dùng --update, không nhận --date
    return _run(
        [sys.executable, str(script), "--update"],
        cwd=AI_DIR, desc=f"OHLCV update ({run_date})",
    )


def step_build_features(run_date: str) -> bool:
    """Phase 2: Build feature parquet for today."""
    script = AI_DIR / "pipeline" / "phase2_feature_pipeline.py"
    if not script.exists():
        log.error("phase2_feature_pipeline.py not found!")
        return False
    return _run(
        [sys.executable, str(script), "--date", run_date],
        cwd=AI_DIR, desc=f"Feature build ({run_date})",
    )


def step_score_ai(run_date: str) -> bool:
    """Phase 6: Score AI signals (v3a + v5 shadow)."""
    script = AI_DIR / "pipeline" / "phase6_shortlist_discord.py"
    if not script.exists():
        log.error("phase6_shortlist_discord.py not found!")
        return False
    return _run(
        [sys.executable, "-m", "pipeline.phase6_shortlist_discord",
         "--date", run_date, "--no-update"],
        cwd=AI_DIR, desc=f"AI scoring ({run_date})",
    )


def step_score_rules(run_date: str) -> bool:
    """Rule-based screener (rules/main.py)."""
    script = RULES_DIR / "main.py"
    if not script.exists():
        log.error("rules/main.py not found!")
        return False
    return _run(
        [sys.executable, str(script), "--date", run_date],
        cwd=RULES_DIR, desc=f"Rule-based screener ({run_date})",
    )


def step_export_ai() -> bool:
    """Export v3a_data.json + v5_data.json → git push."""
    return _run(
        [sys.executable, str(SCHED_DIR / "export_ai_signals.py")],
        cwd=SCHED_DIR, desc="Export AI signals JSON",
    )


def step_export_weekly() -> bool:
    """Export weekly_data.json (only on Fridays)."""
    if date.today().weekday() != 4:  # 4 = Friday
        log.info("Not Friday — skipping weekly export")
        return True
    return _run(
        [sys.executable, str(SCHED_DIR / "export_weekly_signals.py")],
        cwd=SCHED_DIR, desc="Export weekly signals JSON",
    )


def step_export_longhold() -> bool:
    """Export longhold_data.json (v3b signals, daily)."""
    return _run(
        [sys.executable, str(SCHED_DIR / "export_longhold_signals.py")],
        cwd=SCHED_DIR, desc="Export long-hold signals JSON",
    )


def step_git_push_rules(run_date: str) -> bool:
    """Push rule-based signal JSON to GitHub Pages."""
    import os
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        subprocess.run(
            ["git", "remote", "set-url", "origin",
             f"https://{token}@github.com/kienquyen/agentq-daily.git"],
            cwd=REPO, capture_output=True,
        )
    # data.json + signals/ should already be committed by rules/main.py
    # Just force-push any pending changes
    subprocess.run(["git", "add", "-A"], cwd=REPO, capture_output=True)
    commit = subprocess.run(
        ["git", "commit", "-m", f"daily-update: {run_date}"],
        cwd=REPO, capture_output=True, text=True,
    )
    if "nothing to commit" in (commit.stdout + commit.stderr):
        log.info("Nothing new to push for rules")
        return True
    push = subprocess.run(["git", "push", "origin", "main"],
                          cwd=REPO, capture_output=True, text=True)
    if push.returncode == 0:
        log.info("🌐 Rules signals pushed → GitHub Pages")
        return True
    log.error("Push failed: %s", push.stderr[:200])
    return False


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AgentQ daily pipeline")
    parser.add_argument("--date", default=None,
                        help="Trading date YYYY-MM-DD (default: last trading day)")
    parser.add_argument("--skip-rules", action="store_true")
    parser.add_argument("--skip-ai",    action="store_true")
    parser.add_argument("--skip-ohlcv", action="store_true",
                        help="Skip OHLCV download (use existing data)")
    args = parser.parse_args()

    run_date = args.date or _last_trading_day()
    log.info("=" * 60)
    log.info("AgentQ Daily Pipeline — %s", run_date)
    log.info("=" * 60)

    failures = []

    if not args.skip_ohlcv:
        if not step_update_ohlcv(run_date):
            log.warning("OHLCV update failed — continuing with existing data")

    if not args.skip_ai:
        if not step_build_features(run_date):
            failures.append("feature_build")
        else:
            if not step_score_ai(run_date):
                failures.append("ai_scoring")
            if not step_export_ai():
                failures.append("export_ai")
            if not step_export_weekly():
                failures.append("export_weekly")
            if not step_export_longhold():
                failures.append("export_longhold")

    if not args.skip_rules:
        if not step_score_rules(run_date):
            failures.append("rules_scoring")
        else:
            if not step_git_push_rules(run_date):
                failures.append("git_push_rules")

    log.info("=" * 60)
    if failures:
        log.error("Pipeline completed WITH ERRORS: %s", ", ".join(failures))
        sys.exit(1)
    else:
        log.info("✅ Pipeline completed successfully for %s", run_date)


if __name__ == "__main__":
    main()
