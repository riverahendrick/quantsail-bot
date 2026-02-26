/**
 * Centralized mock data for demo/development mode.
 *
 * IMPORTANT: This module is ONLY imported when DASHBOARD_CONFIG.USE_MOCK_DATA
 * is true (demo mode or explicit env toggle). It is never bundled into
 * production builds that talk to a real backend.
 *
 * Data here is designed to look realistic for a CEO demo.
 */

import type { BotState, Trade } from "@/types/dashboard";
import type {
    ConfigVersion,
    ExchangeKey,
    ManagedUser,
    StrategyPerformance,
    PortfolioRisk,
    KillSwitchStatus,
    GridPortfolio,
} from "./api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const now = new Date();
const iso = (daysAgo: number, hoursAgo = 0) =>
    new Date(
        now.getTime() - daysAgo * 86_400_000 - hoursAgo * 3_600_000
    ).toISOString();

// ---------------------------------------------------------------------------
// Bot Config (used by Strategy & Settings pages)
// ---------------------------------------------------------------------------

export const MOCK_BOT_CONFIG: ConfigVersion = {
    version: 3,
    config_hash: "a7f3c9e1d4b2",
    is_active: true,
    created_at: iso(2),
    config_json: {
        strategies: {
            ensemble: {
                mode: "weighted",
                confidence_threshold: 0.55,
                weighted_threshold: 0.6,
            },
            rsi_mean_reversion: { enabled: true, period: 14, oversold: 30, overbought: 70 },
            macd_crossover: { enabled: true, fast: 12, slow: 26, signal: 9 },
            bollinger_breakout: { enabled: true, period: 20, std_dev: 2.0 },
            volume_spike: { enabled: true, threshold_multiplier: 2.5 },
            trend_following: { enabled: false, ema_short: 9, ema_long: 21 },
        },
        execution: {
            order_type: "LIMIT",
            slippage_pct: 0.1,
            timeout_seconds: 30,
            retry_count: 2,
        },
        risk: {
            position_sizing: { method: "risk_pct", risk_pct: 1.0, max_position_pct: 25, kelly_fraction: 0.25 },
            stop_loss: { method: "atr", atr_multiplier: 2.0, fixed_pct: 2.0 },
            take_profit: { method: "risk_reward", risk_reward_ratio: 2.0, fixed_pct: 4.0 },
            trailing_stop: { enabled: true, method: "atr", trail_pct: 1.5, atr_multiplier: 2.5, activation_pct: 1.0 },
            portfolio: { max_daily_trades: 10, max_daily_loss_usd: 20, max_portfolio_exposure_pct: 30 },
        },
        symbols: {
            watchlist: ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT"],
            blacklist: ["LUNAAUSDT"],
        },
        breakers: {
            max_consecutive_losses: 5,
            max_daily_loss_pct: 3.0,
            max_drawdown_pct: 8.0,
        },
        daily: {
            target_usd: 25,
            mode: "OVERDRIVE",
        },
        // profile field for settings page
        profile: "moderate",
        position_sizing: { method: "risk_pct", risk_pct: 1.0, max_position_pct: 25, kelly_fraction: 0.25 },
        stop_loss: { method: "atr", atr_multiplier: 2.0, fixed_pct: 2.0 },
        take_profit: { method: "risk_reward", risk_reward_ratio: 2.0, fixed_pct: 4.0 },
        trailing_stop: { enabled: true, method: "atr", trail_pct: 1.5, atr_multiplier: 2.5, activation_pct: 1.0 },
        portfolio: { max_daily_trades: 10, max_daily_loss_usd: 20, max_portfolio_exposure_pct: 30 },
    } as ConfigVersion["config_json"],
};

// ---------------------------------------------------------------------------
// Exchange Keys
// ---------------------------------------------------------------------------

