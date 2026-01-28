"""Demo script showing engine opening a trade."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quantsail_engine.config.loader import load_config
from quantsail_engine.core.trading_loop import TradingLoop
from quantsail_engine.execution.dry_run_executor import DryRunExecutor
from quantsail_engine.market_data.stub_provider import StubMarketDataProvider
from quantsail_engine.models.signal import SignalType
from quantsail_engine.persistence.stub_models import Base
from quantsail_engine.signals.stub_provider import StubSignalProvider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run demo showing trade lifecycle."""
    logger.info("🎬 DEMO: Engine with trade entry")
    logger.info("=" * 60)

    # Load config
    config = load_config()
    logger.info(f"✅ Config loaded: mode={config.execution.mode}")

    # Create in-memory database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    logger.info("✅ Database connected")

    # Initialize components
    market_data = StubMarketDataProvider(base_price=50000.0)
    signals = StubSignalProvider()  # Will modify signals per tick
    executor = DryRunExecutor()

    # Create trading loop
    loop = TradingLoop(config, session, market_data, signals, executor)
    logger.info("✅ Trading loop initialized")
    logger.info("=" * 60)

    # Tick 1: HOLD signal (no action)
    logger.info("\n🔵 TICK 1: HOLD signal")
    signals.set_next_signal(SignalType.HOLD)
    loop.tick()

    # Tick 2: ENTER_LONG signal (trade opens)
    logger.info("\n🟢 TICK 2: ENTER_LONG signal")
    signals.set_next_signal(SignalType.ENTER_LONG)
    loop.tick()

    # Tick 3-4: HOLD signals (trade stays open)
    logger.info("\n🔵 TICK 3: HOLD signal (trade monitoring)")
    signals.set_next_signal(SignalType.HOLD)
    loop.tick()

    logger.info("\n🔵 TICK 4: HOLD signal (trade monitoring)")
    signals.set_next_signal(SignalType.HOLD)
    loop.tick()

    # Check database
    logger.info("\n" + "=" * 60)
    logger.info("📊 DATABASE SUMMARY:")
    logger.info("=" * 60)

    from quantsail_engine.persistence.stub_models import (
        EquitySnapshot,
        Event,
        Order,
        Trade,
    )

    trades = session.query(Trade).all()
    orders = session.query(Order).all()
    events = session.query(Event).all()
    snapshots = session.query(EquitySnapshot).all()

    logger.info(f"  Trades: {len(trades)}")
    for trade in trades:
        logger.info(
            f"    - {trade.id[:8]} | {trade.symbol} | {trade.status} | "
            f"Entry: ${trade.entry_price:.2f} | Qty: {trade.quantity}"
        )

    logger.info(f"  Orders: {len(orders)}")
    for order in orders:
        logger.info(
            f"    - {order.id[:8]} | {order.order_type} | {order.side} | "
            f"{order.status} | Price: ${order.price or 'MARKET'}"
        )

    logger.info(f"  Events: {len(events)}")
    event_types: dict[str, int] = {}
    for event in events:
        e_type = str(event.type)
        event_types[e_type] = event_types.get(e_type, 0) + 1
    for event_type, count in sorted(event_types.items()):
        logger.info(f"    - {event_type}: {count}")

    logger.info(f"  Equity Snapshots: {len(snapshots)}")
    if snapshots:
        logger.info(f"    - Latest: ${snapshots[-1].equity_usd:.2f}")

    session.close()
    logger.info("\n🏁 DEMO COMPLETE")


if __name__ == "__main__":
    main()
