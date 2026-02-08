"""Tests for Prometheus MetricsService."""

from unittest.mock import MagicMock, patch

import pytest

from quantsail_engine.monitoring.metrics import (
    MetricsConfig,
    MetricsService,
    get_metrics,
    init_metrics,
)


class TestMetricsConfig:
    """Test suite for MetricsConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MetricsConfig()
        assert config.enabled is True
        assert config.port == 9090
        assert config.prefix == "quantsail"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = MetricsConfig(enabled=False, port=8080, prefix="trading")
        assert config.enabled is False
        assert config.port == 8080
        assert config.prefix == "trading"


class TestMetricsServiceDisabled:
    """Test MetricsService when disabled."""

    @pytest.fixture
    def disabled_service(self):
        """Create a disabled metrics service."""
        config = MetricsConfig(enabled=False)
        return MetricsService(config)

    def test_is_enabled_false(self, disabled_service):
        """Test is_enabled property when disabled."""
        assert disabled_service.is_enabled is False

    def test_start_server_returns_false(self, disabled_service):
        """Test start_server returns False when disabled."""
        assert disabled_service.start_server() is False

    def test_record_methods_do_nothing(self, disabled_service):
        """Test recording methods don't error when disabled."""
        # These should not raise
        disabled_service.record_trade_opened("BTC/USDT", "buy")
        disabled_service.record_trade_closed("BTC/USDT", "buy", 10.0)
        disabled_service.set_equity(1000.0)
        disabled_service.set_daily_pnl(50.0)
        disabled_service.record_breaker_trigger("daily_loss")
        disabled_service.record_gate_rejection("insufficient_profit")
        disabled_service.set_kill_switch_active(True)
        disabled_service.set_open_positions(5)
        disabled_service.record_signal("ETH/USDT", "buy")


