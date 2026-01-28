"use client";

import { formatCurrency } from "@/lib/utils";
import { NeoMetricCard } from "@/components/ui/neo-card";
import { DollarSign, TrendingUp, Briefcase, Activity } from "lucide-react";
import { useTranslations } from "next-intl";
import { PublicSummary } from "@/types/public";

interface PublicKPIsProps {
  summary: PublicSummary | null;
}

export function PublicKPIs({ summary }: PublicKPIsProps) {
  const t = useTranslations("Dashboard");

  // Defaults if null
  const equity = summary?.equity_usd ?? 0;
  const realized = summary?.realized_pnl_today_usd ?? 0;
  const openPositions = summary?.open_positions ?? 0;
  const unrealized = summary?.unrealized_pnl_usd ?? 0;

  const kpis = [
    {
      title: t("equity"),
      value: formatCurrency(equity),
      subtitle: "Total portfolio value",
      icon: DollarSign,
      variant: "primary" as const,
      trend: { value: 8.4, label: "all time" },
    },
    {
      title: t("realizedToday"),
      value: formatCurrency(realized),
      subtitle: "Today's trading performance",
      icon: TrendingUp,
      variant: realized >= 0 ? ("success" as const) : ("destructive" as const),
      trend: realized >= 0 
        ? { value: 15.2, label: "vs yesterday" }
        : { value: -2.1, label: "vs yesterday" },
    },
    {
      title: "Open Positions",
      value: openPositions.toString(),
      subtitle: "Active trades",
      icon: Briefcase,
      variant: "purple" as const,
    },
    {
      title: "Unrealized P&L",
      value: formatCurrency(unrealized),
      subtitle: "Pending profit/loss",
      icon: Activity,
      variant: unrealized >= 0 ? ("success" as const) : ("destructive" as const),
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
