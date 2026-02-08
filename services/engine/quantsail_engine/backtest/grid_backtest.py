"""Grid trading backtest runner.

Simulates a spot grid trading strategy on historical OHLCV data.
Grid bots place buy/sell orders at fixed price intervals and profit
from price bouncing within a range — ideal for ranging/volatile markets.

Key design: each grid level is a buy↔sell pair. Buy at the level price,
sell one grid spacing above. Profit per cycle = spacing - fees.
"""

import csv
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _r(val: float, ndigits: int = 2) -> float:
    """Round helper to satisfy Pyre2 type checker."""
    return float(round(float(val), ndigits))


@dataclass
class GridLevel:
    """A single price level in the grid.

    Each level represents a buy price. The corresponding sell price
    is always one grid spacing above (level.price + grid_spacing).
    """

    price: float
    sell_price: float = 0.0   # Set during grid build
    holding: bool = False     # We hold inventory bought at this level
    buy_fill_count: int = 0   # Total buys filled at this level
    sell_fill_count: int = 0  # Total sells filled at this level


@dataclass
class GridTrade:
    """Record of a completed grid buy→sell cycle."""

    timestamp: datetime
    buy_price: float
    sell_price: float
    quantity: float
    gross_profit: float
    fee_cost: float
    net_profit: float


@dataclass
class GridMetrics:
    """Summary metrics from a grid backtest."""

    symbol: str
    regime: str  # Market regime label (e.g. "2022_bear")
    period_days: int
    starting_cash: float
    final_cash: float
    total_pnl: float
    total_pnl_pct: float
    total_trades: int          # Completed buy→sell cycles
    total_buys: int
    total_sells: int
    trades_per_day: float
    avg_profit_per_trade: float
    total_fees: float
    num_rebalances: int
    max_drawdown_pct: float
    grid_lower: float
    grid_upper: float
    num_grids: int
    slippage_pct: float = 0.0
    daily_pnl: dict[str, float] = field(default_factory=dict)


