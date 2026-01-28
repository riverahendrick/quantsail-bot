"use client";

import { useEffect, useState } from "react";
import { PublicSummary } from "@/types/public";
import { PublicKPIs } from "@/components/public/public-kpis";
import { EquityChart } from "@/components/dashboard/equity-chart"; 
import { useTranslations } from "next-intl";
import { DASHBOARD_CONFIG } from "@/lib/config";

export default function PublicOverviewPage() {
  const [summary, setSummary] = useState<PublicSummary | null>(null);
  const t = useTranslations("PublicOverview");

  useEffect(() => {
    // Fetch summary
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
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
         <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
         <p className="text-muted-foreground">{t("subtitle")}</p>
      </div>

      <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-emerald-500">
         <span className="font-bold">{t("statusLine")}</span>
      </div>

      <PublicKPIs summary={summary} />
      
      <div className="mt-4">
        <EquityChart /> 
      </div>
    </div>
  );
}
