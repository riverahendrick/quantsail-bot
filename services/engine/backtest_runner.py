"""
Professional Backtest Runner for Quantsail Engine.
Executes the production TradingLoop against historical data for multiple assets.
"""

import argparse
import logging
import sys
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, patch
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent))

from quantsail_engine.config.models import BotConfig, ExecutionConfig, RiskConfig, SymbolsConfig, DailyConfig, BreakerConfig
from quantsail_engine.core.trading_loop import TradingLoop
from quantsail_engine.execution.executor import ExecutionEngine
from quantsail_engine.market_data.provider import MarketDataProvider
from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.trade_plan import TradePlan
from quantsail_engine.signals.provider import SignalProvider
from quantsail_engine.strategies.ensemble import EnsembleCombiner
from quantsail_engine.signals.provider import SignalProvider
from quantsail_engine.persistence.stub_models import Base

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BacktestRunner")

# Global simulation time
_sim_time = datetime.min.replace(tzinfo=timezone.utc)

class MockDatetime(datetime):
    """Mock datetime class that returns simulated time."""
    @classmethod
    def now(cls, tz=None):
        if tz:
            return _sim_time.astimezone(tz)
        return _sim_time

class BacktestSignalProvider(SignalProvider):
    """Concrete signal provider for backtesting using EnsembleCombiner."""
    
    def __init__(self, config: BotConfig):
        self.combiner = EnsembleCombiner()
        self.config = config
        
    def generate_signal(self, symbol: str, candles: list[Candle], orderbook: Orderbook) -> Any:
        return self.combiner.analyze(symbol, candles, orderbook, self.config)

