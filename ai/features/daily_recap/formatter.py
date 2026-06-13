from typing import Any, Dict, List
import os
import asyncio
import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


# ─── Distribution Days Interpretation ─────────────────────────────────────────────


def _interpret_dist_days(days: int) -> tuple[str, str]:
    """
    Interpret distribution days count.
    Returns: (level_text, risk_emoji)

    Scale:
      0-2: Sạch (Clean)
      3-4: Thận trọng (Caution)
      5:   Nâng cao (Elevated)
      6-7: Rủi ro cao (High Risk)
      ≥8:   Nguy hiểm (Critical)
    """
    if days <= 2:
        return "Sạch", "🟢"
    elif days <= 4:
        return "Thận trọng", "🟡"
    elif days == 5:
        return "Rủi ro gia tăng", "🟠"
    elif days <= 7:
        return "Rủi ro cao", "🔴"
    else:
        return "Nguy hiểm", "🚨"


# Local imports
try:
    from .recap_template import render_recap_html
    from app.utils.image_generator import html_to_png
except Exception as _img_err:
    print(
        f"[formatter] ❌ Image generation unavailable — {type(_img_err).__name__}: {_img_err}"
    )
    logger.error(
        f"[formatter] Image generation unavailable — {type(_img_err).__name__}: {_img_err}"
    )
    render_recap_html = None
    html_to_png = None


# ─── Image Generation ────────────────────────────────────────────────────────


def _normalize_breakdown(bd: Dict) -> Dict:
    """Normalize regime breakdown keys to what the HTML template expects.
    score_regime() returns: trend, vol, breadth, flow, composite, overrides
    Template expects:       trend, vol, breadth, foreign, valuation
    """
    return {
        "trend": bd.get("trend", 0.5),
        "vol": bd.get("vol", 0.5),
        "breadth": bd.get("breadth", 0.5),
        "foreign": bd.get("flow", bd.get("foreign", 0.5)),
        "valuation": bd.get("valuation", 0.5),
    }


def _regime_vn(regime: str) -> str:
    """Map regime to Vietnamese name."""
    return {
        "bull_trending": "XU HƯỚNG TĂNG",
        "recovery": "ĐANG HỒI PHỤC",
        "ranging": "TÍCH LŨY",
        "bear_risk": "GIẢM RỦI RO",
    }.get(regime, "QUAN SÁT")


def _regime_recommendation(regime: str) -> str:
    """Get regime recommendation text."""
    return {
        "bear_risk": "Khuyến nghị phân bổ 0–20%",
        "ranging": "Khuyến nghị phân bổ 30–50%",
        "recovery": "Khuyến nghị phân bổ 50–80%",
        "bull_trending": "Khuyến nghị phân bổ 80–100%",
    }.get(regime, "")


