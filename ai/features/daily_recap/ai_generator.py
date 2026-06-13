"""
Daily Recap — AI Generator (Step 1 upgrade)

Consumes enriched data (watchlist TA signals, USD/VND, upcoming catalysts)
and produces narrative output for the formatter.
"""

from typing import Any, Dict, List, Optional
import asyncio
import pandas as pd

try:
    from features.ai.gemini import GeminiService
except ImportError:
    GeminiService = None

from .market_regime import run_regime_from_recap

# ─── Playbook builder ─────────────────────────────────────────────────────────


def _build_playbook(
    regime: str,
    flow: Dict,
    watchlist_signals: Dict,
    snapshot: Dict,
) -> List[Dict]:
    """Build actionable playbook items based on regime + TA signals."""
    items = []
    dist = snapshot.get("dist_days", 0)

    if regime == "bear_risk":
        items.append(
            {
                "priority": "!",
                "tag": "Hạ margin",
                "action": f"Hạ margin về 0% — bear_risk · dist {dist} ngày",
                "condition": "Tái xem xét khi regime chuyển sang ranging hoặc recovery",
            }
        )
    elif regime == "ranging":
        items.append(
            {
                "priority": "1",
                "tag": "Thận trọng",
                "action": "Giữ margin thấp 30-50% — thị trường tích lũy/dao động",
                "condition": "Ưu tiên mean-reversion, tránh đuổi giá",
            }
        )

    # Bearish watchlist symbols → cắt lỗ / giảm tỉ trọng
    for ticker, sig in watchlist_signals.items():
        if (
            sig.get("ema_cross") == -1
            and sig.get("rsi14") is not None
            and sig["rsi14"] < 35
        ):
            items.append(
                {
                    "priority": str(len(items) + 1),
                    "tag": "Cắt lỗ" if regime == "bear_risk" else "Giảm tỉ trọng",
                    "action": f"Xem xét giảm {ticker} — EMA bearish · RSI {sig['rsi14']:.0f}",
                    "condition": f"EMA9 < EMA26 · RSI {sig['rsi14']:.0f}",
                }
            )

    # Bullish watchlist symbols in inflow → theo dõi/mua
    inflow_tickers = {t for g in flow.get("inflow", []) for t in g.get("tickers", [])}
    for ticker, sig in watchlist_signals.items():
        if sig.get("ema_cross") == 1 and ticker in inflow_tickers:
            rsi = sig.get("rsi14")
            if rsi and 40 < rsi < 70:
                items.append(
                    {
                        "priority": str(len(items) + 1),
                        "tag": "Theo dõi"
                        if regime not in ("bull_trending", "recovery")
                        else "Mua",
                        "action": f"Chuẩn bị vị thế {ticker} — EMA bullish · dòng tiền vào",
                        "condition": f"Vol > 1.5x avg · Đóng > Mở · RSI {rsi:.0f}",
                    }
                )

    # Default hold if no signals
    if len(items) <= 1:
        items.append(
            {
                "priority": str(len(items) + 1),
                "tag": "Giữ nguyên",
                "action": "Duy trì vị thế hiện tại, không mở mới",
                "condition": "Chờ xác nhận trend trước khi hành động",
            }
        )

    return items[:6]


# ─── Risk radar ───────────────────────────────────────────────────────────────


def _build_risk_radar(snapshot: Dict, usd_vnd: float = None) -> List[Dict]:
    items = []
    dist = snapshot.get("dist_days", 0)
    foreign = snapshot.get("foreign_flow_bil", 0)
    vs_ma50 = snapshot.get("vs_ma50_pct", 0)

    # Distribution days scale: 0-2=Sạch, 3-4=Thận trọng, 5=Elevated, 6-7=High Risk, ≥8=Critical
    if dist >= 8:
        items.append(
            {
                "text": f"⚠️ Distribution {dist} ngày — NGUY HIỂM (Critical)",
                "level": "Cao",
            }
        )
    elif dist >= 6:
        items.append(
            {
                "text": f"⚠️ Distribution {dist} ngày — Rủi ro cao (High Risk)",
                "level": "Cao",
            }
        )
    elif dist >= 5:
        items.append(
            {
                "text": f"⚠️ Distribution {dist} ngày — Nâng cao (Elevated)",
                "level": "Cao",
            }
        )
    elif dist >= 3:
        items.append(
            {
                "text": f"Distribution {dist} ngày — Thận trọng (Caution)",
                "level": "Trung bình",
            }
        )
    # 0-2: Thị trường sạch - no warning

    if foreign < -300:
        items.append({"text": f"Ngoại bán ròng mạnh: {foreign:.0f}B", "level": "Cao"})
    elif foreign < -100:
        items.append({"text": f"Ngoại bán ròng: {foreign:.0f}B", "level": "Trung bình"})

    if vs_ma50 < -5:
        items.append(
            {
                "text": f"VNIndex cách MA50: {vs_ma50:+.1f}% — oversold tiềm năng",
                "level": "Trung bình",
            }
        )

    if usd_vnd and usd_vnd > 25400:
        items.append(
            {"text": f"USD/VND {usd_vnd:,.0f} — áp lực tỉ giá", "level": "Trung bình"}
        )

    if not items:
        items.append({"text": "Không có cảnh báo rủi ro nổi bật", "level": "Thấp"})

    return items


