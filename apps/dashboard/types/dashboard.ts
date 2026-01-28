export type BotStatus = "running" | "paused" | "stopped" | "unknown";

export interface BotState {
  status: BotStatus;
  status_reason?: string;
  status_until?: string; // ISO date
  equity_usd: number;
  realized_pnl_today_usd: number;
  win_rate_30d: number; // 0-1
  profit_factor_30d: number;
  daily_lock: {
    target_usd: number;
    mode: "STOP" | "OVERDRIVE";
    realized_pnl: number;
    peak_pnl: number;
    floor_usd: number;
    entries_paused: boolean;
  };
  active_breakers: Array<{
    type: string;
    level: "WARN" | "ERROR";
    expiry?: string;
    reason?: string;
  }>;
}

export interface Trade {
  id: string;
  symbol: string;
  side: "LONG" | "SHORT";
  status: "OPEN" | "CLOSED" | "CANCELED";
  mode: "DRY_RUN" | "LIVE";
  entry_price: number;
  exit_price?: number;
  pnl_usd?: number;
  pnl_pct?: number;
  opened_at: string;
  closed_at?: string;
}

export interface BotEvent {
  seq: number;
  type: string;
  level: "INFO" | "WARN" | "ERROR";
  payload: Record<string, unknown>;
  timestamp: string;
}

export interface DashboardStore {
  botState: BotState;
  recentTrades: Trade[];
  recentEvents: BotEvent[];
  isConnected: boolean;
  lastHeartbeat: string | null;
  
  setBotState: (state: Partial<BotState>) => void;
  addTrade: (trade: Trade) => void;
  addEvent: (event: BotEvent) => void;
  setConnected: (connected: boolean) => void;
  updateHeartbeat: () => void;
}
