#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import hashlib
import uuid
import socket
import platform
from pathlib import Path
from datetime import datetime

import requests
import sys
import site

# ─── Proxy support ───────────────────────────────────────────────────────────
# Set proxy for all HTTP requests (used by vnstock_data web-scraping calls).
# On Railway, set these as Environment Variables in the Railway dashboard:
#   HTTP_PROXY  = http://proxy:8080
#   HTTPS_PROXY = http://proxy:8080
# Or use a paid rotating proxy with Vietnamese IPs (e.g., AstroProxy, Bright Data).
_http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
_https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
if _http_proxy or _https_proxy:
    # Normalise into both case variants so all HTTP clients pick them up.
    if _http_proxy:
        os.environ["HTTP_PROXY"] = _http_proxy
        os.environ["http_proxy"] = _http_proxy
    _eff_https = _https_proxy or _http_proxy
    if _eff_https:
        os.environ["HTTPS_PROXY"] = _eff_https
        os.environ["https_proxy"] = _eff_https

    # Also configure urllib (used by some vnstock internals).
    import urllib.request
    proxy_handler = urllib.request.ProxyHandler(
        {k: v for k, v in {"http": _http_proxy, "https": _eff_https}.items() if v}
    )
    urllib.request.install_opener(urllib.request.build_opener(proxy_handler))

    print(f"🔀 Proxy: http={_http_proxy}, https={_eff_https}")
else:
    print("🔀 Proxy: none (direct connection)")


def _fix_vnstock_path() -> None:
    # 1. Evict local version from module cache if already loaded
    import sys
    import os

    for k in list(sys.modules):
        if k == "vnstock_data" or k.startswith("vnstock_data."):
            src = getattr(sys.modules[k], "__file__", "") or ""
            if "site-packages" not in src and src != "":
                del sys.modules[k]

    # 2. Move project root to the end of sys.path to avoid shadowing site-packages
    root = os.path.abspath(os.path.join(os.getcwd()))
    for path in list(sys.path):
        if path == "" or os.path.abspath(path) == root:
            sys.path.remove(path)
            sys.path.append(path)


_fix_vnstock_path()

def _patch_vnai_auth() -> None:
    """
    Monkey-patch vnai.beam.auth.AuthStateManager._is_cache_valid to handle
    offset-aware datetimes. The installed vnai package does:
        return datetime.now() < expiry
    which crashes when auth_time in auth_state.json is an ISO string with +00:00
    (offset-aware). We strip tzinfo before comparison so it always works.
    """
    try:
        from vnai.beam import auth as _vnai_auth
        from datetime import datetime as _dt

        def _is_cache_valid_patched(self):
            if not self._state.get("auth_time"):
                return False
            auth_time = _dt.fromisoformat(self._state["auth_time"])
            if auth_time.tzinfo is not None:
                auth_time = auth_time.replace(tzinfo=None)
            from datetime import timedelta
            ttl = self._state.get("cache_ttl_minutes", 60)
            expiry = auth_time + timedelta(minutes=ttl)
            return _dt.now() < expiry

        _vnai_auth.AuthStateManager._is_cache_valid = _is_cache_valid_patched
        print("🔧 Patched vnai.beam.auth._is_cache_valid (timezone fix)")
    except Exception as e:
        print(f"⚠️ Could not patch vnai.beam.auth: {e}")


_patch_vnai_auth()


