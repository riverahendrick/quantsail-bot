import { useDashboardStore } from "@/lib/store";
import { formatCurrency, formatPct, cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslations } from "next-intl";

export function RecentTrades() {
  const { recentTrades } = useDashboardStore();
  const t = useTranslations("Dashboard");

  return (
    <Card className="col-span-1 md:col-span-4">
      <CardHeader>
        <CardTitle className="text-base font-medium">{t("recentTrades")}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {recentTrades.length === 0 ? (
             <div className="text-center text-sm text-muted-foreground py-4">{t("noTradesYet")}</div>
          ) : (
            recentTrades.map((trade) => (
              <div key={trade.id} className="flex items-center justify-between border-b pb-4 last:border-0 last:pb-0">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold">{trade.symbol}</span>
                    <span className={cn(
                      "text-xs px-2 py-0.5 rounded-full font-medium",
                      trade.side === "LONG" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                    )}>
                      {trade.side}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(trade.opened_at).toLocaleString()}
                  </span>
                </div>
                
                <div className="flex flex-col items-end gap-1">
                  {trade.status === "CLOSED" ? (
                    <>
                      <span className={cn(
                        "font-medium",
                        (trade.pnl_usd || 0) >= 0 ? "text-green-600" : "text-red-600"
                      )}>
                        {formatCurrency(trade.pnl_usd || 0)}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatPct(trade.pnl_pct || 0)}
                      </span>
                    </>
                  ) : (
                    <span className="text-sm font-medium text-blue-600">{t("open")}</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
