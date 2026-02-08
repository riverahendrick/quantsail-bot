"use client";

import { useEffect, useState } from "react";
import { getStrategyPerformance } from "@/lib/api";
import { GlowCard } from "@/components/ui/glow-card";
import { RefreshCw, TrendingUp, TrendingDown, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTranslations } from "next-intl";
import { formatCurrency, formatPct } from "@/lib/utils";

type StrategyMetrics = {
    name: string;
    enabled: boolean;
    total_trades: number;
    win_rate: number;
    profit_factor: number;
    net_pnl_usd: number;
    avg_trade_usd: number;
    last_signal_at: string | null;
};

export function StrategyPerformanceWidget() {
    const t = useTranslations("StrategyPerformance");
    const [strategies, setStrategies] = useState<StrategyMetrics[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getStrategyPerformance();
            setStrategies(data as StrategyMetrics[]);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : t("loadError");
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <GlowCard variant="default">
            <div className="p-6 border-b border-white/5 flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Activity className="h-5 w-5 text-cyan-400" />
                        {t("title")}
                    </h3>
                    <p className="text-sm text-zinc-400 mt-1">{t("description")}</p>
                </div>
                <Button variant="outline" size="icon" onClick={fetchData} disabled={loading}>
                    <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                </Button>
            </div>
            <div className="p-6">
                {error && (
                    <div className="p-4 mb-4 text-red-500 border border-red-200 rounded text-sm">
                        {error}
                    </div>
                )}

                {strategies.length === 0 && !loading ? (
                    <div className="text-center text-muted-foreground py-8">
                        {t("noStrategies")}
                    </div>
                ) : (
                    <div className="space-y-4">
                        {strategies.map((strategy) => (
                            <div
                                key={strategy.name}
                                className={`p-4 rounded-lg border transition-all ${strategy.enabled
                                    ? "bg-white/5 border-white/10"
                                    : "bg-zinc-900/50 border-zinc-800 opacity-60"
                                    }`}
                            >
                                <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center gap-3">
                                        <span className="font-semibold text-white">{strategy.name}</span>
                                        <span
                                            className={`text-xs px-2 py-0.5 rounded-full ${strategy.enabled
                                                ? "bg-green-500/20 text-green-400 border border-green-500/30"
                                                : "bg-zinc-500/20 text-zinc-400 border border-zinc-500/30"
                                                }`}
                                        >
                                            {strategy.enabled ? t("active") : t("inactive")}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        {strategy.net_pnl_usd >= 0 ? (
                                            <TrendingUp className="h-4 w-4 text-green-400" />
                                        ) : (
                                            <TrendingDown className="h-4 w-4 text-red-400" />
                                        )}
                                        <span
                                            className={`font-mono font-semibold ${strategy.net_pnl_usd >= 0 ? "text-green-400" : "text-red-400"
                                                }`}
                                        >
                                            {formatCurrency(strategy.net_pnl_usd)}
                                        </span>
                                    </div>
                                </div>

                                <div className="grid grid-cols-4 gap-4 text-sm">
                                    <div>
                                        <div className="text-zinc-500 text-xs">{t("trades")}</div>
                                        <div className="font-mono text-white">{strategy.total_trades}</div>
                                    </div>
                                    <div>
                                        <div className="text-zinc-500 text-xs">{t("winRate")}</div>
                                        <div className="font-mono text-white">
                                            {formatPct(strategy.win_rate)}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="text-zinc-500 text-xs">{t("profitFactor")}</div>
                                        <div
                                            className={`font-mono ${strategy.profit_factor >= 1.5
                                                ? "text-green-400"
                                                : strategy.profit_factor >= 1.0
                                                    ? "text-yellow-400"
                                                    : "text-red-400"
                                                }`}
                                        >
                                            {strategy.profit_factor.toFixed(2)}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="text-zinc-500 text-xs">{t("avgTrade")}</div>
                                        <div
                                            className={`font-mono ${strategy.avg_trade_usd >= 0 ? "text-green-400" : "text-red-400"
                                                }`}
                                        >
                                            {formatCurrency(strategy.avg_trade_usd)}
                                        </div>
                                    </div>
                                </div>

                                {strategy.last_signal_at && (
                                    <div className="mt-3 text-xs text-zinc-500">
                                        {t("lastSignal")}: {new Date(strategy.last_signal_at).toLocaleString()}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </GlowCard>
    );
}
