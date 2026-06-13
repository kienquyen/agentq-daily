"""
Configuration Settings - Buytrend/Vnstock AgentQ
Supports environment-based configuration for scaling to 100k users.
"""

import os
from pathlib import Path
from typing import List

def _load_dotenv_if_present() -> None:
    for env_path in [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]:
        try:
            if not env_path.exists():
                continue
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v:
                    os.environ[k] = v
        except Exception:
            continue

_load_dotenv_if_present()

# ===== Required ENV =====
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
VNSTOCK_API_KEY = os.getenv("VNSTOCK_API_KEY", "").strip()

# ===== Global constants =====
TRADING_DAYS = int(os.getenv("TRADING_DAYS", "252"))
RF_ANNUAL = float(os.getenv("RF_ANNUAL", "0.07"))

BENCHMARK_SYMBOL_CANDIDATES: List[str] = [
    s.strip() for s in os.getenv(
        "BENCHMARK_SYMBOL_CANDIDATES",
        "VNINDEX,VNI,VN-INDEX,^VNINDEX"
    ).split(",")
    if s.strip()
]

# ===== Gemini / Google AI =====
GEMINI_API_KEY = (
    os.getenv("GOOGLE_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or ""
).strip()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
AI_TIMEOUT_SEC = int(os.getenv("AI_TIMEOUT_SEC", "30"))

# ===== Database Configuration (for 100k users) =====
TASK3_DB_URL = os.getenv(
    "TASK3_DB_URL",
    "postgresql://user:password@localhost:5432/agentq"
)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "40"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

# ===== Cache Configuration =====
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "1").strip().lower() not in ("0", "false", "False")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
REDIS_URL = os.getenv("REDIS_URL", "")

# ===== Feature flags =====
def _as_bool(x: str, default: bool = False) -> bool:
    if x is None or str(x).strip() == "":
        return default
    return str(x).strip().lower() in ("1", "true", "yes", "on")

TASK1_AI_ENABLED = _as_bool(os.getenv("TASK1_AI_ENABLED", "1"), default=True)
DEBUG_AI = _as_bool(os.getenv("DEBUG_AI", "0"), default=False)
TASK1_AI_TIMEOUT_SEC = int(os.getenv("TASK1_AI_TIMEOUT_SEC", "30"))

# ===== FX Rate =====
USDT_VND = float(os.getenv("USDT_VND", "26630"))

# ===== Validation =====
if not VNSTOCK_API_KEY:
    raise RuntimeError("Missing VNSTOCK_API_KEY env var")
if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN env var")

os.environ["VNSTOCK_API_KEY"] = VNSTOCK_API_KEY

def validate_required():
    errors = []
    if not DISCORD_TOKEN:
        errors.append("DISCORD_TOKEN is missing")
    if TASK1_AI_ENABLED and not GEMINI_API_KEY:
        errors.append("TASK1_AI_ENABLED=true but GEMINI_API_KEY is missing")
    if errors:
        msg = "Config validation failed:\n- " + "\n- ".join(errors)
        raise RuntimeError(msg)
