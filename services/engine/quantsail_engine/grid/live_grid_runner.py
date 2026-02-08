"""Live Grid Runner — Places real limit orders on Binance.

This is the production grid trading engine. Instead of reading CSV ticks,
it polls live prices from Binance and places/manages limit orders for
each grid level across all configured coins.

Features:
- Polls price every N seconds (configurable)
- Places limit buy orders at grid levels below current price
- Places limit sell orders at grid levels above buy price
- Integrates CryptoPanic sentiment to skip buys during bearish conditions
- Persists state to JSON for crash recovery
- Graceful shutdown on SIGINT/SIGTERM
"""

from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timezone
from typing import Any

from quantsail_engine.grid.grid_config import GridCoinConfig, GridPortfolioConfig
from quantsail_engine.grid.grid_state import (
    CoinGridState,
    GridLevelState,
    PortfolioState,
    load_portfolio_state,
    save_portfolio_state,
)

logger = logging.getLogger(__name__)


class LiveGridRunner:
    """Live grid trading engine using Binance limit orders.

    Usage:
        runner = LiveGridRunner(adapter, config, sentiment_provider)
        runner.run()  # Blocks until SIGINT
    """

    def __init__(
        self,
        adapter: Any,  # BinanceSpotAdapter
        config: GridPortfolioConfig,
        sentiment_fn: Any | None = None,
    ) -> None:
        """Initialize live grid runner.

        Args:
            adapter: Binance exchange adapter (must have fetch_ticker,
                     create_order, cancel_order, fetch_open_orders)
            config: Grid portfolio configuration
            sentiment_fn: Optional callable(symbol) -> float score (-1 to +1)
        """
        self.adapter = adapter
        self.config = config
        self.sentiment_fn = sentiment_fn
        self._running = False
        self._state: PortfolioState | None = None
        self._tick_count = 0

    def run(self, max_ticks: int | None = None) -> None:
        """Main event loop. Polls prices and manages grid orders.

        Args:
            max_ticks: Maximum ticks to run (None = infinite, for testnet)
        """
        self._running = True
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        logger.info("=" * 60)
        logger.info("  LIVE GRID ENGINE STARTING")
        logger.info("  Capital: $%s | Coins: %d | Poll: %ds",
                     f"{self.config.total_capital_usd:,.0f}",
                     len(self.config.coins),
                     self.config.poll_interval_seconds)
        logger.info("  Sentiment: %s",
                     "ENABLED" if self.config.sentiment_enabled else "DISABLED")
        logger.info("=" * 60)

        # Load or create state
        self._state = load_portfolio_state()
        if self._state is None:
            logger.info("No saved state found — initializing fresh portfolio")
            self._initialize_portfolio()
        else:
            logger.info("Restored state from disk (%d coins)",
                        len(self._state.coins))
            self._reconcile_with_exchange()

        while self._running:
            if max_ticks is not None and self._tick_count >= max_ticks:
                logger.info("Reached max_ticks=%d, stopping", max_ticks)
                break

            try:
                self._tick()
                self._tick_count += 1
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error("Tick error: %s", e, exc_info=True)

            if self._running:
                time.sleep(self.config.poll_interval_seconds)

        self._shutdown()

    def _initialize_portfolio(self) -> None:
        """Create fresh portfolio state by fetching current prices."""
        assert self._state is None
        self._state = PortfolioState(
            started_at=datetime.now(timezone.utc).isoformat(),
            total_capital_usd=self.config.total_capital_usd,
        )

        for coin in self.config.coins:
            price = self._fetch_price(coin.ccxt_symbol)
            if price is None:
                logger.warning(
                    "Could not fetch price for %s — skipping (may not be "
                    "available on testnet)", coin.symbol)
                continue

            alloc = self.config.total_capital_usd * coin.allocation_pct
            coin_state = self._build_grid(coin, price, alloc)
            self._state.coins[coin.symbol] = coin_state
            logger.info("  %s: grid built around $%.2f, %d levels, $%.0f allocated",
                        coin.symbol, price, len(coin_state.levels), alloc)

        save_portfolio_state(self._state)
        logger.info("Portfolio initialized with %d coins", len(self._state.coins))

    def _build_grid(
        self,
        coin: GridCoinConfig,
        center_price: float,
        allocation_usd: float,
    ) -> CoinGridState:
        """Build grid levels around current price."""
        lower = center_price * (1 - coin.lower_pct / 100)
        upper = center_price * (1 + coin.upper_pct / 100)
        spacing = (upper - lower) / coin.num_grids

        levels: list[GridLevelState] = []
        for i in range(coin.num_grids):
            buy_price = round(lower + i * spacing, 8)
            spread = spacing * 0.8  # sell target = buy + 80% of spacing
            sell_price = round(buy_price + spread, 8)
            levels.append(GridLevelState(
                price=buy_price,
                sell_price=sell_price,
                holding=0.0,
                order_id=None,
                side="buy",
            ))

        return CoinGridState(
            symbol=coin.symbol,
            pair=coin.pair,
            cash=allocation_usd,
            allocation_usd=allocation_usd,
            grid_center=center_price,
            num_grids=coin.num_grids,
            lower_pct=coin.lower_pct,
            upper_pct=coin.upper_pct,
            levels=levels,
        )

    def _tick(self) -> None:
        """Execute one tick: check prices, manage orders for all coins."""
        assert self._state is not None

        for symbol, coin_state in self._state.coins.items():
            price = self._fetch_price(coin_state.pair.replace("_", "/"))
            if price is None:
                continue

            # Check for filled orders
            filled_count = self._check_fills(coin_state)
            if filled_count > 0:
                logger.info("[%s] %d orders filled at price $%.2f",
                            symbol, filled_count, price)

            # Check sentiment before placing new buy orders
            buy_allowed = True
            if self.config.sentiment_enabled and self.sentiment_fn:
                sentiment = self.sentiment_fn(symbol)
                if sentiment is not None and sentiment < self.config.sentiment_bearish_threshold:
                    logger.info(
                        "[%s] Skipping buys — bearish sentiment %.2f (threshold: %.2f)",
                        symbol, sentiment, self.config.sentiment_bearish_threshold)
                    buy_allowed = False

            # Place new orders where needed
            orders_placed = self._manage_orders(coin_state, price, buy_allowed)
            if orders_placed > 0:
                logger.info("[%s] Placed %d new orders", symbol, orders_placed)

            # Check for rebalance (price broke out of grid range)
            if self.config.rebalance_on_breakout:
                self._check_rebalance(coin_state, price)

        # Save state after every tick
        save_portfolio_state(self._state)

        if self._tick_count % 10 == 0:
            self._print_summary()

    def _manage_orders(
        self,
        coin_state: CoinGridState,
        current_price: float,
        buy_allowed: bool,
    ) -> int:
        """Place limit orders for empty grid levels.

        Returns:
            Number of new orders placed
        """
        placed = 0
        qty_per_level = coin_state.cash / max(
            coin_state.num_grids, 1
        ) / current_price if current_price > 0 else 0

        for level in coin_state.levels:
            if level.order_id is not None:
                # Already has an active order
                continue

            ccxt_sym = coin_state.pair.replace("_", "/")

            if level.holding > 0 and level.side == "buy":
                # We hold at this level, place a sell
                level.side = "sell"
                try:
                    qty = level.holding
                    result = self.adapter.create_order(
                        symbol=ccxt_sym,
                        side="sell",
                        order_type="limit",
                        quantity=qty,
                        price=level.sell_price,
                    )
                    level.order_id = str(result.get("id", ""))
                    placed += 1
                    logger.debug("[%s] SELL order at $%.4f, qty=%.6f",
                                 coin_state.symbol, level.sell_price, qty)
                except Exception as e:
                    logger.warning("[%s] Failed to place sell: %s",
                                   coin_state.symbol, e)

            elif level.holding == 0 and level.side == "buy" and buy_allowed:
                # No holding, place a buy if price is above this level
                if current_price > level.price and coin_state.cash > 0:
                    cost = qty_per_level * level.price
                    fee = cost * (self.config.fee_pct / 100)
                    if coin_state.cash >= cost + fee:
                        try:
                            result = self.adapter.create_order(
                                symbol=ccxt_sym,
                                side="buy",
                                order_type="limit",
                                quantity=round(qty_per_level, 8),
                                price=level.price,
                            )
                            level.order_id = str(result.get("id", ""))
                            placed += 1
                            logger.debug("[%s] BUY order at $%.4f, qty=%.6f",
                                         coin_state.symbol, level.price,
                                         qty_per_level)
                        except Exception as e:
                            logger.warning("[%s] Failed to place buy: %s",
                                           coin_state.symbol, e)

        return placed

    def _check_fills(self, coin_state: CoinGridState) -> int:
        """Check which orders have been filled on exchange.

        Returns:
            Number of filled orders detected
        """
        filled = 0
        ccxt_sym = coin_state.pair.replace("_", "/")

        for level in coin_state.levels:
            if level.order_id is None:
                continue

            try:
                order = self.adapter.fetch_order_status(ccxt_sym, level.order_id)
                status = order.get("status", "")

                if status == "closed":
                    # Order was filled
                    filled_price = float(order.get("average", order.get("price", 0)))
                    filled_qty = float(order.get("filled", 0))

                    if level.side == "buy":
                        cost = filled_price * filled_qty
                        fee = cost * (self.config.fee_pct / 100)
                        coin_state.cash -= (cost + fee)
                        level.holding = filled_qty
                        level.side = "sell"
                        coin_state.total_buys += 1
                        coin_state.total_fees += fee
                        logger.info("[%s] BUY FILLED: %.6f @ $%.4f (fee: $%.4f)",
                                    coin_state.symbol, filled_qty, filled_price, fee)

                    elif level.side == "sell":
                        revenue = filled_price * filled_qty
                        fee = revenue * (self.config.fee_pct / 100)
                        profit = revenue - fee - (level.price * filled_qty)
                        coin_state.cash += (revenue - fee)
                        coin_state.total_pnl += profit
                        coin_state.total_sells += 1
                        coin_state.total_fees += fee
                        level.holding = 0.0
                        level.side = "buy"
                        logger.info(
                            "[%s] SELL FILLED: %.6f @ $%.4f (profit: $%.4f)",
                            coin_state.symbol, filled_qty, filled_price, profit)

                    level.order_id = None
                    filled += 1

                elif status == "canceled" or status == "expired":
                    level.order_id = None
                    logger.debug("[%s] Order %s was %s",
                                 coin_state.symbol, level.order_id, status)

            except Exception as e:
                logger.warning("[%s] Error checking order %s: %s",
                               coin_state.symbol, level.order_id, e)

        return filled

    def _check_rebalance(
        self, coin_state: CoinGridState, current_price: float
    ) -> None:
        """Check if price broke out of grid range and rebalance."""
        if not coin_state.levels:
            return

        grid_low = coin_state.levels[0].price
        grid_high = coin_state.levels[-1].sell_price

        if current_price < grid_low * 0.95 or current_price > grid_high * 1.05:
            logger.info(
                "[%s] Price $%.2f broke out of grid [$%.2f-$%.2f] — "
                "REBALANCING", coin_state.symbol, current_price,
                grid_low, grid_high)

            # Cancel all open orders
            self._cancel_all_orders(coin_state)

            # Sell any remaining holdings at market
            for level in coin_state.levels:
                if level.holding > 0:
                    try:
                        ccxt_sym = coin_state.pair.replace("_", "/")
                        self.adapter.create_order(
                            symbol=ccxt_sym,
                            side="sell",
                            order_type="market",
                            quantity=level.holding,
                        )
                        revenue = level.holding * current_price
                        fee = revenue * (self.config.fee_pct / 100)
                        coin_state.cash += (revenue - fee)
                        coin_state.total_fees += fee
                        level.holding = 0.0
                    except Exception as e:
                        logger.error("[%s] Rebalance sell failed: %s",
                                     coin_state.symbol, e)

            # Rebuild grid around new price
            coin_cfg = next(
                (c for c in self.config.coins if c.symbol == coin_state.symbol),
                None,
            )
            if coin_cfg:
                new_state = self._build_grid(
                    coin_cfg, current_price, coin_state.cash
                )
                new_state.total_buys = coin_state.total_buys
                new_state.total_sells = coin_state.total_sells
                new_state.total_fees = coin_state.total_fees
                new_state.total_pnl = coin_state.total_pnl
                new_state.num_rebalances = coin_state.num_rebalances + 1

                assert self._state is not None
                self._state.coins[coin_state.symbol] = new_state
                logger.info("[%s] Grid rebalanced around $%.2f (rebalance #%d)",
                            coin_state.symbol, current_price,
                            new_state.num_rebalances)

    def _cancel_all_orders(self, coin_state: CoinGridState) -> None:
        """Cancel all open orders for a coin."""
        ccxt_sym = coin_state.pair.replace("_", "/")
        for level in coin_state.levels:
            if level.order_id:
                try:
                    self.adapter.cancel_order(ccxt_sym, level.order_id)
                    level.order_id = None
                except Exception as e:
                    logger.warning("[%s] Cancel failed for %s: %s",
                                   coin_state.symbol, level.order_id, e)

    def _reconcile_with_exchange(self) -> None:
        """On startup, reconcile saved state with actual exchange state."""
        assert self._state is not None
        logger.info("Reconciling saved state with exchange...")

        for symbol, coin_state in self._state.coins.items():
            ccxt_sym = coin_state.pair.replace("_", "/")
            try:
                open_orders = self.adapter.fetch_open_orders(ccxt_sym)
                exchange_order_ids = {str(o.get("id", "")) for o in open_orders}

                # Clear order IDs that are no longer on exchange
                for level in coin_state.levels:
                    if level.order_id and level.order_id not in exchange_order_ids:
                        logger.info("[%s] Order %s no longer on exchange — clearing",
                                    symbol, level.order_id)
                        level.order_id = None

                logger.info("[%s] Reconciled: %d exchange orders, %d grid levels",
                            symbol, len(open_orders), len(coin_state.levels))
            except Exception as e:
                logger.warning("[%s] Reconciliation failed: %s", symbol, e)

    def _fetch_price(self, ccxt_symbol: str) -> float | None:
        """Fetch current price from exchange."""
        try:
            ticker = self.adapter.fetch_ticker(ccxt_symbol)
            return float(ticker.get("last", 0))
        except Exception as e:
            logger.warning("Failed to fetch price for %s: %s", ccxt_symbol, e)
            return None

    def _print_summary(self) -> None:
        """Print portfolio summary."""
        assert self._state is not None
        logger.info("─" * 50)
        logger.info("  PORTFOLIO SUMMARY (tick #%d)", self._tick_count)
        logger.info("─" * 50)

        total_pnl = 0.0
        for symbol, cs in self._state.coins.items():
            held_levels = sum(1 for lv in cs.levels if lv.holding > 0)
            total_pnl += cs.total_pnl
            logger.info("  %s: PnL $%+.2f | Cash $%.0f | Held %d/%d | "
                        "Buys %d Sells %d",
                        symbol, cs.total_pnl, cs.cash, held_levels,
                        len(cs.levels), cs.total_buys, cs.total_sells)

        logger.info("  TOTAL PnL: $%+.2f", total_pnl)
        logger.info("─" * 50)

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handle SIGINT/SIGTERM gracefully."""
        logger.info("Shutdown signal received — saving state and stopping...")
        self._running = False

    def _shutdown(self) -> None:
        """Clean shutdown: save state."""
        if self._state is not None:
            save_portfolio_state(self._state)
            logger.info("State saved. Total PnL: $%+.2f",
                        sum(c.total_pnl for c in self._state.coins.values()))
        logger.info("Live grid engine stopped.")