export const MOCK_EXCHANGE_KEYS: ExchangeKey[] = [
    {
        id: "k_8f3a1b4c-e5d2-4a9b-b7c6-d1e0f2a3b4c5",
        exchange: "binance",
        label: "Main Trading Key",
        key_version: 2,
        created_at: iso(30),
        revoked_at: null,
        is_active: true,
    },
    {
        id: "k_2c7d9e0f-a1b3-4c5d-e6f7-081920a1b2c3",
        exchange: "binance",
        label: "Read-Only Monitor",
        key_version: 1,
        created_at: iso(45),
        revoked_at: null,
        is_active: false,
    },
];

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export const MOCK_USERS: ManagedUser[] = [
    {
        id: "u_owner_001",
        email: "hendrick@quantsail.io",
        role: "OWNER",
        created_at: iso(60),
        disabled: false,
    },
    {
        id: "u_ceo_002",
        email: "carlos@quantsail.io",
        role: "CEO",
        created_at: iso(45),
        disabled: false,
    },
    {
        id: "u_dev_003",
        email: "dev@quantsail.io",
        role: "DEVELOPER",
        created_at: iso(20),
        disabled: false,
    },
];

// ---------------------------------------------------------------------------
// System Events
// ---------------------------------------------------------------------------

export const MOCK_EVENTS = [
    { id: "evt_001", seq: 1042, ts: iso(0, 0.1), level: "INFO", type: "TRADE_OPENED", symbol: "BTCUSDT", payload: { side: "LONG", entry: 97250.40, size_usd: 250 } },
    { id: "evt_002", seq: 1041, ts: iso(0, 0.3), level: "INFO", type: "TRADE_CLOSED", symbol: "ETHUSDT", payload: { side: "LONG", pnl_usd: 12.45, pnl_pct: 1.82 } },
    { id: "evt_003", seq: 1040, ts: iso(0, 0.8), level: "WARN", type: "RISK_LIMIT_NEAR", symbol: null, payload: { metric: "daily_loss", current: 15.2, limit: 20 } },
    { id: "evt_004", seq: 1039, ts: iso(0, 1.2), level: "INFO", type: "SIGNAL_GENERATED", symbol: "SOLUSDT", payload: { strategy: "rsi_mean_reversion", confidence: 0.72, direction: "LONG" } },
    { id: "evt_005", seq: 1038, ts: iso(0, 1.5), level: "INFO", type: "HEARTBEAT", symbol: null, payload: { uptime_hours: 72.4, cpu_pct: 12, mem_mb: 245 } },
    { id: "evt_006", seq: 1037, ts: iso(0, 2.0), level: "ERROR", type: "ORDER_REJECTED", symbol: "AVAXUSDT", payload: { reason: "Insufficient balance", order_type: "LIMIT" } },
    { id: "evt_007", seq: 1036, ts: iso(0, 3.0), level: "INFO", type: "TRADE_OPENED", symbol: "BNBUSDT", payload: { side: "LONG", entry: 685.20, size_usd: 180 } },
    { id: "evt_008", seq: 1035, ts: iso(0, 4.5), level: "INFO", type: "TRADE_CLOSED", symbol: "BTCUSDT", payload: { side: "LONG", pnl_usd: 8.30, pnl_pct: 0.95 } },
    { id: "evt_009", seq: 1034, ts: iso(0, 5.0), level: "WARN", type: "VOLATILITY_SPIKE", symbol: "SOLUSDT", payload: { atr_ratio: 2.8, action: "position_reduced" } },
    { id: "evt_010", seq: 1033, ts: iso(0, 6.0), level: "INFO", type: "REBALANCE", symbol: null, payload: { reason: "daily_schedule", positions_adjusted: 3 } },
    { id: "evt_011", seq: 1032, ts: iso(0, 8.0), level: "INFO", type: "CONFIG_ACTIVATED", symbol: null, payload: { version: 3, profile: "moderate" } },
    { id: "evt_012", seq: 1031, ts: iso(0, 12), level: "INFO", type: "BOT_STARTED", symbol: null, payload: { mode: "live", config_version: 3 } },
];

