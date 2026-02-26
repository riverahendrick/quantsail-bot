import { auth } from "./firebase";
import { DASHBOARD_CONFIG } from "./config";
import {
    MOCK_BOT_CONFIG,
    MOCK_EXCHANGE_KEYS,
    MOCK_USERS,
    MOCK_EVENTS,
    MOCK_STRATEGY_PERFORMANCE,
    MOCK_PORTFOLIO_RISK,
    MOCK_KILL_SWITCH,
    MOCK_GRID_PORTFOLIO,
} from "./mock-data";

// Mock data responses for development (only used when explicitly enabled)
function getMockResponse<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const method = (options.method || "GET").toUpperCase();

    // For write operations, return a mock success response
    if (method !== "GET") {
        const writeResponse: Record<string, unknown> = {
            success: true,
            message: `Mock ${method} to ${endpoint} accepted`,
            // Return a plausible object for POST/PATCH that pages might use
            version: 1,
            config_hash: "mock_hash_abc123",
            is_active: true,
            created_at: new Date().toISOString(),
        };
        return Promise.resolve(writeResponse as T);
    }

    // Endpoint-to-mock-data map for GET requests
    const mocks: Record<string, unknown> = {
        "/v1/config": {
            version: 3,
            config_hash: "a1b2c3d4e5f6",
            is_active: true,
            created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
            config_json: MOCK_BOT_CONFIG,
        },
        "/v1/exchanges/binance/keys/status": MOCK_EXCHANGE_KEYS,
        "/v1/users": MOCK_USERS,
        "/v1/events": MOCK_EVENTS,
        "/v1/strategies/performance": MOCK_STRATEGY_PERFORMANCE,
        "/v1/risk/portfolio": MOCK_PORTFOLIO_RISK,
        "/v1/risk/kill-switch/status": MOCK_KILL_SWITCH,
        "/v1/grid/portfolio": MOCK_GRID_PORTFOLIO,
    };

    // Try exact match first, then prefix match for parameterized routes
    let data = mocks[endpoint];
    if (!data) {
        // Handle parameterized routes like /v1/grid/BTCUSDT
        if (endpoint.startsWith("/v1/grid/")) {
            const symbol = endpoint.split("/v1/grid/")[1];
            const coin = MOCK_GRID_PORTFOLIO.coins.find(
                (c: { symbol: string }) => c.symbol.toUpperCase() === symbol?.toUpperCase()
            );
            data = coin ? { ...coin, levels: [] } : {};
        }
    }

    return Promise.resolve((data || {}) as T);
}

async function getHeaders() {
    const user = auth.currentUser;
    const headers: HeadersInit = { "Content-Type": "application/json" };
    if (user) {
        const token = await user.getIdToken();
        headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
}

export async function fetchPrivate<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    // If Mock Data is enabled, return mock responses
    if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
        return getMockResponse<T>(endpoint, options);
    }

    const headers = await getHeaders();
    const url = `${DASHBOARD_CONFIG.API_URL}${endpoint}`;

    let res: Response;
    try {
        res = await fetch(url, {
            ...options,
            headers: { ...headers, ...options.headers },
        });
    } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Unknown network error";
        throw new Error(`Network error calling ${url}. Is the API running and reachable? ${message}`);
    }

    if (!res.ok) {
        const errorText = await res.text();
        let errorJson;
        try {
            errorJson = JSON.parse(errorText);
        } catch {
            errorJson = {};
        }
        throw new Error(errorJson.detail?.message || errorJson.detail || `API Error ${res.status}: ${errorText}`);
    }

    return res.json() as Promise<T>;
}

// --- Config ---

export interface BotConfig {
    strategies: Record<string, unknown>;
    execution: Record<string, unknown>;
    risk: Record<string, unknown>;
    symbols: Record<string, unknown>;
    breakers: Record<string, unknown>;
    daily: Record<string, unknown>;
}

export interface ConfigVersion {
    version: number;
    config_hash: string;
    is_active: boolean;
    created_at: string;
    config_json: BotConfig;
}

export async function getBotConfig() {
    return fetchPrivate<ConfigVersion>("/v1/config");
}

export async function createConfigVersion(config: BotConfig) {
    return fetchPrivate<ConfigVersion>("/v1/config/versions", {
        method: "POST",
        body: JSON.stringify({ config_json: config }),
    });
}

export async function activateConfig(version: number) {
    return fetchPrivate(`/v1/config/activate/${version}`, {
        method: "POST",
    });
}

// --- Exchange Keys ---

export interface ExchangeKey {
    id: string;
    exchange: string;
    label: string | null;
    key_version: number;
    created_at: string;
    revoked_at: string | null;
    is_active: boolean;
}

export async function getKeys() {
    return fetchPrivate<ExchangeKey[]>("/v1/exchanges/binance/keys/status");
}

export async function addKey(label: string, apiKey: string, secretKey: string) {
    return fetchPrivate<ExchangeKey>("/v1/exchanges/binance/keys", {
        method: "POST",
        body: JSON.stringify({ label, api_key: apiKey, secret_key: secretKey }),
    });
}

export async function revokeKey(id: string) {
    return fetchPrivate(`/v1/exchanges/binance/keys/${id}`, {
        method: "DELETE",
    });
}

export async function updateKey(id: string, updates: { label?: string; api_key?: string; secret_key?: string }) {
    return fetchPrivate<ExchangeKey>(`/v1/exchanges/binance/keys/${id}`, {
        method: "PATCH",
        body: JSON.stringify(updates),
    });
}

export async function activateKey(id: string) {
    return fetchPrivate(`/v1/exchanges/binance/keys/${id}/activate`, {
        method: "POST",
    });
}