class BacktestMarketProvider(MarketDataProvider):
    """
    Simulates market data for multiple symbols.
    """

    def __init__(self, data_map: Dict[str, pd.DataFrame]):
        """
        Args:
            data_map: Dict mapping symbol to DataFrame (OHLCV).
                      DataFrames must have 'timestamp' column (datetime, UTC).
        """
        self.data_map = {
            k: v.sort_values("timestamp").reset_index(drop=True) 
            for k, v in data_map.items()
        }
        # Current index per symbol
        self.indices = {k: 0 for k in data_map.keys()}
        self.current_time = datetime.min.replace(tzinfo=timezone.utc)

    def set_time(self, timestamp: datetime) -> None:
        """Update the simulated current time."""
        self.current_time = timestamp
        # Update indices efficiently
        for symbol, df in self.data_map.items():
            curr_idx = self.indices[symbol]
            # Advance index until we pass current_time
            # Stop at the last candle that is <= current_time
            while (curr_idx + 1 < len(df) and 
                   df.iloc[curr_idx + 1]["timestamp"] <= self.current_time):
                curr_idx += 1
            self.indices[symbol] = curr_idx

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        """Return candles up to current_time."""
        if symbol not in self.data_map:
            return []
            
        df = self.data_map[symbol]
        idx = self.indices[symbol]
        
        # Ensure we don't look ahead (idx is already set to <= current_time)
        # Verify the candle at idx is actually valid for this time (e.g. not too old)
        # For simplicity, we assume continuous data or gap handling by strategy
        
        start_idx = max(0, idx - limit + 1)
        slice_df = df.iloc[start_idx : idx + 1]
        
        candles = []
        for _, row in slice_df.iterrows():
            candles.append(Candle(
                timestamp=row["timestamp"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"]
            ))
        return candles

    def get_orderbook(self, symbol: str, depth_levels: int) -> Orderbook:
        """Simulate orderbook based on current close price."""
        if symbol not in self.data_map:
             # Return dummy if no data (should not happen if configured correctly)
             return Orderbook(bids=[(0.0, 0.0)], asks=[(float('inf'), 0.0)])

        df = self.data_map[symbol]
        idx = self.indices[symbol]
        current_candle = df.iloc[idx]
        price = current_candle["close"]
        
        # Simulate 0.05% spread (typical for majors)
        spread = price * 0.0005
        best_bid = price - (spread / 2)
        best_ask = price + (spread / 2)
        
        bids = [(best_bid * (1 - i*0.0001), 1.0) for i in range(depth_levels)]
        asks = [(best_ask * (1 + i*0.0001), 1.0) for i in range(depth_levels)]
        
        return Orderbook(bids=bids, asks=asks)

class BacktestExecutor(ExecutionEngine):
    """
    Simulates trade execution with slippage and fees.
    """
    def __init__(self, slippage_pct: float, fee_pct: float):
        self.slippage_pct = slippage_pct
        self.fee_pct = fee_pct
        self.trades = {} # id -> trade dict
        self.mock_time = datetime.min.replace(tzinfo=timezone.utc)

    def set_time(self, timestamp: datetime):
        self.mock_time = timestamp

    def execute_entry(self, plan: TradePlan) -> dict[str, Any] | None:
        """Simulate entry execution."""
        filled_price = plan.entry_price * (1 + self.slippage_pct)
        filled_qty = plan.quantity
        
        fee_usd = filled_price * filled_qty * self.fee_pct
        
        trade_id = plan.trade_id
        
        trade = {
            "id": trade_id,
            "symbol": plan.symbol,
            "mode": "BACKTEST",
            "status": "OPEN",
            "side": plan.side,
            "entry_price": filled_price,
            "quantity": filled_qty,
            "opened_at": self.mock_time,
            "stop_price": plan.stop_loss_price,
            "take_profit_price": plan.take_profit_price,
            "trailing_enabled": False,
            "trailing_offset": None,
            "fees_paid_usd": fee_usd
        }
        
        order = {
            "id": str(uuid.uuid4()),
            "trade_id": trade_id,
            "symbol": plan.symbol,
            "side": plan.side,
            "order_type": "MARKET",
            "status": "FILLED",
            "quantity": filled_qty,
            "price": plan.entry_price,
            "filled_price": filled_price,
            "filled_qty": filled_qty,
            "filled_at": self.mock_time,
            "created_at": self.mock_time
        }
        
        self.trades[trade_id] = trade
        print(f"DEBUG: Generated Order ID: {order['id']}")
        return {"trade": trade, "orders": [order]}

    def check_exits(self, trade_id: str, current_price: float) -> dict[str, Any] | None:
        """Check if SL or TP is hit."""
        trade = self.trades.get(trade_id)
        if not trade or trade["status"] != "OPEN":
            return None
            
        exit_reason = None
        if current_price <= trade["stop_price"]:
            exit_reason = "STOP_LOSS"
        elif current_price >= trade["take_profit_price"]:
            exit_reason = "TAKE_PROFIT"
            
        if exit_reason:
            filled_price = current_price * (1 - self.slippage_pct)
            fee_usd = filled_price * trade["quantity"] * self.fee_pct
            
            pnl_usd = (filled_price - trade["entry_price"]) * trade["quantity"] - trade.get("fees_paid_usd", 0) - fee_usd
            pnl_pct = (pnl_usd / (trade["entry_price"] * trade["quantity"])) * 100
            
            trade["status"] = "CLOSED"
            trade["closed_at"] = self.mock_time
            trade["exit_price"] = filled_price
            trade["realized_pnl_usd"] = pnl_usd
            trade["pnl_pct"] = pnl_pct
            
            exit_order = {
                "id": str(uuid.uuid4()),
                "trade_id": trade_id,
                "symbol": trade["symbol"],
                "side": "SELL",
                "order_type": "MARKET",
                "status": "FILLED",
                "quantity": trade["quantity"],
                "price": current_price,
                "filled_price": filled_price,
                "filled_qty": trade["quantity"],
                "filled_at": self.mock_time,
                "created_at": self.mock_time
            }
            
            return {
                "trade": trade,
                "exit_order": exit_order,
                "exit_reason": exit_reason
            }
            
        return None
        
    def reconcile_state(self, open_trades: list[Any]) -> None:
        pass

def run_backtest(data_dir: str, starting_cash: float, fee_pct: float, slippage_pct: float):
    """
    Run the multi-asset backtest.
    """
    print(f"🚀 Starting Backtest with data from: {data_dir}")
    print(f"   Budget: ${starting_cash:,.2f}")
    
    # 1. Load Data for Multiple Assets
    data_map = {}
    symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT"]
    all_timestamps = set()
    
    for symbol in symbols:
        # Expected filename format: SYMBOL_USDT_1m_ohlcv.csv (sanitized)
        safe_symbol = symbol.replace("/", "_")
        path = Path(data_dir) / f"{safe_symbol}_1m_ohlcv.csv"
        
        if path.exists():
            print(f"   Loading {symbol}...")
            df = pd.read_csv(path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            # Ensure UTC
            if df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize(timezone.utc)
            else:
                df['timestamp'] = df['timestamp'].dt.tz_convert(timezone.utc)
            
            data_map[symbol] = df
            all_timestamps.update(df['timestamp'].tolist())
        else:
            print(f"⚠️ Warning: Data for {symbol} not found at {path}. Skipping.")
    
    if not data_map:
        print("❌ No data loaded. Exiting.")
        return

    # Create master timeline (sorted unique timestamps)
    timeline = sorted(list(all_timestamps))
    print(f"📅 Simulation Span: {timeline[0]} to {timeline[-1]}")
    print(f"⏱️  Total Ticks: {len(timeline)}")

    # 2. Setup Config
    config = BotConfig(
        execution=ExecutionConfig(mode="dry-run", taker_fee_bps=int(fee_pct*10000)),
        risk=RiskConfig(starting_cash_usd=starting_cash),
        symbols=SymbolsConfig(enabled=list(data_map.keys()), max_concurrent_positions=5),
        daily=DailyConfig(enabled=True, target_usd=2.0, mode="OVERDRIVE"), # $2 Target per day
        breakers=BreakerConfig()
    )
    
    # 3. Setup Components
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    market_provider = BacktestMarketProvider(data_map)
    executor = BacktestExecutor(slippage_pct=slippage_pct, fee_pct=fee_pct)
    signal_provider = BacktestSignalProvider(config)

    loop = TradingLoop(config, session, market_provider, signal_provider, executor)
    
    # 4. Run Loop
    stats = {"daily_pnl": {}}
    
    # Patch datetime.now used in various modules using MockDatetime class
    # We patch the class itself so isinstance() works (returns False for real datetimes but no TypeError)
    with (
        patch('quantsail_engine.core.trading_loop.datetime', MockDatetime),
        patch('quantsail_engine.persistence.repository.datetime', MockDatetime),
        patch('quantsail_engine.breakers.manager.datetime', MockDatetime)
    ):
        
        print("⏳ Processing ticks...")
        
        last_day = None
        
        for i, ts in enumerate(timeline):
            global _sim_time
            ts_pydatetime = ts.to_pydatetime()
            _sim_time = ts_pydatetime
            
            # Update Market Data
            market_provider.set_time(ts_pydatetime)
            executor.set_time(ts_pydatetime)
            
            # Execute Tick
            try:
                loop.tick()
            except Exception as e:
                logger.error(f"Error at {ts}: {e}", exc_info=True)
                break
                
            # Track Daily PnL
            current_day = ts_pydatetime.date()
            if current_day != last_day:
                if last_day:
                    pnl = loop.repo.get_today_realized_pnl() # Gets PnL for "today" (which is now current_day in mock)
                    # Wait, repo.get_today_realized_pnl uses datetime.now() which is mocked to ts.
                    # So if we just crossed midnight, "today" is the NEW day.
                    # We want stats for the *previous* day.
                    # We can store cumulative equity and diff it.
                    pass
                last_day = current_day
                
            if i % 1000 == 0:
                print(f"   {i}/{len(timeline)} ({i/len(timeline)*100:.1f}%) - Equity: ${loop.repo.calculate_equity(starting_cash):.2f}")

    # 5. Final Report
    final_equity = loop.repo.calculate_equity(starting_cash)
    net_profit = final_equity - starting_cash
    
    print("\n" + "="*40)
    print("📊 MULTI-ASSET BACKTEST RESULTS")
    print("="*40)
    print(f"Assets:         {', '.join(data_map.keys())}")
    print(f"Start Cash:     ${starting_cash:,.2f}")
    print(f"Final Equity:   ${final_equity:,.2f}")
    print(f"Net Profit:     ${net_profit:,.2f} ({(net_profit/starting_cash)*100:+.2f}%)")
    
    # Daily breakdown
    # Can query DB for closed trades grouped by day
    trades = loop.repo.get_recent_closed_trades(10000)
    daily_stats = {}
    
    for t in trades:
        date_str = t['closed_at'].date().isoformat()
        daily_stats[date_str] = daily_stats.get(date_str, 0.0) + t['realized_pnl_usd']
        
    print("\n📅 Daily Profit Analysis:")
    days_met_target = 0
    total_days = len(daily_stats) if daily_stats else 1
    
    for date, pnl in sorted(daily_stats.items()):
        status = "✅" if pnl >= 1.0 else "⚠️" if pnl > 0 else "❌"
        if pnl >= 1.0: days_met_target += 1
        print(f"  {date}: ${pnl:6.2f} {status}")
        
    avg_daily = net_profit / total_days
    print(f"\nAverage Daily PnL: ${avg_daily:.2f}")
    print(f"Days Meeting $1 Target: {days_met_target}/{total_days}")
    print("="*40)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data", help="Directory containing CSV files")
    parser.add_argument("--cash", type=float, default=1000.0, help="Starting cash ($1000-$5000)")
    parser.add_argument("--fee", type=float, default=0.001, help="Fee pct")
    parser.add_argument("--slippage", type=float, default=0.0005, help="Slippage pct")
    
    args = parser.parse_args()
    run_backtest(args.data_dir, args.cash, args.fee, args.slippage)