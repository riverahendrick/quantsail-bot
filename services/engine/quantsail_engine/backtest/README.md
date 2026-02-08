# Quantsail Professional Backtesting Framework

A robust, realistic backtesting suite that executes actual production engine code against historical data.

## Overview

This framework allows you to:
- Run the actual TradingLoop, EnsembleStrategy, RiskManager, and safety mechanisms against historical data
- Verify performance metrics (Sharpe, Drawdown, Profit Factor)
- Validate that Circuit Breakers and Daily Lock function correctly in simulation
- Test different fee/slippage scenarios

## Architecture

The framework uses **dependency injection** to replace live services with simulated ones:

```
┌─────────────────────────────────────────────────────────────┐
│                    BacktestRunner                           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ BacktestMarket   │  │ BacktestExecutor │                │
│  │ Provider         │  │                  │                │
│  │ (Historical Data)│  │ (Simulated Fills)│                │
│  └──────────────────┘  └──────────────────┘                │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ BacktestRepo     │  │ TimeManager      │                │
│  │ (SQLite Storage) │  │ (Simulated Time) │                │
│  └──────────────────┘  └──────────────────┘                │
├─────────────────────────────────────────────────────────────┤
│              Production Engine Components                   │
│   TradingLoop | EnsembleStrategy | RiskManager | Gates      │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Download Historical Data

```bash
# Download 30 days of BTC/USDT 1-minute data
python tools/download_data.py --symbol BTC/USDT --timeframe 1m --days 30

# Download with custom output directory
python tools/download_data.py --symbol ETH/USDT --timeframe 5m --days 60 --output ./data
```

### 2. Run a Backtest

```bash
# Basic baseline test
python backtest_runner.py --data-file ./data/BTC_USDT_1m.csv

# Fee impact analysis (compare with 0 fees)
python backtest_runner.py --data-file ./data/BTC_USDT_1m.csv --fee-pct 0.0 --name baseline_no_fees
python backtest_runner.py --data-file ./data/BTC_USDT_1m.csv --fee-pct 0.1 --name baseline_with_fees

# Stress test with high slippage
python backtest_runner.py --data-file ./data/BTC_USDT_1m.csv --slippage-pct 0.2 --name stress_test

# Custom starting capital and daily target
python backtest_runner.py \
  --data-file ./data/BTC_USDT_1m.csv \
  --starting-cash 50000 \
  --daily-target 100 \
  --daily-mode OVERDRIVE
```

### 3. Programmatic Usage

```python
from quantsail_engine.backtest import BacktestRunner
from quantsail_engine.config.models import BotConfig

# Configure
config = BotConfig()
config.symbols.enabled = ["BTC/USDT"]
config.daily.enabled = True
config.daily.target_usd = 50.0

# Create runner
runner = BacktestRunner(
    config=config,
    data_file="./data/BTC_USDT_1m.csv",
    starting_cash=10000.0,
    slippage_pct=0.05,
    fee_pct=0.1,
)

# Run backtest
metrics = runner.run()

# Access results
print(f"Total Return: {metrics.total_return_pct:.2f}%")
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: {metrics.max_drawdown_pct:.2f}%")
print(f"Win Rate: {metrics.win_rate_pct:.1f}%")
print(f"Circuit Breakers Triggered: {metrics.circuit_breaker_triggers}")

