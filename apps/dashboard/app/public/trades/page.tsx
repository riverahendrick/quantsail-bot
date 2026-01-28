"use client";

import { useEffect, useState } from "react";
import { PublicTrade } from "@/types/public";
import { NeoCard } from "@/components/ui/neo-card";
import { cn, formatCurrency } from "@/lib/utils";
import { useTranslations } from "next-intl";
import { DASHBOARD_CONFIG } from "@/lib/config";
import { ArrowUpRight, ArrowDownRight, Clock, History, TrendingUp, Filter } from "lucide-react";

export default function PublicTradesPage() {
  const [trades, setTrades] = useState<PublicTrade[]>([]);
  const [filter, setFilter] = useState<"all" | "open" | "closed">("all");
  const t = useTranslations("PublicTrades");
  const tCommon = useTranslations("Common");

  useEffect(() => {
    const fetchTrades = async () => {
      try {
        const res = await fetch(`${DASHBOARD_CONFIG.API_URL}/public/v1/trades?limit=50`);
        if (res.ok) {
           const data = await res.json();
           setTrades(data);
        } else if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
           throw new Error("Mock fallback");
        }
      } catch (e) {
        if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
            setTrades([
              {
                symbol: "BTC/USDT",
                side: "LONG",
                status: "CLOSED",
                mode: "DRY_RUN",
                opened_at: new Date(Date.now() - 86400000).toISOString(),
                closed_at: new Date().toISOString(),
                entry_price: 65000,
                exit_price: 66000,
                realized_pnl_usd: 150.00
              },
              {
                 symbol: "ETH/USDT",
                 side: "SHORT",
                 status: "OPEN",
                 mode: "DRY_RUN",
                 opened_at: new Date(Date.now() - 3600000).toISOString(),
                 closed_at: null,
                 entry_price: 3200,
                 exit_price: null,
                 realized_pnl_usd: null
              },
              {
                symbol: "SOL/USDT",
                side: "LONG",
                status: "CLOSED",
                mode: "DRY_RUN",
                opened_at: new Date(Date.now() - 172800000).toISOString(),
                closed_at: new Date(Date.now() - 86400000).toISOString(),
                entry_price: 145,
                exit_price: 142,
                realized_pnl_usd: -20.50
              }
            ]);
        } else {
            console.error(e);
        }
      }
    };
    fetchTrades();
  }, []);

  const filteredTrades = trades.filter(trade => {
    if (filter === "open") return trade.status === "OPEN";
    if (filter === "closed") return trade.status === "CLOSED";
    return true;
  });

  const stats = {
    total: trades.length,
    open: trades.filter(t => t.status === "OPEN").length,
    closed: trades.filter(t => t.status === "CLOSED").length,
    profit: trades.filter(t => (t.realized_pnl_usd || 0) > 0).length,
  };

  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div className="animate-fade-in-up">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-lg bg-cyan-500/20">
                <History className="w-5 h-5 text-cyan-400" />
              </div>
              <h1 className="text-4xl font-bold tracking-tight text-white">
                {t("title")}
              </h1>
            </div>
            <p className="text-lg text-zinc-400 max-w-2xl">{t("subtitle")}</p>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-fade-in-up" style={{ animationDelay: "0.1s", opacity: 0 }}>
        <NeoCard variant="default" className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-white/10">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wider">{t("totalTrades")}</p>
              <p className="text-2xl font-bold text-white">{stats.total}</p>
            </div>
          </div>
        </NeoCard>
        <NeoCard variant="primary" className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/20">
              <Clock className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wider">{t("openPositions")}</p>
              <p className="text-2xl font-bold text-white">{stats.open}</p>
            </div>
          </div>
        </NeoCard>
        <NeoCard variant="success" className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/20">
              <ArrowUpRight className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wider">{t("winning")}</p>
              <p className="text-2xl font-bold text-white">{stats.profit}</p>
            </div>
          </div>
        </NeoCard>
        <NeoCard variant="purple" className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-violet-500/20">
              <Filter className="w-4 h-4 text-violet-400" />
            </div>
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wider">{t("closed")}</p>
              <p className="text-2xl font-bold text-white">{stats.closed}</p>
            </div>
          </div>
        </NeoCard>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 animate-fade-in-up" style={{ animationDelay: "0.2s", opacity: 0 }}>
        {(["all", "open", "closed"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={cn(
              "px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200",
              filter === f
                ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                : "bg-white/5 text-zinc-400 border border-white/5 hover:bg-white/10 hover:text-white"
            )}
          >
            {t(f)}
          </button>
        ))}
      </div>

      {/* Trades Table */}
      <NeoCard variant="default" className="animate-fade-in-up overflow-hidden" style={{ animationDelay: "0.3s", opacity: 0 }}>
        <div className="p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-violet-500/20">
              <History className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{t("recentActivity")}</h3>
              <p className="text-sm text-zinc-500">{filteredTrades.length} {t("tradesShown")}</p>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          {filteredTrades.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mb-4">
                <History className="w-10 h-10 text-zinc-600" />
              </div>
              <p className="text-zinc-500 text-lg">{t("noTrades")}</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="text-left py-4 px-6 text-xs font-medium text-zinc-500 uppercase tracking-wider">{t("symbol")}</th>
                  <th className="text-left py-4 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">{t("side")}</th>
                  <th className="text-left py-4 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">{t("status")}</th>
                  <th className="text-right py-4 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">{t("entry")}</th>
                  <th className="text-right py-4 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">{t("exit")}</th>
                  <th className="text-right py-4 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">{t("pnl")}</th>
                  <th className="text-right py-4 px-6 text-xs font-medium text-zinc-500 uppercase tracking-wider">{t("time")}</th>
                </tr>
              </thead>
              <tbody>
                {filteredTrades.map((trade, i) => (
                  <tr 
                    key={i} 
                    className="group border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors"
                    style={{ animationDelay: `${i * 0.05}s` }}
                  >
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "w-10 h-10 rounded-xl flex items-center justify-center",
                          trade.side === "LONG" ? "bg-emerald-500/10" : "bg-rose-500/10"
                        )}>
                          {trade.side === "LONG" ? (
                            <ArrowUpRight className="w-5 h-5 text-emerald-400" />
                          ) : (
                            <ArrowDownRight className="w-5 h-5 text-rose-400" />
                          )}
                        </div>
                        <span className="font-semibold text-white">{trade.symbol}</span>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <span className={cn(
                        "px-3 py-1 rounded-full text-xs font-bold border",
                        trade.side === "LONG" 
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                          : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                      )}>
                        {trade.side}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <span className={cn(
                        "px-3 py-1 rounded-full text-xs font-bold border",
                        trade.status === "OPEN"
                          ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
                          : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
                      )}>
                        {trade.status}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-right font-mono text-zinc-300">
                      {formatCurrency(trade.entry_price)}
                    </td>
                    <td className="py-4 px-4 text-right font-mono text-zinc-300">
                      {trade.exit_price ? formatCurrency(trade.exit_price) : "-"}
                    </td>
                    <td className="py-4 px-4 text-right">
                      {trade.realized_pnl_usd !== null ? (
                        <span className={cn(
                          "font-bold font-mono",
                          trade.realized_pnl_usd >= 0 ? "text-emerald-400" : "text-rose-400"
                        )}>
                          {trade.realized_pnl_usd >= 0 ? "+" : ""}
                          {formatCurrency(trade.realized_pnl_usd)}
                        </span>
                      ) : (
                        <span className="text-zinc-500">{tCommon("minus")}</span>
                      )}
                    </td>
                    <td className="py-4 px-6 text-right text-sm text-zinc-500">
                      {new Date(trade.closed_at || trade.opened_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </NeoCard>
    </div>
  );
}