// ---------------------------------------------------------------------------
// Strategy Performance
// ---------------------------------------------------------------------------

export const MOCK_STRATEGY_PERFORMANCE: StrategyPerformance[] = [
    { name: "RSI Mean Reversion", enabled: true, total_trades: 142, win_rate: 0.68, profit_factor: 1.85, net_pnl_usd: 324.50, avg_trade_usd: 2.28, last_signal_at: iso(0, 0.5) },
    { name: "MACD Crossover", enabled: true, total_trades: 98, win_rate: 0.62, profit_factor: 1.62, net_pnl_usd: 187.20, avg_trade_usd: 1.91, last_signal_at: iso(0, 1.2) },
    { name: "Bollinger Breakout", enabled: true, total_trades: 67, win_rate: 0.58, profit_factor: 1.45, net_pnl_usd: 112.80, avg_trade_usd: 1.68, last_signal_at: iso(0, 3.0) },
    { name: "Volume Spike", enabled: true, total_trades: 45, win_rate: 0.71, profit_factor: 2.10, net_pnl_usd: 156.90, avg_trade_usd: 3.49, last_signal_at: iso(0, 2.0) },
    { name: "Trend Following", enabled: false, total_trades: 23, win_rate: 0.52, profit_factor: 1.12, net_pnl_usd: -12.40, avg_trade_usd: -0.54, last_signal_at: iso(5) },
];

// ---------------------------------------------------------------------------
// Portfolio Risk
// ---------------------------------------------------------------------------

export const MOCK_PORTFOLIO_RISK: PortfolioRisk = {
    total_exposure_usd: 2450.00,
    open_positions: 3,
    max_drawdown_pct: 4.2,
    current_drawdown_pct: 1.8,
    daily_pnl_usd: 18.65,
    daily_pnl_pct: 0.19,
    var_95_usd: 85.00,
    risk_level: "LOW",
};

// ---------------------------------------------------------------------------
// Kill Switch Status
// ---------------------------------------------------------------------------

export const MOCK_KILL_SWITCH: KillSwitchStatus = {
    is_killed: false,
    current_event: null,
    history_count: 2,
    daily_pnl_pct: 0.19,
    current_drawdown_pct: 1.8,
    consecutive_losses: 1,
};

// ---------------------------------------------------------------------------
// Grid Portfolio
// ---------------------------------------------------------------------------

export const MOCK_GRID_PORTFOLIO: GridPortfolio = {
    active: true,
    started_at: iso(14),
    total_capital_usd: 5000,
    coins: [
        {
            symbol: "BTC", pair: "BTCUSDT", allocation_usd: 2000, cash: 450,
            grid_center: 97100.00, num_grids: 20, lower_pct: -5, upper_pct: 5,
            total_buys: 34, total_sells: 31, total_pnl: 145.20, total_fees: 8.50, net_pnl: 136.70,
            active_orders: 4, filled_levels: 12, total_levels: 20, num_rebalances: 3, last_updated: iso(0, 0.2),
        },
        {
            symbol: "ETH", pair: "ETHUSDT", allocation_usd: 1500, cash: 320,
            grid_center: 2680.00, num_grids: 15, lower_pct: -6, upper_pct: 6,
            total_buys: 28, total_sells: 25, total_pnl: 92.40, total_fees: 5.80, net_pnl: 86.60,
            active_orders: 3, filled_levels: 9, total_levels: 15, num_rebalances: 2, last_updated: iso(0, 0.4),
        },
        {
            symbol: "SOL", pair: "SOLUSDT", allocation_usd: 800, cash: 180,
            grid_center: 172.50, num_grids: 12, lower_pct: -8, upper_pct: 8,
            total_buys: 18, total_sells: 15, total_pnl: 42.10, total_fees: 3.20, net_pnl: 38.90,
            active_orders: 2, filled_levels: 7, total_levels: 12, num_rebalances: 1, last_updated: iso(0, 1.0),
        },
        {
            symbol: "BNB", pair: "BNBUSDT", allocation_usd: 700, cash: 150,
            grid_center: 685.00, num_grids: 10, lower_pct: -4, upper_pct: 4,
            total_buys: 12, total_sells: 10, total_pnl: 28.50, total_fees: 2.10, net_pnl: 26.40,
            active_orders: 2, filled_levels: 6, total_levels: 10, num_rebalances: 1, last_updated: iso(0, 1.5),
        },
    ],
    summary: {
        total_buys: 92,
        total_sells: 81,
        total_pnl: 308.20,
        total_fees: 19.60,
        net_pnl: 288.60,
    },
};