class GridBacktestRunner:
    """Simulates grid trading on historical candle data.

    Core algorithm:
    1. Build N grid levels between lower and upper price bounds
    2. For each candle, check which buy levels fall within [low, high]
    3. If price crosses a buy level → fill buy (mark as "holding")
    4. If price crosses the sell level (one spacing above buy) AND
       level is "holding" → fill sell (book profit!)
    5. If price breaks out of range, add a cooldown before rebalancing
       to avoid whipsaw rebalances on temporary wicks
    """

    # Only rebalance if price stays outside range for this many candles
    REBALANCE_COOLDOWN = 6  # 6 hours at 1h timeframe

    def __init__(
        self,
        data_file: str | Path,
        symbol: str,
        allocation_usd: float = 1000.0,
        num_grids: int = 15,
        lower_pct: float = 5.0,
        upper_pct: float = 5.0,
        fee_pct: float = 0.1,
        rebalance_on_breakout: bool = True,
        slippage_pct: float = 0.0,
        regime: str = "current",
    ) -> None:
        self.data_file = Path(data_file)
        self.symbol = symbol
        self.allocation_usd = allocation_usd
        self.num_grids = num_grids
        self.lower_pct = lower_pct
        self.upper_pct = upper_pct
        self.fee_pct = fee_pct / 100.0  # Convert to decimal
        self.rebalance_on_breakout = rebalance_on_breakout
        self.slippage_pct = slippage_pct / 100.0  # e.g. 0.03 -> 0.0003
        self.regime = regime

        # State
        self.cash = allocation_usd
        self.peak_value = allocation_usd
        self.max_drawdown_pct = 0.0
        self.grid_levels: list[GridLevel] = []
        self.trades: list[GridTrade] = []
        self.candles: list[dict] = []
        self.num_rebalances = 0
        self.total_buys = 0
        self.total_sells = 0
        self.total_fees = 0.0
        self.daily_pnl: dict[str, float] = {}
        self._grid_lower = 0.0
        self._grid_upper = 0.0
        self._grid_spacing = 0.0
        self._qty_per_level_val = 0.0

        # Inventory: maps grid level index -> quantity held
        self._inventory: dict[int, float] = {}

        # Rebalance cooldown counter
        self._outside_range_count = 0

        self._load_data()

    def _load_data(self) -> None:
        """Load OHLCV data from CSV."""
        self.candles = []
        with open(self.data_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts_str = row.get("timestamp", row.get("date", ""))
                try:
                    timestamp = datetime.fromisoformat(str(ts_str))
                except (ValueError, TypeError):
                    continue
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                self.candles.append({
                    "timestamp": timestamp,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row.get("volume", 0)),
                })

    def _build_grid(self, reference_price: float) -> None:
        """Build grid levels centered around reference price.

        Grid structure:
        - N+1 price levels from lower to upper
        - Each level i has: buy_price = level[i].price, sell_price = level[i+1].price
        - Levels below current price start with buys armed
        """
        lower = reference_price * (1 - self.lower_pct / 100.0)
        upper = reference_price * (1 + self.upper_pct / 100.0)

        spacing = (upper - lower) / self.num_grids
        self.grid_levels = []
        for i in range(self.num_grids):
            buy_price: float = _r(lower + i * spacing, 8)
            sell_price: float = _r(lower + (i + 1) * spacing, 8)
            self.grid_levels.append(GridLevel(
                price=buy_price,
                sell_price=sell_price,
                holding=False,
            ))

        self._grid_lower = lower
        self._grid_upper = upper
        self._grid_spacing = spacing

        # Fixed quantity per level based on allocation
        # Each level uses allocation / num_grids worth of capital
        mid_price = (lower + upper) / 2
        self._qty_per_level_val = (self.allocation_usd / self.num_grids) / mid_price

        # Initially buy at all levels below current price (simulating entry)
        for i, level in enumerate(self.grid_levels):
            if level.price < reference_price:
                qty = self._qty_per_level_val
                cost = qty * level.price
                fee = cost * self.fee_pct
                if self.cash >= cost + fee:
                    self.cash -= cost + fee
                    self.total_fees += fee
                    level.holding = True
                    self.total_buys += 1
                    self._inventory[i] = qty

        self._outside_range_count = 0

    def _process_tick(self, candle: dict) -> float:
        """Process one candle tick, return net PnL from completed cycles.

        For each candle we check:
        1. Can any pending sells fill? (sell_price within [low, high])
        2. Can any empty levels fill buys? (buy_price within [low, high])
        Direction-aware ordering prevents same-candle double-fills.
        """
        low = candle["low"]
        high = candle["high"]
        close = candle["close"]
        open_price = candle["open"]
        timestamp = candle["timestamp"]
        tick_pnl = 0.0

        # Determine order: bullish → buys first then sells; bearish → sells first
        if close >= open_price:
            tick_pnl += self._process_buys(low, high, timestamp)
            tick_pnl += self._process_sells(low, high, timestamp)
        else:
            tick_pnl += self._process_sells(low, high, timestamp)
            tick_pnl += self._process_buys(low, high, timestamp)

        # Rebalance check with cooldown to avoid whipsaw
        if self.rebalance_on_breakout:
            if close < self._grid_lower or close > self._grid_upper:
                self._outside_range_count += 1
                if self._outside_range_count >= self.REBALANCE_COOLDOWN:
                    tick_pnl += self._rebalance_grid(close)
            else:
                self._outside_range_count = 0

        # Track portfolio drawdown
        inventory_value = sum(
            qty * close for qty in self._inventory.values()
        )
        portfolio_value = self.cash + inventory_value
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value
        if self.peak_value > 0:
            dd = (self.peak_value - portfolio_value) / self.peak_value * 100
            if dd > self.max_drawdown_pct:
                self.max_drawdown_pct = dd

        return tick_pnl

    def _process_buys(self, low: float, high: float, timestamp: datetime) -> float:
        """Fill buy orders at grid levels within the candle's range."""
        for i, level in enumerate(self.grid_levels):
            if not level.holding and low <= level.price <= high:
                # Apply slippage: buy fills slightly HIGHER (worse for us)
                slip: float = random.uniform(0, self.slippage_pct) if self.slippage_pct > 0 else 0.0
                fill_price: float = level.price * (1.0 + slip)

                qty = self._qty_per_level_val
                cost: float = qty * fill_price
                fee: float = cost * self.fee_pct

                if self.cash >= cost + fee:
                    self.cash -= cost + fee
                    self.total_fees += fee
                    level.holding = True
                    level.buy_fill_count += 1
                    self.total_buys += 1
                    self._inventory[i] = qty
        return 0.0  # Buys don't generate PnL

    def _process_sells(self, low: float, high: float, timestamp: datetime) -> float:
        """Fill sell orders at levels that are holding inventory."""
        pnl: float = 0.0
        levels = self.grid_levels
        inv = self._inventory
        for i, level in enumerate(levels):
            if level.holding and low <= level.sell_price <= high:
                qty: float = inv.get(i, 0.0)
                if qty <= 0:
                    continue

                # Apply slippage: sell fills slightly LOWER (worse for us)
                slip: float = random.uniform(0, self.slippage_pct) if self.slippage_pct > 0 else 0.0
                fill_price: float = level.sell_price * (1.0 - slip)

                revenue: float = qty * fill_price
                sell_fee: float = revenue * self.fee_pct
                buy_cost: float = qty * level.price
                buy_fee: float = buy_cost * self.fee_pct  # Fee already paid

                gross_profit: float = revenue - buy_cost
                net_profit: float = gross_profit - sell_fee

                self.cash += revenue - sell_fee
                self.total_fees += sell_fee
                self.total_sells += 1
                level.holding = False
                level.sell_fill_count += 1
                inv.pop(i, 0.0)

                self.trades.append(GridTrade(
                    timestamp=timestamp,
                    buy_price=level.price,
                    sell_price=level.sell_price,
                    quantity=qty,
                    gross_profit=gross_profit,
                    fee_cost=buy_fee + sell_fee,
                    net_profit=net_profit,
                ))
                pnl = pnl + net_profit
        return pnl

    def _rebalance_grid(self, current_price: float) -> float:
        """Shift grid to center on current price after sustained breakout.

        Returns PnL from liquidating inventory (may be negative).
        """
        rebal_pnl = 0.0

        # Sell all inventory at current market price
        for i, qty in list(self._inventory.items()):
            level = self.grid_levels[i]
            revenue = qty * current_price
            sell_fee = revenue * self.fee_pct
            buy_cost = qty * level.price
            rebal_pnl += (revenue - sell_fee) - (buy_cost)
            # No need to subtract buy_fee again — was already deducted
            self.cash += revenue - sell_fee
            self.total_fees += sell_fee
            self.total_sells += 1

        self._inventory.clear()
        self.num_rebalances += 1

        # Rebuild grid around new price
        self._build_grid(current_price)
        return rebal_pnl

    def run(self) -> GridMetrics:
        """Run the grid backtest.

        Returns:
            GridMetrics with performance results.
        """
        if not self.candles:
            raise ValueError("No candle data loaded")

        # Build initial grid from first candle's close
        first_close = self.candles[0]["close"]
        self._build_grid(first_close)

        print(f"📊 Grid Backtest: {self.symbol}")
        print(f"   Data: {self.data_file.name} ({len(self.candles)} candles)")
        print(f"   Allocation: ${self.allocation_usd:.0f}")
        print(f"   Grid: {self.num_grids} levels, "
              f"range ±{self.lower_pct}/{self.upper_pct}%")
        print(f"   Spacing: ${self._grid_spacing:.2f} "
              f"({self._grid_spacing / first_close * 100:.3f}%)")
        print(f"   Fee: {self.fee_pct*100:.2f}% per side")

        # Process each candle
        for i, candle in enumerate(self.candles):
            tick_pnl = self._process_tick(candle)

            # Track daily PnL
            day_key = candle["timestamp"].strftime("%Y-%m-%d")
            self.daily_pnl[day_key] = self.daily_pnl.get(day_key, 0) + tick_pnl

            if (i + 1) % 2000 == 0:
                inv_count = len(self._inventory)
                print(f"   Tick {i+1}/{len(self.candles)}: "
                      f"cycles={len(self.trades)}, inv={inv_count}, "
                      f"cash=${self.cash:.2f}")

        # Final: sell remaining inventory at last close
        last_close = self.candles[-1]["close"]
        for i, qty in list(self._inventory.items()):
            revenue = qty * last_close
            fee = revenue * self.fee_pct
            self.cash += revenue - fee
            self.total_fees += fee
        self._inventory.clear()

        # Calculate metrics
        total_pnl = self.cash - self.allocation_usd
        first_ts = self.candles[0]["timestamp"]
        last_ts = self.candles[-1]["timestamp"]
        period_days = max((last_ts - first_ts).days, 1)

        avg_ppt: float = (
            float(total_pnl) / len(self.trades) if self.trades else 0.0
        )
        metrics = GridMetrics(
            symbol=self.symbol,
            regime=self.regime,
            period_days=period_days,
            starting_cash=self.allocation_usd,
            final_cash=_r(self.cash),
            total_pnl=_r(total_pnl),
            total_pnl_pct=_r(float(total_pnl) / self.allocation_usd * 100),
            total_trades=len(self.trades),
            total_buys=self.total_buys,
            total_sells=self.total_sells,
            trades_per_day=_r(len(self.trades) / period_days),
            avg_profit_per_trade=_r(avg_ppt, 4),
            total_fees=_r(self.total_fees),
            num_rebalances=self.num_rebalances,
            max_drawdown_pct=_r(self.max_drawdown_pct),
            grid_lower=_r(self._grid_lower),
            grid_upper=_r(self._grid_upper),
            num_grids=self.num_grids,
            slippage_pct=_r(self.slippage_pct * 100),
            daily_pnl=self.daily_pnl,
        )

        print(f"\n✅ Grid Backtest Complete: {self.symbol}")
        print(f"   Total Cycles: {metrics.total_trades} "
              f"({metrics.trades_per_day}/day)")
        print(f"   Buys: {metrics.total_buys}  Sells: {metrics.total_sells}")
        print(f"   PnL: ${metrics.total_pnl:+.2f} "
              f"({metrics.total_pnl_pct:+.2f}%)")
        print(f"   Avg/cycle: ${metrics.avg_profit_per_trade:.4f}")
        print(f"   Fees: ${metrics.total_fees:.2f}")
        print(f"   Rebalances: {metrics.num_rebalances}")
        print(f"   Max Drawdown: {metrics.max_drawdown_pct:.2f}%")

        return metrics
