# features.portfolio/analytics.py
# -*- coding: utf-8 -*-

from typing import Dict, Any

USDT_VND = float(__import__("os").getenv("USDT_VND", "25000"))  # v1 fixed FX


def compute_nav_pack(
    state: Dict[str, Any], vn_prices: Dict[str, float], cr_prices: Dict[str, float]
) -> Dict[str, Any]:
    base = state["base"].upper()
    holdings = state.get("holdings", [])

    nav_vn = 0.0
    nav_crypto = 0.0
    nav_cash = 0.0
    pnl = 0.0

    positions = []
    flags = {}

    for h in holdings:
        t = h["asset_type"]
        sym = h["symbol"].upper()
        qty = float(h["qty"])
        avg = float(h.get("avg_cost", 0.0))

        if t == "VN":
            px = float(vn_prices.get(sym, 0.0))
            if px <= 0:
                flags.setdefault("missing_vn_price", []).append(sym)
            mv = qty * px
            cost = qty * avg
            nav_vn += mv
            pnl += mv - cost
            positions.append({"type": "VN", "symbol": sym, "mv": mv, "pnl": mv - cost})

        elif t == "CRYPTO":
            px = float(cr_prices.get(sym, 0.0))  # USDT
            mv_usdt = qty * px
            cost_usdt = qty * avg

            mv = mv_usdt * USDT_VND if base == "VND" else mv_usdt
            cost = cost_usdt * USDT_VND if base == "VND" else cost_usdt

            nav_crypto += mv
            pnl += mv - cost
            positions.append(
                {"type": "CRYPTO", "symbol": sym, "mv": mv, "pnl": mv - cost}
            )

        elif t == "CASH":
            # qty is amount
            if sym == "VND":
                nav_cash += qty if base == "VND" else qty / USDT_VND
            elif sym == "USDT":
                nav_cash += qty * USDT_VND if base == "VND" else qty

    nav_total = nav_vn + nav_crypto + nav_cash

    w_vn = (nav_vn / nav_total) if nav_total else 0.0
    w_crypto = (nav_crypto / nav_total) if nav_total else 0.0
    w_cash = (nav_cash / nav_total) if nav_total else 0.0

    # concentration
    mvs = sorted([p["mv"] for p in positions], reverse=True)
    top1 = (mvs[0] / nav_total) if nav_total and mvs else 0.0
    top3 = (sum(mvs[:3]) / nav_total) if nav_total and len(mvs) >= 3 else 0.0

    if top1 > float(state["max_pos"]):
        flags["max_pos_breach"] = {"top1": top1, "max_pos": float(state["max_pos"])}

    if top3 > 0.60:
        flags["top3_concentration_high"] = {"top3": top3}

    if w_crypto > float(state["crypto_cap"]):
        flags["crypto_cap_breach"] = {
            "w_crypto": w_crypto,
            "cap": float(state["crypto_cap"]),
        }

    if w_cash < float(state["min_cash"]):
        flags["cash_buffer_low"] = {
            "w_cash": w_cash,
            "min_cash": float(state["min_cash"]),
        }

    return {
        "base": base,
        "nav_total": nav_total,
        "nav_vn": nav_vn,
        "nav_crypto": nav_crypto,
        "nav_cash": nav_cash,
        "w_vn": w_vn,
        "w_crypto": w_crypto,
        "w_cash": w_cash,
        "pnl_unrealized": pnl,
        "positions": positions,
        "concentration": {"top1": top1, "top3": top3},
        "flags": flags,
    }
