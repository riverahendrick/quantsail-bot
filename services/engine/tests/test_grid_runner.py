"""Tests for LiveGridRunner — grid trading engine.

Covers: initialization, tick order placement, fills, sentiment blocking,
rebalance on breakout, order reconciliation, shutdown, and max_ticks.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from quantsail_engine.grid.grid_config import GridCoinConfig, GridPortfolioConfig
from quantsail_engine.grid.grid_state import CoinGridState, GridLevelState, PortfolioState
from quantsail_engine.grid.live_grid_runner import LiveGridRunner


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def single_coin_config() -> GridPortfolioConfig:
    """Minimal config with one coin and 4 grid levels."""
    return GridPortfolioConfig(
        total_capital_usd=1000.0,
        fee_pct=0.1,
        rebalance_on_breakout=True,
        poll_interval_seconds=0,  # no sleep in tests
        sentiment_enabled=False,
        coins=[
            GridCoinConfig(
                symbol="BTC",
                pair="BTC_USDT",
                allocation_pct=1.0,
                num_grids=4,
                lower_pct=10.0,
                upper_pct=10.0,
            ),
        ],
    )


@pytest.fixture()
def mock_adapter() -> MagicMock:
    """Mock exchange adapter with standard stubs."""
    adapter = MagicMock()
    adapter.fetch_ticker.return_value = {"last": 50000.0}
    adapter.create_order.return_value = {"id": "order-001"}
    adapter.fetch_open_orders.return_value = []
    adapter.fetch_order_status.return_value = {"status": "open"}
    return adapter


@pytest.fixture()
def runner(
    mock_adapter: MagicMock,
    single_coin_config: GridPortfolioConfig,
) -> LiveGridRunner:
    """Fresh LiveGridRunner with mocked state I/O."""
    return LiveGridRunner(mock_adapter, single_coin_config)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("quantsail_engine.grid.live_grid_runner.save_portfolio_state")
@patch("quantsail_engine.grid.live_grid_runner.load_portfolio_state", return_value=None)
def test_initialize_portfolio(
    _mock_load: MagicMock,
    mock_save: MagicMock,
    runner: LiveGridRunner,
    mock_adapter: MagicMock,
) -> None:
    """_initialize_portfolio builds grid levels and sets coin state."""
    mock_adapter.fetch_ticker.return_value = {"last": 50000.0}

    runner.run(max_ticks=0)

    assert runner._state is not None
    assert "BTC" in runner._state.coins

    btc = runner._state.coins["BTC"]
    assert btc.num_grids == 4
    assert len(btc.levels) == 4
    assert btc.cash == pytest.approx(1000.0, abs=1)

    # Verify save was called at least once during init
    assert mock_save.call_count >= 1


@patch("quantsail_engine.grid.live_grid_runner.save_portfolio_state")
@patch("quantsail_engine.grid.live_grid_runner.load_portfolio_state", return_value=None)
def test_tick_places_buy_orders(
    _mock_load: MagicMock,
    _mock_save: MagicMock,
    runner: LiveGridRunner,
    mock_adapter: MagicMock,
) -> None:
    """After init, the first tick should place limit buy orders."""
    mock_adapter.fetch_ticker.return_value = {"last": 50000.0}
    order_counter = {"n": 0}

    def make_order(**kwargs: object) -> dict[str, str]:
        order_counter["n"] += 1
        return {"id": f"buy-{order_counter['n']}"}

    mock_adapter.create_order.side_effect = make_order

    runner.run(max_ticks=1)

    # At least one buy order should have been placed
    assert mock_adapter.create_order.call_count >= 1
    buy_calls = [
        c for c in mock_adapter.create_order.call_args_list
        if c[1].get("side") == "buy" or (len(c[0]) > 1 and c[0][1] == "buy")
    ]
    assert len(buy_calls) >= 1


@patch("quantsail_engine.grid.live_grid_runner.save_portfolio_state")
@patch("quantsail_engine.grid.live_grid_runner.load_portfolio_state", return_value=None)
def test_fill_transitions_level_to_sell_side(
    _mock_load: MagicMock,
    _mock_save: MagicMock,
    runner: LiveGridRunner,
    mock_adapter: MagicMock,
) -> None:
    """After a buy fill, the level flips to sell side with correct holding."""
    mock_adapter.fetch_ticker.return_value = {"last": 50000.0}
    mock_adapter.create_order.return_value = {"id": "buy-1"}

    # Init + one tick to place buy orders
    runner.run(max_ticks=1)

    btc = runner._state.coins["BTC"]
    filled_level = next((lv for lv in btc.levels if lv.order_id is not None), None)
    if filled_level is None:
        pytest.skip("No orders were placed in tick 1")

    original_price = filled_level.price
    assert filled_level.side == "buy"

    # Simulate the buy fill
    mock_adapter.fetch_order_status.return_value = {
        "status": "closed",
        "average": str(original_price),
        "filled": "0.02",
        "price": str(original_price),
    }

    runner._tick()

    # Level should flip to sell side with correct holding
    assert filled_level.side == "sell"
    assert filled_level.holding == pytest.approx(0.02)
    assert filled_level.order_id is None  # Cleared after fill
    assert btc.total_buys >= 1


@patch("quantsail_engine.grid.live_grid_runner.save_portfolio_state")
@patch("quantsail_engine.grid.live_grid_runner.load_portfolio_state", return_value=None)
def test_check_fills_updates_state(
    _mock_load: MagicMock,
    _mock_save: MagicMock,
    runner: LiveGridRunner,
    mock_adapter: MagicMock,
) -> None:
    """_check_fills correctly updates cash, holding, and counters."""
    mock_adapter.fetch_ticker.return_value = {"last": 50000.0}
    mock_adapter.create_order.return_value = {"id": "order-A"}

    runner.run(max_ticks=0)  # Init only

    # Manually set a level with an active buy order
    btc = runner._state.coins["BTC"]
    level = btc.levels[0]
    level.order_id = "order-A"
    level.side = "buy"
    initial_cash = btc.cash

    # Simulate fill
    mock_adapter.fetch_order_status.return_value = {
        "status": "closed",
        "average": str(level.price),
        "filled": "0.01",
        "price": str(level.price),
    }

    filled = runner._check_fills(btc)

    assert filled == 1
    assert level.holding == pytest.approx(0.01)
    assert level.side == "sell"  # Flipped to sell
    assert level.order_id is None  # Cleared
    assert btc.total_buys == 1
    assert btc.cash < initial_cash  # Cash decreased


@patch("quantsail_engine.grid.live_grid_runner.save_portfolio_state")
@patch("quantsail_engine.grid.live_grid_runner.load_portfolio_state", return_value=None)
def test_sentiment_blocks_buys(
    _mock_load: MagicMock,
    _mock_save: MagicMock,
    mock_adapter: MagicMock,
    single_coin_config: GridPortfolioConfig,
) -> None:
    """Bearish sentiment prevents buy order placement."""
    single_coin_config.sentiment_enabled = True
    single_coin_config.sentiment_bearish_threshold = -0.3

    sentiment_fn = MagicMock(return_value=-0.5)  # Very bearish
    runner = LiveGridRunner(mock_adapter, single_coin_config, sentiment_fn=sentiment_fn)

    mock_adapter.fetch_ticker.return_value = {"last": 50000.0}

    runner.run(max_ticks=1)

    # With bearish sentiment, no buy orders should be placed
    buy_calls = [
        c for c in mock_adapter.create_order.call_args_list
        if c[1].get("side") == "buy"
    ]
    assert len(buy_calls) == 0


@patch("quantsail_engine.grid.live_grid_runner.save_portfolio_state")
@patch("quantsail_engine.grid.live_grid_runner.load_portfolio_state", return_value=None)
def test_rebalance_on_breakout(
    _mock_load: MagicMock,
    _mock_save: MagicMock,
    runner: LiveGridRunner,
    mock_adapter: MagicMock,
) -> None:
    """Price far outside grid range triggers rebalance."""
    mock_adapter.fetch_ticker.return_value = {"last": 50000.0}
    mock_adapter.create_order.return_value = {"id": "order-init"}

    runner.run(max_ticks=0)  # Init only

    btc_before = runner._state.coins["BTC"]
    old_center = btc_before.grid_center
    assert btc_before.num_rebalances == 0

    # Price crashes far below the grid range (need to be < grid_low * 0.95)
    mock_adapter.fetch_ticker.return_value = {"last": 35000.0}
    mock_adapter.create_order.return_value = {"id": "rebal-order"}

    # Use _tick directly to avoid re-initialization
    runner._tick()

    btc_after = runner._state.coins["BTC"]
    # Grid should be rebalanced
    assert btc_after.num_rebalances == 1
    assert btc_after.grid_center != old_center


@patch("quantsail_engine.grid.live_grid_runner.save_portfolio_state")
@patch("quantsail_engine.grid.live_grid_runner.load_portfolio_state")
def test_reconcile_clears_stale_orders(
    mock_load: MagicMock,
    _mock_save: MagicMock,
    mock_adapter: MagicMock,
    single_coin_config: GridPortfolioConfig,
) -> None:
    """Orders not found on exchange are cleared from state."""
    # Pre-populate state with stale orders
    levels = [
        GridLevelState(price=49000, sell_price=49500, order_id="stale-1", side="buy"),
        GridLevelState(price=49500, sell_price=50000, order_id="live-1", side="buy"),
        GridLevelState(price=50000, sell_price=50500, order_id=None, side="buy"),
    ]
    saved_state = PortfolioState(
        started_at="2026-01-01T00:00:00Z",
        total_capital_usd=1000.0,
        coins={
            "BTC": CoinGridState(
                symbol="BTC",
                pair="BTC_USDT",
                cash=500.0,
                allocation_usd=1000.0,
                grid_center=50000.0,
                num_grids=3,
                lower_pct=10.0,
                upper_pct=10.0,
                levels=levels,
            )
        },
    )
    mock_load.return_value = saved_state

    # Only "live-1" is on exchange
    mock_adapter.fetch_open_orders.return_value = [{"id": "live-1"}]
    mock_adapter.fetch_ticker.return_value = {"last": 50000.0}
    mock_adapter.create_order.return_value = {"id": "new-order"}

    runner = LiveGridRunner(mock_adapter, single_coin_config)
    runner.run(max_ticks=0)

    btc = runner._state.coins["BTC"]
    # "stale-1" should be cleared, "live-1" kept
    assert btc.levels[0].order_id is None  # stale cleared
    assert btc.levels[1].order_id == "live-1"  # live kept


@patch("quantsail_engine.grid.live_grid_runner.save_portfolio_state")
@patch("quantsail_engine.grid.live_grid_runner.load_portfolio_state", return_value=None)
def test_shutdown_saves_state(
    _mock_load: MagicMock,
    mock_save: MagicMock,
    runner: LiveGridRunner,
    mock_adapter: MagicMock,
) -> None:
    """_shutdown persists current state to disk."""
    mock_adapter.fetch_ticker.return_value = {"last": 50000.0}

    runner.run(max_ticks=0)

    mock_save.reset_mock()
    runner._shutdown()

    assert mock_save.call_count == 1


@patch("quantsail_engine.grid.live_grid_runner.save_portfolio_state")
@patch("quantsail_engine.grid.live_grid_runner.load_portfolio_state", return_value=None)
def test_max_ticks(
    _mock_load: MagicMock,
    _mock_save: MagicMock,
    runner: LiveGridRunner,
    mock_adapter: MagicMock,
) -> None:
    """Runner respects max_ticks limit."""
    mock_adapter.fetch_ticker.return_value = {"last": 50000.0}
    mock_adapter.create_order.return_value = {"id": "order-x"}

    runner.run(max_ticks=3)

    assert runner._tick_count == 3
