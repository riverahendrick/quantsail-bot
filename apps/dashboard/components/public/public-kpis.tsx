import { formatCurrency } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { DollarSign, TrendingUp, Briefcase } from "lucide-react";
import { useTranslations } from "next-intl";
import { PublicSummary } from "@/types/public";
import { cn } from "@/lib/utils";

interface PublicKPIsProps {
  summary: PublicSummary | null;
}

export function PublicKPIs({ summary }: PublicKPIsProps) {
  const t = useTranslations("Dashboard");

  // Defaults if null
  const equity = summary?.equity_usd ?? 0;
  const realized = summary?.realized_pnl_today_usd ?? 0;
  const openPositions = summary?.open_positions ?? 0;

  const kpis = [
    {
      title: t("equity"),
      value: formatCurrency(equity),
      icon: DollarSign,
      color: "text-blue-500",
      bg: "bg-blue-500/10",
      border: "border-blue-500/20"
    },
    {
      title: t("realizedToday"),
      value: formatCurrency(realized),
      icon: TrendingUp,
      color: realized >= 0 ? "text-emerald-500" : "text-red-500",
      bg: realized >= 0 ? "bg-emerald-500/10" : "bg-red-500/10",
      border: realized >= 0 ? "border-emerald-500/20" : "border-red-500/20"
    },
    {
      title: "Open Positions", // Placeholder
      value: openPositions.toString(),
      icon: Briefcase,
      color: "text-purple-500",
      bg: "bg-purple-500/10",
      border: "border-purple-500/20"
    }
  ];

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {kpis.map((kpi) => (
        <Card key={kpi.title} className={cn("border-l-4 transition-all", kpi.border)}>
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
