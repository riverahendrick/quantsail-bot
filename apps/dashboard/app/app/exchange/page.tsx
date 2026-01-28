"use client";

import { useEffect, useState } from "react";
import { getKeys, addKey, revokeKey, ExchangeKey } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Trash2, Plus, RefreshCw, Key } from "lucide-react";
import { useTranslations } from "next-intl";

export default function ExchangePage() {
  const t = useTranslations("ExchangePage");
  const [keys, setKeys] = useState<ExchangeKey[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [label, setLabel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchKeys = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getKeys();
      setKeys(data);
    } catch (err: any) {
      setError(err.message || "Failed to load keys");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleAddKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!label || !apiKey || !secretKey) return;

    setSubmitting(true);
    setError(null);
    try {
      await addKey(label, apiKey, secretKey);
      setLabel("");
      setApiKey("");
      setSecretKey("");
      await fetchKeys();
    } catch (err: any) {
      setError(err.message || "Failed to add key");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRevoke = async (id: string) => {
    if (!confirm(t("revokeConfirm"))) return;
    try {
      await revokeKey(id);
      await fetchKeys();
    } catch (err: any) {
      alert(err.message || "Failed to revoke key");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
        <Button variant="outline" size="icon" onClick={fetchKeys} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Add Key Form */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              {t("addKeyTitle")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAddKey} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="label">{t("labelLabel")}</Label>
                <Input
                  id="label"
                  placeholder="My Binance Key"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  disabled={submitting}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="apiKey">{t("apiKeyLabel")}</Label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder="Paste API Key"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  disabled={submitting}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="secretKey">{t("secretKeyLabel")}</Label>
                <Input
                  id="secretKey"
                  type="password"
                  placeholder="Paste Secret Key"
                  value={secretKey}
                  onChange={(e) => setSecretKey(e.target.value)}
                  disabled={submitting}
                />
              </div>
              {error && <p className="text-sm text-red-500">{error}</p>}
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? t("savingButton") : t("saveButton")}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Existing Keys List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              {t("activeKeysTitle")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {keys.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                {t("noKeys")}
              </div>
            ) : (
              <div className="space-y-4">
                {keys.map((key) => (
                  <div
                    key={key.id}
                    className="flex items-center justify-between p-4 border rounded-lg bg-card/50"
                  >
                    <div>
                      <p className="font-medium">{key.label || "Untitled Key"}</p>
                      <p className="text-xs text-muted-foreground font-mono">
                        ID: {key.id.slice(0, 8)}...
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {key.exchange.toUpperCase()} • v{key.key_version}
                      </p>
                    </div>
                    <Button
                      variant="destructive"
                      size="icon"
                      onClick={() => handleRevoke(key.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}