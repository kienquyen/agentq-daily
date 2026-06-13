"""
pipeline/optuna_cutoff_sweep.py
Optimize regime cutoffs for v3b using Optuna to maximize WR@10 (Precision@10).

Design:
  OPT  period: 2025-01-01 → 2025-09-30  (9 months, used for optimization)
  EVAL period: 2025-10-01 → 2026-04-28  (7 months, held-out evaluation)

  Optimizing directly on the full test set would overfit — cutoffs tuned to specific
  market events rather than generalizable thresholds. Two-period design gives an
  honest estimate of out-of-sample performance.

Objective:
  Maximize mean WR@10 on OPT period:
    - Apply T1-T5 filters with trial's regime cutoffs
    - Take top-10 signals per day by probability
    - WR = fraction with forward_ret_20d >= 5%

Chạy:
    python -m pipeline.optuna_cutoff_sweep
    python -m pipeline.optuna_cutoff_sweep --trials 200 --model v3b
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

LABELS_DIR = ROOT / "data" / "labels"
MODELS_DIR = ROOT / "data" / "models"

OPT_START  = "2025-01-01"
OPT_END    = "2025-09-30"
EVAL_START = "2025-10-01"
EVAL_END   = "2099-12-31"
TOP_K      = 10

# Search space per regime
CUTOFF_BOUNDS = {
    "bull":      (0.50, 0.68),
    "sideways":  (0.52, 0.70),
    "deep_bear": (0.55, 0.75),
    "recovery":  (0.48, 0.65),
    "choppy":    (0.55, 0.72),
}


# ── Data loading (once) ───────────────────────────────────────────────────────

def load_data():
    from pipeline.phase4b_ml_model_20d import tier3_filter_20d
    from pipeline.regime_detector import detect_regime

    ts = pd.read_parquet(LABELS_DIR / "training_set_20d.parquet")
    raw = pd.read_parquet(LABELS_DIR / "raw_labels_20d.parquet")
    raw.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in raw.index], names=["symbol", "date"]
    )
    raw = raw[["forward_ret_10d", "max_drawdown_10d"]].rename(
        columns={"forward_ret_10d": "fwd_ret", "max_drawdown_10d": "max_dd"}
    )
    ts = ts.join(raw, how="left")

    # Pre-compute regime per date
    all_dates = sorted(ts.index.get_level_values("date").unique())
    log.info("Pre-computing regime for %d dates...", len(all_dates))
    regime_map = {}
    for d in all_dates:
        try:
            regime, _, _ = detect_regime(d.strftime("%Y-%m-%d"))
            regime_map[d] = regime
        except Exception:
            regime_map[d] = "sideways"

    return ts, regime_map, tier3_filter_20d


def score_model(ts: pd.DataFrame, model, feat_cols: list) -> pd.DataFrame:
    """Score all rows with model probabilities."""
    X = ts[[c for c in feat_cols if c in ts.columns]].copy()
    for c in [c for c in feat_cols if c not in ts.columns]:
        X[c] = 0.0
    proba = model.predict_proba(X[feat_cols])[:, 1]
    result = ts.copy()
    result["raw_prob"] = proba
    result["date_"]    = result.index.get_level_values("date")
    result["symbol"]   = result.index.get_level_values("symbol")
    return result


# ── Core evaluation function ──────────────────────────────────────────────────

def evaluate_cutoffs(
    scored: pd.DataFrame,
    regime_map: dict,
    tier3_fn,
    regime_cutoffs: dict,
    date_start: str,
    date_end: str,
    top_k: int = TOP_K,
) -> dict:
    """
    Apply full pipeline with given cutoffs on [date_start, date_end].
    Returns dict with WR@K, mean_ret, n_signals, n_days.
    """
    sub = scored[
        (scored["date_"] >= pd.Timestamp(date_start)) &
        (scored["date_"] <= pd.Timestamp(date_end))
    ]

    day_wrs, day_rets = [], []

    for date, grp in sub.groupby("date_"):
        regime = regime_map.get(date, "sideways")
        cutoff = regime_cutoffs.get(regime, 0.55)

        scores_df = grp[["symbol", "raw_prob", "hardcheck_pass"]].copy()
        scores_df["score_1000"] = (scores_df["raw_prob"] * 1000).round().astype(int)
        scores_df["rank"] = scores_df["raw_prob"].rank(ascending=False).astype(int)

        try:
            t3 = tier3_fn(scores_df, grp.set_index("symbol"),
                          prob_cutoff=cutoff, regime=regime)
            passed = t3[t3["tier3_pass"].astype(bool)].sort_values(
                "raw_prob", ascending=False
            )
        except Exception:
            continue

        if len(passed) == 0:
            continue

        top_syms = passed.head(top_k)["symbol"].tolist()
        day_rets_list = []
        for sym in top_syms:
            row = grp[grp["symbol"] == sym]
            if not row.empty and pd.notna(row["fwd_ret"].iloc[0]):
                day_rets_list.append(row["fwd_ret"].iloc[0])

        if day_rets_list:
            day_wrs.append(np.mean([r >= 0.05 for r in day_rets_list]))
            day_rets.append(np.mean(day_rets_list))

    if not day_wrs:
        return {"wr5": 0.0, "mean_ret": 0.0, "n_days": 0, "n_signals": 0}

    return {
        "wr5":      float(np.mean(day_wrs)),
        "mean_ret": float(np.mean(day_rets)),
        "n_days":   len(day_wrs),
        "sharpe":   float(np.mean(day_rets) / np.std(day_rets))
                    if np.std(day_rets) > 0 else 0.0,
    }


# ── Optuna optimization ───────────────────────────────────────────────────────

def run_optuna(model_version: str = "v3b", n_trials: int = 100) -> dict:
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
    except ImportError:
        log.error("pip install optuna")
        return {}

    # Load model
    pkl = MODELS_DIR / model_version / "lgbm_model_20d.pkl"
    with open(pkl, "rb") as f:
        payload = pickle.load(f)
    model, feat_cols = payload["model"], payload["feat_cols"]

    # Load current cutoffs as baseline
    baseline_cutoffs = {
        "bull": 0.55, "sideways": 0.58, "deep_bear": 0.58,
        "recovery": 0.53, "choppy": 0.58,
    }
    try:
        cfg = json.loads((MODELS_DIR / model_version / "config.json").read_text())
        if "regime_cutoffs" in cfg:
            baseline_cutoffs = cfg["regime_cutoffs"]
    except Exception:
        pass

    # Load and score data
    log.info("Loading data and scoring %s...", model_version)
    ts, regime_map, tier3_fn = load_data()
    scored = score_model(ts, model, feat_cols)

    # Baseline performance
    log.info("Evaluating baseline cutoffs on OPT period...")
    baseline_opt  = evaluate_cutoffs(scored, regime_map, tier3_fn,
                                     baseline_cutoffs, OPT_START, OPT_END)
    baseline_eval = evaluate_cutoffs(scored, regime_map, tier3_fn,
                                     baseline_cutoffs, EVAL_START, EVAL_END)

    log.info("Baseline OPT:  WR@%d=%.1f%%  MeanRet=%.2f%%  Days=%d",
             TOP_K, baseline_opt["wr5"]*100, baseline_opt["mean_ret"]*100,
             baseline_opt["n_days"])
    log.info("Baseline EVAL: WR@%d=%.1f%%  MeanRet=%.2f%%  Days=%d",
             TOP_K, baseline_eval["wr5"]*100, baseline_eval["mean_ret"]*100,
             baseline_eval["n_days"])

    # Optuna study
    def objective(trial):
        cutoffs = {
            r: trial.suggest_float(r, lo, hi)
            for r, (lo, hi) in CUTOFF_BOUNDS.items()
        }
        result = evaluate_cutoffs(scored, regime_map, tier3_fn,
                                  cutoffs, OPT_START, OPT_END)
        # Penalize if too few days (overfit to very restrictive cutoffs)
        if result["n_days"] < 20:
            return 0.0
        # Composite: 70% WR + 30% Sharpe (normalized)
        return result["wr5"] * 0.7 + min(result["sharpe"], 3.0) / 3.0 * 0.3

    log.info("Running Optuna: %d trials...", n_trials)
    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=42))

    # Seed with baseline
    study.enqueue_trial(baseline_cutoffs)

    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best_cutoffs = study.best_params
    best_trial   = study.best_value

    log.info("Best trial score: %.4f", best_trial)
    log.info("Best cutoffs: %s", best_cutoffs)

    # Evaluate best cutoffs on HELD-OUT eval period
    best_opt  = evaluate_cutoffs(scored, regime_map, tier3_fn,
                                 best_cutoffs, OPT_START, OPT_END)
    best_eval = evaluate_cutoffs(scored, regime_map, tier3_fn,
                                 best_cutoffs, EVAL_START, EVAL_END)

    return {
        "model":          model_version,
        "n_trials":       n_trials,
        "baseline_cutoffs": baseline_cutoffs,
        "best_cutoffs":   best_cutoffs,
        "baseline_opt":   baseline_opt,
        "baseline_eval":  baseline_eval,
        "best_opt":       best_opt,
        "best_eval":      best_eval,
        "study":          study,
    }


# ── Print results ─────────────────────────────────────────────────────────────

def print_results(res: dict) -> None:
    print("\n" + "=" * 65)
    print(f"  OPTUNA CUTOFF OPTIMIZATION — {res['model']}  ({res['n_trials']} trials)")
    print("=" * 65)

    print(f"\n{'Period':<14} {'WR@10':>8} {'MeanRet':>9} {'Sharpe':>8} {'Days':>6}")
    print("─" * 50)
    for label, period_key in [
        ("Baseline OPT",  "baseline_opt"),
        ("Baseline EVAL", "baseline_eval"),
        ("Best OPT",      "best_opt"),
        ("Best EVAL ◄",   "best_eval"),
    ]:
        r = res[period_key]
        print(f"  {label:<12}  {r['wr5']:>7.1%}  {r['mean_ret']:>8.2%}  "
              f"{r.get('sharpe',0):>7.3f}  {r['n_days']:>5d}")

    print(f"\n{'─'*65}")
    print(f"  Regime cutoffs comparison:")
    print(f"  {'Regime':<12} {'Baseline':>10} {'Optimized':>11} {'Delta':>8}")
    print("  " + "─" * 44)
    for regime in ["bull", "sideways", "deep_bear", "recovery", "choppy"]:
        base = res["baseline_cutoffs"].get(regime, 0.55)
        best = res["best_cutoffs"].get(regime, 0.55)
        delta = best - base
        marker = " ▲" if delta > 0.01 else (" ▼" if delta < -0.01 else "  ")
        print(f"  {regime:<12} {base:>10.3f} {best:>11.3f} {delta:>+7.3f}{marker}")

    eval_delta = res["best_eval"]["wr5"] - res["baseline_eval"]["wr5"]
    print(f"\n  OOS improvement (EVAL period): {eval_delta:+.1%} WR@10")
    if eval_delta > 0.02:
        print(f"  ✅ Significant improvement — consider updating config.json")
    elif eval_delta > 0:
        print(f"  🟡 Marginal improvement — monitor before deploying")
    else:
        print(f"  ⚠️  No improvement OOS — baseline cutoffs are robust")

    print(f"\n  To apply: update data/models/{res['model']}/config.json regime_cutoffs")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main(model_version: str = "v3b", n_trials: int = 100) -> None:
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  Optuna Cutoff Sweep — Maximize WR@10                ║")
    log.info("║  OPT:  %s → %s                           ║", OPT_START, OPT_END)
    log.info("║  EVAL: %s → %s                           ║", EVAL_START, EVAL_END)
    log.info("╚══════════════════════════════════════════════════════╝")

    res = run_optuna(model_version=model_version, n_trials=n_trials)
    if not res:
        return

    print_results(res)

    # Save best cutoffs to file
    out_path = ROOT / "logs" / f"optuna_cutoffs_{model_version}.json"
    import json as _json
    save_data = {
        "model":          res["model"],
        "n_trials":       res["n_trials"],
        "best_cutoffs":   res["best_cutoffs"],
        "baseline_cutoffs": res["baseline_cutoffs"],
        "best_eval_wr5":  res["best_eval"]["wr5"],
        "baseline_eval_wr5": res["baseline_eval"]["wr5"],
        "opt_period":     f"{OPT_START} → {OPT_END}",
        "eval_period":    f"{EVAL_START} → {EVAL_END}",
    }
    out_path.write_text(_json.dumps(save_data, indent=2))
    log.info("Results saved → %s", out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",  default="v3b")
    parser.add_argument("--trials", type=int, default=100)
    args = parser.parse_args()
    main(model_version=args.model, n_trials=args.trials)
