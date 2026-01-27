import logging
import os
from unittest.mock import patch

from pytest import LogCaptureFixture

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
