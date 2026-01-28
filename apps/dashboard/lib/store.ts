import { create } from "zustand";
import { DashboardStore } from "@/types/dashboard";

export const useDashboardStore = create<DashboardStore>((set) => ({
  botState: {
    status: "unknown",
    equity_usd: 0,
    realized_pnl_today_usd: 0,
    win_rate_30d: 0,
    profit_factor_30d: 0,
    daily_lock: {
      target_usd: 0,
      mode: "STOP",
      realized_pnl: 0,
      peak_pnl: 0,
      floor_usd: 0,
      entries_paused: false,
    },
    active_breakers: [],
  },
  recentTrades: [],
  recentEvents: [],
  isConnected: false,
  lastHeartbeat: null,

  setBotState: (state) =>
    set((s) => ({ botState: { ...s.botState, ...state } })),

  addTrade: (trade) =>
    set((s) => {
      // Upsert based on ID
      const exists = s.recentTrades.findIndex((t) => t.id === trade.id);
      let newTrades = [...s.recentTrades];
      if (exists >= 0) {
        newTrades[exists] = trade;
      } else {
        newTrades = [trade, ...newTrades];
      }
      // Sort by open date desc and limit to 50
      return {
        recentTrades: newTrades
          .sort(
            (a, b) =>
              new Date(b.opened_at).getTime() - new Date(a.opened_at).getTime()
          )
          .slice(0, 50),
      };
    }),

  addEvent: (event) =>
    set((s) => ({
      recentEvents: [event, ...s.recentEvents].slice(0, 50),
    })),

  setConnected: (connected) => set({ isConnected: connected }),
  updateHeartbeat: () => set({ lastHeartbeat: new Date().toISOString() }),
}));
