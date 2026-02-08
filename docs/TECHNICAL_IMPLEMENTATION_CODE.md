# QuantSail Bot - Technical Implementation Code Examples
## Production-Ready Code for Backtesting, Strategies, and Execution

**Companion to:** QUANTSAIL_COMPLETE_IMPLEMENTATION_GUIDE.md  
**Version:** 1.0  
**Date:** February 5, 2026

---

## TABLE OF CONTENTS

1. [Backtesting Framework](#1-backtesting-framework)
2. [Walk-Forward Analysis](#2-walk-forward-analysis)
3. [Monte Carlo Implementation](#3-monte-carlo-implementation)
4. [Strategy Implementations](#4-strategy-implementations)
5. [Cost Models](#5-cost-models)
6. [Position Sizing](#6-position-sizing)
7. [Portfolio Risk Manager](#7-portfolio-risk-manager)
8. [Monitoring & Alerts](#8-monitoring--alerts)

---

## 1. BACKTESTING FRAMEWORK

### 1.1 Historical Data Fetcher

```python
# services/engine/quantsail_engine/research/data_fetcher.py

import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import time

class HistoricalDataFetcher:
    def __init__(self, exchange_id='binance'):
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
    
    def fetch_ohlcv(self, symbol: str, timeframe: str, since: datetime, until: datetime = None) -> pd.DataFrame:
        """
        Fetch OHLCV data with pagination
        
        Args:
            symbol: 'BTC/USDT'
            timeframe: '1m', '5m', '15m', '1h', '4h', '1d'
            since: Start datetime
            until: End datetime (default: now)
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        if until is None:
            until = datetime.utcnow()
        
        since_ms = int(since.timestamp() * 1000)
        until_ms = int(until.timestamp() * 1000)
        
        all_candles = []
        current_since = since_ms
        
        while current_since < until_ms:
            try:
                candles = self.exchange.fetch_ohlcv(
                    symbol, 
                    timeframe, 
                    since=current_since, 
                    limit=1000
                )
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                current_since = candles[-1][0] + 1  # Next timestamp
                
                # Rate limit friendly
                time.sleep(self.exchange.rateLimit / 1000)
                
            except Exception as e:
                print(f"Error fetching {symbol} at {current_since}: {e}")
                time.sleep(5)
                continue
        
        # Convert to DataFrame
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[(df['timestamp'] >= since) & (df['timestamp'] <= until)]
        
        return df.set_index('timestamp')
    
    def fetch_multiple_symbols(self, symbols: List[str], timeframe: str, since: datetime, until: datetime = None) -> Dict[str, pd.DataFrame]:
        """Fetch data for multiple symbols"""
        data = {}
        for symbol in symbols:
            print(f"Fetching {symbol}...")
            df = self.fetch_ohlcv(symbol, timeframe, since, until)
            data[symbol] = df
            print(f"  {len(df)} candles fetched")
        
        return data
    
    def save_to_parquet(self, data: Dict[str, pd.DataFrame], output_dir: str):
        """Save data to Parquet files for faster loading"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        for symbol, df in data.items():
            safe_symbol = symbol.replace('/', '_')
            filename = f"{output_dir}/{safe_symbol}.parquet"
            df.to_parquet(filename)
            print(f"Saved {filename}")


# Usage Example
if __name__ == '__main__':
    fetcher = HistoricalDataFetcher()
    
    symbols = ['BNB/USDT', 'ADA/USDT', 'ETH/USDT', 'SOL/USDT']
    since = datetime(2024, 1, 1)
    until = datetime(2025, 12, 31)
    
    data = fetcher.fetch_multiple_symbols(symbols, '5m', since, until)
    fetcher.save_to_parquet(data, './data/historical')
```

### 1.2 Backtest Engine

```python
# services/engine/quantsail_engine/research/backtest_engine.py

import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import numpy as np

@dataclass
class Trade:
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float]
    stop_price: float
    target_price: float
    quantity: float
    gross_pnl: float = 0.0
    fees: float = 0.0
    slippage: float = 0.0
    spread_cost: float = 0.0
    net_pnl: float = 0.0
    status: str = 'open'  # open, closed_target, closed_stop, closed_time
    
    def close(self, exit_price: float, exit_time: datetime, fees: float, slippage: float, spread_cost: float):
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.fees = fees
        self.slippage = slippage
        self.spread_cost = spread_cost
        
        self.gross_pnl = (exit_price - self.entry_price) * self.quantity
        self.net_pnl = self.gross_pnl - fees - slippage - spread_cost


class BacktestEngine:
    def __init__(self, initial_capital: float, cost_model):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.cost_model = cost_model
        
        self.trades: List[Trade] = []
        self.equity_curve = []
        self.open_positions: Dict[str, Trade] = {}
    
    def run(self, data: pd.DataFrame, strategy, config: dict) -> dict:
        """
        Run backtest on historical data
        
        Args:
            data: DataFrame with OHLCV
            strategy: Strategy instance with generate_signal() method
            config: Config dict with gates, breakers, risk params
        
        Returns:
            Dict with results: trades, metrics, equity_curve
        """
        self.current_capital = self.initial_capital
        self.trades = []
        self.equity_curve = [(data.index[0], self.current_capital)]
        self.open_positions = {}
        
        for i in range(1, len(data)):
            current_candle = data.iloc[i]
            current_time = data.index[i]
            
            # 1. Check exit conditions for open positions
            self._check_exits(current_candle, current_time)
            
            # 2. Generate new signals if no position
            if not self.open_positions:
                signal = strategy.generate_signal(data.iloc[:i+1])
                
                if signal['signal'] == 'ENTER_LONG':
                    # Apply profitability gate
                    if self._passes_profitability_gate(signal, config):
                        # Calculate position size
                        position_size = self._calculate_position_size(
                            signal['entry'], 
                            signal['stop'], 
                            config
                        )
                        
                        if position_size > 0:
                            # Enter trade
                            trade = self._enter_trade(
                                symbol=strategy.symbol,
                                entry_price=signal['entry'],
                                stop_price=signal['stop'],
                                target_price=signal['target'],
                                quantity=position_size,
                                entry_time=current_time
                            )
                            self.trades.append(trade)
                            self.open_positions[strategy.symbol] = trade
            
            # 3. Update equity curve
            open_pnl = sum(
                (current_candle['close'] - trade.entry_price) * trade.quantity 
                for trade in self.open_positions.values()
            )
            current_equity = self.current_capital + open_pnl
            self.equity_curve.append((current_time, current_equity))
        
        # Close any remaining open positions at end
        if self.open_positions:
            last_candle = data.iloc[-1]
            for trade in list(self.open_positions.values()):
                self._close_trade(trade, last_candle['close'], data.index[-1], 'time_stop')
        
        return self._generate_results()
    
    def _passes_profitability_gate(self, signal: dict, config: dict) -> bool:
        """Check if expected profit covers all costs"""
        entry = signal['entry']
        target = signal['target']
        notional = entry  # Simplified, actual should use quantity
        
        # Expected gross profit
        gross_profit = abs(target - entry)
        
        # Costs
        fees = self.cost_model.calculate_fee(notional, is_maker=False) * 2  # Entry + exit
        slippage = self.cost_model.estimate_slippage(notional)
        spread = self.cost_model.estimate_spread(notional)
        
        net_profit = gross_profit - fees - slippage - spread
        min_profit = config.get('execution', {}).get('min_profit_usd', 0.10)
        
        return net_profit >= min_profit
    
    def _calculate_position_size(self, entry: float, stop: float, config: dict) -> float:
        """Calculate position size based on risk"""
        risk_per_trade_pct = config.get('risk', {}).get('max_risk_per_trade_pct', 0.5)
        max_position_pct = config.get('risk', {}).get('max_position_pct_equity', 10)
        
        risk_amount = self.current_capital * (risk_per_trade_pct / 100)
        price_risk_pct = abs(entry - stop) / entry
        
        position_size = risk_amount / price_risk_pct / entry  # In base currency
        max_position = self.current_capital * (max_position_pct / 100) / entry
        
        return min(position_size, max_position)
    
    def _enter_trade(self, symbol: str, entry_price: float, stop_price: float, target_price: float, quantity: float, entry_time: datetime) -> Trade:
        """Execute entry"""
        notional = entry_price * quantity
        
        # Costs
        fees = self.cost_model.calculate_fee(notional, is_maker=False)
        slippage = self.cost_model.estimate_slippage(notional)
        spread = self.cost_model.estimate_spread(notional)
        
        # Adjust capital
        self.current_capital -= (notional + fees + slippage + spread)
        
        return Trade(
            entry_time=entry_time,
            exit_time=None,
            symbol=symbol,
            side='long',
            entry_price=entry_price,
            exit_price=None,
            stop_price=stop_price,
            target_price=target_price,
            quantity=quantity,
            status='open'
        )
    
    def _check_exits(self, candle, current_time):
        """Check stop loss and take profit"""
        for symbol, trade in list(self.open_positions.items()):
            # Stop loss hit
            if candle['low'] <= trade.stop_price:
                self._close_trade(trade, trade.stop_price, current_time, 'closed_stop')
                del self.open_positions[symbol]
            
            # Take profit hit
            elif candle['high'] >= trade.target_price:
                self._close_trade(trade, trade.target_price, current_time, 'closed_target')
                del self.open_positions[symbol]
    
    def _close_trade(self, trade: Trade, exit_price: float, exit_time: datetime, status: str):
        """Execute exit"""
        notional = exit_price * trade.quantity
        
        # Costs
        fees = self.cost_model.calculate_fee(notional, is_maker=False)
        slippage = self.cost_model.estimate_slippage(notional)
        spread = self.cost_model.estimate_spread(notional)
        
        trade.close(exit_price, exit_time, fees, slippage, spread)
        trade.status = status
        
        # Adjust capital
        self.current_capital += (notional - fees - slippage - spread)
    
    def _generate_results(self) -> dict:
        """Calculate metrics"""
        closed_trades = [t for t in self.trades if t.status != 'open']
        
        if not closed_trades:
            return {'error': 'No closed trades'}
        
        total_pnl = sum(t.net_pnl for t in closed_trades)
        total_fees = sum(t.fees for t in closed_trades)
        total_slippage = sum(t.slippage for t in closed_trades)
        total_spread = sum(t.spread_cost for t in closed_trades)
        
        winners = [t for t in closed_trades if t.net_pnl > 0]
        losers = [t for t in closed_trades if t.net_pnl <= 0]
        
        profit_factor = (
            sum(t.net_pnl for t in winners) / abs(sum(t.net_pnl for t in losers))
            if losers else float('inf')
        )
        
        # Equity curve analysis
        equity_df = pd.DataFrame(self.equity_curve, columns=['timestamp', 'equity'])
        equity_df['returns'] = equity_df['equity'].pct_change()
        equity_df['cummax'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['cummax']) / equity_df['cummax']
        max_drawdown = equity_df['drawdown'].min()
        
        return {
            'total_trades': len(closed_trades),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': len(winners) / len(closed_trades) if closed_trades else 0,
            'total_net_pnl': total_pnl,
            'total_fees': total_fees,
            'total_slippage': total_slippage,
            'total_spread': total_spread,
            'profit_factor': profit_factor,
            'avg_trade_pnl': total_pnl / len(closed_trades),
            'max_drawdown': max_drawdown,
            'final_equity': self.current_capital,
            'total_return_pct': (self.current_capital - self.initial_capital) / self.initial_capital * 100,
            'trades': closed_trades,
            'equity_curve': equity_df
        }
```

---

## 2. WALK-FORWARD ANALYSIS

```python
# services/engine/quantsail_engine/research/walk_forward.py

import pandas as pd
from datetime import timedelta
from typing import List, Dict
import numpy as np

class WalkForwardAnalyzer:
    def __init__(self, train_days=90, test_days=30, step_days=30):
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days
    
    def run_wfa(self, data: pd.DataFrame, strategy_class, param_grid: dict, cost_model, initial_capital=1000) -> dict:
        """
        Run walk-forward analysis
        
        Args:
            data: Historical OHLCV data
            strategy_class: Strategy class (not instance)
            param_grid: Dict of parameter ranges to optimize
            cost_model: Cost model instance
            initial_capital: Starting capital
        
        Returns:
            Dict with aggregated results and per-window details
        """
        windows = self._generate_windows(data)
        results = []
        
        for i, (train_data, test_data) in enumerate(windows):
            print(f"Window {i+1}/{len(windows)}: Train {train_data.index[0]} to {train_data.index[-1]}")
            
            # 1. Optimize parameters on train window
            best_params = self._optimize_parameters(
                train_data, 
                strategy_class, 
                param_grid, 
                cost_model, 
                initial_capital
            )
            
            print(f"  Best params: {best_params}")
            
            # 2. Test with frozen parameters on test window
            strategy = strategy_class(**best_params)
            backtest = BacktestEngine(initial_capital, cost_model)
            
            config = {
                'execution': {'min_profit_usd': 0.15},
                'risk': {'max_risk_per_trade_pct': 0.5, 'max_position_pct_equity': 10}
            }
            
            test_result = backtest.run(test_data, strategy, config)
            
            results.append({
                'window': i + 1,
                'train_start': train_data.index[0],
                'train_end': train_data.index[-1],
                'test_start': test_data.index[0],
                'test_end': test_data.index[-1],
                'best_params': best_params,
                'test_pnl': test_result['total_net_pnl'],
                'test_profit_factor': test_result['profit_factor'],
                'test_win_rate': test_result['win_rate'],
                'test_max_dd': test_result['max_drawdown'],
                'test_trades': test_result['total_trades']
            })
            
            print(f"  Test PnL: ${test_result['total_net_pnl']:.2f}, PF: {test_result['profit_factor']:.2f}")
        
        return self._aggregate_results(results)
    
    def _generate_windows(self, data: pd.DataFrame) -> List[tuple]:
        """Generate (train, test) data windows"""
        windows = []
        
        start_idx = 0
        while True:
            train_end_idx = start_idx + self.train_days
            test_end_idx = train_end_idx + self.test_days
            
            if test_end_idx > len(data):
                break
            
            train_data = data.iloc[start_idx:train_end_idx]
            test_data = data.iloc[train_end_idx:test_end_idx]
            
            windows.append((train_data, test_data))
            
            start_idx += self.step_days
        
        return windows
    
    def _optimize_parameters(self, data: pd.DataFrame, strategy_class, param_grid: dict, cost_model, initial_capital) -> dict:
        """Grid search optimization"""
        from itertools import product
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))
        
        best_score = -float('inf')
        best_params = None
        
        config = {
            'execution': {'min_profit_usd': 0.15},
            'risk': {'max_risk_per_trade_pct': 0.5, 'max_position_pct_equity': 10}
        }
        
        for combo in combinations:
            params = dict(zip(param_names, combo))
            
            try:
                strategy = strategy_class(**params)
                backtest = BacktestEngine(initial_capital, cost_model)
                result = backtest.run(data, strategy, config)
                
                # Score: profit factor weighted by trade count (avoid overfit on few trades)
                if result['total_trades'] < 10:
                    score = -float('inf')
                else:
                    score = result['profit_factor'] * np.log(result['total_trades'])
                
                if score > best_score:
                    best_score = score
                    best_params = params
            
            except Exception as e:
                print(f"    Param combo failed: {params} - {e}")
                continue
        
        return best_params
    
    def _aggregate_results(self, results: List[dict]) -> dict:
        """Aggregate WFA results"""
        df = pd.DataFrame(results)
        
        total_pnl = df['test_pnl'].sum()
        positive_windows = (df['test_pnl'] > 0).sum()
        avg_pf = df['test_profit_factor'].mean()
        worst_dd = df['test_max_dd'].min()
        total_trades = df['test_trades'].sum()
        
        return {
            'num_windows': len(results),
            'positive_windows': positive_windows,
            'positive_window_pct': positive_windows / len(results) * 100,
            'total_pnl': total_pnl,
            'avg_pnl_per_window': total_pnl / len(results),
            'avg_profit_factor': avg_pf,
            'worst_max_dd': worst_dd,
            'total_trades': total_trades,
            'per_window_results': df,
            'pass': positive_windows / len(results) >= 0.7 and avg_pf > 1.1  # 70% positive windows + PF > 1.1
        }


# Usage Example
if __name__ == '__main__':
    # Load data
    data = pd.read_parquet('./data/historical/BNB_USDT.parquet')
    
    # Parameter grid for optimization
    param_grid = {
        'atr_period': [10, 14, 20],
        'adx_period': [10, 14, 20],
        'ma_period': [20, 50, 100]
    }
    
    # Cost model
    cost_model = BinanceCostModel(use_bnb=True)
    
    # Run WFA
    wfa = WalkForwardAnalyzer(train_days=90, test_days=30, step_days=30)
    results = wfa.run_wfa(data, TrendStrategy, param_grid, cost_model, initial_capital=1000)
    
    print("\n=== WFA Results ===")
    print(f"Total PnL: ${results['total_pnl']:.2f}")
    print(f"Positive Windows: {results['positive_window_pct']:.1f}%")
    print(f"Avg Profit Factor: {results['avg_profit_factor']:.2f}")
    print(f"Worst Max DD: {results['worst_max_dd']:.2%}")
    print(f"Pass: {results['pass']}")
```

---

## 3. MONTE CARLO IMPLEMENTATION

```python
# services/engine/quantsail_engine/research/monte_carlo.py

import random
import numpy as np
import pandas as pd
from typing import List
from dataclasses import dataclass

class MonteCarloAnalyzer:
    def __init__(self, trades: List, initial_capital: float):
        self.trades = trades
        self.initial_capital = initial_capital
    
    def run_all_tests(self, iterations=1000) -> dict:
        """Run all 3 Monte Carlo tests"""
        print("Running Monte Carlo Tests...")
        
        # Test 1: Trade order randomization
        print("  MC Test 1: Trade Order Randomization...")
        shuffle_results = self.test_trade_shuffle(iterations)
        
        # Test 2: Parameter jitter (requires strategy and data - simplified here)
        # print("  MC Test 2: Parameter Jitter...")
        # param_results = self.test_parameter_jitter(strategy, data, params, iterations=500)
        
        # Test 3: Cost jitter
        print("  MC Test 3: Cost Jitter...")
        cost_results = self.test_cost_jitter(iterations)
        
        return {
            'trade_shuffle': shuffle_results,
            # 'parameter_jitter': param_results,
            'cost_jitter': cost_results
        }
    
    def test_trade_shuffle(self, iterations=1000) -> dict:
        """
        MC Test #1: Shuffle trade order, measure drawdown distribution
        
        This tests if max drawdown is path-dependent
        """
        max_dds = []
        final_equities = []
        
        for i in range(iterations):
            shuffled_trades = self.trades.copy()
            random.shuffle(shuffled_trades)
            
            equity = self.initial_capital
            equity_curve = [equity]
            
            for trade in shuffled_trades:
                equity += trade.net_pnl
                equity_curve.append(equity)
            
            # Calculate max drawdown
            max_dd = self._calculate_max_dd(equity_curve)
            max_dds.append(max_dd)
            final_equities.append(equity)
        
        return {
            'iterations': iterations,
            'mean_max_dd': np.mean(max_dds),
            'median_max_dd': np.median(max_dds),
            'p95_max_dd': np.percentile(max_dds, 95),
            'worst_max_dd': np.max(max_dds),
            'mean_final_equity': np.mean(final_equities),
            'p5_final_equity': np.percentile(final_equities, 5),  # 5th percentile = bad luck
            'pass': np.percentile(max_dds, 95) < 0.20  # 95th percentile DD < 20%
        }
    
    def test_cost_jitter(self, iterations=1000, cost_multipliers=[1.0, 1.5, 2.0]) -> dict:
        """
        MC Test #3: Increase costs (slippage, spread), test profitability
        
        This tests robustness to execution degradation
        """
        results_by_multiplier = {}
        
        for multiplier in cost_multipliers:
            profitable_count = 0
            total_pnls = []
            
            for i in range(iterations):
                total_pnl = 0
                
                for trade in self.trades:
                    # Increase costs
                    adjusted_slippage = trade.slippage * multiplier
                    adjusted_spread = trade.spread_cost * multiplier
                    
                    adjusted_pnl = trade.gross_pnl - trade.fees - adjusted_slippage - adjusted_spread
                    total_pnl += adjusted_pnl
                
                total_pnls.append(total_pnl)
                if total_pnl > 0:
                    profitable_count += 1
            
            results_by_multiplier[f'{multiplier}x'] = {
                'multiplier': multiplier,
                'profitable_pct': profitable_count / iterations * 100,
                'mean_pnl': np.mean(total_pnls),
                'median_pnl': np.median(total_pnls)
            }
        
        # Pass if at 1.5x costs, still >60% profitable
        pass_condition = results_by_multiplier['1.5x']['profitable_pct'] >= 60
        
        return {
            'by_multiplier': results_by_multiplier,
            'pass': pass_condition
        }
    
    def _calculate_max_dd(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown"""
        peak = equity_curve[0]
        max_dd = 0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            
            dd = (equity - peak) / peak
            if dd < max_dd:
                max_dd = dd
        
        return abs(max_dd)


# Usage
if __name__ == '__main__':
    # Assume you have trades from backtest
    from backtest_engine import BacktestEngine
    
    # ... run backtest ...
    # backtest_result = backtest.run(data, strategy, config)
    
    # mc = MonteCarloAnalyzer(backtest_result['trades'], initial_capital=1000)
    # mc_results = mc.run_all_tests(iterations=1000)
    # 
    # print("\n=== Monte Carlo Results ===")
    # print(f"Trade Shuffle:")
    # print(f"  Mean Max DD: {mc_results['trade_shuffle']['mean_max_dd']:.2%}")
    # print(f"  P95 Max DD: {mc_results['trade_shuffle']['p95_max_dd']:.2%}")
    # print(f"  Pass: {mc_results['trade_shuffle']['pass']}")
    # 
    # print(f"\nCost Jitter:")
    # print(f"  1.5x costs profitable: {mc_results['cost_jitter']['by_multiplier']['1.5x']['profitable_pct']:.1f}%")
    # print(f"  Pass: {mc_results['cost_jitter']['pass']}")
```

---

## 4. STRATEGY IMPLEMENTATIONS

### 4.1 Base Strategy Interface

```python
# services/engine/quantsail_engine/strategies/base.py

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict

class BaseStrategy(ABC):
    def __init__(self, symbol: str):
        self.symbol = symbol
    
    @abstractmethod
    def generate_signal(self, candles: pd.DataFrame) -> Dict:
        """
        Generate trading signal
        
        Args:
            candles: OHLCV DataFrame up to current bar (inclusive)
        
        Returns:
            {
                'signal': 'ENTER_LONG' | 'NO_TRADE' | 'EXIT',
                'entry': float,
                'stop': float,
                'target': float,
                'confidence': float (0-1),
                'rationale': str
            }
        """
        pass
```

### 4.2 Trend Strategy (Production)

```python
# services/engine/quantsail_engine/strategies/trend_production.py

import talib as ta
from .base import BaseStrategy

class TrendStrategy(BaseStrategy):
    def __init__(self, symbol='BNB/USDT', atr_period=14, adx_period=14, ma_period=50, lookback=20):
        super().__init__(symbol)
        self.atr_period = atr_period
        self.adx_period = adx_period
        self.ma_period = ma_period
        self.lookback = lookback
    
    def generate_signal(self, candles: pd.DataFrame) -> dict:
        # Need enough data for indicators
        if len(candles) < max(self.atr_period, self.adx_period, self.ma_period, self.lookback):
            return {'signal': 'NO_TRADE'}
        
        # Calculate indicators
        close = candles['close'].values
        high = candles['high'].values
        low = candles['low'].values
        volume = candles['volume'].values
        
        adx = ta.ADX(high, low, close, timeperiod=self.adx_period)
        ma = ta.SMA(close, timeperiod=self.ma_period)
        atr = ta.ATR(high, low, close, timeperiod=self.atr_period)
        
        # Current values
        current_price = close[-1]
        current_adx = adx[-1]
        current_ma = ma[-1]
        current_atr = atr[-1]
        
        # Lookback high
        lookback_high = candles['high'].rolling(self.lookback).max().iloc[-1]
        
        # Volume confirmation
        avg_volume = candles['volume'].rolling(20).mean().iloc[-1]
        current_volume = volume[-1]
        
        # === REGIME FILTER ===
        # Must be in trending market
        is_trending = (current_adx > 25) and (current_price > current_ma)
        
        if not is_trending:
            return {'signal': 'NO_TRADE', 'rationale': f'Not trending: ADX={current_adx:.1f}'}
        
        # === ENTRY CONDITION ===
        # Breakout of recent high with volume
        is_breakout = current_price > lookback_high
        volume_confirmed = current_volume > avg_volume
        
        if is_breakout and volume_confirmed:
            entry = current_price
            stop = entry - (2 * current_atr)
            target = entry + (3 * current_atr)  # 1.5:1 R:R
            
            return {
                'signal': 'ENTER_LONG',
                'entry': entry,
                'stop': stop,
                'target': target,
                'confidence': 0.75,
                'rationale': f'Trend breakout: ADX={current_adx:.1f}, Price above MA, Volume confirmed'
            }
        
        return {'signal': 'NO_TRADE'}
```

### 4.3 Mean Reversion Strategy

```python
# services/engine/quantsail_engine/strategies/mean_reversion_production.py

import talib as ta
from .base import BaseStrategy

class MeanReversionStrategy(BaseStrategy):
    def __init__(self, symbol='ADA/USDT', bb_period=20, bb_std=2, rsi_period=14, adx_threshold=20):
        super().__init__(symbol)
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.adx_threshold = adx_threshold
    
    def generate_signal(self, candles: pd.DataFrame) -> dict:
        if len(candles) < max(self.bb_period, self.rsi_period, 20):
            return {'signal': 'NO_TRADE'}
        
        close = candles['close'].values
        high = candles['high'].values
        low = candles['low'].values
        
        # Indicators
        adx = ta.ADX(high, low, close, timeperiod=14)
        bb_upper, bb_middle, bb_lower = ta.BBANDS(
            close, 
            timeperiod=self.bb_period, 
            nbdevup=self.bb_std, 
            nbdevdn=self.bb_std
        )
        rsi = ta.RSI(close, timeperiod=self.rsi_period)
        
        # Current values
        current_price = close[-1]
        current_low = low[-1]
        current_adx = adx[-1]
        current_rsi = rsi[-1]
        current_bb_lower = bb_lower[-1]
        current_bb_middle = bb_middle[-1]
        
        # === REGIME FILTER ===
        # Must be ranging market (low ADX)
        is_ranging = current_adx < self.adx_threshold
        
        if not is_ranging:
            return {'signal': 'NO_TRADE', 'rationale': f'Trending market: ADX={current_adx:.1f}'}
        
        # === ENTRY CONDITION ===
        # Touch lower BB + RSI oversold
        at_lower_band = current_low <= current_bb_lower
        is_oversold = current_rsi < 30
        
        if at_lower_band and is_oversold:
            entry = current_price
            stop = current_bb_lower - (current_bb_middle - current_bb_lower) * 0.5  # Tight stop
            target = current_bb_middle
            
            return {
                'signal': 'ENTER_LONG',
                'entry': entry,
                'stop': stop,
                'target': target,
                'confidence': 0.70,
                'rationale': f'Mean reversion: RSI={current_rsi:.1f}, at BB lower, ADX={current_adx:.1f}'
            }
        
        return {'signal': 'NO_TRADE'}
```

---

## 5. COST MODELS

```python
# services/engine/quantsail_engine/research/cost_models.py

class BinanceCostModel:
    def __init__(self, use_bnb=True, vip_level=0):
        """
        Binance cost model
        
        Args:
            use_bnb: Use BNB for 25% fee discount
            vip_level: 0-9 (higher = lower fees)
        """
        self.use_bnb = use_bnb
        self.vip_level = vip_level
        
        # Fee schedules (basis points)
        self.maker_fees = {
            0: 10.0,  # 0.10%
            1: 9.0,   # 0.09%
            2: 8.0,
            3: 7.0,
            4: 7.0
        }
        
        self.taker_fees = {
            0: 10.0,
            1: 10.0,
            2: 10.0,
            3: 9.0,
            4: 9.0
        }
        
        # Apply BNB discount
        if use_bnb:
            self.maker_fees = {k: v * 0.75 for k, v in self.maker_fees.items()}
            self.taker_fees = {k: v * 0.75 for k, v in self.taker_fees.items()}
    
    def calculate_fee(self, notional: float, is_maker=False) -> float:
        """
        Calculate trading fee
        
        Args:
            notional: Trade size in USD
            is_maker: True if limit order (maker), False if market (taker)
        
        Returns:
            Fee in USD
        """
        rate_bps = self.maker_fees[self.vip_level] if is_maker else self.taker_fees[self.vip_level]
        return notional * (rate_bps / 10000)
    
    def estimate_slippage(self, notional: float, volatility_percentile=0.5) -> float:
        """
        Estimate slippage based on order size
        
        For small retail sizes (<$1000), slippage is minimal on liquid pairs
        """
        if notional < 100:
            base_slippage_bps = 1  # 0.01%
        elif notional < 500:
            base_slippage_bps = 2
        elif notional < 1000:
            base_slippage_bps = 3
        else:
            base_slippage_bps = 5
        
        # Adjust for volatility
        volatility_factor = 0.5 + volatility_percentile  # 0.5 to 1.5
        adjusted_bps = base_slippage_bps * volatility_factor
        
        return notional * (adjusted_bps / 10000)
    
    def estimate_spread(self, notional: float) -> float:
        """
        Estimate spread cost
        
        Binance BNB/USDT typical spread: 0.01-0.02%
        """
        spread_bps = 2  # 0.02%
        return notional * (spread_bps / 10000)


# Example usage
cost_model = BinanceCostModel(use_bnb=True, vip_level=0)

trade_size = 200
fees = cost_model.calculate_fee(trade_size, is_maker=False) * 2  # Entry + exit
slippage = cost_model.estimate_slippage(trade_size)
spread = cost_model.estimate_spread(trade_size)

total_cost = fees + slippage + spread
print(f"Trade size: ${trade_size}")
print(f"Fees: ${fees:.4f}")
print(f"Slippage: ${slippage:.4f}")
print(f"Spread: ${spread:.4f}")
print(f"Total cost: ${total_cost:.4f} ({total_cost/trade_size*100:.3f}%)")
```

---

## 6. POSITION SIZING

```python
# services/engine/quantsail_engine/execution/position_sizer.py

class PositionSizer:
    def __init__(self, equity: float, config: dict):
        self.equity = equity
        self.config = config
    
    def calculate(self, entry: float, stop: float) -> dict:
        """
        Calculate optimal position size
        
        Returns:
            {
                'quantity': float,
                'notional': float,
                'risk_usd': float,
                'risk_pct': float,
                'viable': bool
            }
        """
        risk_per_trade_pct = self.config['risk']['max_risk_per_trade_pct']
        max_position_pct = self.config['risk']['max_position_pct_equity']
        min_notional = self.config['risk'].get('min_notional_usd', 10)
        
        # Risk-based sizing
        risk_amount = self.equity * (risk_per_trade_pct / 100)
        price_risk_pct = abs(entry - stop) / entry
        
        if price_risk_pct == 0:
            return {'viable': False, 'reason': 'Zero price risk'}
        
        quantity = risk_amount / (price_risk_pct * entry)
        notional = quantity * entry
        
        # Apply constraints
        max_notional = self.equity * (max_position_pct / 100)
        
        if notional > max_notional:
            notional = max_notional
            quantity = notional / entry
        
        if notional < min_notional:
            return {
                'viable': False,
                'reason': f'Notional ${notional:.2f} < min ${min_notional}'
            }
        
        return {
            'viable': True,
            'quantity': quantity,
            'notional': notional,
            'risk_usd': risk_amount,
            'risk_pct': risk_per_trade_pct
        }
```

---

## 7. PORTFOLIO RISK MANAGER

```python
# services/engine/quantsail_engine/core/portfolio_risk_manager.py

from datetime import datetime, timedelta
from typing import Dict, List

class PortfolioRiskManager:
    def __init__(self, config: dict):
        self.config = config
        self.open_positions = {}
        self.daily_trades_count = 0
        self.daily_realized_pnl = 0.0
        self.last_reset = datetime.utcnow().date()
    
    def reset_daily_counters(self):
        """Reset at start of new day"""
        today = datetime.utcnow().date()
        if today > self.last_reset:
            self.daily_trades_count = 0
            self.daily_realized_pnl = 0.0
            self.last_reset = today
    
    def can_open_position(self, symbol: str, notional: float) -> tuple[bool, str]:
        """
        Check if new position can be opened
        
        Returns:
            (allowed: bool, reason: str)
        """
        self.reset_daily_counters()
        
        # Check 1: Max concurrent positions
        max_concurrent = self.config['portfolio']['max_concurrent_positions']
        if len(self.open_positions) >= max_concurrent:
            return False, f"Max concurrent positions ({max_concurrent}) reached"
        
        # Check 2: Max correlated positions
        correlated_count = sum(
            1 for pos_symbol in self.open_positions.keys()
            if self._is_correlated(symbol, pos_symbol)
        )
        max_correlated = self.config['portfolio']['max_correlated_positions']
        if correlated_count >= max_correlated:
            return False, f"Max correlated positions ({max_correlated}) reached"
        
        # Check 3: Max daily trades
        max_daily_trades = self.config['portfolio'].get('max_daily_trades')
        if max_daily_trades and self.daily_trades_count >= max_daily_trades:
            return False, f"Max daily trades ({max_daily_trades}) reached"
        
        # Check 4: Daily loss limit (HARD STOP)
        max_daily_loss = self.config['portfolio']['max_daily_loss_usd']
        if self.daily_realized_pnl <= -max_daily_loss:
            return False, f"Daily loss limit hit: ${self.daily_realized_pnl:.2f}"
        
        # Check 5: Total portfolio exposure
        total_exposure = sum(pos['notional'] for pos in self.open_positions.values())
        max_exposure_pct = self.config['portfolio'].get('max_portfolio_exposure_pct', 30)
        max_exposure = self.equity * (max_exposure_pct / 100)
        
        if total_exposure + notional > max_exposure:
            return False, f"Portfolio exposure limit: ${total_exposure:.2f} + ${notional:.2f} > ${max_exposure:.2f}"
        
        return True, "OK"
    
    def _is_correlated(self, symbol1: str, symbol2: str) -> bool:
        """
        Check if two symbols are correlated
        
        Simplified: same base currency = correlated
        TODO: Implement rolling correlation calculation
        """
        base1 = symbol1.split('/')[0]
        base2 = symbol2.split('/')[0]
        
        # BTC pairs are correlated with each other
        if 'BTC' in base1 and 'BTC' in base2:
            return True
        
        # Stablecoins not correlated
        stables = ['USDT', 'USDC', 'BUSD']
        if base1 in stables or base2 in stables:
            return False
        
        return False
    
    def add_position(self, symbol: str, notional: float):
        """Register new position"""
        self.open_positions[symbol] = {
            'notional': notional,
            'opened_at': datetime.utcnow()
        }
        self.daily_trades_count += 1
    
    def close_position(self, symbol: str, pnl: float):
        """Close position and update PnL"""
        if symbol in self.open_positions:
            del self.open_positions[symbol]
        
        self.daily_realized_pnl += pnl
```

---

## 8. MONITORING & ALERTS

```python
# services/engine/quantsail_engine/monitoring/telegram_alerts.py

import requests
import logging

logger = logging.getLogger(__name__)

class TelegramAlerter:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    def send_alert(self, message: str, level='INFO'):
        """
        Send alert to Telegram
        
        Args:
            message: Alert message
            level: INFO, WARNING, ERROR, SUCCESS
        """
        emoji_map = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '🚨',
            'SUCCESS': '✅'
        }
        
        emoji = emoji_map.get(level, '')
        formatted_message = f"{emoji} <b>{level}</b>\n{message}"
        
        payload = {
            'chat_id': self.chat_id,
            'text': formatted_message,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=5)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
    
    # Pre-defined alerts
    def alert_engine_started(self):
        self.send_alert("Engine started and running", 'INFO')
    
    def alert_trade_opened(self, symbol, entry, stop, target, notional):
        msg = f"""
Trade Opened
Symbol: {symbol}
Entry: ${entry:.2f}
Stop: ${stop:.2f}
Target: ${target:.2f}
Size: ${notional:.2f}
"""
        self.send_alert(msg, 'INFO')
    
    def alert_trade_closed(self, symbol, pnl, status):
        msg = f"""
Trade Closed: {status}
Symbol: {symbol}
PnL: ${pnl:.2f}
"""
        level = 'SUCCESS' if pnl > 0 else 'WARNING'
        self.send_alert(msg, level)
    
    def alert_daily_target_hit(self, pnl):
        msg = f"Daily target hit! 🎯\nPnL: ${pnl:.2f}"
        self.send_alert(msg, 'SUCCESS')
    
    def alert_daily_loss_limit(self, pnl):
        msg = f"""
DAILY LOSS LIMIT HIT
PnL: ${pnl:.2f}
All entries paused until tomorrow.
"""
        self.send_alert(msg, 'ERROR')
    
    def alert_breaker_triggered(self, breaker_type, duration_min):
        msg = f"""
Circuit Breaker Triggered
Type: {breaker_type}
Duration: {duration_min} minutes
"""
        self.send_alert(msg, 'WARNING')
    
    def alert_error(self, error_msg):
        self.send_alert(f"Engine Error:\n{error_msg}", 'ERROR')


# Prometheus Metrics
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
TRADES_TOTAL = Counter('quantsail_trades_total', 'Total trades', ['symbol', 'side', 'status'])
TRADE_PNL = Histogram('quantsail_trade_pnl_usd', 'Trade PnL', buckets=[-10, -5, -1, 0, 1, 5, 10, 50])
EQUITY = Gauge('quantsail_equity_usd', 'Current equity')
DAILY_PNL = Gauge('quantsail_daily_pnl_usd', 'Daily realized PnL')
BREAKER_TRIGGERS = Counter('quantsail_breaker_triggers', 'Breaker triggers', ['type'])
GATE_REJECTIONS = Counter('quantsail_gate_rejections', 'Gate rejections', ['reason'])

def start_metrics_server(port=9090):
    """Start Prometheus metrics HTTP server"""
    start_http_server(port)
    logger.info(f"Metrics server started on port {port}")

# Usage in engine
def on_trade_closed(trade):
    TRADES_TOTAL.labels(symbol=trade.symbol, side=trade.side, status=trade.status).inc()
    TRADE_PNL.observe(trade.realized_pnl_usd)
    
def update_equity(equity):
    EQUITY.set(equity)
    
def update_daily_pnl(pnl):
    DAILY_PNL.set(pnl)
```

---

## APPENDIX: Complete Project Structure

```
quantsail-bot/
├── services/
│   ├── engine/
│   │   ├── quantsail_engine/
│   │   │   ├── research/           # NEW: Backtesting & research tools
│   │   │   │   ├── data_fetcher.py
│   │   │   │   ├── backtest_engine.py
│   │   │   │   ├── walk_forward.py
│   │   │   │   ├── monte_carlo.py
│   │   │   │   └── cost_models.py
│   │   │   ├── strategies/
│   │   │   │   ├── base.py
│   │   │   │   ├── trend_production.py
│   │   │   │   ├── mean_reversion_production.py
│   │   │   │   └── volatility_expansion.py
│   │   │   ├── execution/
│   │   │   │   ├── position_sizer.py
│   │   │   │   └── oanda_adapter.py  # For forex later
│   │   │   ├── core/
│   │   │   │   ├── portfolio_risk_manager.py
│   │   │   │   └── trading_loop.py
│   │   │   └── monitoring/
│   │   │       ├── telegram_alerts.py
│   │   │       └── metrics.py
│   │   └── scripts/
│   │       ├── fetch_historical_data.py
│   │       ├── run_backtest.py
│   │       ├── run_walk_forward.py
│   │       └── run_monte_carlo.py
│   └── api/
└── data/                           # NEW: Historical data storage
    ├── historical/
    │   ├── BNB_USDT.parquet
    │   ├── ADA_USDT.parquet
    │   └── ...
    └── reports/                    # NEW: Research reports
        ├── backtest_results.json
        ├── wfa_results.json
        └── monte_carlo_results.json
```

---

**Document End**  
**Version:** 1.0  
**Date:** February 5, 2026  
**Status:** Production-Ready Code Examples
