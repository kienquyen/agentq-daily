# features.portfolio/storage.py
# -*- coding: utf-8 -*-

import json
from typing import Dict, Any, List

from features.portfolio.db import SessionLocal, Portfolio, Holding, Snapshot, now_utc

# Locked defaults (per your requirement: "Lock Task3 defaults")
LOCKED_DEFAULTS = dict(max_pos=0.20, crypto_cap=0.30, min_cash=0.10)


def get_or_create_portfolio(user_id: int) -> Portfolio:
    db = SessionLocal()
    try:
        p = db.query(Portfolio).filter(Portfolio.user_id == user_id).one_or_none()
        if not p:
            p = Portfolio(
                user_id=user_id,
                base_currency="VND",
                risk_score=7,
                **LOCKED_DEFAULTS,
            )
            db.add(p)
            db.commit()
            db.refresh(p)
        return p
    finally:
        db.close()


def has_saved_portfolio(user_id: int) -> bool:
    db = SessionLocal()
    try:
        return db.query(Holding).filter(Holding.user_id == user_id).count() > 0
    finally:
        db.close()


def replace_holdings(
    user_id: int, base: str, risk: int, holdings_rows: List[Dict[str, Any]]
) -> None:
    """
    Replace holdings for a user (multi-user safe).
    """
    base = (base or "VND").strip().upper()
    risk = int(risk or 7)

    db = SessionLocal()
    try:
        p = db.query(Portfolio).filter(Portfolio.user_id == user_id).one_or_none()
        if not p:
            p = Portfolio(
                user_id=user_id,
                base_currency="VND",
                risk_score=7,
                **LOCKED_DEFAULTS,
            )
            db.add(p)
            db.flush()

        # Update portfolio meta
        p.base_currency = base
        p.risk_score = risk
        p.max_pos = LOCKED_DEFAULTS["max_pos"]
        p.crypto_cap = LOCKED_DEFAULTS["crypto_cap"]
        p.min_cash = LOCKED_DEFAULTS["min_cash"]
        p.updated_at = now_utc()

        # Replace holdings
        db.query(Holding).filter(Holding.user_id == user_id).delete()

        for r in holdings_rows:
            db.add(
                Holding(
                    user_id=user_id,
                    asset_type=r["asset_type"],
                    symbol=r["symbol"],
                    qty=float(r["qty"]),
                    avg_cost=float(r.get("avg_cost", 0.0)),
                    cost_ccy=r.get("cost_ccy", "VND"),
                    updated_at=now_utc(),
                )
            )

        db.commit()
    finally:
        db.close()


def load_portfolio_state(user_id: int) -> Dict[str, Any]:
    """
    Return portfolio + holdings in a single dict.
    """
    db = SessionLocal()
    try:
        p = get_or_create_portfolio(user_id)
        hs = db.query(Holding).filter(Holding.user_id == user_id).all()
        return {
            "base": p.base_currency,
            "risk": p.risk_score,
            "max_pos": p.max_pos,
            "crypto_cap": p.crypto_cap,
            "min_cash": p.min_cash,
            "holdings": [
                dict(
                    asset_type=h.asset_type,
                    symbol=h.symbol,
                    qty=h.qty,
                    avg_cost=h.avg_cost,
                    cost_ccy=h.cost_ccy,
                )
                for h in hs
            ],
        }
    finally:
        db.close()


def append_snapshot(user_id: int, payload: Dict[str, Any]) -> None:
    db = SessionLocal()
    try:
        s = Snapshot(
            user_id=user_id,
            ts=now_utc(),
            nav_base=float(payload["nav_base"]),
            nav_vn=float(payload["nav_vn"]),
            nav_crypto=float(payload["nav_crypto"]),
            nav_cash=float(payload["nav_cash"]),
            w_vn=float(payload["w_vn"]),
            w_crypto=float(payload["w_crypto"]),
            w_cash=float(payload["w_cash"]),
            pnl_unrealized=float(payload["pnl_unrealized"]),
            regime_state=str(payload.get("regime_state", "Neutral")),
            flags_json=json.dumps(payload.get("flags", {}), ensure_ascii=False),
            beta_btc_3m=payload.get("beta_btc_3m"),
            beta_btc_6m=payload.get("beta_btc_6m"),
            beta_vni_6m=payload.get("beta_vni_6m"),
            beta_vni_12m=payload.get("beta_vni_12m"),
            sharpe_30d=payload.get("sharpe_30d"),
            sharpe_60d=payload.get("sharpe_60d"),
            sharpe_90d=payload.get("sharpe_90d"),
        )
        db.add(s)
        db.commit()
    finally:
        db.close()


