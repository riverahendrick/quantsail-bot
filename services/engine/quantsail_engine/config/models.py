"""Pydantic configuration models with type safety and validation."""

from typing import Literal

from pydantic import BaseModel, Field


class ExecutionConfig(BaseModel):
    """Execution mode and profitability settings."""

    mode: Literal["dry-run", "live"] = Field(
        default="dry-run",
        description="Trading mode: dry-run for simulation, live for real execution",
    )
    min_profit_usd: float = Field(
        default=0.10,
        ge=0.0,
        description="Minimum expected profit in USD to accept a trade",
    )


class RiskConfig(BaseModel):
    """Risk management parameters."""

    starting_cash_usd: float = Field(
        default=10000.0,
        gt=0.0,
        description="Starting cash in USD for equity calculations",
    )
    max_risk_per_trade_pct: float = Field(
        default=0.25,
        gt=0.0,
        le=100.0,
        description="Maximum risk per trade as percentage of portfolio",
    )


class SymbolsConfig(BaseModel):
    """Symbol configuration and position limits."""

    enabled: list[str] = Field(
        default_factory=lambda: ["BTC/USDT"],
        min_length=1,
        description="List of trading symbols (e.g., BTC/USDT, ETH/USDT)",
    )
    max_concurrent_positions: int = Field(
        default=1,
        ge=1,
        description="Maximum number of concurrent positions allowed",
    )


class TrendStrategyConfig(BaseModel):
    """Configuration for Trend Strategy."""
    ema_fast: int = 20
    ema_slow: int = 50
    adx_threshold: float = 25.0


class MeanReversionStrategyConfig(BaseModel):
    """Configuration for Mean Reversion Strategy."""
    bb_period: int = 20
    bb_std_dev: float = 2.0
    rsi_period: int = 14
    rsi_oversold: float = 30.0


class BreakoutStrategyConfig(BaseModel):
    """Configuration for Breakout Strategy."""
    donchian_period: int = 20
    atr_period: int = 14
    atr_filter_mult: float = 1.0


class EnsembleConfig(BaseModel):
    """Configuration for Ensemble Logic."""
    min_agreement: int = 2
    confidence_threshold: float = 0.5


class StrategiesConfig(BaseModel):
    """Container for all strategy configurations."""
    trend: TrendStrategyConfig = Field(default_factory=TrendStrategyConfig)
    mean_reversion: MeanReversionStrategyConfig = Field(default_factory=MeanReversionStrategyConfig)
    breakout: BreakoutStrategyConfig = Field(default_factory=BreakoutStrategyConfig)
    ensemble: EnsembleConfig = Field(default_factory=EnsembleConfig)


class BotConfig(BaseModel):
    """Top-level bot configuration."""

    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    symbols: SymbolsConfig = Field(default_factory=SymbolsConfig)
    strategies: StrategiesConfig = Field(default_factory=StrategiesConfig)
