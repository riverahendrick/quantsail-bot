export interface PublicSummary {
  ts: string | null;
  equity_usd: number | null;
  cash_usd: number | null;
  unrealized_pnl_usd: number | null;
  realized_pnl_today_usd: number | null;
  open_positions: number | null;
}

export interface PublicTrade {
  symbol: string;
  side: "LONG" | "SHORT";
  status: "OPEN" | "CLOSED" | "CANCELED";
  mode: "DRY_RUN" | "LIVE";
  opened_at: string;
  closed_at: string | null;
  entry_price: number;
  exit_price: number | null;
  realized_pnl_usd: number | null;
}

export interface PublicEvent {
  ts: string;
  level: "INFO" | "WARN" | "ERROR";
  type: string;
  symbol: string | null;
  payload: Record<string, unknown>;
}
