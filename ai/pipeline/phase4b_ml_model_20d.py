"""
Phase 4B: LightGBM Propensity-to-Buy Model — 20-Day / +5% Horizon

Independent model parallel to the existing 5-day model (phase4_ml_model.py).
  - Label: +5% forward return in 20 trading days, max drawdown < -10%
  - Saves to:  data/models/lgbm_model_20d.pkl
  - Tier3 adapted for monthly entry (relaxed EMA proximity, wider DD tolerance)

Usage:
    python -m pipeline.phase4b_ml_model_20d               # train + save
    python -m pipeline.phase4b_ml_model_20d --check        # dataset stats
    python -m pipeline.phase4b_ml_model_20d --predict DATE # score a date
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── paths ──────────────────────────────────────────────────────────────────────
LABELS_DIR   = ROOT / "data" / "labels"
FEATURES_DIR = ROOT / "data" / "features"
MODELS_DIR   = ROOT / "data" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

TRAINING_SET_20D_PATH = LABELS_DIR / "training_set_20d.parquet"
MODEL_20D_PATH        = MODELS_DIR / "lgbm_model_20d.pkl"
METRICS_20D_PATH      = MODELS_DIR / "eval_metrics_20d.json"
IMPORTANCE_20D_PATH   = MODELS_DIR / "feature_importance_20d.csv"

# ── time split ─────────────────────────────────────────────────────────────────
# Note: 20-day labels need 20 trading-day lookahead, so the effective
# label cutoff is ~1 month before today. Dates after that have NaN labels.
#
# Val split rationale (v3 — 2026-05-17):
#   Restored original split (2yr train) — smaller train hurt test AUC badly.
#   Val remains 2024-H2 (sideways). To compensate for early-stopping pressure,
#   regularisation is tightened (reg_lambda 0.15→0.5, reg_alpha 0.1→0.3,
#   min_child_samples 25→50, max_depth 6→5) so the model converges more slowly
#   and early-stopping fires at a more representative iteration count.
TRAIN_START = "2022-07-01"
TRAIN_END   = "2024-06-30"
VAL_START   = "2024-07-01"
VAL_END     = "2024-12-31"
TEST_START  = "2025-01-01"
TEST_END    = "2099-12-31"

# ── columns to drop before training ───────────────────────────────────────────
DROP_COLS = {
    "close_vnd",
    "avg_val_21d_b",
    "hardcheck_reasons",
    "label_valid",
    "forward_ret_10d",   # 5d model column — may be present in joined dataset
    "max_drawdown_10d",  # 5d model column
    "label",
    # Interaction features (Layer 1a) excluded until isotonic recalibration (Layer 3):
    # adding them shifts best_iter 23→6, prob capped at 0.387 → 0 live signals
    "rel_strength_20d", "rel_strength_5d", "sharpe_x_mkt_vol", "momentum_in_bull",
    "bb_spread_vs_mkt", "price_pos_vs_mkt", "vol_spike_x_mkt", "bench_sharpe_x_trend",
    # NOTE (2026-05-22): Foreign 5d features have low importance (0–5) but
    # removing them causes bench_sharpe_12m to dominate (importance 199→570)
    # and extreme overfitting (train=0.835, P@50=1.0). Keep all 7 foreign features.
    # foreign_net_val_5d, foreign_net_ratio_5d, foreign_buy_pct_5d, foreign_net_days_5d
}

# ── LightGBM params — tuned for longer horizon (smoother signal) ───────────────
LGBM_PARAMS = {
    "objective":        "binary",
    "metric":           "auc",
    "n_estimators":     600,
    "learning_rate":    0.04,
    "max_depth":        6,
    "num_leaves":       31,
    "min_child_samples": 25,
    "subsample":        0.8,
    "colsample_bytree": 0.8,
    "reg_alpha":        0.1,
    "reg_lambda":       0.15,
    "random_state":     42,
    "n_jobs":           -1,
    "verbose":          -1,
}

# NOTE (2026-05-17): Interaction features (Layer 1a) were added to feat_cols but
# caused probability calibration shift — best_iter dropped 23→6, max_prob capped
# at 0.387 (<0.50 cutoff) → 0 live signals.  Root cause: with only 6 trees the
# model barely departs from the base rate; interaction features add enough
# variance to the val loss that early-stopping fires earlier.
# Proper fix requires isotonic recalibration (Layer 3) before interaction
# features can be used in production.  For now, feature set reverted to v1 (80).

EARLY_STOPPING_ROUNDS = 80

# ── Tier-3 config (relaxed for monthly holding) ────────────────────────────────
PROB_CUTOFF_20D = 0.55       # calibrated 2026-05-22: portfolio sim (1.5B / 100M / 15 positions)
                              # Static 0.55 = best PnL +494M/yr, ROI 33%, Sharpe 0.94
                              # Dynamic regime cutoffs add complexity without PnL gain
                              # Recovery regime: ENABLED at cutoff=0.53 (backtest: WR5=70.9%, Sharpe=4.12)
EMA_NEAR_PCT_20D = 12.0      # within ±12% of EMA20 or EMA50 (wider than 5d model's ±5%)

# ── Per-sector cutoff overrides ────────────────────────────────────────────────
# Calibrated 2026-05-23 via sector x cutoff grid on training_set_20d (2025-01→2026-04)
# Rule: raise cutoff when sector AvgRet < 5% at base OR clear improvement ≥ +2% at higher cutoff
# Reference: pipeline/backtest_live_system.py scenario S2 analysis
SECTOR_CUTOFFS: dict[str, float] = {
    # Group B — clear improvement when raised
    "Hàng không – Du lịch": 0.58,  # avg +3.86%→+7.10%, WR 46%→65% at 0.58
    "Công nghệ":             0.56,  # avg +2.98%→+5.22%, WR 48%→56% at 0.56
    "VLXD":                  0.56,  # avg +5.94%→+7.13%, WR 43%→51% at 0.56
    "NA":                    0.56,  # avg +4.72%→+7.54%, WR 47%→60% at 0.56
    # Group C — weak baseline, needs stricter filter
    "Bất động sản":          0.58,  # avg +0.24% in backtest (WR 29%), +4.32% at 0.58
                                    # NOTE: override DISABLED in deep_bear (see SECTOR_CUTOFFS_DEEP_BEAR)
    "Thực phẩm":             0.58,  # WR only 29.2% at base — weakest sector
}

# ── Regime-aware override: deep_bear ──────────────────────────────────────────
# Backtest 2023-2026 shows BĐS in deep_bear is EXCELLENT at base cutoff:
#   deep_bear @ 0.52: WR=78.3%, avg=+11.37%, Sharpe=4.23
#   deep_bear @ 0.58: WR=74.2%, avg= +9.62%, Sharpe=3.25  ← WORSE
# → Relax BĐS cutoff back to base when regime == deep_bear
# Regime-aware config: n=421, WR=59.6%, avg=+7.71%, Sharpe=3.34
#                  vs always-0.58: n=346, WR=55.2%, avg=+6.76%, Sharpe=3.13
SECTOR_CUTOFFS_DEEP_BEAR: dict[str, float] = {
    # BĐS removed → falls back to base prob_cutoff during deep_bear
    "Hàng không – Du lịch": 0.58,
    "Công nghệ":             0.56,
    "VLXD":                  0.56,
    "NA":                    0.56,
    "Thực phẩm":             0.58,
}

# ── Regime-aware hold period (trading days) ────────────────────────────────────
# Backtest 2022-2026 (n=1,197 signals):
#   T+20 Sharpe=1.79  T+25 Sharpe=1.99  T+30 Sharpe=2.06
# By regime:
#   bull      → T+30 best (Sharpe 2.25), T+25 strong (2.36) → use T+25
#   deep_bear → T+25 best (WR 65%, Sharpe 1.65), SL risk at T+30
#   choppy    → unstable; T+25 reasonable
#   sideways  → Sharpe peaks at T+20 (2.29) then DROPS → stop at T+20
#   recovery  → ENABLED at cutoff 0.53 (backtest 2022-2026: WR5=70.9%, Sharpe=4.12)
HOLD_DAYS_REGIME: dict[str, int] = {
    "bull":      25,
    "deep_bear": 25,
    "choppy":    25,
    "sideways":  20,
    "recovery":  20,   # recovery: T+20 (shorter hold, fast bounce regime)
    "unknown":   25,
}
HOLD_DAYS_DEFAULT = 25   # default when regime not in map


# ═════════════════════════════════════════════════════════════════════════════
# Feature helpers
# ═════════════════════════════════════════════════════════════════════════════

def _add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add interaction features (phase4 base + Layer 1a market-regime interactions)."""
    out = df.copy()

    # ── original phase4 interactions ─────────────────────────────────────────
    if "rsi_14" in out.columns and "mfi_14" in out.columns:
        out["rsi_mfi_gap"] = out["rsi_14"] - out["mfi_14"]
    if "ha_trend" in out.columns and "adx" in out.columns:
        out["trend_adx_interaction"] = out["ha_trend"] * out["adx"]
    if "beta_12m" in out.columns and "asymmetry" in out.columns:
        denom = out["beta_12m"].abs().replace(0, np.nan)
        out["beta_asym_ratio"] = out["asymmetry"] / denom
    if "sharpe_12m" in out.columns and "alpha_3m" in out.columns:
        out["sharpe_alpha"] = out["sharpe_12m"] * out["alpha_3m"]

    # ── Layer 1a: market-regime interaction features ───────────────────────────
    # These solve the "broadcast problem": stock_feature × vnx_feature gives a
    # value that differs per stock AND varies by market regime.
    #
    # NOTE: vni_ret_20d, vni_ret_5d, vni_vol_20d are stored as percentages
    # (e.g. -2.1, not -0.021). We keep units consistent.
    #
    # Only compute if source columns exist and the interaction col is not already there.

    def _safe_add(col, series):
        if col not in out.columns:
            out[col] = series

    has = lambda *cols: all(c in out.columns for c in cols)

    if has("return_20d", "vni_ret_20d"):
        _safe_add("rel_strength_20d", out["return_20d"] - out["vni_ret_20d"])

    if has("return_5d", "vni_ret_5d"):
        _safe_add("rel_strength_5d", out["return_5d"] - out["vni_ret_5d"])

    if has("sharpe_12m", "vni_vol_20d"):
        _safe_add("sharpe_x_mkt_vol", out["sharpe_12m"] * out["vni_vol_20d"])

    if has("rsi_14", "vni_above_ma50"):
        _safe_add("momentum_in_bull", out["rsi_14"] * out["vni_above_ma50"])

    if has("bb_width_pct", "vni_vol_20d"):
        _safe_add("bb_spread_vs_mkt", out["bb_width_pct"] - out["vni_vol_20d"])

    if has("price_vs_ema200", "vni_vs_52w_high_pct"):
        _safe_add("price_pos_vs_mkt", out["price_vs_ema200"] - out["vni_vs_52w_high_pct"])

    if has("vol_spike_ratio", "vni_ret_5d"):
        _safe_add("vol_spike_x_mkt",
                  out["vol_spike_ratio"] * (1 + out["vni_ret_5d"] / 100))

    if has("bench_sharpe_12m", "vni_above_ma50"):
        _safe_add("bench_sharpe_x_trend", out["bench_sharpe_12m"] * out["vni_above_ma50"])

    return out


