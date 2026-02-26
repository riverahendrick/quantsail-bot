"use client";

import { useDashboardStore } from "@/lib/store";
import { NeoCard } from "@/components/ui/neo-card";
import { useTranslations } from "next-intl";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency } from "@/lib/utils";
import { DASHBOARD_CONFIG } from "@/lib/config";
import { TrendingUp, Activity, Sparkles } from "lucide-react";

// Deterministic profitable equity curve for demo mode
const generateDummyData = () => {
  const data = [];
  let val = 10000;
  // Seeded daily returns that always net positive — realistic but profitable
  const dailyReturns = [
    0.005, 0.012, -0.003, 0.018, 0.008, -0.002, 0.015, 0.006, 0.010, -0.004,
    0.020, 0.003, 0.014, -0.001, 0.009, 0.011, -0.005, 0.022, 0.007, 0.013,
    0.004, 0.016, -0.003, 0.019, 0.008, 0.010, 0.005, 0.012, 0.015, 0.009,
  ];
  for (let i = 0; i < 30; i++) {
    val = val * (1 + dailyReturns[i]);
    data.push({
      date: new Date(Date.now() - (30 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      value: Math.round(val * 100) / 100,
    });
  }
  return data;
};

// Custom Tooltip Component
function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  const t = useTranslations("Dashboard");

  if (active && payload && payload.length) {
    return (
      <div className="rounded-xl px-4 py-3 border border-cyan-500/30 bg-[#0a0a0f]/95 backdrop-blur-xl shadow-[0_0_30px_-5px_rgba(6,182,212,0.3)]">
        <p className="text-xs text-zinc-500 mb-1">{label}</p>
        <p className="text-xl font-bold text-cyan-400 number-display">
          {formatCurrency(payload[0].value)}
        </p>
        <div className="flex items-center gap-1 mt-1">
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <p className="text-xs text-zinc-400">{t("equity")}</p>
        </div>
      </div>
    );
  }
  return null;
}

export function EquityChart() {
  const { botState } = useDashboardStore();
  const t = useTranslations("Dashboard");
  const tCommon = useTranslations("Common");

  let chartData: { date: string; value: number }[] = [];

  if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
    const data = generateDummyData();
    chartData = [...data, { date: "Now", value: data[data.length - 1]?.value || 13200 }];
  } else if (botState.equity_usd) {
    chartData = [{ date: "Now", value: botState.equity_usd }];
  }

  // Calculate stats
  const startValue = chartData[0]?.value || 0;
  const endValue = chartData[chartData.length - 1]?.value || 0;
  const change = endValue - startValue;
  const changePct = startValue > 0 ? (change / startValue) * 100 : 0;
  const isPositive = change >= 0;

  if (chartData.length < 2 && !DASHBOARD_CONFIG.USE_MOCK_DATA) {
    return (
      <NeoCard variant="default">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-lg bg-cyan-500/20">
              <Activity className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{t("equityCurve")}</h3>
              <p className="text-sm text-zinc-500">{t("waitingForData")}</p>
            </div>
          </div>
          <div className="h-[300px] flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
              <div className="relative">
                <div className="w-20 h-20 rounded-full border-2 border-dashed border-cyan-500/30 animate-spin" style={{ animationDuration: '3s' }} />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-cyan-400/50" />
                </div>
              </div>
              <p className="text-sm text-zinc-500">{t("waitingForData")}</p>
            </div>
          </div>
        </div>
      </NeoCard>
    );
  }

  return (
    <NeoCard variant="default" className="overflow-hidden" gradientBorder>
      {/* Header with Stats */}
      <div className="p-6 border-b border-white/5">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/20">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{t("equityCurve")}</h3>
              <p className="text-sm text-zinc-500">{t("equitySubtitle")}</p>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="flex items-center gap-4 sm:gap-6">
            <div className="text-right">
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">{t("current")}</p>
              <p className="text-2xl font-bold text-white number-display">{formatCurrency(endValue)}</p>
            </div>
            <div className="w-px h-12 bg-white/10 hidden sm:block" />
            <div className="text-right">
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">{t("change")}</p>
              <p className={`text-2xl font-bold number-display ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                {isPositive ? tCommon("plus") : ''}{formatCurrency(change)}
              </p>
            </div>
            <div className="w-px h-12 bg-white/10 hidden lg:block" />
            <div className="text-right hidden lg:block">
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">{t("return")}</p>
              <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg ${isPositive ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-rose-500/10 border border-rose-500/20'}`}>
                <span className={`text-lg font-bold number-display ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {isPositive ? tCommon("plus") : ''}{changePct.toFixed(2)}{tCommon("percent")}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="p-6">
        <div className="h-[340px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                {/* Enhanced gradient for the area fill - stronger at top */}
                <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={isPositive ? "#06b6d4" : "#f43f5e"} stopOpacity={0.5} />
                  <stop offset="30%" stopColor={isPositive ? "#3b82f6" : "#fb7185"} stopOpacity={0.3} />
                  <stop offset="70%" stopColor={isPositive ? "#3b82f6" : "#fb7185"} stopOpacity={0.1} />
                  <stop offset="100%" stopColor={isPositive ? "#3b82f6" : "#fb7185"} stopOpacity={0} />
                </linearGradient>

                {/* Neon line gradient */}
                <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor={isPositive ? "#22d3ee" : "#fb7185"} />
                  <stop offset="50%" stopColor={isPositive ? "#06b6d4" : "#f43f5e"} />
                  <stop offset="100%" stopColor={isPositive ? "#3b82f6" : "#e11d48"} />
                </linearGradient>

                {/* Glow gradient under the line */}
                <linearGradient id="glowGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={isPositive ? "#06b6d4" : "#f43f5e"} stopOpacity={0.6} />
                  <stop offset="100%" stopColor={isPositive ? "#06b6d4" : "#f43f5e"} stopOpacity={0} />
                </linearGradient>

                {/* Enhanced glow filter */}
                <filter id="lineGlow" x="-100%" y="-100%" width="300%" height="300%">
                  <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                  <feGaussianBlur stdDeviation="8" result="coloredBlurHeavy" />
                  <feMerge>
                    <feMergeNode in="coloredBlurHeavy" />
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>

                {/* Area glow filter */}
                <filter id="areaGlow" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="6" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.03)"
                vertical={false}
              />

              <XAxis
                dataKey="date"
                stroke="rgba(255,255,255,0.1)"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                minTickGap={30}
                tick={{ fill: '#52525b' }}
              />

              <YAxis
                stroke="rgba(255,255,255,0.1)"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `$${(val / 1000).toFixed(1)}k`}
                domain={['auto', 'auto']}
                tick={{ fill: '#52525b' }}
              />

              <Tooltip
                content={<CustomTooltip />}
                cursor={{ stroke: 'rgba(6,182,212,0.3)', strokeWidth: 1, strokeDasharray: '4 4' }}
              />

              {/* Background glow area */}
              <Area
                type="monotone"
                dataKey="value"
                stroke="none"
                fill="url(#glowGradient)"
                fillOpacity={0.3}
              />

              {/* Main area */}
              <Area
                type="monotone"
                dataKey="value"
                stroke="url(#lineGradient)"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorEquity)"
                animationDuration={1500}
                animationEasing="ease-out"
                filter="url(#lineGlow)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bottom Glow Line */}
      <div className="h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />
    </NeoCard>
  );
}
