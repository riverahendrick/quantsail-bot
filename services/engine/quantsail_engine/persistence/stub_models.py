"""Stub database models for engine testing (temporary until API service is ready)."""


from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class Trade(Base):
    """Trade model stub."""

    __tablename__ = "trades"

    id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    status = Column(String, nullable=False)
    side = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    opened_at = Column(DateTime, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    pnl_usd = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)


class Order(Base):
    """Order model stub."""

    __tablename__ = "orders"

    id = Column(String, primary_key=True)
    trade_id = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    order_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    filled_price = Column(Float, nullable=True)
    filled_qty = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False)
    filled_at = Column(DateTime, nullable=True)


class Event(Base):
    """Event model stub."""

    __tablename__ = "events"

    seq = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String, nullable=False)
    level = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    public_safe = Column(String, nullable=False, default="false")
    timestamp = Column(DateTime, nullable=False)


class EquitySnapshot(Base):
    """Equity snapshot model stub."""

    __tablename__ = "equity_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equity_usd = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
