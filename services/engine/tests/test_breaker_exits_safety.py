"""Critical exit safety tests - prove exits never blocked by breakers."""


from quantsail_engine.breakers.manager import BreakerManager
from quantsail_engine.config.models import BotConfig


def test_breaker_manager_exits_allowed_always_true(in_memory_db) -> None:
    """Test breaker manager exits_allowed always returns True."""
    from quantsail_engine.persistence.repository import EngineRepository

    config = BotConfig()
    repo = EngineRepository(in_memory_db)
    manager = BreakerManager(config=config.breakers, repo=repo)

    # Trigger multiple breakers
    manager.trigger_breaker("volatility", "Test1", 30, {"atr": 2.0})
    manager.trigger_breaker("spread_slippage", "Test2", 60, {"spread_bps": 100.0})
    manager.trigger_breaker("consecutive_losses", "Test3", 180, {"losses": 3})

    # Verify entries blocked
    entries_allowed, _ = manager.entries_allowed()
    assert entries_allowed is False

    # Verify exits always allowed
    exits_allowed, reason = manager.exits_allowed()
    assert exits_allowed is True
    assert reason is None
