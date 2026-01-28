"use client";

import { useDashboardStore } from "@/lib/store";
import { formatCurrency } from "@/lib/utils";
import { NeoCard } from "@/components/ui/neo-card";
import { useTranslations } from "next-intl";
import { Lock, Unlock, ArrowUpToLine, ArrowDownToLine, Target } from "lucide-react";
import { cn } from "@/lib/utils";

export function DailyLockWidget() {
  const { botState } = useDashboardStore();
  const t = useTranslations("Dashboard");
  const tCommon = useTranslations("Common");
  const lock = botState.daily_lock;

  const progress = Math.min(100, Math.max(0, (lock.realized_pnl / lock.target_usd) * 100));
  const isTargetHit = lock.realized_pnl >= lock.target_usd;

  return (
    <NeoCard variant={lock.entries_paused ? "destructive" : "success"} className="h-full">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className={cn(
              "p-2.5 rounded-xl",
              lock.entries_paused ? "bg-rose-500/20" : "bg-emerald-500/20"
            )}>
              <Target className={cn(
                "w-5 h-5",
                lock.entries_paused ? "text-rose-400" : "text-emerald-400"
              )} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{t("dailyTargetLock")}</h3>
              <p className="text-sm text-zinc-500">{t("tradingLimits")}</p>
            </div>
          </div>
          
          {/* Status Badge */}
          <div
            className={cn(
              "px-3 py-1.5 rounded-full text-xs font-bold flex items-center gap-1.5 border",
              lock.entries_paused
                ? "bg-rose-500/20 text-rose-400 border-rose-500/30"
                : "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
            )}
          >
            {lock.entries_paused ? <Lock className="w-3 h-3" /> : <Unlock className="w-3 h-3" />}
            {lock.entries_paused ? t("locked") : t("active")}
          </div>
        </div>

        {/* Progress Section */}
        <div className="space-y-4 mb-6">
          <div className="flex justify-between items-end">
            <div>
              <span className="text-xs text-zinc-500 uppercase tracking-wider">{t("realized")}</span>
              <div
                className={cn(
                  "text-3xl font-bold number-display mt-1",
                  lock.realized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"
                )}
              >
                {formatCurrency(lock.realized_pnl)}
              </div>
            </div>
            <div className="text-right">
              <span className="text-xs text-zinc-500 uppercase tracking-wider">{t("target")}</span>
              <div className="text-xl font-semibold text-white number-display mt-1">
                {formatCurrency(lock.target_usd)}
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="relative">
            <div className="h-3 w-full overflow-hidden rounded-full bg-white/5">
              <div
                className={cn(
                  "h-full transition-all duration-700 ease-out rounded-full relative",
                  isTargetHit
                    ? "bg-gradient-to-r from-emerald-500 to-emerald-400"
                    : "bg-gradient-to-r from-cyan-500 to-blue-500"
                )}
                style={{ width: `${progress}%` }}
              >
                {/* Shimmer effect on progress bar */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
              </div>
            </div>
            {/* Progress markers */}
            <div className="flex justify-between mt-2">
              <span className="text-xs text-zinc-500">{tCommon("zero")}{tCommon("percent")}</span>
              <span className={cn(
                "text-xs font-medium",
                progress >= 50 ? "text-white" : "text-zinc-500"
              )}>
                {progress.toFixed(1)}{tCommon("percent")}
              </span>
              <span className="text-xs text-zinc-500">{tCommon("hundred")}{tCommon("percent")}</span>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-1.5 rounded-lg bg-cyan-500/20">
                <ArrowUpToLine className="w-3.5 h-3.5 text-cyan-400" />
              </div>
              <span className="text-xs text-zinc-500">{t("peak")}</span>
            </div>
            <p className="font-semibold text-white number-display">
              {formatCurrency(lock.peak_pnl)}
            </p>
          </div>

          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-1.5 rounded-lg bg-orange-500/20">
                <ArrowDownToLine className="w-3.5 h-3.5 text-orange-400" />
              </div>
              <span className="text-xs text-zinc-500">{t("floor")}</span>
            </div>
            <p className="font-semibold text-orange-400 number-display">
              {formatCurrency(lock.floor_usd)}
            </p>
          </div>
        </div>

        {/* Mode Indicator */}
        <div className="mt-4 pt-4 border-t border-white/5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-500">{t("mode")}{tCommon("colonSeparator")}</span>
            <span className="text-xs font-medium text-white px-3 py-1 rounded-full bg-white/10 border border-white/5">
              {lock.mode}
            </span>
          </div>
        </div>
      </div>
    </NeoCard>
  );
}
