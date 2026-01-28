import { useDashboardStore } from "@/lib/store";
import { formatCurrency, formatPct, cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { DollarSign, TrendingUp, Activity, BarChart2 } from "lucide-react";
import { useTranslations } from "next-intl";

export function KPIGrid() {
  const { botState } = useDashboardStore();
  const t = useTranslations("Dashboard");

  const kpis = [
    {
      title: t("equity"),
      value: formatCurrency(botState.equity_usd),
      icon: DollarSign,
      color: "text-blue-500",
      bg: "bg-blue-500/10",
      border: "border-blue-500/20"
    },
    {
      title: t("realizedToday"),
      value: formatCurrency(botState.realized_pnl_today_usd),
      icon: TrendingUp,
      color: botState.realized_pnl_today_usd >= 0 ? "text-emerald-500" : "text-red-500",
      bg: botState.realized_pnl_today_usd >= 0 ? "bg-emerald-500/10" : "bg-red-500/10",
      border: botState.realized_pnl_today_usd >= 0 ? "border-emerald-500/20" : "border-red-500/20"
    },
    {
      title: t("winRate"),
      value: formatPct(botState.win_rate_30d),
      icon: Activity,
      color: "text-purple-500",
      bg: "bg-purple-500/10",
      border: "border-purple-500/20"
    },
    {
      title: t("profitFactor"),
      value: botState.profit_factor_30d.toFixed(2),
      icon: BarChart2,
      color: "text-orange-500",
      bg: "bg-orange-500/10",
      border: "border-orange-500/20"
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {kpis.map((kpi) => (
        <Card key={kpi.title} className={cn("border-l-4 transition-all hover:translate-y-[-2px] hover:shadow-lg", kpi.border)}>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
               <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">{kpi.title}</p>
                  <div className="text-2xl font-bold tracking-tight">{kpi.value}</div>
               </div>
               <div className={cn("p-3 rounded-xl", kpi.bg)}>
                  <kpi.icon className={cn("h-6 w-6", kpi.color)} />
               </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}