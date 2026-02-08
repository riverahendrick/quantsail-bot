"""Pydantic configuration models with type safety and validation."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


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


class PositionSizingConfig(BaseModel):
    """Dynamic position sizing configuration."""

    method: Literal["fixed", "risk_pct", "kelly"] = Field(
        default="risk_pct",
        description="Sizing method: fixed (static qty), risk_pct (ATR-based risk), kelly (Kelly criterion)",
    )
    fixed_quantity: float = Field(
        default=0.01,
        gt=0.0,
        description="Fixed position quantity (used when method=fixed). Recommended: 0.01 for BTC",
    )
    risk_pct: float = Field(
        default=1.0,
        gt=0.0,
        le=10.0,
        description="Risk per trade as % of equity (used when method=risk_pct). Recommended: 1-2%",
    )
    max_position_pct: float = Field(
        default=10.0,
        gt=0.0,
        le=100.0,
        description="Maximum single position size as % of equity. Recommended: 5-15%",
    )
    kelly_fraction: float = Field(
        default=0.25,
        gt=0.0,
        le=1.0,
        description="Kelly fraction multiplier (0.25 = quarter-Kelly). Recommended: 0.25",
    )


class StopLossConfig(BaseModel):
    """Stop-loss configuration."""

    method: Literal["fixed_pct", "atr"] = Field(
        default="atr",
        description="SL method: fixed_pct (static %) or atr (ATR-multiple). Recommended: atr",
    )
    fixed_pct: float = Field(
        default=2.0,
        gt=0.0,
        le=50.0,
        description="Fixed SL as % below entry (used when method=fixed_pct). Recommended: 1.5-3%",
    )
    atr_period: int = Field(
        default=14,
        ge=5,
        le=50,
        description="ATR period for dynamic SL calculation. Recommended: 14",
    )
    atr_multiplier: float = Field(
        default=2.0,
        gt=0.0,
        le=10.0,
        description="ATR multiplier for SL distance. Recommended: 1.5-3.0",
    )


class TakeProfitConfig(BaseModel):
    """Take-profit configuration."""

    method: Literal["fixed_pct", "atr", "risk_reward"] = Field(
        default="risk_reward",
        description="TP method: fixed_pct (static %), atr (ATR-multiple), risk_reward (ratio of SL). Recommended: risk_reward",
    )
    fixed_pct: float = Field(
        default=4.0,
        gt=0.0,
        le=100.0,
        description="Fixed TP as % above entry (used when method=fixed_pct). Recommended: 3-6%",
    )
    atr_multiplier: float = Field(
        default=3.0,
        gt=0.0,
        le=10.0,
        description="ATR multiplier for TP distance (used when method=atr). Recommended: 2.0-4.0",
    )
    risk_reward_ratio: float = Field(
        default=2.0,
        gt=0.0,
        le=10.0,
        description="Risk:reward ratio (TP = SL_distance * ratio). Recommended: 2.0-3.0",
    )


class TrailingStopConfig(BaseModel):
    """Trailing stop-loss configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable trailing stop-loss. Recommended: True",
    )
    method: Literal["atr", "pct", "chandelier"] = Field(
        default="atr",
        description="Trailing method: atr (ATR-based), pct (fixed %), chandelier (ATR from high). Recommended: atr",
    )
    atr_period: int = Field(
        default=14,
        ge=5,
        le=50,
        description="ATR period for trailing calculation. Recommended: 14",
    )
    atr_multiplier: float = Field(
        default=2.5,
        gt=0.0,
        le=10.0,
        description="ATR multiplier for trailing distance. Recommended: 2.0-3.0",
    )
    trail_pct: float = Field(
        default=2.0,
        gt=0.0,
        le=50.0,
        description="Fixed trailing % (used when method=pct). Recommended: 1.5-3%",
    )
    activation_pct: float = Field(
        default=1.0,
        ge=0.0,
        le=50.0,
        description="Profit % threshold to activate trailing (0 = immediate). Recommended: 0.5-1.5%",
    )