class TestMetricsServiceEnabled:
    """Test MetricsService when enabled with manually injected mocks."""

    @pytest.fixture
    def service_with_mocks(self):
        """Create service and inject mock metrics."""
        config = MetricsConfig(enabled=True)
        service = MetricsService.__new__(MetricsService)
        service.config = config
        service._server_started = False
        
        # Create mock metrics
        service._trades_total = MagicMock()
        service._trades_opened = MagicMock()
        service._trades_closed = MagicMock()
        service._trade_pnl = MagicMock()
        service._equity = MagicMock()
        service._daily_pnl = MagicMock()
        service._breaker_triggers = MagicMock()
        service._gate_rejections = MagicMock()
        service._kill_switch_active = MagicMock()
        service._open_positions = MagicMock()
        service._signals_generated = MagicMock()
        
        return service

    def test_is_enabled_true(self, service_with_mocks):
        """Test is_enabled when enabled."""
        assert service_with_mocks.is_enabled is True

    def test_record_trade_opened(self, service_with_mocks):
        """Test recording trade opened."""
        service_with_mocks.record_trade_opened("BTC/USDT", "buy")
        
        service_with_mocks._trades_opened.labels.assert_called_with(
            symbol="BTC/USDT", side="buy"
        )

    def test_record_trade_closed_win(self, service_with_mocks):
        """Test recording winning trade."""
        service_with_mocks.record_trade_closed("ETH/USDT", "sell", pnl=15.50)
        
        service_with_mocks._trades_closed.labels.assert_called_with(
            symbol="ETH/USDT", side="sell", result="win"
        )
        service_with_mocks._trade_pnl.observe.assert_called_with(15.50)

    def test_record_trade_closed_loss(self, service_with_mocks):
        """Test recording losing trade."""
        service_with_mocks.record_trade_closed("ETH/USDT", "buy", pnl=-5.25)
        
        service_with_mocks._trades_closed.labels.assert_called_with(
            symbol="ETH/USDT", side="buy", result="loss"
        )
        service_with_mocks._trade_pnl.observe.assert_called_with(-5.25)

    def test_record_trade_closed_breakeven(self, service_with_mocks):
        """Test recording breakeven trade."""
        service_with_mocks.record_trade_closed("XRP/USDT", "buy", pnl=0.0)
        
        service_with_mocks._trades_closed.labels.assert_called_with(
            symbol="XRP/USDT", side="buy", result="breakeven"
        )

    def test_record_trade_closed_explicit_result(self, service_with_mocks):
        """Test recording trade with explicit result."""
        service_with_mocks.record_trade_closed(
            "SOL/USDT", "sell", pnl=0.0, result="manual_close"
        )
        
        service_with_mocks._trades_closed.labels.assert_called_with(
            symbol="SOL/USDT", side="sell", result="manual_close"
        )

    def test_set_equity(self, service_with_mocks):
        """Test setting equity gauge."""
        service_with_mocks.set_equity(10500.00)
        service_with_mocks._equity.set.assert_called_with(10500.00)

    def test_set_daily_pnl(self, service_with_mocks):
        """Test setting daily PnL gauge."""
        service_with_mocks.set_daily_pnl(75.25)
        service_with_mocks._daily_pnl.set.assert_called_with(75.25)

    def test_record_breaker_trigger(self, service_with_mocks):
        """Test recording circuit breaker trigger."""
        service_with_mocks.record_breaker_trigger("daily_loss")
        service_with_mocks._breaker_triggers.labels.assert_called_with(
            breaker_type="daily_loss"
        )

    def test_record_gate_rejection(self, service_with_mocks):
        """Test recording gate rejection."""
        service_with_mocks.record_gate_rejection("high_spread")
        service_with_mocks._gate_rejections.labels.assert_called_with(reason="high_spread")

    def test_set_kill_switch_active_true(self, service_with_mocks):
        """Test setting kill switch active."""
        service_with_mocks.set_kill_switch_active(True)
        service_with_mocks._kill_switch_active.set.assert_called_with(1)

    def test_set_kill_switch_active_false(self, service_with_mocks):
        """Test setting kill switch inactive."""
        service_with_mocks.set_kill_switch_active(False)
        service_with_mocks._kill_switch_active.set.assert_called_with(0)

    def test_set_open_positions(self, service_with_mocks):
        """Test setting open positions count."""
        service_with_mocks.set_open_positions(3)
        service_with_mocks._open_positions.set.assert_called_with(3)

    def test_record_signal(self, service_with_mocks):
        """Test recording signal."""
        service_with_mocks.record_signal("BTC/USDT", "buy")
        service_with_mocks._signals_generated.labels.assert_called_with(
            symbol="BTC/USDT", signal_type="buy"
        )


class TestModuleFunctions:
    """Test module-level convenience functions."""

    def test_init_and_get_metrics(self):
        """Test init_metrics and get_metrics."""
        import quantsail_engine.monitoring.metrics as metrics_module
        metrics_module._metrics = None
        
        config = MetricsConfig(enabled=False)
        service = init_metrics(config)
        
        assert service is not None
        assert get_metrics() is service

    def test_get_metrics_returns_none_before_init(self):
        """Test get_metrics returns None if not initialized."""
        import quantsail_engine.monitoring.metrics as metrics_module
        metrics_module._metrics = None
        
        assert get_metrics() is None


class TestMetricsServiceNoneHandling:
    """Test that methods handle None metrics gracefully."""

    def test_record_with_none_metrics(self):
        """Test recording methods when metrics are None."""
        config = MetricsConfig(enabled=True)
        service = MetricsService.__new__(MetricsService)
        service.config = config
        
        # Set all metrics to None 
        service._trades_total = None
        service._trades_opened = None
        service._trades_closed = None
        service._trade_pnl = None
        service._equity = None
        service._daily_pnl = None
        service._breaker_triggers = None
        service._gate_rejections = None
        service._kill_switch_active = None
        service._open_positions = None
        service._signals_generated = None
        
        # None of these should raise
        service.record_trade_opened("BTC/USDT", "buy")
        service.record_trade_closed("BTC/USDT", "buy", 10.0)
        service.set_equity(1000.0)
        service.set_daily_pnl(50.0)
        service.record_breaker_trigger("daily_loss")
        service.record_gate_rejection("insufficient_profit")
        service.set_kill_switch_active(True)
        service.set_open_positions(5)
        service.record_signal("ETH/USDT", "buy")


