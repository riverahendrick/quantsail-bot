"use client";

import { useCallback, useEffect, useState } from "react";
import { getBotConfig, createConfigVersion, activateConfig, ConfigVersion } from "@/lib/api";
import { GlowCard } from "@/components/ui/glow-card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
    Save,
    RefreshCw,
    AlertTriangle,
    CheckCircle2,
    Shield,
    TrendingUp,
    Zap,
    SlidersHorizontal,
} from "lucide-react";
import { useTranslations } from "next-intl";

type Profile = "conservative" | "moderate" | "aggressive" | "custom";

interface ProfilePreset {
    key: Profile;
    icon: React.ComponentType<{ className?: string }>;
    color: string;
    borderColor: string;
    glowColor: string;
}

const PROFILES: ProfilePreset[] = [
    {
        key: "conservative",
        icon: Shield,
        color: "from-emerald-500/20 to-green-500/10",
        borderColor: "border-emerald-500/30",
        glowColor: "shadow-emerald-500/10",
    },
    {
        key: "moderate",
        icon: TrendingUp,
        color: "from-blue-500/20 to-cyan-500/10",
        borderColor: "border-blue-500/30",
        glowColor: "shadow-blue-500/10",
    },
    {
        key: "aggressive",
        icon: Zap,
        color: "from-orange-500/20 to-red-500/10",
        borderColor: "border-orange-500/30",
        glowColor: "shadow-orange-500/10",
    },
    {
        key: "custom",
        icon: SlidersHorizontal,
        color: "from-violet-500/20 to-purple-500/10",
        borderColor: "border-violet-500/30",
        glowColor: "shadow-violet-500/10",
    },
];

// Parameter display sections
interface ParamField {
    key: string;
    path: string[];
    step?: number;
    min?: number;
    max?: number;
}

const PARAM_SECTIONS: { titleKey: string; fields: ParamField[] }[] = [
    {
        titleKey: "positionSizing",
        fields: [
            { key: "riskPct", path: ["position_sizing", "risk_pct"], step: 0.1, min: 0.1, max: 5 },
            { key: "maxPositionPct", path: ["position_sizing", "max_position_pct"], step: 1, min: 5, max: 50 },
            { key: "kellyFraction", path: ["position_sizing", "kelly_fraction"], step: 0.05, min: 0.05, max: 0.5 },
        ],
    },
    {
        titleKey: "stopLoss",
        fields: [
            { key: "slAtrMultiplier", path: ["stop_loss", "atr_multiplier"], step: 0.1, min: 0.5, max: 5 },
            { key: "slFixedPct", path: ["stop_loss", "fixed_pct"], step: 0.5, min: 0.5, max: 10 },
        ],
    },
    {
        titleKey: "takeProfitSection",
        fields: [
            { key: "tpRiskReward", path: ["take_profit", "risk_reward_ratio"], step: 0.1, min: 1, max: 5 },
            { key: "tpFixedPct", path: ["take_profit", "fixed_pct"], step: 0.5, min: 1, max: 15 },
        ],
    },
    {
        titleKey: "trailingStopSection",
        fields: [
            { key: "tsTrailPct", path: ["trailing_stop", "trail_pct"], step: 0.1, min: 0.5, max: 5 },
            { key: "tsAtrMultiplier", path: ["trailing_stop", "atr_multiplier"], step: 0.1, min: 1, max: 5 },
            { key: "tsActivationPct", path: ["trailing_stop", "activation_pct"], step: 0.1, min: 0.1, max: 3 },
        ],
    },
    {
        titleKey: "portfolioSection",
        fields: [
            { key: "maxDailyTrades", path: ["portfolio", "max_daily_trades"], step: 1, min: 1, max: 50 },
            { key: "maxDailyLossUsd", path: ["portfolio", "max_daily_loss_usd"], step: 5, min: 5, max: 200 },
            { key: "maxExposurePct", path: ["portfolio", "max_portfolio_exposure_pct"], step: 5, min: 5, max: 80 },
        ],
    },
    {
        titleKey: "ensembleSection",
        fields: [
            { key: "confidenceThreshold", path: ["strategies", "ensemble", "confidence_threshold"], step: 0.05, min: 0.1, max: 1 },
            { key: "weightedThreshold", path: ["strategies", "ensemble", "weighted_threshold"], step: 0.05, min: 0.1, max: 1 },
        ],
    },
];

function getNestedValue(obj: Record<string, unknown>, path: string[]): number {
    let current: unknown = obj;
    for (const key of path) {
        if (current && typeof current === "object" && key in (current as Record<string, unknown>)) {
            current = (current as Record<string, unknown>)[key];
        } else {
            return 0;
        }
    }
    return typeof current === "number" ? current : 0;
}

