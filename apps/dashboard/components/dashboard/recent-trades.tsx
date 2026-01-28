"use client";

import { useDashboardStore } from "@/lib/store";
import { formatCurrency, formatPct, cn } from "@/lib/utils";
import { NeoCard } from "@/components/ui/neo-card";
import { useTranslations } from "next-intl";
import { ArrowUpRight, ArrowDownRight, Clock, History } from "lucide-react";

export function RecentTrades() {
  const { recentTrades } = useDashboardStore();
  const t = useTranslations("Dashboard");

  return (
    <NeoCard variant="default" className="h-full">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-violet-500/20">
              <History className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{t("recentTrades")}</h3>
              <p className="text-sm text-zinc-500">{t("last24hActivity")}</p>
            </div>
          </div>
          <span className="text-xs text-zinc-500 bg-white/5 px-3 py-1 rounded-full border border-white/5">
            {recentTrades.length} {t("trades")}
          </span>
        </div>

        {/* Trades List */}
        {recentTrades.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
              <Clock className="w-8 h-8 text-zinc-600" />
            </div>
            <p className="text-zinc-500">{t("noTradesYet")}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {recentTrades.map((trade, index) => (
              <div
                key={trade.id}
                className={cn(
                  "group flex items-center justify-between p-4 rounded-xl",
                  "bg-white/[0.02] hover:bg-white/[0.05]",
                  "border border-white/5 hover:border-white/10",
                  "transition-all duration-200"
                )}
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <div className="flex items-center gap-4">
                  {/* Side Indicator */}
                  <div
                    className={cn(
                      "w-10 h-10 rounded-xl flex items-center justify-center",
                      trade.side === "LONG"
                        ? "bg-emerald-500/20 text-emerald-400"
                        : "bg-rose-500/20 text-rose-400"
                    )}
                  >
                    {trade.side === "LONG" ? (
                      <ArrowUpRight className="w-5 h-5" />
                    ) : (
                      <ArrowDownRight className="w-5 h-5" />
                    )}
                  </div>

                  {/* Trade Info */}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white">{trade.symbol}</span>
                      <span
                        className={cn(
                          "text-xs px-2 py-0.5 rounded-full font-medium",
                          trade.side === "LONG"
                            ? "bg-emerald-500/20 text-emerald-400"
                            : "bg-rose-500/20 text-rose-400"
                        )}
                      >
                        {trade.side}
                      </span>
                      {trade.status === "OPEN" && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/20">
                          {t("open")}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-zinc-500">
                      {new Date(trade.opened_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* P&L */}
                <div className="text-right">
                  {trade.status === "CLOSED" ? (
                    <>
                      <div
                        className={cn(
                          "font-semibold number-display",
                          (trade.pnl_usd || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                        )}
                      >
                        {(trade.pnl_usd || 0) >= 0 ? "+" : ""}
                        {formatCurrency(trade.pnl_usd || 0)}
                      </div>
                      <span
                        className={cn(
                          "text-xs",
                          (trade.pnl_pct || 0) >= 0 ? "text-emerald-500/70" : "text-rose-500/70"
                        )}
                      >
                        {formatPct(trade.pnl_pct || 0)}
                      </span>
                    </>
                  ) : (
                    <span className="text-sm font-medium text-cyan-400 animate-pulse">
                      {t("open")}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </NeoCard>
  );
}