async def generate_recap_image(
    data: Dict[str, Any],
    ai_data: Dict[str, Any],
    output_filename: str = "daily_recap.png",
) -> str:
    """
    Synthesizes all data and AI insights into a premium PNG report.
    Returns the output path if successful, empty string otherwise.
    """
    # Module-level import may have failed at startup — retry lazily at runtime
    _render_fn = render_recap_html
    _png_fn = html_to_png
    if not _render_fn or not _png_fn:
        try:
            import importlib, sys as _sys
            import os as _os

            _root = _os.path.dirname(
                _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
            )
            if _root not in _sys.path:
                _sys.path.insert(0, _root)
            from features.daily_recap.recap_template import (
                render_recap_html as _render_fn,
            )  # type: ignore
            from app.utils.image_generator import html_to_png as _png_fn  # type: ignore

            print("[generate_recap_image] ✅ Lazy import succeeded")
        except Exception as _lazy_err:
            print(
                f"[generate_recap_image] ❌ Lazy import also failed — {type(_lazy_err).__name__}: {_lazy_err}"
            )
            return ""

    # 1. Map to Template Schema
    snap_raw = data.get("snapshot", {})

    # Use date from snapshot if available, else current
    raw_date = snap_raw.get("date", datetime.now().strftime("%Y-%m-%d"))
    try:
        formatted_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        formatted_date = datetime.now().strftime("%d/%m/%Y")

    # Format currency/billion values
    def _to_bil(val):
        try:
            return int(val)
        except:
            return 0

    template_data = {
        "mast_date": formatted_date,
        "mast_time": datetime.now().strftime("%H:%M"),
        "snapshot": {
            "date": formatted_date,
            "vni_price": f"{snap_raw.get('vnindex', 0):,.2f}",
            "vni_chg": snap_raw.get("change_abs", 0),
            "vni_chg_pct": f"{snap_raw.get('change_pct', 0):+.2f}",
            "vs_ma50_pct": f"{snap_raw.get('vs_ma50_pct', 0):+.2f}",
            "vs_ma50_pct_val": snap_raw.get("vs_ma50_pct", 0),
            "usd_vnd": f"{snap_raw.get('usd_vnd', 0):,.0f}"
            if snap_raw.get("usd_vnd")
            else "—",
            "dist_days": snap_raw.get("dist_days", 0),
            "advances": snap_raw.get("ad_advances", 0),
            "declines": snap_raw.get("ad_declines", 0),
            "ad_de_ratio": f"{'🔼' if snap_raw.get('ad_de_ratio', 0) >= 1 else '🔽'} {snap_raw.get('ad_de_ratio', 0):,.2f}",
            "ad_de_ratio_val": snap_raw.get("ad_de_ratio", 0),
            "foreign_flow_bil": _to_bil(snap_raw.get("foreign_flow_bil", 0)),
            "exposure_pct": ai_data.get(
                "exposure_pct", snap_raw.get("exposure_pct", 45)
            ),
        },
        "ai_data": {
            "regime": ai_data.get("regime", "ranging"),
            "regime_vn": _regime_vn(ai_data.get("regime", "ranging")),
            "regime_recommendation": _regime_recommendation(
                ai_data.get("regime", "ranging")
            ),
            "regime_score": ai_data.get("regime_score", 0.5),
            "regime_breakdown": _normalize_breakdown(
                ai_data.get("regime_breakdown", {})
            ),
            "regime_takeaway": ai_data.get("regime_takeaway", "Quan sát thị trường"),
            "interpretation": ai_data.get("interpretation", ""),
            "playbook": ai_data.get("playbook", []),
        },
        "flow": {
            "inflow": [
                {
                    "sector": item["sector"],
                    "tickers": item["tickers"],
                    "value": _to_bil(item.get("value_bil", item.get("value", 0))),
                }
                for item in data.get("flow", {}).get("inflow", [])
            ],
            "outflow": [
                {
                    "sector": item["sector"],
                    "tickers": item["tickers"],
                    "value": _to_bil(item.get("value_bil", item.get("value", 0))),
                }
                for item in data.get("flow", {}).get("outflow", [])
            ],
        },
        "flow_data_quality": data.get("flow_data_quality", "verified"),
        "watchlist": {},
        "weekly_watchlist": [],
        "catalysts": [],
        "ticker_flow": {"inflow": [], "outflow": []},
        "portfolio_actions": [],
        "news": ai_data.get("ai_news", [])[:5],
    }

    # Both watchlists sourced from flow data.
    # ticker_flow (individual stocks) needs foreign_trade to work — empty in historical mode when API fails.
    # flow (sector-level) always works and includes top tickers per sector.
    raw_tf = data.get("ticker_flow", {})
    flow_data = data.get("flow", {})

    # Build sector lookup: prefer ticker_flow (individual) then flow (sector)
    ticker_sectors = {
        item["ticker"]: item.get("sector", "") for item in raw_tf.get("inflow", [])
    }
    ticker_sectors.update(
        {item["ticker"]: item.get("sector", "") for item in raw_tf.get("outflow", [])}
    )
    ticker_sectors.update(
        {
            t: item.get("sector", "Khác")
            for item in flow_data.get("inflow", []) + flow_data.get("outflow", [])
            for t in item.get("tickers", [])
        }
    )

    # Daily watchlist: all tickers from ticker_flow inflow (up to 50)
    daily_candidates = sorted(
        raw_tf.get("inflow", []),
        key=lambda x: x.get("value_bil", 0) or 0,
        reverse=True,
    )

    # Weekly watchlist: top 30 tickers by 7-day cumulative inflow via fetch_session_stats
    weekly_inflow_map: Dict[str, float] = {}
    _target_date = snap_raw.get("date")
    if _target_date:
        try:
            # Build weekly ticker pool: top 30 from ticker_flow inflow + sector flow
            weekly_pool_set = {item["ticker"] for item in daily_candidates[:30]}
            for item in flow_data.get("inflow", []):
                for t in item.get("tickers", [])[:5]:
                    if len(weekly_pool_set) >= 30:
                        break
                    weekly_pool_set.add(t)
            weekly_ticker_pool = list(weekly_pool_set)

            from vnstock_data import Trading
            from infrastructure.external.market_data import fetch_history
            from datetime import datetime as dt, timedelta

            target_dt = dt.strptime(_target_date, "%Y-%m-%d")
            lookback, trading_days, lookback_start = 0, 0, target_dt
            while trading_days < 7 and lookback < 20:
                lookback_start = target_dt - timedelta(days=lookback)
                try:
                    hist = await asyncio.to_thread(
                        fetch_history,
                        "VND",
                        lookback_start.strftime("%Y-%m-%d"),
                        _target_date,
                    )
                    if hist is not None and not hist.empty:
                        trading_days = len(hist)
                except Exception:
                    pass
                lookback += 1
            week_start = lookback_start.strftime("%Y-%m-%d")

            async def _fetch_7day(ticker):
                try:
                    trd = Trading(source="vci", symbol=ticker)
                    df = await asyncio.to_thread(
                        trd.foreign_trade, start=week_start, end=_target_date
                    )
                    if df is None or df.empty:
                        return ticker, 0.0
                    total_net = 0.0
                    for _, row in df.iterrows():
                        bv = float(row.get("fr_buy_value_matched", 0) or 0)
                        sv = float(row.get("fr_sell_value_matched", 0) or 0)
                        total_net += bv - sv
                    return ticker, round(total_net / 1e9, 1)
                except Exception:
                    return ticker, 0.0

            sem = asyncio.Semaphore(2)

            async def _bounded_fetch(ticker):
                async with sem:
                    return await _fetch_7day(ticker)

            weekly_results = await asyncio.gather(
                *[_bounded_fetch(t) for t in weekly_ticker_pool]
            )
            weekly_inflow_map = dict(weekly_results)
        except Exception as e:
            print(f"[generate_recap_image] ⚠️ 7-day inflow fetch failed: {e}")

    weekly_candidates = sorted(
        [t for t, v in weekly_inflow_map.items() if v > 0],
        key=lambda t: weekly_inflow_map.get(t, 0),
        reverse=True,
    )

    # Also use ai_data watchlist_signals (bullish inflow tickers from _get_watchlist_signals)
    wl_signals = (
        ai_data.get("watchlist_signals") or data.get("watchlist_signals", {}) or {}
    )

    # Import once for signal fetching; use target_date from snapshot for historical accuracy
    try:
        from app.vnstock_core.core import fetch_technical_signals

        _fts = fetch_technical_signals
    except Exception:
        _fts = None

    def _build_signal_label(ema, rsi):
        if ema == 1:
            return f"EMA tăng · RSI {rsi}"
        elif ema == -1:
            return f"EMA giảm · RSI {rsi}"
        elif rsi >= 60:
            return f"Momentum tăng · RSI {rsi}"
        elif rsi < 40:
            return f"Bán quá mức · RSI {rsi}"
        else:
            return f"Trung lập · RSI {rsi}"

    # Build signals dict for daily + weekly candidates (fetch if not already available)
    ticker_signals = dict(wl_signals)
    all_candidate_tickers = set(
        [item["ticker"] for item in daily_candidates] + weekly_candidates
    )
    for ticker in all_candidate_tickers:
        if ticker not in ticker_signals and _fts:
            try:
                sig = await asyncio.to_thread(
                    _fts, ticker, lookback_days=80, target_date=_target_date
                )
                if sig and sig.get("rsi14") is not None:
                    ticker_signals[ticker] = sig
            except Exception:
                pass

    # Section 4 — Danh sách theo dõi ngày: filter EMA9>EMA26 + RSI<80 first, then top 5 by inflow, ranked by score
    daily_filtered = []
    for item in daily_candidates:
        ticker = item["ticker"]
        sig = ticker_signals.get(ticker, {})
        rsi_raw = sig.get("rsi14")
        rsi = int(rsi_raw) if rsi_raw is not None else 50
        ema = sig.get("ema_cross")
        ema = ema if ema is not None else 0
        if ema != 1 or rsi >= 80:
            continue
        score = min(100, max(0, int((rsi - 30) * 1.5)))
        inflow_val = item.get("value_bil", 0) or 0
        daily_filtered.append(
            {
                "ticker": ticker,
                "sector": ticker_sectors.get(ticker, "Khác"),
                "label": _build_signal_label(ema, rsi),
                "rsi14": rsi,
                "score": score,
                "inflow": inflow_val,
            }
        )

    daily_filtered.sort(key=lambda x: x["inflow"], reverse=True)
    daily_filtered = daily_filtered[:5]
    daily_filtered.sort(key=lambda x: x["score"], reverse=True)
    for row in daily_filtered:
        template_data["watchlist"][row["ticker"]] = {
            "label": row["label"],
            "rsi14": row["rsi14"],
            "score": row["score"],
        }

    # Section 5 — Danh mục theo dõi tuần: filter first, then top 5 by 7-day inflow, ranked by score
    weekly_filtered = []
    for ticker in weekly_candidates:
        sig = ticker_signals.get(ticker, {})
        rsi_raw = sig.get("rsi14")
        rsi = int(rsi_raw) if rsi_raw is not None else 50
        ema_cross = sig.get("ema_cross")
        ema_cross = ema_cross if ema_cross is not None else 0
        if ema_cross != 1 or rsi >= 80:
            continue
        score = min(100, max(0, int((rsi - 30) * 1.5)))
        inflow_val = weekly_inflow_map.get(ticker, 0)
        weekly_filtered.append(
            {
                "ticker": ticker,
                "sector": ticker_sectors.get(ticker, "Khác"),
                "rsi14": rsi,
                "score": score,
                "inflow": inflow_val,
            }
        )

    weekly_filtered.sort(key=lambda x: x["inflow"], reverse=True)
    weekly_filtered = weekly_filtered[:5]
    weekly_filtered.sort(key=lambda x: x["score"], reverse=True)
    template_data["weekly_watchlist"] = weekly_filtered

    # Render HTML and convert to PNG
    try:
        html_content = _render_fn(template_data)
        output_path = await _png_fn(
            html_content,
            output_filename,
        )
        return output_path or ""
    except Exception as _img_err:
        print(
            f"[generate_recap_image] ❌ PNG generation failed — {type(_img_err).__name__}: {_img_err}"
        )
        import traceback

        traceback.print_exc()
        return ""


