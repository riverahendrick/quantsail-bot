"use client";

import { useDashboardWs } from "@/lib/hooks/use-dashboard-ws";
import { StatusBanner } from "./status-banner";
import { KPIGrid } from "./kpi-grid";
import { DailyLockWidget } from "./daily-lock-widget";
import { BreakersWidget } from "./breakers-widget";
import { RecentTrades } from "./recent-trades";
import { EquityChart } from "./equity-chart";
import { ArmingModal } from "./arming-modal";
import { useTranslations } from "next-intl";

export function DashboardView() {
  useDashboardWs();
  const t = useTranslations("Dashboard");

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">{t("overviewTitle")}</h1>
          <p className="text-muted-foreground">{t("overviewSubtitle")}</p>
        </div>
        <div>
          <ArmingModal />
        </div>
      </div>
      
      <StatusBanner />
      
      <KPIGrid />
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Left Column: Charts & Status */}
        <div className="md:col-span-3 space-y-6">
           <EquityChart />
           <RecentTrades />
        </div>

        {/* Right Column: Widgets */}
        <div className="md:col-span-1 space-y-6">
           <DailyLockWidget />
           <BreakersWidget />
        </div>
      </div>
    </div>
  );
}