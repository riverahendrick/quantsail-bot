"use client";

import { useCallback, useEffect, useState } from "react";
import { getBotConfig, createConfigVersion, activateConfig, ConfigVersion } from "@/lib/api";
import { GlowCard } from "@/components/ui/glow-card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Save, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { StrategyPerformanceWidget } from "@/components/dashboard/strategy-performance-widget";

export default function StrategyPage() {
  const t = useTranslations("StrategyPage");
  const [config, setConfig] = useState<ConfigVersion | null>(null);
  const [jsonInput, setJsonInput] = useState("");
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
      setJsonInput(JSON.stringify(data.config_json, null, 2));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("loadError");
      if (msg.includes("No active config")) {
        // First run or empty DB
        setJsonInput("{\n  \"strategies\": {},\n  \"execution\": {},\n  \"risk\": {},\n  \"symbols\": {},\n  \"breakers\": {},\n  \"daily\": {}\n}");
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      // 1. Validate JSON
      let parsed;
      try {
        parsed = JSON.parse(jsonInput);
      } catch {
        throw new Error(t("invalidJson"));
      }

      // 2. Create Version
      const newVersion = await createConfigVersion(parsed);

      // 3. Activate Version
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
        <Button variant="outline" size="icon" onClick={fetchConfig} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Status Card */}
        <GlowCard variant="default" className="lg:col-span-1 h-fit">
          <div className="p-6 border-b border-white/5">
            <h3 className="text-lg font-semibold text-white">{t("activeVersionTitle")}</h3>
            <p className="text-sm text-zinc-400 mt-1">{t("activeVersionDesc")}</p>
          </div>
          <div className="p-6 space-y-4">
            {config ? (
              <>
                <div className="flex justify-between items-center border-b pb-2">
                  <span className="text-sm font-medium text-muted-foreground">{t("version")}</span>
                  <span className="font-mono text-lg font-bold">{t("versionLabel", { v: config.version })}</span>
                </div>
                <div className="flex justify-between items-center border-b pb-2">
                  <span className="text-sm font-medium text-muted-foreground">{t("hash")}</span>
                  <span className="font-mono text-xs truncate max-w-[120px]" title={config.config_hash}>
                    {config.config_hash.slice(0, 8)}{t("Common.ellipsis")}
                  </span>
                </div>
                <div className="flex justify-between items-center border-b pb-2">
                  <span className="text-sm font-medium text-muted-foreground">{t("created")}</span>
                  <span className="text-sm">{new Date(config.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-muted-foreground">{t("status")}</span>
                  <div className="flex items-center text-green-500 gap-1">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="text-sm font-bold">{t("active")}</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-muted-foreground text-sm">{t("noActiveConfig")}</div>
            )}

            <div className="bg-amber-500/10 p-3 rounded-lg border border-amber-500/20">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5" />
                <p className="text-xs text-yellow-600 dark:text-yellow-400">
                  {t("immutableNote")}
                </p>
              </div>
            </div>
          </div>
        </GlowCard>

        {/* Editor */}
        <GlowCard variant="default" className="lg:col-span-2">
          <div className="p-6 border-b border-white/5">
            <h3 className="text-lg font-semibold text-white">{t("editorTitle")}</h3>
            <p className="text-sm text-zinc-400 mt-1">{t("editorDesc")}</p>
          </div>
          <div className="p-6 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="json-editor">{t("configJsonLabel")}</Label>
              <Textarea
                id="json-editor"
                className="font-mono text-xs min-h-[500px]"
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                spellCheck={false}
              />
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

            <Button onClick={handleSave} disabled={saving} className="w-full sm:w-auto">
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
          </div>
        </GlowCard>
      </div>

      {/* Strategy Performance Metrics */}
      <StrategyPerformanceWidget />
    </div>
  );
}
