# features.portfolio/db.py
# -*- coding: utf-8 -*-

import os
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

# =========================
# ENV
# =========================
from config.settings import TASK3_DB_URL
DB_URL = TASK3_DB_URL
if not DB_URL:
    raise RuntimeError("Missing TASK3_DB_URL in .env")

# SQLAlchemy sync engine
engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def now_utc():
    return datetime.now(timezone.utc)


# =========================
# ORM MODELS (kept in db.py to match your file list)
# =========================
class Portfolio(Base):
    __tablename__ = "t3_portfolios"

    user_id = Column(BigInteger, primary_key=True, index=True)

    base_currency = Column(String(8), default="VND")
    risk_score = Column(Integer, default=7)

    # LOCK DEFAULTS (Task3 defaults locked)
    max_pos = Column(Float, default=0.20)      # 20%
    crypto_cap = Column(Float, default=0.30)   # 30%
    min_cash = Column(Float, default=0.10)     # 10%

    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc)

    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    snapshots = relationship("Snapshot", back_populates="portfolio", cascade="all, delete-orphan")


class Holding(Base):
    __tablename__ = "t3_holdings"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("t3_portfolios.user_id"), index=True, nullable=False)

    asset_type = Column(String(10))  # VN | CRYPTO | CASH
    symbol = Column(String(32))
    qty = Column(Float, default=0.0)
    avg_cost = Column(Float, default=0.0)
    cost_ccy = Column(String(8), default="VND")

    updated_at = Column(DateTime(timezone=True), default=now_utc)

    portfolio = relationship("Portfolio", back_populates="holdings")

    __table_args__ = (
        Index("ix_t3_holdings_user_symbol_type", "user_id", "symbol", "asset_type"),
    )


class Snapshot(Base):
    __tablename__ = "t3_snapshots"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("t3_portfolios.user_id"), index=True, nullable=False)
    ts = Column(DateTime(timezone=True), default=now_utc, index=True)

    nav_base = Column(Float, default=0.0)
    nav_vn = Column(Float, default=0.0)
    nav_crypto = Column(Float, default=0.0)
    nav_cash = Column(Float, default=0.0)

    w_vn = Column(Float, default=0.0)
    w_crypto = Column(Float, default=0.0)
    w_cash = Column(Float, default=0.0)

    pnl_unrealized = Column(Float, default=0.0)

    beta_btc_3m = Column(Float, nullable=True)
    beta_btc_6m = Column(Float, nullable=True)
    beta_vni_6m = Column(Float, nullable=True)
    beta_vni_12m = Column(Float, nullable=True)

    sharpe_30d = Column(Float, nullable=True)
    sharpe_60d = Column(Float, nullable=True)
    sharpe_90d = Column(Float, nullable=True)

    regime_state = Column(String(16), default="Neutral")
    flags_json = Column(Text, default="{}")

    portfolio = relationship("Portfolio", back_populates="snapshots")


def init_db() -> None:
    """
    Call once at bot start.
    """
    Base.metadata.create_all(bind=engine)
