"""Emergency kill switch for immediate trading halt.

Provides multiple mechanisms to stop all trading activity:
- Manual operator trigger
- Automatic triggers based on thresholds
- Remote kill via API/file signal

Critical safety component per IMPL_GUIDE requirements.
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable


class KillReason(Enum):
    """Reasons for kill switch activation."""
    MANUAL = auto()            # Operator manually triggered
    MAX_DAILY_LOSS = auto()    # Daily loss limit exceeded
    MAX_DRAWDOWN = auto()       # Maximum drawdown exceeded
    MARGIN_CALL = auto()        # Margin requirements not met
    EXCHANGE_ERROR = auto()     # Exchange API issues
    DATA_FEED_FAILURE = auto()  # Market data issues
    SYSTEM_ERROR = auto()       # Internal system error
    REMOTE_SIGNAL = auto()      # External kill signal received
    SCHEDULED = auto()          # Scheduled maintenance


@dataclass
class KillEvent:
    """Record of a kill switch activation."""
    timestamp: datetime
    reason: KillReason
    triggered_by: str
    details: str
    auto_resume_at: datetime | None = None
    acknowledged: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason.name,
            "triggered_by": self.triggered_by,
            "details": self.details,
            "auto_resume_at": self.auto_resume_at.isoformat() if self.auto_resume_at else None,
            "acknowledged": self.acknowledged,
        }


@dataclass 
class KillSwitchConfig:
    """Kill switch configuration."""
    # Automatic triggers
    max_daily_loss_pct: float = 5.0
    max_drawdown_pct: float = 15.0
    max_consecutive_losses: int = 5
    
    # Remote kill file path
    kill_file_path: str = "/tmp/quantsail_kill"
    check_kill_file: bool = True
    kill_file_check_interval_seconds: int = 10
    
    # Callbacks
    on_kill_callbacks: list[Callable[[KillEvent], None]] = field(default_factory=list)
    on_resume_callbacks: list[Callable[[], None]] = field(default_factory=list)


class KillSwitch:
    """Emergency kill switch for trading halt.
    
    Provides immediate stop capability for all trading activity.
    Can be triggered manually, automatically based on thresholds,
    or via external signals.
    
    Example:
        >>> kill_switch = KillSwitch(config)
        >>> 
        >>> # Check before trading
        >>> if kill_switch.is_killed:
        ...     print("Trading halted")
        ...     return
        >>> 
        >>> # Trigger manually
        >>> kill_switch.trigger(KillReason.MANUAL, "operator", "Taking a break")
        >>> 
        >>> # Resume trading
        >>> kill_switch.resume("operator")
    """
    
    def __init__(self, config: KillSwitchConfig | None = None):
        """Initialize kill switch.
        
        Args:
            config: Configuration options
        """
        self.config = config or KillSwitchConfig()
        
        # State
        self._is_killed = False
        self._current_event: KillEvent | None = None
        self._history: list[KillEvent] = []
        
        # Metrics tracking for auto-triggers
        self._daily_pnl_pct: float = 0.0
        self._peak_equity: float = 0.0
        self._current_equity: float = 0.0
        self._consecutive_losses: int = 0
        
        # Kill file monitoring
        self._kill_file_task: asyncio.Task[None] | None = None
    
    @property
    def is_killed(self) -> bool:
        """Check if kill switch is active."""
        return self._is_killed
    
    @property
    def current_event(self) -> KillEvent | None:
        """Get current kill event if active."""
        return self._current_event if self._is_killed else None
    
    @property
    def history(self) -> list[KillEvent]:
        """Get history of kill events."""
        return self._history.copy()
    
    def trigger(
        self,
        reason: KillReason,
        triggered_by: str,
        details: str = "",
        auto_resume_minutes: int | None = None,
    ) -> KillEvent:
        """Trigger the kill switch.
        
        Args:
            reason: Why the kill switch was triggered
            triggered_by: Who/what triggered it
            details: Additional details
            auto_resume_minutes: Optional auto-resume time
            
        Returns:
            The kill event created
        """
        auto_resume_at = None
        if auto_resume_minutes:
            from datetime import timedelta
            auto_resume_at = datetime.now(timezone.utc) + timedelta(minutes=auto_resume_minutes)
        
        event = KillEvent(
            timestamp=datetime.now(timezone.utc),
            reason=reason,
            triggered_by=triggered_by,
            details=details,
            auto_resume_at=auto_resume_at,
        )
        
        self._is_killed = True
        self._current_event = event
        self._history.append(event)
        
        # Execute callbacks
        for callback in self.config.on_kill_callbacks:
            try:
                callback(event)
            except Exception:
                pass  # Don't let callback errors prevent kill
        
        return event
    
    def resume(self, resumed_by: str) -> bool:
        """Resume trading.
        
        Args:
            resumed_by: Who is resuming trading
            
        Returns:
            True if resumed, False if not currently killed
        """
        if not self._is_killed:
            return False
        
        if self._current_event:
            self._current_event.acknowledged = True
        
        self._is_killed = False
        self._current_event = None
        
        # Execute callbacks
        for callback in self.config.on_resume_callbacks:
            try:
                callback()
            except Exception:
                pass
        
        return True
    
    def check_thresholds(
        self,
        daily_pnl_pct: float,
        current_equity: float,
        peak_equity: float,
        consecutive_losses: int,
    ) -> KillEvent | None:
        """Check if any automatic thresholds are breached.
        
        Should be called periodically by the trading loop.
        
        Args:
            daily_pnl_pct: Today's P&L as percentage
            current_equity: Current account equity
            peak_equity: Peak equity value
            consecutive_losses: Number of consecutive losing trades
            
        Returns:
            KillEvent if threshold breached, None otherwise
        """
        if self._is_killed:
            return None
        
        # Update tracking
        self._daily_pnl_pct = daily_pnl_pct
        self._current_equity = current_equity
        self._peak_equity = peak_equity
        self._consecutive_losses = consecutive_losses
        
        # Check daily loss
        if daily_pnl_pct <= -self.config.max_daily_loss_pct:
            return self.trigger(
                reason=KillReason.MAX_DAILY_LOSS,
                triggered_by="auto",
                details=f"Daily loss {daily_pnl_pct:.2f}% exceeds limit of -{self.config.max_daily_loss_pct}%",
            )
        
        # Check drawdown
        if peak_equity > 0:
            drawdown_pct = (peak_equity - current_equity) / peak_equity * 100
            if drawdown_pct >= self.config.max_drawdown_pct:
                return self.trigger(
                    reason=KillReason.MAX_DRAWDOWN,
                    triggered_by="auto",
                    details=f"Drawdown {drawdown_pct:.2f}% exceeds limit of {self.config.max_drawdown_pct}%",
                )
        
        # Check consecutive losses
        if consecutive_losses >= self.config.max_consecutive_losses:
            return self.trigger(
                reason=KillReason.MAX_DAILY_LOSS,  # Use daily loss for consecutive
                triggered_by="auto",
                details=f"{consecutive_losses} consecutive losses exceeds limit of {self.config.max_consecutive_losses}",
                auto_resume_minutes=60,  # Auto-resume after 1 hour
            )
        
        return None
    
    def check_kill_file(self) -> KillEvent | None:
        """Check for external kill file signal.
        
        Returns:
            KillEvent if file exists, None otherwise
        """
        if not self.config.check_kill_file:
            return None
        
        if self._is_killed:
            return None
        
        kill_path = Path(self.config.kill_file_path)
        
        if kill_path.exists():
            try:
                content = kill_path.read_text().strip()
                details = content if content else "Kill file detected"
                
                return self.trigger(
                    reason=KillReason.REMOTE_SIGNAL,
                    triggered_by="kill_file",
                    details=details,
                )
            except Exception as e:
                return self.trigger(
                    reason=KillReason.REMOTE_SIGNAL,
                    triggered_by="kill_file",
                    details=f"Kill file detected (error reading: {e})",
                )
        
        return None
    
    async def start_monitoring(self) -> None:
        """Start background kill file monitoring."""
        if not self.config.check_kill_file:
            return
        
        async def monitor_loop() -> None:
            while True:
                self.check_kill_file()
                await asyncio.sleep(self.config.kill_file_check_interval_seconds)
        
        self._kill_file_task = asyncio.create_task(monitor_loop())
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if self._kill_file_task:
            self._kill_file_task.cancel()
            try:
                await self._kill_file_task
            except asyncio.CancelledError:
                pass
            self._kill_file_task = None
    
    def get_status(self) -> dict[str, Any]:
        """Get current kill switch status.
        
        Returns:
            Status dictionary
        """
        return {
            "is_killed": self._is_killed,
            "current_event": self._current_event.to_dict() if self._current_event else None,
            "history_count": len(self._history),
            "daily_pnl_pct": self._daily_pnl_pct,
            "current_drawdown_pct": (
                (self._peak_equity - self._current_equity) / self._peak_equity * 100
                if self._peak_equity > 0 else 0
            ),
            "consecutive_losses": self._consecutive_losses,
        }
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.
        
        Returns:
            Complete state dictionary
        """
        return {
            "status": self.get_status(),
            "config": {
                "max_daily_loss_pct": self.config.max_daily_loss_pct,
                "max_drawdown_pct": self.config.max_drawdown_pct,
                "max_consecutive_losses": self.config.max_consecutive_losses,
            },
            "history": [e.to_dict() for e in self._history],
        }
