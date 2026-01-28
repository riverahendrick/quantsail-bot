"use client";

import { useDashboardStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { NeoCard } from "@/components/ui/neo-card";
import { AlertTriangle, PauseCircle, Zap, Wifi, WifiOff } from "lucide-react";
import { useTranslations } from "next-intl";

export function StatusBanner() {
  const { botState, isConnected, lastHeartbeat } = useDashboardStore();
  const t = useTranslations("Dashboard");
  const tCommon = useTranslations("Common");

  if (!botState) return null;

  const statusConfig = {
    running: {
      icon: Zap,
      variant: "success" as const,
      gradient: "from-emerald-500/20 to-emerald-400/10",
      iconBg: "bg-emerald-500/20",
      iconColor: "text-emerald-400",
      pulse: true,
      label: t("running"),
    },
    paused: {
      icon: PauseCircle,
      variant: "warning" as const,
      gradient: "from-amber-500/20 to-amber-400/10",
      iconBg: "bg-amber-500/20",
      iconColor: "text-amber-400",
      pulse: false,
      label: t("paused"),
    },
    stopped: {
      icon: AlertTriangle,
      variant: "destructive" as const,
      gradient: "from-rose-500/20 to-rose-400/10",
      iconBg: "bg-rose-500/20",
      iconColor: "text-rose-400",
      pulse: false,
      label: t("stopped"),
    },
    unknown: {
      icon: AlertTriangle,
      variant: "default" as const,
      gradient: "from-zinc-500/20 to-zinc-400/10",
      iconBg: "bg-zinc-500/20",
      iconColor: "text-zinc-400",
      pulse: false,
      label: t("unknown"),
    },
  };

  const config = statusConfig[botState.status] || statusConfig.unknown;
  const Icon = config.icon;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {/* Bot Status Card */}
      <NeoCard variant={config.variant} className={cn("overflow-hidden")}>
        <div className={cn("p-5 bg-gradient-to-br", config.gradient)}>
          <div className="flex items-center gap-4">
            <div className={cn("relative p-3 rounded-xl", config.iconBg)}>
              <Icon className={cn("w-6 h-6", config.iconColor)} />
              {config.pulse && (
                <>
                  <span className="absolute inset-0 rounded-xl animate-ping opacity-30 bg-emerald-400" />
                  <span className="absolute -inset-1 rounded-xl animate-ping opacity-20 bg-emerald-400 animation-delay-200" />
                </>
              )}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold text-white capitalize">
                  {config.label}
                </h3>
                <span className={cn("w-2 h-2 rounded-full", config.iconColor, config.pulse && "animate-pulse")} />
              </div>
              
              {botState.status_reason && (
                <p className="text-sm text-zinc-400 mt-0.5 truncate">
                  {botState.status_reason}
                  {botState.status_until && (
                    <span className="text-zinc-500">
                      {t("untilTime", { time: new Date(botState.status_until).toLocaleTimeString() })}
                    </span>
                  )}
                </p>
              )}
            </div>
          </div>
        </div>
      </NeoCard>

      {/* Connection Status Card */}
      <NeoCard variant={isConnected ? "primary" : "destructive"}>
        <div className="p-5">
          <div className="flex items-center gap-4">
            <div className={cn(
              "p-3 rounded-xl transition-all duration-300",
              isConnected ? "bg-cyan-500/20" : "bg-rose-500/20"
            )}>
              {isConnected ? (
                <Wifi className="w-6 h-6 text-cyan-400" />
              ) : (
                <WifiOff className="w-6 h-6 text-rose-400" />
              )}
            </div>
            
            <div className="flex-1">
              <p className="text-sm font-medium text-zinc-400">{t("systemConnection")}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className={cn(
                  "w-2 h-2 rounded-full animate-pulse",
                  isConnected ? "bg-emerald-400" : "bg-rose-400"
                )} />
                <span className={cn(
                  "font-semibold",
                  isConnected ? "text-emerald-400" : "text-rose-400"
                )}>
                  {isConnected ? t("connected") : t("disconnected")}
                </span>
              </div>
              {lastHeartbeat && (
                <p className="text-xs text-zinc-500 mt-1">
                  {t("lastHeartbeat")}{tCommon("colonSeparator")}{" "}
                  {new Date(lastHeartbeat).toLocaleTimeString()}
                </p>
              )}
            </div>
          </div>
        </div>
      </NeoCard>
    </div>
  );
}