# Save report
runner.save_report(metrics, "./results/my_backtest.json")
runner.close()
```

## Performance Metrics

The framework calculates comprehensive metrics:

| Metric | Description |
|--------|-------------|
| **Total Return %** | Overall return percentage |
| **Net Profit (USD)** | Absolute profit/loss in USD |
| **Max Drawdown %** | Largest peak-to-trough decline |
| **Profit Factor** | Gross profit / gross loss |
| **Sharpe Ratio** | Risk-adjusted return (annualized) |
| **Sortino Ratio** | Downside-risk-adjusted return |
| **Win Rate %** | Percentage of winning trades |
| **Avg Win/Loss** | Average winning and losing trade |
| **Circuit Breakers** | Number of safety triggers |
| **Daily Lock Hits** | Number of daily lock engagements |

## Scenarios to Test

### 1. Baseline Test
Standard configuration with Trend + Mean Reversion strategies:
```bash
python backtest_runner.py --data-file ./data/BTC_USDT_1m.csv --name baseline
```

### 2. Stress Test (High Volatility)
Test Circuit Breakers during market crashes:
```bash
# Use high slippage to simulate volatile conditions
python backtest_runner.py \
  --data-file ./data/crash_period.csv \
  --slippage-pct 0.2 \
  --fee-pct 0.15 \
  --name stress_volatility
```

### 3. Fee Impact Analysis
Quantify how much alpha is lost to exchange fees:
```bash
# Zero fees (upper bound)
python backtest_runner.py --data-file ./data/BTC_USDT_1m.csv --fee-pct 0.0 --name fees_0

# Standard fees
python backtest_runner.py --data-file ./data/BTC_USDT_1m.csv --fee-pct 0.1 --name fees_0.1

# High fees
python backtest_runner.py --data-file ./data/BTC_USDT_1m.csv --fee-pct 0.2 --name fees_0.2
```

### 4. Daily Lock Modes
Test STOP vs OVERDRIVE modes:
```bash
# STOP mode - pause at target
python backtest_runner.py --data-file ./data/BTC_USDT_1m.csv --daily-mode STOP --name mode_stop

# OVERDRIVE mode - trail profit floor
python backtest_runner.py --data-file ./data/BTC_USDT_1m.csv --daily-mode OVERDRIVE --name mode_overdrive
```

## Output Files

Each backtest generates:

1. **JSON Report** (`{name}.json`): Full metrics and configuration
2. **SQLite Database** (`{name}.db`): All trades, orders, events, and equity curve
3. **Summary CSV** (`backtest_summary.csv`): Append-only summary for batch comparisons

## Key Design Principles

### 1. No Look-ahead Bias
The `BacktestMarketProvider` only returns data up to the current simulated timestamp:
```python
time_mgr.set_time(datetime(2024, 1, 1, 12, 30))
candles = provider.get_candles("BTC/USDT", "1m", 100)
# Returns only candles up to 12:30, not future data
```

### 2. Production Code Execution
The backtest imports and runs the actual engine modules:
- `TradingLoop` logic is reproduced in `BacktestRunner._tick_symbol()`
- `EnsembleSignalProvider` generates real signals
- `DailyLockManager` and `BreakerManager` operate normally

### 3. Deterministic Time
All components receive time from `TimeManager`:
- Trade timestamps use simulated time
- Daily lock checks use simulated date
- Circuit breaker expirations use simulated time

## Testing

Run the test suite:
```bash
# All backtest tests
python -m pytest tests/test_backtest_*.py -v

# Specific test files
python -m pytest tests/test_backtest_market_provider.py -v
python -m pytest tests/test_backtest_executor.py -v
python -m pytest tests/test_backtest_metrics.py -v
python -m pytest tests/test_backtest_integration.py -v
```

## Troubleshooting

### No Data File
```
FileNotFoundError: Data file not found: ./data/BTC_USDT_1m.csv
```
Run the download tool first:
```bash
python tools/download_data.py --symbol BTC/USDT --timeframe 1m --days 30
```

### Out of Memory with Large Datasets
For large backtests, consider:
- Using Parquet format instead of CSV
- Reducing the tick interval
- Processing data in chunks

### Slow Execution
Backtests can be slow with:
- High-frequency data (1m candles)
- Many tick intervals
- Complex strategies

Optimize by:
- Increasing `--tick-interval` (e.g., 900s for 15-min)
- Increasing `--progress-interval` to reduce console output
