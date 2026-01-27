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
    taker_fee_bps: float = Field(
        default=10.0,  # 0.1%
        ge=0.0,
        description="Taker fee in basis points (e.g. 10 bps = 0.1%)",
    )
    maker_fee_bps: float = Field(
        default=10.0,  # 0.1%
        ge=0.0,
        description="Maker fee in basis points (e.g. 10 bps = 0.1%)",
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


class VolatilityBreakerConfig(BaseModel):
    """Configuration for volatility spike breaker."""
    enabled: bool = Field(default=True, description="Enable volatility spike breaker")
    atr_multiple_pause: float = Field(
        default=3.0,
        ge=0.0,
        description="ATR multiple threshold to trigger pause (e.g., 3.0 = 3x ATR)",
    )
    pause_minutes: int = Field(
        default=30,
        ge=1,
        description="Minutes to pause entries after trigger",
    )


class SpreadSlippageBreakerConfig(BaseModel):
    """Configuration for spread/slippage spike breaker."""
    enabled: bool = Field(default=True, description="Enable spread/slippage spike breaker")
    max_spread_bps: float = Field(
        default=50.0,
        ge=0.0,
        description="Maximum spread in basis points (e.g., 50 bps = 0.5%)",
    )
    pause_minutes: int = Field(
        default=30,
        ge=1,
        description="Minutes to pause entries after trigger",
    )


class ConsecutiveLossesBreakerConfig(BaseModel):
    """Configuration for consecutive losses breaker."""
    enabled: bool = Field(default=True, description="Enable consecutive losses breaker")
    max_losses: int = Field(
        default=3,
        ge=1,
        description="Maximum consecutive losing trades before pause",
    )
    pause_minutes: int = Field(
        default=180,
        ge=1,
        description="Minutes to pause entries after trigger",
    )


class ExchangeInstabilityBreakerConfig(BaseModel):
    """Configuration for exchange instability breaker."""
    enabled: bool = Field(default=True, description="Enable exchange instability breaker")
    max_disconnects_5m: int = Field(
        default=5,
        ge=1,
        description="Maximum disconnects in 5 minutes before pause",
    )
    pause_minutes: int = Field(
        default=60,
        ge=1,
        description="Minutes to pause entries after trigger",
    )


class NewsPauseConfig(BaseModel):
    """Configuration for news-based pause (stub for MVP)."""
    enabled: bool = Field(default=False, description="Enable news-based pause (MVP stub)")
    provider: str = Field(default="newsapi", description="News provider (stub)")
    impact_threshold: str = Field(default="high", description="Impact threshold (stub)")
    negative_pause_minutes: int = Field(
        default=60,
        ge=1,
        description="Minutes to pause on negative news (stub)",
    )


class DailyConfig(BaseModel):
    """Daily profit target and lock configuration."""
    enabled: bool = Field(default=True, description="Enable daily target lock")
    target_usd: float = Field(
        default=50.0,
        ge=0.0,
        description="Daily profit target in USD",
    )
    mode: Literal["STOP", "OVERDRIVE"] = Field(
        default="STOP",
        description="Daily lock mode: STOP (pause at target) or OVERDRIVE (trail floor)",
    )
    overdrive_trailing_buffer_usd: float = Field(
        default=10.0,
        ge=0.0,
        description="Trailing buffer in USD for OVERDRIVE mode",
    )
    timezone: str = Field(
        default="UTC",
        description="Timezone for daily boundary (e.g., UTC, America/New_York)",
    )


class BreakerConfig(BaseModel):
    """Container for all circuit breaker configurations."""
    volatility: VolatilityBreakerConfig = Field(
        default_factory=VolatilityBreakerConfig
    )
    spread_slippage: SpreadSlippageBreakerConfig = Field(
        default_factory=SpreadSlippageBreakerConfig
    )
    consecutive_losses: ConsecutiveLossesBreakerConfig = Field(
        default_factory=ConsecutiveLossesBreakerConfig
    )
    exchange_instability: ExchangeInstabilityBreakerConfig = Field(
        default_factory=ExchangeInstabilityBreakerConfig
    )
    news: NewsPauseConfig = Field(default_factory=NewsPauseConfig)


class BotConfig(BaseModel):
    """Top-level bot configuration."""

    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    symbols: SymbolsConfig = Field(default_factory=SymbolsConfig)
    strategies: StrategiesConfig = Field(default_factory=StrategiesConfig)
    breakers: BreakerConfig = Field(default_factory=BreakerConfig)
    daily: DailyConfig = Field(default_factory=DailyConfig)
