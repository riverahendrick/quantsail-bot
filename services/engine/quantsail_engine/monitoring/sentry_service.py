"""Sentry integration for error tracking and performance monitoring.

Provides:
- Error capture with context
- Performance transaction tracing
- Custom breadcrumbs for trade flow
- Sampling configuration

Following IMPL_GUIDE requirements for production monitoring.
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generator

# Sentry SDK - will be available in production
try:
    import sentry_sdk
    from sentry_sdk import Hub, capture_exception, capture_message, set_context, set_tag, set_user
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    from sentry_sdk.integrations.httpx import HttpxIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:  # pragma: no cover
    SENTRY_AVAILABLE = False
    # Stub sentry objects so @patch targets exist even without the SDK
    sentry_sdk = None  # type: ignore[assignment]
    Hub = None  # type: ignore[assignment,misc]
    AsyncioIntegration = None  # type: ignore[assignment,misc]
    HttpxIntegration = None  # type: ignore[assignment,misc]
    LoggingIntegration = None  # type: ignore[assignment,misc]
    # Mock sentry functions for when SDK not installed
    def capture_exception(*args: Any, **kwargs: Any) -> None: pass
    def capture_message(*args: Any, **kwargs: Any) -> None: pass
    def set_context(*args: Any, **kwargs: Any) -> None: pass
    def set_tag(*args: Any, **kwargs: Any) -> None: pass
    def set_user(*args: Any, **kwargs: Any) -> None: pass


class SentryLevel(Enum):
    """Sentry message levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


@dataclass
class SentryConfig:
    """Sentry configuration."""
    dsn: str
    environment: str = "development"
    release: str = ""
    # Sampling
    traces_sample_rate: float = 0.1  # 10% of transactions
    profiles_sample_rate: float = 0.1  # 10% of profiled transactions
    error_sample_rate: float = 1.0  # 100% of errors
    # Features
    enabled: bool = True
    debug: bool = False
    # Filtering
    ignore_errors: list[str] = field(default_factory=lambda: [
        "ConnectionResetError",
        "asyncio.CancelledError",
    ])
    

