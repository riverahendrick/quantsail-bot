import logging
import os
from unittest.mock import patch

from pytest import LogCaptureFixture

from quantsail_engine.config.models import BotConfig, ExecutionConfig
from quantsail_engine.security.encryption import DecryptedCredentials

from main import main as run_main
from quantsail_engine.main import main


def test_main_returns_zero(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        result = main()

    assert result == 0
    assert "Quantsail Engine starting" in caplog.text


def test_root_main_returns_zero() -> None:
    assert run_main() == 0


def test_main_respects_max_ticks_env_var(caplog: LogCaptureFixture) -> None:
    with patch.dict(os.environ, {"MAX_TICKS": "1"}):
        with caplog.at_level(logging.INFO):
            result = main()
    
    assert result == 0
    assert "max_ticks=1" in caplog.text


def test_main_config_load_error(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)
    with patch("quantsail_engine.main.load_config", side_effect=Exception("Config broken")):
        result = main()
    
    assert result == 1
    assert "Failed to load configuration: Config broken" in caplog.text


def test_main_db_connection_error(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)
    with patch("quantsail_engine.main.create_engine", side_effect=Exception("DB down")):
        result = main()
    
    assert result == 1
    assert "Database connection failed: DB down" in caplog.text


def test_main_keyboard_interrupt(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    # Mock TradingLoop to raise KeyboardInterrupt on run()
    with patch("quantsail_engine.main.TradingLoop") as mock_cls:
        mock_instance = mock_cls.return_value
        mock_instance.run.side_effect = KeyboardInterrupt()
        
        result = main()
    
    assert result == 0
    assert "Shutdown requested by user" in caplog.text
    assert "Engine stopped" in caplog.text


def test_main_runtime_error(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)
    # Mock TradingLoop to raise RuntimeError on run()
    with patch("quantsail_engine.main.TradingLoop") as mock_cls:
        mock_instance = mock_cls.return_value
        mock_instance.run.side_effect = RuntimeError("Crash")
        
        result = main()
    
    assert result == 1
    assert "Trading loop error: Crash" in caplog.text


def test_main_live_mode_requires_keys(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)
    live_config = BotConfig(execution=ExecutionConfig(mode="live"))

    with patch("quantsail_engine.main.load_config", return_value=live_config), \
        patch.dict(os.environ, {"MASTER_KEY": "11" * 32}, clear=False), \
        patch("quantsail_engine.persistence.repository.EngineRepository.get_active_exchange_credentials", return_value=None), \
        patch("quantsail_engine.main.TradingLoop") as mock_loop:
        # Clear BINANCE keys to force failure
        if "BINANCE_API_KEY" in os.environ: del os.environ["BINANCE_API_KEY"]
        if "BINANCE_SECRET" in os.environ: del os.environ["BINANCE_SECRET"]
        
        mock_loop.return_value.run.return_value = None
        result = main()

    assert result == 1
    assert "Live mode requires active exchange keys" in caplog.text


def test_main_live_mode_uses_db_keys(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    live_config = BotConfig(execution=ExecutionConfig(mode="live"))
    creds = DecryptedCredentials(api_key="api", secret_key="secret")

    with patch("quantsail_engine.main.load_config", return_value=live_config), \
        patch.dict(os.environ, {"MASTER_KEY": "22" * 32, "BINANCE_TESTNET": "false"}, clear=False), \
        patch("quantsail_engine.persistence.repository.EngineRepository.get_active_exchange_credentials", return_value=creds), \
        patch("quantsail_engine.execution.binance_adapter.BinanceSpotAdapter") as mock_adapter, \
        patch("quantsail_engine.main.TradingLoop") as mock_loop:
        mock_loop.return_value.run.return_value = None
        result = main()

    assert result == 0
    mock_adapter.assert_called_with("api", "secret", testnet=False)