// ---------------------------------------------------------------------------
// Bot State (for Zustand store — overview KPIs, status banner, daily lock)
// ---------------------------------------------------------------------------

export const MOCK_BOT_STATE: BotState = {
    status: "running",
    status_reason: "Live trading — moderate profile active",
    equity_usd: 10842.50,
    realized_pnl_today_usd: 18.65,
    win_rate_30d: 0.645,
    profit_factor_30d: 1.72,
    daily_lock: {
        target_usd: 25,
        mode: "OVERDRIVE",
        realized_pnl: 18.65,
        peak_pnl: 22.10,
        floor_usd: 12.00,
        entries_paused: false,
    },
    active_breakers: [],
};

// ---------------------------------------------------------------------------
// Recent Trades (for Zustand store — RecentTrades widget)
// ---------------------------------------------------------------------------

export const MOCK_TRADES: Trade[] = [
    { id: "t_001", symbol: "BTCUSDT", side: "LONG", status: "OPEN", mode: "LIVE", entry_price: 97250.40, opened_at: iso(0, 0.1) },
    { id: "t_002", symbol: "BNBUSDT", side: "LONG", status: "OPEN", mode: "LIVE", entry_price: 685.20, opened_at: iso(0, 3.0) },
    { id: "t_003", symbol: "ETHUSDT", side: "LONG", status: "CLOSED", mode: "LIVE", entry_price: 2665.00, exit_price: 2713.50, pnl_usd: 12.45, pnl_pct: 1.82, opened_at: iso(0, 2.0), closed_at: iso(0, 0.3) },
    { id: "t_004", symbol: "BTCUSDT", side: "LONG", status: "CLOSED", mode: "LIVE", entry_price: 96800.00, exit_price: 97720.00, pnl_usd: 8.30, pnl_pct: 0.95, opened_at: iso(0, 6.0), closed_at: iso(0, 4.5) },
    { id: "t_005", symbol: "SOLUSDT", side: "LONG", status: "CLOSED", mode: "LIVE", entry_price: 170.20, exit_price: 173.80, pnl_usd: 5.12, pnl_pct: 2.12, opened_at: iso(0, 8.0), closed_at: iso(0, 5.5) },
    { id: "t_006", symbol: "AVAXUSDT", side: "SHORT", status: "CLOSED", mode: "LIVE", entry_price: 38.50, exit_price: 39.10, pnl_usd: -3.12, pnl_pct: -1.56, opened_at: iso(0, 10), closed_at: iso(0, 7.0) },
    { id: "t_007", symbol: "BNBUSDT", side: "LONG", status: "CLOSED", mode: "LIVE", entry_price: 680.00, exit_price: 688.50, pnl_usd: 4.50, pnl_pct: 1.25, opened_at: iso(0, 14), closed_at: iso(0, 11) },
    { id: "t_008", symbol: "ETHUSDT", side: "LONG", status: "CLOSED", mode: "LIVE", entry_price: 2640.00, exit_price: 2655.00, pnl_usd: 2.85, pnl_pct: 0.57, opened_at: iso(1, 2.0), closed_at: iso(0, 20) },
];
