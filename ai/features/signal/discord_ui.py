"""
Signal AI Weekly — Discord UI handler

Dùng config weekly (backtest_dynamic_exit) thay vì daily v3a:
  - Cutoff: 0.60 (cố định, không điều chỉnh theo regime)
  - Top-K:  8
  - T2 vol_ratio: BỎ (long-hold không cần vol mạnh lúc vào)
  - T3 EMA ±12%, T4 bearish candles, HC: giống daily
  - Không vào regime recovery
  - Max hold: 120 ngày
  - Exit: re-score mỗi 5 ngày, thoát khi prob < 0.40 (SIGNAL strategy)
"""

from __future__ import annotations

import asyncio
import logging
import numpy as np
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import discord
from discord.ui import View, Button

log = logging.getLogger(__name__)

# ── Weekly model config (từ backtest_dynamic_exit.py) ─────────────────────────
WEEKLY_CUTOFF   = 0.60
WEEKLY_TOP_K    = 8
WEEKLY_MAX_HOLD = 120
WEEKLY_EMA_PCT  = 12.0   # ±12% EMA9 hoặc EMA26
SIGNAL_THRESH   = 0.40   # exit khi re-score prob < 0.40

_DISCORD_CHAR_LIMIT = 1990


# ── Helpers ───────────────────────────────────────────────────────────────────

def _split_message(text: str) -> list[str]:
    if len(text) <= _DISCORD_CHAR_LIMIT:
        return [text]
    parts: list[str] = []
    while text:
        if len(text) <= _DISCORD_CHAR_LIMIT:
            parts.append(text); break
        cut = text.rfind("\n", 0, _DISCORD_CHAR_LIMIT)
        if cut == -1: cut = _DISCORD_CHAR_LIMIT
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts


def _last_friday(ref: Optional[date] = None) -> str:
    d = ref or date.today()
    days_since_fri = (d.weekday() - 4) % 7
    return (d - timedelta(days=days_since_fri)).strftime("%Y-%m-%d")


def _add_n_trading_days(date_str: str, n: int) -> str:
    from datetime import datetime
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    count = 0
    while count < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            count += 1
    return d.strftime("%d/%m")


# ── Weekly scorer ──────────────────────────────────────────────────────────────

