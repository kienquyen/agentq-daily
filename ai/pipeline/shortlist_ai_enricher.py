"""
pipeline/shortlist_ai_enricher.py
AI Enrichment for Shortlist — News Filter (#1) + Fundamental Scan (#3)

Designed to be called synchronously from get_shortlist_20d().
Two Gemini calls per shortlist run:
  Call 1 — News Filter  : flag symbols affected by bad news (CAUTION / SKIP)
  Call 2 — Fundamental  : P/E, ROE verdict per symbol

Both calls are non-blocking at the shortlist level:
  if Gemini / data fetch fails → silently returns empty enrichment, shortlist sends as-is.

Model: gemini-2.0-flash (fast, cheap, JSON mode — already configured in .env)
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

log = logging.getLogger(__name__)

# ── Gemini sync helper ─────────────────────────────────────────────────────────

def _gemini_json(prompt: str, max_tokens: int = 800) -> Optional[dict | list]:
    """
    Synchronous Gemini call → returns parsed JSON or None on any error.
    Reuses the same API key / model from config / env.
    """
    try:
        from config.settings import GEMINI_API_KEY, GEMINI_MODEL
    except ImportError:
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
        GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

    if not GEMINI_API_KEY:
        log.debug("[enricher] No GEMINI_API_KEY — skipping AI enrichment.")
        return None

    try:
        from google import genai
        from google.genai import types
        from app.utils.helpers import safe_json_extract

        client = genai.Client(api_key=GEMINI_API_KEY)
        resp   = client.models.generate_content(
            model   = GEMINI_MODEL or "gemini-2.0-flash",
            contents= prompt,
            config  = types.GenerateContentConfig(
                temperature          = 0.0,
                top_p                = 0.1,
                top_k                = 1,
                max_output_tokens    = max_tokens,
                response_mime_type   = "application/json",
            ),
        )
        return safe_json_extract(resp.text or "")
    except Exception as e:
        log.warning("[enricher] Gemini call failed: %s", e)
        return None


# ── Ratio fetch helper ─────────────────────────────────────────────────────────

def _safe_float(val) -> Optional[float]:
    try:
        if val is None:
            return None
        f = float(val)
        return None if (f != f or abs(f) > 1e9) else round(f, 2)
    except Exception:
        return None


def _fetch_ratio_one(sym: str) -> tuple[str, Optional[dict]]:
    try:
        from app.vnstock_core.core import fetch_ratio
        df = fetch_ratio(sym, "Q")
        if df.empty:
            return sym, None
        row = df.iloc[-1]
        return sym, {
            "pe":  _safe_float(row.get("pe")),
            "pb":  _safe_float(row.get("pb")),
            "roe": _safe_float(row.get("roe")),
            "roa": _safe_float(row.get("roa")),
        }
    except Exception as e:
        log.debug("[enricher] fetch_ratio(%s): %s", sym, e)
        return sym, None


# ── Step 1: News Filter ────────────────────────────────────────────────────────

def _news_filter(symbols: list[str], date_str: str) -> dict[str, dict]:
    """
    Fetch recent headlines for symbols, ask Gemini to classify each:
      OK      — no significant negative news
      CAUTION — minor negative signal, worth watching
      SKIP    — serious negative news (investigation, major profit drop, lawsuit)

    Returns: {symbol: {"news_tag": "OK"|"CAUTION"|"SKIP", "news_note": "..."}}
    """
    try:
        from features.daily_recap.data_fetcher import get_news
        news_items = get_news(symbols=symbols, limit=20)
    except Exception as e:
        log.warning("[enricher] News fetch failed: %s", e)
        return {}

    if not news_items:
        return {}

    news_text = "\n".join(
        f"- {n['headline']}: {(n.get('impact_base') or '')[:120]}"
        for n in news_items
    )

    prompt = (
        "Bạn là chuyên gia phân tích chứng khoán Việt Nam.\n"
        f"Các mã cần đánh giá: {', '.join(symbols)}\n\n"
        f"Tin tức 3 ngày gần nhất:\n{news_text}\n\n"
        "Với mỗi mã, phân loại tác động tin tức:\n"
        "  OK      — không có tin xấu đáng kể\n"
        "  CAUTION — có dấu hiệu tiêu cực nhỏ, nên theo dõi\n"
        "  SKIP    — tin xấu nghiêm trọng (điều tra, kiện tụng, lợi nhuận sụt mạnh)\n\n"
        "Chỉ đánh dấu CAUTION/SKIP khi có tin tức RÕ RÀNG liên quan đến mã đó. "
        "Không suy đoán nếu không có tin cụ thể.\n\n"
        "Trả JSON object dạng:\n"
        '{"VCB": {"news_tag": "OK", "news_note": ""}, '
        '"HPG": {"news_tag": "CAUTION", "news_note": "Q1 lợi nhuận giảm 15%"}}'
    )

    result = _gemini_json(prompt, max_tokens=600)
    if not result or not isinstance(result, dict):
        log.debug("[enricher] News filter: no valid JSON from Gemini.")
        return {}

    # Normalise — ensure all queried symbols present
    out = {}
    for sym in symbols:
        item = result.get(sym, {})
        out[sym] = {
            "news_tag":  item.get("news_tag",  "OK"),
            "news_note": item.get("news_note", ""),
        }
    return out


# ── Step 2: Fundamental Scan ───────────────────────────────────────────────────

def _fundamental_scan(symbols: list[str]) -> dict[str, dict]:
    """
    Fetch P/E, ROE etc. for all symbols in parallel, then ask Gemini for a verdict.

    Returns: {symbol: {"fund_pe": float|None, "fund_roe": float|None,
                        "fund_verdict": str, "fund_tag": "OK"|"WEAK"|"RISK"}}
    """
    # 1. Parallel ratio fetch (max 5 workers — don't hammer vnstock API)
    ratios: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_fetch_ratio_one, sym): sym for sym in symbols}
        for fut in as_completed(futures, timeout=30):
            sym, data = fut.result()
            if data:
                ratios[sym] = data

    if not ratios:
        log.debug("[enricher] No ratio data fetched — skipping fundamental scan.")
        return {}

    # 2. Build summary for Gemini
    ratio_lines = []
    for sym in symbols:
        r = ratios.get(sym)
        if not r:
            ratio_lines.append(f"  {sym}: P/E=N/A P/B=N/A ROE=N/A ROA=N/A")
            continue
        pe  = f"{r['pe']:.1f}x"  if r.get("pe")  else "N/A"
        pb  = f"{r['pb']:.1f}x"  if r.get("pb")  else "N/A"
        roe = f"{r['roe']:.1f}%" if r.get("roe") else "N/A"
        roa = f"{r['roa']:.1f}%" if r.get("roa") else "N/A"
        ratio_lines.append(f"  {sym}: P/E={pe} P/B={pb} ROE={roe} ROA={roa}")

    # Build a compact one-line example using actual symbols to anchor the format
    example_sym = symbols[0]
    example_pe  = ratios.get(example_sym, {}).get("pe") or 12.0
    example_roe = ratios.get(example_sym, {}).get("roe") or 15.0

    prompt = (
        "Bạn là chuyên gia phân tích cơ bản chứng khoán Việt Nam.\n"
        "Đánh giá nhanh các chỉ số cơ bản sau (quý gần nhất):\n"
        + "\n".join(ratio_lines) + "\n\n"
        "QUAN TRỌNG: Chỉ trả về JSON object thuần túy theo đúng format bên dưới.\n"
        "Không thêm key nào khác. Không dùng array. Không giải thích thêm.\n\n"
        "Quy tắc fund_tag:\n"
        "  OK   — P/E ≤ 30 VÀ ROE ≥ 8%\n"
        "  WEAK — ROE < 8% (hiệu quả vốn thấp)\n"
        "  RISK — P/E > 40 HOẶC ROE âm (định giá cực cao hoặc thua lỗ)\n\n"
        "fund_verdict: nhận xét 3-6 từ tiếng Việt\n\n"
        f'Format bắt buộc (key là mã cổ phiếu):\n'
        f'{{"{example_sym}": {{"fund_verdict": "Định giá hợp lý", '
        f'"fund_tag": "OK", "fund_pe": {example_pe:.1f}, "fund_roe": {example_roe:.1f}}}, '
        f'"...": {{...}}}}'
    )

    result = _gemini_json(prompt, max_tokens=1200)

    # ── Normalise Gemini response → per-symbol dict ───────────────────────────
    parsed: dict[str, dict] = {}

    if result and isinstance(result, dict):
        # Happy path: Gemini returned {symbol: {...}} directly
        if any(sym in result for sym in symbols):
            parsed = result
        # Fallback path: Gemini returned {"analysis": [...]} or similar array wrapper
        elif isinstance(list(result.values())[0] if result else None, list):
            for item in list(result.values())[0]:
                sym = item.get("ticker") or item.get("symbol") or item.get("ma") or ""
                sym = sym.upper().strip()
                if sym in symbols:
                    parsed[sym] = item

    # ── Rule-based fallback: apply hard thresholds for any symbol not parsed ──
    def _rule_tag(pe, roe) -> tuple[str, str]:
        """Return (fund_tag, fund_verdict) based on hard rules."""
        if roe is not None and roe < 0:
            return "RISK", "ROE âm — thua lỗ"
        if pe is not None and pe > 40:
            return "RISK", f"P/E {pe:.0f}x — định giá cực cao"
        if roe is not None and roe < 8:
            return "WEAK", f"ROE {roe:.1f}% — hiệu quả vốn thấp"
        if pe is not None and pe > 25:
            return "OK", f"P/E cao {pe:.0f}x, theo dõi"
        return "OK", "Cơ bản ổn"

    out = {}
    for sym in symbols:
        r_raw  = ratios.get(sym, {})
        pe_raw = r_raw.get("pe")
        roe_raw= r_raw.get("roe")
        item   = parsed.get(sym, {})

        fund_pe      = item.get("fund_pe")  or pe_raw
        fund_roe     = item.get("fund_roe") or roe_raw
        fund_verdict = item.get("fund_verdict", "")
        fund_tag     = item.get("fund_tag", "")

        # Override with rule-based if Gemini missed or returned wrong tag
        rule_tag, rule_verdict = _rule_tag(pe_raw, roe_raw)
        if not fund_tag or fund_tag not in ("OK", "WEAK", "RISK"):
            fund_tag     = rule_tag
            fund_verdict = rule_verdict
        elif fund_tag == "OK" and rule_tag in ("WEAK", "RISK"):
            # Rule overrides a Gemini "OK" when numbers clearly say otherwise
            fund_tag     = rule_tag
            fund_verdict = rule_verdict

        out[sym] = {
            "fund_pe":      fund_pe,
            "fund_roe":     fund_roe,
            "fund_verdict": fund_verdict,
            "fund_tag":     fund_tag,
        }

    if not out:
        log.debug("[enricher] Fundamental scan: no data — returning empty.")
    return out


# ── Main entry point ───────────────────────────────────────────────────────────

def enrich_signals(signals: list[dict], date_str: str) -> dict[str, dict]:
    """
    Synchronous entry point. Run news filter + fundamental scan in parallel threads.

    Returns per-symbol enrichment:
    {
      "VCB": {
        "news_tag":     "OK" | "CAUTION" | "SKIP",
        "news_note":    "",
        "fund_pe":      12.3,
        "fund_roe":     18.5,
        "fund_verdict": "Định giá hợp lý",
        "fund_tag":     "OK" | "WEAK" | "RISK",
      },
      ...
    }
    Falls back to default (OK, empty) per symbol on any error.
    """
    if not signals:
        return {}

    symbols = [s["symbol"] for s in signals]
    # Default enrichment — used as fallback for any symbol not returned by Gemini
    default = lambda: {
        "news_tag": "OK", "news_note": "",
        "fund_pe": None, "fund_roe": None, "fund_verdict": "", "fund_tag": "OK",
    }
    enrichment = {sym: default() for sym in symbols}

    # Run both enrichments in parallel threads
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_news  = pool.submit(_news_filter,       symbols, date_str)
        f_fund  = pool.submit(_fundamental_scan,  symbols)

        try:
            news_result = f_news.result(timeout=45)
            for sym, data in news_result.items():
                if sym in enrichment:
                    enrichment[sym].update(data)
        except Exception as e:
            log.warning("[enricher] News filter thread failed: %s", e)

        try:
            fund_result = f_fund.result(timeout=45)
            for sym, data in fund_result.items():
                if sym in enrichment:
                    enrichment[sym].update(data)
        except Exception as e:
            log.warning("[enricher] Fundamental scan thread failed: %s", e)

    log.info(
        "[enricher] Done: %d symbols | news flags: %s | fund tags: %s",
        len(symbols),
        {s: enrichment[s]["news_tag"] for s in symbols},
        {s: enrichment[s]["fund_tag"] for s in symbols},
    )
    return enrichment


# ── Discord formatter ──────────────────────────────────────────────────────────

def format_enrichment_section(
    signals: list[dict],
    enrichment: dict[str, dict],
) -> str:
    """
    Build the enrichment block appended below the main shortlist table.

    Layout:
      📰 Tin tức:
        ⚠️ ACB — Q1 lợi nhuận giảm 15% (cẩn thận)
        🚫 XYZ — đang bị điều tra (bỏ qua)
        ✅ VCB, HPG — không có tin xấu nổi bật

      📊 Cơ bản (quý gần nhất):
        VCB  P/E 12.3x ROE 18.5% │ Định giá hợp lý ✅
        HPG  P/E  7.1x ROE 15.2% │ ROE cao P/E thấp ✅
        ACB  P/E  9.4x ROE 20.1% │ Cơ bản tốt ⚠️
    """
    if not enrichment:
        return ""

    lines = []

    # ── News section ──────────────────────────────────────────────────────────
    caution_syms = [s["symbol"] for s in signals if enrichment.get(s["symbol"], {}).get("news_tag") == "CAUTION"]
    skip_syms    = [s["symbol"] for s in signals if enrichment.get(s["symbol"], {}).get("news_tag") == "SKIP"]
    ok_syms      = [s["symbol"] for s in signals if enrichment.get(s["symbol"], {}).get("news_tag") == "OK"]

    lines.append("📰 **Tin tức:**")
    for sym in skip_syms:
        note = enrichment[sym].get("news_note", "")
        lines.append(f"  🚫 `{sym}` — {note} _(nên bỏ qua)_")
    for sym in caution_syms:
        note = enrichment[sym].get("news_note", "")
        lines.append(f"  ⚠️ `{sym}` — {note}")
    if ok_syms:
        lines.append(f"  ✅ {', '.join(f'`{s}`' for s in ok_syms)} — không có tin xấu nổi bật")
    lines.append("")

    # ── Fundamental section ────────────────────────────────────────────────────
    has_fund = any(
        enrichment.get(s["symbol"], {}).get("fund_pe") is not None
        or enrichment.get(s["symbol"], {}).get("fund_roe") is not None
        for s in signals
    )
    if has_fund:
        lines.append("📊 **Cơ bản (quý gần nhất):**")
        lines.append("```")
        for s in signals:
            sym  = s["symbol"]
            e    = enrichment.get(sym, {})
            pe   = e.get("fund_pe")
            roe  = e.get("fund_roe")
            verd = e.get("fund_verdict", "")
            tag  = e.get("fund_tag", "OK")
            tag_icon = {"OK": "✅", "WEAK": "⚠️", "RISK": "🚫"}.get(tag, "")

            pe_str  = f"P/E {pe:.1f}x"  if pe  is not None else "P/E  N/A"
            roe_str = f"ROE {roe:.1f}%" if roe is not None else "ROE  N/A"
            verd_str = f" {verd}" if verd else ""

            lines.append(f"{sym:<5}  {pe_str:<11}  {roe_str:<11} │{verd_str} {tag_icon}")
        lines.append("```")

    return "\n".join(lines)