import sys


@pytest.fixture
def mock_prometheus(monkeypatch):
    """Inject a mock prometheus_client module into sys.modules.

    This makes ``from prometheus_client import Counter, Gauge, Histogram``
    and ``from prometheus_client import start_http_server`` resolve even when
    the real package is not installed.  Every Counter/Gauge/Histogram call
    returns a fresh MagicMock, which is good enough for coverage.
    """
    fake_mod = MagicMock()
    fake_mod.Counter = MagicMock(side_effect=lambda *a, **kw: MagicMock())
    fake_mod.Gauge = MagicMock(side_effect=lambda *a, **kw: MagicMock())
    fake_mod.Histogram = MagicMock(side_effect=lambda *a, **kw: MagicMock())
    fake_mod.start_http_server = MagicMock()

    monkeypatch.setitem(sys.modules, "prometheus_client", fake_mod)
    return fake_mod



class TestMetricsServerStartup:
    """Test the HTTP server startup logic."""

    def test_start_server_success(self, mock_prometheus):
        """Test successful server startup."""
        import threading
        config = MetricsConfig(enabled=True, port=9191)
        service = MetricsService.__new__(MetricsService)
        service.config = config
        service._server_started = False
        service._lock = threading.Lock()

        result = service.start_server()

        assert result is True
        assert service._server_started is True
        mock_prometheus.start_http_server.assert_called_once_with(9191)

    def test_start_server_already_started(self, mock_prometheus):
        """Test start_server when already started."""
        import threading
        config = MetricsConfig(enabled=True)
        service = MetricsService.__new__(MetricsService)
        service.config = config
        service._server_started = True
        service._lock = threading.Lock()

        result = service.start_server()

        assert result is True
        mock_prometheus.start_http_server.assert_not_called()

    def test_start_server_exception(self, mock_prometheus):
        """Test start_server handles exceptions."""
        import threading
        mock_prometheus.start_http_server.side_effect = Exception("Port already in use")

        config = MetricsConfig(enabled=True)
        service = MetricsService.__new__(MetricsService)
        service.config = config
        service._server_started = False
        service._lock = threading.Lock()

        result = service.start_server()

        assert result is False
        assert service._server_started is False


class TestMetricsInitialization:
    """Test _initialize_metrics edge cases."""

    def test_initialize_with_disabled_config(self):
        """Test that disabled config skips metric initialization."""
        config = MetricsConfig(enabled=False)
        service = MetricsService(config)

        assert service._trades_total is None
        assert service._equity is None
        assert service.is_enabled is False

    def test_initialize_with_enabled_config_creates_real_metrics(self, mock_prometheus):
        """Test that enabled config creates real prometheus metrics."""
        config = MetricsConfig(enabled=True, prefix="test_quantsail")
        service = MetricsService(config)

        # Should have created real prometheus metrics (not None)
        assert service._trades_total is not None
        assert service._trades_opened is not None
        assert service._trades_closed is not None
        assert service._trade_pnl is not None
        assert service._equity is not None
        assert service._daily_pnl is not None
        assert service._breaker_triggers is not None
        assert service._gate_rejections is not None
        assert service._kill_switch_active is not None
        assert service._open_positions is not None
        assert service._signals_generated is not None
        assert service.is_enabled is True

    def test_real_metrics_can_record_values(self, mock_prometheus):
        """Test that real initialized metrics can record values."""
        config = MetricsConfig(enabled=True, prefix="test_record")
        service = MetricsService(config)

        # Should not raise exceptions
        service.record_trade_opened("BTC/USDT", "buy")
        service.record_trade_closed("ETH/USDT", "sell", pnl=100.0, result="win")
        service.set_equity(10000.0)
        service.set_daily_pnl(250.0)
        service.record_breaker_trigger("volatility")
        service.record_gate_rejection("profitability")
        service.set_kill_switch_active(True)
        service.set_open_positions(3)
        service.record_signal("BTC/USDT", "ENTER_LONG")