function setNestedValue(obj: Record<string, unknown>, path: string[], value: number): Record<string, unknown> {
    const result = JSON.parse(JSON.stringify(obj)) as Record<string, unknown>;
    let current: Record<string, unknown> = result;
    for (let i = 0; i < path.length - 1; i++) {
        if (!(path[i] in current) || typeof current[path[i]] !== "object") {
            current[path[i]] = {};
        }
        current = current[path[i]] as Record<string, unknown>;
    }
    current[path[path.length - 1]] = value;
    return result;
}

// Profile defaults matching Python parameter_profiles.py
const PROFILE_DEFAULTS: Record<string, Record<string, unknown>> = {
    conservative: {
        profile: "conservative",
        position_sizing: { method: "risk_pct", risk_pct: 0.5, max_position_pct: 15, kelly_fraction: 0.15 },
        stop_loss: { method: "atr", atr_multiplier: 3.0, fixed_pct: 3.0 },
        take_profit: { method: "risk_reward", risk_reward_ratio: 3.0, fixed_pct: 6.0 },
        trailing_stop: { enabled: true, method: "atr", trail_pct: 2.0, atr_multiplier: 3.0, activation_pct: 1.5 },
        portfolio: { max_daily_trades: 5, max_daily_loss_usd: 10, max_portfolio_exposure_pct: 20 },
        strategies: { ensemble: { mode: "agreement", confidence_threshold: 0.7, weighted_threshold: 0.7 } },
    },
    moderate: {
        profile: "moderate",
        position_sizing: { method: "risk_pct", risk_pct: 1.0, max_position_pct: 25, kelly_fraction: 0.25 },
        stop_loss: { method: "atr", atr_multiplier: 2.0, fixed_pct: 2.0 },
        take_profit: { method: "risk_reward", risk_reward_ratio: 2.0, fixed_pct: 4.0 },
        trailing_stop: { enabled: true, method: "atr", trail_pct: 1.5, atr_multiplier: 2.5, activation_pct: 1.0 },
        portfolio: { max_daily_trades: 10, max_daily_loss_usd: 20, max_portfolio_exposure_pct: 30 },
        strategies: { ensemble: { mode: "weighted", confidence_threshold: 0.5, weighted_threshold: 0.6 } },
    },
    aggressive: {
        profile: "aggressive",
        position_sizing: { method: "kelly", risk_pct: 2.0, max_position_pct: 40, kelly_fraction: 0.35 },
        stop_loss: { method: "atr", atr_multiplier: 1.5, fixed_pct: 1.5 },
        take_profit: { method: "risk_reward", risk_reward_ratio: 1.5, fixed_pct: 3.0 },
        trailing_stop: { enabled: true, method: "atr", trail_pct: 1.0, atr_multiplier: 2.0, activation_pct: 0.5 },
        portfolio: { max_daily_trades: 20, max_daily_loss_usd: 50, max_portfolio_exposure_pct: 45 },
        strategies: { ensemble: { mode: "weighted", confidence_threshold: 0.3, weighted_threshold: 0.5 } },
    },
};

