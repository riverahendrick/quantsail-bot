import signal
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from sqlalchemy.orm import Session

from quantsail_engine.config.models import (
    BotConfig,
    ExecutionConfig,
    RiskConfig,
    SymbolsConfig,
)
from quantsail_engine.core.state_machine import TradingState
from quantsail_engine.core.trading_loop import TradingLoop
from quantsail_engine.execution.executor import ExecutionEngine
from quantsail_engine.market_data.provider import MarketDataProvider
from quantsail_engine.models.candle import Orderbook
from quantsail_engine.signals.provider import SignalProvider


@pytest.fixture
def mock_deps() -> dict[str, MagicMock]:
    session = MagicMock(spec=Session)
    # Provide bind.dialect.name so EngineRepository.append_event works
    mock_bind = MagicMock()
    mock_bind.dialect.name = "sqlite"
    type(session).bind = PropertyMock(return_value=mock_bind)
    return {
        "session": session,
        "market_data": MagicMock(spec=MarketDataProvider),
        "signal_provider": MagicMock(spec=SignalProvider),
        "execution": MagicMock(spec=ExecutionEngine),
    }


@pytest.fixture
def config() -> BotConfig:
    return BotConfig(
        execution=ExecutionConfig(mode="dry-run"),
        symbols=SymbolsConfig(enabled=["BTC/USDT"]),
        risk=RiskConfig(starting_cash_usd=10000.0),
    )


def test_trading_loop_exit_logic(config: BotConfig, mock_deps: dict[str, MagicMock]) -> None:
    loop = TradingLoop(
        config=config,
        session=mock_deps["session"],
        market_data_provider=mock_deps["market_data"],
        signal_provider=mock_deps["signal_provider"],
        execution_engine=mock_deps["execution"],
    )

    symbol = "BTC/USDT"
    sm = loop.state_machines[symbol]

    # 1. Setup IN_POSITION state
    sm._current_state = TradingState.IN_POSITION
    t_id = str(uuid.uuid4())
    loop.open_trades[symbol] = t_id

    # Mock market data
    mock_deps["market_data"].get_orderbook.return_value = Orderbook(
        bids=[(51995.0, 1.0)], asks=[(52005.0, 1.0)]
    )

    # Mock exit check returning True (TP hit)
    mock_deps["execution"].check_exits.return_value = {
        "trade": {
            "id": t_id,
            "exit_price": 52000.0,
            "realized_pnl_usd": 200.0,
            "status": "CLOSED"
        },
        "exit_order": {
            "id": str(uuid.uuid4()),
            "trade_id": t_id,
            "symbol": "BTC/USDT",
            "order_type": "MARKET",
            "side": "SELL",
            "status": "FILLED",
            "quantity": 0.01,
            "created_at": "2024-01-01T00:00:00Z",
            "filled_at": "2024-01-01T00:00:01Z",
            "filled_price": 52000.0,
        },
        "exit_reason": "TAKE_PROFIT"
    }

    # 2. Run tick: IN_POSITION -> EXIT_PENDING -> IDLE (all in one tick)
    loop._tick_symbol(symbol)
    assert sm.current_state == TradingState.IDLE
    
    # Verify open trade removed
    assert symbol not in loop.open_trades
    
    # Verify persistence calls
    mock_deps["execution"].check_exits.assert_called()


def test_trading_loop_missing_trade_id_recovery(
    config: BotConfig, mock_deps: dict[str, MagicMock]
) -> None:
    loop = TradingLoop(
        config=config,
        session=mock_deps["session"],
        market_data_provider=mock_deps["market_data"],
        signal_provider=mock_deps["signal_provider"],
        execution_engine=mock_deps["execution"],
    )
    symbol = "BTC/USDT"
    sm = loop.state_machines[symbol]
    
    # Case 1: IN_POSITION but no trade ID
    sm._current_state = TradingState.IN_POSITION
    loop.open_trades.clear()
    loop._tick_symbol(symbol)
    assert sm.current_state == TradingState.IDLE
    
    # Case 2: EXIT_PENDING but no trade ID
    sm._current_state = TradingState.EXIT_PENDING
    loop.open_trades.clear()
    loop._tick_symbol(symbol)
    assert sm.current_state == TradingState.IDLE


def test_signal_handler(config: BotConfig, mock_deps: dict[str, MagicMock]) -> None:
    loop = TradingLoop(
        config=config,
        session=mock_deps["session"],
        market_data_provider=mock_deps["market_data"],
        signal_provider=mock_deps["signal_provider"],
        execution_engine=mock_deps["execution"],
    )
    
    assert loop._shutdown_requested is False
    loop._signal_handler(signal.SIGINT, None)
    assert loop._shutdown_requested is True