# ─── Portfolio actions ────────────────────────────────────────────────────────


async def _build_portfolio_actions(
    regime: str,
    holdings: List[Dict],
    prices: Dict[str, float],
    watchlist_signals: Dict,
    target_date: str = None,
) -> List[Dict]:
    """
    For each VN holding, generate a specific action based on:
      - regime (Risk-Off / Neutral / Risk-On)
      - PnL% vs avg_cost
      - EMA cross signal and RSI
    Returns list of {symbol, qty, avg_cost, curr_price, pnl_pct, action, tag, note}.
    """
    actions = []

    # ─── Data fetchers for non-scan symbols or historical ─────────────────────
    from app.vnstock_core.core import fetch_ohlcv, fetch_technical_signals

    for h in holdings:
        if (h.get("asset_type") or "").upper().strip() != "VN":
            continue
        sym = (h.get("symbol") or "").upper().strip()
        if not sym:
            continue

        avg_cost = float(h.get("avg_cost") or 0)
        qty = float(h.get("qty") or 0)
        curr_price = prices.get(sym, 0.0)

        # Fallback for historical or non-scan tickers
        if curr_price <= 0 and target_date:
            try:
                df = fetch_ohlcv(sym, start=target_date, end=target_date)
                if not df.empty:
                    curr_price = float(df.iloc[-1]["close"])
            except Exception:
                pass

        # Last resort: current price (not ideal for historical recap)
        if curr_price <= 0:
            try:
                from app.vnstock_core.core import fetch_last_prices

                curr_price = fetch_last_prices([sym]).get(sym, 0.0)
            except Exception:
                pass

        # ── Unit normalization ──────────────────────────────────────────────
        # avg_cost is always entered by user in full VND (e.g., 90,000 not 90).
        # curr_price comes from: scan (full VND, data_fetcher auto-scales),
        #   fetch_ohlcv (nghìn đồng, e.g., 26.75), or fetch_last_prices (full VND, _scale_vnd).
        # We normalize curr_price to full VND: if < 1000, it's in nghìn đồng → scale up.
        import logging as _lg

        _lg.getLogger(__name__).info(
            f"[PnL DEBUG] {sym}: raw_curr={curr_price:.4f}, avg_cost={avg_cost:.2f}"
        )
        if curr_price > 0 and curr_price < 1000 and avg_cost >= 1000:
            curr_price *= 1000
            _lg.getLogger(__name__).info(
                f"[PnL DEBUG] {sym}: scaled curr_price → {curr_price:.2f}"
            )

        pnl_pct = (
            ((curr_price / avg_cost) - 1) * 100
            if avg_cost > 0 and curr_price > 0
            else None
        )
        _lg.getLogger(__name__).warning(f"[PnL DEBUG] {sym}: pnl_pct={pnl_pct}")

        # TA signal — prefer from watchlist (if current date), else fetch historical
        sig = watchlist_signals.get(sym)
        if not sig:
            try:
                # For historical, we need a range ending at target_date for EMA/RSI
                sig = await asyncio.to_thread(
                    fetch_technical_signals, sym, target_date=target_date
                )
            except Exception:
                sig = {}

        ema_cross = sig.get("ema_cross") if sig else None
        rsi = sig.get("rsi14") if sig else None

        # Action decision (Aligned with AgentQ labels)
        pnl_str = f"PnL {pnl_pct:+.1f}%" if pnl_pct is not None else "PnL N/A"

        # Decide regime label for logic
        mkt_bias = "Neutral"
        if regime in ("bull_trending", "recovery"):
            mkt_bias = "Risk-On"
        if regime == "bear_risk":
            mkt_bias = "Risk-Off"

        # Default tag/action
        tag, action = "Giữ nguyên", f"Giữ {sym} · {pnl_str}"

        if mkt_bias == "Risk-Off":
            if pnl_pct is not None and pnl_pct < -5:
                tag, action = (
                    "Cắt lỗ",
                    f"Cắt {sym} — {pnl_str} vượt ngưỡng stop -5% (Risk-Off)",
                )
            elif ema_cross == -1 and rsi is not None and rsi < 40:
                tag, action = (
                    "Giảm tỉ trọng",
                    f"Giảm {sym} — RSI {rsi:.0f} & EMA bearish",
                )
            elif ema_cross == -1:
                tag, action = (
                    "Theo dõi chặt",
                    f"Theo dõi {sym} — EMA bearish ({pnl_str})",
                )
        elif mkt_bias == "Risk-On":
            if ema_cross == 1 and rsi is not None and 40 < rsi < 70:
                tag, action = (
                    "Giữ/Thêm",
                    f"Gia tăng {sym} — EMA bullish (RSI {rsi:.0f})",
                )
            else:
                tag, action = "Giữ nguyên", f"Giữ {sym} ({pnl_str})"
        else:  # Neutral
            if pnl_pct is not None and pnl_pct < -7:
                tag, action = "Cắt lỗ", f"Cắt {sym} — {pnl_str} vượt ngưỡng stop"
            elif ema_cross == 1 and rsi is not None and 45 < rsi < 65:
                tag, action = "Giữ nguyên", f"Giữ {sym} — EMA bullish ({pnl_str})"
            else:
                tag, action = "Giữ nguyên", f"Giữ {sym} ({pnl_str}) · RSI {rsi:.0f}"

        actions.append(
            {
                "symbol": sym,
                "qty": qty,
                "avg_cost": avg_cost,
                "curr_price": curr_price,
                "pnl_pct": pnl_pct,
                "tag": tag,
                "action": action,
                "ema_cross": ema_cross,
                "rsi": rsi,
            }
        )

    return actions


