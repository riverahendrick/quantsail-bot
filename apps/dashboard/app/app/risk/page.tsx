"use client";

import { useEffect, useState } from "react";
import { 
    stopBot, pauseEntries, resumeEntries, getBotConfig, ConfigVersion 
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ShieldAlert, PauseCircle, PlayCircle, StopCircle, Lock } from "lucide-react";
import { useTranslations } from "next-intl";

export default function RiskPage() {
    const t = useTranslations("RiskPage");
    const [config, setConfig] = useState<ConfigVersion | null>(null);
    const [actionLoading, setActionLoading] = useState<string | null>(null);
    const [statusMessage, setStatusMessage] = useState<string | null>(null);

    useEffect(() => {
        getBotConfig().then(setConfig).catch(console.error);
    }, []);

    const handleAction = async (actionName: string, actionFn: () => Promise<any>) => {
        setActionLoading(actionName);
        setStatusMessage(null);
        try {
            await actionFn();
            setStatusMessage(`${actionName} executed successfully.`);
        } catch (err: any) {
            setStatusMessage(`Error: ${err.message}`);
        } finally {
            setActionLoading(null);
        }
    };

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>

            {statusMessage && (
                <div className={`p-4 rounded-md border ${statusMessage.startsWith("Error") ? "bg-red-500/10 border-red-500/20 text-red-600" : "bg-green-500/10 border-green-500/20 text-green-600"}`}>
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
                        <CardDescription>{t("emergencyDesc")}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <Button 
                            variant="destructive" 
                            className="w-full flex items-center justify-center gap-2"
                            onClick={() => handleAction("Stop Bot", stopBot)}
                            disabled={!!actionLoading}
                        >
                            <StopCircle className="h-4 w-4" />
                            {actionLoading === "Stop Bot" ? t("stopping") : t("stopBot")}
                        </Button>
                        
                        <div className="grid grid-cols-2 gap-4">
                            <Button 
                                variant="outline" 
                                className="border-orange-200 hover:bg-orange-50 dark:border-orange-900 dark:hover:bg-orange-900/20"
                                onClick={() => handleAction("Pause Entries", pauseEntries)}
                                disabled={!!actionLoading}
                            >
                                <PauseCircle className="h-4 w-4 mr-2 text-orange-500" />
                                {t("pauseEntries")}
                            </Button>
                            <Button 
                                variant="outline" 
                                className="border-green-200 hover:bg-green-50 dark:border-green-900 dark:hover:bg-green-900/20"
                                onClick={() => handleAction("Resume Entries", resumeEntries)}
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
                        <CardDescription>{t("dailyLimitsDesc")}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {config ? (
                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between border-b pb-2">
                                    <span className="text-muted-foreground">{t("targetMode")}</span>
                                    <span className="font-mono">{config.config_json?.daily?.mode || "N/A"}</span>
                                </div>
                                <div className="flex justify-between border-b pb-2">
                                    <span className="text-muted-foreground">{t("targetUsd")}</span>
                                    <span className="font-mono">${config.config_json?.daily?.target_usd || 0}</span>
                                </div>
                                <div className="flex justify-between border-b pb-2">
                                    <span className="text-muted-foreground">{t("maxLossUsd")}</span>
                                    <span className="font-mono text-red-500">-${Math.abs(config.config_json?.daily?.max_loss_usd || 0)}</span>
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