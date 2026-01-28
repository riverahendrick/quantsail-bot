"use client";

import { useDashboardStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

// Dummy data generator if no real data
const generateDummyData = () => {
  const data = [];
  let val = 10000;
  for (let i = 0; i < 30; i++) {
    val = val * (1 + (Math.random() * 0.04 - 0.015)); // Random walk
    data.push({
      date: new Date(Date.now() - (30 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      value: val,
    });
  }
  return data;
};

export function EquityChart() {
  const { botState } = useDashboardStore();
  const t = useTranslations("Dashboard");
  
  // Real logic: Should fetch from API. 
  // If API not ready and MOCK is OFF, show nothing or placeholder.
  // If MOCK is ON, show dummy.
  
  let chartData: {date: string; value: number}[] = [];
  
  if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
    const data = generateDummyData();
    chartData = [...data, { date: "Now", value: botState.equity_usd || 10000 }];
  } else if (botState.equity_usd) {
    // If real mode, we might only have current point until historical API exists
    chartData = [{ date: "Now", value: botState.equity_usd }];
  }

  if (chartData.length < 2 && !DASHBOARD_CONFIG.USE_MOCK_DATA) {
     return (
        <Card className="col-span-1 md:col-span-2 lg:col-span-3 border-border bg-card">
          <CardHeader>
            <CardTitle className="text-base font-medium">{t("equityCurve")}</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px] flex items-center justify-center text-muted-foreground">
             {t("waitingForData")}
          </CardContent>
        </Card>
     );
  }

  return (
    <Card className="col-span-1 md:col-span-2 lg:col-span-3 border-border bg-card">
      <CardHeader>
        <CardTitle className="text-base font-medium">{t("equityCurve")}</CardTitle>
      </CardHeader>
      <CardContent className="h-[300px] w-full pl-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
            <XAxis 
              dataKey="date" 
              stroke="#52525b" 
              fontSize={12} 
              tickLine={false} 
              axisLine={false}
              minTickGap={30}
            />
            <YAxis 
              stroke="#52525b" 
              fontSize={12} 
              tickLine={false} 
              axisLine={false}
              tickFormatter={(val) => `$${val}`}
              domain={['auto', 'auto']}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', color: '#fafafa' }}
              itemStyle={{ color: '#3b82f6' }}
              formatter={(val: number | string | Array<number | string>) => [formatCurrency(Number(val)), t("equity")]}
              labelStyle={{ color: '#a1a1aa' }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorEquity)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}