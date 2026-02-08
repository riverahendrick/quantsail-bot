"""Debug: reproduce the intermittent 'float has no attribute replace' error.

Runs the same config repeatedly on coins that errored previously
(SOL, BNB, NEAR, UNI, XRP) until the error reproduces, then prints
the FULL traceback so we can fix it.
"""
import sys
import traceback
import gc
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
logging.disable(logging.CRITICAL)

from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile
from quantsail_engine.backtest.runner import BacktestRunner

DATA_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data" / "historical"
)

# Coins that errored during the full test
ERROR_PRONE = [
    ("SOL", DATA_DIR / "SOL_USDT_1h_ohlcv.csv"),
    ("BNB", DATA_DIR / "BNB_USDT_1h_ohlcv.csv"),
    ("NEAR", DATA_DIR / "NEAR_USDT_1h_ohlcv.csv"),
    ("XRP", DATA_DIR / "XRP_USDT_1h_ohlcv.csv"),
    ("UNI", DATA_DIR / "UNI_USDT_1h_ohlcv.csv"),
    ("ADA", DATA_DIR / "ADA_USDT_1h_ohlcv.csv"),
]

STRATEGY_CONFIGS = {
    "trend_only": {"weight_trend": 1.0, "weight_mean_reversion": 0.0, "weight_breakout": 0.0, "weight_vwap": 0.0},
    "mean_rev_only": {"weight_trend": 0.0, "weight_mean_reversion": 1.0, "weight_breakout": 0.0, "weight_vwap": 0.0},
    "breakout_only": {"weight_trend": 0.0, "weight_mean_reversion": 0.0, "weight_breakout": 1.0, "weight_vwap": 0.0},
    "vwap_only": {"weight_trend": 0.0, "weight_mean_reversion": 0.0, "weight_breakout": 0.0, "weight_vwap": 1.0},
}

def run_one(sym, path, strategy_override=None):
    base = BotConfig()
    cfg_dict = apply_profile(base.model_dump(), "aggressive_1h")
    cfg_dict["symbols"] = {"enabled": [sym]}
    if strategy_override is not None:
        cfg_dict["strategies"]["ensemble"]["min_agreement"] = 1
        cfg_dict["strategies"]["ensemble"]["confidence_threshold"] = 0.30
        cfg_dict["strategies"]["ensemble"]["weighted_threshold"] = 0.15
        for k, v in strategy_override.items():
            cfg_dict["strategies"]["ensemble"][k] = v
    cfg = BotConfig(**cfg_dict)
    runner = BacktestRunner(
        config=cfg,
        data_file=path,
        starting_cash=5000.0,
        slippage_pct=0.05,
        fee_pct=0.1,
        tick_interval_seconds=3600,
        progress_interval=99999,
    )
    m = runner.run()
    runner.close()
    del runner, m, cfg
    gc.collect()

if __name__ == "__main__":
    attempt = 0
    max_attempts = 50
    print(f"Attempting to reproduce .replace() error (max {max_attempts} attempts)...")
    
    while attempt < max_attempts:
        for sym, path in ERROR_PRONE:
            for strat_name, weights in STRATEGY_CONFIGS.items():
                attempt += 1
                try:
                    run_one(sym, path, strategy_override=weights)
                    print(f"  [{attempt}] {sym} {strat_name}: OK")
                except Exception as e:
                    if "replace" in str(e):
                        print(f"\n{'='*60}")
                        print(f"REPRODUCED at attempt {attempt}: {sym} {strat_name}")
                        print(f"{'='*60}")
                        traceback.print_exc()
                        print(f"{'='*60}")
                        sys.exit(0)
                    else:
                        print(f"  [{attempt}] {sym} {strat_name}: OTHER ERR: {e}")
                if attempt >= max_attempts:
                    break
            if attempt >= max_attempts:
                break
    
    print(f"\nCould not reproduce after {max_attempts} attempts.")
    print("The error may be truly random or tied to memory conditions.")