def _score_weekly(date_str: str) -> dict:
    """
    Score với weekly config:
      - cutoff=0.60 cố định (không điều chỉnh regime/sector)
      - Bỏ T2 vol_ratio
      - Giữ T3 EMA, T4 candles, HC, không vào recovery
      - Top-K = 8
    """
    import pandas as pd
    from pathlib import Path as _Path

    ROOT = _Path(__file__).resolve().parent.parent.parent

    # ── Detect regime (hiển thị thôi, không dùng để điều chỉnh cutoff) ─────
    regime, _, regime_detail = "sideways", 0.58, {}
    try:
        from pipeline.regime_detector import detect_regime
        regime, _, regime_detail = detect_regime(date_str)
    except Exception as e:
        log.warning("[weekly] regime detection failed: %s", e)

    # Không vào recovery (fast bounce, không hợp long-hold)
    if regime == "recovery":
        return {
            "date": date_str, "regime": regime, "regime_detail": regime_detail,
            "prob_cutoff": WEEKLY_CUTOFF, "signals": [], "near_misses": [],
            "error": f"Regime RECOVERY — không vào (fast bounce, không hợp weekly hold {WEEKLY_MAX_HOLD}d)",
        }

    # ── Feature file ──────────────────────────────────────────────────────────
    feat_path = ROOT / "data" / "features" / f"{date_str}.parquet"
    if not feat_path.exists():
        return {
            "date": date_str, "regime": regime, "regime_detail": regime_detail,
            "prob_cutoff": WEEKLY_CUTOFF, "signals": [], "near_misses": [],
            "error": f"Không có feature file: data/features/{date_str}.parquet",
        }

    # ── Score ─────────────────────────────────────────────────────────────────
    try:
        from pipeline.phase4b_ml_model_20d import load_model_20d, predict_scores_20d
        model, feat_cols = load_model_20d()
        feature_df = pd.read_parquet(feat_path)
        scores = predict_scores_20d(model, feat_cols, feature_df)
    except Exception as e:
        return {
            "date": date_str, "regime": regime, "regime_detail": regime_detail,
            "prob_cutoff": WEEKLY_CUTOFF, "signals": [], "near_misses": [],
            "error": f"Lỗi scoring: {e}",
        }

    n_universe = len(feature_df)
    n_hardcheck = int(scores["hardcheck_pass"].sum()) if "hardcheck_pass" in scores.columns else n_universe

    # Merge feature cols cần cho T3/T4
    fdf = feature_df.copy()
    if "symbol" not in fdf.columns and fdf.index.name == "symbol":
        fdf = fdf.reset_index()
    fdf_idx = fdf.set_index("symbol") if "symbol" in fdf.columns else fdf

    hc_pass = scores[scores["hardcheck_pass"].astype(bool)].copy()

    passed, near_misses = [], []

    for _, row in hc_pass.iterrows():
        sym  = row["symbol"]
        prob = float(row["raw_prob"])
        frow = fdf_idx.loc[sym] if sym in fdf_idx.index else None

        def _get(col, default=np.nan):
            if frow is None: return default
            return frow[col] if col in frow.index else default

        # T1: prob >= 0.60 (cố định)
        if prob < WEEKLY_CUTOFF:
            near_misses.append({"symbol": sym, "prob": prob,
                                "reason": f"T1:prob_low({prob:.3f}<{WEEKLY_CUTOFF})"})
            continue

        # T2: BỎ — không check vol_ratio

        # T3: close ±12% EMA9 hoặc EMA26
        close = _get("close_vnd")
        ema9  = _get("ema9")
        ema26 = _get("ema26")
        near9  = np.isfinite(ema9)  and abs(close / ema9  - 1) * 100 <= WEEKLY_EMA_PCT
        near26 = np.isfinite(ema26) and abs(close / ema26 - 1) * 100 <= WEEKLY_EMA_PCT
        if np.isfinite(close) and not (near9 or near26):
            pct9  = abs(close / ema9  - 1) * 100 if np.isfinite(ema9)  else 999
            pct26 = abs(close / ema26 - 1) * 100 if np.isfinite(ema26) else 999
            near_misses.append({"symbol": sym, "prob": prob,
                                 "reason": f"T3:not_near_ema({pct9:.0f}%/{pct26:.0f}%)"})
            continue

        # T4: không có bearish reversal candles
        t4_fail = None
        if _get("candle_shooting_star", 0) == 1:     t4_fail = "T4:shooting_star"
        elif _get("candle_bearish_engulfing", 0) == 1: t4_fail = "T4:bearish_engulfing"
        elif _get("candle_evening_star", 0) == 1:      t4_fail = "T4:evening_star"
        if t4_fail:
            near_misses.append({"symbol": sym, "prob": prob, "reason": t4_fail})
            continue

        passed.append({
            "symbol":      sym,
            "prob":        round(prob, 4),
            "close_price": float(close) * 1000 if np.isfinite(close) else None,  # → VND
        })

    # Sort by prob, top-K
    passed.sort(key=lambda x: x["prob"], reverse=True)
    signals = passed[:WEEKLY_TOP_K]

    # Near misses: top 5 gần cutoff nhất
    near_misses.sort(key=lambda x: x["prob"], reverse=True)
    near_misses = near_misses[:5]

    return {
        "date":          date_str,
        "regime":        regime,
        "regime_detail": regime_detail,
        "prob_cutoff":   WEEKLY_CUTOFF,
        "n_universe":    n_universe,
        "n_hardcheck":   n_hardcheck,
        "signals":       signals,
        "near_misses":   near_misses,
        "error":         None,
    }


# ── Formatter ─────────────────────────────────────────────────────────────────