def load_snapshots_nav(user_id: int, limit: int = 800) -> List[Dict[str, Any]]:
    """
    Minimal snapshot series for performance metrics.
    """
    db = SessionLocal()
    try:
        rows = (
            db.query(Snapshot)
            .filter(Snapshot.user_id == user_id)
            .order_by(Snapshot.ts.asc())
            .limit(limit)
            .all()
        )
        return [{"ts": r.ts, "nav_base": r.nav_base} for r in rows]
    finally:
        db.close()


def serialize_holdings_to_modal(rows: List[Dict[str, Any]]) -> tuple:
    """
    Serialize holdings rows to modal text format.
    Returns (stocks_text, crypto_text, cash_vnd, cash_usdt).
    """
    stock_lines = []
    crypto_lines = []
    cash_vnd = ""
    cash_usdt = ""

    for r in rows:
        sym = r.get("symbol", "")
        qty = r.get("qty", 0)
        avg = r.get("avg_cost", 0)
        atype = r.get("asset_type", "")
        ccy = r.get("cost_ccy", "VND")

        if atype == "VN":
            stock_lines.append(f"{sym},{qty:.0f},{avg:.0f}")
        elif atype == "CRYPTO":
            crypto_lines.append(f"{sym},{qty},{avg}")
        elif atype == "CASH":
            if ccy == "VND":
                cash_vnd = f"{qty:.0f}"
            elif ccy == "USDT":
                cash_usdt = f"{qty}"

    return (
        "\n".join(stock_lines),
        "\n".join(crypto_lines),
        cash_vnd,
        cash_usdt,
    )


def add_holding(
    user_id: int,
    asset_type: str,
    symbol: str,
    qty: float,
    avg_cost: float,
    cost_ccy: str,
) -> bool:
    """
    Add or update a single holding. If symbol already exists for this user, update it.
    Returns True if successful.
    """
    db = SessionLocal()
    try:
        existing = (
            db.query(Holding)
            .filter(
                Holding.user_id == user_id,
                Holding.symbol == symbol.upper(),
                Holding.asset_type == asset_type,
            )
            .one_or_none()
        )
        if existing:
            existing.qty = float(qty)
            existing.avg_cost = float(avg_cost)
            existing.updated_at = now_utc()
        else:
            db.add(
                Holding(
                    user_id=user_id,
                    asset_type=asset_type,
                    symbol=symbol.upper(),
                    qty=float(qty),
                    avg_cost=float(avg_cost),
                    cost_ccy=cost_ccy,
                    updated_at=now_utc(),
                )
            )
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def update_holding(
    user_id: int, symbol: str, asset_type: str, qty: float, avg_cost: float
) -> bool:
    """
    Update quantity and avg_cost of an existing holding.
    Returns True if found and updated.
    """
    db = SessionLocal()
    try:
        h = (
            db.query(Holding)
            .filter(
                Holding.user_id == user_id,
                Holding.symbol == symbol.upper(),
                Holding.asset_type == asset_type,
            )
            .one_or_none()
        )
        if not h:
            return False
        h.qty = float(qty)
        h.avg_cost = float(avg_cost)
        h.updated_at = now_utc()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def delete_holding(user_id: int, symbol: str, asset_type: str) -> bool:
    """
    Delete a single holding.
    Returns True if found and deleted.
    """
    db = SessionLocal()
    try:
        count = (
            db.query(Holding)
            .filter(
                Holding.user_id == user_id,
                Holding.symbol == symbol.upper(),
                Holding.asset_type == asset_type,
            )
            .delete()
        )
        db.commit()
        return count > 0
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


# --- Backward-compatible alias (expected by older ui.py) ---
def get_latest_portfolio(user_id: int) -> Dict[str, Any]:
    """
    Older UI expects get_latest_portfolio() in storage.py.
    We alias to load_portfolio_state().
    """
    return load_portfolio_state(user_id)
