"""Stub database models for engine testing (matches API models)."""

import uuid
import datetime as dt
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Generic JSON for SQLite compatibility (SQLAlchemy handles mapping)
JSON_TYPE = sa.JSON().with_variant(JSONB, "postgresql")
NUMERIC_24_10 = sa.Numeric(24, 10)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class Trade(Base):
    """Trade model stub."""
    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    side: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    status: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    mode: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    opened_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    closed_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    entry_price: Mapped[Decimal] = mapped_column(NUMERIC_24_10, nullable=False)
    entry_qty: Mapped[Decimal] = mapped_column(NUMERIC_24_10, nullable=False)
    entry_notional_usd: Mapped[Decimal] = mapped_column(NUMERIC_24_10, nullable=False)

    stop_price: Mapped[Decimal | None] = mapped_column(NUMERIC_24_10, nullable=True)
    take_profit_price: Mapped[Decimal | None] = mapped_column(NUMERIC_24_10, nullable=True)
    trailing_enabled: Mapped[bool] = mapped_column(
        sa.Boolean(), server_default=sa.text("false"), nullable=False
    )
    trailing_offset: Mapped[Decimal | None] = mapped_column(NUMERIC_24_10, nullable=True)

    exit_price: Mapped[Decimal | None] = mapped_column(NUMERIC_24_10, nullable=True)
    realized_pnl_usd: Mapped[Decimal | None] = mapped_column(NUMERIC_24_10, nullable=True)
    fees_paid_usd: Mapped[Decimal | None] = mapped_column(NUMERIC_24_10, nullable=True)
    slippage_est_usd: Mapped[Decimal | None] = mapped_column(NUMERIC_24_10, nullable=True)
    notes: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)


class Order(Base):
    """Order model stub."""
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Note: In stub we can relax FK constraints if needed, but keeping them is better for parity
    trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("trades.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    side: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    order_type: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    qty: Mapped[Decimal] = mapped_column(NUMERIC_24_10, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(NUMERIC_24_10, nullable=True)
    filled_qty: Mapped[Decimal | None] = mapped_column(NUMERIC_24_10, nullable=True)
    filled_price: Mapped[Decimal | None] = mapped_column(NUMERIC_24_10, nullable=True)
    status: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    exchange_order_id: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    filled_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc), nullable=False
    )


class EquitySnapshot(Base):
    """Equity snapshot model stub."""
    __tablename__ = "equity_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    equity_usd: Mapped[Decimal] = mapped_column(NUMERIC_24_10, nullable=False)
    cash_usd: Mapped[Decimal] = mapped_column(NUMERIC_24_10, nullable=False)
    unrealized_pnl_usd: Mapped[Decimal] = mapped_column(NUMERIC_24_10, nullable=False)
    realized_pnl_today_usd: Mapped[Decimal] = mapped_column(NUMERIC_24_10, nullable=False)
    open_positions: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)


class Event(Base):
    """Event model stub."""
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seq: Mapped[int] = mapped_column(sa.BigInteger(), default=0, nullable=False) # Stub: SQLite doesn't support Identity
    ts: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    level: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    type: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    symbol: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    trade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("trades.id", ondelete="SET NULL"),
        nullable=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    public_safe: Mapped[bool] = mapped_column(
        sa.Boolean(), server_default=sa.text("false"), nullable=False
    )


class ExchangeKey(Base):
    """Exchange key model stub."""
    __tablename__ = "exchange_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exchange: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    label: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    ciphertext: Mapped[bytes] = mapped_column(sa.LargeBinary(), nullable=False)
    nonce: Mapped[bytes] = mapped_column(sa.LargeBinary(), nullable=False)
    key_version: Mapped[int] = mapped_column(
        sa.Integer(), server_default=sa.text("1"), nullable=False
    )
    # Removing created_by relation for stub simplicity unless needed, 
    # but for parity let's keep the column, just maybe not the internal User FK if User model isn't here.
    # We will assume User model is NOT present in stub_models (it wasn't before).
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean(), server_default=sa.text("true"), nullable=False
    )
    revoked_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
