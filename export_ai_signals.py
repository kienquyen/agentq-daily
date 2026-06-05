#!/usr/bin/env python3
"""
Export AI model signals lên agentq-daily repo.
Chạy thủ công hoặc tự động sau khi model chạy xong.

Usage:
    python3 export_ai_signals.py
"""
import json, subprocess
from pathlib import Path
from datetime import datetime

import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent / "Project AgentQ (Sabo)" / "Historical version"
V3A_DIR  = BASE / "20260523_update AI shortlist_v3a_add foreign flow"
V5_DIR   = BASE / "20260509_Quant upgrade_V5.5"
OUT_DIR  = Path(__file__).parent  # agentq-daily/

# ── Helper ─────────────────────────────────────────────────────────────────────
def load_signal_log(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["signal_date"] = pd.to_datetime(df["signal_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return df

def df_to_records(df: pd.DataFrame) -> list:
    records = []
    for _, r in df.iterrows():
        rec = {
            "signal_date":   str(r.get("signal_date", "")),
            "symbol":        str(r.get("symbol", "")),
            "entry_price":   float(r["entry_price"]) if pd.notna(r.get("entry_price")) else None,
            "prob":          round(float(r["prob"]), 4) if pd.notna(r.get("prob")) else None,
            "regime":        str(r.get("regime", "")),
            "cutoff":        float(r["cutoff"]) if pd.notna(r.get("cutoff")) else None,
            "status":        str(r.get("status", "")),
            "exit_date":     str(r["exit_date"]) if pd.notna(r.get("exit_date")) else None,
            "exit_price":    float(r["exit_price"]) if pd.notna(r.get("exit_price")) else None,
            "actual_return": round(float(r["actual_return"]), 2) if pd.notna(r.get("actual_return")) else None,
            "is_win":        bool(r["is_win"]) if pd.notna(r.get("is_win")) else None,
            "exit_reason":   str(r["exit_reason"]) if pd.notna(r.get("exit_reason", None)) else None,
        }
        records.append(rec)
    return records

def compute_stats(df: pd.DataFrame) -> dict:
    done = df[df["status"] == "completed"]
    if done.empty:
        return {"total": 0, "win_rate": 0, "avg_return": 0, "best": 0, "worst": 0}
    wins = done["is_win"].fillna(False)
    rets = done["actual_return"].dropna()
    return {
        "total":      int(len(done)),
        "win_rate":   round(float(wins.mean()) * 100, 1),
        "avg_return": round(float(rets.mean()), 2) if len(rets) else 0,
        "best":       round(float(rets.max()), 2) if len(rets) else 0,
        "worst":      round(float(rets.min()), 2) if len(rets) else 0,
    }

# ── Export v3a (AI Shortlist — 20D hold) ──────────────────────────────────────
def export_v3a():
    log_path = V3A_DIR / "data" / "feedback" / "signal_log.csv"
    df = load_signal_log(log_path)

    active    = df[df["status"].isin(["pending","open","active"])].copy() if not df.empty else pd.DataFrame()
    recent    = df[df["status"] == "completed"].tail(20).copy() if not df.empty else pd.DataFrame()
    stats     = compute_stats(df) if not df.empty else {}

    # Lấy daily shadow signal gần nhất có signal
    shadow_dir = V3A_DIR / "data" / "shadow_signals" / "v3a"
    latest_signals = []
    if shadow_dir.exists():
        for f in sorted(shadow_dir.glob("2026-*.json"), reverse=True)[:30]:
            try:
                d = json.loads(f.read_text())
                if d.get("n_signals", 0) > 0:
                    latest_signals.append({
                        "date":       f.stem,
                        "n_signals":  d["n_signals"],
                        "prob_cutoff":d.get("prob_cutoff"),
                        "regime":     d.get("regime"),
                        "signals":    d.get("signals", [])[:10],
                    })
                    if len(latest_signals) >= 10:
                        break
            except Exception:
                pass

    payload = {
        "model":           "v3a",
        "name":            "AI Shortlist — 20D Hold",
        "description":     "LightGBM model, xác suất outperform +5% trong 20 phiên",
        "generated_at":    datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats":           stats,
        "active_signals":  df_to_records(active) if not active.empty else [],
        "recent_history":  df_to_records(recent.iloc[::-1]) if not recent.empty else [],
        "daily_signals":   latest_signals,
    }

    out = OUT_DIR / "v3a_data.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"✅ v3a exported → {out.name}  ({len(payload['active_signals'])} active, {len(payload['recent_history'])} history)")
    return payload

# ── Export V5 (Outperform Market) ─────────────────────────────────────────────
def export_v5():
    log_path = V5_DIR / "data" / "feedback" / "signal_log.csv"
    df = load_signal_log(log_path)

    active  = df[df["status"].isin(["pending","open","active"])].copy() if not df.empty else pd.DataFrame()
    recent  = df[df["status"] == "completed"].tail(20).copy() if not df.empty else pd.DataFrame()
    stats   = compute_stats(df) if not df.empty else {}

    payload = {
        "model":           "v5",
        "name":            "Outperform Market — V5",
        "description":     "Model V5.5: xác suất outperform VNIndex trong 20 phiên",
        "generated_at":    datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats":           stats,
        "active_signals":  df_to_records(active) if not active.empty else [],
        "recent_history":  df_to_records(recent.iloc[::-1]) if not recent.empty else [],
    }

    out = OUT_DIR / "v5_data.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"✅ V5  exported → {out.name}  ({len(payload['active_signals'])} active, {len(payload['recent_history'])} history)")
    return payload

# ── Push to GitHub ─────────────────────────────────────────────────────────────
def push_to_github():
    try:
        subprocess.run(["git", "add", "v3a_data.json", "v5_data.json"],
                       cwd=OUT_DIR, capture_output=True)
        commit = subprocess.run(
            ["git", "commit", "-m", f"ai-signals: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"],
            cwd=OUT_DIR, capture_output=True, text=True)
        if "nothing to commit" in (commit.stdout + commit.stderr):
            print("📁 No changes to push")
            return
        push = subprocess.run(["git", "push", "origin", "main"],
                              cwd=OUT_DIR, capture_output=True, text=True)
        if push.returncode == 0:
            print("🌐 AI signals pushed → https://kienquyen.github.io/agentq-daily/")
        else:
            print(f"⚠️ Push failed: {push.stderr[:100]}")
    except Exception as e:
        print(f"⚠️ Git error: {e}")

# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Exporting AI model signals...")
    export_v3a()
    export_v5()
    push_to_github()
