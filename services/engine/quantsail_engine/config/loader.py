"""Configuration loader with JSON file and environment variable support."""

import json
import os
from pathlib import Path
from typing import Any

from .models import BotConfig


def load_config(config_path: str | None = None) -> BotConfig:
    """
    Load configuration from JSON file with environment variable overrides.

    Priority: env vars > config file > defaults

    Args:
        config_path: Path to JSON config file. If None, uses ENGINE_CONFIG_PATH env var
                     or defaults to 'config.json' in engine service root.

    Returns:
        Validated BotConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file has invalid JSON
        pydantic.ValidationError: If config values are invalid
    """
    # Determine config file path
    if config_path is None:
        config_path = os.environ.get("ENGINE_CONFIG_PATH", "config.json")

    config_file = Path(config_path)
    if not config_file.is_absolute():
        # Resolve relative to engine service root
        engine_root = Path(__file__).parent.parent.parent
        config_file = engine_root / config_file

    # Load JSON config
    config_data: dict[str, Any] = {}
    if config_file.exists():
        with open(config_file) as f:
            config_data = json.load(f)
    else:
        raise FileNotFoundError(f"Config file not found: {config_file}")

    # Apply environment variable overrides
    # Format: QUANTSAIL_EXECUTION_MODE, QUANTSAIL_RISK_STARTING_CASH_USD, etc.
    if mode := os.environ.get("QUANTSAIL_EXECUTION_MODE"):
        config_data.setdefault("execution", {})["mode"] = mode

    if min_profit := os.environ.get("QUANTSAIL_EXECUTION_MIN_PROFIT_USD"):
        config_data.setdefault("execution", {})["min_profit_usd"] = float(min_profit)

    if starting_cash := os.environ.get("QUANTSAIL_RISK_STARTING_CASH_USD"):
        config_data.setdefault("risk", {})["starting_cash_usd"] = float(starting_cash)

    if max_risk := os.environ.get("QUANTSAIL_RISK_MAX_RISK_PER_TRADE_PCT"):
        config_data.setdefault("risk", {})["max_risk_per_trade_pct"] = float(max_risk)

    if symbols := os.environ.get("QUANTSAIL_SYMBOLS_ENABLED"):
        config_data.setdefault("symbols", {})["enabled"] = symbols.split(",")

    if max_positions := os.environ.get("QUANTSAIL_SYMBOLS_MAX_CONCURRENT_POSITIONS"):
        config_data.setdefault("symbols", {})["max_concurrent_positions"] = int(max_positions)

    # Validate and return
    return BotConfig(**config_data)
