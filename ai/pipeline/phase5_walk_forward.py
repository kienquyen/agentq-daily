"""
Phase 5 — Walk-Forward Training

Retrains LightGBM monthly on a rolling 18-month window to keep the model
aligned with the current market regime instead of decaying on a stale snapshot.

Two modes:

  Backtest  — simulates monthly retraining from a start date forward.
              For each month M, trains on [M-18m, M-3m], validates on
              [M-3m, M], then evaluates signals on [M, M+1m].
              Reports win-rate evolution vs the static baseline.

  Retrain   — trains on the latest 18 months of data and overwrites
              data/models/lgbm_model.pkl.  Run monthly via cron.

Usage:
    python -m pipeline.phase5_walk_forward --backtest
    python -m pipeline.phase5_walk_forward --backtest --start 2024-01-01
    python -m pipeline.phase5_walk_forward --retrain
    python -m pipeline.phase5_walk_forward --retrain --train-months 18
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

MODELS_DIR  = ROOT / "data" / "models"
WF_DIR      = MODELS_DIR / "walk_forward"
WF_DIR.mkdir(parents=True, exist_ok=True)

WF_RESULTS_PATH  = WF_DIR / "backtest_results.json"
WF_META_PATH     = WF_DIR / "retrain_meta.json"

# Default walk-forward config
TRAIN_MONTHS = 18
VAL_MONTHS   = 3
STEP_MONTHS  = 1

# Auto-retrain trigger: retrain when this many NEW labeled rows have
# accumulated since the last retrain.
# 198 symbols × 20 trading days ≈ 3,960 rows ≈ 1 calendar month.
RETRAIN_ROW_THRESHOLD  = 3_960
# Hard minimum: never retrain more often than this many calendar days.
RETRAIN_MIN_DAYS       = 5


# ── core training helper ───────────────────────────────────────────────────────

def _train_one_window(
    df: pd.DataFrame,
    train_start: pd.Timestamp,
    train_end: pd.Timestamp,
    val_start: pd.Timestamp,
    val_end: pd.Timestamp,
) -> Tuple:
    """
    Train one LightGBM model on a specific date window.
    Returns (model, feat_cols, val_auc).
    """
    import lightgbm as lgb
    from pipeline.phase4_ml_model import (
        get_feature_cols, _add_interaction_features,
        _compute_scale_pos_weight, LGBM_PARAMS, EARLY_STOPPING_ROUNDS,
    )

    dates = df.index.get_level_values("date")
    train_df = df[(dates >= train_start) & (dates <  val_start)].copy()
    val_df   = df[(dates >= val_start)   & (dates <= val_end)].copy()

    if len(train_df) < 500 or len(val_df) < 50:
        raise ValueError(
            f"Insufficient data: train={len(train_df)} val={len(val_df)}"
        )

    train_df = _add_interaction_features(train_df)
    val_df   = _add_interaction_features(val_df)
    feat_cols = get_feature_cols(train_df)

    X_train, y_train = train_df[feat_cols], train_df["label"]
    X_val,   y_val   = val_df[feat_cols],   val_df["label"]

    spw = _compute_scale_pos_weight(y_train)
    params = dict(LGBM_PARAMS)
    params["scale_pos_weight"] = spw

    model = lgb.LGBMClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[
            lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False),
            lgb.log_evaluation(period=9999),   # silent
        ],
    )

    from sklearn.metrics import roc_auc_score
    val_auc = round(float(roc_auc_score(y_val, model.predict_proba(X_val)[:, 1])), 4)

    return model, feat_cols, val_auc


# ── backtest ───────────────────────────────────────────────────────────────────

def backtest(
    start: str = "2024-01-01",
    end: Optional[str] = None,
    train_months: int = TRAIN_MONTHS,
    val_months: int = VAL_MONTHS,
    step_months: int = STEP_MONTHS,
    prob_cutoff: float = 0.60,
) -> pd.DataFrame:
    """
    Simulate monthly walk-forward retraining and evaluate next-month win rate.

    For each step date M (monthly from start → end):
      - Train:    [M - train_months,  M - val_months]
      - Val:      [M - val_months,    M]              (early stopping only)
      - Evaluate: [M,                 M + step_months]

    Returns DataFrame with one row per step.
    """
    from pipeline.phase4_ml_model import prepare_dataset, _add_interaction_features, get_feature_cols

    log.info("Loading dataset ...")
    df = prepare_dataset()
    dates = df.index.get_level_values("date")
    data_start = dates.min()
    data_end   = dates.max()

    if end is None:
        end = data_end.strftime("%Y-%m-%d")

    # Generate monthly step dates
    steps = pd.date_range(start=start, end=end, freq="MS")   # month-start
    log.info("Walk-forward backtest: %d steps  |  train=%dm  val=%dm  cutoff=%.2f",
             len(steps), train_months, val_months, prob_cutoff)
    log.info("Data range: %s → %s", data_start.date(), data_end.date())

    records = []

    for i, step in enumerate(steps, 1):
        train_start = step - pd.DateOffset(months=train_months)
        val_start   = step - pd.DateOffset(months=val_months)
        train_end   = step
        eval_end    = step + pd.DateOffset(months=step_months) - pd.Timedelta(days=1)

        # Skip if eval period is beyond data
        if step > data_end:
            log.info("  [%d/%d] %s — no evaluation data, stopping.", i, len(steps), step.date())
            break

        # Clamp to available data
        train_start = max(train_start, data_start)

        try:
            model, feat_cols, val_auc = _train_one_window(
                df,
                train_start=train_start,
                train_end=train_end,
                val_start=val_start,
                val_end=step - pd.Timedelta(days=1),
            )
        except ValueError as e:
            log.warning("  [%d/%d] %s — skipped: %s", i, len(steps), step.date(), e)
            continue

        # Evaluate on next month
        eval_df = df[(dates >= step) & (dates <= eval_end)].copy()
        eval_df = _add_interaction_features(eval_df)

        # Align columns
        for c in feat_cols:
            if c not in eval_df.columns:
                eval_df[c] = 0.0
        eval_df = eval_df[feat_cols + ["label"]]

        y_eval = eval_df["label"].values
        proba  = model.predict_proba(eval_df[feat_cols])[:, 1]

        mask      = proba >= prob_cutoff
        n_signals = int(mask.sum())
        n_days    = eval_df.index.get_level_values("date").nunique()
        win_rate  = float(y_eval[mask].mean()) if n_signals > 0 else float("nan")
        baseline  = float(y_eval.mean())

        rec = {
            "step_date":    step.strftime("%Y-%m-%d"),
            "train_start":  train_start.strftime("%Y-%m-%d"),
            "train_end":    (step - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "val_auc":      val_auc,
            "eval_rows":    len(eval_df),
            "eval_days":    n_days,
            "baseline":     round(baseline, 4),
            "n_signals":    n_signals,
            "signals_per_day": round(n_signals / max(n_days, 1), 1),
            "win_rate":     round(win_rate, 4) if not np.isnan(win_rate) else None,
            "lift":         round(win_rate - baseline, 4) if not np.isnan(win_rate) else None,
        }
        records.append(rec)

        log.info(
            "  [%d/%d] %s  val_auc=%.4f  win_rate=%s  signals/day=%.1f  lift=%s",
            i, len(steps), step.strftime("%Y-%m"),
            val_auc,
            f"{win_rate:.1%}" if not np.isnan(win_rate) else "n/a",
            n_signals / max(n_days, 1),
            f"{win_rate - baseline:+.1%}" if not np.isnan(win_rate) else "n/a",
        )

    result_df = pd.DataFrame(records)

    if not result_df.empty:
        _print_summary(result_df)
        WF_RESULTS_PATH.write_text(
            json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        log.info("Results saved → %s", WF_RESULTS_PATH)

    return result_df


def _print_summary(df: pd.DataFrame) -> None:
    log.info("\n%s", "=" * 70)
    log.info("WALK-FORWARD BACKTEST SUMMARY")
    log.info("=" * 70)

    valid = df[df["win_rate"].notna()]
    if valid.empty:
        log.info("No valid evaluation months.")
        return

    avg_wr   = valid["win_rate"].mean()
    avg_lift = valid["lift"].mean()
    avg_spd  = valid["signals_per_day"].mean()
    avg_vauc = valid["val_auc"].mean()

    log.info("  Months evaluated:     %d", len(valid))
    log.info("  Avg val AUC:          %.4f", avg_vauc)
    log.info("  Avg baseline:         %.1f%%", valid["baseline"].mean() * 100)
    log.info("  Avg win rate:         %.1f%%", avg_wr * 100)
    log.info("  Avg lift:             %+.1f%%", avg_lift * 100)
    log.info("  Avg signals/day:      %.1f", avg_spd)
    log.info("  Best month:           %s  (%.1f%%)",
             valid.loc[valid["win_rate"].idxmax(), "step_date"],
             valid["win_rate"].max() * 100)
    log.info("  Worst month:          %s  (%.1f%%)",
             valid.loc[valid["win_rate"].idxmin(), "step_date"],
             valid["win_rate"].min() * 100)

    log.info("\n  %-12s  %-10s  %-10s  %-8s  %-14s", "Month", "Win rate", "Baseline", "Lift", "Signals/day")
    log.info("  %s", "-" * 60)
    for _, row in valid.iterrows():
        wr = row["win_rate"]
        bl = row["baseline"]
        lt = row["lift"]
        log.info("  %-12s  %-10s  %-10s  %-8s  %-14s",
                 row["step_date"],
                 f"{wr:.1%}",
                 f"{bl:.1%}",
                 f"{lt:+.1%}",
                 f"{row['signals_per_day']:.1f}")
    log.info("=" * 70)


# ── production retrain ────────────────────────────────────────────────────────

def retrain_current(
    train_months: int = TRAIN_MONTHS,
    val_months: int = VAL_MONTHS,
) -> None:
    """
    Retrain on the latest `train_months` of data and save to lgbm_model.pkl.
    Run this monthly (e.g. first trading day of each month).
    """
    from pipeline.phase4_ml_model import prepare_dataset, MODEL_PATH

    log.info("=== Walk-Forward: Retrain Current Model ===")
    df = prepare_dataset()
    dates = df.index.get_level_values("date")
    data_end   = dates.max()
    train_start = data_end - pd.DateOffset(months=train_months)
    val_start   = data_end - pd.DateOffset(months=val_months)

    log.info("Train: %s → %s  |  Val: %s → %s",
             train_start.date(), (data_end - pd.DateOffset(months=val_months)).date(),
             val_start.date(), data_end.date())

    model, feat_cols, val_auc = _train_one_window(
        df,
        train_start=train_start,
        train_end=data_end,
        val_start=val_start,
        val_end=data_end,
    )
    log.info("Val AUC: %.4f", val_auc)

    payload = {"model": model, "feat_cols": feat_cols, "train_end": str(data_end.date())}
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(payload, f)
    log.info("Model saved → %s", MODEL_PATH)

    # Timestamped snapshot for rollback
    snapshot_path = WF_DIR / f"lgbm_{data_end.strftime('%Y%m%d')}.pkl"
    with open(snapshot_path, "wb") as f:
        pickle.dump(payload, f)
    log.info("Snapshot → %s", snapshot_path)

    # Update metadata so auto_retrain knows when this ran
    meta = _load_meta()
    meta["last_retrain_date"]    = pd.Timestamp.now().strftime("%Y-%m-%d")
    meta["rows_at_last_retrain"] = _count_labeled_rows()
    meta["train_end"]            = str(data_end.date())
    meta["val_auc"]              = val_auc
    _save_meta(meta)


# ── auto-retrain trigger ──────────────────────────────────────────────────────

def _load_meta() -> dict:
    if WF_META_PATH.exists():
        try:
            return json.loads(WF_META_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_meta(meta: dict) -> None:
    WF_META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def _count_labeled_rows() -> int:
    """Count current valid labeled rows in training_set.parquet."""
    from pipeline.phase4_ml_model import LABELS_DIR
    ts_path = LABELS_DIR / "training_set.parquet"
    if not ts_path.exists():
        return 0
    try:
        df = pd.read_parquet(ts_path, columns=["label_valid"])
        return int((df["label_valid"] == 1).sum())
    except Exception:
        return 0


def should_retrain(
    row_threshold: int = RETRAIN_ROW_THRESHOLD,
    min_days: int = RETRAIN_MIN_DAYS,
) -> tuple[bool, str]:
    """
    Check whether the model should be retrained.

    Returns (should_retrain: bool, reason: str).

    Triggers retrain when BOTH conditions are met:
      1. At least `min_days` calendar days since last retrain.
      2. At least `row_threshold` new labeled rows since last retrain.
    """
    meta = _load_meta()
    current_rows = _count_labeled_rows()
    today = pd.Timestamp.now().normalize()

    last_retrain_date = pd.Timestamp(meta["last_retrain_date"]) if "last_retrain_date" in meta else None
    rows_at_last      = meta.get("rows_at_last_retrain", 0)

    # First-ever run
    if last_retrain_date is None:
        return True, "no previous retrain found — first run"

    days_since = (today - last_retrain_date).days
    new_rows   = current_rows - rows_at_last

    if days_since < min_days:
        return False, f"only {days_since}d since last retrain (min={min_days}d)"

    if new_rows < row_threshold:
        return False, (
            f"{new_rows:,} new rows since last retrain "
            f"(need {row_threshold:,} ≈ {row_threshold // 198} trading days)"
        )

    return True, (
        f"{new_rows:,} new rows in {days_since}d "
        f"(threshold={row_threshold:,}, min_days={min_days})"
    )


def auto_retrain(
    row_threshold: int = RETRAIN_ROW_THRESHOLD,
    min_days: int = RETRAIN_MIN_DAYS,
    train_months: int = TRAIN_MONTHS,
    val_months: int = VAL_MONTHS,
) -> bool:
    """
    Check trigger conditions and retrain if met.
    Updates retrain_meta.json after a successful retrain.

    Returns True if retrain was performed, False otherwise.

    Designed to be called daily from a cron job:
        python -m pipeline.phase5_walk_forward --auto
    """
    triggered, reason = should_retrain(row_threshold=row_threshold, min_days=min_days)
    current_rows = _count_labeled_rows()

    if not triggered:
        log.info("Auto-retrain: skipped — %s", reason)
        log.info("  Current labeled rows: %d", current_rows)
        meta = _load_meta()
        if "last_retrain_date" in meta:
            log.info("  Last retrain:         %s  (%d rows)",
                     meta["last_retrain_date"], meta.get("rows_at_last_retrain", 0))
        return False

    log.info("Auto-retrain: triggered — %s", reason)
    retrain_current(train_months=train_months, val_months=val_months)

    # Update metadata
    meta = _load_meta()
    meta["last_retrain_date"]    = pd.Timestamp.now().strftime("%Y-%m-%d")
    meta["rows_at_last_retrain"] = current_rows
    meta["retrain_reason"]       = reason
    meta.setdefault("retrain_history", []).append({
        "date":   meta["last_retrain_date"],
        "rows":   current_rows,
        "reason": reason,
    })
    _save_meta(meta)
    log.info("Metadata saved → %s", WF_META_PATH)
    return True


def show_auto_status() -> None:
    """Print current trigger status without retraining."""
    meta = _load_meta()
    current_rows = _count_labeled_rows()
    triggered, reason = should_retrain()

    print(f"\n{'='*55}")
    print("Auto-Retrain Status")
    print(f"{'='*55}")
    print(f"  Current labeled rows:   {current_rows:,}")
    if "last_retrain_date" in meta:
        rows_then = meta.get("rows_at_last_retrain", 0)
        new_rows  = current_rows - rows_then
        days_since = (pd.Timestamp.now() - pd.Timestamp(meta["last_retrain_date"])).days
        print(f"  Last retrain:           {meta['last_retrain_date']}  ({rows_then:,} rows)")
        print(f"  New rows since:         {new_rows:,}  (need {RETRAIN_ROW_THRESHOLD:,})")
        print(f"  Days since retrain:     {days_since}  (min {RETRAIN_MIN_DAYS})")
    else:
        print("  Last retrain:           never")
    print(f"  Threshold:              {RETRAIN_ROW_THRESHOLD:,} rows ≈ {RETRAIN_ROW_THRESHOLD // 198} trading days")
    print(f"  Decision:               {'✓ RETRAIN' if triggered else '✗ skip'} — {reason}")

    history = meta.get("retrain_history", [])
    if history:
        print(f"\n  Retrain history ({len(history)} runs):")
        for h in history[-5:]:
            print(f"    {h['date']}  rows={h['rows']:,}  {h['reason']}")
    print(f"{'='*55}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description="Phase 5 — Walk-Forward Training")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--backtest", action="store_true", help="Run historical backtest")
    group.add_argument("--retrain",  action="store_true", help="Retrain on latest data (unconditional)")
    group.add_argument("--auto",     action="store_true", help="Retrain only if enough new data (cron mode)")
    group.add_argument("--status",   action="store_true", help="Show trigger status without retraining")
    p.add_argument("--start",        type=str, default="2024-01-01", help="Backtest start date")
    p.add_argument("--end",          type=str, default=None,         help="Backtest end date")
    p.add_argument("--train-months", type=int, default=TRAIN_MONTHS, help="Rolling window size (months)")
    p.add_argument("--val-months",   type=int, default=VAL_MONTHS,   help="Validation window (months)")
    p.add_argument("--cutoff",       type=float, default=0.58,       help="Prob cutoff for win-rate eval")
    p.add_argument("--row-threshold",type=int, default=RETRAIN_ROW_THRESHOLD,
                                                                      help="New rows needed to trigger retrain")
    p.add_argument("--min-days",     type=int, default=RETRAIN_MIN_DAYS,
                                                                      help="Min calendar days between retrains")
    args = p.parse_args()

    if args.backtest:
        backtest(
            start=args.start,
            end=args.end,
            train_months=args.train_months,
            val_months=args.val_months,
            prob_cutoff=args.cutoff,
        )
    elif args.retrain:
        retrain_current(
            train_months=args.train_months,
            val_months=args.val_months,
        )
    elif args.auto:
        auto_retrain(
            row_threshold=args.row_threshold,
            min_days=args.min_days,
            train_months=args.train_months,
            val_months=args.val_months,
        )
    elif args.status:
        show_auto_status()


if __name__ == "__main__":
    main()
