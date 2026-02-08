"""Tests for Telegram alerter service."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from quantsail_engine.alerts.telegram import (
    Alert,
    AlertPriority,
    AlertType,
    TelegramAlerter,
    TelegramConfig,
)


class TestAlert:
    """Test suite for Alert dataclass."""

    def test_to_telegram_message_basic(self):
        """Test basic message formatting."""
        alert = Alert(
            alert_type=AlertType.TRADE_OPENED,
            priority=AlertPriority.MEDIUM,
            title="Trade Opened",
            message="BTC position opened",
        )
        msg = alert.to_telegram_message()
        assert "*Trade Opened*" in msg
        assert "BTC position opened" in msg
        assert "📈" in msg  # Trade opened emoji

    def test_to_telegram_message_with_metadata(self):
        """Test message with metadata."""
        alert = Alert(
            alert_type=AlertType.TRADE_CLOSED,
            priority=AlertPriority.MEDIUM,
            title="Trade Closed",
            message="Position closed",
            metadata={"symbol": "BTC/USDT", "pnl": "+100"},
        )
        msg = alert.to_telegram_message()
        assert "Symbol: `BTC/USDT`" in msg
        assert "Pnl: `+100`" in msg

    def test_to_telegram_message_critical_priority(self):
        """Test critical priority formatting."""
        alert = Alert(
            alert_type=AlertType.BREAKER_ACTIVATED,
            priority=AlertPriority.CRITICAL,
            title="Emergency Stop",
            message="Trading halted",
        )
        msg = alert.to_telegram_message()
        assert "🔴 CRITICAL:" in msg
        assert "🚨" in msg  # Breaker emoji

    def test_to_telegram_message_high_priority(self):
        """Test high priority formatting."""
        alert = Alert(
            alert_type=AlertType.GATE_TRIGGERED,
            priority=AlertPriority.HIGH,
            title="Gate Activated",
            message="Position reduced",
        )
        msg = alert.to_telegram_message()
        assert "🟠" in msg

    def test_get_emoji_all_types(self):
        """Test emoji mapping for all alert types."""
        emoji_map = {
            AlertType.TRADE_OPENED: "📈",
            AlertType.TRADE_CLOSED: "📊",
            AlertType.POSITION_SIZED: "⚖️",
            AlertType.GATE_TRIGGERED: "🚧",
            AlertType.BREAKER_ACTIVATED: "🚨",
            AlertType.DAILY_SUMMARY: "📋",
            AlertType.ERROR: "❌",
            AlertType.SYSTEM_STATUS: "ℹ️",
        }
        for alert_type, expected_emoji in emoji_map.items():
            alert = Alert(
                alert_type=alert_type,
                priority=AlertPriority.LOW,
                title="Test",
                message="Test message",
            )
            assert expected_emoji in alert.to_telegram_message()


class TestTelegramConfig:
    """Test suite for TelegramConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TelegramConfig(bot_token="token", chat_id="123")
        assert config.enabled is True
        assert config.min_priority == AlertPriority.LOW
        assert config.max_alerts_per_minute == 10
        assert config.max_errors_per_hour == 5