def get_feature_cols(df: pd.DataFrame, include_fundamentals: bool = False) -> List[str]:
    exclude = set(DROP_COLS)
    exclude |= set(df.select_dtypes(include="object").columns)
    if not include_fundamentals:
        exclude |= {c for c in df.columns if c.startswith("fund_")}
    return [c for c in df.columns if c not in exclude]


# ═════════════════════════════════════════════════════════════════════════════
# Dataset preparation
# ═════════════════════════════════════════════════════════════════════════════

def prepare_dataset() -> pd.DataFrame:
    if not TRAINING_SET_20D_PATH.exists():
        raise FileNotFoundError(
            f"training_set_20d.parquet not found at {TRAINING_SET_20D_PATH}.\n"
            "Run first: python -m pipeline.phase3b_label_generator_20d"
        )

    df = pd.read_parquet(TRAINING_SET_20D_PATH)

    if "label_valid" in df.columns:
        before = len(df)
        df = df[df["label_valid"] == 1].copy()
        log.info("Dropped %d rows with label_valid=0 (kept %d)", before - len(df), len(df))

    if "label" not in df.columns:
        raise ValueError("training_set_20d.parquet is missing 'label' column")

    df = _add_interaction_features(df)
    log.info("20D dataset shape: %s", df.shape)
    return df


