from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NUMERIC_24_10 = sa.Numeric(24, 10)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (sa.UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    role: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=lambda: dt.datetime.now(dt.timezone.utc),
        nullable=False,
    )


class ExchangeKey(Base):
    __tablename__ = "exchange_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exchange: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    label: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    ciphertext: Mapped[bytes] = mapped_column(sa.LargeBinary(), nullable=False)
    nonce: Mapped[bytes] = mapped_column(sa.LargeBinary(), nullable=False)
    key_version: Mapped[int] = mapped_column(
        sa.Integer(), server_default=sa.text("1"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=lambda: dt.datetime.now(dt.timezone.utc),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean(), server_default=sa.text("true"), nullable=False
    )
    revoked_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )


class BotConfigVersion(Base):
    __tablename__ = "bot_config_versions"
    __table_args__ = (
        sa.UniqueConstraint("version", name="uq_bot_config_versions_version"),
        sa.Index(
            "uq_bot_config_versions_is_active",
            "is_active",
            unique=True,
            postgresql_where=sa.text("is_active"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    config_hash: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=lambda: dt.datetime.now(dt.timezone.utc),
        nullable=False,
    )
    activated_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean(), server_default=sa.text("false"), nullable=False
    )


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        sa.Index("ix_trades_symbol_opened_at", "symbol", sa.desc("opened_at")),
        sa.Index("ix_trades_status", "status"),
    )

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
    notes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        sa.Index("ix_orders_trade_id", "trade_id"),
        sa.Index("ix_orders_symbol_created_at", "symbol", sa.desc("created_at")),
        sa.Index("ix_orders_exchange_order_id", "exchange_order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=lambda: dt.datetime.now(dt.timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=lambda: dt.datetime.now(dt.timezone.utc),
        nullable=False,
    )


class EquitySnapshot(Base):
    __tablename__ = "equity_snapshots"
    __table_args__ = (sa.Index("ix_equity_snapshots_ts", sa.desc("ts")),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    equity_usd: Mapped[Decimal] = mapped_column(NUMERIC_24_10, nullable=False)
    cash_usd: Mapped[Decimal] = mapped_column(NUMERIC_24_10, nullable=False)
    unrealized_pnl_usd: Mapped[Decimal] = mapped_column(NUMERIC_24_10, nullable=False)
    realized_pnl_today_usd: Mapped[Decimal] = mapped_column(NUMERIC_24_10, nullable=False)
    open_positions: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        sa.Index("uq_events_seq", "seq", unique=True),
        sa.Index("ix_events_ts", sa.desc("ts")),
        sa.Index("ix_events_type", "type"),
        sa.Index("ix_events_symbol", "symbol"),
        sa.Index("ix_events_public_safe", "public_safe"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seq: Mapped[int] = mapped_column(sa.BigInteger(), sa.Identity(), nullable=False)
    ts: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    level: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    type: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    symbol: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    trade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("trades.id", ondelete="SET NULL"),
        nullable=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    public_safe: Mapped[bool] = mapped_column(
        sa.Boolean(), server_default=sa.text("false"), nullable=False
    )
