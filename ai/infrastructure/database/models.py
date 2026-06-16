"""
Database Models and Connection Pool - Infrastructure Layer
Optimized for 100k users with connection pooling.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

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
    Pool,
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.pool import QueuePool

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    from config.settings import TASK3_DB_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_TIMEOUT
except ImportError:
    TASK3_DB_URL = os.getenv("TASK3_DB_URL", "sqlite:///./agentq.db")
    DB_POOL_SIZE = 20
    DB_MAX_OVERFLOW = 40
    DB_POOL_TIMEOUT = 30

Base = declarative_base()

# ===== Connection Pool Configuration =====
engine = create_engine(
    TASK3_DB_URL,
    poolclass=QueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db_session() -> Session:
    """Get a database session from the pool."""
    return SessionLocal()

def now_utc():
    return datetime.now(timezone.utc)

# ===== ORM MODELS =====

class Portfolio(Base):
    __tablename__ = "t3_portfolios"

    user_id = Column(BigInteger, primary_key=True, index=True)
    base_currency = Column(String(8), default="VND")
    risk_score = Column(Integer, default=7)

    max_pos = Column(Float, default=0.20)
    crypto_cap = Column(Float, default=0.30)
    min_cash = Column(Float, default=0.10)

    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc)

    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    snapshots = relationship("Snapshot", back_populates="portfolio", cascade="all, delete-orphan")


class Holding(Base):
    __tablename__ = "t3_holdings"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("t3_portfolios.user_id"), index=True, nullable=False)
    asset_type = Column(String(10))
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

    regime_state = Column(String(32), default="Neutral")
    flags_json = Column(Text, nullable=True)

    portfolio = relationship("Portfolio", back_populates="snapshots")


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
