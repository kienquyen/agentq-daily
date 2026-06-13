# features.portfolio/parser.py
# -*- coding: utf-8 -*-

from typing import List, Dict, Any


def _parse_lines(text: str) -> List[List[str]]:
    lines = [x.strip() for x in (text or "").splitlines() if x.strip()]
    out = []
    for ln in lines:
        parts = [p.strip() for p in ln.split(",")]
        out.append(parts)
    return out

def parse_portfolio_modal_input(
    stocks_text: str,
    crypto_text: str,
    cash_vnd: str,
    cash_usdt: str,
    risk_text: str,
):
    rows = []

    def parse_block(text: str, asset_type: str, cost_ccy: str):
        text = (text or "").strip()
        if not text:
            return
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) != 3:
                raise ValueError(f"Line '{ln}' must be: SYMBOL,qty,avg_cost")
            sym, qty, avg = parts
            rows.append(
                dict(
                    asset_type=asset_type,
                    symbol=sym.upper(),
                    qty=float(qty),
                    avg_cost=float(avg),
                    cost_ccy=cost_ccy,
                )
            )

    try:
        parse_block(stocks_text, "VN", "VND")
        parse_block(crypto_text, "CRYPTO", "USDT")

        if (cash_vnd or "").strip():
            rows.append(dict(asset_type="CASH", symbol="VND", qty=float(cash_vnd), avg_cost=1.0, cost_ccy="VND"))
        if (cash_usdt or "").strip():
            rows.append(dict(asset_type="CASH", symbol="USDT", qty=float(cash_usdt), avg_cost=1.0, cost_ccy="USDT"))

        risk = 7
        try:
            t = int((risk_text or "7").strip())
            if 1 <= t <= 10:
                risk = t
        except Exception:
            risk = 7

        if not rows:
            return False, "Portfolio is empty."
        return True, {"rows": rows, "risk": risk}

    except Exception as e:
        return False, str(e)


def parse_5fields_inputs(stock_text: str, crypto_text: str, vnd_cash: str, usdt_cash: str) -> List[Dict[str, Any]]:
    """
    Field 1: stock_text lines: TICKER,Qty,AvgCost
    Field 2: crypto_text lines: SYMBOL,Qty,AvgCost
    Field 3: vnd_cash: number
    Field 4: usdt_cash: number
    """
    rows: List[Dict[str, Any]] = []

    # ---- STOCK (VN) ----
    for parts in _parse_lines(stock_text):
        if len(parts) < 3:
            continue
        sym, qty, avg = parts[0].upper(), parts[1], parts[2]
        try:
            rows.append(
                {
                    "asset_type": "VN",
                    "symbol": sym,
                    "qty": float(qty),
                    "avg_cost": float(avg),
                    "cost_ccy": "VND",
                }
            )
        except Exception:
            continue

    # ---- CRYPTO ----
    for parts in _parse_lines(crypto_text):
        if len(parts) < 3:
            continue
        sym, qty, avg = parts[0].upper(), parts[1], parts[2]
        try:
            rows.append(
                {
                    "asset_type": "CRYPTO",
                    "symbol": sym,
                    "qty": float(qty),
                    "avg_cost": float(avg),
                    "cost_ccy": "USDT",
                }
            )
        except Exception:
            continue

    # ---- CASH VND ----
    try:
        vnd = float((vnd_cash or "0").replace(",", "").strip())
        if vnd > 0:
            rows.append(
                {
                    "asset_type": "CASH",
                    "symbol": "VND",
                    "qty": vnd,
                    "avg_cost": 1.0,
                    "cost_ccy": "VND",
                }
            )
    except Exception:
        pass

    # ---- CASH USDT ----
    try:
        usdt = float((usdt_cash or "0").replace(",", "").strip())
        if usdt > 0:
            rows.append(
                {
                    "asset_type": "CASH",
                    "symbol": "USDT",
                    "qty": usdt,
                    "avg_cost": 1.0,
                    "cost_ccy": "USDT",
                }
            )
    except Exception:
        pass

    return rows