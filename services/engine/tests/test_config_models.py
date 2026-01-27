"""Unit tests for configuration Pydantic models."""

import pytest
from pydantic import ValidationError

from quantsail_engine.config.models import BotConfig, ExecutionConfig, RiskConfig, SymbolsConfig


def test_execution_config_defaults() -> None:
    """Test ExecutionConfig uses correct defaults."""
    config = ExecutionConfig()
    assert config.mode == "dry-run"
    assert config.min_profit_usd == 0.10


def test_execution_config_validation_min_profit_negative() -> None:
    """Test ExecutionConfig rejects negative min_profit_usd."""
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        ExecutionConfig(min_profit_usd=-0.01)


def test_execution_config_invalid_mode() -> None:
    """Test ExecutionConfig rejects invalid mode."""
    with pytest.raises(ValidationError, match="Input should be 'dry-run' or 'live'"):
        ExecutionConfig(mode="invalid")  # type: ignore[arg-type]


def test_risk_config_defaults() -> None:
    """Test RiskConfig uses correct defaults."""
    config = RiskConfig()
    assert config.starting_cash_usd == 10000.0
    assert config.max_risk_per_trade_pct == 0.25


def test_risk_config_validation_starting_cash_zero() -> None:
    """Test RiskConfig rejects zero starting_cash_usd."""
    with pytest.raises(ValidationError, match="greater than 0"):
        RiskConfig(starting_cash_usd=0.0)


def test_risk_config_validation_starting_cash_negative() -> None:
    """Test RiskConfig rejects negative starting_cash_usd."""
    with pytest.raises(ValidationError, match="greater than 0"):
        RiskConfig(starting_cash_usd=-100.0)


def test_risk_config_validation_max_risk_zero() -> None:
    """Test RiskConfig rejects zero max_risk_per_trade_pct."""
    with pytest.raises(ValidationError, match="greater than 0"):
        RiskConfig(max_risk_per_trade_pct=0.0)


def test_risk_config_validation_max_risk_above_100() -> None:
    """Test RiskConfig rejects max_risk_per_trade_pct > 100."""
    with pytest.raises(ValidationError, match="less than or equal to 100"):
        RiskConfig(max_risk_per_trade_pct=101.0)


def test_symbols_config_defaults() -> None:
    """Test SymbolsConfig uses correct defaults."""
    config = SymbolsConfig()
    assert config.enabled == ["BTC/USDT"]
    assert config.max_concurrent_positions == 1


def test_symbols_config_validation_empty_enabled() -> None:
    """Test SymbolsConfig rejects empty enabled list."""
    with pytest.raises(ValidationError, match="at least 1 item"):
        SymbolsConfig(enabled=[])


def test_symbols_config_validation_max_positions_zero() -> None:
    """Test SymbolsConfig rejects zero max_concurrent_positions."""
    with pytest.raises(ValidationError, match="greater than or equal to 1"):
        SymbolsConfig(max_concurrent_positions=0)


def test_bot_config_defaults() -> None:
    """Test BotConfig uses nested defaults."""
    config = BotConfig()
    assert config.execution.mode == "dry-run"
    assert config.risk.starting_cash_usd == 10000.0
    assert config.symbols.enabled == ["BTC/USDT"]


def test_bot_config_partial_override() -> None:
    """Test BotConfig allows partial section overrides."""
    config = BotConfig(
        execution={"mode": "live"},  # type: ignore[arg-type]
        symbols={"enabled": ["ETH/USDT", "BTC/USDT"]},  # type: ignore[arg-type]
    )
    assert config.execution.mode == "live"
    assert config.execution.min_profit_usd == 0.10  # Default preserved
    assert config.risk.starting_cash_usd == 10000.0  # Default preserved
    assert config.symbols.enabled == ["ETH/USDT", "BTC/USDT"]


def test_bot_config_full_override() -> None:
    """Test BotConfig with all sections explicitly set."""
    config = BotConfig(
        execution=ExecutionConfig(mode="live", min_profit_usd=0.50),
        risk=RiskConfig(starting_cash_usd=50000.0, max_risk_per_trade_pct=1.0),
        symbols=SymbolsConfig(enabled=["ETH/USDT"], max_concurrent_positions=3),
    )
    assert config.execution.mode == "live"
    assert config.execution.min_profit_usd == 0.50
    assert config.risk.starting_cash_usd == 50000.0
    assert config.risk.max_risk_per_trade_pct == 1.0
    assert config.symbols.enabled == ["ETH/USDT"]
    assert config.symbols.max_concurrent_positions == 3
