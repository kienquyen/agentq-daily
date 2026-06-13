"""
pipeline/v5_shadow.py — v5 (alpha-10) shadow scorer + 30-day monitor

v5 differs fundamentally from v3x models:
  - model file:  v5/lgbm_model_alpha10.pkl   (not lgbm_model_20d.pkl)
  - label:       alpha_20d >= 10% (beat VNINDEX)   (not absolute +5%)
  - decision:    value_gate (liquidity + price)     (not hardcheck/tier3)
  - cutoff:      single 0.657                         (not regime cutoffs)

This runs SHADOW-ONLY: logs daily top-K to data/shadow_signals/v5/{date}.json.
After ~30 trading days, run evaluate_v5_shadow() to compare logged predictions
against realized alpha (needs T+20 forward data to mature).

Daily hook: called from phase6.get_shortlist_20d (non-fatal).
Evaluate:   python -m pipeline.v5_shadow --evaluate
Backfill:   python -m pipeline.v5_shadow --backfill 30
"""
from __future__ import annotations
import argparse, json, logging, pickle
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger(__name__)

MODELS_DIR  = ROOT / "data" / "models"
FEATURES_DIR = ROOT / "data" / "features"
OHLCV_DIR    = ROOT / "data" / "ohlcv"
SHADOW_DIR   = ROOT / "data" / "shadow_signals" / "v5"

TOP_K = 10
_MODEL_CACHE = {}


def _load_v5():
    if "m" not in _MODEL_CACHE:
        with open(MODELS_DIR / "v5" / "lgbm_model_alpha10.pkl", "rb") as f:
            p = pickle.load(f)
        cfg = json.loads((MODELS_DIR / "v5" / "config.json").read_text())
        dl = cfg.get("_decision_layer", {})
        _MODEL_CACHE["m"]  = p["model"]
        _MODEL_CACHE["fc"] = p["feat_cols"]
        mg = dl.get("momentum_gate", {})
        _MODEL_CACHE["gate"] = {
            "min_liq":  dl.get("min_liquidity_b", 1.4),
            "min_price": dl.get("min_price", 14000),
            "cutoff":   dl.get("prob_cutoff", 0.657),
            "ret20_min": mg.get("return_20d_min", 0.0),
            "ema9_min":  mg.get("ema9_vs_ema26_min", 0.0),
            "cooldown":  dl.get("cooldown_days", 20),
        }
    return _MODEL_CACHE["m"], _MODEL_CACHE["fc"], _MODEL_CACHE["gate"]


def _recent_symbols(date_str: str, cooldown: int) -> set:
    """Symbols signaled within last `cooldown` calendar days (from shadow logs)."""
    if not SHADOW_DIR.exists():
        return set()
    cutoff = pd.Timestamp(date_str) - pd.Timedelta(days=cooldown)
    recent = set()
    for lf in SHADOW_DIR.glob("*.json"):
        try:
            d = pd.Timestamp(lf.stem)
            if cutoff <= d < pd.Timestamp(date_str):
                data = json.loads(lf.read_text())
                for s in data.get("signals", []):
                    recent.add(s["symbol"])
        except Exception:
            pass
    return recent


def score_v5_shadow(date_str: str) -> dict:
    """Score v5 for one date, apply value gate, return top-K signals."""
    feat_path = FEATURES_DIR / f"{date_str}.parquet"
    if not feat_path.exists():
        return {"date": date_str, "version": "v5", "n_signals": 0,
                "signals": [], "error": f"no feature file {date_str}"}

    df = pd.read_parquet(feat_path)
    if "symbol" not in df.columns:        # feature files store symbol as index
        df["symbol"] = df.index
    model, fc, gate = _load_v5()
    X = df[[c for c in fc if c in df.columns]].copy()
    for c in [c for c in fc if c not in df.columns]: X[c] = 0.0
    df["prob"] = model.predict_proba(X[fc])[:, 1]

    # Value gate: cutoff + liquidity + price (NO hardcheck)
    g = df[df["prob"] >= gate["cutoff"]].copy()
    if "avg_val_21d_b" in g.columns:
        g = g[(g["avg_val_21d_b"].isna()) | (g["avg_val_21d_b"] >= gate["min_liq"])]
    if "close_vnd" in g.columns:
        g = g[(g["close_vnd"].isna()) | (g["close_vnd"] >= gate["min_price"])]

    # Momentum confirmation gate — avoid falling knives (validated OOS)
    if "return_20d" in g.columns:
        g = g[(g["return_20d"].isna()) | (g["return_20d"] >= gate["ret20_min"])]
    if "ema9_vs_ema26_pct" in g.columns:
        g = g[(g["ema9_vs_ema26_pct"].isna()) | (g["ema9_vs_ema26_pct"] >= gate["ema9_min"])]

    # Cooldown — exclude symbols signaled within last N days
    recent = _recent_symbols(date_str, gate["cooldown"])
    if recent and "symbol" in g.columns:
        g = g[~g["symbol"].isin(recent)]

    g = g.sort_values("prob", ascending=False).head(TOP_K)
    signals = [{"symbol": (s if isinstance(s,str) else idx),
                "prob": round(float(r["prob"]), 4),
                "close_price": int(r.get("close_vnd", 0) or 0)}
               for idx, r in g.iterrows() for s in [r.get("symbol", idx)]]
    return {"date": date_str, "version": "v5",
            "prob_cutoff": gate["cutoff"], "n_signals": len(signals),
            "signals": signals, "error": None}


