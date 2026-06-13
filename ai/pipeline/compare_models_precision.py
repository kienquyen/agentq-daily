"""
pipeline/compare_models_precision.py
So sánh v3a / v3b / v3d theo Precision@K và Mean Return@K trên test set.

Metrics:
  - AUC (ROC)
  - Precision@K  (WR của top K signals mỗi ngày)
  - Mean Return@K (return trung bình 20 ngày của top K)
  - Regime breakdown
  - Lift@K       (return@K / base positive rate)

Test set: 2025-01-01 → hiện tại

Chạy:
    python -m pipeline.compare_models_precision
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODELS_DIR = ROOT / "data" / "models"
LABELS_DIR = ROOT / "data" / "labels"

TEST_START = "2025-01-01"
KS = [10, 20, 50]

# ── Load data ─────────────────────────────────────────────────────────────────

def _load_test_set() -> pd.DataFrame:
    """
    Load test set với forward_ret (real 20d return) joined vào.
    """
    ts = pd.read_parquet(LABELS_DIR / "training_set_20d.parquet")

    # Filter test set
    dates = ts.index.get_level_values("date")
    test  = ts[dates >= TEST_START].copy()

    # Join forward_ret từ raw_labels (cột tên là forward_ret_10d dù là 20d)
    raw = pd.read_parquet(LABELS_DIR / "raw_labels_20d.parquet")
    raw.index = pd.MultiIndex.from_tuples(
        [(s, pd.Timestamp(d)) for s, d in raw.index], names=["symbol", "date"]
    )
    # Rename để rõ ràng
    raw = raw[["forward_ret_10d"]].rename(columns={"forward_ret_10d": "forward_ret_20d"})

    test = test.join(raw, how="left")
    print(f"Test set: {len(test):,} rows  |  {test['label'].mean()*100:.1f}% positive  "
          f"|  {test.index.get_level_values('date').min().date()} → "
          f"{test.index.get_level_values('date').max().date()}")
    return test


def _load_model(version: str):
    """Load model pkl từ versioned dir hoặc flat file."""
    versioned = MODELS_DIR / version / "lgbm_model_20d.pkl"
    flat      = MODELS_DIR / "lgbm_model_20d.pkl"
    path = versioned if versioned.exists() else flat
    with open(path, "rb") as f:
        payload = pickle.load(f)
    return payload["model"], payload["feat_cols"]


# ── Metrics ───────────────────────────────────────────────────────────────────

def precision_at_k(y_true: np.ndarray, y_prob: np.ndarray, k: int) -> float:
    k = min(k, len(y_true))
    top_idx = np.argsort(y_prob)[::-1][:k]
    return float(np.mean(y_true[top_idx]))


def mean_return_at_k(fwd_ret: np.ndarray, y_prob: np.ndarray, k: int) -> float:
    """Mean forward return of top-K signals."""
    k = min(k, len(y_prob))
    top_idx = np.argsort(y_prob)[::-1][:k]
    vals = fwd_ret[top_idx]
    valid = vals[~np.isnan(vals)]
    return float(np.mean(valid)) if len(valid) > 0 else float("nan")


def evaluate_model(model, feat_cols, test_df: pd.DataFrame) -> dict:
    """Compute all metrics for one model on test set."""
    # Only use cols available in model
    available = [c for c in feat_cols if c in test_df.columns]
    missing   = [c for c in feat_cols if c not in test_df.columns]

    X = test_df[available].copy()
    # Fill missing cols with 0
    for c in missing:
        X[c] = 0.0

    y       = test_df["label"].values.astype(float)
    fwd_ret = test_df["forward_ret_20d"].values.astype(float) \
              if "forward_ret_20d" in test_df.columns else np.full(len(y), np.nan)
    proba   = model.predict_proba(X[feat_cols])[:, 1]

    valid_mask = ~np.isnan(y)
    y_v    = y[valid_mask].astype(int)
    p_v    = proba[valid_mask]
    r_v    = fwd_ret[valid_mask]

    result = {
        "auc":          roc_auc_score(y_v, p_v) if len(np.unique(y_v)) > 1 else float("nan"),
        "n_test":       int(valid_mask.sum()),
        "pos_rate":     float(y_v.mean()),
        "missing_cols": len(missing),
    }

    for k in KS:
        result[f"p@{k}"]  = precision_at_k(y_v, p_v, k)
        result[f"ret@{k}"] = mean_return_at_k(r_v, p_v, k)

    return result, proba


def evaluate_by_regime(model, feat_cols, test_df: pd.DataFrame) -> dict:
    """Breakdown Precision@20 by regime."""
    if "regime_label" not in test_df.columns:
        return {}

    available = [c for c in feat_cols if c in test_df.columns]
    X = test_df[available].copy()
    for c in [c for c in feat_cols if c not in test_df.columns]:
        X[c] = 0.0
    proba = model.predict_proba(X[feat_cols])[:, 1]

    y       = test_df["label"].values.astype(float)
    fwd_ret = test_df["forward_ret_20d"].values.astype(float) \
              if "forward_ret_20d" in test_df.columns else np.full(len(y), np.nan)

    breakdown = {}
    for regime in test_df["regime_label"].unique():
        mask = (test_df["regime_label"] == regime).values & ~np.isnan(y)
        if mask.sum() < 20:
            continue
        breakdown[regime] = {
            "n":     int(mask.sum()),
            "p@20":  precision_at_k(y[mask].astype(int), proba[mask], 20),
            "ret@20": mean_return_at_k(fwd_ret[mask], proba[mask], 20),
        }
    return breakdown


# ── Daily top-K simulation ────────────────────────────────────────────────────

def simulate_daily_topk(model, feat_cols, test_df: pd.DataFrame, k: int = 20) -> pd.DataFrame:
    """
    Mỗi ngày: chọn top-K signals, tính WR và mean return.
    Giúp thấy variance và consistency theo thời gian.
    """
    available = [c for c in feat_cols if c in test_df.columns]
    X = test_df[available].copy()
    for c in [c for c in feat_cols if c not in test_df.columns]:
        X[c] = 0.0
    proba = model.predict_proba(X[feat_cols])[:, 1]

    test_copy        = test_df.copy()
    test_copy["prob"] = proba

    y       = test_df["label"].values.astype(float)
    fwd_ret = test_df["forward_ret_20d"].values.astype(float) \
              if "forward_ret_20d" in test_df.columns else np.full(len(y), np.nan)
    test_copy["label_f"]   = y
    test_copy["fwd_ret_f"] = fwd_ret

    dates = test_copy.index.get_level_values("date")
    test_copy["date_"] = dates

    rows = []
    for d, grp in test_copy.groupby("date_"):
        grp_valid = grp[~grp["label_f"].isna()]
        if len(grp_valid) < k:
            continue
        top = grp_valid.nlargest(k, "prob")
        wr  = float(top["label_f"].mean())
        mr  = float(top["fwd_ret_f"].dropna().mean()) if not top["fwd_ret_f"].isna().all() else float("nan")
        rows.append({"date": d, "wr": wr, "mean_ret": mr, "n_signals": len(top)})

    return pd.DataFrame(rows).set_index("date")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  Model Comparison: Precision@K + Mean Return@K on Test Set")
    print(f"  Test period: {TEST_START} → hiện tại")
    print("=" * 70)

    test_df = _load_test_set()

    models_to_compare = {
        "v3a": "v3a",
        "v3b": "v3b",
        "v3d": "v3d",
        "v3e": "v3e",
        "v3f": "v3f",
    }

    results   = {}
    regimes   = {}
    daily_sim = {}

    for name, version in models_to_compare.items():
        pkl_path = MODELS_DIR / version / "lgbm_model_20d.pkl"
        if not pkl_path.exists():
            print(f"  ⚠️  {name}: model not found at {pkl_path}")
            continue
        print(f"\nLoading {name} ({version})...")
        model, feat_cols = _load_model(version)
        metrics, proba   = evaluate_model(model, feat_cols, test_df)
        results[name]    = metrics

        # Regime breakdown
        reg_bkdn = evaluate_by_regime(model, feat_cols, test_df)
        if reg_bkdn:
            regimes[name] = reg_bkdn

        # Daily simulation @20
        daily_sim[name] = simulate_daily_topk(model, feat_cols, test_df, k=20)

    if not results:
        print("No models loaded.")
        return

    # ── Print comparison table ────────────────────────────────────────────────
    print("\n")
    print("=" * 70)
    print("  OVERALL METRICS")
    print("=" * 70)
    header = f"{'Metric':<18}" + "".join(f"{m:>12}" for m in results)
    print(header)
    print("-" * (18 + 12 * len(results)))

    # AUC
    row = f"{'AUC':<18}"
    for name, m in results.items():
        row += f"{m['auc']:>12.4f}"
    print(row)

    # Positive rate (base rate)
    row = f"{'Base rate':<18}"
    for name, m in results.items():
        row += f"{m['pos_rate']*100:>11.1f}%"
    print(row)

    # Precision@K
    for k in KS:
        row = f"{'Precision@'+str(k):<18}"
        for name, m in results.items():
            val = m.get(f"p@{k}", float("nan"))
            row += f"{val*100:>11.1f}%"
        print(row)

    # Mean Return@K
    print()
    for k in KS:
        row = f"{'MeanRet@'+str(k):<18}"
        for name, m in results.items():
            val = m.get(f"ret@{k}", float("nan"))
            if val == val:
                row += f"{val*100:>11.2f}%"
            else:
                row += f"{'N/A':>12}"
        print(row)

    # Lift (Precision@K / base rate)
    print()
    for k in KS:
        row = f"{'Lift@'+str(k):<18}"
        for name, m in results.items():
            p    = m.get(f"p@{k}", float("nan"))
            base = m.get("pos_rate", float("nan"))
            lift = p / base if base > 0 else float("nan")
            row += f"{lift:>12.2f}x"
        print(row)

    # ── Regime breakdown ──────────────────────────────────────────────────────
    if regimes:
        print("\n")
        print("=" * 70)
        print("  PRECISION@20 BY REGIME")
        print("=" * 70)
        all_regimes = sorted(set(r for bkdn in regimes.values() for r in bkdn))
        print(f"{'Regime':<14}" + "".join(f"{'P@20 ' + m:>14}" for m in regimes))
        print("-" * (14 + 14 * len(regimes)))
        for reg in all_regimes:
            row = f"{reg:<14}"
            for name, bkdn in regimes.items():
                if reg in bkdn:
                    p = bkdn[reg]["p@20"]
                    n = bkdn[reg]["n"]
                    row += f"{p*100:>10.1f}% ({n:4d})"
                else:
                    row += f"{'—':>14}"
            print(row)

        # Mean return by regime
        print()
        print(f"{'Regime':<14}" + "".join(f"{'Ret@20 '+m:>14}" for m in regimes))
        print("-" * (14 + 14 * len(regimes)))
        for reg in all_regimes:
            row = f"{reg:<14}"
            for name, bkdn in regimes.items():
                if reg in bkdn:
                    r = bkdn[reg].get("ret@20", float("nan"))
                    row += f"{r*100:>13.2f}%" if r == r else f"{'N/A':>14}"
                else:
                    row += f"{'—':>14}"
            print(row)

    # ── Daily simulation ──────────────────────────────────────────────────────
    if daily_sim:
        print("\n")
        print("=" * 70)
        print("  DAILY TOP-20 SIMULATION SUMMARY (2025-01-01 → now)")
        print("=" * 70)
        print(f"{'Metric':<28}" + "".join(f"{m:>12}" for m in daily_sim))
        print("-" * (28 + 12 * len(daily_sim)))

        metrics_daily = {
            "Mean daily WR@20":   lambda df: df["wr"].mean(),
            "Median daily WR@20": lambda df: df["wr"].median(),
            "Days WR > 50%":      lambda df: (df["wr"] > 0.5).mean(),
            "Days WR > 60%":      lambda df: (df["wr"] > 0.6).mean(),
            "Mean daily Ret@20":  lambda df: df["mean_ret"].mean(),
            "Sharpe (daily WR)":  lambda df: df["wr"].mean() / df["wr"].std() if df["wr"].std() > 0 else float("nan"),
        }

        for label, fn in metrics_daily.items():
            row = f"{label:<28}"
            for name, df in daily_sim.items():
                val = fn(df)
                if "WR" in label or "Days" in label:
                    row += f"{val*100:>11.1f}%"
                elif "Ret" in label:
                    row += f"{val*100:>11.2f}%"
                else:
                    row += f"{val:>12.3f}"
            print(row)

    print("\n")
    print("=" * 70)
    print("  INTERPRETATION")
    print("=" * 70)
    # Find best model per metric
    if len(results) > 1:
        for k in KS:
            best = max(results, key=lambda m: results[m].get(f"p@{k}", 0))
            best_val = results[best].get(f"p@{k}", 0) * 100
            print(f"  Best Precision@{k:<3}: {best} ({best_val:.1f}%)")

        for k in [20, 50]:
            best = max(
                (m for m in results if results[m].get(f"ret@{k}", float("nan")) == results[m].get(f"ret@{k}", float("nan"))),
                key=lambda m: results[m].get(f"ret@{k}", -999),
                default=None
            )
            if best:
                best_val = results[best].get(f"ret@{k}", 0) * 100
                print(f"  Best MeanRet@{k:<3} : {best} ({best_val:.2f}%)")

    print()


if __name__ == "__main__":
    main()
