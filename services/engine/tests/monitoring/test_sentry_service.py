"""Tests for Sentry service."""

import pytest
from unittest.mock import MagicMock, patch, ANY

from quantsail_engine.monitoring.sentry_service import (
    SentryConfig,
    SentryLevel,
    SentryService,
    init_sentry,
    get_sentry,
    SENTRY_AVAILABLE,
)


class TestSentryConfig:
    """Test suite for SentryConfig."""

    def test_default_values(self):
        """Test default configuration."""
        config = SentryConfig(dsn="https://test@sentry.io/123")
        assert config.environment == "development"
        assert config.traces_sample_rate == 0.1
        assert config.enabled is True

    def test_ignore_errors_default(self):
        """Test default ignored errors."""
        config = SentryConfig(dsn="test")
        assert "ConnectionResetError" in config.ignore_errors
        assert "asyncio.CancelledError" in config.ignore_errors


class TestSentryService:
    """Test suite for SentryService."""

    @pytest.fixture
    def config(self) -> SentryConfig:
        """Create test config."""
        return SentryConfig(
            dsn="https://test@sentry.io/123",
            environment="test",
        )

    @pytest.fixture
    def service(self, config: SentryConfig) -> SentryService:
        """Create service with test config."""
        return SentryService(config)

    @pytest.fixture
    def initialized_service(self, config: SentryConfig) -> SentryService:
        """Create an initialized service with mocked sentry_sdk."""
        service = SentryService(config)
        service._initialized = True  # Simulate initialization
        return service

    # ── initialized service tests require SENTRY_AVAILABLE patched ──

    def test_init(self, service: SentryService, config: SentryConfig):
        """Test service initialization."""
        assert service.config == config
        assert service._initialized is False

    def test_initialize_disabled(self, config: SentryConfig):
        """Test initialization when disabled."""
        config.enabled = False
        service = SentryService(config)
        result = service.initialize()
        assert result is False
        assert service._initialized is False

    def test_initialize_no_dsn(self, config: SentryConfig):
        """Test initialization without DSN."""
        config.dsn = ""
        service = SentryService(config)
        result = service.initialize()
        assert result is False

    def test_capture_error_not_initialized(self, service: SentryService):
        """Test capture_error when not initialized."""
        result = service.capture_error(ValueError("test"))
        assert result is None

    def test_capture_warning_not_initialized(self, service: SentryService):
        """Test capture_warning when not initialized."""
        result = service.capture_warning("test warning")
        assert result is None

    def test_add_breadcrumb_not_initialized(self, service: SentryService):
        """Test add_breadcrumb when not initialized."""
        # Should not raise
        service.add_breadcrumb("test", "message")

    def test_set_trading_context_not_initialized(self, service: SentryService):
        """Test set_trading_context when not initialized."""
        # Should not raise
        service.set_trading_context(symbol="BTC/USDT")

    def test_transaction_not_initialized(self, service: SentryService):
        """Test transaction context manager when not initialized."""
        with service.transaction("test", "name") as tx:
            assert tx is None

    def test_span_not_initialized(self, service: SentryService):
        """Test span context manager when not initialized."""
        with service.span("test", "description") as span:
            assert span is None

    def test_flush_not_initialized(self, service: SentryService):
        """Test flush when not initialized."""
        # Should not raise
        service.flush()

    def test_scrub_sensitive_data(self, service: SentryService):
        """Test sensitive data scrubbing."""
        event = {
            "api_key": "secret123",
            "user": "test",
            "nested": {
                "password": "hidden",
                "data": "visible",
            },
        }
        scrubbed = service._scrub_sensitive_data(event)
        assert scrubbed["api_key"] == "[REDACTED]"
        assert scrubbed["user"] == "test"
        assert scrubbed["nested"]["password"] == "[REDACTED]"
        assert scrubbed["nested"]["data"] == "visible"

    def test_scrub_sensitive_data_list(self, service: SentryService):
        """Test scrubbing with nested lists."""
        event = {
            "items": [
                {"token": "secret", "name": "test"},
                {"value": "ok"},
            ],
        }
        scrubbed = service._scrub_sensitive_data(event)
        assert scrubbed["items"][0]["token"] == "[REDACTED]"
        assert scrubbed["items"][0]["name"] == "test"
        assert scrubbed["items"][1]["value"] == "ok"

    def test_get_release_from_env(self, service: SentryService):
        """Test release version from environment."""
        with patch.dict("os.environ", {"SENTRY_RELEASE": "v1.0.0"}):
            release = service._get_release()
            assert release == "v1.0.0"

    # Tests for initialized service
    @patch("quantsail_engine.monitoring.sentry_service.capture_exception")
    @patch("quantsail_engine.monitoring.sentry_service.set_context")
    @patch("quantsail_engine.monitoring.sentry_service.set_tag")
    def test_capture_error_initialized(
        self, mock_set_tag, mock_set_context, mock_capture, initialized_service
    ):
        """Test capture_error when initialized with context and tags."""
        mock_capture.return_value = "event-id-123"
        
        result = initialized_service.capture_error(
            ValueError("test"),
            context={"key": "value"},
            tags={"tag1": "val1"},
        )
        
        mock_set_context.assert_called_once_with("trading_context", {"key": "value"})
        mock_set_tag.assert_called_once_with("tag1", "val1")
        mock_capture.assert_called_once()
        assert result == "event-id-123"

    @patch("quantsail_engine.monitoring.sentry_service.capture_message")
    @patch("quantsail_engine.monitoring.sentry_service.set_context")
    @patch("quantsail_engine.monitoring.sentry_service.set_tag")
    def test_capture_warning_initialized(
        self, mock_set_tag, mock_set_context, mock_capture, initialized_service
    ):
        """Test capture_warning when initialized with context and tags."""
        mock_capture.return_value = "warn-id-456"
        
        result = initialized_service.capture_warning(
            "warning message",
            context={"ctx": "data"},
            tags={"severity": "high"},
        )
        
        mock_set_context.assert_called_once_with("trading_context", {"ctx": "data"})
        mock_set_tag.assert_called_once_with("severity", "high")
        mock_capture.assert_called_once_with("warning message", level="warning")
        assert result == "warn-id-456"

    @patch("quantsail_engine.monitoring.sentry_service.SENTRY_AVAILABLE", True)
    @patch("quantsail_engine.monitoring.sentry_service.sentry_sdk")
    def test_add_breadcrumb_initialized(self, mock_sdk, initialized_service):
        """Test add_breadcrumb when initialized."""
        initialized_service.add_breadcrumb(
            category="trade",
            message="Opened position",
            data={"price": 50000},
            level="info",
        )
        
        mock_sdk.add_breadcrumb.assert_called_once_with(
            category="trade",
            message="Opened position",
            data={"price": 50000},
            level="info",
        )

    @patch("quantsail_engine.monitoring.sentry_service.set_context")
    @patch("quantsail_engine.monitoring.sentry_service.set_tag")
    def test_set_trading_context_initialized(
        self, mock_set_tag, mock_set_context, initialized_service
    ):
        """Test set_trading_context when initialized with all params."""
        initialized_service.set_trading_context(
            symbol="ETH/USDT",
            strategy="breakout",
            position={"side": "long"},
            equity=10000.0,
        )
        
        # Should set tags for symbol and strategy
        assert mock_set_tag.call_count == 2
        mock_set_tag.assert_any_call("symbol", "ETH/USDT")
        mock_set_tag.assert_any_call("strategy", "breakout")
        
        # Should set context with all fields
        mock_set_context.assert_called_once()
        context_call = mock_set_context.call_args
        assert context_call[0][0] == "trading"
        ctx_data = context_call[0][1]
        assert ctx_data["symbol"] == "ETH/USDT"
        assert ctx_data["strategy"] == "breakout"
        assert ctx_data["position"] == {"side": "long"}
        assert ctx_data["equity"] == 10000.0

    @patch("quantsail_engine.monitoring.sentry_service.SENTRY_AVAILABLE", True)
    @patch("quantsail_engine.monitoring.sentry_service.sentry_sdk")
    def test_transaction_initialized(self, mock_sdk, initialized_service):
        """Test transaction context manager when initialized."""
        mock_tx = MagicMock()
        mock_sdk.start_transaction.return_value.__enter__ = MagicMock(return_value=mock_tx)
        mock_sdk.start_transaction.return_value.__exit__ = MagicMock(return_value=False)
        
        with initialized_service.transaction("backtest", "run", "desc") as tx:
            assert tx == mock_tx
        
        mock_sdk.start_transaction.assert_called_once_with(
            op="backtest", name="run", description="desc"
        )

    @patch("quantsail_engine.monitoring.sentry_service.SENTRY_AVAILABLE", True)
    @patch("quantsail_engine.monitoring.sentry_service.Hub")
    def test_span_initialized(self, mock_hub_class, initialized_service):
        """Test span context manager when initialized."""
        mock_hub = MagicMock()
        mock_span = MagicMock()
        mock_hub.start_span.return_value = mock_span
        mock_hub_class.current = mock_hub
        
        with initialized_service.span("calculate", "computing pnl") as span:
            assert span == mock_span
        
        mock_hub.start_span.assert_called_once_with(op="calculate", description="computing pnl")
        mock_span.finish.assert_called_once()

    @patch("quantsail_engine.monitoring.sentry_service.SENTRY_AVAILABLE", True)
    @patch("quantsail_engine.monitoring.sentry_service.sentry_sdk")
    def test_flush_initialized(self, mock_sdk, initialized_service):
        """Test flush when initialized."""
        initialized_service.flush(timeout=5.0)
        mock_sdk.flush.assert_called_once_with(timeout=5.0)

    def test_before_send_filters_ignored_error(self, service: SentryService):
        """Test _before_send filters ignored errors."""
        # Add an error to ignore
        service.config.ignore_errors.append("ValueError")
        
        hint = {"exc_info": (ValueError, ValueError("test"), None)}
        event = {"message": "test error"}
        
        result = service._before_send(event, hint)
        assert result is None  # Should be filtered out

    def test_before_send_passes_non_ignored_error(self, service: SentryService):
        """Test _before_send passes non-ignored errors through."""
        hint = {"exc_info": (RuntimeError, RuntimeError("test"), None)}
        event = {"message": "test error", "api_key": "secret"}
        
        result = service._before_send(event, hint)
        # Should scrub and return
        assert result is not None
        assert result["api_key"] == "[REDACTED]"

    def test_before_send_no_exc_info(self, service: SentryService):
        """Test _before_send without exception info."""
        hint = {}
        event = {"message": "test", "token": "secret123"}
        
        result = service._before_send(event, hint)
        assert result is not None
        assert result["token"] == "[REDACTED]"