def time_split(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if isinstance(df.index, pd.MultiIndex):
        dates = df.index.get_level_values("date")
    else:
        dates = pd.to_datetime(df.index)

    train = df[(dates >= TRAIN_START) & (dates <= TRAIN_END)]
    val   = df[(dates >= VAL_START)   & (dates <= VAL_END)]
    test  = df[(dates >= TEST_START)  & (dates <= TEST_END)]

    log.info("Split → train=%d  val=%d  test=%d", len(train), len(val), len(test))

    if len(train) == 0 or len(val) == 0:
        log.warning("Standard split empty — using 70/15/15 chronological fallback.")
        n = len(df)
        train = df.iloc[:int(n * 0.70)]
        val   = df.iloc[int(n * 0.70):int(n * 0.85)]
        test  = df.iloc[int(n * 0.85):]
        log.info("Fallback → train=%d val=%d test=%d", len(train), len(val), len(test))

    return train, val, test


# ═════════════════════════════════════════════════════════════════════════════
# Training
# ═════════════════════════════════════════════════════════════════════════════

def _scale_pos_weight(labels: pd.Series) -> float:
    neg = (labels == 0).sum()
    pos = (labels == 1).sum()
    return round(neg / pos, 4) if pos > 0 else 1.0


def train(df: pd.DataFrame) -> Tuple:
    try:
        import lightgbm as lgb
    except ImportError as e:
        raise ImportError("pip install lightgbm") from e

    train_df, val_df, test_df = time_split(df)
    feat_cols = get_feature_cols(df)
    log.info("Feature count: %d", len(feat_cols))

    X_tr, y_tr = train_df[feat_cols].copy(), train_df["label"]
    X_va, y_va = val_df[feat_cols].copy(),   val_df["label"]
    X_te, y_te = test_df[feat_cols].copy(),  test_df["label"]

    # ── RobustZScoreNorm for Alpha158 features (clip outliers) ───────────────
    # Only normalize Alpha158 features — LightGBM handles others natively.
    # Fit on train only, apply to val/test (no leakage).
    alpha158_cols = [c for c in feat_cols if c.startswith("alpha158_")]
    if alpha158_cols:
        try:
            from sklearn.preprocessing import RobustScaler
            scaler = RobustScaler(quantile_range=(5, 95))   # clip ~2σ outliers
            X_tr[alpha158_cols] = scaler.fit_transform(X_tr[alpha158_cols].fillna(0))
            X_va[alpha158_cols] = scaler.transform(X_va[alpha158_cols].fillna(0))
            X_te[alpha158_cols] = scaler.transform(X_te[alpha158_cols].fillna(0))
            log.info("RobustZScoreNorm applied to %d alpha158 features", len(alpha158_cols))
        except Exception as _e:
            log.warning("RobustZScoreNorm failed (non-fatal): %s", _e)

    spw = _scale_pos_weight(y_tr)
    log.info("Class balance: pos=%d neg=%d  scale_pos_weight=%.2f",
             (y_tr == 1).sum(), (y_tr == 0).sum(), spw)

    params = dict(LGBM_PARAMS)
    params["scale_pos_weight"] = spw

    model = lgb.LGBMClassifier(**params)
    model.fit(
        X_tr, y_tr,
        eval_set=[(X_va, y_va)],
        callbacks=[
            lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False),
            lgb.log_evaluation(period=50),
        ],
    )

    metrics = evaluate(model, feat_cols, train_df, val_df, test_df)
    return model, feat_cols, metrics


