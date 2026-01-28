"use client";

import { NeoCard } from "@/components/ui/neo-card";
import { useTranslations } from "next-intl";
import { 
  Shield, 
  Eye, 
  Lock, 
  Database, 
  Server, 
  Key,
  CheckCircle2,
  FileCode,
  Globe,
  Users
} from "lucide-react";

export default function PublicTransparencyPage() {
  const t = useTranslations("PublicTransparency");

  const pipelineFeatures = [
    { icon: FileCode, label: t("voteAgg") },
    { icon: Database, label: t("confScore") },
    { icon: Shield, label: t("riskGates") },
  ];

  const safetyFeatures = [
    { icon: Server, label: t("circuitBreakers") },
    { icon: Globe, label: t("newsEvents") },
    { icon: Lock, label: t("dailyLock") },
  ];

  const hiddenItems = [
    t("hidden1"),
    t("hidden2"),
    t("hidden3"),
    t("hidden4"),
  ];

  return (
    <div className="flex flex-col gap-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="text-center animate-fade-in-up">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyan-500/10 border border-cyan-500/20 mb-4">
          <Eye className="w-4 h-4 text-cyan-400" />
          <span className="text-sm text-cyan-400 font-medium">{t("transparencyBadge")}</span>
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-white mb-4">
          {t("title")}
        </h1>
        <p className="text-lg text-zinc-400 max-w-2xl mx-auto">{t("subtitle")}</p>
      </div>

      {/* How It Works Section */}
      <div className="animate-fade-in-up" style={{ animationDelay: "0.1s", opacity: 0 }}>
        <NeoCard variant="primary" gradientBorder>
          <div className="p-8">
            <div className="flex items-center gap-4 mb-6">
              <div className="p-3 rounded-xl bg-cyan-500/20">
                <Server className="w-8 h-8 text-cyan-400" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">{t("pipelineTitle")}</h2>
                <p className="text-zinc-400">{t("pipelineSubtitle")}</p>
              </div>
            </div>
            
            <p className="text-zinc-300 leading-relaxed mb-6">{t("pipelineDesc")}</p>
            
            <div className="grid md:grid-cols-3 gap-4">
              {pipelineFeatures.map((feature, i) => (
                <div 
                  key={i} 
                  className="p-4 rounded-xl bg-white/[0.03] border border-white/5 hover:border-cyan-500/20 transition-colors"
                >
                  <div className="p-2 rounded-lg bg-cyan-500/10 w-fit mb-3">
                    <feature.icon className="w-5 h-5 text-cyan-400" />
                  </div>
                  <p className="text-sm text-zinc-300">{feature.label}</p>
                </div>
              ))}
            </div>
          </div>
        </NeoCard>
      </div>

      {/* Safety Features Grid */}
      <div className="grid md:grid-cols-2 gap-6 animate-fade-in-up" style={{ animationDelay: "0.2s", opacity: 0 }}>
        <NeoCard variant="success">
          <div className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-emerald-500/20">
                <Shield className="w-6 h-6 text-emerald-400" />
              </div>
              <h3 className="text-xl font-bold text-white">{t("safetyTitle")}</h3>
            </div>
            <p className="text-zinc-400 text-sm mb-4">{t("safetyDesc")}</p>
            <ul className="space-y-3">
              {safetyFeatures.map((feature, i) => (
                <li key={i} className="flex items-center gap-3">
                  <div className="p-1.5 rounded-lg bg-emerald-500/10">
                    <feature.icon className="w-4 h-4 text-emerald-400" />
                  </div>
                  <span className="text-sm text-zinc-300">{feature.label}</span>
                </li>
              ))}
            </ul>
          </div>
        </NeoCard>

        <NeoCard variant="purple">
          <div className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-violet-500/20">
                <Users className="w-6 h-6 text-violet-400" />
              </div>
              <h3 className="text-xl font-bold text-white">{t("publicAccessTitle")}</h3>
            </div>
            <p className="text-zinc-400 text-sm mb-4">{t("publicAccessDesc")}</p>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span className="text-sm text-zinc-300">{t("realTimeData")}</span>
              </div>
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span className="text-sm text-zinc-300">{t("tradeHistory")}</span>
              </div>
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span className="text-sm text-zinc-300">{t("performanceMetrics")}</span>
              </div>
            </div>
          </div>
        </NeoCard>
      </div>

      {/* Privacy Section */}
      <NeoCard variant="default" className="animate-fade-in-up" style={{ animationDelay: "0.3s", opacity: 0 }}>
        <div className="p-8">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 rounded-xl bg-rose-500/20">
              <Lock className="w-8 h-8 text-rose-400" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">{t("privacyTitle")}</h2>
              <p className="text-zinc-400">{t("privacySubtitle")}</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <p className="text-zinc-300 leading-relaxed mb-6">{t("privacyDesc")}</p>
              <div className="p-4 rounded-xl bg-rose-500/5 border border-rose-500/10">
                <div className="flex items-center gap-2 mb-3">
                  <Key className="w-4 h-4 text-rose-400" />
                  <span className="text-sm font-medium text-rose-400">{t("protectedData")}</span>
                </div>
                <ul className="space-y-2">
                  {hiddenItems.map((item, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-zinc-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-400/50" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="space-y-4">
              <NeoCard variant="glow" className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-emerald-500/20">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <p className="font-medium text-white">{t("auditableTitle")}</p>
                    <p className="text-sm text-zinc-500">{t("auditableDesc")}</p>
                  </div>
                </div>
              </NeoCard>
              <NeoCard variant="glow" className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-cyan-500/20">
                    <Database className="w-5 h-5 text-cyan-400" />
                  </div>
                  <div>
                    <p className="font-medium text-white">{t("immutableTitle")}</p>
                    <p className="text-sm text-zinc-500">{t("immutableDesc")}</p>
                  </div>
                </div>
              </NeoCard>
            </div>
          </div>
        </div>
      </NeoCard>

      {/* Trust Badge */}
      <div className="text-center animate-fade-in-up" style={{ animationDelay: "0.4s", opacity: 0 }}>
        <div className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 border border-emerald-500/20">
          <Shield className="w-5 h-5 text-emerald-400" />
          <span className="text-emerald-400 font-medium">{t("trustMessage")}</span>
        </div>
      </div>
    </div>
  );
}