class TestModuleFunctions:
    """Test module-level convenience functions."""

    @patch("quantsail_engine.monitoring.sentry_service.SentryService")
    def test_init_sentry(self, mock_service_class):
        """Test init_sentry creates and initializes service."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        config = SentryConfig(dsn="https://test@sentry.io/123")
        result = init_sentry(config)
        
        mock_service_class.assert_called_once_with(config)
        mock_service.initialize.assert_called_once()
        assert result == mock_service

    def test_get_sentry_returns_none_when_not_initialized(self):
        """Test get_sentry returns None when not initialized."""
        import quantsail_engine.monitoring.sentry_service as sentry_module
        
        # Save and reset the global
        original = sentry_module._service
        sentry_module._service = None
        
        try:
            result = get_sentry()
            assert result is None
        finally:
            sentry_module._service = original

    def test_get_sentry_returns_service_when_initialized(self):
        """Test get_sentry returns service when initialized."""
        import quantsail_engine.monitoring.sentry_service as sentry_module
        
        mock_service = MagicMock()
        original = sentry_module._service
        sentry_module._service = mock_service
        
        try:
            result = get_sentry()
            assert result == mock_service
        finally:
            sentry_module._service = original


@patch("quantsail_engine.monitoring.sentry_service.SENTRY_AVAILABLE", True)
class TestSentryRealInitialization:
    """Test real sentry SDK initialization (when sentry_sdk is available)."""

    @patch("quantsail_engine.monitoring.sentry_service.LoggingIntegration", create=True)
    @patch("quantsail_engine.monitoring.sentry_service.HttpxIntegration", create=True)
    @patch("quantsail_engine.monitoring.sentry_service.AsyncioIntegration", create=True)
    @patch("quantsail_engine.monitoring.sentry_service.sentry_sdk")
    def test_initialize_calls_sentry_sdk_init(self, mock_sentry_sdk, *_mocks):
        """Test initialize calls sentry_sdk.init with correct parameters."""
        config = SentryConfig(
            dsn="https://test@sentry.io/123",
            environment="test",
            traces_sample_rate=0.5,
        )
        service = SentryService(config)
        
        result = service.initialize()
        
        assert result is True
        mock_sentry_sdk.init.assert_called_once()
        call_kwargs = mock_sentry_sdk.init.call_args.kwargs
        assert call_kwargs["dsn"] == "https://test@sentry.io/123"
        assert call_kwargs["environment"] == "test"
        assert call_kwargs["traces_sample_rate"] == 0.5

    @patch("quantsail_engine.monitoring.sentry_service.sentry_sdk")
    def test_initialize_exception_returns_false(self, mock_sentry_sdk):
        """Test initialize returns False when sentry_sdk.init raises exception."""
        mock_sentry_sdk.init.side_effect = Exception("Init failed")
        
        config = SentryConfig(dsn="https://test@sentry.io/123")
        service = SentryService(config)
        
        result = service.initialize()
        
        assert result is False
        assert service._initialized is False

    @patch("subprocess.run")
    def test_get_release_from_git(self, mock_run):
        """Test _get_release falls back to git commit hash."""
        import os
        # Remove the env var if set
        original = os.environ.get("SENTRY_RELEASE")
        if "SENTRY_RELEASE" in os.environ:
            del os.environ["SENTRY_RELEASE"]
        
        mock_run.return_value = MagicMock(returncode=0, stdout="abc1234\n")
        
        config = SentryConfig(dsn="https://test@sentry.io/123")
        service = SentryService(config)
        
        result = service._get_release()
        
        assert result == "quantsail@abc1234"
        
        # Restore
        if original is not None:
            os.environ["SENTRY_RELEASE"] = original

    @patch("subprocess.run")
    def test_get_release_git_failure_returns_unknown(self, mock_run):
        """Test _get_release returns unknown when git fails."""
        import os
        original = os.environ.get("SENTRY_RELEASE")
        if "SENTRY_RELEASE" in os.environ:
            del os.environ["SENTRY_RELEASE"]
        
        mock_run.side_effect = Exception("git not found")
        
        config = SentryConfig(dsn="https://test@sentry.io/123")
        service = SentryService(config)
        
        result = service._get_release()
        
        assert result == "quantsail@unknown"
        
        if original is not None:
            os.environ["SENTRY_RELEASE"] = original

