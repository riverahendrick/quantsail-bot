"use client";

import { useEffect, useState } from "react";
import { getKillSwitchStatus, triggerKillSwitch, resumeTrading } from "@/lib/api";
import { GlowCard } from "@/components/ui/glow-card";
import { Button } from "@/components/ui/button";
import { AlertTriangle, Power, PlayCircle, RefreshCw, ShieldOff } from "lucide-react";
import { useTranslations } from "next-intl";

type KillSwitchStatus = {
    is_killed: boolean;
    current_event: {
        timestamp: string;
        reason: string;
        triggered_by: string;
        details: string;
        auto_resume_at: string | null;
    } | null;
    history_count: number;
    daily_pnl_pct: number;
    current_drawdown_pct: number;
    consecutive_losses: number;
};

export function KillSwitchWidget() {
    const t = useTranslations("KillSwitch");
    const [status, setStatus] = useState<KillSwitchStatus | null>(null);
    const [loading, setLoading] = useState(false);
    const [actionLoading, setActionLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchStatus = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getKillSwitchStatus();
            setStatus(data as KillSwitchStatus);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : t("loadError");
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        // Poll status every 10 seconds
        const interval = setInterval(fetchStatus, 10000);
        return () => clearInterval(interval);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleKill = async () => {
        if (!confirm(t("confirmKill"))) return;

        setActionLoading(true);
        try {
            await triggerKillSwitch("Manual operator trigger from dashboard");
            await fetchStatus();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : t("actionError");
            setError(msg);
        } finally {
            setActionLoading(false);
        }
    };

    const handleResume = async () => {
        if (!confirm(t("confirmResume"))) return;

        setActionLoading(true);
        try {
            await resumeTrading();
            await fetchStatus();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : t("actionError");
            setError(msg);
        } finally {
            setActionLoading(false);
        }
    };

    const isKilled = status?.is_killed ?? false;

    return (
        <GlowCard variant={isKilled ? "destructive" : "default"}>
            <div className="p-6 border-b border-white/5 flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        {isKilled ? (
                            <ShieldOff className="h-5 w-5 text-red-400 animate-pulse" />
                        ) : (
                            <Power className="h-5 w-5 text-green-400" />
                        )}
                        {t("title")}
                    </h3>
                    <p className="text-sm text-zinc-400 mt-1">{t("description")}</p>
                </div>
                <Button variant="outline" size="icon" onClick={fetchStatus} disabled={loading}>
                    <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                </Button>
            </div>

            <div className="p-6 space-y-6">
                {error && (
                    <div className="p-4 text-red-500 border border-red-200 rounded text-sm">
                        {error}
                    </div>
                )}

                {/* Status Display */}
                <div className="flex items-center justify-center">
                    <div
                        className={`px-6 py-3 rounded-lg border-2 font-bold text-lg ${isKilled
                                ? "bg-red-500/20 border-red-500/50 text-red-400"
                                : "bg-green-500/20 border-green-500/50 text-green-400"
                            }`}
                    >
                        {isKilled ? (
                            <div className="flex items-center gap-2">
                                <AlertTriangle className="h-5 w-5 animate-pulse" />
                                {t("statusKilled")}
                            </div>
                        ) : (
                            <div className="flex items-center gap-2">
                                <Power className="h-5 w-5" />
                                {t("statusActive")}
                            </div>
                        )}
                    </div>
                </div>

                {/* Kill Event Details */}
                {isKilled && status?.current_event && (
                    <div className="p-4 rounded-lg bg-red-900/20 border border-red-500/30 space-y-2">
                        <div className="text-sm">
                            <span className="text-zinc-400">{t("reason")}:</span>{" "}
                            <span className="text-red-400 font-medium">
                                {status.current_event.reason}
                            </span>
                        </div>
                        <div className="text-sm">
                            <span className="text-zinc-400">{t("triggeredBy")}:</span>{" "}
                            <span className="text-white">{status.current_event.triggered_by}</span>
                        </div>
                        <div className="text-sm">
                            <span className="text-zinc-400">{t("time")}:</span>{" "}
                            <span className="text-white font-mono">
                                {new Date(status.current_event.timestamp).toLocaleString()}
                            </span>
                        </div>
                        {status.current_event.details && (
                            <div className="text-sm">
                                <span className="text-zinc-400">{t("details")}:</span>{" "}
                                <span className="text-zinc-300">{status.current_event.details}</span>
                            </div>
                        )}
                        {status.current_event.auto_resume_at && (
                            <div className="text-sm">
                                <span className="text-zinc-400">{t("autoResume")}:</span>{" "}
                                <span className="text-yellow-400 font-mono">
                                    {new Date(status.current_event.auto_resume_at).toLocaleString()}
                                </span>
                            </div>
                        )}
                    </div>
                )}

                {/* Quick Stats */}
                {status && !isKilled && (
                    <div className="grid grid-cols-3 gap-4 text-center">
                        <div className="p-3 rounded bg-white/5">
                            <div className="text-xs text-zinc-400">{t("dailyPnl")}</div>
                            <div
                                className={`font-mono font-semibold ${status.daily_pnl_pct >= 0 ? "text-green-400" : "text-red-400"
                                    }`}
                            >
                                {status.daily_pnl_pct >= 0 ? "+" : ""}
                                {status.daily_pnl_pct.toFixed(2)}%
                            </div>
                        </div>
                        <div className="p-3 rounded bg-white/5">
                            <div className="text-xs text-zinc-400">{t("drawdown")}</div>
                            <div
                                className={`font-mono font-semibold ${status.current_drawdown_pct > 10 ? "text-red-400" : "text-yellow-400"
                                    }`}
                            >
                                {status.current_drawdown_pct.toFixed(2)}%
                            </div>
                        </div>
                        <div className="p-3 rounded bg-white/5">
                            <div className="text-xs text-zinc-400">{t("losses")}</div>
                            <div
                                className={`font-mono font-semibold ${status.consecutive_losses > 3 ? "text-red-400" : "text-white"
                                    }`}
                            >
                                {status.consecutive_losses}
                            </div>
                        </div>
                    </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3">
                    {isKilled ? (
                        <Button
                            className="flex-1 bg-green-600 hover:bg-green-700"
                            onClick={handleResume}
                            disabled={actionLoading}
                        >
                            {actionLoading ? (
                                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                                <PlayCircle className="h-4 w-4 mr-2" />
                            )}
                            {t("resumeButton")}
                        </Button>
                    ) : (
                        <Button
                            variant="destructive"
                            className="flex-1"
                            onClick={handleKill}
                            disabled={actionLoading}
                        >
                            {actionLoading ? (
                                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                                <ShieldOff className="h-4 w-4 mr-2" />
                            )}
                            {t("killButton")}
                        </Button>
                    )}
                </div>

                {/* History Count */}
                {status && status.history_count > 0 && (
                    <div className="text-center text-xs text-zinc-500">
                        {t("historyCount", { count: status.history_count })}
                    </div>
                )}
            </div>
        </GlowCard>
    );
}