STOP_LOSS_PCT = 0.07   # SL -7% for v5 value model


def build_v5_discord_message(date_str: str) -> str:
    """
    Format v5 (VALUE) shortlist for Discord with SL -7%.
    Distinct branding from v3b momentum shortlist to avoid confusion.
    """
    res = score_v5_shadow(date_str)
    dl_cut = _load_v5()[2]["cutoff"]
    lines = []
    lines.append("━" * 30)
    lines.append(f"💎  **AI SHORTLIST — VALUE/ALPHA (v5)**  |  {date_str}")
    lines.append("━" * 30)
    lines.append("🎯 **Mục tiêu: outperform VNINDEX ≥ +10% trong ~1 tháng (T+20)**")
    lines.append(f"🧠 Model: v5 LightGBM (value + earnings + momentum confirm)  |  Cutoff: `{dl_cut:.3f}`")
    lines.append(f"🛡️ **Stop-loss: -{STOP_LOSS_PCT*100:.0f}%**  |  Hold tối đa T+20  |  Cooldown {_load_v5()[2]['cooldown']}d")
    lines.append("")

    if res.get("error"):
        lines.append(f"⚠️ Lỗi: `{res['error']}`")
        return "\n".join(lines)

    sigs = res.get("signals", [])
    if not sigs:
        lines.append("🔕 **Hôm nay không có cổ phiếu value đủ điều kiện.**")
        lines.append("> v5 rất selective — chỉ fire khi có value+momentum rõ ràng (thường vài lệnh/tháng).")
        lines.append("")
        lines.append("⚠️ *Tín hiệu tham khảo từ mô hình ML. Không phải khuyến nghị đầu tư.*")
        return "\n".join(lines)

    lines.append(f"📋 **DANH SÁCH VALUE ({len(sigs)} mã):**")
    lines.append("```")
    lines.append(f"  {'Mã':<6} {'Prob':>5} {'Giá vào':>9} {'SL -7%':>9} {'Cắt lỗ tại'}")
    lines.append(f"  {'─'*5} {'─'*5} {'─'*9} {'─'*9} {'─'*10}")
    for s in sigs:
        entry = s.get("close_price", 0) or 0
        sl = int(entry * (1 - STOP_LOSS_PCT)) if entry else 0
        entry_k = f"{entry/1000:,.1f}k" if entry else "—"
        sl_k    = f"{sl/1000:,.1f}k" if sl else "—"
        lines.append(f"  {s['symbol']:<6} {s['prob']:>5.3f} {entry_k:>9} {sl_k:>9}   nếu giá ≤ {sl_k}")
    lines.append("```")
    lines.append(f"💡 *SL -{STOP_LOSS_PCT*100:.0f}%: cắt lỗ khi giá giảm {STOP_LOSS_PCT*100:.0f}% từ giá vào. "
                 f"Mục tiêu chốt khi outperform index hoặc đạt T+20.*")
    lines.append("")
    lines.append("⚠️ *Tín hiệu tham khảo từ mô hình ML. Không phải khuyến nghị đầu tư. Tự chịu trách nhiệm.*")
    return "\n".join(lines)


