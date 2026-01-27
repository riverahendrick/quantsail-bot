# Quantsail — Configuration Specification v1 (No Guessing)

All configuration must be:
- validated (schema + constraints),
- stored as versioned records in Postgres,
- activated explicitly,
- and reflected in engine behavior.

## 1) Sections
exchange, symbols, execution, risk, strategies, gates, breakers, daily_lock, news, transparency, observability

## 2) Keys (explicit)
### 2.1 exchange
- exchange.name: "binance"
- exchange.market_type: "spot"
- exchange.quote_asset_allowlist: ["USDT","USDC"]
- exchange.fee_model: { type:"fixed_bps", maker_bps:10, taker_bps:10 }

### 2.2 symbols
- symbols.enabled: ["BTC/USDT","ETH/USDT"]
- symbols.max_concurrent_positions: 1
- symbols.per_symbol_overrides: {}

### 2.3 execution
- execution.mode: "dry-run" | "live" (default "dry-run")
- execution.arm_live_required: true
- execution.order_type_entry: "market" | "limit" (default "market")
- execution.order_type_exit: "market" | "limit" (default "market")
- execution.slippage_model: { type:"orderbook_depth", depth_levels:10 }
- execution.min_profit_usd: 0.10

### 2.4 risk
- risk.max_risk_per_trade_pct: 0.25
- risk.max_position_pct_equity: 20
- risk.min_notional_usd: 10
- risk.max_trades_per_day: null

### 2.5 strategies
- strategies.enabled: { trend:true, mean_reversion:true, breakout:true }
- strategies.timeframes: ["1m","5m","15m","1h"]
- strategies.ensemble: { min_agreement:2, confidence_threshold:0.60 }

### 2.6 gates
- gates.profitability_enabled: true
- gates.require_spread_under_bps: 30
- gates.require_volatility_under: null

### 2.7 breakers
- breakers.volatility: { enabled:true, atr_multiple_pause:3.0, pause_minutes:30 }
- breakers.spread_slippage: { enabled:true, max_spread_bps:50, pause_minutes:30 }
- breakers.consecutive_losses: { enabled:true, max_losses:3, pause_minutes:180 }
- breakers.exchange_instability: { enabled:true, max_disconnects_5m:5, pause_minutes:60 }

### 2.8 daily_lock
- daily_lock.enabled: true
- daily_lock.daily_target_usd: 2.00
- daily_lock.mode: "STOP" | "OVERDRIVE" (default "STOP")
- daily_lock.overdrive_trailing_buffer_usd: 5.00
- daily_lock.force_close_on_floor: false

### 2.9 news
- news.enabled: true
- news.provider: "cryptopanic"
- news.impact_threshold: "high"
- news.negative_pause_minutes: 120

### 2.10 transparency
- transparency.public_delay_seconds: 0
- transparency.hide_exact_sizes: true
- transparency.size_buckets_usd: [10,25,50,100,250,500,1000]

### 2.11 observability
- observability.metrics_enabled: true
- observability.log_level: "INFO"
- observability.alerts_enabled: true