def _stable_device_id() -> str:
    # ưu tiên seed tĩnh (bạn có thể set VNSTOCK_DEVICE_SEED trong Railway Variables)
    seed = (
        os.getenv("VNSTOCK_DEVICE_SEED")
        or os.getenv("RAILWAY_SERVICE_ID")
        or os.getenv("RAILWAY_PROJECT_ID")
        or os.getenv("RAILWAY_STATIC_URL")
        or "local-project"
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


def _ensure_api_key_file(api_key: str) -> str:
    cfg_dir = Path.home() / ".vnstock"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = cfg_dir / "api_key.json"
    cfg_file.write_text(
        json.dumps({"api_key": api_key}, ensure_ascii=False), encoding="utf-8"
    )
    return str(cfg_file)


def _fetch_profile(api_key: str) -> tuple[str, str]:
    """
    Trả về (username, email) từ API.
    Lưu ý: API của VNStock có thể trả dạng {data:{...}} hoặc trả thẳng {...}
    """
    url = "https://vnstocks.com/api/vnstock/user/profile"
    r = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
    r.raise_for_status()
    j = r.json()
    data = j.get("data") if isinstance(j, dict) else None
    if isinstance(data, dict):
        username = data.get("username") or data.get("user") or "Unknown"
        email = data.get("email") or "unknown"
        return username, email
    # fallback nếu API trả thẳng
    if isinstance(j, dict):
        return (
            j.get("username") or j.get("user") or "Unknown",
            j.get("email") or "unknown",
        )
    return ("Unknown", "unknown")


def _ensure_user_json(api_key: str, device_id: str) -> str:
    """
    Tạo ~/.vnstock/user.json theo format installer của VNStock
    """
    cfg_dir = Path.home() / ".vnstock"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    user_file = cfg_dir / "user.json"

    username, email = _fetch_profile(api_key)

    # format tương thích với script generate_user_info.min.py
    user_info = {
        "user": username,
        "email": email,
        "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, socket.gethostname())),
        "os": platform.system(),
        "os_version": platform.version(),
        "ip": "unknown",
        "cwd": os.getcwd(),
        "python": {
            "version": f"{platform.python_version()}",
            "executable": os.path.realpath(os.sys.executable),
            "is_virtual_env": (
                hasattr(os.sys, "base_prefix") and os.sys.base_prefix != os.sys.prefix
            ),
            "virtual_env_path": os.getenv("VIRTUAL_ENV"),
        },
        "time": datetime.now().isoformat(),
        "device_id": device_id,
        # 2 field này trong script gốc là hardware uuid + mac
        # trên cloud có thể không ổn định, nhưng ta vẫn để placeholder để đúng schema
        "hardware_uuid": "cloud",
        "mac_address": "cloud",
    }

    user_file.write_text(
        json.dumps(user_info, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return str(user_file)


def _ensure_auth_state(api_key: str, device_id: str) -> None:
    """Create auth_state.json for vnstock_data paid API authentication.

    IMPORTANT: auth_time must be a naive datetime string (no +00:00 suffix).
    vnai.beam.auth uses `datetime.now() < expiry` — if auth_time is offset-aware,
    the comparison raises TypeError: can't compare offset-naive and offset-aware datetimes.
    TTL is set to 30 days so Railway containers don't expire mid-session.
    """
    cfg_dir = Path.home() / ".vnstock"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    auth_file = cfg_dir / "auth_state.json"

    # Always overwrite: containers are ephemeral and a stale file with an
    # expired TTL would cause the same TypeError on the next restart.
    auth_state = {
        "session_id": str(uuid.uuid4()),
        "authenticated": True,
        "user": "cloud",
        "tier": "golden",
        # Naive datetime (no timezone suffix) — vnai compares with datetime.now() which is also naive.
        "auth_time": datetime.now().isoformat(),
        "packages_notified": ["vnstock"],
        "cache_ttl_minutes": 43200,  # 30 days — prevents mid-session expiry on Railway
    }
    auth_file.write_text(json.dumps(auth_state, indent=2), encoding="utf-8")
    print("   auth_state  =", auth_file)


def bootstrap() -> None:
    api_key = (os.getenv("VNSTOCK_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("❌ Missing VNSTOCK_API_KEY (set in Railway Variables)")

    os.environ["VNSTOCK_API_KEY"] = api_key

    os.environ.setdefault("VNSTOCK_DEVICE_ID", _stable_device_id())
    os.environ.setdefault(
        "VNSTOCK_PACKAGE_NAME",
        os.getenv("VNSTOCK_PACKAGE_NAME") or "qcapital.discord.bot",
    )

    api_key_path = _ensure_api_key_file(api_key)
    user_path = _ensure_user_json(api_key, os.environ["VNSTOCK_DEVICE_ID"])
    _ensure_auth_state(api_key, os.environ["VNSTOCK_DEVICE_ID"])

    print("✅ VNSTOCK BOOTSTRAP OK")
    print("   api_key.json =", api_key_path)
    print("   user.json    =", user_path)
    print("   device_id    =", os.environ["VNSTOCK_DEVICE_ID"])
    print("   package      =", os.environ["VNSTOCK_PACKAGE_NAME"])


# chạy ngay khi import
bootstrap()