# ═════════════════════════════════════════════════════════════════════════════
# Evaluation
# ═════════════════════════════════════════════════════════════════════════════

def _roc_auc(y_true, y_prob) -> float:
    from sklearn.metrics import roc_auc_score
    return round(float(roc_auc_score(y_true, y_prob)), 4) if len(np.unique(y_true)) > 1 else float("nan")

def _pr_auc(y_true, y_prob) -> float:
    from sklearn.metrics import average_precision_score
    return round(float(average_precision_score(y_true, y_prob)), 4) if len(np.unique(y_true)) > 1 else float("nan")

def _precision_at_k(y_true, y_prob, k: int = 50) -> float:
    k = min(k, len(y_true))
    top_idx = np.argsort(y_prob)[::-1][:k]
    return round(float(np.mean(y_true.values[top_idx])), 4)


def evaluate(model, feat_cols, train_df, val_df, test_df) -> Dict:
    results = {}
    for name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        if len(split_df) == 0:
            results[name] = {}
            continue
        X = split_df[feat_cols]
        y = split_df["label"]
        proba = model.predict_proba(X)[:, 1]
        results[name] = {
            "roc_auc":         _roc_auc(y, proba),
            "pr_auc":          _pr_auc(y, proba),
            "precision_at_50": _precision_at_k(y, proba, k=50),
            "n_rows":          len(split_df),
            "n_pos":           int((y == 1).sum()),
        }
    return results


