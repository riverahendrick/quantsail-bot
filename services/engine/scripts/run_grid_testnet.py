"""Launch script for grid trading on Binance testnet.

Loads configuration from .env, initializes the exchange adapter and
sentiment provider, and starts the live grid runner.

Usage:
    # Full testnet run (polls every 60s, runs indefinitely)
    python scripts/run_grid_testnet.py

    # Quick test (5 ticks, 10s interval)
    python scripts/run_grid_testnet.py --ticks 5 --interval 10

    # Dry-run mode (no real orders, just prints what it would do)
    python scripts/run_grid_testnet.py --dry-run

    # Custom capital
    python scripts/run_grid_testnet.py --capital 1000
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add engine root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quantsail_engine.grid.grid_config import GridPortfolioConfig, load_grid_config  # noqa: E402
from quantsail_engine.grid.live_grid_runner import LiveGridRunner  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("grid_testnet")


def load_env_file(env_path: str | None = None) -> None:
    """Load .env file into os.environ (simple parser, no dependencies)."""
    if env_path is None:
        env_path = str(
            Path(__file__).resolve().parent.parent / ".env"
        )

    path = Path(env_path)
    if not path.exists():
        logger.warning("No .env file found at %s", path)
        return

    loaded = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Don't override existing env vars
                if key not in os.environ:
                    os.environ[key] = value
                    loaded += 1

    logger.info("Loaded %d env vars from %s", loaded, path)


def create_sentiment_function() -> object | None:
    """Create a CryptoPanic sentiment lookup function.

    Returns:
        Callable(symbol) -> float | None, or None if not configured
    """
    api_key = os.environ.get("CRYPTOPANIC_API_KEY")
    if not api_key:
        logger.info("No CRYPTOPANIC_API_KEY — sentiment disabled")
        return None

    try:
        from quantsail_engine.market_data.cryptopanic import (
            CryptoPanicConfig,
            CryptoPanicProvider,
        )

        config = CryptoPanicConfig(api_key=api_key)
        # We'll create a simple sync wrapper around the async provider
        provider = CryptoPanicProvider(config)
        logger.info("CryptoPanic sentiment provider initialized")

        # Cache to avoid hammering the API
        sentiment_cache: dict[str, float] = {}
        cache_tick: list[int] = [0]

        def get_sentiment(symbol: str) -> float | None:
            """Get sentiment for a symbol, cached per tick."""
            if symbol in sentiment_cache:
                return sentiment_cache[symbol]

            try:
                # Run async in new loop (safe for sync context)
                loop = asyncio.new_event_loop()
                try:
                    summary = loop.run_until_complete(
                        provider.get_sentiment(symbol, time_window_hours=6)
                    )
                    score = summary.avg_sentiment if summary else 0.0
                    sentiment_cache[symbol] = score
                    return score
                finally:
                    loop.close()
            except Exception as e:
                logger.debug("Sentiment fetch failed for %s: %s", symbol, e)
                return None

        return get_sentiment

    except ImportError as e:
        logger.warning("CryptoPanic import failed: %s — sentiment disabled", e)
        return None


class DryRunAdapter:
    """Fake adapter that logs actions instead of placing real orders.

    Used with --dry-run flag for testing without any exchange connection.
    """

    def __init__(self) -> None:
        """Initialize dry-run adapter."""
        self._order_counter = 0
        self._orders: dict[str, dict[str, object]] = {}

    def fetch_ticker(self, symbol: str) -> dict[str, float]:
        """Return a simulated ticker."""
        # For dry-run, use approximate current prices
        prices: dict[str, float] = {
            "BTC/USDT": 97000.0,
            "ETH/USDT": 2700.0,
            "BNB/USDT": 650.0,
            "SOL/USDT": 200.0,
            "XRP/USDT": 2.50,
            "LINK/USDT": 20.0,
            "ADA/USDT": 0.75,
            "DOGE/USDT": 0.35,
            "NEAR/USDT": 3.50,
            "SUI/USDT": 3.20,
        }
        price = prices.get(symbol, 100.0)
        return {"last": price, "bid": price * 0.999, "ask": price * 1.001}

    def create_order(self, **kwargs: object) -> dict[str, object]:
        """Simulate order creation."""
        self._order_counter += 1
        order_id = f"DRY-{self._order_counter}"
        order = {"id": order_id, "status": "open", **kwargs}
        self._orders[order_id] = order
        logger.info(
            "  [DRY-RUN] %s %s %.6f @ $%.4f",
            kwargs.get("side", "?"),
            kwargs.get("symbol", "?"),
            kwargs.get("quantity", 0),
            kwargs.get("price", 0),
        )
        return order

    def fetch_order_status(
        self, symbol: str, order_id: str
    ) -> dict[str, object]:
        """Return stored order."""
        return self._orders.get(order_id, {"status": "canceled"})

    def fetch_open_orders(self, symbol: str) -> list[dict[str, object]]:
        """Return empty list."""
        return []

    def cancel_order(self, symbol: str, order_id: str) -> dict[str, str]:
        """Simulate cancel."""
        if order_id in self._orders:
            del self._orders[order_id]
        return {"status": "canceled"}


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run grid trading bot on Binance testnet"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Dry-run mode (no real orders)",
    )
    parser.add_argument(
        "--ticks", type=int, default=None,
        help="Max ticks to run (default: infinite)",
    )
    parser.add_argument(
        "--interval", type=int, default=60,
        help="Seconds between ticks (default: 60)",
    )
    parser.add_argument(
        "--capital", type=float, default=5000.0,
        help="Total capital in USD (default: 5000)",
    )
    parser.add_argument(
        "--no-sentiment", action="store_true",
        help="Disable CryptoPanic sentiment gating",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to grid config JSON (default: use built-in 10-coin portfolio)",
    )
    parser.add_argument(
        "--env", type=str, default=None,
        help="Path to .env file (default: services/engine/.env)",
    )
    args = parser.parse_args()

    # Load environment
    load_env_file(args.env)

    # Verify keys
    api_key = os.environ.get("BINANCE_API_KEY")
    secret = os.environ.get("BINANCE_SECRET")
    testnet = os.environ.get("BINANCE_TESTNET", "false").lower() == "true"

    if not args.dry_run and (not api_key or not secret):
        logger.error(
            "❌ BINANCE_API_KEY and BINANCE_SECRET required. "
            "Set them in .env or as environment variables."
        )
        return 1

    # Load grid config
    config = load_grid_config(args.config)
    config.total_capital_usd = args.capital
    config.poll_interval_seconds = args.interval
    config.sentiment_enabled = not args.no_sentiment

    logger.info("=" * 60)
    logger.info("  QUANTSAIL GRID BOT — TESTNET LAUNCHER")
    logger.info("=" * 60)
    logger.info("  Mode: %s", "DRY-RUN" if args.dry_run else "LIVE TESTNET")
    logger.info("  Capital: $%s", f"{config.total_capital_usd:,.0f}")
    logger.info("  Coins: %d", len(config.coins))
    logger.info("  Poll interval: %ds", config.poll_interval_seconds)
    logger.info("  Sentiment: %s",
                "ENABLED" if config.sentiment_enabled else "DISABLED")
    logger.info("  Testnet: %s", testnet)
    if args.ticks:
        logger.info("  Max ticks: %d", args.ticks)

    # Create adapter
    if args.dry_run:
        adapter: object = DryRunAdapter()
        logger.info("  Using DRY-RUN adapter (no real orders)")
    else:
        from quantsail_engine.execution.binance_adapter import BinanceSpotAdapter
        assert api_key is not None and secret is not None
        adapter = BinanceSpotAdapter(api_key, secret, testnet=testnet)
        logger.info("  Connected to Binance %s",
                     "TESTNET" if testnet else "MAINNET ⚠️")

    # Create sentiment function
    sentiment_fn = None
    if config.sentiment_enabled:
        sentiment_fn = create_sentiment_function()

    # Create and run the grid engine
    runner = LiveGridRunner(
        adapter=adapter,
        config=config,
        sentiment_fn=sentiment_fn,
    )

    try:
        runner.run(max_ticks=args.ticks)
    except KeyboardInterrupt:
        logger.info("Shutdown requested")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
