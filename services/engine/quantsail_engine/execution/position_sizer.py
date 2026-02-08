"""Adaptive position sizing for trading execution.

This module provides position sizing strategies that optimize trade size
based on profitability constraints, risk limits, and fee structures.

Example:
    >>> sizer = AdaptivePositionSizer(fee_rate_bps=10, use_bnb_discount=True)
    >>> result = sizer.find_optimal_size(
    ...     entry_price=50000.0,
    ...     target_price=51000.0,
    ...     stop_price=49500.0,
    ...     equity=10000.0,
    ... )
    >>> if result:
    ...     print(f"Trade ${result.notional} for ${result.net_profit:.2f} profit")
"""

import logging
from dataclasses import dataclass
from typing import Sequence, Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PositionSizeResult:
    """Result of position sizing calculation.
    
    Attributes:
        notional: Trade notional value in quote currency (e.g., USDT)
        quantity: Position size in base currency (e.g., BTC)
        gross_profit: Expected gross profit before fees
        total_fees: Total trading fees (entry + exit)
        spread_cost: Estimated spread cost
        slippage_cost: Estimated slippage cost
        net_profit: Expected net profit after all costs
        min_profit: Minimum required profit for this size
        risk_amount: Amount at risk if stop is hit
        risk_pct: Percentage of equity at risk
    """
    
    notional: float
    quantity: float
    gross_profit: float
    total_fees: float
    spread_cost: float
    slippage_cost: float
    net_profit: float
    min_profit: float
    risk_amount: float
    risk_pct: float
    
    @property
    def total_costs(self) -> float:
        """Total trading costs."""
        return self.total_fees + self.spread_cost + self.slippage_cost
    
    @property
    def is_profitable(self) -> bool:
        """Whether expected profit exceeds minimum threshold."""
        return self.net_profit >= self.min_profit


@dataclass(frozen=True)
class FeeModel:
    """Trading fee model configuration.
    
    Attributes:
        maker_rate_bps: Maker fee in basis points
        taker_rate_bps: Taker fee in basis points  
        use_bnb_discount: Whether BNB discount is active (25% off)
        spread_bps: Estimated spread in basis points
        slippage_bps: Estimated slippage in basis points
    """
    
    maker_rate_bps: float = 10.0  # 0.10%
    taker_rate_bps: float = 10.0  # 0.10%
    use_bnb_discount: bool = True
    spread_bps: float = 2.0  # 0.02%
    slippage_bps: float = 3.0  # 0.03%
    
    @property
    def effective_maker_bps(self) -> float:
        """Get effective maker fee with BNB discount."""
        return self.maker_rate_bps * 0.75 if self.use_bnb_discount else self.maker_rate_bps
    
    @property
    def effective_taker_bps(self) -> float:
        """Get effective taker fee with BNB discount."""
        return self.taker_rate_bps * 0.75 if self.use_bnb_discount else self.taker_rate_bps
    
    def calculate_fee(self, notional: float, is_maker: bool = False) -> float:
        """Calculate fee for a given notional value.
        
        Args:
            notional: Trade notional value
            is_maker: Whether this is a maker order
            
        Returns:
            Fee amount in quote currency
        """
        rate_bps = self.effective_maker_bps if is_maker else self.effective_taker_bps
        return notional * rate_bps / 10000
    
    def calculate_spread_cost(self, notional: float) -> float:
        """Calculate spread cost."""
        return notional * self.spread_bps / 10000
    
    def calculate_slippage(self, notional: float) -> float:
        """Calculate slippage cost."""
        return notional * self.slippage_bps / 10000


