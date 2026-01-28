"use client";

import { useDashboardStore } from "@/lib/store";
import { formatCurrency, formatPct } from "@/lib/utils";
import { NeoMetricCard } from "@/components/ui/neo-card";
import { useTranslations } from "next-intl";
import { TrendingUp, Target, BarChart2, Wallet } from "lucide-react";

export function KPIGrid() {
  const { botState } = useDashboardStore();
  const t = useTranslations("Dashboard");

  const kpis = [
    {
      title: t("equity"),
      value: formatCurrency(botState.equity_usd),
      subtitle: "Total portfolio value",
      icon: Wallet,
      variant: "primary" as const,
      trend: { value: 5.2, label: "vs last week" },
    },
    {
      title: t("realizedToday"),
      value: formatCurrency(botState.realized_pnl_today_usd),
      subtitle: "Today's realized P&L",
      icon: TrendingUp,
      variant: botState.realized_pnl_today_usd >= 0 ? ("success" as const) : ("destructive" as const),
      trend: botState.realized_pnl_today_usd >= 0 
        ? { value: 12.5, label: "above avg" }
        : { value: -3.2, label: "below avg" },
    },
    {
      title: t("winRate"),
      value: formatPct(botState.win_rate_30d),
      subtitle: "Last 30 days",
      icon: Target,
      variant: "purple" as const,
      trend: { value: 2.1, label: "vs last month" },
    },
    {
      title: t("profitFactor"),
      value: botState.profit_factor_30d.toFixed(2),
      subtitle: "Gross profit / Gross loss",
      icon: BarChart2,
      variant: "warning" as const,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {kpis.map((kpi, index) => (
        <div
          key={kpi.title}
          className="animate-fade-in-up"
          style={{ animationDelay: `${index * 0.1}s`, opacity: 0 }}
        >
          <NeoMetricCard
            title={kpi.title}
            value={kpi.value}
            subtitle={kpi.subtitle}
            icon={kpi.icon}
            variant={kpi.variant}
            trend={kpi.trend}
          />
        </div>
      ))}
    </div>
  );
}
