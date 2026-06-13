"""
v5_decision_optuna.py — v5 (alpha-10) decision layer + Optuna cutoff calibration

Value gate (replaces hardcheck — keeps oversold/value candidates):
  VG1: avg_val_21d >= min_liquidity_b   (lighter than hardcheck's 3.0B)
  VG2: close >= min_price               (penny-stock floor, lighter than 10k)
  → NO trend/momentum/candle filters (those remove the value bounce names)

Optuna jointly optimizes (min_liquidity, min_price, prob_cutoff) to maximize
Precision@10 on a calibration period, then validates on held-out.

Split:
  CALIB: 2025-02-01 → 2025-09-30   (optimize here)
  EVAL:  2025-10-01 → 2026-04-29   (held-out validation)

Chạy:
    python -m pipeline.v5_decision_optuna --trials 150
"""
from __future__ import annotations
import argparse, json, logging, pickle, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

LABELS_DIR = ROOT / "data" / "labels"
MODELS_DIR = ROOT / "data" / "models"

CALIB_START, CALIB_END = "2025-02-01", "2025-09-30"
EVAL_START,  EVAL_END  = "2025-10-01", "2026-04-29"
TOP_K = 10

# Search bounds
BOUNDS = {
    "min_liquidity_b": (0.5, 3.0),
    "min_price":       (3000, 15000),
    "prob_cutoff":     (0.30, 0.80),
}


def value_gate(row, min_liq, min_price):
    """Light gate: liquidity + price floor only. Returns True if passes."""
    av = row.get("avg_val_21d_b", np.nan)
    cl = row.get("close_vnd", np.nan)
    if pd.notna(av) and av < min_liq:   return False
    if pd.notna(cl) and cl < min_price: return False
    return True


def precision_at_k(sub: pd.DataFrame, min_liq, min_price, cutoff, k=TOP_K):
    """Apply value gate + cutoff, take top-K per day, return mean P@K + coverage."""
    precs = []
    for d, g in sub.groupby("date_"):
        gg = g[g["raw_prob"] >= cutoff]
        if len(gg) == 0: continue
        # value gate
        mask = gg.apply(lambda r: value_gate(r, min_liq, min_price), axis=1)
        gg = gg[mask]
        if len(gg) == 0: continue
        top = gg.nlargest(min(k, len(gg)), "raw_prob")
        precs.append(top["label_i"].mean())
    return (np.mean(precs) if precs else 0.0), len(precs)


def load_scored():
    df = pd.read_parquet(LABELS_DIR / "training_set_20d_alpha10.parquet").dropna(subset=["label"])
    with open(MODELS_DIR / "v5" / "lgbm_model_alpha10.pkl", "rb") as f:
        p = pickle.load(f)
    model, fc = p["model"], p["feat_cols"]
    X = df[[c for c in fc if c in df.columns]].copy()
    for c in [c for c in fc if c not in df.columns]: X[c] = 0.0
    df["raw_prob"] = model.predict_proba(X[fc])[:, 1]
    df["label_i"]  = df["label"].astype(int)
    df["date_"]    = df.index.get_level_values("date")
    return df


def main(n_trials=150):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    df = load_scored()
    calib = df[(df["date_"]>=CALIB_START)&(df["date_"]<=CALIB_END)].copy()
    evald = df[(df["date_"]>=EVAL_START)&(df["date_"]<=EVAL_END)].copy()
    log.info("Calib rows=%d (pos %.1f%%) | Eval rows=%d (pos %.1f%%)",
             len(calib), calib["label_i"].mean()*100, len(evald), evald["label_i"].mean()*100)

    base_calib = calib["label_i"].mean()
    base_eval  = evald["label_i"].mean()

    # Baseline: hardcheck + cutoff 0.50 (what v5 would get with old pipeline)
    def baseline(sub):
        precs=[]
        for d,g in sub.groupby("date_"):
            gg=g[(g["raw_prob"]>=0.50)&(g["hardcheck_pass"]==1)]
            if len(gg)==0: continue
            precs.append(gg.nlargest(min(TOP_K,len(gg)),"raw_prob")["label_i"].mean())
        return np.mean(precs) if precs else 0
    bl_calib, bl_eval = baseline(calib), baseline(evald)
    log.info("Baseline (hardcheck+cut.50): calib P@10=%.1f%% | eval P@10=%.1f%%",
             bl_calib*100, bl_eval*100)

    def objective(trial):
        ml = trial.suggest_float("min_liquidity_b", *BOUNDS["min_liquidity_b"])
        mp = trial.suggest_float("min_price", *BOUNDS["min_price"])
        ct = trial.suggest_float("prob_cutoff", *BOUNDS["prob_cutoff"])
        p10, ndays = precision_at_k(calib, ml, mp, ct)
        if ndays < 15:   # need enough signal days (penalize over-restrictive)
            return 0.0
        return p10

    log.info("Running Optuna: %d trials...", n_trials)
    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best = study.best_params
    log.info("Best params: %s", {k: round(v,4) for k,v in best.items()})

    # Evaluate best on calib + held-out eval
    pc, nc = precision_at_k(calib, best["min_liquidity_b"], best["min_price"], best["prob_cutoff"])
    pe, ne = precision_at_k(evald, best["min_liquidity_b"], best["min_price"], best["prob_cutoff"])

    print("\n" + "="*64)
    print(f"  v5 DECISION LAYER + OPTUNA CUTOFF  ({n_trials} trials)")
    print("="*64)
    print(f"  {'':<26}{'CALIB':>12}{'EVAL(OOS)':>12}")
    print(f"  {'Base pos rate':<26}{base_calib:>11.1%}{base_eval:>12.1%}")
    print(f"  {'Baseline(hc+cut.50) P@10':<26}{bl_calib:>11.1%}{bl_eval:>12.1%}")
    print(f"  {'v5 value-gate+optuna P@10':<26}{pc:>11.1%}{pe:>12.1%}")
    print(f"  {'Lift vs base (eval)':<26}{'':<12}{pe/base_eval:>11.2f}x")
    print(f"  {'Signal days':<26}{nc:>12}{ne:>12}")
    print()
    print(f"  Optimal gate: liquidity>={best['min_liquidity_b']:.1f}B  price>={best['min_price']:.0f}  prob_cutoff={best['prob_cutoff']:.3f}")

    # Save to v5 config
    v5 = MODELS_DIR / "v5"
    cfg = json.loads((v5/"config.json").read_text())
    cfg["_decision_layer"] = {
        "type": "value_gate",
        "min_liquidity_b": round(best["min_liquidity_b"],3),
        "min_price":       round(best["min_price"],0),
        "prob_cutoff":     round(best["prob_cutoff"],3),
        "no_hardcheck":    True,
        "_note": "value gate (liquidity+price only) — keeps oversold/value candidates",
    }
    cfg["_eval_p10_oos"] = round(pe,4)
    cfg["_eval_lift_oos"] = round(pe/base_eval,3)
    (v5/"config.json").write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"\n  Saved decision layer → {v5/'config.json'}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--trials", type=int, default=150)
    main(n_trials=p.parse_args().trials)