class TestTelegramAlerter:
    """Test suite for TelegramAlerter."""

    @pytest.fixture
    def config(self) -> TelegramConfig:
        """Create test configuration."""
        return TelegramConfig(
            bot_token="test_token",
            chat_id="123456",
        )

    @pytest.fixture
    def alerter(self, config: TelegramConfig) -> TelegramAlerter:
        """Create alerter with test config."""
        return TelegramAlerter(config)

    def test_init(self, alerter: TelegramAlerter, config: TelegramConfig):
        """Test alerter initialization."""
        assert alerter.config == config
        assert alerter._client is None
        assert alerter._alert_timestamps == []

    @pytest.mark.asyncio
    async def test_send_alert_disabled(self, config: TelegramConfig):
        """Test alerter respects disabled flag."""
        config.enabled = False
        alerter = TelegramAlerter(config)
        
        alert = Alert(
            alert_type=AlertType.TRADE_OPENED,
            priority=AlertPriority.HIGH,
            title="Test",
            message="Test",
        )
        
        result = await alerter.send_alert(alert)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_priority_filter(self, config: TelegramConfig):
        """Test priority filtering."""
        config.min_priority = AlertPriority.HIGH
        alerter = TelegramAlerter(config)
        
        # Low priority should be filtered
        alert = Alert(
            alert_type=AlertType.DAILY_SUMMARY,
            priority=AlertPriority.LOW,
            title="Summary",
            message="Daily summary",
        )
        
        result = await alerter.send_alert(alert)
        assert result is False
        
        # Medium priority also filtered
        alert.priority = AlertPriority.MEDIUM
        result = await alerter.send_alert(alert)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_rate_limited(self, alerter: TelegramAlerter):
        """Test rate limiting blocks send_alert."""
        now = datetime.now(timezone.utc)
        # Fill up rate limit
        alerter._alert_timestamps = [now for _ in range(15)]
        
        alert = Alert(
            alert_type=AlertType.TRADE_OPENED,
            priority=AlertPriority.MEDIUM,
            title="Test",
            message="Test",
        )
        
        # send_alert should return False due to rate limit (covers line 178)
        result = await alerter.send_alert(alert)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_success(self, alerter: TelegramAlerter):
        """Test successful alert sending."""
        with patch.object(alerter, "_send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            alert = Alert(
                alert_type=AlertType.TRADE_OPENED,
                priority=AlertPriority.MEDIUM,
                title="Trade",
                message="Test trade",
            )
            
            result = await alerter.send_alert(alert)
            
            assert result is True
            mock_send.assert_called_once()
            assert len(alerter._alert_timestamps) == 1

    @pytest.mark.asyncio
    async def test_send_trade_opened(self, alerter: TelegramAlerter):
        """Test send_trade_opened helper."""
        with patch.object(alerter, "send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            result = await alerter.send_trade_opened(
                symbol="BTC/USDT",
                side="LONG",
                entry_price=50000.0,
                position_size=0.1,
                strategy="trend",
            )
            
            assert result is True
            call_args = mock_send.call_args[0][0]
            assert call_args.alert_type == AlertType.TRADE_OPENED
            assert call_args.metadata["symbol"] == "BTC/USDT"

    @pytest.mark.asyncio
    async def test_send_trade_closed(self, alerter: TelegramAlerter):
        """Test send_trade_closed helper."""
        with patch.object(alerter, "send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await alerter.send_trade_closed(
                symbol="BTC/USDT",
                side="LONG",
                entry_price=50000.0,
                exit_price=55000.0,
                pnl_usd=500.0,
                pnl_pct=10.0,
            )
            
            call_args = mock_send.call_args[0][0]
            assert call_args.alert_type == AlertType.TRADE_CLOSED
            assert "🟢" in call_args.title  # Positive P&L

    @pytest.mark.asyncio
    async def test_send_trade_closed_loss(self, alerter: TelegramAlerter):
        """Test send_trade_closed with loss."""
        with patch.object(alerter, "send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await alerter.send_trade_closed(
                symbol="BTC/USDT",
                side="LONG",
                entry_price=50000.0,
                exit_price=48000.0,
                pnl_usd=-200.0,
                pnl_pct=-4.0,
            )
            
            call_args = mock_send.call_args[0][0]
            assert "🔴" in call_args.title  # Negative P&L

    @pytest.mark.asyncio
    async def test_send_breaker_activated(self, alerter: TelegramAlerter):
        """Test send_breaker_activated helper."""
        with patch.object(alerter, "send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await alerter.send_breaker_activated(
                breaker_name="daily_loss",
                reason="Max daily loss exceeded",
                cooldown_minutes=60,
            )
            
            call_args = mock_send.call_args[0][0]
            assert call_args.alert_type == AlertType.BREAKER_ACTIVATED
            assert call_args.priority == AlertPriority.CRITICAL
            assert call_args.metadata["cooldown"] == "60 min"

    @pytest.mark.asyncio
    async def test_send_gate_triggered(self, alerter: TelegramAlerter):
        """Test send_gate_triggered helper."""
        with patch.object(alerter, "send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await alerter.send_gate_triggered(
                gate_name="margin_check",
                action="position_reduced",
                details="Position reduced by 50%",
            )
            
            call_args = mock_send.call_args[0][0]
            assert call_args.alert_type == AlertType.GATE_TRIGGERED
            assert call_args.priority == AlertPriority.HIGH

    @pytest.mark.asyncio
    async def test_send_daily_summary(self, alerter: TelegramAlerter):
        """Test send_daily_summary helper."""
        with patch.object(alerter, "send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await alerter.send_daily_summary(
                date=datetime(2024, 1, 15),
                total_pnl_usd=150.0,
                total_trades=12,
                win_rate=66.7,
                equity=10150.0,
            )
            
            call_args = mock_send.call_args[0][0]
            assert call_args.alert_type == AlertType.DAILY_SUMMARY
            assert call_args.priority == AlertPriority.LOW
            assert "2024-01-15" in call_args.message

    @pytest.mark.asyncio
    async def test_send_error(self, alerter: TelegramAlerter):
        """Test send_error helper."""
        with patch.object(alerter, "send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await alerter.send_error(
                error_type="ConnectionError",
                message="Failed to connect to exchange",
            )
            
            call_args = mock_send.call_args[0][0]
            assert call_args.alert_type == AlertType.ERROR
            assert len(alerter._error_timestamps) == 1

    @pytest.mark.asyncio
    async def test_send_error_throttled(self, alerter: TelegramAlerter):
        """Test error rate limiting."""
        alerter._error_timestamps = [
            datetime.now(timezone.utc) for _ in range(10)
        ]
        
        result = await alerter.send_error(
            error_type="Test",
            message="Should be throttled",
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_context_manager(self, config: TelegramConfig):
        """Test async context manager."""
        async with TelegramAlerter(config) as alerter:
            assert alerter._client is not None
        
        # Client should be closed after exiting
        assert alerter._client is None

    def test_check_rate_limit_cleans_old(self, alerter: TelegramAlerter):
        """Test rate limit cleanup of old timestamps."""
        from datetime import timedelta
        
        old = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent = datetime.now(timezone.utc)
        
        alerter._alert_timestamps = [old, old, recent]
        
        # Should clean old timestamps and allow
        assert alerter._check_rate_limit() is True
        assert len(alerter._alert_timestamps) == 1


class TestTelegramHTTPSending:
    """Tests for HTTP sending methods with mocked httpx."""

    @pytest.fixture
    def config(self) -> TelegramConfig:
        """Create test configuration."""
        return TelegramConfig(
            bot_token="test_token",
            chat_id="123456",
        )

    @pytest.fixture
    def alerter(self, config: TelegramConfig) -> TelegramAlerter:
        """Create alerter with test config."""
        return TelegramAlerter(config)

    @pytest.mark.asyncio
    async def test_send_message_without_client(self, alerter: TelegramAlerter):
        """Test _send_message creates temporary client when _client is None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            result = await alerter._send_message("Test message")
            
            assert result is True
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_existing_client(self, alerter: TelegramAlerter):
        """Test _send_message uses existing client when available."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        alerter._client = mock_client
        
        result = await alerter._send_message("Test message")
        
        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_with_client_success(self, alerter: TelegramAlerter):
        """Test successful message send."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        result = await alerter._send_with_client(mock_client, "Test message")
        
        assert result is True
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["text"] == "Test message"
        assert call_args[1]["json"]["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_send_with_client_rate_limited(self, alerter: TelegramAlerter):
        """Test handling Telegram 429 rate limit response."""
        import httpx
        
        mock_rate_limit_response = MagicMock()
        mock_rate_limit_response.status_code = 429
        mock_rate_limit_response.json.return_value = {"parameters": {"retry_after": 0.01}}
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[mock_rate_limit_response, mock_success_response])
        
        result = await alerter._send_with_client(mock_client, "Test message")
        
        assert result is True
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_send_with_client_non_retryable_error(self, alerter: TelegramAlerter):
        """Test handling non-retryable error codes."""
        mock_response = MagicMock()
        mock_response.status_code = 401  # Unauthorized
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        result = await alerter._send_with_client(mock_client, "Test message")
        
        assert result is False
        # Should only try once for non-retryable errors
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_send_with_client_timeout_with_retry(self, alerter: TelegramAlerter):
        """Test timeout handling with retries."""
        import httpx
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            httpx.TimeoutException("Timeout"),
            httpx.TimeoutException("Timeout"),
            mock_success_response,
        ])
        
        result = await alerter._send_with_client(mock_client, "Test message")
        
        assert result is True
        assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_send_with_client_timeout_exhausted(self, alerter: TelegramAlerter):
        """Test timeout handling when all retries exhausted."""
        import httpx
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        
        result = await alerter._send_with_client(mock_client, "Test message")
        
        assert result is False
        assert mock_client.post.call_count == 3  # max_retries

    @pytest.mark.asyncio
    async def test_send_with_client_http_error(self, alerter: TelegramAlerter):
        """Test handling of HTTP errors."""
        import httpx
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
        
        result = await alerter._send_with_client(mock_client, "Test message")
        
        assert result is False
        # Should not retry on generic HTTP errors
        assert mock_client.post.call_count == 1

