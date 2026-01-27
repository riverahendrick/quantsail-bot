"""Unit tests for configuration loader."""

import json
from pathlib import Path

import pytest

from quantsail_engine.config.loader import load_config


def test_load_config_from_default_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading config from default config.json file."""
    config_file = tmp_path / "config.json"
    config_data = {
        "execution": {"mode": "dry-run", "min_profit_usd": 0.20},
        "risk": {"starting_cash_usd": 5000.0, "max_risk_per_trade_pct": 0.5},
        "symbols": {"enabled": ["ETH/USDT"], "max_concurrent_positions": 2},
    }
    config_file.write_text(json.dumps(config_data))

    # Explicitly pass the config file path
    config = load_config(str(config_file))
    assert config.execution.mode == "dry-run"
    assert config.execution.min_profit_usd == 0.20
    assert config.risk.starting_cash_usd == 5000.0
    assert config.symbols.enabled == ["ETH/USDT"]


def test_load_config_from_explicit_path(tmp_path: Path) -> None:
    """Test loading config from explicit file path."""
    config_file = tmp_path / "custom.json"
    config_data = {"execution": {"mode": "live"}}
    config_file.write_text(json.dumps(config_data))

    config = load_config(str(config_file))
    assert config.execution.mode == "live"


def test_load_config_from_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading config from ENGINE_CONFIG_PATH environment variable."""
    config_file = tmp_path / "env_config.json"
    config_data = {"risk": {"starting_cash_usd": 20000.0}}
    config_file.write_text(json.dumps(config_data))

    monkeypatch.setenv("ENGINE_CONFIG_PATH", str(config_file))

    config = load_config()
    assert config.risk.starting_cash_usd == 20000.0


def test_load_config_file_not_found(tmp_path: Path) -> None:
    """Test error when config file doesn't exist."""
    nonexistent = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(str(nonexistent))


def test_load_config_invalid_json(tmp_path: Path) -> None:
    """Test error when config file has invalid JSON."""
    config_file = tmp_path / "invalid.json"
    config_file.write_text("{invalid json")

    with pytest.raises(json.JSONDecodeError):
        load_config(str(config_file))


def test_load_config_env_override_execution_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test QUANTSAIL_EXECUTION_MODE environment variable override."""
    config_file = tmp_path / "config.json"
    config_data = {"execution": {"mode": "dry-run"}}
    config_file.write_text(json.dumps(config_data))

    monkeypatch.setenv("QUANTSAIL_EXECUTION_MODE", "live")

    config = load_config(str(config_file))
    assert config.execution.mode == "live"


def test_load_config_env_override_min_profit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test QUANTSAIL_EXECUTION_MIN_PROFIT_USD environment variable override."""
    config_file = tmp_path / "config.json"
    config_data = {"execution": {"min_profit_usd": 0.10}}
    config_file.write_text(json.dumps(config_data))

    monkeypatch.setenv("QUANTSAIL_EXECUTION_MIN_PROFIT_USD", "0.50")

    config = load_config(str(config_file))
    assert config.execution.min_profit_usd == 0.50


def test_load_config_env_override_starting_cash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test QUANTSAIL_RISK_STARTING_CASH_USD environment variable override."""
    config_file = tmp_path / "config.json"
    config_data = {"risk": {"starting_cash_usd": 10000.0}}
    config_file.write_text(json.dumps(config_data))

    monkeypatch.setenv("QUANTSAIL_RISK_STARTING_CASH_USD", "50000.0")

    config = load_config(str(config_file))
    assert config.risk.starting_cash_usd == 50000.0


def test_load_config_env_override_symbols(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test QUANTSAIL_SYMBOLS_ENABLED environment variable override."""
    config_file = tmp_path / "config.json"
    config_data = {"symbols": {"enabled": ["BTC/USDT"]}}
    config_file.write_text(json.dumps(config_data))

    monkeypatch.setenv("QUANTSAIL_SYMBOLS_ENABLED", "ETH/USDT,SOL/USDT")

    config = load_config(str(config_file))
    assert config.symbols.enabled == ["ETH/USDT", "SOL/USDT"]


def test_load_config_env_override_max_positions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test QUANTSAIL_SYMBOLS_MAX_CONCURRENT_POSITIONS environment variable override."""
    config_file = tmp_path / "config.json"
    config_data = {"symbols": {"max_concurrent_positions": 1}}
    config_file.write_text(json.dumps(config_data))

    monkeypatch.setenv("QUANTSAIL_SYMBOLS_MAX_CONCURRENT_POSITIONS", "5")

    config = load_config(str(config_file))
    assert config.symbols.max_concurrent_positions == 5


def test_load_config_multiple_env_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test multiple environment variable overrides work together."""
    config_file = tmp_path / "config.json"
    config_data = {
        "execution": {"mode": "dry-run", "min_profit_usd": 0.10},
        "risk": {"starting_cash_usd": 10000.0},
    }
    config_file.write_text(json.dumps(config_data))

    monkeypatch.setenv("QUANTSAIL_EXECUTION_MODE", "live")
    monkeypatch.setenv("QUANTSAIL_EXECUTION_MIN_PROFIT_USD", "1.00")
    monkeypatch.setenv("QUANTSAIL_RISK_STARTING_CASH_USD", "100000.0")

    config = load_config(str(config_file))
    assert config.execution.mode == "live"
    assert config.execution.min_profit_usd == 1.00
    assert config.risk.starting_cash_usd == 100000.0


def test_load_config_env_creates_missing_sections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test environment variables create sections if not in config file."""
    config_file = tmp_path / "config.json"
    config_data: dict[str, object] = {}  # Empty config
    config_file.write_text(json.dumps(config_data))

    monkeypatch.setenv("QUANTSAIL_EXECUTION_MODE", "live")
    monkeypatch.setenv("QUANTSAIL_RISK_STARTING_CASH_USD", "25000.0")

    config = load_config(str(config_file))
    assert config.execution.mode == "live"
    assert config.risk.starting_cash_usd == 25000.0
