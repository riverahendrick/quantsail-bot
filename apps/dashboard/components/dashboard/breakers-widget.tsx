"use client";

import { useDashboardStore } from "@/lib/store";
import { NeoCard } from "@/components/ui/neo-card";
import { useTranslations } from "next-intl";
import { AlertOctagon, CheckCircle2, Shield, Clock } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";

export function BreakersWidget() {
  const { botState } = useDashboardStore();
  const t = useTranslations("Dashboard");
  const breakers = botState.active_breakers;

  const hasBreakers = breakers.length > 0;

  return (
    <NeoCard variant={hasBreakers ? "destructive" : "success"}>
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={cn(
              "p-2.5 rounded-xl",
              hasBreakers ? "bg-rose-500/20" : "bg-emerald-500/20"
            )}>
              <Shield className={cn(
                "w-5 h-5",
                hasBreakers ? "text-rose-400" : "text-emerald-400"
              )} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{t("activeBreakers")}</h3>
              <p className="text-sm text-zinc-500">{t("circuitProtection")}</p>
            </div>
          </div>
          
          {hasBreakers ? (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-500/20 border border-rose-500/30">
              <AlertOctagon className="w-4 h-4 text-rose-400" />
              <span className="text-xs font-bold text-rose-400">{breakers.length}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-bold text-emerald-400">{t("ok")}</span>
            </div>
          )}
        </div>

        {/* Content */}
        {breakers.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-3">
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
            </div>
            <p className="text-zinc-400 font-medium">{t("noActiveBreakers")}</p>
            <p className="text-xs text-zinc-600 mt-1">{t("allSystemsOperational")}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {breakers.map((breaker, idx) => (
              <div
                key={idx}
                className={cn(
                  "p-4 rounded-xl",
                  "bg-rose-500/10 border border-rose-500/20",
                  "animate-fade-in-up"
                )}
                style={{ animationDelay: `${idx * 0.1}s`, opacity: 0 }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-rose-500/20">
                      <AlertOctagon className="w-4 h-4 text-rose-400" />
                    </div>
                    <div>
                      <p className="font-medium text-rose-400">
                        {breaker.type}
                      </p>
                      {breaker.expiry && (
                        <p className="text-xs text-rose-300/70 mt-0.5">
                          {t("expiresIn")} {formatDistanceToNow(new Date(breaker.expiry))}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  {breaker.expiry && (
                    <div className="flex items-center gap-1.5 text-xs text-zinc-500 shrink-0">
                      <Clock className="w-3 h-3" />
                      <span>
                        {formatDistanceToNow(new Date(breaker.expiry))}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </NeoCard>
  );
}
