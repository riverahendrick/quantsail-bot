"use client";

import { useEffect, useState } from "react";
import { getGridPortfolio, GridPortfolio } from "@/lib/api";
import { GlowCard } from "@/components/ui/glow-card";
import { NeoMetricCard } from "@/components/ui/neo-card";
import { Button } from "@/components/ui/button";
import { formatCurrency, formatPct } from "@/lib/utils";
import { useTranslations } from "next-intl";
import {
    Grid3x3,
    RefreshCw,
    Wallet,
    TrendingUp,
    TrendingDown,
    BarChart2,
    Layers,
    ArrowUpDown,
} from "lucide-react";

export function GridPortfolioWidget() {
    const t = useTranslations("GridPage");
    const [portfolio, setPortfolio] = useState<GridPortfolio | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getGridPortfolio();
            setPortfolio(data);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : t("loadError");
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 15000);
        return () => clearInterval(interval);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    if (error) {
        return (
            <div className="p-4 text-red-500 border border-red-200 rounded text-sm">
                {error}
            </div>
        );
    }

    if (!portfolio || !portfolio.active) {
        return (
            <GlowCard variant="default">
                <div className="p-8 text-center">
                    <Grid3x3 className="h-12 w-12 text-zinc-600 mx-auto mb-4" />
                    <p className="text-zinc-400">{t("inactive")}</p>
                </div>
            </GlowCard>
        );
    }

    const { summary, coins } = portfolio;
    const netPnl = summary.net_pnl;

    return (
        <div className="space-y-6">
            {/* Portfolio Summary KPIs */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <Grid3x3 className="h-6 w-6 text-cyan-400" />
                        {t("summaryTitle")}
                    </h2>
                    <p className="text-sm text-zinc-400 mt-1">
                        {t("since")} {portfolio.started_at ? new Date(portfolio.started_at).toLocaleDateString() : "—"}
                    </p>
                </div>
                <Button variant="outline" size="icon" onClick={fetchData} disabled={loading}>
                    <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                </Button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <NeoMetricCard
                    title={t("capital")}
                    value={formatCurrency(portfolio.total_capital_usd)}
                    icon={Wallet}
                />
                <NeoMetricCard
                    title={t("buys")}
                    value={String(summary.total_buys)}
                    icon={TrendingDown}
                />
                <NeoMetricCard
                    title={t("sells")}
                    value={String(summary.total_sells)}
                    icon={TrendingUp}
                />
                <NeoMetricCard
                    title={t("pnl")}
                    value={formatCurrency(netPnl)}
                    icon={BarChart2}
                    variant={netPnl >= 0 ? "success" : "destructive"}
                />
            </div>

            {/* Per-Coin Grid Details */}
            <h3 className="text-lg font-semibold text-white flex items-center gap-2 mt-8">
                <Layers className="h-5 w-5 text-cyan-400" />
                {t("coinTitle")}
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {coins.map((coin) => (
                    <GlowCard key={coin.symbol} variant="default">
                        <div className="p-5">
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                                        <span className="text-sm font-bold text-cyan-400">
                                            {coin.symbol.slice(0, 3)}
                                        </span>
                                    </div>
                                    <div>
                                        <span className="font-semibold text-white">{coin.pair}</span>
                                        <div className="text-xs text-zinc-500">
                                            {t("allocation")}: {formatCurrency(coin.allocation_usd)}
                                        </div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className={`font-mono font-semibold ${coin.net_pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                                        {formatCurrency(coin.net_pnl)}
                                    </div>
                                    <div className="text-xs text-zinc-500">{t("pnl")}</div>
                                </div>
                            </div>

                            <div className="grid grid-cols-3 gap-3 text-sm">
                                <div className="p-2 rounded bg-white/5">
                                    <div className="text-xs text-zinc-500">{t("center")}</div>
                                    <div className="font-mono text-white">${coin.grid_center.toFixed(4)}</div>
                                </div>
                                <div className="p-2 rounded bg-white/5">
                                    <div className="text-xs text-zinc-500">{t("range")}</div>
                                    <div className="font-mono text-white">
                                        {formatPct(coin.lower_pct)}–{formatPct(coin.upper_pct)}
                                    </div>
                                </div>
                                <div className="p-2 rounded bg-white/5">
                                    <div className="text-xs text-zinc-500">{t("levels")}</div>
                                    <div className="font-mono text-white">{coin.total_levels}</div>
                                </div>
                            </div>

                            <div className="flex items-center justify-between mt-3 text-xs text-zinc-500">
                                <div className="flex items-center gap-3">
                                    <span><ArrowUpDown className="h-3 w-3 inline mr-1" />{coin.total_buys}B / {coin.total_sells}S</span>
                                    <span>{t("filled")}: {coin.filled_levels}/{coin.total_levels}</span>
                                </div>
                                {coin.last_updated && (
                                    <span>{new Date(coin.last_updated).toLocaleTimeString()}</span>
                                )}
                            </div>
                        </div>
                    </GlowCard>
                ))}
            </div>
        </div>
    );
}
