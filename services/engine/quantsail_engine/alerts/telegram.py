"""Telegram alert service for operator notifications.

Provides real-time notifications for:
- Trade executions
- Circuit breaker activations  
- Position size changes
- Daily performance summaries

Follows IMPL_GUIDE requirements for operator alerting.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any

import httpx


class AlertPriority(Enum):
    """Alert priority levels."""
    LOW = auto()      # Daily summaries, minor updates
    MEDIUM = auto()   # Trade executions, position changes
    HIGH = auto()     # Gate activations, margin warnings
    CRITICAL = auto()  # Circuit breaker, emergency stop


class AlertType(Enum):
    """Types of alerts."""
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    POSITION_SIZED = "position_sized"
    GATE_TRIGGERED = "gate_triggered"
    BREAKER_ACTIVATED = "breaker_activated"
    DAILY_SUMMARY = "daily_summary"
    ERROR = "error"
    SYSTEM_STATUS = "system_status"


@dataclass
class Alert:
    """Alert message container."""
    alert_type: AlertType
    priority: AlertPriority
    title: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_telegram_message(self) -> str:
        """Format alert as Telegram message with markdown."""
        emoji = self._get_emoji()
        priority_tag = self._get_priority_tag()
        
        lines = [
            f"{emoji} *{priority_tag}{self.title}*",
            "",
            self.message,
        ]
        
        if self.metadata:
            lines.append("")
            lines.append("_Details:_")
            for key, value in self.metadata.items():
                # Format key nicely
                formatted_key = key.replace("_", " ").title()
                lines.append(f"• {formatted_key}: `{value}`")
        
        lines.append("")
        lines.append(f"🕐 {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return "\n".join(lines)
    
    def _get_emoji(self) -> str:
        """Get emoji based on alert type."""
        emojis = {
            AlertType.TRADE_OPENED: "📈",
            AlertType.TRADE_CLOSED: "📊",
            AlertType.POSITION_SIZED: "⚖️",
            AlertType.GATE_TRIGGERED: "🚧",
            AlertType.BREAKER_ACTIVATED: "🚨",
            AlertType.DAILY_SUMMARY: "📋",
            AlertType.ERROR: "❌",
            AlertType.SYSTEM_STATUS: "ℹ️",
        }
        return emojis.get(self.alert_type, "📌")
    
    def _get_priority_tag(self) -> str:
        """Get priority tag for message title."""
        if self.priority == AlertPriority.CRITICAL:
            return "🔴 CRITICAL: "
        elif self.priority == AlertPriority.HIGH:
            return "🟠 "
        return ""


@dataclass 
class TelegramConfig:
    """Telegram bot configuration."""
    bot_token: str
    chat_id: str
    enabled: bool = True
    # Alert filtering
    min_priority: AlertPriority = AlertPriority.LOW
    # Rate limiting
    max_alerts_per_minute: int = 10
    # Error throttling
    max_errors_per_hour: int = 5


class TelegramAlerter:
    """Telegram notification service.
    
    Sends formatted alerts to a Telegram chat via bot.
    Includes rate limiting, priority filtering, and error handling.
    
    Example:
        >>> config = TelegramConfig(bot_token="xxx", chat_id="123")
        >>> alerter = TelegramAlerter(config)
        >>> await alerter.send_trade_opened(
        ...     symbol="BTC/USDT",
        ...     side="LONG",
        ...     entry_price=50000.0,
        ...     position_size=0.1,
        ... )
    """
    
    TELEGRAM_API_BASE = "https://api.telegram.org"
    
    def __init__(self, config: TelegramConfig):
        """Initialize alerter with configuration.
        
        Args:
            config: Telegram bot configuration
        """
        self.config = config
        self._client: httpx.AsyncClient | None = None
        
        # Rate limiting state
        self._alert_timestamps: list[datetime] = []
        self._error_timestamps: list[datetime] = []
        
        # Retry configuration
        self._max_retries = 3
        self._retry_delay = 1.0
    
    async def __aenter__(self) -> "TelegramAlerter":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send an alert to Telegram.
        
        Args:
            alert: Alert to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.config.enabled:
            return False
        
        # Check priority filter
        if alert.priority.value < self.config.min_priority.value:
            return False
        
        # Check rate limit
        if not self._check_rate_limit():
            return False
        
        # Send message
        success = await self._send_message(alert.to_telegram_message())
        
        if success:
            self._alert_timestamps.append(datetime.now(timezone.utc))
        
        return success
    
    async def send_trade_opened(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        position_size: float,
        strategy: str = "unknown",
        **kwargs: Any,
    ) -> bool:
        """Send trade opened notification.
        
        Args:
            symbol: Trading pair
            side: LONG or SHORT  
            entry_price: Entry price
            position_size: Position size in base currency
            strategy: Strategy name
            **kwargs: Additional metadata
        """
        metadata = {
            "symbol": symbol,
            "side": side,
            "entry_price": f"${entry_price:,.2f}",
            "size": f"{position_size:.4f}",
            "strategy": strategy,
            **kwargs,
        }
        
        alert = Alert(
            alert_type=AlertType.TRADE_OPENED,
            priority=AlertPriority.MEDIUM,
            title=f"Trade Opened: {symbol}",
            message=f"{side} position opened at ${entry_price:,.2f}",
            metadata=metadata,
        )
        return await self.send_alert(alert)
    
    async def send_trade_closed(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        pnl_usd: float,
        pnl_pct: float,
        **kwargs: Any,
    ) -> bool:
        """Send trade closed notification.
        
        Args:
            symbol: Trading pair
            side: LONG or SHORT
            entry_price: Entry price
            exit_price: Exit price
            pnl_usd: Profit/loss in USD
            pnl_pct: Profit/loss percentage
            **kwargs: Additional metadata
        """
        emoji = "🟢" if pnl_usd >= 0 else "🔴"
        
        metadata = {
            "symbol": symbol,
            "side": side,
            "entry": f"${entry_price:,.2f}",
            "exit": f"${exit_price:,.2f}",
            "pnl_usd": f"{'+' if pnl_usd >= 0 else ''}{pnl_usd:,.2f}",
            "pnl_pct": f"{'+' if pnl_pct >= 0 else ''}{pnl_pct:.2f}%",
            **kwargs,
        }
        
        alert = Alert(
            alert_type=AlertType.TRADE_CLOSED,
            priority=AlertPriority.MEDIUM,
            title=f"{emoji} Trade Closed: {symbol}",
            message=f"P&L: {'+' if pnl_usd >= 0 else ''}${pnl_usd:,.2f} ({'+' if pnl_pct >= 0 else ''}{pnl_pct:.2f}%)",
            metadata=metadata,
        )
        return await self.send_alert(alert)
    
    async def send_breaker_activated(
        self,
        breaker_name: str,
        reason: str,
        cooldown_minutes: int = 0,
        **kwargs: Any,
    ) -> bool:
        """Send circuit breaker activation notification.
        
        Args:
            breaker_name: Name of the breaker that activated
            reason: Reason for activation
            cooldown_minutes: Cooldown period
            **kwargs: Additional metadata
        """
        metadata = {
            "breaker": breaker_name,
            "reason": reason,
            **kwargs,
        }
        if cooldown_minutes > 0:
            metadata["cooldown"] = f"{cooldown_minutes} min"
        
        alert = Alert(
            alert_type=AlertType.BREAKER_ACTIVATED,
            priority=AlertPriority.CRITICAL,
            title=f"Circuit Breaker: {breaker_name}",
            message=f"⚠️ Trading halted: {reason}",
            metadata=metadata,
        )
        return await self.send_alert(alert)
    
    async def send_gate_triggered(
        self,
        gate_name: str,
        action: str,
        details: str = "",
        **kwargs: Any,
    ) -> bool:
        """Send gate trigger notification.
        
        Args:
            gate_name: Name of the gate
            action: Action taken (e.g., "position reduced")
            details: Additional details
            **kwargs: Additional metadata
        """
        metadata = {
            "gate": gate_name,
            "action": action,
            **kwargs,
        }
        
        alert = Alert(
            alert_type=AlertType.GATE_TRIGGERED,
            priority=AlertPriority.HIGH,
            title=f"Gate Triggered: {gate_name}",
            message=details if details else action,
            metadata=metadata,
        )
        return await self.send_alert(alert)
    
    async def send_daily_summary(
        self,
        date: datetime,
        total_pnl_usd: float,
        total_trades: int,
        win_rate: float,
        equity: float,
        **kwargs: Any,
    ) -> bool:
        """Send daily performance summary.
        
        Args:
            date: Summary date
            total_pnl_usd: Total P&L for the day
            total_trades: Number of trades
            win_rate: Win rate percentage
            equity: Current equity
            **kwargs: Additional metrics
        """
        emoji = "🟢" if total_pnl_usd >= 0 else "🔴"
        
        message_lines = [
            f"📅 *Daily Summary - {date.strftime('%Y-%m-%d')}*",
            "",
            f"💰 P&L: {emoji} {'+' if total_pnl_usd >= 0 else ''}${total_pnl_usd:,.2f}",
            f"📊 Trades: {total_trades}",
            f"🎯 Win Rate: {win_rate:.1f}%",
            f"💵 Equity: ${equity:,.2f}",
        ]
        
        metadata = {
            "trades": total_trades,
            "win_rate": f"{win_rate:.1f}%",
            **kwargs,
        }
        
        alert = Alert(
            alert_type=AlertType.DAILY_SUMMARY,
            priority=AlertPriority.LOW,
            title="Daily Summary",
            message="\n".join(message_lines),
            metadata=metadata,
        )
        return await self.send_alert(alert)
    
    async def send_error(
        self,
        error_type: str,
        message: str,
        **kwargs: Any,
    ) -> bool:
        """Send error notification.
        
        Args:
            error_type: Type of error
            message: Error message
            **kwargs: Additional metadata
        """
        # Check error rate limit
        if not self._check_error_limit():
            return False
        
        self._error_timestamps.append(datetime.now(timezone.utc))
        
        alert = Alert(
            alert_type=AlertType.ERROR,
            priority=AlertPriority.HIGH,
            title=f"Error: {error_type}",
            message=message,
            metadata=kwargs,
        )
        return await self.send_alert(alert)
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now(timezone.utc)
        cutoff = now.replace(second=0, microsecond=0)  # Start of current minute
        
        # Clean old timestamps
        self._alert_timestamps = [
            ts for ts in self._alert_timestamps
            if ts >= cutoff
        ]
        
        return len(self._alert_timestamps) < self.config.max_alerts_per_minute
    
    def _check_error_limit(self) -> bool:
        """Check if we're within error rate limits."""
        now = datetime.now(timezone.utc)
        one_hour_ago = now.replace(minute=0, second=0, microsecond=0)
        
        # Clean old timestamps
        self._error_timestamps = [
            ts for ts in self._error_timestamps
            if ts >= one_hour_ago
        ]
        
        return len(self._error_timestamps) < self.config.max_errors_per_hour
    
    async def _send_message(self, text: str) -> bool:
        """Send message via Telegram API.
        
        Args:
            text: Message text (markdown formatted)
            
        Returns:
            True if sent successfully
        """
        if not self._client:
            async with httpx.AsyncClient(timeout=30.0) as client:
                return await self._send_with_client(client, text)
        return await self._send_with_client(self._client, text)
    
    async def _send_with_client(self, client: httpx.AsyncClient, text: str) -> bool:
        """Send message using provided client with retries."""
        url = f"{self.TELEGRAM_API_BASE}/bot{self.config.bot_token}/sendMessage"
        payload = {
            "chat_id": self.config.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        
        for attempt in range(self._max_retries):
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    return True
                elif response.status_code == 429:
                    # Rate limited by Telegram
                    retry_after = response.json().get("parameters", {}).get("retry_after", 10)
                    await asyncio.sleep(retry_after)
                else:
                    # Log error but don't retry for other codes
                    break
            except httpx.TimeoutException:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
            except httpx.HTTPError:
                break
        
        return False
