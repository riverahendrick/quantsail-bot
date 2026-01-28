import { useDashboardStore } from "@/lib/store";
import { formatCurrency } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslations } from "next-intl";
import { Lock, Unlock, ArrowDownToLine, ArrowUpToLine } from "lucide-react";
import { cn } from "@/lib/utils";

export function DailyLockWidget() {
  const { botState } = useDashboardStore();
  const t = useTranslations("Dashboard");
  const tCommon = useTranslations("Common");
  const lock = botState.daily_lock;

  const progress = Math.min(100, Math.max(0, (lock.realized_pnl / lock.target_usd) * 100));
  const isTargetHit = lock.realized_pnl >= lock.target_usd;
  
  // Gradient calculation based on progress
  const progressColor = isTargetHit 
    ? "bg-gradient-to-r from-emerald-500 to-emerald-400" 
    : "bg-gradient-to-r from-blue-600 to-blue-400";

  return (
    <Card className="col-span-1 md:col-span-1 border-border bg-card h-full">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          {t("dailyTargetLock")}
        </CardTitle>
        <div className={cn(
          "px-2.5 py-0.5 rounded-full text-xs font-bold flex items-center gap-1.5 border",
          lock.entries_paused 
            ? "bg-red-500/10 text-red-500 border-red-500/20" 
            : "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
        )}>
          {lock.entries_paused ? <Lock className="h-3 w-3" /> : <Unlock className="h-3 w-3" />}
          {lock.entries_paused ? "LOCKED" : "ACTIVE"}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        
        {/* Main Progress Area */}
        <div className="space-y-2">
          <div className="flex justify-between items-end">
             <div>
                <span className="text-xs text-muted-foreground uppercase tracking-wider">{t("realized")}</span>
                <div className={cn(
                  "text-2xl font-bold",
                  lock.realized_pnl >= 0 ? "text-emerald-500" : "text-red-500"
                )}>
                  {formatCurrency(lock.realized_pnl)}
                </div>
             </div>
             <div className="text-right">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">{t("target")}</span>
                <div className="text-lg font-semibold text-foreground">
                  {formatCurrency(lock.target_usd)}
                </div>
             </div>
          </div>

          <div className="relative h-3 w-full overflow-hidden rounded-full bg-secondary shadow-inner">
             <div 
               className={cn("h-full transition-all duration-500 ease-out shadow-lg", progressColor)}
               style={{ width: `${progress}%` }}
             />
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4 pt-2">
           <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/30 border border-border/50">
             <div className="p-2 rounded-full bg-blue-500/10 text-blue-500">
               <ArrowUpToLine className="h-4 w-4" />
             </div>
             <div>
               <p className="text-xs text-muted-foreground">{t("peak")}</p>
               <p className="font-mono font-medium">{formatCurrency(lock.peak_pnl)}</p>
             </div>
           </div>
           
           <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/30 border border-border/50">
             <div className="p-2 rounded-full bg-orange-500/10 text-orange-500">
               <ArrowDownToLine className="h-4 w-4" />
             </div>
             <div>
               <p className="text-xs text-muted-foreground">{t("floor")}</p>
               <p className="font-mono font-medium text-orange-500">{formatCurrency(lock.floor_usd)}</p>
             </div>
           </div>
        </div>

        <div className="text-xs text-center text-muted-foreground pt-2 border-t border-border">
          {t("mode")}{tCommon("colonSeparator")}<span className="font-bold text-foreground">{lock.mode}</span>
        </div>

      </CardContent>
    </Card>
  );
}
