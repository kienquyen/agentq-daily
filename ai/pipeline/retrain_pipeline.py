#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/retrain_pipeline.py
Monthly Retrain Pipeline — LightGBM 20D

Flow (2 bước tách biệt):
  BƯỚC 1 — train_candidate():
    - Load old metrics (AUC baseline)
    - Backup production model
    - Train model mới → lưu vào candidate files (KHÔNG đụng production)
    - Trả về báo cáo + AUC comparison để user xem xét

  BƯỚC 2 — deploy_candidate() hoặc discard_candidate():
    - deploy:  copy candidate → production (chỉ chạy khi user xác nhận)
    - discard: xoá candidate files, giữ nguyên production

Files:
  Production : data/models/lgbm_model_20d.pkl + eval_metrics_20d.json
  Candidate  : data/models/lgbm_model_20d_candidate.pkl + eval_metrics_20d_candidate.json
  Backup     : data/models/lgbm_model_20d_backup.pkl + eval_metrics_20d_backup.json

CLI:
    python -m pipeline.retrain_pipeline              # train candidate
    python -m pipeline.retrain_pipeline --deploy     # deploy existing candidate
    python -m pipeline.retrain_pipeline --discard    # discard candidate
    python -m pipeline.retrain_pipeline --status     # show candidate status
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

_ROOT       = Path(__file__).resolve().parent.parent
_MODELS_DIR = _ROOT / "data" / "models"
_MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Production
_MODEL_PATH   = _MODELS_DIR / "lgbm_model_20d.pkl"
_METRICS_PATH = _MODELS_DIR / "eval_metrics_20d.json"

# Candidate (new model awaiting approval)
_CAND_MODEL   = _MODELS_DIR / "lgbm_model_20d_candidate.pkl"
_CAND_METRICS = _MODELS_DIR / "eval_metrics_20d_candidate.json"

