#!/usr/bin/env python3
"""
Layer 1a full pipeline: patch parquets → rebuild training set → retrain 20d model.

Run:
    python -m pipeline.run_layer1a_retrain
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

METRICS_20D_PATH   = ROOT / "data" / "models" / "eval_metrics_20d.json"
IMPORTANCE_20D_PATH = ROOT / "data" / "models" / "feature_importance_20d.csv"

# ── Load BEFORE metrics for comparison ────────────────────────────────────────
before_metrics = None
if METRICS_20D_PATH.exists():
    with open(METRICS_20D_PATH) as f:
        before_metrics = json.load(f)
    print("Loaded BEFORE metrics:")
    for split, vals in before_metrics.items():
        if vals:
            print(f"  [{split}] AUC={vals.get('roc_auc','?')}  PR-AUC={vals.get('pr_auc','?')}  n={vals.get('n_rows','?')}")

before_n_features = None
if IMPORTANCE_20D_PATH.exists():
    fi_before = pd.read_csv(IMPORTANCE_20D_PATH)
    before_n_features = len(fi_before)
    vnx_nonzero_before = int((fi_before[fi_before["feature"].str.contains("vni_")]["importance"] > 0).sum())
    print(f"\nBEFORE: {before_n_features} features, VNX features with importance>0: {vnx_nonzero_before}")

print("\n" + "="*60)
print("STEP 1: Patching feature parquets with interaction features")
print("="*60)

from pipeline.patch_interaction_features import patch_all_parquets
patch_all_parquets()

print("\n" + "="*60)
print("STEP 2: Rebuilding 20d training set")
print("="*60)

from pipeline.phase3b_label_generator_20d import build_training_set_20d
df_train = build_training_set_20d(save=True)
print("Training set shape:", df_train.shape)

print("\n" + "="*60)
print("STEP 3: Retraining 20d LightGBM model")
print("="*60)

from pipeline.phase4b_ml_model_20d import (
    prepare_dataset, time_split, train, evaluate,
    save_model, get_feature_cols,
)

df = prepare_dataset()
train_df, val_df, test_df = time_split(df)
feat_cols = get_feature_cols(df)

print(f"\nNew feature count: {len(feat_cols)}")

interaction_in = [c for c in feat_cols if any(tag in c for tag in [
    "rel_strength", "x_mkt", "x_trend", "in_bull", "vs_mkt"
])]
print(f"New interaction features included ({len(interaction_in)}): {interaction_in}")

model, feat_cols_out, metrics = train(df)
print("\nMETRICS:", json.dumps(metrics, indent=2))

save_model(model, feat_cols_out, metrics)

# ── Step 4: Side-by-side comparison ───────────────────────────────────────────
print("\n" + "="*60)
print("STEP 4: BEFORE → AFTER comparison")
print("="*60)

def fmt(val):
    if val is None or val != val:
        return "   n/a  "
    return f"{val:.4f}"

b = before_metrics or {}
a = metrics

print(f"{'Metric':<25} {'BEFORE':>10} {'AFTER':>10}")
print("-" * 47)
for split in ["train", "val", "test"]:
    bv = b.get(split, {})
    av = a.get(split, {})
    print(f"{split.upper()+' AUC':<25} {fmt(bv.get('roc_auc')):>10} {fmt(av.get('roc_auc')):>10}")
    print(f"{split.upper()+' PR-AUC':<25} {fmt(bv.get('pr_auc')):>10} {fmt(av.get('pr_auc')):>10}")
    print(f"{split.upper()+' P@50':<25} {fmt(bv.get('precision_at_50')):>10} {fmt(av.get('precision_at_50')):>10}")
    print()

print(f"{'N features':<25} {str(before_n_features or '?'):>10} {str(len(feat_cols_out)):>10}")

fi_after = pd.read_csv(IMPORTANCE_20D_PATH)
vnx_nonzero_after = int((fi_after[fi_after["feature"].str.contains("vni_|rel_strength|x_mkt|x_trend|in_bull|vs_mkt")]["importance"] > 0).sum())
print(f"{'VNX/regime features imp>0':<25} {str(vnx_nonzero_before if before_n_features else '?'):>10} {str(vnx_nonzero_after):>10}")

print("\n--- Top 15 feature importances (AFTER) ---")
print(fi_after.head(15).to_string(index=False))

print("\n--- Interaction features importance ---")
interaction_fi = fi_after[fi_after["feature"].isin(interaction_in)].sort_values("importance", ascending=False)
if not interaction_fi.empty:
    print(interaction_fi.to_string(index=False))
else:
    print("  (none of the new interaction features found in importance CSV)")

print("\nLayer 1a complete.")