def log_v5_shadow(date_str: str) -> dict:
    """Score + persist v5 shadow log for date_str."""
    SHADOW_DIR.mkdir(parents=True, exist_ok=True)
    result = score_v5_shadow(date_str)
    (SHADOW_DIR / f"{date_str}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("[v5-shadow] Logged %d signal(s) for %s", result["n_signals"], date_str)
    return result


def backfill(n_days: int = 30) -> None:
    """Backfill last n_days of v5 shadow logs from existing feature files."""
    files = sorted(FEATURES_DIR.glob("20*.parquet"))[-n_days:]
    print(f"Backfilling {len(files)} days of v5 shadow logs...")
    for f in files:
        d = f.stem
        r = log_v5_shadow(d)
        print(f"  {d}: {r['n_signals']} signals  {[s['symbol'] for s in r['signals'][:5]]}")


def evaluate_v5_shadow() -> None:
    """
    Evaluate logged v5 shadow predictions against realized alpha.
    For each logged signal, compute actual alpha_20d = ret_20d - vnindex_ret_20d,
    win = alpha_20d >= 0.10. Only evaluates matured signals (T+20 available).
    """
    # Load VNINDEX forward 20d returns
    vni = pd.read_parquet(OHLCV_DIR / "VNINDEX.parquet")
    vni["time"] = pd.to_datetime(vni["time"])
    vni = vni.sort_values("time").set_index("time")["close"].astype(float)
    vni_fwd = {}
    cl, dt = vni.values, vni.index
    for i in range(len(cl)-20):
        vni_fwd[dt[i]] = cl[i+20]/cl[i] - 1

    logs = sorted(SHADOW_DIR.glob("*.json"))
    rows = []
    for lf in logs:
        data = json.loads(lf.read_text())
        d = pd.Timestamp(data["date"])
        vni_ret = vni_fwd.get(d)
        if vni_ret is None: continue   # not matured
        for s in data["signals"]:
            sym = s["symbol"]
            sp = OHLCV_DIR / f"{sym}.parquet"
            if not sp.exists(): continue
            sd = pd.read_parquet(sp); sd["time"]=pd.to_datetime(sd["time"])
            sd = sd.sort_values("time").reset_index(drop=True)
            fut = sd[sd["time"]>=d]
            if len(fut)<21: continue
            ei = fut.index[0]
            if ei+20 >= len(sd): continue
            ret = sd["close"].iloc[ei+20]/sd["close"].iloc[ei] - 1
            alpha = ret - vni_ret
            rows.append({"date":d,"symbol":sym,"prob":s["prob"],
                         "ret_20d":ret,"alpha_20d":alpha,
                         "win_alpha":int(alpha>=0.10),    # beat VNINDEX >= 10%
                         "win_profit":int(ret>0.05)})      # absolute return > 5%

    if not rows:
        print("Chưa có signal nào matured (cần T+20 forward data). Đợi thêm.")
        return
    df = pd.DataFrame(rows)
    print("="*56)
    print(f"  v5 SHADOW EVALUATION — {df['date'].nunique()} ngày, {len(df)} signals")
    print("="*56)
    print(f"  Date range: {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"  WIN-alpha  (alpha>=10%, beat index): {df['win_alpha'].mean():>6.1%}  ({df['win_alpha'].sum()}/{len(df)})")
    print(f"  WIN-profit (ret_20d > 5%, lãi tuyệt đối): {df['win_profit'].mean():>6.1%}  ({df['win_profit'].sum()}/{len(df)})")
    print(f"  Cả 2 (alpha>=10% VÀ ret>5%):         {((df['win_alpha']==1)&(df['win_profit']==1)).mean():>6.1%}")
    print(f"  Mean alpha_20d:  {df['alpha_20d'].mean():>6.1%}   |  Mean ret_20d: {df['ret_20d'].mean():>6.1%}")
    print(f"  % beat index (alpha>0): {(df['alpha_20d']>0).mean():.1%}")
    print(f"\n  Expectation OOS (dedup, momentum gate):")
    print(f"    WIN-alpha ~30-36% | WIN-profit ~50% | mean alpha ~+10%")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", type=int, default=0)
    p.add_argument("--evaluate", action="store_true")
    a = p.parse_args()
    if a.backfill: backfill(a.backfill)
    elif a.evaluate: evaluate_v5_shadow()
    else: print("Use --backfill N or --evaluate")
