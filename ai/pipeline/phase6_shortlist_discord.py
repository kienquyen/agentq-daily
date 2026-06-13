"""
Phase 6: Daily Shortlist — Discord Message Generator

Generates today's ML-based buy shortlist and returns a structured result
ready for Discord. Called by the Discord bot Cog at 19:00 ICT.

Workflow:
  1. Update OHLCV data for today       (phase1a, optional — skip if already done)
  2. Recompute today's features        (phase2)
  3. Score all symbols                 (phase4 predict_scores + tier3_filter)
  4. Format Discord message            (Vietnamese, emoji-rich)

Usage (standalone test):
    python -m pipeline.phase6_shortlist_discord
    python -m pipeline.phase6_shortlist_discord --date 2026-04-07
    python -m pipeline.phase6_shortlist_discord --date 2026-04-07 --no-update
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

_OHLCV_DIR = Path(__file__).resolve().parent.parent / "data" / "ohlcv"

# ── helpers ────────────────────────────────────────────────────────────────────

def _is_trading_day(d: date) -> bool:
    """Rough check: Mon–Fri, not a Vietnamese public holiday."""
    return d.weekday() < 5   # 0=Mon … 4=Fri; 5=Sat, 6=Sun


def _last_trading_day(ref: Optional[date] = None) -> str:
    """Return the most-recent weekday on or before ref (default today)."""
    d = ref or date.today()
    while not _is_trading_day(d):
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _add_n_trading_days(date_str: str, n: int) -> str:
    """Return the date that is n trading days (Mon-Fri) after date_str."""
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    count = 0
    while count < n:
        d += timedelta(days=1)
        if _is_trading_day(d):
            count += 1
    return d.strftime("%d/%m")   # short display: DD/MM


def _get_signal_statuses(signal_date: str, symbols: list) -> dict:
    """
    Look up feedback_tracker signal_log.csv for (signal_date, symbol) pairs.

    Returns dict keyed by symbol:
        {
            "status":        "new" | "pending" | "t20" | "stop_loss",
            "actual_return": float | None,   # % (e.g. +7.2 or -10.5)
            "exit_price":    float | None,
            "is_win":        bool | None,    # True if actual_return >= WIN_THRESHOLD
        }

    - "new"       : signal not yet logged (e.g. generated today, before log_signals runs)
    - "pending"   : logged, still holding (T+hold not reached, no SL hit)
    - "t20"       : closed normally at T+hold
    - "stop_loss" : closed early via -10% stop-loss
    """
    default = {"status": "new", "actual_return": None, "exit_price": None, "is_win": None, "exit_date": None}
    result  = {s: dict(default) for s in symbols}
    try:
        from pipeline.feedback_tracker import _SIGNAL_LOG
        sl_path = Path(str(_SIGNAL_LOG))
        if not sl_path.exists():
            return result
        df = pd.read_csv(sl_path, dtype=str)
        df_date = df[df["signal_date"] == signal_date]
        for _, row in df_date.iterrows():
            sym = row.get("symbol", "")
            if sym not in result:
                continue
            db_status   = row.get("status", "pending")
            exit_reason = row.get("exit_reason", "")
            try:
                actual_return = float(row.get("actual_return") or "nan")
                if actual_return != actual_return:   # NaN check
                    actual_return = None
            except (ValueError, TypeError):
                actual_return = None
            try:
                exit_price = float(row.get("exit_price") or "nan")
                if exit_price != exit_price:
                    exit_price = None
            except (ValueError, TypeError):
                exit_price = None

            # Parse exit_date → short "DD/MM" format
            exit_date_raw = row.get("exit_date", "")
            exit_date_short = None
            if exit_date_raw and exit_date_raw.strip():
                try:
                    import datetime as _dt
                    exit_date_short = _dt.datetime.strptime(exit_date_raw.strip(), "%Y-%m-%d").strftime("%d/%m")
                except ValueError:
                    exit_date_short = exit_date_raw.strip()

            if db_status == "completed":
                status_key = exit_reason if exit_reason in ("t20", "stop_loss") else "t20"
            else:
                status_key = "pending"

            # Determine win: from is_win column, fallback to actual_return > 0%
            is_win_raw = row.get("is_win", "")
            if str(is_win_raw).lower() in ("true", "1"):
                is_win = True
            elif str(is_win_raw).lower() in ("false", "0"):
                is_win = False
            elif actual_return is not None:
                is_win = actual_return > 0.0
            else:
                is_win = None

            result[sym] = {
                "status":        status_key,
                "actual_return": actual_return,
                "exit_price":    exit_price,
                "is_win":        is_win,
                "exit_date":     exit_date_short,
            }
    except Exception:
        pass
    return result


def _get_latest_close(symbol: str, as_of: Optional[str] = None) -> Optional[float]:
    """
    Return the latest close price (VND) from data/ohlcv/{symbol}.parquet.
    If as_of is given, return the close on or before that date.
    Returns None if file not found or data insufficient.
    """
    path = _OHLCV_DIR / f"{symbol}.parquet"
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path, columns=["time", "close"])
        df["time"] = pd.to_datetime(df["time"])
        if as_of:
            df = df[df["time"] <= pd.Timestamp(as_of)]
        if df.empty:
            return None
        return float(df.sort_values("time").iloc[-1]["close"])
    except Exception:
        return None


# ── Shadow logging ────────────────────────────────────────────────────────────

def _log_shadow_result(date_str: str, version: str, result: dict) -> None:
    """
    Lưu kết quả shadow scoring vào data/shadow_signals/{version}/{date_str}.json.
    Dùng để so sánh win rate active vs shadow sau N ngày.
    """
    import json as _json
    shadow_dir = Path("data/shadow_signals") / version
    shadow_dir.mkdir(parents=True, exist_ok=True)
    out = {
        "date":          date_str,
        "version":       version,
        "regime":        result.get("regime"),
        "prob_cutoff":   result.get("prob_cutoff"),
        "n_signals":     len(result.get("signals", [])),
        "signals":       [
            {"symbol": s["symbol"], "prob": s["prob"], "close_price": s.get("close_price", 0)}
            for s in result.get("signals", [])
        ],
        "error":         result.get("error"),
    }
    (shadow_dir / f"{date_str}.json").write_text(
        _json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("[shadow] Logged %d signal(s) for %s [%s]",
             out["n_signals"], date_str, version)


# ── OHLCV update (phase1a) ─────────────────────────────────────────────────────

def _update_ohlcv(date_str: str) -> None:
    """Refresh OHLCV store for all symbols up to date_str."""
    try:
        from pipeline.phase1a_ohlcv_store import run as phase1a_run
        log.info("[phase6] Updating OHLCV for %s …", date_str)
        phase1a_run(mode="incremental")
        log.info("[phase6] OHLCV update done.")
    except Exception as exc:
        log.warning("[phase6] OHLCV update failed (non-fatal): %s", exc)


# ── feature update (phase2) ────────────────────────────────────────────────────

def _update_features(date_str: str) -> bool:
    """
    Run Phase 2 for a single date.  Returns True if feature file was written.
    """
    try:
        from pipeline.phase2_feature_pipeline import run as phase2_run
        log.info("[phase6] Computing features for %s …", date_str)
        phase2_run(target_date=date_str)
        feat_path = Path("data/features") / f"{date_str}.parquet"
        ok = feat_path.exists()
        if ok:
            log.info("[phase6] Features ready: %s", feat_path)
        else:
            log.warning("[phase6] Feature file not found after phase2 run.")
        return ok
    except Exception as exc:
        log.error("[phase6] Feature update failed: %s", exc)
        return False


# ── scoring (phase4) ───────────────────────────────────────────────────────────

def _score(date_str: str) -> dict:
    """
    Load features + model → apply tier3 → return structured result.

    Returns:
        {
            "date":        str,
            "n_universe":  int,
            "n_hardcheck": int,
            "prob_cutoff": float,
            "hist_wr":     int,          # approximate historical win rate %
            "signals":     list[dict],   # passed tier3
            "near_misses": list[dict],   # top 5 rejected (closest to cutoff)
            "error":       str | None,
        }
    """
    from pipeline.phase4_ml_model import (
        load_model, predict_scores, tier3_filter, PROB_CUTOFF,
    )

    feat_path = Path("data/features") / f"{date_str}.parquet"
    if not feat_path.exists():
        return {
            "date": date_str, "n_universe": 0, "n_hardcheck": 0,
            "prob_cutoff": PROB_CUTOFF, "hist_wr": 0,
            "signals": [], "near_misses": [], "error": f"No feature file for {date_str}",
        }

    try:
        model, feat_cols = load_model()
        feature_df = pd.read_parquet(feat_path)

        scores = predict_scores(model, feat_cols, feature_df)
        t3 = tier3_filter(scores, feature_df, prob_cutoff=PROB_CUTOFF)

        passed   = t3[t3["tier3_pass"]].copy()
        rejected = t3[~t3["tier3_pass"]].copy()

        n_hardcheck = int(scores["hardcheck_pass"].sum())

        # Historical win rate lookup
        _wr_map = [(0.60, 63), (0.58, 58), (0.56, 56), (0.54, 51),
                   (0.52, 48), (0.50, 44), (0.47, 40), (0.45, 37)]
        hist_wr = next((v for k, v in _wr_map if PROB_CUTOFF >= k - 0.005), 30)

        # Build close_price lookup from feature_df (symbol → close_vnd)
        close_map: dict = {}
        if "close_vnd" in feature_df.columns:
            _idx = feature_df.index if feature_df.index.name == "symbol" else None
            if _idx is not None:
                close_map = feature_df["close_vnd"].to_dict()
            elif "symbol" in feature_df.columns:
                close_map = feature_df.set_index("symbol")["close_vnd"].to_dict()

        signals = [
            {
                "symbol":      row["symbol"],
                "prob":        round(float(row["raw_prob"]), 4),
                "score":       int(row["score_1000"]),
                "rank":        int(row["rank"]),
                "reasons":     row.get("tier3_reasons", ""),
                "close_price": int(close_map.get(row["symbol"], 0)),
            }
            for _, row in passed.iterrows()
        ]

        # Near misses: rejected symbols with highest prob (all already passed hardcheck)
        near_misses_df = (
            rejected
            .sort_values("raw_prob", ascending=False)
            .head(5)
        )
        near_misses = [
            {
                "symbol":  row["symbol"],
                "prob":    round(float(row["raw_prob"]), 4),
                "reasons": row.get("tier3_reasons", ""),
            }
            for _, row in near_misses_df.iterrows()
        ]

        return {
            "date":        date_str,
            "n_universe":  len(scores),
            "n_hardcheck": n_hardcheck,
            "prob_cutoff": PROB_CUTOFF,
            "hist_wr":     hist_wr,
            "signals":     signals,
            "near_misses": near_misses,
            "error":       None,
        }

    except Exception as exc:
        log.error("[phase6] Scoring failed: %s", exc, exc_info=True)
        return {
            "date": date_str, "n_universe": 0, "n_hardcheck": 0,
            "prob_cutoff": PROB_CUTOFF, "hist_wr": 0,
            "signals": [], "near_misses": [],
            "error": str(exc),
        }


# ── Discord message formatter ──────────────────────────────────────────────────

def format_discord_message(result: dict) -> str:
    """
    Format the scoring result as a Discord message (≤2000 chars per chunk).
    Returns a single string; caller splits at \\n\\n---SPLIT---\\n\\n if needed.
    """
    date_str  = result["date"]
    signals   = result["signals"]
    near_miss = result["near_misses"]
    cutoff    = result["prob_cutoff"]
    hist_wr   = result["hist_wr"]
    n_uni     = result["n_universe"]
    n_hc      = result["n_hardcheck"]
    err       = result.get("error")

    # Parse date for display
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = d.strftime("%d/%m/%Y (%A)")
    except Exception:
        date_display = date_str

    lines = []

    # ── Header ──────────────────────────────────────────────────────────────
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🎯  **SHORTLIST MUA — {date_display}**")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(
        f"🤖 Model: LightGBM  |  Cutoff: `{cutoff:.2f}`  |  "
        f"Tỷ lệ thắng lịch sử: **~{hist_wr}%**"
    )
    lines.append(
        f"📊 Vũ trụ: **{n_uni}** mã → hardcheck: **{n_hc}** → "
        f"tín hiệu: **{len(signals)}** mã"
    )
    lines.append("")

    # ── Error state ──────────────────────────────────────────────────────────
    if err:
        lines.append(f"⚠️ **Lỗi khi tạo shortlist:** `{err}`")
        lines.append("Vui lòng kiểm tra log hệ thống.")
        return "\n".join(lines)

    # ── Signals ──────────────────────────────────────────────────────────────
    if signals:
        lines.append(f"📋 **DANH SÁCH MUA ({len(signals)} mã):**")
        lines.append("```")
        lines.append(f"  {'Mã':<6}  {'Giá (nghìn)':>11}  {'Prob':>6}  {'Score':>6}")
        lines.append(f"  {'─'*6}  {'─'*11}  {'─'*6}  {'─'*6}")
        for s in signals:
            price_k = s['close_price'] / 1000 if s.get("close_price") else None
            price_str = f"{price_k:,.1f}" if price_k else "—"
            lines.append(
                f"  {s['symbol']:<6}  {price_str:>11}  {s['prob']:>6.3f}  {s['score']:>6}"
            )
        lines.append("```")
        lines.append(
            "💡 *Mua tại giá đóng cửa hôm nay. "
            f"Target: +3% trong 5 ngày giao dịch.*"
        )
    else:
        lines.append("🔕 **Hôm nay không có mã nào đủ điều kiện.**")
        lines.append("")
        lines.append(
            "> Thị trường hiện chưa tạo ra setup đủ chất lượng "
            f"(prob ≥ {cutoff:.2f}). "
            "Model đang bảo toàn vốn — đây là tính năng, không phải lỗi. 🛡️"
        )

    # ── Near misses ──────────────────────────────────────────────────────────
    if near_miss:
        lines.append("")
        lines.append("🔍 **Mã gần qua filter (top 5):**")
        for nm in near_miss:
            # Extract primary failure reason (first T-tag)
            reason_short = nm["reasons"].split("|")[0] if nm["reasons"] else "—"
            lines.append(
                f"  • `{nm['symbol']}` prob={nm['prob']:.3f}  _{reason_short}_"
            )

    # ── Footer ───────────────────────────────────────────────────────────────
    lines.append("")
    lines.append(
        "⚠️ *Đây là tín hiệu tham khảo từ mô hình ML, "
        "không phải khuyến nghị đầu tư. "
        "Tự chịu trách nhiệm khi giao dịch.*"
    )

    return "\n".join(lines)


# ── 20-day scoring (phase4b) ────────────────────────────────────────────────────

def _score_20d(date_str: str, version: str | None = None) -> dict:
    """
    Score using the 20-day / +5% model with dynamic regime-aware prob cutoff.

    Args:
        date_str: ngày scoring (YYYY-MM-DD)
        version:  model version ('v3a', 'v3b', ...). None = active version.

    Returns same structure as _score() but with horizon/target/regime metadata.
    """
    from pipeline.phase4b_ml_model_20d import (
        load_model_20d, predict_scores_20d, tier3_filter_20d, PROB_CUTOFF_20D,
        SECTOR_CUTOFFS, HOLD_DAYS_REGIME, HOLD_DAYS_DEFAULT,
    )
    from pipeline.regime_detector import (
        detect_regime, REGIME_CUTOFFS, REGIME_SIZE_MULT,
    )

    # ── Load version config (fallback to hardcoded constants) ────────────────
    try:
        from pipeline.model_registry import registry
        _ver = version or registry.active()
        cfg = registry.config(_ver)
    except Exception:
        cfg = {}
        _ver = version or "v3a"

    _regime_cutoffs  = cfg.get("regime_cutoffs",  REGIME_CUTOFFS)
    _regime_size     = cfg.get("regime_size_mult", REGIME_SIZE_MULT)
    _hold_days_map   = cfg.get("hold_days_regime", HOLD_DAYS_REGIME)
    _hold_default    = cfg.get("hold_days_default", HOLD_DAYS_DEFAULT)
    _sector_cutoffs  = cfg.get("sector_cutoffs",   SECTOR_CUTOFFS)
    _sector_db       = cfg.get("sector_cutoffs_deep_bear", None)
    _tier5_threshold = cfg.get("tier_filters", {}).get("T5_vol_spike_ratio", 1.6)
    _tier5_regimes   = cfg.get("tier_filters", {}).get("T5_regimes", ["deep_bear", "choppy"])
    _topk_per_regime = cfg.get("topk_per_regime", {})

    feat_path = Path("data/features") / f"{date_str}.parquet"

    # ── Detect regime ─────────────────────────────────────────────────────────
    regime, dynamic_cutoff, regime_detail = detect_regime(date_str,
                                                           cutoff_map=_regime_cutoffs)
    size_mult = regime_detail.get("size_mult", _regime_size.get(regime, 1.0))
    hold_days = _hold_days_map.get(regime, _hold_default)
    log.info(
        "[phase6] 20D [%s] regime=%s  cutoff=%.2f  size=%.1fx  "
        "ret20=%+.1f%%  vs_ma50=%+.1f%%  vol=%.1f%%  rsi=%.0f",
        _ver, regime, dynamic_cutoff, size_mult,
        regime_detail.get("ret_20d", 0), regime_detail.get("vs_ma50", 0),
        regime_detail.get("vol_20d", 0), regime_detail.get("rsi_14", 0),
    )
    log.info(
        "[phase6] 20D regime=%s  cutoff=%.2f (v2 dynamic)  size=%.1fx  "
        "ret20=%+.1f%%  vs_ma50=%+.1f%%  vol=%.1f%%  rsi=%.0f",
        regime, dynamic_cutoff, size_mult,
        regime_detail.get("ret_20d", 0), regime_detail.get("vs_ma50", 0),
        regime_detail.get("vol_20d", 0), regime_detail.get("rsi_14", 0),
    )

    if not feat_path.exists():
        return {
            "date": date_str, "n_universe": 0, "n_hardcheck": 0,
            "prob_cutoff": dynamic_cutoff, "hist_wr": 59,
            "horizon": "20d", "target_pct": 5, "model_version": _ver,
            "regime": regime, "regime_detail": regime_detail,
            "size_mult": size_mult, "hold_days": hold_days,
            "signals": [], "near_misses": [], "error": f"No feature file for {date_str}",
        }

    try:
        model, feat_cols = load_model_20d(version=_ver)
        feature_df = pd.read_parquet(feat_path)

        n_universe_raw = len(feature_df)

        # ── Filter: chỉ giữ mã có data đúng target_date ──────────────────────
        if "date" in feature_df.columns:
            feature_df = feature_df[feature_df["date"] == date_str].copy()
        n_fresh = len(feature_df)
        n_stale = n_universe_raw - n_fresh
        log.info(
            "[phase6] [%s] Date filter: %d total → %d fresh (%d stale) for %s",
            _ver, n_universe_raw, n_fresh, n_stale, date_str,
        )

        scores   = predict_scores_20d(model, feat_cols, feature_df)
        # Use version-specific sector cutoffs
        active_sector_cutoffs = (
            _sector_db if (regime == "deep_bear" and _sector_db) else _sector_cutoffs
        )
        t3       = tier3_filter_20d(scores, feature_df,
                                    prob_cutoff=dynamic_cutoff,
                                    sector_cutoffs=active_sector_cutoffs,
                                    regime=regime)

        passed   = t3[t3["tier3_pass"]].copy()
        rejected = t3[~t3["tier3_pass"]].copy()

        n_hardcheck = int(scores["hardcheck_pass"].sum())

        # Historical WR by regime (backtest 43,146 signals 2022-07→2026-04, optimal cutoffs)
        _wr_map_20d = {
            "recovery":  71,  # cutoff=0.53: WR5=70.9%, Sharpe=4.12, SL=0.3%
            "bull":      57,  # cutoff=0.55: WR5=57.3%, Sharpe=2.47, SL=1.0%
            "sideways":  61,  # cutoff=0.58: WR5=61.4%, Sharpe=2.97, SL=1.1%
            "deep_bear": 77,  # cutoff=0.58: WR5=77.1%, Sharpe=2.40, SL=8.0%
            "choppy":    62,  # cutoff=0.58: WR5=61.8%, Sharpe=3.52, SL=0.7%
        }
        hist_wr = _wr_map_20d.get(regime, 74)

        close_map: dict = {}
        if "close_vnd" in feature_df.columns:
            if feature_df.index.name == "symbol":
                close_map = feature_df["close_vnd"].to_dict()
            elif "symbol" in feature_df.columns:
                close_map = feature_df.set_index("symbol")["close_vnd"].to_dict()

        raw_signals = [
            {
                "symbol":      row["symbol"],
                "prob":        round(float(row["raw_prob"]), 4),
                "score":       int(row["score_1000"]),
                "rank":        int(row["rank"]),
                "reasons":     row.get("tier3_reasons", ""),
                "close_price": int(close_map.get(row["symbol"], 0)),
            }
            for _, row in passed.iterrows()
        ]

        # ── Pyramid position filter ───────────────────────────────────────────
        # Skip signals for symbols that already have an open position,
        # unless price has moved ≥3% up since last entry (pyramid layer 2).
        # Max 2 concurrent layers per symbol. No averaging down.
        try:
            from pipeline.position_filter import apply_position_filter
            signals, pos_blocked = apply_position_filter(raw_signals, date_str)
            if pos_blocked:
                log.info(
                    "[phase6] Position filter: %d raw → %d allowed, %d blocked",
                    len(raw_signals), len(signals), len(pos_blocked),
                )
        except Exception as pf_exc:
            log.warning("[phase6] Position filter failed (non-fatal): %s", pf_exc)
            signals, pos_blocked = raw_signals, []

        # ── Top-K per regime filter ───────────────────────────────────────────
        # Limit signals to top-K based on regime (capital management).
        # Signals that pass all filters but exceed K are shown separately
        # as "topk_overflow" — visible in Discord for manual review.
        topk_overflow: list[dict] = []
        if _topk_per_regime:
            k = _topk_per_regime.get(regime, _topk_per_regime.get("unknown", 0))
            if k and k > 0 and len(signals) > k:
                # signals already sorted by prob descending (from tier3_filter)
                signals_sorted = sorted(signals, key=lambda s: s["prob"], reverse=True)
                topk_overflow  = signals_sorted[k:]
                signals        = signals_sorted[:k]
                log.info(
                    "[phase6] Top-K filter: regime=%s k=%d → %d signals, %d overflow",
                    regime, k, len(signals), len(topk_overflow),
                )

        near_misses = [
            {
                "symbol":  row["symbol"],
                "prob":    round(float(row["raw_prob"]), 4),
                "reasons": row.get("tier3_reasons", ""),
            }
            for _, row in rejected.sort_values("raw_prob", ascending=False).head(5).iterrows()
        ]

        return {
            "date":            date_str,
            "model_version":   _ver,
            "n_universe":      len(scores),
            "n_universe_raw":  n_universe_raw,
            "n_fresh":         n_fresh,
            "n_stale":         n_stale,
            "n_hardcheck":     n_hardcheck,
            "prob_cutoff":     dynamic_cutoff,
            "hist_wr":         hist_wr,
            "horizon":         "20d",
            "target_pct":      5,
            "regime":          regime,
            "regime_detail":   regime_detail,
            "size_mult":       size_mult,
            "hold_days":       hold_days,
            "topk_limit":      _topk_per_regime.get(regime, 0) if _topk_per_regime else 0,
            "signals":         signals,
            "signals_raw":     raw_signals,
            "topk_overflow":   topk_overflow,
            "pos_blocked":     pos_blocked,
            "near_misses":     near_misses,
            "error":           None,
        }

    except Exception as exc:
        log.error("[phase6] 20D [%s] scoring failed: %s", _ver, exc, exc_info=True)
        return {
            "date": date_str, "model_version": _ver,
            "n_universe": 0, "n_hardcheck": 0,
            "prob_cutoff": dynamic_cutoff, "hist_wr": 59,
            "horizon": "20d", "target_pct": 5,
            "regime": regime, "regime_detail": regime_detail, "size_mult": size_mult,
            "signals": [], "near_misses": [],
            "error": str(exc),
        }


def format_discord_message_20d(result: dict) -> str:
    """Format 20-day shortlist result for Discord (regime v2 — 5 regimes)."""
    date_str   = result["date"]
    signals    = result["signals"]
    near_miss  = result["near_misses"]
    cutoff     = result["prob_cutoff"]
    hist_wr    = result["hist_wr"]
    n_uni      = result["n_universe"]
    n_hc       = result["n_hardcheck"]
    err        = result.get("error")
    regime     = result.get("regime", "sideways")
    rd         = result.get("regime_detail", {})
    size_mult  = result.get("size_mult", 1.0)
    hold_days  = result.get("hold_days", 25)

    # ── Regime v2 display maps (5 regimes) ────────────────────────────────────
    regime_emoji = {
        "recovery":  "🟢",
        "bull":      "📈",
        "sideways":  "🟡",
        "deep_bear": "🔴",
        "choppy":    "😴",
    }
    regime_label = {
        "recovery":  "RECOVERY",
        "bull":      "BULL",
        "sideways":  "SIDEWAYS",
        "deep_bear": "DEEP BEAR",
        "choppy":    "CHOPPY",
    }
    regime_note = {
        "recovery":  "Vùng vàng — thị trường nhích dưới MA50, vol vừa phải (WR ~92%)",
        "bull":      "Uptrend rõ ràng — setup tốt, R/R an toàn (WR ~81%)",
        "sideways":  "Đi ngang — filter chặt hơn để loại bỏ noise (WR ~84%→89%)",
        "deep_bear": "Crash/Panic — WR cao nhưng risk đuôi lớn, size nhỏ (WR ~87%)",
        "choppy":    "Drift 2024-H2 — model yếu nhất, cutoff cao, cẩn trọng (WR ~52%)",
    }
    size_note = {
        "recovery":  "↑ Size x1.2 (best regime)",
        "bull":      "Size x1.0 (normal)",
        "sideways":  "Size x1.0 (normal)",
        "deep_bear": "↓ Size x0.5 (fat-tail risk)",
        "choppy":    "↓↓ Size x0.4 (worst regime)",
    }

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = d.strftime("%d/%m/%Y (%A)")
    except Exception:
        date_display = date_str

    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📈  **SHORTLIST DÀI HẠN — {date_display}**")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Regime banner
    r_emoji = regime_emoji.get(regime, "⚪")
    r_label = regime_label.get(regime, regime.upper())
    r_note  = regime_note.get(regime, "")
    r_size  = size_note.get(regime, f"Size x{size_mult:.1f}")
    ret20   = rd.get("ret_20d", 0)
    vs_ma50 = rd.get("vs_ma50", 0)
    vol20   = rd.get("vol_20d", 0)
    rsi14   = rd.get("rsi_14", 0)

    lines.append(f"{r_emoji} **Regime: {r_label}**  —  {r_note}")
    lines.append(
        f"   📐 {r_size}  |  "
        f"VNX: ret20={ret20:+.1f}%  vs_MA50={vs_ma50:+.1f}%  "
        f"vol={vol20:.0f}%  RSI={rsi14:.0f}"
    )
    lines.append("")

    cutoff_tag = (
        "↓ nới" if cutoff < 0.50
        else "↑ chặt hơn" if cutoff > 0.50
        else "= mặc định"
    )
    lines.append(
        f"🤖 Model: LightGBM 20D  |  Cutoff: `{cutoff:.2f}` ({cutoff_tag})  |  "
        f"WR lịch sử: **~{hist_wr}%**"
    )
    # Show per-sector cutoff overrides (regime-aware)
    try:
        from pipeline.phase4b_ml_model_20d import SECTOR_CUTOFFS as _SC, SECTOR_CUTOFFS_DEEP_BEAR as _SC_DB
        active_sc = _SC_DB if result.get("regime") == "deep_bear" else _SC
        if active_sc:
            overrides = "  |  ".join(
                f"{sec}: `{thr:.2f}`" for sec, thr in sorted(active_sc.items())
            )
            regime_note = " *(deep_bear — BĐS override OFF)*" if result.get("regime") == "deep_bear" else ""
            lines.append(f"🏭 Sector cutoffs: {overrides}{regime_note}")
    except Exception:
        pass
    # Funnel stats: raw → fresh → hardcheck → signals
    n_raw   = result.get("n_universe_raw", n_uni)
    n_fresh = result.get("n_fresh", n_uni)
    n_stale = result.get("n_stale", 0)
    stale_note = f" _(bỏ {n_stale} mã data cũ)_" if n_stale > 0 else ""
    topk_limit_hdr = result.get("topk_limit", 0)
    topk_note = f" → top-**{topk_limit_hdr}**" if topk_limit_hdr else ""
    overflow_n = len(result.get("topk_overflow", []))
    overflow_note = f" _(+{overflow_n} vượt giới hạn)_" if overflow_n else ""
    lines.append(
        f"📊 Vũ trụ: **{n_raw}** mã → có data hôm nay: **{n_fresh}**{stale_note}"
        f" → hardcheck: **{n_hc}** → tín hiệu: **{len(signals)}** mã{topk_note}{overflow_note}"
    )
    hold_note = " *(sideways — giữ ngắn hơn, filter chặt hơn)*" if regime == "sideways" else ""
    lines.append(f"🎯 **Target: +5% trong T+{hold_days} ngày giao dịch (~{hold_days//5} tuần)**{hold_note}")
    lines.append("")

    if err:
        lines.append(f"⚠️ **Lỗi:** `{err}`")
        return "\n".join(lines)

    if signals:
        # ── Resolve open/closed status from feedback log ──────────────────────
        statuses = _get_signal_statuses(date_str, [s["symbol"] for s in signals])

        lines.append(f"📋 **DANH SÁCH ({len(signals)} mã):**")
        lines.append("```")
        entry_date_short = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m")
        exit_date_short  = _add_n_trading_days(date_str, hold_days)   # e.g. "17/06"
        # Table: Mã | Vào | Mua(k) | +/- | Giữ | Thoát | Status
        lines.append(f"  {'Mã':<5} {'Vào':>5} {'Mua(k)':>6} {'+/-':>6}  {'Giữ':>4} {'Thoát':>5}  {'Status':<11}")
        lines.append(f"  {'─'*5} {'─'*5} {'─'*6} {'─'*6}  {'─'*4} {'─'*5}  {'─'*11}")
        for s in signals:
            entry_vnd  = s.get("close_price") or 0
            entry_k    = entry_vnd / 1000 if entry_vnd else None
            price_str  = f"{entry_k:,.1f}" if entry_k else "—"

            st          = statuses.get(s["symbol"], {"status": "new", "actual_return": None})
            st_key      = st["status"]
            actual_ret  = st.get("actual_return")

            if st_key in ("t20", "stop_loss"):
                # Closed — show actual return from feedback log
                perf_str = f"{actual_ret:+.1f}%" if actual_ret is not None else "   —  "
                if st_key == "stop_loss":
                    status_str = "!SL"
                else:
                    is_win = st.get("is_win")
                    status_str = "Closed-Win" if is_win else "Closed-Lost"
            else:
                # Open or brand-new — show current vs entry
                cur_vnd = _get_latest_close(s["symbol"])
                if entry_vnd and cur_vnd:
                    perf     = (cur_vnd - entry_vnd) / entry_vnd * 100
                    perf_str = f"{perf:+.1f}%"
                else:
                    perf_str = "   —  "
                status_str = "Open"

            hold_str = f"T+{hold_days}"
            lines.append(
                f"  {s['symbol']:<5} {entry_date_short:>5} {price_str:>6} {perf_str:>6}"
                f"  {hold_str:>4} {exit_date_short:>5}  {status_str:<11}"
            )
        lines.append("```")
        lines.append(
            f"💡 *Mua(k)=giá vào(nghìn đ) · +/-=so entry(Open)/thực tế(Closed) · "
            f"Giữ=T+{hold_days}ngày · Thoát=ngày đích · "
            f"Closed-Win=đóng lãi>0% · Closed-Lost=đóng lỗ≤0% · !SL=cắt lỗ -10% · Open=đang mở*"
        )

        # ── AI Enrichment block (news + fundamental) ──────────────────────────
        enrichment = result.get("enrichment", {})
        if enrichment:
            try:
                from pipeline.shortlist_ai_enricher import format_enrichment_section
                enrich_block = format_enrichment_section(signals, enrichment)
                if enrich_block:
                    lines.append("")
                    lines.append(enrich_block)
            except Exception:
                pass

    else:
        no_signal_msg = {
            "recovery":  f"🟢 **Regime RECOVERY — không có tín hiệu đủ điều kiện (cutoff={cutoff:.2f}).**\n> Thị trường đang trong vùng vàng nhưng chưa có setup tốt hôm nay.",
            "bull":      f"📈 **Regime BULL — không có setup đủ điều kiện (cutoff={cutoff:.2f}).**\n> Uptrend nhưng mô hình chưa tìm thấy cổ phiếu vượt trội — kiên nhẫn.",
            "sideways":  f"🟡 **Regime SIDEWAYS — không có tín hiệu đủ điều kiện (cutoff={cutoff:.2f}).**\n> Thị trường đi ngang, cần tín hiệu mạnh hơn để qua filter.",
            "deep_bear": f"🔴 **Regime DEEP BEAR — không có tín hiệu (cutoff={cutoff:.2f}). Mô hình đang bảo vệ vốn.**\n> Chờ thị trường ổn định hoặc xuất hiện recovery play.",
            "choppy":    f"😴 **Regime CHOPPY — không có tín hiệu (cutoff={cutoff:.2f}). Cẩn trọng tối đa.**\n> Đây là regime nguy hiểm nhất với model. Nên nghỉ ngơi chờ xu hướng rõ.",
        }
        lines.append(no_signal_msg.get(regime,
            f"🔕 **Hôm nay không có mã đủ điều kiện (cutoff={cutoff:.2f}).**"
        ))

    # ── Top-K overflow (passed all filters but cut by regime K limit) ──────────
    topk_overflow = result.get("topk_overflow", [])
    topk_limit    = result.get("topk_limit", 0)
    if topk_overflow:
        lines.append("")
        lines.append(
            f"📊 **Vượt top-{topk_limit} ({regime}) — {len(topk_overflow)} mã đủ điều kiện nhưng quá giới hạn vốn:**"
        )
        for sig in topk_overflow:
            prob_str = f"prob={sig.get('prob', sig.get('raw_prob', 0)):.3f}"
            lines.append(f"  • `{sig['symbol']}` {prob_str}")

    if near_miss:
        lines.append("")
        lines.append("🔍 **Mã gần qua filter (top 5):**")
        for nm in near_miss:
            reason_short = nm["reasons"].split("|")[0] if nm["reasons"] else "—"
            lines.append(f"  • `{nm['symbol']}` prob={nm['prob']:.3f}  _{reason_short}_")

    # ── Position filter blocked signals ──────────────────────────────────────
    pos_blocked = result.get("pos_blocked", [])
    if pos_blocked:
        # Tách riêng cooldown vs concentration/runup
        cooldown_blocked     = [pb for pb in pos_blocked if "cooldown" in pb.get("filter_reason", "")]
        non_cooldown_blocked = [pb for pb in pos_blocked if "cooldown" not in pb.get("filter_reason", "")]

        # Cooldown section — in riêng với emoji và note ngày cụ thể
        if cooldown_blocked:
            lines.append("")
            lines.append(f"⏭️ **Bỏ qua (đã signal trong {28} ngày gần đây):**")
            for pb in cooldown_blocked:
                last_date  = pb.get("cooldown_last_date", "?")
                days_ago   = pb.get("cooldown_days_ago",  0)
                days_left  = pb.get("cooldown_days_left", 0)
                prob_str   = f"prob={pb.get('prob', pb.get('raw_prob', 0)):.3f}"
                lines.append(
                    f"  • `{pb['symbol']}` {prob_str}"
                    f"  — signal {last_date} ({days_ago}d trước, còn ~{days_left}d)"
                )

        # Concentration / runup section
        if non_cooldown_blocked:
            lines.append("")
            lines.append("🔒 **Bỏ qua (vượt giới hạn tập trung vốn):**")
            for pb in non_cooldown_blocked:
                reason = pb.get("filter_reason", "")
                if "concentration" in reason:
                    note = "vượt 40% danh mục"
                elif "runup" in reason:
                    note = "giá đã tăng >7% từ entry trước (WR thấp)"
                else:
                    note = reason
                prob_str = f"prob={pb.get('prob', pb.get('raw_prob', 0)):.3f}"
                lines.append(f"  • `{pb['symbol']}` {prob_str}  — {note}")

    lines.append("")
    lines.append(
        "⚠️ *Tín hiệu tham khảo từ mô hình ML. "
        "Không phải khuyến nghị đầu tư. Tự chịu trách nhiệm.*"
    )
    return "\n".join(lines)


# ── Public API ─────────────────────────────────────────────────────────────────

def get_shortlist(
    date_str: Optional[str] = None,
    update_ohlcv: bool = True,
    update_features: bool = True,
) -> dict:
    """
    Full pipeline: update data → score → return result dict.

    Args:
        date_str:         Target date (YYYY-MM-DD). Default = last trading day.
        update_ohlcv:     If True, refresh OHLCV store before computing features.
        update_features:  If True, recompute phase-2 features for date_str.

    Returns:
        Result dict (see _score) with an extra "discord_message" key.
    """
    if date_str is None:
        date_str = _last_trading_day()

    log.info("[phase6] Generating shortlist for %s", date_str)

    if update_ohlcv:
        _update_ohlcv(date_str)

    if update_features:
        ok = _update_features(date_str)
        if not ok:
            log.warning("[phase6] Feature update failed — trying to score with existing file.")

    result = _score(date_str)
    result["discord_message"] = format_discord_message(result)
    return result


def get_shortlist_20d(
    date_str: Optional[str] = None,
    update_ohlcv: bool = True,
    update_features: bool = True,
) -> dict:
    """
    Full pipeline for 20-day model: update data → score → return result dict.

    Returns:
        Result dict (see _score_20d) with an extra "discord_message" key.
    """
    if date_str is None:
        date_str = _last_trading_day()

    log.info("[phase6] Generating 20D shortlist for %s", date_str)

    if update_ohlcv:
        _update_ohlcv(date_str)

    if update_features:
        ok = _update_features(date_str)
        if not ok:
            log.warning("[phase6] Feature update failed — trying to score with existing file.")

    result = _score_20d(date_str)

    # ── Shadow mode: chạy version phụ song song, log kết quả (không hiển thị) ──
    shadow_result: dict | None = None
    try:
        from pipeline.model_registry import registry as _reg
        _shadow_ver = _reg.shadow()
        _active_ver = _reg.active()
        if _shadow_ver and _shadow_ver != _active_ver:
            log.info("[phase6] Shadow scoring: %s", _shadow_ver)
            shadow_result = _score_20d(date_str, version=_shadow_ver)
            _log_shadow_result(date_str, _shadow_ver, shadow_result)
    except Exception as _se:
        log.warning("[phase6] Shadow scoring failed (non-fatal): %s", _se)
    result["shadow"] = shadow_result

    # ── v5 shadow (alpha-10 value model — separate scorer, log only) ──────────
    try:
        from pipeline.v5_shadow import log_v5_shadow
        v5_res = log_v5_shadow(date_str)
        log.info("[phase6] v5 shadow: %d signal(s) logged", v5_res.get("n_signals", 0))
    except Exception as _v5e:
        log.warning("[phase6] v5 shadow failed (non-fatal): %s", _v5e)

    # ── AI Enrichment: news filter + fundamental scan ─────────────────────────
    enrichment: dict = {}
    if result.get("signals"):
        try:
            from pipeline.shortlist_ai_enricher import enrich_signals
            enrichment = enrich_signals(result["signals"], date_str)
            log.info("[phase6] AI enrichment done for %d signal(s).", len(result["signals"]))
        except Exception as exc:
            log.warning("[phase6] AI enrichment failed (non-fatal): %s", exc)
    result["enrichment"] = enrichment

    result["discord_message"] = format_discord_message_20d(result)

    # ── Feedback loop: log signals for T+N tracking (regime-aware hold) ─────────
    try:
        from pipeline.feedback_tracker import log_signals
        n_logged = log_signals(
            signal_date = date_str,
            signals     = result.get("signals", []),
            regime      = result.get("regime", "sideways"),
            cutoff      = result.get("prob_cutoff", 0.50),
            hold_days   = result.get("hold_days", 25),
        )
        if n_logged:
            log.info("[phase6] Feedback: logged %d new signal(s) for %s", n_logged, date_str)
    except Exception as exc:
        log.warning("[phase6] Feedback log failed (non-fatal): %s", exc)

    return result


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    p = argparse.ArgumentParser(description="Phase 6 — Daily Shortlist Discord Message")
    p.add_argument("--date",       type=str, default=None,  help="Target date YYYY-MM-DD (default: last trading day)")
    p.add_argument("--no-update",  action="store_true",     help="Skip OHLCV + feature update (use cached files)")
    p.add_argument("--no-ohlcv",   action="store_true",     help="Skip OHLCV update only")
    p.add_argument("--20d",        dest="horizon_20d", action="store_true", help="Use 20-day model instead of 5-day")
    args = p.parse_args()

    if args.horizon_20d:
        result = get_shortlist_20d(
            date_str=args.date,
            update_ohlcv=(not args.no_update and not args.no_ohlcv),
            update_features=not args.no_update,
        )
    else:
        result = get_shortlist(
            date_str=args.date,
            update_ohlcv=(not args.no_update and not args.no_ohlcv),
            update_features=not args.no_update,
        )

    print("\n" + "=" * 65)
    print("PHASE 6 — DISCORD PREVIEW")
    print("=" * 65)
    print(result["discord_message"])
    print("=" * 65)
    print(f"\nSignals : {len(result['signals'])}")
    print(f"Error   : {result['error'] or 'None'}")


if __name__ == "__main__":
    main()