class TrendStrategyConfig(BaseModel):
    """Configuration for Trend Strategy."""
    ema_fast: int = Field(default=20, ge=2, description="Fast EMA period. Recommended: 12-20")
    ema_slow: int = Field(default=50, ge=5, description="Slow EMA period. Recommended: 50-200")
    adx_threshold: float = Field(default=25.0, ge=0.0, le=100.0, description="Min ADX for trend confirmation. Recommended: 20-30")

    @model_validator(mode="after")
    def _ema_fast_lt_slow(self) -> "TrendStrategyConfig":
        if self.ema_fast >= self.ema_slow:
            raise ValueError(
                f"ema_fast ({self.ema_fast}) must be less than ema_slow ({self.ema_slow})"
            )
        return self


class MeanReversionStrategyConfig(BaseModel):
    """Configuration for Mean Reversion Strategy."""
    bb_period: int = Field(default=20, ge=5, description="Bollinger Band period. Recommended: 20")
    bb_std_dev: float = Field(default=2.0, gt=0.0, description="Bollinger Band std dev multiplier. Recommended: 2.0")
    rsi_period: int = Field(default=14, ge=5, description="RSI period. Recommended: 14")
    rsi_oversold: float = Field(default=30.0, ge=0.0, le=100.0, description="RSI oversold threshold. Recommended: 25-35")


class BreakoutStrategyConfig(BaseModel):
    """Configuration for Breakout Strategy."""
    donchian_period: int = Field(default=20, ge=5, description="Donchian Channel period. Recommended: 20")
    atr_period: int = Field(default=14, ge=5, description="ATR period for volatility filter. Recommended: 14")
    atr_filter_mult: float = Field(default=1.0, gt=0.0, description="ATR filter multiplier for breakout validation. Recommended: 1.0")


class VWAPReversionConfig(BaseModel):
    """Configuration for VWAP Mean Reversion Strategy."""

    enabled: bool = Field(default=True, description="Enable VWAP reversion strategy")
    deviation_entry_pct: float = Field(
        default=1.5,
        gt=0.0,
        le=10.0,
        description="Min % deviation below VWAP to trigger long entry. Recommended: 1.0-2.5%",
    )
    deviation_exit_pct: float = Field(
        default=0.3,
        ge=0.0,
        le=5.0,
        description="% deviation from VWAP to trigger exit (revert to mean). Recommended: 0.1-0.5%",
    )
    obv_confirmation: bool = Field(
        default=True,
        description="Require OBV uptick to confirm VWAP entry. Recommended: True",
    )
    rsi_oversold: float = Field(
        default=35.0,
        ge=0.0,
        le=100.0,
        description="RSI oversold threshold for VWAP strategy. Recommended: 30-40",
    )
    rsi_period: int = Field(
        default=14,
        ge=5,
        le=50,
        description="RSI period for VWAP strategy. Recommended: 14",
    )


class MACDStrategyConfig(BaseModel):
    """MACD indicator configuration (used across strategies)."""

    fast_period: int = Field(default=12, ge=2, description="MACD fast EMA period. Recommended: 12")
    slow_period: int = Field(default=26, ge=5, description="MACD slow EMA period. Recommended: 26")
    signal_period: int = Field(default=9, ge=2, description="MACD signal line period. Recommended: 9")


class PerCoinStrategyOverride(BaseModel):
    """Per-symbol strategy weight overrides for per-coin routing.

    When set, these weights override the global ensemble weights for a
    specific trading symbol. Fields left as None fall back to the global value.

    Example: To route XRP through trend-only:
        PerCoinStrategyOverride(
            weight_trend=1.0,
            weight_mean_reversion=0.0,
            weight_breakout=0.0,
            weight_vwap=0.0,
        )
    """

    weight_trend: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Override trend weight for this symbol (None = use global)",
    )
    weight_mean_reversion: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Override mean reversion weight for this symbol (None = use global)",
    )
    weight_breakout: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Override breakout weight for this symbol (None = use global)",
    )
    weight_vwap: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Override VWAP weight for this symbol (None = use global)",
    )
    min_agreement: int | None = Field(
        default=None, ge=1,
        description="Override min_agreement for this symbol (None = use global)",
    )
    confidence_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Override confidence_threshold for this symbol (None = use global)",
    )
    weighted_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Override weighted_threshold for this symbol (None = use global)",
    )


