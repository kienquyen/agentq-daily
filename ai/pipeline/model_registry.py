"""
Model Registry — quản lý versioning cho AI Shortlist model.

Cấu trúc thư mục:
    data/models/
      active_version.txt      ← "v3a" (production) | "v3b" (candidate)
      shadow_version.txt       ← version chạy song song (optional, "" = off)
      v3a/
        lgbm_model_20d.pkl
        eval_metrics_20d.json
        feature_importance_20d.csv
        config.json
      v3b/
        lgbm_model_20d.pkl
        eval_metrics_20d.json
        config.json

Usage:
    from pipeline.model_registry import registry

    cfg    = registry.config()                  # config của active version
    model  = registry.load_model()              # pkl của active version
    cfg_v  = registry.config("v3b")             # config của version cụ thể
    shadow = registry.shadow_version()          # "" nếu shadow tắt
"""

from __future__ import annotations

import json
import logging
import pickle
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

_MODELS_DIR   = Path("data/models")
_ACTIVE_FILE  = _MODELS_DIR / "active_version.txt"
_SHADOW_FILE  = _MODELS_DIR / "shadow_version.txt"
_REGISTRY_FILE = _MODELS_DIR / "registry.json"


# ── Registry metadata ──────────────────────────────────────────────────────────

def _load_registry() -> dict:
    """Load registry.json — metadata về tất cả versions."""
    if _REGISTRY_FILE.exists():
        try:
            return json.loads(_REGISTRY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"versions": {}}


def _save_registry(data: dict) -> None:
    _REGISTRY_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Active / Shadow version ────────────────────────────────────────────────────

def get_active_version() -> str:
    """Trả về version đang production. Mặc định 'v3a'."""
    if _ACTIVE_FILE.exists():
        v = _ACTIVE_FILE.read_text(encoding="utf-8").strip()
        if v:
            return v
    return "v3a"


def set_active_version(version: str) -> None:
    """Chuyển active version (hot-swap, không cần restart bot)."""
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)
    _ACTIVE_FILE.write_text(version.strip(), encoding="utf-8")
    log.info("[registry] Active version → %s", version)


def get_shadow_version() -> str:
    """Trả về shadow version. '' = shadow OFF."""
    if _SHADOW_FILE.exists():
        return _SHADOW_FILE.read_text(encoding="utf-8").strip()
    return ""


def set_shadow_version(version: str) -> None:
    """Bật/tắt shadow mode. set_shadow_version('') để tắt."""
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)
    _SHADOW_FILE.write_text(version.strip(), encoding="utf-8")
    if version:
        log.info("[registry] Shadow mode ON → %s", version)
    else:
        log.info("[registry] Shadow mode OFF")


# ── Config ─────────────────────────────────────────────────────────────────────

def load_config(version: str | None = None) -> dict:
    """
    Load config.json cho version (mặc định: active version).
    Trả về {} nếu không tìm thấy (caller tự fallback về hardcode).
    """
    v = version or get_active_version()
    cfg_path = _MODELS_DIR / v / "config.json"
    if not cfg_path.exists():
        log.warning("[registry] config.json not found for version '%s'", v)
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.error("[registry] Failed to load config for '%s': %s", v, exc)
        return {}


# ── Model artifacts ────────────────────────────────────────────────────────────

def get_model_path(version: str | None = None) -> Path:
    """Trả về path đến lgbm_model_20d.pkl của version."""
    v = version or get_active_version()
    versioned = _MODELS_DIR / v / "lgbm_model_20d.pkl"
    if versioned.exists():
        return versioned
    # Fallback: file gốc (tương thích ngược với code cũ)
    legacy = _MODELS_DIR / "lgbm_model_20d.pkl"
    log.warning("[registry] Versioned model not found for '%s', using legacy path", v)
    return legacy


def get_metrics_path(version: str | None = None) -> Path:
    v = version or get_active_version()
    versioned = _MODELS_DIR / v / "eval_metrics_20d.json"
    if versioned.exists():
        return versioned
    return _MODELS_DIR / "eval_metrics_20d.json"


def load_metrics(version: str | None = None) -> dict:
    path = get_metrics_path(version)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


# ── Version management ─────────────────────────────────────────────────────────

def list_versions() -> list[str]:
    """Trả về danh sách tất cả versions có trong data/models/."""
    if not _MODELS_DIR.exists():
        return []
    return sorted([
        d.name for d in _MODELS_DIR.iterdir()
        if d.is_dir() and (d / "lgbm_model_20d.pkl").exists()
    ])


def version_exists(version: str) -> bool:
    return (_MODELS_DIR / version / "lgbm_model_20d.pkl").exists()


