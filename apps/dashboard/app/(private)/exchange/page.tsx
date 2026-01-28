"use client";

import { useCallback, useEffect, useState } from "react";
import { getKeys, addKey, revokeKey, updateKey, activateKey, ExchangeKey } from "@/lib/api";
import { GlowCard } from "@/components/ui/glow-card";
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
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusKind, setStatusKind] = useState<"success" | "error" | null>(null);

  // Form state
  const [label, setLabel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [editingKeyId, setEditingKeyId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState("");
  const [editApiKey, setEditApiKey] = useState("");
  const [editSecretKey, setEditSecretKey] = useState("");
  const [updating, setUpdating] = useState(false);

  const fetchKeys = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getKeys();
      setKeys(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("loadError");
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleAddKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!label || !apiKey || !secretKey) return;

    setSubmitting(true);
    setError(null);
    setStatusMessage(null);
    setStatusKind(null);
    try {
      await addKey(label, apiKey, secretKey);
      setLabel("");
      setApiKey("");
      setSecretKey("");
      await fetchKeys();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("addError");
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRevoke = async (id: string) => {
    if (!confirm(t("revokeConfirm"))) return;
    try {
      await revokeKey(id);
      await fetchKeys();
    } catch (err: unknown) {
      setStatusKind("error");
      const msg = err instanceof Error ? err.message : t("revokeError");
      setStatusMessage(msg);
    }
  };

  const handleActivate = async (id: string) => {
    setStatusMessage(null);
    setStatusKind(null);
    try {
      await activateKey(id);
      setStatusKind("success");
      setStatusMessage(t("activateSuccess"));
      await fetchKeys();
    } catch (err: unknown) {
      setStatusKind("error");
      const msg = err instanceof Error ? err.message : t("activateError");
      setStatusMessage(msg);
    }
  };

  const startEdit = (key: ExchangeKey) => {
    setEditingKeyId(key.id);
    setEditLabel(key.label || "");
    setEditApiKey("");
    setEditSecretKey("");
  };

  const cancelEdit = () => {
    setEditingKeyId(null);
    setEditLabel("");
    setEditApiKey("");
    setEditSecretKey("");
  };

  const handleUpdate = async (id: string) => {
    setUpdating(true);
    setStatusMessage(null);
    setStatusKind(null);
    try {
      const updates: { label?: string; api_key?: string; secret_key?: string } = {};
      if (editLabel) updates.label = editLabel;
      if (editApiKey || editSecretKey) {
        updates.api_key = editApiKey;
        updates.secret_key = editSecretKey;
      }
      await updateKey(id, updates);
      setStatusKind("success");
      setStatusMessage(t("updateSuccess"));
      cancelEdit();
      await fetchKeys();
    } catch (err: unknown) {
      setStatusKind("error");
      const msg = err instanceof Error ? err.message : t("updateError");
      setStatusMessage(msg);
    } finally {
      setUpdating(false);
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

      {statusMessage && (
        <div className={`p-4 rounded-md border ${statusKind === "error" ? "bg-red-500/10 border-red-500/20 text-red-600" : "bg-green-500/10 border-green-500/20 text-green-600"}`}>
          {statusMessage}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {/* Add Key Form */}
        <GlowCard variant="default">
          <div className="p-6 border-b border-white/5">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Plus className="h-5 w-5 text-cyan-400" />
              {t("addKeyTitle")}
            </h3>
          </div>
          <div className="p-6">
            <form onSubmit={handleAddKey} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="label">{t("labelLabel")}</Label>
                <Input
                  id="label"
                  placeholder={t("labelPlaceholder")}
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
                  placeholder={t("apiKeyPlaceholder")}
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
                  placeholder={t("secretKeyPlaceholder")}
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
          </div>
        </GlowCard>

        {/* Existing Keys List */}
        <GlowCard variant="default">
          <div className="p-6 border-b border-white/5">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Key className="h-5 w-5 text-violet-400" />
              {t("activeKeysTitle")}
            </h3>
          </div>
          <div className="p-6">
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
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{key.label || t("untitledKey")}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${key.is_active ? "border-green-500/30 text-green-600 bg-green-500/10" : "border-muted text-muted-foreground"}`}>
                          {key.is_active ? t("activeLabel") : t("inactiveLabel")}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground font-mono">
                        {t("idLabel")} {key.id.slice(0, 8)}{t("Common.ellipsis")}
                      </p>
                      <div className="text-xs text-muted-foreground flex items-center gap-2">
                        <span>{key.exchange.toUpperCase()}</span>
                        <span className="border-r border-muted-foreground/50 h-3" />
                        <span>{t("versionLabel", { v: key.key_version })}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {!key.is_active && (
                        <Button variant="outline" size="sm" onClick={() => handleActivate(key.id)}>
                          {t("activateButton")}
                        </Button>
                      )}
                      <Button variant="outline" size="sm" onClick={() => startEdit(key)}>
                        {t("editButton")}
                      </Button>
                      <Button
                        variant="destructive"
                        size="icon"
                        onClick={() => handleRevoke(key.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
                {editingKeyId && (
                  <div className="p-4 rounded-xl bg-white/[0.05] border border-white/10 space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="edit-label">{t("editLabel")}</Label>
                      <Input
                        id="edit-label"
                        placeholder={t("labelPlaceholder")}
                        value={editLabel}
                        onChange={(e) => setEditLabel(e.target.value)}
                        disabled={updating}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="edit-api">{t("apiKeyLabel")}</Label>
                      <Input
                        id="edit-api"
                        type="password"
                        placeholder={t("apiKeyPlaceholder")}
                        value={editApiKey}
                        onChange={(e) => setEditApiKey(e.target.value)}
                        disabled={updating}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="edit-secret">{t("secretKeyLabel")}</Label>
                      <Input
                        id="edit-secret"
                        type="password"
                        placeholder={t("secretKeyPlaceholder")}
                        value={editSecretKey}
                        onChange={(e) => setEditSecretKey(e.target.value)}
                        disabled={updating}
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <Button onClick={() => handleUpdate(editingKeyId)} disabled={updating}>
                        {updating ? t("updatingButton") : t("updateButton")}
                      </Button>
                      <Button variant="outline" onClick={cancelEdit} disabled={updating}>
                        {t("cancelButton")}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </GlowCard>
      </div>
    </div>
  );
}