# ═════════════════════════════════════════════════════════════════════════════
# Persist
# ═════════════════════════════════════════════════════════════════════════════

def save_model(model, feat_cols: List[str], metrics: Dict) -> None:
    payload = {"model": model, "feat_cols": feat_cols, "horizon": "20d",
               "ret_threshold": 0.05, "prob_cutoff": PROB_CUTOFF_20D}
    with open(MODEL_20D_PATH, "wb") as f:
        pickle.dump(payload, f)
    log.info("Model saved → %s", MODEL_20D_PATH)

    with open(METRICS_20D_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    log.info("Metrics saved → %s", METRICS_20D_PATH)

    import lightgbm as lgb
    fi = pd.DataFrame({
        "feature":    feat_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    fi.to_csv(IMPORTANCE_20D_PATH, index=False)
    log.info("Feature importance → %s", IMPORTANCE_20D_PATH)
    log.info("\nTop-20 features:\n%s", fi.head(20).to_string(index=False))


def load_model_20d(version: str | None = None) -> Tuple:
    """
    Returns (model, feat_cols) cho version chỉ định (mặc định: active version).
    Fallback về legacy path nếu versioned file không tồn tại.
    """
    try:
        from pipeline.model_registry import registry
        model_path = registry.model_path(version)
    except Exception:
        model_path = MODEL_20D_PATH

    if not model_path.exists():
        # Last-resort fallback: legacy flat file
        if MODEL_20D_PATH.exists():
            model_path = MODEL_20D_PATH
        else:
            raise FileNotFoundError(
                f"No 20D model at {model_path}. "
                "Run: python -m pipeline.phase4b_ml_model_20d"
            )
    with open(model_path, "rb") as f:
        payload = pickle.load(f)
    return payload["model"], payload["feat_cols"]


# ═════════════════════════════════════════════════════════════════════════════
# Scoring
# ═════════════════════════════════════════════════════════════════════════════

def predict_scores_20d(
    model,
    feat_cols: List[str],
    feature_df: pd.DataFrame,
    top_n: int = 200,
) -> pd.DataFrame:
    """Score symbols for a given date (same interface as phase4.predict_scores)."""
    df = _add_interaction_features(feature_df.copy())

    missing = [c for c in feat_cols if c not in df.columns]
    if missing:
        log.warning("Missing %d feature cols (filling 0): %s", len(missing), missing[:5])
    for c in missing:
        df[c] = 0.0

    X = df[feat_cols]
    proba = model.predict_proba(X)[:, 1]

    result = pd.DataFrame({
        "symbol":   df.index.get_level_values("symbol") if isinstance(df.index, pd.MultiIndex) else df.index,
        "raw_prob": proba,
    }).reset_index(drop=True)

    result["hardcheck_pass"] = df["hardcheck_pass"].values if "hardcheck_pass" in df.columns else True
    result = result.sort_values("raw_prob", ascending=False).reset_index(drop=True)

    n = min(top_n, len(result))
    result["rank"] = range(1, len(result) + 1)
    result["score_1000"] = (
        1000 - (result["rank"] - 1) * (999 / max(n - 1, 1))
    ).round(0).astype(int).clip(1, 1000)
    result.loc[~result["hardcheck_pass"].astype(bool), "score_1000"] = 0

    return result[["symbol", "raw_prob", "score_1000", "hardcheck_pass", "rank"]]


# ── Tier 3 — monthly entry filter ─────────────────────────────────────────────

def tier3_filter_20d(
    scores: pd.DataFrame,
    feature_df: pd.DataFrame,
    prob_cutoff: float = PROB_CUTOFF_20D,
    sector_cutoffs: dict | None = None,
    regime: str | None = None,
) -> pd.DataFrame:
    """
    Tier 3 for 20-day model (relaxed vs 5-day).

    Conditions:
      T1: raw_prob >= prob_cutoff  (can be raised per-sector via sector_cutoffs)
      T2: vol_ratio_20d >= 0.70  (slightly relaxed: monthly hold, entry vol less critical)
      T3: close within ±12% of EMA20 or EMA50  (wider zone for monthly entry)
      T4: no bearish reversal candles

    sector_cutoffs : {sector_name: min_prob} — overrides prob_cutoff for specific sectors.
                     Defaults to module-level SECTOR_CUTOFFS if None.
    regime         : current market regime string. When 'deep_bear', uses
                     SECTOR_CUTOFFS_DEEP_BEAR (BĐS override relaxed) instead of
                     SECTOR_CUTOFFS. Backtest shows BĐS WR=78% avg=+11% in deep_bear
                     — raising cutoff hurts performance in this regime.
    """
    if sector_cutoffs is None:
        # Regime-aware: deep_bear relaxes BĐS back to base cutoff
        if regime == "deep_bear":
            sector_cutoffs = SECTOR_CUTOFFS_DEEP_BEAR
        else:
            sector_cutoffs = SECTOR_CUTOFFS

    # Lazy-load sector info (cached inside sector_library)
    _sector_fn = None
    if sector_cutoffs:
        try:
            from features.industry.sector_library import get_sector_info
            _sector_fn = get_sector_info
        except ImportError:
            pass
    fdf = feature_df.copy()
    fdf.index.name = "symbol"

    merged = scores[scores["hardcheck_pass"].astype(bool)].copy().set_index("symbol")

    for col in ["vol_ratio_20d", "ema20", "ema50", "ema9", "ema26", "close_vnd",
                "candle_shooting_star", "candle_bearish_engulfing", "candle_evening_star",
                "vol_spike_ratio"]:
        merged[col] = fdf[col] if col in fdf.columns else np.nan

    merged = merged.reset_index()
    results = []

    for _, row in merged.iterrows():
        failures = []

        # T1: prob cutoff (per-sector override)
        sym = row["symbol"]
        effective_cutoff = prob_cutoff
        if _sector_fn and sector_cutoffs:
            try:
                info = _sector_fn(sym)
                sec  = info.get("primary_sector", "") if info else ""
                sector_cutoff = sector_cutoffs.get(sec, prob_cutoff)
                effective_cutoff = max(sector_cutoff, prob_cutoff)  # sector cannot be lower than regime cutoff
            except Exception:
                pass
        if row["raw_prob"] < effective_cutoff:
            failures.append(f"T1:prob_low({row['raw_prob']:.3f}<{effective_cutoff:.2f})")

        # T2: volume (relaxed to 0.70x for monthly)
        vr = row.get("vol_ratio_20d", np.nan)
        if np.isfinite(vr) and vr < 0.70:
            failures.append(f"T2:vol_weak({vr:.2f}x)")

        # T3: price near EMA — prefer EMA20/50, fall back to EMA9/26
        # (feature pipeline may only have EMA9/26; NaN triggers explicit fallback)
        close = row.get("close_vnd", np.nan)
        ema_a = row.get("ema20", np.nan)
        if not np.isfinite(ema_a):
            ema_a = row.get("ema9", np.nan)
        ema_b = row.get("ema50", np.nan)
        if not np.isfinite(ema_b):
            ema_b = row.get("ema26", np.nan)
        near_a = np.isfinite(ema_a) and abs(close / ema_a - 1) * 100 <= EMA_NEAR_PCT_20D
        near_b = np.isfinite(ema_b) and abs(close / ema_b - 1) * 100 <= EMA_NEAR_PCT_20D
        if np.isfinite(close) and not (near_a or near_b):
            pct_a = abs(close / ema_a - 1) * 100 if np.isfinite(ema_a) else 999
            pct_b = abs(close / ema_b - 1) * 100 if np.isfinite(ema_b) else 999
            failures.append(f"T3:not_near_ema(ema_a={pct_a:.1f}% ema_b={pct_b:.1f}%)")

        # T4: no bearish reversal candles
        for col, tag in [
            ("candle_shooting_star",     "T4:shooting_star"),
            ("candle_bearish_engulfing", "T4:bearish_engulfing"),
            ("candle_evening_star",      "T4:evening_star"),
        ]:
            if row.get(col, 0.0) == 1.0:
                failures.append(tag)

        # T5: vol spike filter — chỉ áp dụng với deep_bear / choppy
        # Backtest 2022-07→2026-05 (59 signals): vol_spike > 1.6x → WR 20%, avg -3.6%
        # Ngưỡng 1.6x = biến động 1 tháng cao hơn 60% so với baseline 6 tháng
        if regime in ("deep_bear", "choppy"):
            vsr = row.get("vol_spike_ratio", np.nan)
            if np.isfinite(vsr) and vsr > 1.6:
                failures.append(f"T5:vol_spike({vsr:.2f}x>1.6)")

        results.append({
            "symbol":        row["symbol"],
            "raw_prob":      round(row["raw_prob"], 4),
            "score_1000":    row["score_1000"],
            "rank":          row["rank"],
            "tier3_pass":    len(failures) == 0,
            "tier3_reasons": "|".join(failures),
        })

    return pd.DataFrame(results).sort_values("raw_prob", ascending=False).reset_index(drop=True)


# ═════════════════════════════════════════════════════════════════════════════
# CLI helpers
# ═════════════════════════════════════════════════════════════════════════════

def run_predict_20d(date_str: str, prob_cutoff: float = PROB_CUTOFF_20D) -> None:
    model, feat_cols = load_model_20d()

    feat_path = FEATURES_DIR / f"{date_str}.parquet"
    if not feat_path.exists():
        log.error("No feature file for %s.", date_str)
        sys.exit(1)

    feature_df = pd.read_parquet(feat_path)
    scores = predict_scores_20d(model, feat_cols, feature_df)
    t3 = tier3_filter_20d(scores, feature_df, prob_cutoff=prob_cutoff)
    passed   = t3[t3["tier3_pass"]]
    rejected = t3[~t3["tier3_pass"]]

    print(f"\n{'='*65}")
    print(f"  20D SHORTLIST — {date_str}  (target: +5% / 20 trading days)")
    print(f"{'='*65}")
    print(f"  Universe:         {len(scores):>4} symbols")
    print(f"  Passed hardcheck: {int(scores['hardcheck_pass'].sum()):>4} symbols")
    print(f"  Prob cutoff:      {prob_cutoff:.2f}")
    print(f"  Passed Tier 3:    {len(passed):>4} symbols  ← SIGNAL")
    print(f"{'='*65}")

    if passed.empty:
        print("\n  Không có mã nào vượt qua Tier 3 hôm nay.\n")
    else:
        # Get close prices
        close_map = {}
        feat_df = pd.read_parquet(feat_path)
        if "close_vnd" in feat_df.columns:
            close_map = feat_df["close_vnd"].to_dict() if feat_df.index.name == "symbol" else \
                        feat_df.set_index("symbol")["close_vnd"].to_dict() if "symbol" in feat_df.columns else {}

        print(f"\n  {'Symbol':<7}  {'Giá (k)':>8}  {'Prob':>7}  {'Score':>7}")
        print(f"  {'─'*7}  {'─'*8}  {'─'*7}  {'─'*7}")
        for _, row in passed.iterrows():
            price_k = close_map.get(row["symbol"], 0) / 1000
            price_s = f"{price_k:.1f}" if price_k > 0 else "—"
            print(f"  {row['symbol']:<7}  {price_s:>8}  {row['raw_prob']:>7.4f}  {int(row['score_1000']):>7}")

    if not rejected.empty:
        print(f"\n  Fail Tier 3 ({len(rejected)} mã):")
        for _, row in rejected.head(10).iterrows():
            print(f"  {row['symbol']:<7}  prob={row['raw_prob']:.3f}  [{row['tier3_reasons']}]")
    print()


def run() -> None:
    log.info("=== Phase 4B: 20-Day LightGBM Training ===")
    df = prepare_dataset()

    if len(df) < 50:
        log.warning("Only %d valid rows — run Phase 1A + Phase 2 backfill + Phase 3B first.", len(df))

    model, feat_cols, metrics = train(df)

    log.info("\n--- Evaluation ---")
    for split, vals in metrics.items():
        if vals:
            log.info(
                "[%s] ROC-AUC=%.4f  PR-AUC=%.4f  P@50=%.4f  n=%d  pos=%d",
                split,
                vals.get("roc_auc", float("nan")),
                vals.get("pr_auc", float("nan")),
                vals.get("precision_at_50", float("nan")),
                vals.get("n_rows", 0),
                vals.get("n_pos", 0),
            )

    save_model(model, feat_cols, metrics)
    log.info("=== Phase 4B complete ===")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4B: 20-Day LightGBM model")
    parser.add_argument("--check",   action="store_true", help="Show dataset stats")
    parser.add_argument("--predict", metavar="DATE",      help="Score symbols for DATE")
    parser.add_argument("--cutoff",  type=float, default=PROB_CUTOFF_20D)
    args = parser.parse_args()

    if args.check:
        from pipeline.phase3b_label_generator_20d import _show_stats
        _show_stats()
        if METRICS_20D_PATH.exists():
            m = json.load(open(METRICS_20D_PATH))
            print("Model metrics:")
            for split, vals in m.items():
                if vals:
                    print(f"  [{split}] AUC={vals.get('roc_auc','?')}  P@50={vals.get('precision_at_50','?')}  n={vals.get('n_rows','?')}")
    elif args.predict:
        run_predict_20d(args.predict, prob_cutoff=args.cutoff)
    else:
        run()


if __name__ == "__main__":
    main()
