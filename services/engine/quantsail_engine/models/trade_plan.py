"""Trade plan model before execution."""

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid


@dataclass(frozen=True)
class TradePlan:
    """
    Trade plan with entry and exit parameters.

    All prices are in quote currency (e.g., USDT for BTC/USDT).
    """

    symbol: str
    side: str  # "BUY" for long entry
    entry_price: float
    quantity: float
    stop_loss_price: float
    take_profit_price: float

    # Fee and slippage estimates
    estimated_fee_usd: float
    estimated_slippage_usd: float
    estimated_spread_cost_usd: float
    
    # Execution Metadata
    timestamp: datetime
    trade_id: str

    def __post_init__(self) -> None:
        """Validate trade plan parameters."""
        if self.entry_price <= 0:
            raise ValueError("Entry price must be positive")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.stop_loss_price <= 0:
            raise ValueError("Stop loss price must be positive")
        if self.take_profit_price <= 0:
            raise ValueError("Take profit price must be positive")

        # For long positions: SL < entry < TP
        if self.side == "BUY":
            if self.stop_loss_price >= self.entry_price:
                raise ValueError("Stop loss must be below entry price for long")
            if self.take_profit_price <= self.entry_price:
                raise ValueError("Take profit must be above entry price for long")

    @property
    def position_value_usd(self) -> float:
        """Total position value in USD at entry."""
        return self.entry_price * self.quantity

    @property
    def risk_usd(self) -> float:
        """Maximum loss in USD if stop loss is hit (before fees/slippage)."""
        return (self.entry_price - self.stop_loss_price) * self.quantity

    @property
    def reward_usd(self) -> float:
        """Maximum profit in USD if take profit is hit (before fees/slippage)."""
        return (self.take_profit_price - self.entry_price) * self.quantity

    @property
    def risk_reward_ratio(self) -> float:
        """Reward-to-risk ratio."""
        return self.reward_usd / self.risk_usd if self.risk_usd > 0 else 0.0