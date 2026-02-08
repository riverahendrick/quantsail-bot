"use client";

import { useEffect, useState } from "react";
import { getPortfolioRisk } from "@/lib/api";
import { GlowCard } from "@/components/ui/glow-card";
import { RefreshCw, Shield, AlertTriangle, TrendingDown, DollarSign } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTranslations } from "next-intl";
import { formatCurrency, formatPct } from "@/lib/utils";

type PortfolioRisk = {
    total_exposure_usd: number;
    open_positions: number;
    max_drawdown_pct: number;
    current_drawdown_pct: number;
    daily_pnl_usd: number;
    daily_pnl_pct: number;
    var_95_usd: number;
    risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
};

const riskColors = {
    LOW: "text-green-400 bg-green-500/20 border-green-500/30",
    MEDIUM: "text-yellow-400 bg-yellow-500/20 border-yellow-500/30",
    HIGH: "text-orange-400 bg-orange-500/20 border-orange-500/30",
    CRITICAL: "text-red-400 bg-red-500/20 border-red-500/30",
};

export function RiskPortfolioWidget() {
    const t = useTranslations("RiskPortfolio");
    const [risk, setRisk] = useState<PortfolioRisk | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getPortfolioRisk();
            setRisk(data as PortfolioRisk);
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

    const getRiskIcon = () => {
        if (!risk) return <Shield className="h-5 w-5 text-cyan-400" />;
        switch (risk.risk_level) {
            case "CRITICAL":
                return <AlertTriangle className="h-5 w-5 text-red-400 animate-pulse" />;
            case "HIGH":
                return <AlertTriangle className="h-5 w-5 text-orange-400" />;
            default:
                return <Shield className="h-5 w-5 text-cyan-400" />;
        }
    };

    return (
        <GlowCard variant={risk?.risk_level === "CRITICAL" ? "destructive" : "default"}>
            <div className="p-6 border-b border-white/5 flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        {getRiskIcon()}
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

                {!risk && !loading ? (
                    <div className="text-center text-muted-foreground py-8">
                        {t("noData")}
                    </div>
                ) : risk ? (
                    <div className="space-y-6">
                        {/* Risk Level Badge */}
                        <div className="flex items-center justify-center">
                            <span
                                className={`text-sm font-bold px-4 py-2 rounded-lg border ${riskColors[risk.risk_level]
                                    }`}
                            >
                                {t(`riskLevel.${risk.risk_level}`)}
                            </span>
                        </div>

                        {/* Key Metrics Grid */}
                        <div className="grid grid-cols-2 gap-4">
                            {/* Total Exposure */}
                            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                                <div className="flex items-center gap-2 text-zinc-400 text-xs mb-1">
                                    <DollarSign className="h-3 w-3" />
                                    {t("exposure")}
                                </div>
                                <div className="font-mono text-lg font-semibold text-white">
                                    {formatCurrency(risk.total_exposure_usd)}
                                </div>
                                <div className="text-xs text-zinc-500 mt-1">
                                    {risk.open_positions} {t("positions")}
                                </div>
                            </div>

                            {/* Current Drawdown */}
                            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                                <div className="flex items-center gap-2 text-zinc-400 text-xs mb-1">
                                    <TrendingDown className="h-3 w-3" />
                                    {t("drawdown")}
                                </div>
                                <div
                                    className={`font-mono text-lg font-semibold ${risk.current_drawdown_pct > 10
                                        ? "text-red-400"
                                        : risk.current_drawdown_pct > 5
                                            ? "text-yellow-400"
                                            : "text-green-400"
                                        }`}
                                >
                                    {formatPct(risk.current_drawdown_pct)}
                                </div>
                                <div className="text-xs text-zinc-500 mt-1">
                                    {t("maxDrawdown")}: {formatPct(risk.max_drawdown_pct)}
                                </div>
                            </div>

                            {/* Daily P&L */}
                            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                                <div className="text-zinc-400 text-xs mb-1">{t("dailyPnl")}</div>
                                <div
                                    className={`font-mono text-lg font-semibold ${risk.daily_pnl_usd >= 0 ? "text-green-400" : "text-red-400"
                                        }`}
                                >
                                    {formatCurrency(risk.daily_pnl_usd)}
                                </div>
                                <div
                                    className={`text-xs mt-1 ${risk.daily_pnl_pct >= 0 ? "text-green-500" : "text-red-500"
                                        }`}
                                >
                                    {risk.daily_pnl_pct >= 0 ? "+" : ""}
                                    {formatPct(risk.daily_pnl_pct)}
                                </div>
                            </div>

                            {/* VaR */}
                            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                                <div className="text-zinc-400 text-xs mb-1">{t("var95")}</div>
                                <div className="font-mono text-lg font-semibold text-amber-400">
                                    {formatCurrency(Math.abs(risk.var_95_usd))}
                                </div>
                                <div className="text-xs text-zinc-500 mt-1">{t("var95Desc")}</div>
                            </div>
                        </div>

                        {/* Drawdown Progress Bar */}
                        <div>
                            <div className="flex justify-between text-xs text-zinc-400 mb-2">
                                <span>{t("drawdownBar")}</span>
                                <span>{formatPct(risk.max_drawdown_pct)} {t("limit")}</span>
                            </div>
                            <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                                <div
                                    className={`h-full transition-all duration-500 ${risk.current_drawdown_pct > risk.max_drawdown_pct * 0.8
                                        ? "bg-red-500"
                                        : risk.current_drawdown_pct > risk.max_drawdown_pct * 0.5
                                            ? "bg-yellow-500"
                                            : "bg-cyan-500"
                                        }`}
                                    style={{
                                        width: `${Math.min(
                                            (risk.current_drawdown_pct / risk.max_drawdown_pct) * 100,
                                            100
                                        )}%`,
                                    }}
                                />
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="flex items-center justify-center py-8">
                        <RefreshCw className="h-6 w-6 text-zinc-500 animate-spin" />
                    </div>
                )}
            </div>
        </GlowCard>
    );
}
