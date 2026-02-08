"""Portfolio-level risk manager for multi-position safety controls.

This module gates new entries based on:
- Maximum concurrent positions
- Correlated symbol exposure
- Daily trade count limits
- Daily loss limits (hard stop)
- Total portfolio exposure
"""

from datetime import datetime, date, timezone
from typing import TypedDict

from quantsail_engine.config.models import SymbolsConfig, PortfolioConfig, RiskConfig


class OpenPosition(TypedDict):
    """Representation of an open position for risk tracking."""
    notional: float
    opened_at: datetime


class PortfolioRiskManager:
    """Gates new position entries based on portfolio-level risk constraints.
    
    Tracks all open positions and enforces:
    - max_concurrent_positions (from SymbolsConfig)
    - max_correlated_positions
    - max_daily_trades
    - max_daily_loss_usd (HARD STOP - no new entries after breach)
    - max_portfolio_exposure_pct
    
    Usage:
        manager = PortfolioRiskManager(symbols_config, portfolio_config, risk_config)
        allowed, reason = manager.can_open_position("BTC/USDT", 500.0)
        if allowed:
            manager.add_position("BTC/USDT", 500.0)
        # On close:
        manager.close_position("BTC/USDT", pnl=12.50)
    """
    
    def __init__(
        self,
        symbols_config: SymbolsConfig,
        portfolio_config: PortfolioConfig,
        risk_config: RiskConfig,
    ):
        self.symbols_config = symbols_config
        self.portfolio_config = portfolio_config
        self.risk_config = risk_config
        
        self.open_positions: dict[str, OpenPosition] = {}
        self.daily_trades_count = 0
        self.daily_realized_pnl = 0.0
        self._last_reset: date = datetime.now(timezone.utc).date()
    
    @property
    def equity(self) -> float:
        """Get current equity (starting cash adjusted by daily P&L)."""
        return self.risk_config.starting_cash_usd + self.daily_realized_pnl
    
    def reset_daily_counters(self) -> bool:
        """Reset daily counters at day boundary.
        
        Returns:
            True if counters were reset, False if already current.
        """
        today = datetime.now(timezone.utc).date()
        if today > self._last_reset:
            self.daily_trades_count = 0
            self.daily_realized_pnl = 0.0
            self._last_reset = today
            return True
        return False
    
    def can_open_position(self, symbol: str, notional: float) -> tuple[bool, str]:
        """Check if a new position can be opened.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            notional: Position notional value in USD
            
        Returns:
            Tuple of (allowed, reason). If allowed is False, reason explains why.
        """
        self.reset_daily_counters()
        
        # CHECK 1: Max concurrent positions
        max_concurrent = self.symbols_config.max_concurrent_positions
        if len(self.open_positions) >= max_concurrent:
            return False, f"Max concurrent positions ({max_concurrent}) reached"
        
        # CHECK 2: Max correlated positions
        max_correlated = self.portfolio_config.max_correlated_positions
        correlated_count = sum(
            1 for pos_symbol in self.open_positions.keys()
            if self._is_correlated(symbol, pos_symbol)
        )
        if correlated_count >= max_correlated:
            return False, f"Max correlated positions ({max_correlated}) reached"
        
        # CHECK 3: Max daily trades
        max_daily_trades = self.portfolio_config.max_daily_trades
        if self.daily_trades_count >= max_daily_trades:
            return False, f"Max daily trades ({max_daily_trades}) reached"
        
        # CHECK 4: Daily loss limit (HARD STOP)
        max_daily_loss = self.portfolio_config.max_daily_loss_usd
        if self.daily_realized_pnl <= -max_daily_loss:
            return False, f"Daily loss limit hit: ${self.daily_realized_pnl:.2f}"
        
        # CHECK 5: Total portfolio exposure
        total_exposure = sum(pos["notional"] for pos in self.open_positions.values())
        max_exposure_pct = self.portfolio_config.max_portfolio_exposure_pct
        max_exposure = self.equity * (max_exposure_pct / 100)
        
        if total_exposure + notional > max_exposure:
            return (
                False,
                f"Portfolio exposure limit: ${total_exposure:.2f} + ${notional:.2f} > ${max_exposure:.2f}",
            )
        
        return True, "OK"
    
    def _is_correlated(self, symbol1: str, symbol2: str) -> bool:
        """Check if two symbols are considered correlated.
        
        Simplified correlation: same base currency = correlated.
        E.g., BTC/USDT and BTC/EUR are correlated.
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol
            
        Returns:
            True if correlated, False otherwise.
        """
        base1 = symbol1.split("/")[0]
        base2 = symbol2.split("/")[0]
        
        # Same base currency = correlated
        if base1 == base2:
            return True
        
        # Stablecoins are never correlated with each other
        stables = {"USDT", "USDC", "BUSD", "DAI", "TUSD"}
        if base1 in stables and base2 in stables:
            return False
        
        return False
    
    def add_position(self, symbol: str, notional: float) -> None:
        """Register a new open position.
        
        Args:
            symbol: Trading symbol
            notional: Position notional value in USD
        """
        self.open_positions[symbol] = OpenPosition(
            notional=notional,
            opened_at=datetime.now(timezone.utc),
        )
        self.daily_trades_count += 1
    
    def close_position(self, symbol: str, pnl: float) -> bool:
        """Close a position and update daily P&L.
        
        Args:
            symbol: Trading symbol to close
            pnl: Realized profit/loss in USD
            
        Returns:
            True if position was found and closed, False otherwise.
        """
        if symbol not in self.open_positions:
            return False
        
        del self.open_positions[symbol]
        self.daily_realized_pnl += pnl
        return True
    
    def get_status_summary(self) -> dict:
        """Get current portfolio risk status for monitoring/logging.
        
        Returns:
            Dictionary with current portfolio risk metrics.
        """
        total_exposure = sum(pos["notional"] for pos in self.open_positions.values())
        return {
            "open_positions": len(self.open_positions),
            "max_concurrent": self.symbols_config.max_concurrent_positions,
            "daily_trades": self.daily_trades_count,
            "max_daily_trades": self.portfolio_config.max_daily_trades,
            "daily_pnl_usd": self.daily_realized_pnl,
            "daily_loss_limit_usd": self.portfolio_config.max_daily_loss_usd,
            "total_exposure_usd": total_exposure,
            "equity_usd": self.equity,
            "exposure_pct": (total_exposure / self.equity * 100) if self.equity > 0 else 0,
            "max_exposure_pct": self.portfolio_config.max_portfolio_exposure_pct,
        }