def create_version(
    version: str,
    source_pkl: Path,
    source_metrics: Path | None = None,
    config_overrides: dict | None = None,
) -> None:
    """
    Tạo version mới từ model pkl + optional metrics + config overrides.
    Dùng khi promote candidate hoặc tạo v3b từ v3a.
    """
    version_dir = _MODELS_DIR / version
    version_dir.mkdir(parents=True, exist_ok=True)

    # Copy model
    shutil.copy2(source_pkl, version_dir / "lgbm_model_20d.pkl")

    # Copy metrics nếu có
    if source_metrics and source_metrics.exists():
        shutil.copy2(source_metrics, version_dir / "eval_metrics_20d.json")

    # Config: inherit từ active version, apply overrides
    base_cfg = load_config(get_active_version())
    if config_overrides:
        base_cfg.update(config_overrides)
    base_cfg["_version"]  = version
    base_cfg["_created"]  = datetime.now().strftime("%Y-%m-%d")
    (version_dir / "config.json").write_text(
        json.dumps(base_cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log.info("[registry] Created version '%s' at %s", version, version_dir)


def archive_version(version: str) -> str:
    """
    Lưu snapshot của version vào data/models/archive/{version}_{timestamp}/.
    Trả về tên archive.
    """
    src = _MODELS_DIR / version
    if not src.exists():
        raise FileNotFoundError(f"Version '{version}' not found")
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    archive_name = f"{version}_{ts}"
    dst = _MODELS_DIR / "archive" / archive_name
    shutil.copytree(src, dst)
    log.info("[registry] Archived '%s' → %s", version, dst)
    return archive_name


def promote_to_production(
    candidate_version: str,
    production_version: str = "v3a",
    archive_first: bool = True,
) -> str:
    """
    Promote candidate → production:
    1. Archive production hiện tại (nếu archive_first=True)
    2. Copy candidate artifacts → production dir
    3. Giữ candidate dir nguyên (không xóa)
    Trả về tên archive (hoặc '' nếu skip archive).
    """
    if not version_exists(candidate_version):
        raise FileNotFoundError(f"Candidate '{candidate_version}' has no model file")

    archive_name = ""
    if archive_first and version_exists(production_version):
        archive_name = archive_version(production_version)

    prod_dir = _MODELS_DIR / production_version
    cand_dir = _MODELS_DIR / candidate_version
    prod_dir.mkdir(parents=True, exist_ok=True)

    for f in cand_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, prod_dir / f.name)
    # Update version tag in config
    cfg_path = prod_dir / "config.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        cfg["_version"]   = production_version
        cfg["_promoted_from"] = candidate_version
        cfg["_promoted_at"]   = datetime.now().strftime("%Y-%m-%d %H:%M")
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))

    # Also update legacy flat files for backward compat
    legacy_pkl = _MODELS_DIR / "lgbm_model_20d.pkl"
    legacy_bak = _MODELS_DIR / "lgbm_model_20d_backup.pkl"
    if legacy_pkl.exists():
        shutil.copy2(legacy_pkl, legacy_bak)
    shutil.copy2(prod_dir / "lgbm_model_20d.pkl", legacy_pkl)

    log.info("[registry] Promoted '%s' → '%s' (archive: %s)",
             candidate_version, production_version, archive_name or "skipped")
    return archive_name


# ── Status summary ─────────────────────────────────────────────────────────────

def status_summary() -> dict:
    """Trả về dict tóm tắt trạng thái registry — dùng cho Discord."""
    active  = get_active_version()
    shadow  = get_shadow_version()
    versions = list_versions()
    result = {
        "active":   active,
        "shadow":   shadow or None,
        "versions": {},
    }
    for v in versions:
        cfg = load_config(v)
        m   = load_metrics(v)
        result["versions"][v] = {
            "description": cfg.get("_description", ""),
            "created":     cfg.get("_created", ""),
            "auc":         m.get("test_auc") or m.get("auc"),
            "is_active":   v == active,
            "is_shadow":   v == shadow,
        }
    return result


# ── Convenience singleton ──────────────────────────────────────────────────────

class _Registry:
    """Thin wrapper — dùng `registry.config()`, `registry.load_model()`, v.v."""

    def active(self) -> str:
        return get_active_version()

    def shadow(self) -> str:
        return get_shadow_version()

    def config(self, version: str | None = None) -> dict:
        return load_config(version)

    def model_path(self, version: str | None = None) -> Path:
        return get_model_path(version)

    def metrics(self, version: str | None = None) -> dict:
        return load_metrics(version)

    def set_active(self, version: str) -> None:
        set_active_version(version)

    def set_shadow(self, version: str) -> None:
        set_shadow_version(version)

    def status(self) -> dict:
        return status_summary()


registry = _Registry()
