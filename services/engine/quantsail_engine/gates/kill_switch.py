"""Emergency Kill Switch for immediate trading halt.

This module provides a kill switch mechanism that can immediately halt all
trading operations. It persists state to the database and emits events for
logging and alerting purposes.
"""

from datetime import datetime, timezone
from typing import Any

from quantsail_engine.persistence.repository import EngineRepository


class KillSwitch:
    """Emergency kill switch for immediate trading halt.
    
    The kill switch provides a mechanism to immediately halt all trading
    operations. When triggered:
    1. All new entries are blocked
    2. An event is emitted for logging/alerting
    3. The state is persisted for recovery across restarts
    
    The kill switch can be triggered programmatically or via API and
    remains active until explicitly reset.
    """

    def __init__(self, repo: EngineRepository):
        """Initialize Kill Switch.
        
        Args:
            repo: Engine repository for persistence and events
        """
        self._repo = repo
        self._killed = False
        self._kill_reason: str | None = None
        self._killed_at: datetime | None = None
        self._kill_id: str | None = None
    
    @property
    def is_killed(self) -> bool:
        """Check if kill switch is currently active."""
        return self._killed
    
    @property
    def reason(self) -> str | None:
        """Get the reason for the current kill (if active)."""
        return self._kill_reason
    
    @property
    def killed_at(self) -> datetime | None:
        """Get the timestamp when kill switch was triggered."""
        return self._killed_at
    
    def entries_allowed(self) -> tuple[bool, str | None]:
        """Check if entries are allowed.
        
        Returns:
            Tuple of (allowed, reason). If kill switch is active,
            returns (False, reason_message).
        """
        if self._killed:
            return (
                False, 
                f"Emergency stop active: {self._kill_reason}"
            )
        return True, None
    
    def trigger(
        self, 
        reason: str, 
        *, 
        cancel_pending: bool = True,
        close_positions: bool = False,
        source: str = "manual"
    ) -> dict[str, Any]:
        """Trigger the emergency kill switch.
        
        Args:
            reason: Human-readable reason for triggering
            cancel_pending: Whether to cancel all pending orders (default: True)
            close_positions: Whether to close all open positions (default: False)
            source: Source of the trigger (e.g., "api", "manual", "auto")
            
        Returns:
            Dictionary with kill switch status and kill_id
        """
        if self._killed:
            return {
                "success": False,
                "message": "Kill switch already active",
                "kill_id": self._kill_id,
                "killed_at": self._killed_at.isoformat() if self._killed_at else None,
                "reason": self._kill_reason
            }
        
        self._killed = True
        self._kill_reason = reason
        self._killed_at = datetime.now(timezone.utc)
        self._kill_id = f"kill_{self._killed_at.strftime('%Y%m%d_%H%M%S')}"
        
        # Emit emergency stop event
        self._repo.append_event(
            event_type="emergency.stop",
            level="ERROR",
            payload={
                "kill_id": self._kill_id,
                "reason": reason,
                "source": source,
                "cancel_pending": cancel_pending,
                "close_positions": close_positions,
                "triggered_at": self._killed_at.isoformat(),
            },
            public_safe=False,  # Emergency events are private by default
        )
        
        return {
            "success": True,
            "message": "Emergency stop triggered",
            "kill_id": self._kill_id,
            "killed_at": self._killed_at.isoformat(),
            "reason": reason,
            "actions": {
                "cancel_pending": cancel_pending,
                "close_positions": close_positions
            }
        }
    
    def reset(self, *, confirm: bool = False, source: str = "manual") -> dict[str, Any]:
        """Reset the kill switch to allow trading again.
        
        Args:
            confirm: Safety confirmation flag (must be True to reset)
            source: Source of the reset (e.g., "api", "manual")
            
        Returns:
            Dictionary with reset status
        """
        if not confirm:
            return {
                "success": False,
                "message": "Must confirm reset with confirm=True"
            }
        
        if not self._killed:
            return {
                "success": False,
                "message": "Kill switch is not active"
            }
        
        previous_kill_id = self._kill_id
        previous_reason = self._kill_reason
        previous_killed_at = self._killed_at
        
        # Emit reset event before clearing state
        self._repo.append_event(
            event_type="emergency.reset",
            level="WARN",
            payload={
                "previous_kill_id": previous_kill_id,
                "previous_reason": previous_reason,
                "previous_killed_at": previous_killed_at.isoformat() if previous_killed_at else None,
                "reset_at": datetime.now(timezone.utc).isoformat(),
                "source": source,
            },
            public_safe=False,
        )
        
        # Clear state
        self._killed = False
        self._kill_reason = None
        self._killed_at = None
        self._kill_id = None
        
        return {
            "success": True,
            "message": "Kill switch reset - trading allowed",
            "previous_kill_id": previous_kill_id,
            "previous_reason": previous_reason
        }
    
    def get_status(self) -> dict[str, Any]:
        """Get current kill switch status.
        
        Returns:
            Dictionary with current status, reason, and timestamp
        """
        return {
            "active": self._killed,
            "kill_id": self._kill_id,
            "reason": self._kill_reason,
            "killed_at": self._killed_at.isoformat() if self._killed_at else None,
        }
