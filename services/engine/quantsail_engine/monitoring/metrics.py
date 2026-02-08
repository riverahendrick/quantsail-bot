"""Prometheus metrics for the trading engine.

This module provides metrics collection and exposure for monitoring
the trading engine's performance, health, and operational statistics.

Example:
    >>> from quantsail_engine.monitoring.metrics import MetricsService, get_metrics
    >>> 
    >>> # Initialize (typically at startup)
    >>> metrics = MetricsService(port=9090)
    >>> metrics.start_server()
    >>> 
    >>> # Record events
    >>> metrics.record_trade_opened("BTC/USDT", "buy")
    >>> metrics.record_trade_closed("BTC/USDT", "buy", pnl=25.50)
    >>> metrics.set_equity(10250.00)
"""

import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# Module-level singleton
_metrics: "MetricsService | None" = None


@dataclass(frozen=True)
class MetricsConfig:
    """Configuration for metrics service.
    
    Attributes:
        enabled: Whether metrics collection is enabled
        port: HTTP server port for Prometheus scraping
        prefix: Metric name prefix
    """
    
    enabled: bool = True
    port: int = 9090
    prefix: str = "quantsail"


class MetricsService:
    """Prometheus metrics service for trading engine monitoring.
    
    Exposes key trading and operational metrics for Prometheus scraping:
    - Trade counts by symbol/side/status
    - PnL histograms
    - Equity gauges
    - Circuit breaker triggers
    - Gate rejections
    
    Example:
        >>> config = MetricsConfig(port=9090)
        >>> metrics = MetricsService(config)
        >>> metrics.start_server()
        >>> metrics.record_trade_opened("ETH/USDT", "sell")
    """
    
    def __init__(self, config: MetricsConfig | None = None) -> None:
        """Initialize metrics service.
        
        Args:
            config: Metrics configuration (uses defaults if not provided)
        """
        self.config = config or MetricsConfig()
        self._server_started = False
        self._lock = threading.Lock()
        
        # Metrics will be lazily initialized when first accessed
        self._trades_total: "Counter | None" = None
        self._trades_opened: "Counter | None" = None
        self._trades_closed: "Counter | None" = None
        self._trade_pnl: "Histogram | None" = None
        self._equity: "Gauge | None" = None
        self._daily_pnl: "Gauge | None" = None
        self._breaker_triggers: "Counter | None" = None
        self._gate_rejections: "Counter | None" = None
        self._kill_switch_active: "Gauge | None" = None
        self._open_positions: "Gauge | None" = None
        self._signals_generated: "Counter | None" = None
        
        if self.config.enabled:
            self._initialize_metrics()
    
    def _initialize_metrics(self) -> None:
        """Initialize Prometheus metrics objects."""
        try:
            from prometheus_client import Counter, Gauge, Histogram
        except ImportError:  # pragma: no cover
            logger.warning(
                "prometheus_client not installed. Metrics will be disabled. "
                "Install with: pip install prometheus-client"
            )
            self.config = MetricsConfig(enabled=False)
            return
        
        prefix = self.config.prefix
        
        # Trade counters
        self._trades_total = Counter(
            f"{prefix}_trades_total",
            "Total number of trades executed",
            ["symbol", "side", "status"],
        )
        
        self._trades_opened = Counter(
            f"{prefix}_trades_opened_total",
            "Total number of trades opened",
            ["symbol", "side"],
        )
        
        self._trades_closed = Counter(
            f"{prefix}_trades_closed_total",
            "Total number of trades closed",
            ["symbol", "side", "result"],
        )
        
        # PnL histogram with sensible buckets in USD
        self._trade_pnl = Histogram(
            f"{prefix}_trade_pnl_usd",
            "Trade PnL distribution in USD",
            buckets=[-50, -20, -10, -5, -2, -1, 0, 1, 2, 5, 10, 20, 50, 100],
        )
        
        # Equity gauges
        self._equity = Gauge(
            f"{prefix}_equity_usd",
            "Current equity in USD",
        )
        
        self._daily_pnl = Gauge(
            f"{prefix}_daily_pnl_usd",
            "Daily realized PnL in USD",
        )
        
        # Circuit breaker and safety metrics
        self._breaker_triggers = Counter(
            f"{prefix}_breaker_triggers_total",
            "Number of circuit breaker triggers",
            ["breaker_type"],
        )
        
        self._gate_rejections = Counter(
            f"{prefix}_gate_rejections_total",
            "Number of gate rejections",
            ["reason"],
        )
        
        self._kill_switch_active = Gauge(
            f"{prefix}_kill_switch_active",
            "Whether kill switch is currently active (0=inactive, 1=active)",
        )
        
        # Position tracking
        self._open_positions = Gauge(
            f"{prefix}_open_positions",
            "Number of currently open positions",
        )
        
        # Signal generation
        self._signals_generated = Counter(
            f"{prefix}_signals_generated_total",
            "Number of signals generated",
            ["symbol", "signal_type"],
        )
        
        logger.info("Prometheus metrics initialized")
    
    def start_server(self) -> bool:
        """Start the Prometheus HTTP server.
        
        Returns:
            True if server started successfully, False otherwise
        """
        if not self.config.enabled:
            logger.info("Metrics disabled, server not started")
            return False
        
        with self._lock:
            if self._server_started:
                logger.warning("Metrics server already started")
                return True
            
            try:
                from prometheus_client import start_http_server
                start_http_server(self.config.port)
                self._server_started = True
                logger.info(f"Prometheus metrics server started on port {self.config.port}")
                return True
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")
                return False
    
    @property
    def is_enabled(self) -> bool:
        """Check if metrics collection is enabled."""
        return self.config.enabled
    
    # --- Trade Recording Methods ---
    
    def record_trade_opened(self, symbol: str, side: str) -> None:
        """Record a trade being opened.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            side: Trade side ("buy" or "sell")
        """
        if not self.config.enabled or self._trades_opened is None:
            return
        self._trades_opened.labels(symbol=symbol, side=side).inc()
        self._trades_total.labels(symbol=symbol, side=side, status="opened").inc()
    
    def record_trade_closed(
        self, 
        symbol: str, 
        side: str, 
        pnl: float,
        result: str | None = None,
    ) -> None:
        """Record a trade being closed.
        
        Args:
            symbol: Trading pair symbol
            side: Trade side
            pnl: Realized PnL in USD
            result: Trade result ("win", "loss", "breakeven")
        """
        if not self.config.enabled:
            return
        
        if result is None:
            if pnl > 0:
                result = "win"
            elif pnl < 0:
                result = "loss"
            else:
                result = "breakeven"
        
        if self._trades_closed:
            self._trades_closed.labels(symbol=symbol, side=side, result=result).inc()
        if self._trades_total:
            self._trades_total.labels(symbol=symbol, side=side, status="closed").inc()
        if self._trade_pnl:
            self._trade_pnl.observe(pnl)
    
    # --- Equity Methods ---
    
    def set_equity(self, equity: float) -> None:
        """Update current equity gauge.
        
        Args:
            equity: Current equity in USD
        """
        if not self.config.enabled or self._equity is None:
            return
        self._equity.set(equity)
    
    def set_daily_pnl(self, pnl: float) -> None:
        """Update daily PnL gauge.
        
        Args:
            pnl: Daily realized PnL in USD
        """
        if not self.config.enabled or self._daily_pnl is None:
            return
        self._daily_pnl.set(pnl)
    
    # --- Safety Metrics ---
    
    def record_breaker_trigger(self, breaker_type: str) -> None:
        """Record a circuit breaker trigger.
        
        Args:
            breaker_type: Type of breaker ("daily_loss", "drawdown", "volatility", etc.)
        """
        if not self.config.enabled or self._breaker_triggers is None:
            return
        self._breaker_triggers.labels(breaker_type=breaker_type).inc()
    
    def record_gate_rejection(self, reason: str) -> None:
        """Record a profitability gate rejection.
        
        Args:
            reason: Rejection reason ("insufficient_profit", "high_spread", etc.)
        """
        if not self.config.enabled or self._gate_rejections is None:
            return
        self._gate_rejections.labels(reason=reason).inc()
    
    def set_kill_switch_active(self, active: bool) -> None:
        """Update kill switch status.
        
        Args:
            active: Whether kill switch is currently active
        """
        if not self.config.enabled or self._kill_switch_active is None:
            return
        self._kill_switch_active.set(1 if active else 0)
    
    # --- Position Tracking ---
    
    def set_open_positions(self, count: int) -> None:
        """Update open positions count.
        
        Args:
            count: Number of currently open positions
        """
        if not self.config.enabled or self._open_positions is None:
            return
        self._open_positions.set(count)
    
    # --- Signal Tracking ---
    
    def record_signal(self, symbol: str, signal_type: str) -> None:
        """Record a signal being generated.
        
        Args:
            symbol: Trading pair symbol
            signal_type: Type of signal ("buy", "sell", "hold", "close")
        """
        if not self.config.enabled or self._signals_generated is None:
            return
        self._signals_generated.labels(symbol=symbol, signal_type=signal_type).inc()


def init_metrics(config: MetricsConfig | None = None) -> MetricsService:
    """Initialize the global metrics service.
    
    Args:
        config: Metrics configuration
        
    Returns:
        Initialized MetricsService
    """
    global _metrics
    _metrics = MetricsService(config)
    return _metrics


def get_metrics() -> MetricsService | None:
    """Get the global metrics service instance.
    
    Returns:
        MetricsService if initialized, None otherwise
    """
    return _metrics