class AdaptivePositionSizer:
    """Adaptive position sizing that finds optimal trade size.
    
    Tests multiple notional values and returns the smallest size
    that satisfies the profitability gate.
    
    Attributes:
        fee_model: Fee structure for cost calculations
        test_notionals: Notional values to test in order
        min_profit_floor: Minimum profit floor in quote currency
        min_profit_rate: Minimum profit as fraction of notional
    
    Example:
        >>> sizer = AdaptivePositionSizer()
        >>> result = sizer.find_optimal_size(
        ...     entry_price=100.0,
        ...     target_price=102.0,  # 2% target
        ...     stop_price=99.0,     # 1% stop
        ...     equity=1000.0,
        ... )
        >>> if result:
        ...     print(f"Optimal size: ${result.notional}")
    """
    
    DEFAULT_NOTIONALS: tuple[float, ...] = (25.0, 50.0, 100.0, 200.0, 500.0, 1000.0)
    
    def __init__(
        self,
        fee_model: FeeModel | None = None,
        test_notionals: Sequence[float] | None = None,
        min_profit_floor: float = 0.15,
        min_profit_rate: float = 0.0012,
        max_risk_pct: float = 1.0,
        sizing_config: Any | None = None,  # PositionSizingConfig
    ) -> None:
        """Initialize adaptive position sizer.
        
        Args:
            fee_model: Fee structure (default: Binance with BNB)
            test_notionals: Notional values to test (default: 25-1000)
            min_profit_floor: Minimum profit floor in USD (default: $0.15)
            min_profit_rate: Minimum profit rate (default: 0.12%)
            max_risk_pct: Maximum portfolio risk per trade (default: 1%)
            sizing_config: Configuration for sizing method (fixed, risk_pct, kelly)
        """
        self.fee_model = fee_model or FeeModel()
        self.test_notionals = tuple(test_notionals or self.DEFAULT_NOTIONALS)
        self.min_profit_floor = min_profit_floor
        self.min_profit_rate = min_profit_rate
        self.max_risk_pct = max_risk_pct
        self.sizing_config = sizing_config
    
    def calculate_min_profit(self, notional: float) -> float:
        """Calculate minimum required profit for a given notional.
        
        Formula: max(floor, notional * rate)
        
        Args:
            notional: Trade notional value
            
        Returns:
            Minimum required profit
        """
        return max(self.min_profit_floor, notional * self.min_profit_rate)
    
    def calculate_trade_metrics(
        self,
        notional: float,
        entry_price: float,
        target_price: float,
        stop_price: float,
        equity: float,
    ) -> PositionSizeResult:
        """Calculate all metrics for a given trade size.
        
        Args:
            notional: Trade notional value
            entry_price: Entry price
            target_price: Target exit price
            stop_price: Stop loss price
            equity: Account equity
            
        Returns:
            PositionSizeResult with all calculated metrics
        """
        quantity = notional / entry_price
        
        # Gross profit (direction-agnostic)
        price_diff = abs(target_price - entry_price)
        gross_profit = notional * price_diff / entry_price
        
        # Cost calculation (entry + exit = 2x fee)
        total_fees = self.fee_model.calculate_fee(notional) * 2
        spread_cost = self.fee_model.calculate_spread_cost(notional)
        slippage_cost = self.fee_model.calculate_slippage(notional)
        
        # Net profit
        net_profit = gross_profit - total_fees - spread_cost - slippage_cost
        
        # Risk calculation
        stop_diff = abs(entry_price - stop_price)
        risk_amount = notional * stop_diff / entry_price
        risk_pct = (risk_amount / equity) * 100 if equity > 0 else 100
        
        # Minimum profit threshold
        min_profit = self.calculate_min_profit(notional)
        
        return PositionSizeResult(
            notional=notional,
            quantity=quantity,
            gross_profit=gross_profit,
            total_fees=total_fees,
            spread_cost=spread_cost,
            slippage_cost=slippage_cost,
            net_profit=net_profit,
            min_profit=min_profit,
            risk_amount=risk_amount,
            risk_pct=risk_pct,
        )
    
    def find_optimal_size(
        self,
        entry_price: float,
        target_price: float,
        stop_price: float,
        equity: float,
        max_risk_pct: float | None = None,
    ) -> PositionSizeResult | None:
        """Find the smallest viable trade size.
        
        Tests notionals in order and returns the first one that:
        1. Does not exceed max risk percentage
        2. Has net profit >= minimum profit threshold
        
        Args:
            entry_price: Entry price
            target_price: Target exit price
            stop_price: Stop loss price
            equity: Account equity
            max_risk_pct: Override max risk percentage
            
        Returns:
            PositionSizeResult if viable size found, None otherwise
        """
        if self.sizing_config:
            # Calculate specific size based on method
            calculated_notional = self._calculate_target_notional(
                entry_price, target_price, stop_price, equity
            )
            # If method produced a size, test strictly that size
            if calculated_notional is not None:
                logger.debug(f"Calculated target notional: ${calculated_notional:.2f}")
                notionals_to_test = (calculated_notional,)
            else:
                # Fallback to test notionals
                notionals_to_test = self.test_notionals
        else:
            notionals_to_test = self.test_notionals

        max_risk = max_risk_pct if max_risk_pct is not None else self.max_risk_pct
        
        for notional in notionals_to_test:
            result = self.calculate_trade_metrics(
                notional=notional,
                entry_price=entry_price,
                target_price=target_price,
                stop_price=stop_price,
                equity=equity,
            )
            
            # Skip if exceeds risk limit
            if result.risk_pct > max_risk:
                logger.debug(
                    f"Skipping ${notional}: risk {result.risk_pct:.2f}% > {max_risk}%"
                )
                continue
            
            # Return first profitable size
            if result.is_profitable:
                logger.info(
                    f"Found optimal size: ${notional} "
                    f"(net profit ${result.net_profit:.2f})"
                )
                return result
            
            logger.debug(
                f"Skipping ${notional}: net profit ${result.net_profit:.2f} "
                f"< min ${result.min_profit:.2f}"
            )
        
        logger.warning(f"No viable trade size found (tested {len(notionals_to_test)} options)")
        return None

    def _calculate_target_notional(
        self,
        entry_price: float,
        target_price: float,
        stop_price: float,
        equity: float,
    ) -> float | None:
        """Calculate target notional based on configured method."""
        config = self.sizing_config
        if not config:
            return None
            
        method = config.method
        
        if method == "fixed":
            # Fixed quantity * price
            qty = config.fixed_quantity
            return qty * entry_price
            
        elif method == "risk_pct":
            # Risk % of equity per trade
            # Risk Amount = Equity * risk_pct
            # Position Size = Risk Amount / (Stop Distance %)
            risk_pct = config.risk_pct / 100.0
            risk_amount = equity * risk_pct
            
            stop_distance_pct = abs(entry_price - stop_price) / entry_price
            if stop_distance_pct == 0:
                return None
                
            notional = risk_amount / stop_distance_pct
            
            # Cap at max position size
            max_pos_notional = equity * (config.max_position_pct / 100.0)
            return min(notional, max_pos_notional)
            
        elif method == "kelly":
            # Kelly Criterion
            # Win Rate (p) - assume 0.5 for now, or use config? 
            # Ideally this comes from performance stats.
            # Using simple Kelly with assumed stats if no history.
            # Fraction = p - (1-p)/b where b is payoff ratio.
            
            # Using simplified "Half-Kelly" or configured fraction of equity
            # defaulting to risk_pct logic but scaled by kelly_fraction if detailed stats unavailable
            # For now, fallback to risk_pct logic but use kelly_fraction * equity as max risk?
            # Actually, standard Kelly on Risk is: Size = Equity * Kelly%
            # But Kelly returns LEVERAGE.
            
            # Let's implementation a "Risk-Constrained Kelly" based on risk_pct for now
            # as full Kelly requires live win-rate data.
            # Reverting to risk_pct logic as baseline for 'aggressive' per config defaults
            
            risk_pct = config.risk_pct / 100.0
            risk_amount = equity * risk_pct
            stop_distance_pct = abs(entry_price - stop_price) / entry_price
            if stop_distance_pct == 0:
                return None
            
            notional = risk_amount / stop_distance_pct
            max_pos_notional = equity * (config.max_position_pct / 100.0)
            return min(notional, max_pos_notional)
            
        return None
    
    def find_all_viable_sizes(
        self,
        entry_price: float,
        target_price: float,
        stop_price: float,
        equity: float,
        max_risk_pct: float | None = None,
    ) -> list[PositionSizeResult]:
        """Find all viable trade sizes.
        
        Returns all notional values that satisfy both risk and profitability
        constraints.
        
        Args:
            entry_price: Entry price
            target_price: Target exit price
            stop_price: Stop loss price
            equity: Account equity
            max_risk_pct: Override max risk percentage
            
        Returns:
            List of viable PositionSizeResult objects
        """
        max_risk = max_risk_pct if max_risk_pct is not None else self.max_risk_pct
        viable: list[PositionSizeResult] = []
        
        for notional in self.test_notionals:
            result = self.calculate_trade_metrics(
                notional=notional,
                entry_price=entry_price,
                target_price=target_price,
                stop_price=stop_price,
                equity=equity,
            )
            
            if result.risk_pct <= max_risk and result.is_profitable:
                viable.append(result)
        
        return viable
