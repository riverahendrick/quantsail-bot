"use client";

import { useEffect, useState } from "react";
import { PublicTrade } from "@/types/public";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, formatCurrency } from "@/lib/utils";
import { useTranslations } from "next-intl";
import { DASHBOARD_CONFIG } from "@/lib/config";

export default function PublicTradesPage() {
  const [trades, setTrades] = useState<PublicTrade[]>([]);
  const t = useTranslations("PublicTrades");

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
                opened_at: new Date().toISOString(),
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
              }
            ]);
        } else {
            console.error(e);
        }
      }
    };
    fetchTrades();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div>
         <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
         <p className="text-muted-foreground">{t("subtitle")}</p>
      </div>

      <Card className="border-border bg-card">
        <CardHeader>
          <CardTitle className="text-base font-medium">{t("recentActivity")}</CardTitle>
        </CardHeader>
        <CardContent>
          {trades.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">{t("noTrades")}</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="pb-3 font-medium text-muted-foreground">{t("symbol")}</th>
                    <th className="pb-3 font-medium text-muted-foreground">{t("side")}</th>
                    <th className="pb-3 font-medium text-muted-foreground">{t("status")}</th>
                    <th className="pb-3 font-medium text-muted-foreground text-right">{t("entry")}</th>
                    <th className="pb-3 font-medium text-muted-foreground text-right">{t("exit")}</th>
                    <th className="pb-3 font-medium text-muted-foreground text-right">{t("pnl")}</th>
                    <th className="pb-3 font-medium text-muted-foreground text-right">{t("time")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {trades.map((trade, i) => (
                    <tr key={i} className="group hover:bg-muted/50">
                      <td className="py-3 font-medium">{trade.symbol}</td>
                      <td className="py-3">
                         <span className={cn(
                           "px-2 py-0.5 rounded-full text-xs font-bold",
                           trade.side === "LONG" ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"
                         )}>
                           {trade.side}
                         </span>
                      </td>
                      <td className="py-3">{trade.status}</td>
                      <td className="py-3 text-right">{formatCurrency(trade.entry_price)}</td>
                      <td className="py-3 text-right">
                        {trade.exit_price ? formatCurrency(trade.exit_price) : "-"}
                      </td>
                      <td className="py-3 text-right">
                        {trade.realized_pnl_usd !== null ? (
                          <span className={cn(
                             "font-bold",
                             trade.realized_pnl_usd >= 0 ? "text-emerald-500" : "text-red-500"
                          )}>
                             {formatCurrency(trade.realized_pnl_usd)}
                          </span>
                        ) : "-"}
                      </td>
                      <td className="py-3 text-right text-muted-foreground">
                        {new Date(trade.closed_at || trade.opened_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}