# Backup (snapshot before last deploy)
_BACKUP_MODEL   = _MODELS_DIR / "lgbm_model_20d_backup.pkl"
_BACKUP_METRICS = _MODELS_DIR / "eval_metrics_20d_backup.json"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_metrics(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def _backup_production() -> None:
    if _MODEL_PATH.exists():
        shutil.copy2(_MODEL_PATH,   _BACKUP_MODEL)
    if _METRICS_PATH.exists():
        shutil.copy2(_METRICS_PATH, _BACKUP_METRICS)
    log.info("[retrain] Production backed up.")


def candidate_exists() -> bool:
    return _CAND_MODEL.exists() and _CAND_METRICS.exists()


def get_candidate_metrics() -> dict:
    return _load_metrics(_CAND_METRICS)


# ── Step 1: Train candidate ────────────────────────────────────────────────────

def train_candidate(progress_cb=None) -> dict:
    """
    Train model mới, lưu vào candidate files.
    KHÔNG đụng production model.

    Returns report dict:
      status         : "ready" | "error"
      old_auc        : float  (production test AUC)
      new_auc        : float  (candidate test AUC)
      auc_delta      : float
      auc_ok         : bool   (new >= old - tolerance)
      metrics_old    : dict
      metrics_new    : dict
      duration_sec   : float
      timestamp      : str
      recommendation : str    ("deploy" | "review" | "discard")
    """
    def _notify(msg: str) -> None:
        log.info("[retrain] %s", msg)
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    t_start = datetime.now()
    report  = {
        "status":         "error",
        "old_auc":        0.0,
        "new_auc":        0.0,
        "auc_delta":      0.0,
        "auc_ok":         False,
        "metrics_old":    {},
        "metrics_new":    {},
        "duration_sec":   0.0,
        "timestamp":      t_start.strftime("%Y-%m-%d %H:%M"),
        "recommendation": "discard",
    }

    try:
        # 1. Old metrics
        _notify("📂 Đọc metrics model hiện tại...")
        old_metrics  = _load_metrics(_METRICS_PATH)
        old_test_auc = old_metrics.get("test", {}).get("roc_auc", 0.0)
        old_val_auc  = old_metrics.get("val",  {}).get("roc_auc", 0.0)
        report["metrics_old"] = old_metrics
        report["old_auc"]     = old_test_auc
        _notify(f"   Hiện tại → test AUC={old_test_auc:.4f}  val AUC={old_val_auc:.4f}")

        # 2. Backup production
        _notify("💾 Backup production model...")
        _backup_production()

        # 3. Prepare dataset
        _notify("📊 Chuẩn bị dataset (features + labels)...")
        from pipeline.phase4b_ml_model_20d import prepare_dataset, train, save_model

        df = prepare_dataset()
        n_rows = len(df)
        n_pos  = int(df["label"].sum()) if "label" in df.columns else 0
        _notify(
            f"   Dataset: {n_rows:,} rows  |  {n_pos:,} positive  |  "
            f"pos_rate={n_pos / max(n_rows, 1) * 100:.1f}%"
        )

        if n_rows < 100:
            report["status"] = "error"
            report["reason"] = f"Dataset quá nhỏ ({n_rows} rows)."
            return report

        # 4. Train (saves nothing yet)
        _notify("🧠 Đang train LightGBM... (~2-3 phút)")
        model, feat_cols, new_metrics = train(df)

        new_test_auc = new_metrics.get("test", {}).get("roc_auc", 0.0)
        new_val_auc  = new_metrics.get("val",  {}).get("roc_auc", 0.0)
        auc_delta    = new_test_auc - old_test_auc
        auc_ok       = new_test_auc >= old_test_auc - 0.005

        report["new_auc"]     = new_test_auc
        report["auc_delta"]   = round(auc_delta, 4)
        report["metrics_new"] = new_metrics
        report["auc_ok"]      = auc_ok
        _notify(
            f"   Candidate → test AUC={new_test_auc:.4f}  val AUC={new_val_auc:.4f}  "
            f"Δ={auc_delta:+.4f}  {'✅ OK' if auc_ok else '⚠️ Thấp hơn ngưỡng'}"
        )

        # 5. Save to candidate files AND versioned v3b/ directory
        import pickle
        payload = {
            "model": model, "feat_cols": feat_cols,
            "horizon": "20d", "ret_threshold": 0.05,
            "prob_cutoff": 0.50,
        }
        # Legacy flat files (backward compat)
        with open(_CAND_MODEL, "wb") as f:
            pickle.dump(payload, f)
        with open(_CAND_METRICS, "w") as f:
            json.dump(new_metrics, f, indent=2)

        # Versioned: save to data/models/v3b/
        try:
            from pipeline.model_registry import create_version
            create_version(
                version="v3b",
                source_pkl=_CAND_MODEL,
                source_metrics=_CAND_METRICS,
                config_overrides={
                    "_description": f"v3b candidate — retrained {t_start.strftime('%Y-%m-%d')}",
                    "_model_file":  "lgbm_model_20d.pkl",
                },
            )
            _notify("   Candidate lưu → data/models/v3b/ (versioned)")
        except Exception as ve:
            log.warning("[retrain] Failed to create versioned v3b: %s", ve)

        _notify(f"   Candidate lưu → {_CAND_MODEL.name}")

        report["status"] = "ready"
        report["recommendation"] = "deploy" if auc_ok else "review"

    except Exception as exc:
        log.error("[retrain] train_candidate crashed: %s", exc, exc_info=True)
        report["status"] = "error"
        report["reason"] = str(exc)

    finally:
        report["duration_sec"] = round((datetime.now() - t_start).total_seconds(), 1)

    return report


# ── Step 2a: Deploy candidate ──────────────────────────────────────────────────

def deploy_candidate() -> dict:
    """
    Copy candidate → production. Ghi đè production model.
    Chỉ gọi sau khi user đã xác nhận.
    Returns: {"success": bool, "message": str}
    """
    if not candidate_exists():
        return {"success": False, "message": "Không có candidate model để deploy."}
    try:
        # Deploy qua registry (archive v3a, promote v3b → v3a)
        try:
            from pipeline.model_registry import promote_to_production
            archive_name = promote_to_production("v3b", "v3a", archive_first=True)
            log.info("[retrain] Promoted v3b → v3a via registry (archive=%s)", archive_name)
        except Exception as re:
            log.warning("[retrain] Registry promote failed, fallback to flat copy: %s", re)

        # Legacy flat files (backward compat)
        shutil.copy2(_CAND_MODEL,   _MODEL_PATH)
        shutil.copy2(_CAND_METRICS, _METRICS_PATH)
        # Clean up candidate flat files
        _CAND_MODEL.unlink(missing_ok=True)
        _CAND_METRICS.unlink(missing_ok=True)
        log.info("[retrain] Candidate deployed to production.")
        return {"success": True, "message": "✅ Model mới đã được deploy vào production."}
    except Exception as exc:
        log.error("[retrain] deploy_candidate failed: %s", exc)
        return {"success": False, "message": f"❌ Deploy thất bại: {exc}"}


# ── Step 2b: Discard candidate ─────────────────────────────────────────────────

def discard_candidate() -> dict:
    """
    Xoá candidate files. Production không thay đổi.
    Returns: {"success": bool, "message": str}
    """
    if not candidate_exists():
        return {"success": False, "message": "Không có candidate để discard."}
    _CAND_MODEL.unlink(missing_ok=True)
    _CAND_METRICS.unlink(missing_ok=True)
    log.info("[retrain] Candidate discarded.")
    return {"success": True, "message": "🗑️ Candidate đã xoá. Production model giữ nguyên."}


# ── Discord formatters ─────────────────────────────────────────────────────────

def format_train_report(report: dict) -> str:
    """Format train_candidate() result for Discord — shows AUC + awaits decision."""
    status  = report.get("status", "error")
    old_auc = report.get("old_auc", 0.0)
    new_auc = report.get("new_auc", 0.0)
    delta   = report.get("auc_delta", 0.0)
    auc_ok  = report.get("auc_ok", False)
    dur     = report.get("duration_sec", 0)
    ts      = report.get("timestamp", "")
    old_m   = report.get("metrics_old", {})
    new_m   = report.get("metrics_new", {})

    if status == "error":
        return (
            f"❌ **Retrain thất bại**\n"
            f"`{report.get('reason', 'Unknown error')}`"
        )

    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🧠  **RETRAIN HOÀN TẤT — CHỜ XÁC NHẬN DEPLOY**")
    lines.append(f"🕐 {ts}  |  ⏱ {dur:.0f}s")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")

    # AUC table
    if new_m:
        lines.append("**So sánh AUC (production vs candidate):**")
        lines.append("```")
        lines.append(f"{'Split':<8} {'Hiện tại':>9} {'Candidate':>9} {'Δ':>7}")
        lines.append(f"{'─'*8} {'─'*9} {'─'*9} {'─'*7}")
        for split in ("train", "val", "test"):
            o = old_m.get(split, {}).get("roc_auc", float("nan"))
            n = new_m.get(split, {}).get("roc_auc", float("nan"))
            d = n - o if (o == o and n == n) else float("nan")
            marker = "  ◄" if split == "test" else ""
            lines.append(
                f"{split:<8} {o:>9.4f} {n:>9.4f} {d:>+7.4f}{marker}"
            )
        lines.append("```")

        nt = new_m.get("test", {})
        lines.append(
            f"📊 Test: **{nt.get('n_rows', 0):,}** rows  |  "
            f"**{nt.get('n_pos', 0):,}** positive  |  "
            f"P@50: **{nt.get('precision_at_50', 0):.2f}**"
        )

    lines.append("")
    if auc_ok:
        lines.append(
            f"✅ **AUC candidate ({new_auc:.4f}) ≥ ngưỡng chấp nhận** "
            f"→ Khuyến nghị **Deploy**"
        )
    else:
        lines.append(
            f"⚠️ **AUC candidate ({new_auc:.4f}) thấp hơn production ({old_auc:.4f})** "
            f"→ Khuyến nghị **Giữ model cũ**"
        )
    lines.append("")
    lines.append("👇 **Bạn quyết định:**")
    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    p = argparse.ArgumentParser(description="Retrain Pipeline")
    p.add_argument("--deploy",   action="store_true", help="Deploy existing candidate")
    p.add_argument("--discard",  action="store_true", help="Discard candidate")
    p.add_argument("--status",   action="store_true", help="Show candidate status")
    args = p.parse_args()

    if args.deploy:
        r = deploy_candidate()
        print(r["message"])
    elif args.discard:
        r = discard_candidate()
        print(r["message"])
    elif args.status:
        if candidate_exists():
            m = get_candidate_metrics()
            auc = m.get("test", {}).get("roc_auc", "?")
            print(f"Candidate exists — test AUC={auc}")
        else:
            print("No candidate model.")
    else:
        def _cb(msg): print(f"  {msg}")
        report = train_candidate(progress_cb=_cb)
        print("\n" + format_train_report(report))
        if report["status"] == "ready":
            ans = input("\nDeploy candidate? [y/N]: ").strip().lower()
            if ans == "y":
                r = deploy_candidate()
                print(r["message"])
            else:
                r = discard_candidate()
                print(r["message"])