def _pct_icon(pct: float) -> str:
    if pct > 0:
        return "🔼"
    if pct < 0:
        return "🔽"
    return "⚪"


def _tag_emoji(tag: str) -> str:
    tag = tag.lower()
    if "macro" in tag or "fed" in tag or "inflation" in tag:
        return "📊 Macro · "
    if "sector" in tag or "industry" in tag:
        return "🏭 Sector · "
    if "risk" in tag or "alert" in tag:
        return "⚠️ Risk · "
    return "📰 "


def _level_label(level: str) -> str:
    level = level.lower()
    if level in ("high", "cao", "cao."):
        return "🔴 Cao"
    if level in ("medium", "med", "trung bình"):
        return "🟡 TB"
    if level in ("low", "thấp", "thấp."):
        return "🟢 Thấp"
    return "⚪ Trung bình"


def format_daily_recap(
    data: Dict[str, Any], ai_data: Dict[str, Any], mode: str = "full"
) -> str:
    snap = data.get("snapshot", {})
    raw_date = snap.get("date", datetime.now().strftime("%Y-%m-%d"))
    try:
        date_str = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        date_str = datetime.now().strftime("%d/%m/%Y")

    lines = []

    # ── HEADER ──
    lines.append(f"🇻🇳 **AgentQ — Bản Tin Sáng** — {date_str}\n")

    if ai_data and ai_data.get("regime"):
        reg = ai_data["regime"]
        score = ai_data.get("regime_score", 0.5)
        bd = ai_data.get("regime_breakdown", {})

        reg_emoji = {
            "bull_trending": "🟢",
            "recovery": "🔵",
            "ranging": "🟡",
            "bear_risk": "🔴",
        }.get(reg, "⚪")

        from .ai_generator import label_vn_regime

        reg_vn = label_vn_regime(reg)

        lines.append(f"🧭 Thị trường: {reg_emoji} {reg_vn.upper()} (Điểm: {score:.2f})")

        t, v, b = bd.get("trend", 0), bd.get("vol", 0), bd.get("breadth", 0)
        f, va = bd.get("foreign", 0), bd.get("valuation", 0)
        lines.append(f"```")
        lines.append(f"Xu hướng {t:.2f} · Biến động {v:.2f} · Độ rộng {b:.2f}")
        lines.append(f"Dòng tiền {f:.2f} · Định giá {va:.2f}")
        lines.append(f"```")

        if ai_data.get("regime_takeaway"):
            lines.append(f"💡 {ai_data['regime_takeaway']}\n")

    # ── COMPACT MODE ──
    if mode == "compact":
        usd = snap.get("usd_vnd")
        usd_str = f" | USD/VND {usd:,.0f}" if usd else ""
        lines.append(
            f"📊 VNI {snap['vnindex']:.1f} ({snap['change_pct']:+.1f}%)"
            f" · Khối ngoại {snap['foreign_flow_bil']:.0f}B{usd_str}\n"
        )
        inflow = [i["sector"] for i in data.get("flow", {}).get("inflow", [])]
        outflow = [i["sector"] for i in data.get("flow", {}).get("outflow", [])]
        lines.append(
            f"🔥 🟢 {', '.join(inflow) or 'Không có'} | 🔴 {', '.join(outflow) or 'Không có'}\n"
        )
        if ai_data and ai_data.get("playbook"):
            first = ai_data["playbook"][0]
            lines.append(f"🎯 {first.get('action', '')}\n")
        if ai_data and ai_data.get("ai_news"):
            n = ai_data["ai_news"][0]
            txt = (n.get("ai_summary") or n.get("headline", ""))[:100]
            lines.append(f"📰 {_tag_emoji(n.get('tag', 'Neutral'))}{txt}\n")
        return "\n".join(lines).strip()

    # ── FULL MODE ──

    # 1. Market Snapshot
    lines.append("📊 **Tổng quan thị trường**")
    vni_icon = _pct_icon(snap["change_pct"])
    ma_icon = _pct_icon(snap["vs_ma50_pct"])
    usd = snap.get("usd_vnd")
    if usd:
        lines.append(f"• **USD/VND:** {usd:,.0f}")
    lines.append(
        f"• **VNIndex:** {snap['vnindex']:.2f} {vni_icon} ({snap['change_pct']:+.2f}%)"
    )
    lines.append(f"• **Cách MA50:** {ma_icon} {snap['vs_ma50_pct']:+.2f}%")
    lines.append(
        f"• **Ngày phân phối:** {snap['dist_days']} ({_interpret_dist_days(snap['dist_days'])[1]} {_interpret_dist_days(snap['dist_days'])[0]})"
    )
    lines.append(
        f"• **Độ rộng:** {snap['ad_advances']} Tăng / "
        f"{snap.get('ad_unchanged', 0)} Đi ngang / {snap['ad_declines']} Giảm "
        f"**(A/D: {'🔼' if snap.get('ad_de_ratio', 0) >= 1 else '🔽'} {snap.get('ad_de_ratio', 0.0):.2f})**"
    )
    lines.append(f"• **Khối ngoại:** {snap['foreign_flow_bil']:.0f}B\n")

    # 2. Money Flow — Sector view
    lines.append("🔥 **Dòng tiền theo Ngành** (Foreign Net Value)")
    outflow_list = data.get("flow", {}).get("outflow", [])
    inflow_list = data.get("flow", {}).get("inflow", [])

    lines.append("🔴 Dòng ra:")
    if outflow_list:
        for item in outflow_list:
            val_str = f" ({item['value_bil']:+.0f}B)" if item.get("value_bil") else ""
            lines.append(
                f"- {item['sector'].ljust(12)}: {', '.join(item['tickers'][:6])}{val_str}"
            )
    else:
        lines.append("- Không có")

    lines.append("🟢 Dòng vào:")
    if inflow_list:
        for item in inflow_list:
            val_str = f" ({item['value_bil']:+.0f}B)" if item.get("value_bil") else ""
            lines.append(
                f"- {item['sector'].ljust(12)}: {', '.join(item['tickers'][:6])}{val_str}"
            )
    else:
        lines.append("- Không có")
    lines.append("")

    # 2b. Top-5 individual stocks removed per user request

    # 3 & 4. Watchlists
    raw_tf = data.get("ticker_flow", {})
    flow_data = data.get("flow", {})

    # Sector lookup
    ticker_sectors = {}
    for item in raw_tf.get("inflow", []) + raw_tf.get("outflow", []):
        ticker_sectors[item.get("ticker", "")] = item.get("sector", "")
    for item in flow_data.get("inflow", []) + flow_data.get("outflow", []):
        for t in item.get("tickers", []):
            ticker_sectors[t] = item.get("sector", "Khác")

    # Daily: top 5 from ticker_flow (sorted by daily inflow desc)
    daily_candidates = sorted(
        raw_tf.get("inflow", []),
        key=lambda x: x.get("value_bil", 0) or 0,
        reverse=True,
    )

    # Weekly: top tickers by 7-day cumulative inflow via fetch_session_stats
    weekly_inflow_map: Dict[str, float] = {}
    if daily_candidates:
        try:
            from app.vnstock_core.core import fetch_session_stats

            td = data.get("snapshot", {}).get("date")
            if td:
                weekly_pool = list({item["ticker"] for item in daily_candidates[:30]})
                seen = set(weekly_pool)
                for item in flow_data.get("inflow", []):
                    for t in item.get("tickers", [])[:5]:
                        if len(weekly_pool) >= 30:
                            break
                        if t not in seen:
                            weekly_pool.append(t)
                            seen.add(t)
                from vnstock_data import Trading
                from infrastructure.external.market_data import fetch_history
                from datetime import datetime as dt, timedelta

                target_dt = dt.strptime(td, "%Y-%m-%d")
                lookback, trading_days, lookback_start = 0, 0, target_dt
                while trading_days < 7 and lookback < 20:
                    lookback_start = target_dt - timedelta(days=lookback)
                    try:
                        hist = fetch_history(
                            "VND",
                            lookback_start.strftime("%Y-%m-%d"),
                            td,
                        )
                        if hist is not None and not hist.empty:
                            trading_days = len(hist)
                    except Exception:
                        pass
                    lookback += 1
                week_start = lookback_start.strftime("%Y-%m-%d")
                for ticker in weekly_pool:
                    try:
                        trd = Trading(source="vci", symbol=ticker)
                        df = trd.foreign_trade(start=week_start, end=td)
                        if df is None or df.empty:
                            continue
                        total_net = 0.0
                        for _, row in df.iterrows():
                            bv = float(row.get("fr_buy_value_matched", 0) or 0)
                            sv = float(row.get("fr_sell_value_matched", 0) or 0)
                            total_net += bv - sv
                        weekly_inflow_map[ticker] = round(total_net / 1e9, 1)
                    except Exception:
                        pass
        except Exception as e:
            pass

    weekly_candidates = sorted(
        [t for t, v in weekly_inflow_map.items() if v > 0],
        key=lambda t: weekly_inflow_map.get(t, 0),
        reverse=True,
    )

    wl_signals = (
        ai_data.get("watchlist_signals") or data.get("watchlist_signals", {}) or {}
    )

    # Fetch signals synchronously for missing tickers
    target_date = data.get("snapshot", {}).get("date")
    ticker_signals = dict(wl_signals)
    all_candidates = set(
        [item["ticker"] for item in daily_candidates] + weekly_candidates
    )
    for ticker in all_candidates:
        if ticker not in ticker_signals:
            try:
                from app.vnstock_core.core import fetch_technical_signals

                sig = fetch_technical_signals(
                    ticker, lookback_days=80, target_date=target_date
                )
                if sig and sig.get("rsi14") is not None:
                    ticker_signals[ticker] = sig
            except Exception:
                pass

    def _signal_desc(ema, rsi):
        if ema == 1:
            return "✅ Phá kháng cự · EMA9 > EMA26"
        elif ema == -1:
            return "❌ Cắt xuống EMA9"
        elif rsi >= 60:
            return f"📈 Momentum tăng · RSI {rsi}"
        elif rsi < 40:
            return f"📉 Bán quá mức · RSI {rsi}"
        else:
            return f"⚖️ Trung lập · RSI {rsi}"

    # Section 4 — Danh sách theo dõi ngày: filter EMA9>EMA26 + RSI<80 first, then top 5 by inflow, ranked by score
    daily_filtered = []
    for item in daily_candidates:
        ticker = item["ticker"]
        sig = ticker_signals.get(ticker, {})
        rsi_raw = sig.get("rsi14")
        rsi = int(rsi_raw) if rsi_raw is not None else 50
        ema = sig.get("ema_cross") or 0
        if ema != 1 or rsi >= 80:
            continue
        score = min(100, max(0, int((rsi - 30) * 1.5)))
        label = f"EMA tăng · RSI {rsi}"
        inflow_val = item.get("value_bil", 0) or 0
        daily_filtered.append((ticker, label, score, inflow_val))

    daily_filtered.sort(key=lambda x: x[3], reverse=True)
    daily_filtered = daily_filtered[:5]
    daily_filtered.sort(key=lambda x: x[2], reverse=True)

    if daily_filtered:
        lines.append("📋 **DANH SÁCH THEO DÕI – 5 MÃ**")
        for ticker, label, score, _ in daily_filtered:
            lines.append(f"  • {ticker} — {label} — Điểm {score}")
        lines.append("")

    # Section 5 — Danh mục theo dõi tuần: filter first, then top 5 by 7-day inflow, ranked by score
    weekly_filtered = []
    for ticker in weekly_candidates:
        sig = ticker_signals.get(ticker, {})
        rsi_raw = sig.get("rsi14")
        rsi = int(rsi_raw) if rsi_raw is not None else 50
        ema = sig.get("ema_cross") or 0
        if ema != 1 or rsi >= 80:
            continue
        score = min(100, max(0, int((rsi - 30) * 1.5)))
        inflow_val = weekly_inflow_map.get(ticker, 0)
        weekly_filtered.append(
            (ticker, ticker_sectors.get(ticker, "Khác"), score, inflow_val)
        )

    weekly_filtered.sort(key=lambda x: x[3], reverse=True)
    weekly_filtered = weekly_filtered[:5]
    weekly_filtered.sort(key=lambda x: x[2], reverse=True)

    if weekly_filtered:
        lines.append("📅 **DANH MỤC THEO DÕI TUẦN**")
        lines.append("Top 5 inflow tuần · EMA9 > EMA26")
        for ticker, sector, score, _ in weekly_filtered:
            lines.append(f"  • {ticker} — {sector} · Điểm {score}")
        lines.append("")

    # 4. Risk Radar
    if ai_data and ai_data.get("risk_radar"):
        lines.append("⚠️ **Rủi ro cần theo dõi**")
        for risk in ai_data["risk_radar"]:
            if isinstance(risk, dict):
                lvl = _level_label(risk.get("level", "Thấp"))
                lines.append(f"- {lvl} {risk.get('text', risk)}")
            else:
                lines.append(f"- {risk}")
        lines.append("")

    # 5. Key Insights (AI news) - Top 5 with URLs
    news_items = (ai_data or {}).get("ai_news") or data.get("news", [])
    if news_items:
        lines.append("📰 **Tin tức nổi bật**")
        for i, item in enumerate(news_items[:5], 1):
            content = item.get("ai_summary") or item.get("impact_base", "") or ""
            tag_emoji = _tag_emoji(item.get("tag", "Neutral"))
            lvl_emoji = _level_label(item.get("level", "Thấp"))
            tickers = item.get("tickers", [])
            tick_str = f" `{'` `'.join(tickers)}`" if tickers else ""
            url = item.get("url", "")

            # Headline
            headline = item.get("headline", "")
            if url:
                lines.append(f"{i}. {tag_emoji}**{headline}**{tick_str} {lvl_emoji}")
                lines.append(f"   🔗 {url}")
            else:
                lines.append(f"{i}. {tag_emoji}**{headline}**{tick_str} {lvl_emoji}")

            # Short description if available
            if content and content != headline:
                desc_short = content[:120] + "..." if len(content) > 120 else content
                lines.append(f"   └ {desc_short}")
            lines.append("")

    # 6b. Portfolio Actions
    port_actions = (ai_data or {}).get("portfolio_actions", [])
    if port_actions:
        lines.append("💼 **Danh mục — Actions hôm nay**")
        tag_icons = {
            "Cắt lỗ": "🔴",
            "Giảm tỉ trọng": "🟠",
            "Theo dõi chặt": "🟡",
            "Giữ nguyên": "⚪",
            "Giữ/Thêm": "🟢",
        }
        for p in port_actions:
            icon = tag_icons.get(p.get("tag", ""), "•")
            pnl = p.get("pnl_pct")
            pnl_str = f" · {pnl:+.1f}%" if pnl is not None else ""
            rsi = p.get("rsi")
            rsi_str = f" · RSI {rsi:.0f}" if rsi else ""
            lines.append(f"{icon} {p['symbol']} [{p.get('tag', '')}]{pnl_str}{rsi_str}")
            lines.append(f"  └ {p['action']}")
        lines.append("")

    # 7. Upcoming Catalysts
    catalysts = data.get("upcoming_catalysts", [])
    if catalysts:
        lines.append("📅 **Sự kiện sắp tới**")
        for c in catalysts:
            sym = c.get("symbol", "")
            date = c.get("date", "")
            title = c.get("title", "")
            lines.append(f"- **{date}** `{sym}` — {title}")
        lines.append("")

    return "\n".join(lines).strip()
