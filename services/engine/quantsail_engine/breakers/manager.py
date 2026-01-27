"""Circuit breaker manager for coordinating active breakers."""

from datetime import datetime, timedelta, timezone

from quantsail_engine.breakers.models import ActiveBreaker
from quantsail_engine.cache.news import get_news_cache
from quantsail_engine.config.models import BreakerConfig
from quantsail_engine.persistence.repository import EngineRepository


class BreakerManager:
    """Manages circuit breakers and entry/exit gating."""

    def __init__(self, config: BreakerConfig, repo: EngineRepository):
        """
        Initialize breaker manager.

        Args:
            config: Breaker configuration
            repo: Engine repository for event emission
        """
        self.config = config
        self.repo = repo
        self.active_breakers: dict[str, ActiveBreaker] = {}

    def entries_allowed(self) -> tuple[bool, str | None]:
        """
        Check if entries are allowed (no active breakers or news pause).

        Returns:
            Tuple of (allowed, rejection_reason)
        """
        self._expire_breakers()

        # Check news pause if enabled
        if self.config.news.enabled:
            cache = get_news_cache()
            if cache.is_negative_news_active():
                return False, "negative news pause active"

        if self.active_breakers:
            # Return first active breaker as reason
            breaker = next(iter(self.active_breakers.values()))
            reason = f"{breaker.breaker_type} breaker active: {breaker.reason}"
            return False, reason

        return True, None

    def exits_allowed(self) -> tuple[bool, str | None]:
        """
        Check if exits are allowed (always True - exits never blocked).

        Returns:
            Tuple of (True, None)
        """
        return True, None

    def trigger_breaker(
        self,
        breaker_type: str,
        reason: str,
        pause_minutes: int,
        context: dict[str, float],
    ) -> None:
        """
        Trigger a circuit breaker.

        Args:
            breaker_type: Type of breaker (e.g., "volatility", "spread_slippage")
            reason: Human-readable reason
            pause_minutes: Minutes to pause entries
            context: Additional context data
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=pause_minutes)

        breaker = ActiveBreaker(
            breaker_type=breaker_type,
            triggered_at=now,
            expires_at=expires_at,
            reason=reason,
            context=context,
        )

        self.active_breakers[breaker_type] = breaker

        # Emit breaker.triggered event
        self.repo.append_event(
            event_type="breaker.triggered",
            level="WARN",
            payload={
                "breaker_type": breaker_type,
                "reason": reason,
                "triggered_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "pause_minutes": pause_minutes,
                **context,
            },
            public_safe=True,
        )

    def _expire_breakers(self) -> None:
        """Check for expired breakers and remove them."""
        now = datetime.now(timezone.utc)
        expired = []

        for breaker_type, breaker in self.active_breakers.items():
            if now >= breaker.expires_at:
                expired.append(breaker_type)

                # Calculate active duration
                active_for_minutes = (now - breaker.triggered_at).total_seconds() / 60

                # Emit breaker.expired event
                self.repo.append_event(
                    event_type="breaker.expired",
                    level="INFO",
                    payload={
                        "breaker_type": breaker_type,
                        "expired_at": now.isoformat(),
                        "was_active_for_minutes": round(active_for_minutes, 2),
                    },
                    public_safe=True,
                )

        # Remove expired breakers
        for breaker_type in expired:
            del self.active_breakers[breaker_type]
