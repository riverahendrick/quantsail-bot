"""Additional tests for config loader edge cases and coverage."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from quantsail_engine.config.loader import load_config


def test_load_config_pydantic_validation_error(tmp_path: Path) -> None:
    """Test that Pydantic validation errors are raised."""
    config_file = tmp_path / "invalid_config.json"
    config_data = {
        "execution": {"min_profit_usd": -1.0},  # Invalid: must be >= 0
    }
    config_file.write_text(json.dumps(config_data))

    with pytest.raises(ValidationError):
        load_config(str(config_file))


def test_load_config_all_env_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test all environment variable overrides including max_risk."""
    config_file = tmp_path / "config.json"
    config_data = {
        "execution": {"mode": "dry-run"},
        "risk": {"starting_cash_usd": 10000.0, "max_risk_per_trade_pct": 0.25},
    }
    config_file.write_text(json.dumps(config_data))

    # Set the env var that hasn't been tested
    monkeypatch.setenv("QUANTSAIL_RISK_MAX_RISK_PER_TRADE_PCT", "2.0")

    config = load_config(str(config_file))
    assert config.risk.max_risk_per_trade_pct == 2.0


def test_load_config_relative_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading config from relative path (uses engine root resolution)."""
    # This will use the actual config.json in the engine directory
    monkeypatch.delenv("ENGINE_CONFIG_PATH", raising=False)

    # Load using relative path - this exercises lines 36-37
    config = load_config("config.json")
    assert config.execution.mode == "dry-run"  # From actual config.json
