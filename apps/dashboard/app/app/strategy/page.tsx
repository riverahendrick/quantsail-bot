"use client";

import { useEffect, useState } from "react";
import { getBotConfig, createConfigVersion, activateConfig, ConfigVersion } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Save, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";
import { useTranslations } from "next-intl";

export default function StrategyPage() {
  const t = useTranslations("StrategyPage");
  const [config, setConfig] = useState<ConfigVersion | null>(null);
  const [jsonInput, setJsonInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getBotConfig();
      setConfig(data);
      setJsonInput(JSON.stringify(data.config_json, null, 2));
    } catch (err: any) {
      if (err.message.includes("No active config")) {
        // First run or empty DB
        setJsonInput("{\n  \"strategies\": {},\n  \"execution\": {},\n  \"risk\": {},\n  \"symbols\": {},\n  \"breakers\": {},\n  \"daily\": {}\n}");
      } else {
        setError(err.message || "Failed to load config");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      // 1. Validate JSON
      let parsed;
      try {
        parsed = JSON.parse(jsonInput);
      } catch (e) {
        throw new Error("Invalid JSON format");
      }

      // 2. Create Version
      const newVersion = await createConfigVersion(parsed);

      // 3. Activate Version
      await activateConfig(newVersion.version);

      setSuccess(`Version ${newVersion.version} created and activated!`);
      await fetchConfig();

    } catch (err: any) {
      setError(err.message || "Failed to save config");
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
        <Card className="lg:col-span-1 h-fit">
          <CardHeader>
            <CardTitle>{t("activeVersionTitle")}</CardTitle>
            <CardDescription>{t("activeVersionDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {config ? (
              <>
                <div className="flex justify-between items-center border-b pb-2">
                  <span className="text-sm font-medium text-muted-foreground">{t("version")}</span>
                  <span className="font-mono text-lg font-bold">v{config.version}</span>
                </div>
                <div className="flex justify-between items-center border-b pb-2">
                  <span className="text-sm font-medium text-muted-foreground">{t("hash")}</span>
                  <span className="font-mono text-xs truncate max-w-[120px]" title={config.config_hash}>
                    {config.config_hash.slice(0, 8)}...
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
            
            <div className="bg-yellow-500/10 p-3 rounded-md border border-yellow-500/20">
               <div className="flex items-start gap-2">
                 <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5" />
                 <p className="text-xs text-yellow-600 dark:text-yellow-400">
                   {t("immutableNote")}
                 </p>
               </div>
            </div>
          </CardContent>
        </Card>

        {/* Editor */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>{t("editorTitle")}</CardTitle>
            <CardDescription>{t("editorDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="json-editor">Config JSON</Label>
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
                Error: {error}
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
          </CardContent>
        </Card>
      </div>
    </div>
  );
}