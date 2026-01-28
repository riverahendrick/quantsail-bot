"""Stub database models for engine testing (temporary until API service is ready)."""


import uuid
from datetime import datetime, timezone
from sqlalchemy import JSON, Column, DateTime, Float, Integer, LargeBinary, String, Boolean, Uuid
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class Trade(Base):
    """Trade model stub."""

    __tablename__ = "trades"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    symbol = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    status = Column(String, nullable=False)
    side = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    entry_qty = Column(Float, nullable=False)
    entry_notional_usd = Column(Float, nullable=False, default=0.0)
    opened_at = Column(DateTime, nullable=False)
    stop_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    trailing_enabled = Column(Boolean, nullable=False, default=False)
    trailing_offset = Column(Float, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    realized_pnl_usd = Column(Float, nullable=True)
    fees_paid_usd = Column(Float, nullable=True)
    slippage_est_usd = Column(Float, nullable=True)
    notes = Column(JSON, nullable=True)


class Order(Base):
    """Order model stub."""

    __tablename__ = "orders"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    trade_id = Column(Uuid, nullable=False)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    order_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    qty = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    filled_price = Column(Float, nullable=True)
    filled_qty = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False)
    filled_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    exchange_order_id = Column(String, nullable=True)
    idempotency_key = Column(String, nullable=True)


class Event(Base):
    """Event model stub."""

    __tablename__ = "events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    seq = Column(Integer, default=0) # SQLite stub doesn't strictly autoinc non-PK
    type = Column(String, nullable=False)
    level = Column(String, nullable=False)
    symbol = Column(String, nullable=True)
    trade_id = Column(Uuid, nullable=True)
    payload = Column(JSON, nullable=False)
    public_safe = Column(Boolean, nullable=False, default=False)
    ts = Column(DateTime, nullable=False)


class EquitySnapshot(Base):
    """Equity snapshot model stub."""

    __tablename__ = "equity_snapshots"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    equity_usd = Column(Float, nullable=False)
    cash_usd = Column(Float, nullable=False, default=0.0)
    unrealized_pnl_usd = Column(Float, nullable=False, default=0.0)
    realized_pnl_today_usd = Column(Float, nullable=False, default=0.0)
    open_positions = Column(Integer, nullable=False, default=0)
    meta = Column(JSON, nullable=True)
    ts = Column(DateTime, nullable=False)


class ExchangeKey(Base):
    """Exchange key model stub (encrypted)."""

    __tablename__ = "exchange_keys"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    exchange = Column(String, nullable=False)
    label = Column(String, nullable=True)
    ciphertext = Column(LargeBinary, nullable=False)
    nonce = Column(LargeBinary, nullable=False)
    key_version = Column(Integer, nullable=False, default=1)
    created_by = Column(Uuid, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, nullable=False, default=True)
    revoked_at = Column(DateTime, nullable=True)
