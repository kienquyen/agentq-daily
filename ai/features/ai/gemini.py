"""Gemini AI Service"""

import asyncio
from typing import Optional, Dict, Any

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    from config.settings import GEMINI_API_KEY, GEMINI_MODEL, AI_TIMEOUT_SEC, DEBUG_AI
except ImportError:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    AI_TIMEOUT_SEC = 30
    DEBUG_AI = False

from app.utils.helpers import safe_json_extract


def _dbg(*args):
    if DEBUG_AI:
        print(*args)

# google.genai will be imported lazily inside the class
genai = None
types = None


class GeminiService:
    def __init__(self):
        self.client = None
        self._model_name = (GEMINI_MODEL or "gemini-2.0-flash").strip()
        self._init_error: Optional[str] = None

        # Lazy import google.genai
        global genai, types
        if genai is None or types is None:
            try:
                from google import genai as _genai
                from google.genai import types as _types
                genai = _genai
                types = _types
            except Exception as e:
                self._init_error = f"google.genai not installed: {e}"
                return

        if not GEMINI_API_KEY:
            self._init_error = "Missing GEMINI_API_KEY"
            return

        try:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            self._init_error = f"Init failed: {type(e).__name__}: {e}"
            self.client = None

    def is_ready(self) -> bool:
        return self.client is not None

    def last_error(self) -> str:
        return self._init_error or ""

    def model_name(self) -> str:
        return self._model_name

    async def generate_json(self, prompt: str, timeout_sec: int = AI_TIMEOUT_SEC) -> Optional[Dict[str, Any]]:
        if not self.is_ready():
            _dbg("Gemini not ready:", self.last_error())
            return None

        def _call_sync() -> str:
            assert self.client is not None
            resp = self.client.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    top_p=0.1,
                    top_k=1,
                    max_output_tokens=500,
                    response_mime_type="application/json",
                ),
            )
            return resp.text or ""

        try:
            raw = await asyncio.wait_for(asyncio.to_thread(_call_sync), timeout=timeout_sec)
            _dbg("AI RAW:", raw)
            return safe_json_extract(raw)
        except Exception as e:
            _dbg("AI error:", type(e).__name__, str(e))
            return None