def snapshot_date_too_old(target_date: str) -> bool:
    try:
        dt = pd.to_datetime(target_date).date()
        return dt < pd.Timestamp.now().date()
    except:
        return False


# ─── Main generator ───────────────────────────────────────────────────────────


class AICapacityPlanner:
    def __init__(self, ai_service=None):
        self.ai = ai_service or (GeminiService() if GeminiService else None)

    async def generate_recap(
        self,
        data: Dict[str, Any],
        include_ai_news: bool,
        user_id: int = None,
        target_date: str = None,
    ) -> Dict[str, Any]:
        snapshot = data.get("snapshot", {})
        flow = data.get("flow", {})
        watchlist_signals = data.get("watchlist_signals", {})
        prices = data.get("prices", {})
        usd_vnd = data.get("usd_vnd")

        # Regime — run in thread to avoid blocking the Discord event loop.
        # compute_regime_features() fetches 700 days of OHLCV (blocking I/O).
        feat, regime, score, bd = await asyncio.to_thread(
            run_regime_from_recap, data, target_date
        )
        take = "Thị trường " + label_vn_regime(regime)

        # Playbook
        playbook = _build_playbook(regime, flow, watchlist_signals, snapshot)

        # Risk radar
        risk_radar = _build_risk_radar(snapshot, usd_vnd)

        # Portfolio actions + exposure (per-holding, requires user_id)
        portfolio_actions: List[Dict] = []
        exposure_pct: int = 45  # default fallback
        if user_id:
            try:
                from features.portfolio.storage import load_portfolio_state
                from features.portfolio.price_vn import (
                    fetch_vn_last_prices as fetch_vn_prices,
                )

                state = load_portfolio_state(user_id)
                holdings = state.get("holdings", [])

                # Compute VN equity exposure % = VN market value / Total portfolio NAV
                vn_holdings = [
                    h for h in holdings if (h.get("asset_type") or "").upper() == "VN"
                ]
                if vn_holdings:
                    vn_syms = [h["symbol"] for h in vn_holdings if h.get("symbol")]
                    live_px = {**prices}  # start with scan prices
                    missing = [
                        s for s in vn_syms if s not in live_px or live_px[s] <= 0
                    ]
                    if missing:
                        try:
                            extra = await asyncio.to_thread(fetch_vn_prices, missing)
                            live_px.update(extra)
                        except Exception:
                            pass

                    # Numerator: VN stock positions at live market price
                    # Fall back to avg_cost only if live price truly missing (logged)
                    vn_mkt_val = 0.0
                    for h in vn_holdings:
                        sym = h.get("symbol")
                        if not sym:
                            continue
                        px = live_px.get(sym)
                        if not px or px <= 0:
                            px = float(h.get("avg_cost", 0))
                        vn_mkt_val += float(h.get("qty", 0)) * px

                    # Denominator: Total portfolio NAV
                    #   = VN market value
                    #   + Cash (qty IS the VND balance for CASH holdings)
                    #   + Other non-VN non-CASH assets at cost basis (crypto, gold)
                    cash_vnd = sum(
                        float(h.get("qty", 0))
                        for h in holdings
                        if (h.get("asset_type") or "").upper() == "CASH"
                        and (h.get("cost_ccy") or "VND").upper() == "VND"
                    )
                    other_cost = sum(
                        float(h.get("qty", 0)) * float(h.get("avg_cost", 0))
                        for h in holdings
                        if (h.get("asset_type") or "").upper() not in ("VN", "CASH")
                    )
                    total_nav = vn_mkt_val + cash_vnd + other_cost
                    if total_nav > 0:
                        exposure_pct = min(
                            100, int(round(vn_mkt_val / total_nav * 100))
                        )

                portfolio_actions = await _build_portfolio_actions(
                    regime, holdings, prices, watchlist_signals, target_date
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(
                    f"Error building portfolio actions: {e}", exc_info=True
                )

        # Build Interpretation (Narrative)
        days = snapshot.get("dist_days", 0)
        vni_chg = snapshot.get("change_pct", 0.0)

        interp = f"VNIndex {'tăng' if vni_chg >= 0 else 'giảm'} {abs(vni_chg):.1f}% trong phiên hôm nay. "
        if days >= 4:
            interp += (
                f"Số ngày phân phối (Distribution) hiện là {days}, mức rủi ro CAO. "
            )
        elif days >= 2:
            interp += f"Thị trường có {days} ngày phân phối, cần thận trọng quan sát. "
        else:
            interp += "Áp lực cung chưa đáng kể. "

        if usd_vnd and usd_vnd > 25400:
            interp += f"Tỉ giá USD/VND ({usd_vnd:,.0f}) đang gây áp lực lên tâm lý khối ngoại. "

        # AI news analysis
        ai_news = []
        if include_ai_news and self.ai and self.ai.is_ready() and data.get("news"):
            symbols = list(
                {
                    t
                    for group in ("inflow", "outflow")
                    for item in flow.get(group, [])
                    for t in item.get("tickers", [])
                }
            )[:10]

            news_items = data["news"][:5]
            news_text = "\n".join(
                f"- {n['headline']}: {n['impact_base']}" for n in news_items
            )
            prompt = (
                "Bạn là chuyên gia phân tích chứng khoán Việt Nam. Phân tích các tin tức sau.\n"
                "YÊU CẦU:\n"
                "1. Tóm tắt ý chính và tác động tới thị trường/mã liên quan (25-40 từ).\n"
                "2. Xác định Sentiment: 'Bullish', 'Bearish', 'Neutral'.\n"
                "3. Xác định mức độ: 'Cao', 'Trung bình', 'Thấp'.\n"
                f"4. Ưu tiên mã: {', '.join(symbols) if symbols else 'Toàn thị trường'}.\n\n"
                f"Tin tức:\n{news_text}\n\n"
                "Trả JSON list:\n"
                '[{"headline":"...","ai_summary":"...","tag":"Bullish|Bearish|Neutral","level":"Cao|Trung bình|Thấp","tickers":["VCB"]}]'
            )
            ai_res = await self.ai.generate_json(prompt)
            if ai_res and isinstance(ai_res, list):
                ai_news = ai_res
            else:
                for item in news_items[:5]:
                    ai_news.append(
                        {
                            "headline": item.get("headline", ""),
                            "ai_summary": item.get("impact_base", "")[:100] + "..."
                            if item.get("impact_base")
                            else "",
                            "tag": "Neutral",
                            "level": "Thấp",
                            "tickers": [],
                            "url": item.get("url", ""),
                        }
                    )
        else:
            for item in data.get("news", [])[:5]:
                ai_news.append(
                    {
                        "headline": item.get("headline", ""),
                        "ai_summary": item.get("impact_base", "")
                        or item.get("ai_summary", ""),
                        "tag": item.get("tag", "Neutral"),
                        "level": "Thấp",
                        "tickers": [],
                        "url": item.get("url", ""),
                    }
                )

        return {
            "regime": regime,
            "regime_score": score,
            "regime_breakdown": bd,
            "regime_takeaway": take,
            "interpretation": interp,
            "playbook": playbook,
            "risk_radar": risk_radar,
            "ai_news": ai_news,
            "watchlist_signals": watchlist_signals,
            "portfolio_actions": portfolio_actions,
            "exposure_pct": exposure_pct,
            # Foreign flow data from feat
            "foreign_net_1d": feat.get("foreign_net_1d"),
            "foreign_net_10d": feat.get("foreign_net_10d"),
            "flow_streak": feat.get("flow_streak"),
            "flow_acceleration": feat.get("flow_acceleration"),
            "foreign_net_pct_rank": feat.get("foreign_net_pct_rank"),
        }


def label_vn_regime(label: str) -> str:
    mapping = {
        "bull_trending": "xu hướng tăng tích cực",
        "recovery": "đang hồi phục",
        "ranging": "đi ngang tích lũy",
        "bear_risk": "rủi ro điều chỉnh cao",
        "unknown": "không xác định",
    }
    return mapping.get(label, label)