class EnsembleConfig(BaseModel):
    """Configuration for Ensemble Logic."""

    mode: Literal["agreement", "weighted"] = Field(
        default="agreement",
        description="Ensemble mode: agreement (min N agree), weighted (weighted score). Recommended: weighted",
    )
    min_agreement: int = Field(
        default=2,
        ge=1,
        description="Min strategies that must agree (agreement mode). Recommended: 2",
    )
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Min confidence to accept signal (agreement mode). Recommended: 0.4-0.6",
    )
    weighted_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Min weighted score to accept signal (weighted mode). Recommended: 0.5-0.7",
    )
    weight_trend: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Weight for trend strategy (weighted mode). Recommended: 0.25-0.40",
    )
    weight_mean_reversion: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Weight for mean reversion strategy (weighted mode). Recommended: 0.20-0.30",
    )
    weight_breakout: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Weight for breakout strategy (weighted mode). Recommended: 0.15-0.25",
    )
    weight_vwap: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Weight for VWAP reversion strategy (weighted mode). Recommended: 0.20-0.30",
    )
    per_coin_overrides: dict[str, PerCoinStrategyOverride] = Field(
        default_factory=dict,
        description=(
            "Per-symbol strategy weight overrides. Keys are symbol names "
            "(e.g. 'XRP', 'BNB'). Values override the global ensemble weights "
            "for that symbol. Unspecified symbols use global weights."
        ),
    )


class SymbolRegimeOverride(BaseModel):
    """Per-symbol overrides for regime filter thresholds."""
    adx_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Override ADX threshold for this symbol (None = use global)",
    )
    atr_threshold_pct: float | None = Field(
        default=None,
        ge=0.0,
        description="Override ATR% threshold for this symbol (None = use global)",
    )


class RegimeConfig(BaseModel):
    """Configuration for Market Regime Filtering."""
    enabled: bool = Field(default=True, description="Enable regime filtering to avoid chop")
    adx_period: int = Field(default=14, ge=5, description="ADX period. Recommended: 14")
    adx_threshold: float = Field(
        default=25.0,
        ge=0.0,
        le=100.0,
        description="Min ADX to consider market trending. Recommended: 20-25"
    )
    atr_period: int = Field(default=14, ge=5, description="ATR period. Recommended: 14")
    atr_threshold_pct: float = Field(
        default=0.5,
        ge=0.0,
        description="Min ATR% (ATR/Close * 100) to consider market volatile. Recommended: 0.5-1.0%"
    )
    per_symbol_overrides: dict[str, SymbolRegimeOverride] = Field(
        default_factory=dict,
        description="Per-symbol threshold overrides (e.g. {'BTC': {'adx_threshold': 30}})",
    )


class StrategiesConfig(BaseModel):
    """Container for all strategy configurations."""
    trend: TrendStrategyConfig = Field(default_factory=TrendStrategyConfig)
    mean_reversion: MeanReversionStrategyConfig = Field(default_factory=MeanReversionStrategyConfig)
    breakout: BreakoutStrategyConfig = Field(default_factory=BreakoutStrategyConfig)
    vwap_reversion: VWAPReversionConfig = Field(default_factory=VWAPReversionConfig)
    macd: MACDStrategyConfig = Field(default_factory=MACDStrategyConfig)
    ensemble: EnsembleConfig = Field(default_factory=EnsembleConfig)
    regime: RegimeConfig = Field(default_factory=RegimeConfig)


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


class PortfolioConfig(BaseModel):
    """Portfolio-level risk constraints."""
    max_correlated_positions: int = Field(
        default=1,
        ge=1,
        description="Maximum positions in correlated symbols (e.g., both BTC/USDT and ETH/USDT)",
    )
    max_daily_trades: int = Field(
        default=10,
        ge=1,
        description="Maximum number of trades allowed per day",
    )
    max_daily_loss_usd: float = Field(
        default=20.0,
        ge=0.0,
        description="Daily loss limit in USD that triggers trading halt",
    )
    max_portfolio_exposure_pct: float = Field(
        default=30.0,
        gt=0.0,
        le=100.0,
        description="Maximum total exposure as percentage of equity",
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


class CooldownConfig(BaseModel):
    """Configuration for stop-loss cooldown gate."""
    enabled: bool = Field(default=True, description="Enable cooldown after stop-loss exits")
    cooldown_minutes: int = Field(
        default=360,
        ge=0,
        description="Minutes to block re-entry after a stop-loss exit. Recommended: 360 (6h)",
    )


class DailySymbolLimitConfig(BaseModel):
    """Configuration for daily per-symbol consecutive loss limit."""
    enabled: bool = Field(default=True, description="Enable daily per-symbol loss limit")
    max_consecutive_losses: int = Field(
        default=2,
        ge=1,
        description="Max consecutive losses per symbol per day before pausing. Recommended: 2",
    )


class StreakSizerConfig(BaseModel):
    """Configuration for losing streak position size reduction."""
    enabled: bool = Field(default=True, description="Enable position size reduction on losing streaks")
    reduction_factor: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description="Position size multiplier after consecutive losses. Recommended: 0.5 (half size)",
    )
    min_consecutive_losses: int = Field(
        default=2,
        ge=1,
        description="Consecutive losses before reduction kicks in. Recommended: 2",
    )


