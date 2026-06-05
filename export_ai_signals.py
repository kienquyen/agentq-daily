#!/usr/bin/env python3
"""
Export AI model signals lên agentq-daily repo.
Chạy thủ công hoặc tự động sau khi model chạy xong.

Usage:
    python3 export_ai_signals.py
"""
import json, subprocess, sys
from pathlib import Path
from datetime import datetime

import pandas as pd
sys.path.insert(0, str(Path(__file__).parent.parent / "Vnstock_Daily_Signals_Rules"))

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE    = Path(__file__).parent.parent / "Project AgentQ (Sabo)" / "Historical version"
CURR    = BASE / "20260523_update AI shortlist_v3a_add foreign flow"  # project đang chạy
V3A_DIR = CURR   # v3a signals ở đây
V5_DIR  = CURR   # V5 production signals cũng ở đây (shadow_signals/v5/)
OUT_DIR = Path(__file__).parent  # agentq-daily/

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

# ── Export V5 (Outperform Market — CD5, value+momentum gate) ─────────────────
def export_v5():
    """
    V5 production signals nằm ở data/shadow_signals/v5/ trong project hiện tại.
    Format: date, symbol, prob, close_price (= giá vào), SL -7%.
    Actual return được lấy từ signal_log.csv nếu có (cross-ref by date+symbol).
    """
    shadow_dir  = V5_DIR / "data" / "shadow_signals" / "v5"
    log_path    = V5_DIR / "data" / "feedback" / "signal_log.csv"

    # Load feedback log để lấy actual return
    df_log = pd.DataFrame()
    if log_path.exists():
        df_log = pd.read_csv(log_path)

    # Fetch giá lịch sử để tính Ret20d + Alpha
    _price_cache = {}
    _unit_div    = 1000  # VCI trả về đơn vị nghìn VND
    try:
        from main import _fetch_history_any_source
        for sym in ["NAF","BSR","VNINDEX"]:
            df, _ = _fetch_history_any_source(sym, "2026-01-01",
                                               datetime.utcnow().strftime("%Y-%m-%d"))
            if not df.empty:
                _price_cache[sym] = df.set_index("time")["close"]
    except Exception as e:
        print(f"  ⚠️ Không fetch được giá: {e}")

    def _ret20(sym, date_str, price_vnd):
        if sym not in _price_cache: return None
        prices  = _price_cache[sym]
        entry_k = price_vnd / _unit_div
        fut     = prices[prices.index > pd.Timestamp(date_str)].head(20)
        if len(fut) < 20: return None
        return round((float(fut.iloc[-1]) - entry_k) / entry_k * 100, 2)

    def _alpha20(sym, date_str, price_vnd):
        r_s = _ret20(sym, date_str, price_vnd)
        if r_s is None or "VNINDEX" not in _price_cache: return None
        vni_slice = _price_cache["VNINDEX"]
        vni_entry = vni_slice[vni_slice.index <= pd.Timestamp(date_str)]
        if vni_entry.empty: return None
        r_vni = _ret20("VNINDEX", date_str, float(vni_entry.iloc[-1]) * _unit_div)
        if r_vni is None: return None
        return round(r_s - r_vni, 2)

    # Đọc tất cả V5 shadow signals
    all_signals = []
    if shadow_dir.exists():
        for f in sorted(shadow_dir.glob("*.json"), reverse=True):
            try:
                d = json.loads(f.read_text())
                n = d.get("n_signals", 0)
                if n == 0:
                    continue
                date_str = f.stem
                for s in d.get("signals", []):
                    sym   = s.get("symbol", "")
                    prob  = s.get("prob")
                    price = s.get("close_price") or s.get("close_vnd")

                    # Tìm actual return trong feedback log
                    actual_ret = None
                    is_win     = None
                    status     = "completed"
                    exit_date  = None
                    exit_price = None
                    if not df_log.empty:
                        match = df_log[
                            (df_log["symbol"] == sym) &
                            (df_log["signal_date"].astype(str).str[:10] == date_str)
                        ]
                        if not match.empty:
                            row = match.iloc[0]
                            actual_ret = float(row["actual_return"]) if pd.notna(row.get("actual_return")) else None
                            is_win     = bool(row["is_win"])          if pd.notna(row.get("is_win"))     else None
                            status     = str(row.get("status", "completed"))
                            exit_date  = str(row["exit_date"])        if pd.notna(row.get("exit_date"))  else None
                            exit_price = float(row["exit_price"])     if pd.notna(row.get("exit_price")) else None
                        else:
                            # Không có trong log → xem là pending nếu signal còn mới (< 25 ngày)
                            try:
                                sig_dt = datetime.strptime(date_str, "%Y-%m-%d")
                                days_passed = (datetime.utcnow() - sig_dt).days
                                status = "pending" if days_passed < 25 else "completed"
                            except Exception:
                                status = "pending"

                    # Tính Ret20d + Alpha từ OHLCV nếu chưa có trong log
                    price_vnd = float(price) if price else None
                    if actual_ret is None and price_vnd:
                        actual_ret = _ret20(sym, date_str, price_vnd)
                        alpha_val  = _alpha20(sym, date_str, price_vnd)
                        if actual_ret is not None:
                            # WIN = alpha > 0 (outperform index)
                            is_win = (alpha_val is not None and alpha_val > 0)
                        else:
                            alpha_val = None
                    else:
                        alpha_val = _alpha20(sym, date_str, price_vnd) if price_vnd else None

                    all_signals.append({
                        "signal_date":   date_str,
                        "symbol":        sym,
                        "entry_price":   price_vnd,
                        "prob":          round(float(prob), 4) if prob else None,
                        "cutoff":        round(float(d.get("prob_cutoff", 0)), 3),
                        "regime":        d.get("regime", ""),
                        "status":        status,
                        "exit_date":     exit_date,
                        "exit_price":    exit_price,
                        "actual_return": round(actual_ret, 2) if actual_ret is not None else None,
                        "alpha":         round(alpha_val, 2) if alpha_val is not None else None,
                        "is_win":        is_win,   # WIN = alpha > 0
                        "sl_pct":        -7.0,
                    })
            except Exception as e:
                print(f"  ⚠️ Skip {f.name}: {e}")

    active  = [s for s in all_signals if s["status"] == "pending"]
    history = [s for s in all_signals if s["status"] == "completed"]

    # Stats chỉ tính trades đã có actual_return
    trades_with_ret = [s for s in history if s["actual_return"] is not None]
    if trades_with_ret:
        wins    = sum(1 for s in trades_with_ret if s["is_win"])
        wr      = round(wins / len(trades_with_ret) * 100, 1)
        avg_ret = round(sum(s["actual_return"] for s in trades_with_ret) / len(trades_with_ret), 2)
        best    = round(max(s["actual_return"] for s in trades_with_ret), 2)
        worst   = round(min(s["actual_return"] for s in trades_with_ret), 2)
    else:
        wr = avg_ret = best = worst = 0

    stats = {
        "total":      len(all_signals),
        "win_rate":   wr,
        "avg_return": avg_ret,
        "best":       best,
        "worst":      worst,
        "note":       "WIN = outperform VNIndex (alpha > 0)"
    }

    payload = {
        "model":          "v5",
        "name":           "Outperform Market — V5",
        "description":    "CD5 + value/momentum gate, SL -7% | Selective — im lặng khi không có setup",
        "generated_at":   datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats":          stats,
        "active_signals": active,
        "recent_history": history[:20],
        "all_signals":    all_signals,  # toàn bộ lịch sử
    }

    out = OUT_DIR / "v5_data.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"✅ V5  exported → {out.name}  ({len(active)} pending, {len(history)} history | {len(all_signals)} total signals)")
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
