"use client";

import { useEffect, useState } from "react";
import { PublicSummary } from "@/types/public";
import { PublicKPIs } from "@/components/public/public-kpis";
import { EquityChart } from "@/components/dashboard/equity-chart";
import { useTranslations } from "next-intl";
import { DASHBOARD_CONFIG } from "@/lib/config";
import { NeoCard, NeoStatusCard } from "@/components/ui/neo-card";
import { 
  Activity, 
  Globe, 
  Shield, 
  Zap, 
  TrendingUp,
  Clock,
  Lock,
  ArrowRight,
  Sparkles
} from "lucide-react";
import Link from "next/link";

export default function PublicOverviewPage() {
  const [summary, setSummary] = useState<PublicSummary | null>(null);
  const t = useTranslations("PublicOverview");

  useEffect(() => {
    const fetchSummary = async () => {
       try {
         const res = await fetch(`${DASHBOARD_CONFIG.API_URL}/public/v1/summary`);
         if (res.ok) {
            const data = await res.json();
            setSummary(data);
         } else if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
            throw new Error("Mock fallback");
         }
       } catch (e) {
         if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
             setSummary({
                ts: new Date().toISOString(),
                equity_usd: 10250.50,
                cash_usd: 5000,
                unrealized_pnl_usd: 150.20,
                realized_pnl_today_usd: 45.30,
                open_positions: 1
             });
         } else {
             console.error("Failed to fetch public summary", e);
         }
       }
    };
    
    fetchSummary();
  }, []);

  return (
    <div className="flex flex-col gap-8">
      {/* Hero Section */}
      <div className="animate-fade-in-up">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white">
                {t("title")}
              </h1>
            </div>
            <p className="text-lg text-zinc-400 max-w-2xl leading-relaxed">
              {t("subtitle")}
            </p>
          </div>
          
          {/* Trust Badges */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-400"></span>
              </span>
              <span className="text-sm font-medium text-emerald-400">{t("liveTrading")}</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10">
              <Globe className="w-4 h-4 text-cyan-400" />
              <span className="text-sm text-zinc-400">{t("publicData")}</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10">
              <Shield className="w-4 h-4 text-violet-400" />
              <span className="text-sm text-zinc-400">{t("verified")}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Status Section */}
      <div className="grid md:grid-cols-3 gap-4 animate-fade-in-up" style={{ animationDelay: "0.1s", opacity: 0 }}>
        <NeoStatusCard 
          title={t("botStatus")} 
          status="online" 
          message={t("automatedTrading")}
        />
        <NeoCard variant="primary" className="p-5">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-cyan-500/20">
              <Clock className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <p className="text-sm text-zinc-400">{t("lastUpdate")}</p>
              <p className="text-lg font-semibold text-white">
                {summary && summary.ts ? new Date(summary.ts).toLocaleTimeString() : "--:--"}
              </p>
            </div>
          </div>
        </NeoCard>
        <NeoCard variant="purple" className="p-5">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-violet-500/20">
              <TrendingUp className="w-6 h-6 text-violet-400" />
            </div>
            <div>
              <p className="text-sm text-zinc-400">{t("tradesToday")}</p>
              <p className="text-lg font-semibold text-white">{summary?.open_positions || 0}</p>
            </div>
          </div>
        </NeoCard>
      </div>

      {/* KPIs */}
      <div className="animate-fade-in-up" style={{ animationDelay: "0.2s", opacity: 0 }}>
        <PublicKPIs summary={summary} />
      </div>
      
      {/* Chart Section */}
      <div className="animate-fade-in-up" style={{ animationDelay: "0.3s", opacity: 0 }}>
        <EquityChart />
      </div>

      {/* Info Cards Grid */}
      <div className="grid md:grid-cols-2 gap-6 animate-fade-in-up" style={{ animationDelay: "0.4s", opacity: 0 }}>
        {/* Transparency Card */}
        <NeoCard variant="default" interactive>
          <div className="p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-xl bg-blue-500/20">
                <Shield className="w-6 h-6 text-blue-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-white mb-2">{t("transparencyTitle")}</h3>
                <p className="text-sm text-zinc-400 leading-relaxed mb-4">
                  {t("transparencyDescription")}
                </p>
                <div className="flex flex-wrap gap-2 mb-4">
                  <span className="px-3 py-1 rounded-full text-xs bg-white/5 text-zinc-400 border border-white/10">
                    {t("noApiKeys")}
                  </span>
                  <span className="px-3 py-1 rounded-full text-xs bg-white/5 text-zinc-400 border border-white/10">
                    {t("sanitizedData")}
                  </span>
                  <span className="px-3 py-1 rounded-full text-xs bg-white/5 text-zinc-400 border border-white/10">
                    {t("realTimeUpdates")}
                  </span>
                </div>
                <Link 
                  href="/public/transparency"
                  className="inline-flex items-center gap-2 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                >
                  {t("learnMore")}
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </div>
        </NeoCard>

        {/* Security Card */}
        <NeoCard variant="success" interactive>
          <div className="p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-xl bg-emerald-500/20">
                <Lock className="w-6 h-6 text-emerald-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-white mb-2">{t("securityTitle")}</h3>
                <p className="text-sm text-zinc-400 leading-relaxed mb-4">
                  {t("securityDescription")}
                </p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <Zap className="w-4 h-4 text-amber-400" />
                    <span>{t("circuitBreakersActive")}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <Activity className="w-4 h-4 text-emerald-400" />
                    <span>{t("dailyLimitsEnabled")}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </NeoCard>
      </div>

      {/* CTA Section */}
      <div className="text-center animate-fade-in-up" style={{ animationDelay: "0.5s", opacity: 0 }}>
        <NeoCard variant="glow" className="inline-block">
          <div className="px-8 py-6">
            <p className="text-zinc-400 mb-4">{t("ctaText")}</p>
            <Link 
              href="/public/trades"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-medium hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
            >
              {t("viewTrades")}
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </NeoCard>
      </div>
    </div>
  );
}
