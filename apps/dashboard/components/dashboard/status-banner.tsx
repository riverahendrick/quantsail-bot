import { useDashboardStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { AlertTriangle, CheckCircle2, PauseCircle, Activity } from "lucide-react";
import { useTranslations } from "next-intl";

export function StatusBanner() {
  const { botState, isConnected, lastHeartbeat } = useDashboardStore();
  const t = useTranslations("Dashboard");
  const tCommon = useTranslations("Common");

  if (!botState) return null;

  const styles = {
    running: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    paused: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    stopped: "bg-red-500/10 text-red-500 border-red-500/20",
    unknown: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  };

  const icons = {
    running: CheckCircle2,
    paused: PauseCircle,
    stopped: AlertTriangle,
    unknown: AlertTriangle,
  };

  const Icon = icons[botState.status] || AlertTriangle;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className={cn("flex items-center gap-4 rounded-xl border px-6 py-4 transition-colors", styles[botState.status])}>
        <div className={cn("p-2 rounded-full bg-background/50 backdrop-blur-sm")}>
           <Icon className="h-6 w-6" />
        </div>
        <div className="flex flex-col">
          <span className="text-lg font-bold capitalize tracking-tight">{t(botState.status)}</span>
          {botState.status_reason && (
            <span className="text-sm opacity-90">
              {botState.status_reason}
              {botState.status_until && ` (${t("until")} ${new Date(botState.status_until).toLocaleTimeString()})`}
            </span>
          )}
        </div>
      </div>
      
      {/* Connection Status Mini-Card */}
      <div className={cn(
        "flex items-center gap-4 rounded-xl border px-6 py-4 bg-card text-card-foreground",
        !isConnected && "border-red-500/50 opacity-70"
      )}>
        <div className="p-2 rounded-full bg-secondary">
          <Activity className={cn("h-6 w-6", isConnected ? "text-primary" : "text-red-500")} />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-medium text-muted-foreground">{t("systemConnection")}</span>
          <div className="flex items-center gap-2">
            <span className={cn("h-2 w-2 rounded-full animate-pulse", isConnected ? "bg-green-500" : "bg-red-500")} />
            <span className="font-bold">
              {isConnected ? t("connected") : t("disconnected")}
            </span>
          </div>
          {lastHeartbeat && (
            <span className="text-xs text-muted-foreground">{t("lastHeartbeat")}{tCommon("colonSeparator")}{new Date(lastHeartbeat).toLocaleTimeString()}</span>
          )}
        </div>
      </div>
    </div>
  );
}