def _format_weekly_message(result: dict) -> str:
    from datetime import datetime as _dt

    date_str     = result["date"]
    signals      = result["signals"]
    near_misses  = result["near_misses"]
    regime       = result.get("regime", "sideways")
    rd           = result.get("regime_detail", {})
    n_uni        = result.get("n_universe", 0)
    n_hc         = result.get("n_hardcheck", 0)
    error        = result.get("error")

    regime_emoji = {"recovery":"🟢","bull":"📈","sideways":"🟡","deep_bear":"🔴","choppy":"😴"}
    regime_label = {"recovery":"RECOVERY","bull":"BULL","sideways":"SIDEWAYS",
                    "deep_bear":"DEEP BEAR","choppy":"CHOPPY"}

    try:
        d = _dt.strptime(date_str, "%Y-%m-%d")
        date_display = d.strftime("%d/%m/%Y (%A)")
    except Exception:
        date_display = date_str

    exit_date_short = _add_n_trading_days(date_str, WEEKLY_MAX_HOLD)

    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🤖  **SIGNAL AI WEEKLY — {date_display}**")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    r_emoji = regime_emoji.get(regime, "⚪")
    r_label = regime_label.get(regime, regime.upper())
    ret20   = rd.get("ret_20d", 0)
    vs_ma50 = rd.get("vs_ma50", 0)
    vol20   = rd.get("vol_20d", 0)
    rsi14   = rd.get("rsi_14", 0)
    lines.append(f"{r_emoji} Regime: **{r_label}**  |  VNX: ret20={ret20:+.1f}%  vsMA50={vs_ma50:+.1f}%  vol={vol20:.0f}%  RSI={rsi14:.0f}")
    lines.append("")

    lines.append(
        f"🔧 Model: LightGBM 20D  |  Cutoff: `{WEEKLY_CUTOFF}` (cố định, không điều chỉnh regime)  |  "
        f"Top-K: `{WEEKLY_TOP_K}`  |  Max hold: `{WEEKLY_MAX_HOLD}d`"
    )
    lines.append(
        f"📋 Filters: T1≥0.60 · ~~T2~~ · T3 EMA±12% · T4 no bearish candles · HC · no recovery"
    )
    lines.append(
        f"🚪 Exit: re-score mỗi 5 ngày, thoát khi prob < {SIGNAL_THRESH} (SIGNAL strategy)"
    )
    lines.append(
        f"📊 Vũ trụ: {n_uni} mã → hardcheck: {n_hc} → tín hiệu: **{len(signals)} mã**"
    )
    lines.append("")

    if error:
        lines.append(f"⚠️ **{error}**")
        return "\n".join(lines)

    if signals:
        lines.append(f"📋 **DANH SÁCH ({len(signals)} mã) — Friday {date_str}:**")
        lines.append("```")
        lines.append(f"  {'Mã':<8} {'Prob':>6}  {'Giá(k)':>7}  {'Hold':>6}  {'Thoát':>6}")
        lines.append(f"  {'─'*8} {'─'*6}  {'─'*7}  {'─'*6}  {'─'*6}")
        for s in signals:
            price_k = s["close_price"] / 1000 if s.get("close_price") else 0
            price_s = f"{price_k:,.1f}" if price_k else "—"
            lines.append(
                f"  {s['symbol']:<8} {s['prob']:>6.3f}  {price_s:>7}  T+{WEEKLY_MAX_HOLD}d  {exit_date_short}"
            )
        lines.append("```")
        lines.append(
            f"💡 *Giá(k) = giá đóng cửa (nghìn đ) · Hold = T+{WEEKLY_MAX_HOLD} ngày tối đa · "
            f"Thoát sớm khi prob < {SIGNAL_THRESH}*"
        )
    else:
        lines.append(f"🟡 **Không có tín hiệu đủ điều kiện** (cutoff={WEEKLY_CUTOFF}).")
        if near_misses:
            lines.append(f"\n🔍 **Mã gần qua filter (top 5):**")
            for nm in near_misses:
                lines.append(f"  • {nm['symbol']} prob={nm['prob']:.3f}  _{nm['reason']}_")

    lines.append("")
    lines.append("⚠️ *Tín hiệu tham khảo từ mô hình ML. Không phải khuyến nghị đầu tư.*")
    return "\n".join(lines)


