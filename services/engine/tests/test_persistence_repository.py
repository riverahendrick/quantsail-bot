"""Tests for EngineRepository."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from quantsail_engine.persistence.repository import EngineRepository


def test_save_trade(in_memory_db: Session) -> None:
    """Test saving a new trade."""
    repo = EngineRepository(in_memory_db)
    t_id = uuid.uuid4()
    trade_data = {
        "id": t_id,
        "symbol": "BTC/USDT",
        "mode": "DRY_RUN",
        "status": "OPEN",
        "side": "BUY",
        "entry_price": 50000.0,
        "quantity": 0.1,
        "opened_at": datetime.now(timezone.utc),
        "closed_at": None,
        "exit_price": None,
        "realized_pnl_usd": None,
    }

    trade_id = repo.save_trade(trade_data)
    assert trade_id == str(t_id)

    # Verify it was saved
    saved_trade = repo.get_trade(trade_id)
    assert saved_trade is not None
    assert saved_trade["symbol"] == "BTC/USDT"
    assert saved_trade["status"] == "OPEN"


def test_update_trade(in_memory_db: Session) -> None:
    """Test updating an existing trade."""
    repo = EngineRepository(in_memory_db)
    now = datetime.now(timezone.utc)
    t_id = uuid.uuid4()

    # Create trade
    trade_data = {
        "id": t_id,
        "symbol": "ETH/USDT",
        "mode": "DRY_RUN",
        "status": "OPEN",
        "side": "BUY",
        "entry_price": 3000.0,
        "quantity": 1.0,
        "opened_at": now,
        "closed_at": None,
        "exit_price": None,
        "realized_pnl_usd": None,
    }
    repo.save_trade(trade_data)

    # Update trade
    trade_data["status"] = "CLOSED"
    trade_data["closed_at"] = now
    trade_data["exit_price"] = 3200.0
    trade_data["realized_pnl_usd"] = 200.0

    repo.update_trade(trade_data)

    # Verify update
    updated_trade = repo.get_trade(str(t_id))
    assert updated_trade is not None
    assert updated_trade["status"] == "CLOSED"
    assert updated_trade["exit_price"] == 3200.0
    assert updated_trade["realized_pnl_usd"] == 200.0


def test_get_trade_nonexistent(in_memory_db: Session) -> None:
    """Test getting a nonexistent trade returns None."""
    repo = EngineRepository(in_memory_db)
    trade = repo.get_trade(str(uuid.uuid4()))
    assert trade is None


def test_save_order(in_memory_db: Session) -> None:
    """Test saving a new order."""
    repo = EngineRepository(in_memory_db)
    now = datetime.now(timezone.utc)
    t_id = uuid.uuid4()

    # Create trade first
    trade_data = {
        "id": t_id,
        "symbol": "BTC/USDT",
        "mode": "DRY_RUN",
        "status": "OPEN",
        "side": "BUY",
        "entry_price": 50000.0,
        "quantity": 0.1,
        "opened_at": now,
    }
    repo.save_trade(trade_data)

    # Create order
    o_id = uuid.uuid4()
    order_data = {
        "id": o_id,
        "trade_id": t_id,
        "symbol": "BTC/USDT",
        "side": "BUY",
        "order_type": "MARKET",
        "status": "FILLED",
        "quantity": 0.1,
        "price": 50000.0,
        "filled_price": 50000.0,
        "filled_qty": 0.1,
        "created_at": now,
        "filled_at": now,
    }

    order_id = repo.save_order(order_data)
    assert order_id == str(o_id)


def test_append_event(in_memory_db: Session) -> None:
    """Test appending an event."""
    repo = EngineRepository(in_memory_db)

    seq = repo.append_event(
        event_type="market.tick",
        level="INFO",
        payload={"symbol": "BTC/USDT", "price": 50000.0},
        public_safe=True,
    )

    assert seq is not None
    assert seq >= 0


def test_calculate_equity_no_trades(in_memory_db: Session) -> None:
    """Test equity calculation with no trades."""
    repo = EngineRepository(in_memory_db)
    equity = repo.calculate_equity(starting_cash_usd=10000.0)
    assert equity == 10000.0


def test_calculate_equity_with_closed_trades(in_memory_db: Session) -> None:
    """Test equity calculation with closed trades."""
    repo = EngineRepository(in_memory_db)
    now = datetime.now(timezone.utc)

    # Create and close trade 1 (+200 USD)
    trade1 = {
        "id": uuid.uuid4(),
        "symbol": "BTC/USDT",
        "mode": "DRY_RUN",
        "status": "CLOSED",
        "side": "BUY",
        "entry_price": 50000.0,
        "quantity": 0.1,
        "opened_at": now,
        "closed_at": now,
        "exit_price": 52000.0,
        "realized_pnl_usd": 200.0,
    }
    repo.save_trade(trade1)

    # Create and close trade 2 (-50 USD)
    trade2 = {
        "id": uuid.uuid4(),
        "symbol": "ETH/USDT",
        "mode": "DRY_RUN",
        "status": "CLOSED",
        "side": "BUY",
        "entry_price": 3000.0,
        "quantity": 1.0,
        "opened_at": now,
        "closed_at": now,
        "exit_price": 2950.0,
        "realized_pnl_usd": -50.0,
    }
    repo.save_trade(trade2)

    # Equity = 10000 + 200 - 50 = 10150
    equity = repo.calculate_equity(starting_cash_usd=10000.0)
    assert equity == 10150.0


def test_calculate_equity_ignores_open_trades(in_memory_db: Session) -> None:
    """Test equity calculation ignores open trades."""
    repo = EngineRepository(in_memory_db)
    now = datetime.now(timezone.utc)

    # Create closed trade
    closed_trade = {
        "id": uuid.uuid4(),
        "symbol": "BTC/USDT",
        "mode": "DRY_RUN",
        "status": "CLOSED",
        "side": "BUY",
        "entry_price": 50000.0,
        "quantity": 0.1,
        "opened_at": now,
        "closed_at": now,
        "exit_price": 51000.0,
        "realized_pnl_usd": 100.0,
    }
    repo.save_trade(closed_trade)

    # Create open trade (should be ignored)
    open_trade = {
        "id": uuid.uuid4(),
        "symbol": "ETH/USDT",
        "mode": "DRY_RUN",
        "status": "OPEN",
        "side": "BUY",
        "entry_price": 3000.0,
        "quantity": 1.0,
        "opened_at": now,
    }
    repo.save_trade(open_trade)

    # Only closed trade PnL should be included
    equity = repo.calculate_equity(starting_cash_usd=10000.0)
    assert equity == 10100.0


def test_save_equity_snapshot(in_memory_db: Session) -> None:
    """Test saving an equity snapshot."""
    repo = EngineRepository(in_memory_db)
    repo.save_equity_snapshot(equity_usd=10500.0)

    # Verify snapshot was saved (no direct getter, but commit should succeed)
    from quantsail_engine.persistence.stub_models import EquitySnapshot

    snapshots = in_memory_db.query(EquitySnapshot).all()
    assert len(snapshots) == 1
    assert snapshots[0].equity_usd == 10500.0