export default function SettingsPage() {
    const t = useTranslations("SettingsPage");
    const [config, setConfig] = useState<ConfigVersion | null>(null);
    const [configData, setConfigData] = useState<Record<string, unknown>>({});
    const [selectedProfile, setSelectedProfile] = useState<Profile>("custom");
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const fetchConfig = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getBotConfig();
            setConfig(data);
            setConfigData(data.config_json as unknown as Record<string, unknown>);
            const profile = (data.config_json as unknown as Record<string, unknown>).profile;
            if (typeof profile === "string" && ["conservative", "moderate", "aggressive"].includes(profile)) {
                setSelectedProfile(profile as Profile);
            } else {
                setSelectedProfile("custom");
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : t("loadError");
            if (!msg.includes("No active config")) {
                setError(msg);
            }
        } finally {
            setLoading(false);
        }
    }, [t]);

    useEffect(() => {
        fetchConfig();
    }, [fetchConfig]);

    const handleProfileSelect = (profile: Profile) => {
        setSelectedProfile(profile);
        if (profile !== "custom" && PROFILE_DEFAULTS[profile]) {
            // Deep merge profile defaults into current config
            const merged = { ...JSON.parse(JSON.stringify(configData)), ...JSON.parse(JSON.stringify(PROFILE_DEFAULTS[profile])) };
            setConfigData(merged);
        }
    };

    const handleParamChange = (path: string[], value: number) => {
        setSelectedProfile("custom");
        setConfigData(setNestedValue(configData, path, value));
    };

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        setSuccess(null);

        try {
            const payload = { ...configData, profile: selectedProfile };
            const newVersion = await createConfigVersion(payload as unknown as Parameters<typeof createConfigVersion>[0]);
            await activateConfig(newVersion.version);
            setSuccess(t("saveSuccess", { version: newVersion.version }));
            await fetchConfig();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : t("saveError");
            setError(msg);
        } finally {
            setSaving(false);
        }
    };

    const handleReset = () => {
        if (config) {
            setConfigData(config.config_json as unknown as Record<string, unknown>);
            const profile = (config.config_json as unknown as Record<string, unknown>).profile;
            if (typeof profile === "string" && ["conservative", "moderate", "aggressive"].includes(profile)) {
                setSelectedProfile(profile as Profile);
            } else {
                setSelectedProfile("custom");
            }
        }
        setError(null);
        setSuccess(null);
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
                    <p className="text-sm text-zinc-400 mt-1">{t("subtitle")}</p>
                </div>
                <Button variant="outline" size="icon" onClick={fetchConfig} disabled={loading}>
                    <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                </Button>
            </div>

            {/* Profile Selector */}
            <GlowCard variant="default">
                <div className="p-6 border-b border-white/5">
                    <h3 className="text-lg font-semibold text-white">{t("profileTitle")}</h3>
                    <p className="text-sm text-zinc-400 mt-1">{t("profileDesc")}</p>
                </div>
                <div className="p-6">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                        {PROFILES.map(({ key, icon: Icon, color, borderColor, glowColor }) => (
                            <button
                                key={key}
                                onClick={() => handleProfileSelect(key)}
                                className={`relative group p-4 rounded-xl border transition-all duration-200 text-left ${selectedProfile === key
                                    ? `bg-linear-to-br ${color} ${borderColor} shadow-lg ${glowColor}`
                                    : "border-white/10 hover:border-white/20 hover:bg-white/5"
                                    }`}
                            >
                                <Icon
                                    className={`h-6 w-6 mb-2 ${selectedProfile === key ? "text-white" : "text-zinc-500"
                                        }`}
                                />
                                <p className={`text-sm font-semibold ${selectedProfile === key ? "text-white" : "text-zinc-300"
                                    }`}>
                                    {t(`profile_${key}`)}
                                </p>
                                <p className="text-xs text-zinc-500 mt-0.5">{t(`profileDesc_${key}`)}</p>
                                {selectedProfile === key && (
                                    <div className="absolute top-2 right-2">
                                        <CheckCircle2 className="h-4 w-4 text-green-400" />
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>
                </div>
            </GlowCard>

            {/* Parameter Sections */}
            <div className="grid gap-6 lg:grid-cols-2">
                {PARAM_SECTIONS.map((section) => (
                    <GlowCard key={section.titleKey} variant="default">
                        <div className="p-6 border-b border-white/5">
                            <h3 className="text-lg font-semibold text-white">{t(section.titleKey)}</h3>
                        </div>
                        <div className="p-6 space-y-5">
                            {section.fields.map((field) => {
                                const value = getNestedValue(configData, field.path);
                                return (
                                    <div key={field.key} className="space-y-2">
                                        <div className="flex items-center justify-between">
                                            <Label className="text-sm text-zinc-300">{t(field.key)}</Label>
                                            <span className="text-sm font-mono text-cyan-400 min-w-[60px] text-right">
                                                {typeof value === "number" ? value.toFixed(field.step && field.step < 1 ? 2 : 0) : value}
                                            </span>
                                        </div>
                                        <input
                                            type="range"
                                            min={field.min ?? 0}
                                            max={field.max ?? 100}
                                            step={field.step ?? 1}
                                            value={value}
                                            onChange={(e) => handleParamChange(field.path, parseFloat(e.target.value))}
                                            className="w-full h-2 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                                        />
                                        <div className="flex justify-between text-xs text-zinc-600">
                                            <span>{field.min ?? 0}</span>
                                            <span>{field.max ?? 100}</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </GlowCard>
                ))}
            </div>

            {/* Status Messages + Actions */}
            <GlowCard variant="default">
                <div className="p-6 space-y-4">
                    {/* Warning */}
                    <div className="bg-amber-500/10 p-3 rounded-lg border border-amber-500/20">
                        <div className="flex items-start gap-2">
                            <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5" />
                            <p className="text-xs text-yellow-600 dark:text-yellow-400">
                                {t("saveWarning")}
                            </p>
                        </div>
                    </div>

                    {error && (
                        <div className="p-3 rounded-md bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-sm">
                            {t("errorPrefix")} {error}
                        </div>
                    )}

                    {success && (
                        <div className="p-3 rounded-md bg-green-500/10 border border-green-500/20 text-green-600 dark:text-green-400 text-sm">
                            {success}
                        </div>
                    )}

                    <div className="flex gap-3">
                        <Button onClick={handleSave} disabled={saving} className="flex-1 sm:flex-none">
                            {saving ? (
                                <>
                                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                                    {t("savingButton")}
                                </>
                            ) : (
                                <>
                                    <Save className="mr-2 h-4 w-4" />
                                    {t("saveButton")}
                                </>
                            )}
                        </Button>
                        <Button variant="outline" onClick={handleReset} disabled={saving}>
                            {t("resetButton")}
                        </Button>
                    </div>
                </div>
            </GlowCard>
        </div>
    );
}