// --- Users (Owner Only) ---

export type UserRole = "OWNER" | "CEO" | "DEVELOPER" | "ADMIN";

export interface ManagedUser {
    id: string;
    email: string;
    role: UserRole;
    created_at: string;
    disabled?: boolean | null;
    password_reset_link?: string | null;
}

export async function listUsers() {
    return fetchPrivate<ManagedUser[]>("/v1/users");
}

export async function createUser(email: string, role: UserRole, sendResetLink: boolean) {
    return fetchPrivate<ManagedUser>("/v1/users", {
        method: "POST",
        body: JSON.stringify({ email, role, send_reset_link: sendResetLink }),
    });
}

export async function updateUser(
    id: string,
    updates: { role?: UserRole; disabled?: boolean; sendResetLink?: boolean }
) {
    return fetchPrivate<ManagedUser>(`/v1/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
            role: updates.role,
            disabled: updates.disabled,
            send_reset_link: updates.sendResetLink,
        }),
    });
}

// --- Bot Control ---

export interface ArmResponse {
    arming_token: string;
    expires_in_seconds: number;
}

export async function armBot() {
    return fetchPrivate<ArmResponse>("/v1/bot/arm", { method: "POST" });
}

export async function startBot(mode: "dry-run" | "live", armingToken?: string) {
    return fetchPrivate("/v1/bot/start", {
        method: "POST",
        body: JSON.stringify({ mode, arming_token: armingToken }),
    });
}

export async function stopBot() {
    return fetchPrivate("/v1/bot/stop", { method: "POST" });
}

export async function pauseEntries() {
    return fetchPrivate("/v1/bot/pause_entries", { method: "POST" });
}

export async function resumeEntries() {
    return fetchPrivate("/v1/bot/resume_entries", { method: "POST" });
}

// --- Data ---

export async function getPrivateEvents() {
    return fetchPrivate<unknown[]>("/v1/events");
}

// --- Strategy Performance ---

export interface StrategyPerformance {
    name: string;
    enabled: boolean;
    total_trades: number;
    win_rate: number;
    profit_factor: number;
    net_pnl_usd: number;
    avg_trade_usd: number;
    last_signal_at: string | null;
}

export async function getStrategyPerformance() {
    return fetchPrivate<StrategyPerformance[]>("/v1/strategies/performance");
}

// --- Portfolio Risk ---

export interface PortfolioRisk {
    total_exposure_usd: number;
    open_positions: number;
    max_drawdown_pct: number;
    current_drawdown_pct: number;
    daily_pnl_usd: number;
    daily_pnl_pct: number;
    var_95_usd: number;
    risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

export async function getPortfolioRisk() {
    return fetchPrivate<PortfolioRisk>("/v1/risk/portfolio");
}

// --- Kill Switch ---

export interface KillSwitchStatus {
    is_killed: boolean;
    current_event: {
        timestamp: string;
        reason: string;
        triggered_by: string;
        details: string;
        auto_resume_at: string | null;
    } | null;
    history_count: number;
    daily_pnl_pct: number;
    current_drawdown_pct: number;
    consecutive_losses: number;
}

export async function getKillSwitchStatus() {
    return fetchPrivate<KillSwitchStatus>("/v1/risk/kill-switch/status");
}

export async function triggerKillSwitch(reason: string) {
    return fetchPrivate("/v1/risk/kill-switch/trigger", {
        method: "POST",
        body: JSON.stringify({ reason }),
    });
}

export async function resumeTrading() {
    return fetchPrivate("/v1/risk/kill-switch/resume", {
        method: "POST",
    });
}

// --- Grid Portfolio ---

export interface GridCoinSummary {
    symbol: string;
    pair: string;
    allocation_usd: number;
    cash: number;
    grid_center: number;
    num_grids: number;
    lower_pct: number;
    upper_pct: number;
    total_buys: number;
    total_sells: number;
    total_pnl: number;
    total_fees: number;
    net_pnl: number;
    active_orders: number;
    filled_levels: number;
    total_levels: number;
    num_rebalances: number;
    last_updated: string | null;
}

export interface GridPortfolio {
    active: boolean;
    started_at: string | null;
    total_capital_usd: number;
    coins: GridCoinSummary[];
    summary: {
        total_buys: number;
        total_sells: number;
        total_pnl: number;
        total_fees: number;
        net_pnl: number;
    };
}

export interface GridCoinDetail extends GridCoinSummary {
    levels: {
        price: number;
        sell_price: number;
        holding: number;
        order_id: string | null;
        side: string;
    }[];
}

export async function getGridPortfolio() {
    return fetchPrivate<GridPortfolio>("/v1/grid/portfolio");
}

export async function getGridCoinDetail(symbol: string) {
    return fetchPrivate<GridCoinDetail>(`/v1/grid/${symbol.toUpperCase()}`);
}

// --- Public API ---

export interface PublicGridPerformance {
    active: boolean;
    coins_traded: number;
    total_fills: number;
    daily_return_pct: number;
    total_pnl_usd: number;
    strategy: string;
    last_updated: string | null;
}

export async function getPublicGridPerformance(): Promise<PublicGridPerformance> {
    if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
        return {
            active: true,
            coins_traded: 5,
            total_fills: 312,
            daily_return_pct: 1.24,
            total_pnl_usd: 845.20,
            strategy: "Grid v2 (Adaptive Spread)",
            last_updated: new Date().toISOString(),
        };
    }
    const url = `${DASHBOARD_CONFIG.API_URL}/public/v1/grid/performance`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch grid performance");
    return res.json();
}
