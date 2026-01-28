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
import { Sparkles, Shield, Bot } from "lucide-react";

export function DashboardView() {
  useDashboardWs();
  const t = useTranslations("Dashboard");

  return (
    <div className="flex flex-col gap-8 max-w-[1600px] mx-auto pb-8">
      {/* Header Section */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between animate-fade-in-up">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white">
              {t("overviewTitle")}
            </h1>
            <Sparkles className="w-5 h-5 text-cyan-400" />
          </div>
          <p className="text-zinc-400">{t("overviewSubtitle")}</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl bg-white/[0.03] border border-white/10">
            <Shield className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-zinc-400">{t("securedConnection")}</span>
          </div>
          <ArmingModal />
        </div>
      </div>

      {/* Status Banner */}
      <div className="animate-fade-in-up" style={{ animationDelay: "0.1s", opacity: 0 }}>
        <StatusBanner />
      </div>

      {/* KPI Grid */}
      <div className="animate-fade-in-up" style={{ animationDelay: "0.2s", opacity: 0 }}>
        <KPIGrid />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Charts & Trades */}
        <div className="lg:col-span-3 space-y-6">
          <div className="animate-fade-in-up" style={{ animationDelay: "0.3s", opacity: 0 }}>
            <EquityChart />
          </div>
          
          <div className="animate-fade-in-up" style={{ animationDelay: "0.4s", opacity: 0 }}>
            <RecentTrades />
          </div>
        </div>

        {/* Right Column: Widgets */}
        <div className="lg:col-span-1 space-y-6">
          <div className="animate-fade-in-up" style={{ animationDelay: "0.35s", opacity: 0 }}>
            <DailyLockWidget />
          </div>
          
          <div className="animate-fade-in-up" style={{ animationDelay: "0.45s", opacity: 0 }}>
            <BreakersWidget />
          </div>
        </div>
      </div>
    </div>
  );
}