class GridSymbolConfig(BaseModel):
    """Per-symbol grid trading configuration."""

    enabled: bool = Field(default=True, description="Enable grid trading for this symbol")
    lower_pct: float = Field(
        default=5.0, gt=0.0, le=50.0,
        description="Grid lower bound as pct below reference price. E.g. 5.0 = -5%",
    )
    upper_pct: float = Field(
        default=5.0, gt=0.0, le=50.0,
        description="Grid upper bound as pct above reference price. E.g. 5.0 = +5%",
    )
    num_grids: int = Field(
        default=15, ge=3, le=500,
        description="Number of grid levels. More grids = more trades, smaller profit each",
    )
    allocation_usd: float = Field(
        default=1000.0, gt=0.0,
        description="Capital allocated to this symbol's grid",
    )
    rebalance_on_breakout: bool = Field(
        default=True,
        description="Auto-shift grid if price breaks out of range",
    )


class GridConfig(BaseModel):
    """Grid trading configuration for consistent daily income."""

    enabled: bool = Field(default=False, description="Enable grid trading layer")
    fee_pct: float = Field(
        default=0.1, ge=0.0, le=5.0,
        description="Trading fee per side in percent (e.g. 0.1 = 0.1%)",
    )
    symbols: dict[str, GridSymbolConfig] = Field(
        default_factory=dict,
        description=(
            "Per-symbol grid configs. Keys are symbol names (e.g. 'BTC'). "
            "Grid bots run independently on each configured symbol."
        ),
    )


class BotConfig(BaseModel):
    """Top-level bot configuration."""

    profile: Literal["conservative", "moderate", "aggressive", "custom"] = Field(
        default="custom",
        description="Parameter profile: conservative, moderate, aggressive, or custom",
    )
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    symbols: SymbolsConfig = Field(default_factory=SymbolsConfig)
    strategies: StrategiesConfig = Field(default_factory=StrategiesConfig)
    breakers: BreakerConfig = Field(default_factory=BreakerConfig)
    daily: DailyConfig = Field(default_factory=DailyConfig)
    portfolio: PortfolioConfig = Field(default_factory=PortfolioConfig)
    position_sizing: PositionSizingConfig = Field(default_factory=PositionSizingConfig)
    stop_loss: StopLossConfig = Field(default_factory=StopLossConfig)
    take_profit: TakeProfitConfig = Field(default_factory=TakeProfitConfig)
    trailing_stop: TrailingStopConfig = Field(default_factory=TrailingStopConfig)
    cooldown: "CooldownConfig" = Field(default_factory=lambda: CooldownConfig())
    daily_symbol_limit: "DailySymbolLimitConfig" = Field(
        default_factory=lambda: DailySymbolLimitConfig()
    )
    streak_sizer: "StreakSizerConfig" = Field(
        default_factory=lambda: StreakSizerConfig()
    )
    grid: GridConfig = Field(default_factory=GridConfig)

    @model_validator(mode="after")
    def _validate_risk_coherence(self) -> "BotConfig":
        """Validate that SL/TP/position sizing parameters are coherent."""
        # Risk per trade should not exceed max position exposure
        if self.risk.max_risk_per_trade_pct > self.portfolio.max_portfolio_exposure_pct:
            raise ValueError(
                f"max_risk_per_trade_pct ({self.risk.max_risk_per_trade_pct}) "
                f"cannot exceed max_portfolio_exposure_pct ({self.portfolio.max_portfolio_exposure_pct})"
            )
        # Daily loss limit should not exceed daily target (sanity check)
        if self.portfolio.max_daily_loss_usd > self.daily.target_usd * 2:
            raise ValueError(
                f"max_daily_loss_usd ({self.portfolio.max_daily_loss_usd}) "
                f"should not exceed 2x daily target_usd ({self.daily.target_usd})"
            )
        return self

