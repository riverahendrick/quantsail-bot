"use client";

import { useEffect, useState } from "react";
import {
    stopBot, pauseEntries, resumeEntries, getBotConfig, ConfigVersion
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ShieldAlert, PauseCircle, PlayCircle, StopCircle, Lock } from "lucide-react";
import { useTranslations } from "next-intl";
import { formatCurrency } from "@/lib/utils";

export default function RiskPage() {
    const t = useTranslations("RiskPage");
    const [config, setConfig] = useState<ConfigVersion | null>(null);
    const [actionLoading, setActionLoading] = useState<string | null>(null);
    const [statusMessage, setStatusMessage] = useState<string | null>(null);
    const [statusKind, setStatusKind] = useState<"success" | "error" | null>(null);

    useEffect(() => {
        getBotConfig()
            .then(setConfig)
            .catch((err: any) => {
                setStatusKind("error");
                setStatusMessage(t("configLoadError", { error: err?.message || t("unknownError") }));
            });
    }, [t]);

    const handleAction = async (actionLabel: string, actionFn: () => Promise<any>) => {
        setActionLoading(actionLabel);
        setStatusMessage(null);
        setStatusKind(null);
        try {
            await actionFn();
            setStatusKind("success");
            setStatusMessage(t("actionSuccess", { action: actionLabel }));
        } catch (err: any) {
            setStatusKind("error");
            setStatusMessage(t("actionError", { action: actionLabel, error: err?.message || t("unknownError") }));
        } finally {
            setActionLoading(null);
        }
    };

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>

            {statusMessage && (
                <div className={`p-4 rounded-md border ${statusKind === "error" ? "bg-red-500/10 border-red-500/20 text-red-600" : "bg-green-500/10 border-green-500/20 text-green-600"}`}>
                    {statusMessage}
                </div>
            )}

            <div className="grid gap-6 md:grid-cols-2">
                {/* Emergency Controls */}
                <Card className="border-red-200 dark:border-red-900">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-red-600 dark:text-red-400">
                            <ShieldAlert className="h-5 w-5" />
                            {t("emergencyTitle")}
                        </CardTitle>
                        <p className="text-sm text-muted-foreground">{t("emergencyDesc")}</p>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <Button 
                            variant="destructive" 
                            className="w-full flex items-center justify-center gap-2"
                            onClick={() => handleAction(t("stopBot"), stopBot)}
                            disabled={!!actionLoading}
                        >
                            <StopCircle className="h-4 w-4" />
                            {actionLoading === t("stopBot") ? t("stopping") : t("stopBot")}
                        </Button>
                        
                        <div className="grid grid-cols-2 gap-4">
                            <Button 
                                variant="outline" 
                                className="border-orange-200 hover:bg-orange-50 dark:border-orange-900 dark:hover:bg-orange-900/20"
                                onClick={() => handleAction(t("pauseEntries"), pauseEntries)}
                                disabled={!!actionLoading}
                            >
                                <PauseCircle className="h-4 w-4 mr-2 text-orange-500" />
                                {t("pauseEntries")}
                            </Button>
                            <Button 
                                variant="outline" 
                                className="border-green-200 hover:bg-green-50 dark:border-green-900 dark:hover:bg-green-900/20"
                                onClick={() => handleAction(t("resumeEntries"), resumeEntries)}
                                disabled={!!actionLoading}
                            >
                                <PlayCircle className="h-4 w-4 mr-2 text-green-500" />
                                {t("resumeEntries")}
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Daily Lock Config View */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Lock className="h-5 w-5" />
                            {t("dailyLimitsTitle")}
                        </CardTitle>
                        <p className="text-sm text-muted-foreground">{t("dailyLimitsDesc")}</p>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {config ? (
                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between border-b pb-2">
                                    <span className="text-muted-foreground">{t("targetMode")}</span>
                                    <span className="font-mono">{config.config_json?.daily?.mode || t("notAvailable")}</span>
                                </div>
                                <div className="flex justify-between border-b pb-2">
                                    <span className="text-muted-foreground">{t("targetUsd")}</span>
                                    <span className="font-mono">{formatCurrency(config.config_json?.daily?.target_usd || 0)}</span>
                                </div>
                                <div className="flex justify-between border-b pb-2">
                                    <span className="text-muted-foreground">{t("maxLossUsd")}</span>
                                    <span className="font-mono text-red-500">{formatCurrency(-Math.abs(config.config_json?.daily?.max_loss_usd || 0))}</span>
                                </div>
                            </div>
                        ) : (
                            <div className="text-muted-foreground text-sm">{t("loading")}</div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
