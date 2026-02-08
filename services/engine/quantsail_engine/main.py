"""Main entry point for the trading engine."""

import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quantsail_engine.config.loader import load_config
from quantsail_engine.core.trading_loop import TradingLoop
from quantsail_engine.execution.dry_run_executor import DryRunExecutor
from quantsail_engine.market_data.stub_provider import StubMarketDataProvider
from quantsail_engine.monitoring.sentry_service import SentryConfig, init_sentry, get_sentry
from quantsail_engine.security.encryption import EncryptionService
from quantsail_engine.signals.ensemble_provider import EnsembleSignalProvider

# Try to import real DB models, fall back to stub
try:
    from app.db.base import Base  # type: ignore[import-not-found]
except ModuleNotFoundError:
    from quantsail_engine.persistence.stub_models import Base

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Main entry point for the trading engine."""
    logger.info("🚀 Quantsail Engine starting...")

    # Initialize Sentry (if SENTRY_DSN is configured)
    sentry_dsn = os.environ.get("SENTRY_DSN", "")
    if sentry_dsn:
        sentry_env = os.environ.get("SENTRY_ENVIRONMENT", "development")
        sentry_config = SentryConfig(
            dsn=sentry_dsn,
            environment=sentry_env,
            traces_sample_rate=0.1,
        )
        sentry = init_sentry(sentry_config)
        logger.info(f"✅ Sentry initialized (env={sentry_env})")
    else:
        logger.info("⚠️ Sentry not configured (set SENTRY_DSN to enable)")

    # Load configuration
    try:
        config = load_config()
        logger.info(f"✅ Configuration loaded: mode={config.execution.mode}")
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        sentry = get_sentry()
        if sentry:
            sentry.capture_error(e, context={"phase": "config_load"})
            sentry.flush()
        return 1

    # Create database session
    database_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    logger.info(f"📊 Connecting to database: {database_url.split('@')[0]}...")

    try:
        engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        logger.info("✅ Database connected")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        sentry = get_sentry()
        if sentry:
            sentry.capture_error(e, context={"phase": "db_connect"})
            sentry.flush()
        return 1

    # Initialize components
    logger.info("🔧 Initializing trading components...")
    market_data_provider = StubMarketDataProvider(base_price=50000.0)
    # Use EnsembleProvider by default
    signal_provider = EnsembleSignalProvider(config)
    
    if config.execution.mode == "live":
        from quantsail_engine.execution.binance_adapter import BinanceSpotAdapter
        from quantsail_engine.execution.live_executor import LiveExecutor
        from quantsail_engine.persistence.repository import EngineRepository
        
        repo = EngineRepository(session)
        encryption = EncryptionService()
        credentials = repo.get_active_exchange_credentials("binance", encryption)

        api_key = credentials.api_key if credentials else os.environ.get("BINANCE_API_KEY")
        secret = credentials.secret_key if credentials else os.environ.get("BINANCE_SECRET")
        testnet = os.environ.get("BINANCE_TESTNET", "false").lower() == "true"
        
        if not api_key or not secret:
            logger.error(
                "❌ Live mode requires active exchange keys (dashboard) or BINANCE_API_KEY/BINANCE_SECRET"
            )
            return 1
            
        adapter = BinanceSpotAdapter(api_key, secret, testnet=testnet)
        execution_engine = LiveExecutor(repo, adapter)
        logger.info(f"✅ Live execution enabled (Testnet: {testnet})")
    else:
        execution_engine = DryRunExecutor()
        logger.info("✅ Dry-run execution enabled")

    # Create trading loop
    trading_loop = TradingLoop(
        config=config,
        session=session,
        market_data_provider=market_data_provider,
        signal_provider=signal_provider,
        execution_engine=execution_engine,
    )
    logger.info("✅ Trading loop initialized")

    # Run the loop
    try:
        max_ticks_env = os.environ.get("MAX_TICKS")
        max_ticks = int(max_ticks_env) if max_ticks_env is not None else 5
        logger.info(
            f"▶️  Starting trading loop for symbols: {config.symbols.enabled} "
            f"(max_ticks={max_ticks})"
        )
        trading_loop.run(max_ticks=max_ticks)
    except KeyboardInterrupt:
        logger.info("⏸️  Shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ Trading loop error: {e}", exc_info=True)
        sentry = get_sentry()
        if sentry:
            sentry.capture_error(e, context={"phase": "trading_loop"})
            sentry.flush()
        return 1
    finally:
        # Flush any pending Sentry events
        sentry = get_sentry()
        if sentry:
            sentry.flush()
        session.close()
        logger.info("🛑 Engine stopped")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
