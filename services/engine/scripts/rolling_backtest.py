"""Rolling window backtest script for walk-forward validation."""

import sys
import csv
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile
from quantsail_engine.backtest.runner import BacktestRunner

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical"
TEMP_DIR = Path(__file__).resolve().parent / "temp_data"
RESULTS_FILE = Path(__file__).resolve().parent / "rolling_backtest_results.csv"

# Configuration
WINDOW_DAYS = 30
STEP_DAYS = 7
PROFILE = "aggressive_1h"
SYMBOL = "BTC"
CSV_FILE = "BTC_USDT_1h_ohlcv.csv"
CASH = 5000.0


def prepare_temp_dir():
    """Create or clean temp directory."""
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir()
    print(f"Created temp directory: {TEMP_DIR}")


def run_rolling_backtest():
    """Execute rolling window backtest."""
    print(f"Starting Rolling Backtest for {SYMBOL} ({PROFILE})")
    print(f"Window: {WINDOW_DAYS} days, Step: {STEP_DAYS} days")
    
    # Load full dataset
    data_path = DATA_DIR / CSV_FILE
    if not data_path.exists():
        print(f"Error: Data file not found at {data_path}")
        return

    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    total_duration = (df['timestamp'].max() - df['timestamp'].min()).days
    print(f"Data range: {df['timestamp'].min()} to {df['timestamp'].max()} ({total_duration} days)")

    # Prepare results storage
    results = []
    
    # Calculate windows
    start_time = df['timestamp'].min()
    end_time = df['timestamp'].max()
    
    current_start = start_time
    
    window_idx = 0
    
    while current_start + pd.Timedelta(days=WINDOW_DAYS) <= end_time:
        window_idx += 1
        current_end = current_start + pd.Timedelta(days=WINDOW_DAYS)
        
        print(f"\nProcessing Window {window_idx}: {current_start} to {current_end}")
        
        # Slice data
        mask = (df['timestamp'] >= current_start) & (df['timestamp'] < current_end)
        window_df = df.loc[mask].copy()
        
        if window_df.empty:
            print("  Skipping empty window")
            current_start += pd.Timedelta(days=STEP_DAYS)
            continue
            
        # Check sufficient data points (assuming 1h candles)
        min_candles = WINDOW_DAYS * 24 * 0.9  # 90% coverage required
        if len(window_df) < min_candles:
            print(f"  Skipping: Insufficient data ({len(window_df)} candles vs required {min_candles})")
            current_start += pd.Timedelta(days=STEP_DAYS)
            continue

        # Save temp file
        temp_file = TEMP_DIR / f"window_{window_idx}.csv"
        window_df.to_csv(temp_file, index=False)
        
        # Run Backtest
        try:
            base = BotConfig()
            tuned = apply_profile(base.model_dump(), PROFILE)
            if "symbols" not in tuned:
                tuned["symbols"] = {}
            tuned["symbols"]["enabled"] = [SYMBOL]
            
            config = BotConfig(**tuned)
            
            runner = BacktestRunner(
                config=config, 
                data_file=temp_file, 
                starting_cash=CASH,
                slippage_pct=0.05,
                fee_pct=0.1,
                tick_interval_seconds=3600,
                progress_interval=1000  # Silent-ish
            )
            
            metrics = runner.run()
            
            # Store results
            result = {
                "window": window_idx,
                "start_date": current_start.date(),
                "end_date": current_end.date(),
                "trades": metrics.total_trades,
                "win_rate": metrics.win_rate_pct,
                "net_pnl": metrics.net_profit_usd,
                "roi_pct": metrics.total_return_pct,
                "max_dd": metrics.max_drawdown_pct,
                "profit_factor": metrics.profit_factor
            }
            results.append(result)
            
            print(f"  Trades: {metrics.total_trades} | Win%: {metrics.win_rate_pct:.1f}% | PnL: ${metrics.net_profit_usd:.2f} | MaxDD: {metrics.max_drawdown_pct:.2f}%")
            
            runner.close()
            
        except Exception as e:
            print(f"  Error in window {window_idx}: {e}")
            import traceback
            traceback.print_exc()
        
        # Advance window
        current_start += pd.Timedelta(days=STEP_DAYS)

    # Save aggregated results
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv(RESULTS_FILE, index=False)
        print(f"\nSaved rolling backtest results to {RESULTS_FILE}")
        
        # Print summary stats
        print("\n--- Walk-Forward Summary ---")
        print(f"Total Windows: {len(results)}")
        print(f"Profitable Windows: {len(results_df[results_df['net_pnl'] > 0])}")
        print(f"Average PnL per Window: ${results_df['net_pnl'].mean():.2f}")
        print(f"Avg Max Drawdown: {results_df['max_dd'].mean():.2f}%")
        print(f"Best Window PnL: ${results_df['net_pnl'].max():.2f}")
        print(f"Worst Window PnL: ${results_df['net_pnl'].min():.2f}")
    else:
        print("\nNo results generated.")

    # Cleanup
    shutil.rmtree(TEMP_DIR)
    print("Cleaned up temp directory.")


if __name__ == "__main__":
    prepare_temp_dir()
    run_rolling_backtest()
