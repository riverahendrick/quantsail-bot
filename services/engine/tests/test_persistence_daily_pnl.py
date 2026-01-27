"""Tests for EngineRepository daily PnL."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from quantsail_engine.persistence.repository import EngineRepository


def test_get_today_realized_pnl(in_memory_db: Session) -> None:
    repo = EngineRepository(in_memory_db)
    now = datetime.now(timezone.utc)
    
    # Trade 1: Closed Today (+50)
    repo.save_trade({
        "id": "t1", "symbol": "BTC/USDT", "mode": "DRY_RUN", "status": "CLOSED", 
        "side": "BUY", "entry_price": 100, "quantity": 1, "opened_at": now, 
        "closed_at": now, "pnl_usd": 50.0, "pnl_pct": 0.5
    })
    
    # Trade 2: Closed Yesterday (should be ignored)
    yesterday = now - timedelta(days=1, hours=1) 
    repo.save_trade({
        "id": "t2", "symbol": "BTC/USDT", "mode": "DRY_RUN", "status": "CLOSED",
        "side": "BUY", "entry_price": 100, "quantity": 1, "opened_at": yesterday,
        "closed_at": yesterday, "pnl_usd": 100.0, "pnl_pct": 1.0
    })
    
    pnl = repo.get_today_realized_pnl("UTC")
    assert pnl == 50.0

def test_get_today_closed_trades(in_memory_db: Session) -> None:
    repo = EngineRepository(in_memory_db)
    now = datetime.now(timezone.utc)
    
    repo.save_trade({
        "id": "t1", "symbol": "BTC/USDT", "mode": "DRY_RUN", "status": "CLOSED",
        "side": "BUY", "entry_price": 100, "quantity": 1, "opened_at": now,
        "closed_at": now, "pnl_usd": 50.0, "pnl_pct": 0.5
    })
    
    trades = repo.get_today_closed_trades("UTC")
    assert len(trades) == 1
    assert trades[0].id == "t1"