# ── Pipeline runner (blocking) ────────────────────────────────────────────────

def _run_pipeline(date_str: Optional[str] = None, update_data: bool = False) -> dict:
    if date_str is None:
        date_str = _last_friday()

    if update_data:
        try:
            from pipeline.phase1a_ohlcv_store import run_ohlcv_update
            run_ohlcv_update(date_str)
        except Exception as e:
            log.warning("[weekly] OHLCV update failed (non-fatal): %s", e)
        try:
            from pipeline.phase2_feature_pipeline import run_feature_pipeline
            run_feature_pipeline(date_str)
        except Exception as e:
            log.warning("[weekly] Feature update failed (non-fatal): %s", e)

    result = _score_weekly(date_str)
    result["discord_message"] = _format_weekly_message(result)
    return result


# ── Discord helpers ───────────────────────────────────────────────────────────

async def _safe_defer(interaction: discord.Interaction, ephemeral: bool = True) -> bool:
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral)
        return True
    except Exception:
        return False


async def _safe_followup(interaction: discord.Interaction, content: str,
                         *, ephemeral: bool = True, **kwargs):
    try:
        return await interaction.followup.send(content=content, ephemeral=ephemeral, **kwargs)
    except discord.errors.NotFound:
        return None


# ── Result view ───────────────────────────────────────────────────────────────

class SignalWeeklyResultView(View):
    def __init__(self, last_date: Optional[str] = None, timeout: int = 300):
        super().__init__(timeout=timeout)
        self._last_date = last_date

    @discord.ui.button(label="🔄 Cập nhật data & chạy lại", style=discord.ButtonStyle.secondary)
    async def btn_refresh(self, interaction: discord.Interaction, button: Button):
        await _run_and_reply(interaction, date_str=self._last_date, update_data=True)

    @discord.ui.button(label="📅 Friday trước", style=discord.ButtonStyle.secondary)
    async def btn_prev_friday(self, interaction: discord.Interaction, button: Button):
        from datetime import datetime as _dt
        if self._last_date:
            d = _dt.strptime(self._last_date, "%Y-%m-%d").date()
        else:
            d = _dt.strptime(_last_friday(), "%Y-%m-%d").date()
        prev = (d - timedelta(days=7)).strftime("%Y-%m-%d")
        await _run_and_reply(interaction, date_str=prev, update_data=False)


# ── Core runner ───────────────────────────────────────────────────────────────

async def _run_and_reply(
    interaction: discord.Interaction,
    date_str: Optional[str] = None,
    update_data: bool = False,
):
    ok = await _safe_defer(interaction, ephemeral=True)
    if not ok:
        return

    if date_str is None:
        date_str = _last_friday()

    status = (
        f"🔄 Đang cập nhật OHLCV + features cho **{date_str}**… (~1-2 phút)"
        if update_data
        else f"⚡ Đang chạy **weekly model** (cutoff=0.60, top-8, no T2) cho **{date_str}**…"
    )
    await _safe_followup(interaction, status, ephemeral=True)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run_pipeline, date_str, update_data)

    message = result.get("discord_message") or result.get("error") or "Không có kết quả."
    parts = _split_message(message)

    for i, part in enumerate(parts):
        view = SignalWeeklyResultView(last_date=date_str) if i == len(parts) - 1 else None
        kwargs: dict = {"ephemeral": True}
        if view:
            kwargs["view"] = view
        await _safe_followup(interaction, part, **kwargs)


# ── Public entry point ────────────────────────────────────────────────────────

async def open_signal_weekly_entry(interaction: discord.Interaction):
    """Button 7: Signal AI Weekly — dùng weekly config (cutoff=0.60, top-8, no T2)."""
    await _run_and_reply(interaction, date_str=None, update_data=False)