class SentryService:
    """Sentry integration service for error tracking.
    
    Wraps the Sentry SDK with trading-specific context and helpers.
    
    Example:
        >>> config = SentryConfig(dsn="https://xxx@sentry.io/123")
        >>> sentry = SentryService(config)
        >>> sentry.initialize()
        >>> 
        >>> with sentry.transaction("backtest", "run_strategy"):
        ...     # Your code here
        ...     sentry.add_breadcrumb("trade", "Opened BTC long", {"price": 50000})
    """
    
    def __init__(self, config: SentryConfig):
        """Initialize Sentry service.
        
        Args:
            config: Sentry configuration
        """
        self.config = config
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize Sentry SDK.
        
        Returns:
            True if initialization successful
        """
        if not self.config.enabled:
            return False
        
        if not SENTRY_AVAILABLE:
            return False
        
        if not self.config.dsn:
            return False
        
        try:
            sentry_sdk.init(
                dsn=self.config.dsn,
                environment=self.config.environment,
                release=self.config.release or self._get_release(),
                traces_sample_rate=self.config.traces_sample_rate,
                profiles_sample_rate=self.config.profiles_sample_rate,
                debug=self.config.debug,
                integrations=[
                    AsyncioIntegration(),
                    HttpxIntegration(),
                    LoggingIntegration(
                        level=None,  # Capture no logs as breadcrumbs
                        event_level=None,  # Don't send logs as events
                    ),
                ],
                before_send=self._before_send,
            )
            self._initialized = True
            return True
        except Exception:
            return False
    
    def _get_release(self) -> str:
        """Get release version from environment or git."""
        # Try environment variable first
        release = os.environ.get("SENTRY_RELEASE", "")
        if release:
            return release
        
        # Try to get git commit hash
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return f"quantsail@{result.stdout.strip()}"
        except Exception:
            pass
        
        return "quantsail@unknown"
    
    def _before_send(self, event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
        """Filter events before sending.
        
        Args:
            event: Sentry event
            hint: Additional context
            
        Returns:
            Event to send, or None to drop
        """
        # Check if error should be filtered
        if "exc_info" in hint:
            exc_type, exc_value, tb = hint["exc_info"]
            if exc_type.__name__ in self.config.ignore_errors:
                return None
        
        # Scrub sensitive data
        event = self._scrub_sensitive_data(event)
        
        return event
    
    def _scrub_sensitive_data(self, event: dict[str, Any]) -> dict[str, Any]:
        """Scrub sensitive data from event.
        
        Removes API keys, secrets, and PII from event data.
        """
        sensitive_keys = {
            "api_key", "apikey", "api-key",
            "secret", "password", "token",
            "authorization", "auth",
            "private_key", "privatekey",
        }
        
        def scrub_dict(d: dict[str, Any]) -> dict[str, Any]:
            result = {}
            for key, value in d.items():
                key_lower = key.lower()
                if any(s in key_lower for s in sensitive_keys):
                    result[key] = "[REDACTED]"
                elif isinstance(value, dict):
                    result[key] = scrub_dict(value)
                elif isinstance(value, list):
                    result[key] = [
                        scrub_dict(v) if isinstance(v, dict) else v
                        for v in value
                    ]
                else:
                    result[key] = value
            return result
        
        return scrub_dict(event)
    
    def capture_error(
        self,
        error: Exception,
        context: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
        level: SentryLevel = SentryLevel.ERROR,
    ) -> str | None:
        """Capture an exception.
        
        Args:
            error: Exception to capture
            context: Additional context data
            tags: Tags for filtering
            level: Severity level
            
        Returns:
            Event ID if captured, None otherwise
        """
        if not self._initialized:
            return None
        
        if context:
            set_context("trading_context", context)
        
        if tags:
            for key, value in tags.items():
                set_tag(key, value)
        
        return capture_exception(error)
    
    def capture_warning(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ) -> str | None:
        """Capture a warning message.
        
        Args:
            message: Warning message
            context: Additional context
            tags: Tags for filtering
            
        Returns:
            Event ID if captured
        """
        if not self._initialized:
            return None
        
        if context:
            set_context("trading_context", context)
        
        if tags:
            for key, value in tags.items():
                set_tag(key, value)
        
        return capture_message(message, level="warning")
    
    def add_breadcrumb(
        self,
        category: str,
        message: str,
        data: dict[str, Any] | None = None,
        level: str = "info",
    ) -> None:
        """Add a breadcrumb for debugging.
        
        Breadcrumbs are trail markers that show what happened before an error.
        
        Args:
            category: Category (e.g., "trade", "signal", "gate")
            message: Description of what happened
            data: Additional data
            level: Severity (debug/info/warning/error)
        """
        if not self._initialized:
            return
        
        if not SENTRY_AVAILABLE:
            return
        
        sentry_sdk.add_breadcrumb(
            category=category,
            message=message,
            data=data or {},
            level=level,
        )
    
    def set_trading_context(
        self,
        symbol: str | None = None,
        strategy: str | None = None,
        position: dict[str, Any] | None = None,
        equity: float | None = None,
    ) -> None:
        """Set trading context for all subsequent events.
        
        Args:
            symbol: Current trading symbol
            strategy: Active strategy name
            position: Current position info
            equity: Current equity
        """
        if not self._initialized:
            return
        
        context: dict[str, Any] = {}
        if symbol:
            context["symbol"] = symbol
            set_tag("symbol", symbol)
        if strategy:
            context["strategy"] = strategy
            set_tag("strategy", strategy)
        if position:
            context["position"] = position
        if equity is not None:
            context["equity"] = equity
        
        if context:
            set_context("trading", context)
    
    @contextmanager
    def transaction(
        self,
        op: str,
        name: str,
        description: str = "",
    ) -> Generator[Any, None, None]:
        """Create a performance transaction.
        
        Args:
            op: Operation type (e.g., "backtest", "trade", "signal")
            name: Transaction name
            description: Optional description
            
        Yields:
            Transaction span for adding child spans
        """
        if not self._initialized or not SENTRY_AVAILABLE:
            yield None
            return
        
        with sentry_sdk.start_transaction(
            op=op,
            name=name,
            description=description,
        ) as transaction:
            yield transaction
    
    @contextmanager  
    def span(
        self,
        op: str,
        description: str,
    ) -> Generator[Any, None, None]:
        """Create a span within a transaction.
        
        Args:
            op: Operation type
            description: Span description
            
        Yields:
            Span object
        """
        if not self._initialized or not SENTRY_AVAILABLE:
            yield None
            return
        
        hub = Hub.current
        span = hub.start_span(op=op, description=description)
        try:
            yield span
        finally:
            span.finish()
    
    def flush(self, timeout: float = 2.0) -> None:
        """Flush pending events.
        
        Args:
            timeout: Maximum time to wait
        """
        if self._initialized and SENTRY_AVAILABLE:
            sentry_sdk.flush(timeout=timeout)


# Convenience functions for module-level access
_service: SentryService | None = None


def init_sentry(config: SentryConfig) -> SentryService:
    """Initialize the global Sentry service.
    
    Args:
        config: Sentry configuration
        
    Returns:
        Initialized service
    """
    global _service
    _service = SentryService(config)
    _service.initialize()
    return _service


def get_sentry() -> SentryService | None:
    """Get the global Sentry service.
    
    Returns:
        Service if initialized, None otherwise
    """
    return _service
