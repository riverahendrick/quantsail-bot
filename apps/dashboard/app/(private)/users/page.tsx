"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createUser,
  listUsers,
  updateUser,
  ManagedUser,
  UserRole,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RefreshCw, UserPlus, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { DASHBOARD_CONFIG } from "@/lib/config";

type UserEdits = Record<string, { role: UserRole; disabled: boolean }>;

export default function UsersPage() {
  const t = useTranslations("UsersPage");

  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [userEdits, setUserEdits] = useState<UserEdits>({});
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusKind, setStatusKind] = useState<"success" | "error" | null>(null);
  const [resetLink, setResetLink] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("ADMIN");
  const [sendResetLink, setSendResetLink] = useState(true);
  const [creating, setCreating] = useState(false);
  const [savingUserId, setSavingUserId] = useState<string | null>(null);
  const [resettingUserId, setResettingUserId] = useState<string | null>(null);

  const seedEdits = (data: ManagedUser[]) => {
    const nextEdits: UserEdits = {};
    data.forEach((user) => {
      nextEdits[user.id] = {
        role: user.role,
        disabled: Boolean(user.disabled),
      };
    });
    setUserEdits(nextEdits);
  };

  const getErrorMessage = (err: unknown, fallback: string) => {
    if (err instanceof Error && err.message) {
      return err.message;
    }
    return fallback;
  };

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setLoadError(null);

    if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
      setUsers([]);
      setUserEdits({});
      setLoading(false);
      return;
    }

    try {
      const data = await listUsers();
      setUsers(data);
      seedEdits(data);
    } catch (err: unknown) {
      setLoadError(getErrorMessage(err, t("loadError")));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setCreating(true);
    setStatusMessage(null);
    setStatusKind(null);
    setResetLink(null);

    try {
      const created = await createUser(email, role, sendResetLink);
      setStatusKind("success");
      setStatusMessage(t("createSuccess"));
      if (created.password_reset_link) {
        setResetLink(created.password_reset_link);
      }
      setEmail("");
      setRole("ADMIN");
      setSendResetLink(true);
      await fetchUsers();
    } catch (err: unknown) {
      setStatusKind("error");
      setStatusMessage(getErrorMessage(err, t("createError")));
    } finally {
      setCreating(false);
    }
  };

  const handleSave = async (user: ManagedUser) => {
    const edits = userEdits[user.id];
    if (!edits) return;

    const updates: { role?: UserRole; disabled?: boolean } = {};
    if (edits.role !== user.role) {
      updates.role = edits.role;
    }
    if (edits.disabled !== Boolean(user.disabled)) {
      updates.disabled = edits.disabled;
    }
    if (Object.keys(updates).length === 0) return;

    setSavingUserId(user.id);
    setStatusMessage(null);
    setStatusKind(null);
    setResetLink(null);

    try {
      await updateUser(user.id, updates);
      setStatusKind("success");
      setStatusMessage(t("updateSuccess"));
      await fetchUsers();
    } catch (err: unknown) {
      setStatusKind("error");
      setStatusMessage(getErrorMessage(err, t("updateError")));
    } finally {
      setSavingUserId(null);
    }
  };

  const handleResetLink = async (user: ManagedUser) => {
    setResettingUserId(user.id);
    setStatusMessage(null);
    setStatusKind(null);
    setResetLink(null);

    try {
      const updated = await updateUser(user.id, { sendResetLink: true });
      setStatusKind("success");
      setStatusMessage(t("resetSuccess"));
      if (updated.password_reset_link) {
        setResetLink(updated.password_reset_link);
      }
    } catch (err: unknown) {
      setStatusKind("error");
      setStatusMessage(getErrorMessage(err, t("resetError")));
    } finally {
      setResettingUserId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <Button variant="outline" size="icon" onClick={fetchUsers} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {statusMessage && (
        <div
          className={`rounded-md border p-4 ${
            statusKind === "error"
              ? "border-red-500/20 bg-red-500/10 text-red-600"
              : "border-green-500/20 bg-green-500/10 text-green-600"
          }`}
        >
          {statusMessage}
        </div>
      )}

      {resetLink && (
        <div className="rounded-md border border-blue-500/20 bg-blue-500/10 p-4 text-blue-700">
          <div className="text-sm font-medium">{t("resetLinkLabel")}</div>
          <div className="break-all font-mono text-sm">{resetLink}</div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5" />
              {t("createTitle")}
            </CardTitle>
            <p className="text-sm text-muted-foreground">{t("createDescription")}</p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="user-email">{t("emailLabel")}</Label>
                <Input
                  id="user-email"
                  type="email"
                  placeholder={t("emailPlaceholder")}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={creating}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="user-role">{t("roleLabel")}</Label>
                <select
                  id="user-role"
                  className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  value={role}
                  onChange={(e) => setRole(e.target.value as UserRole)}
                  disabled={creating}
                >
                  <option value="OWNER">{t("roleOwner")}</option>
                  <option value="CEO">{t("roleCeo")}</option>
                  <option value="DEVELOPER">{t("roleDeveloper")}</option>
                  <option value="ADMIN">{t("roleAdmin")}</option>
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={sendResetLink}
                  onChange={(e) => setSendResetLink(e.target.checked)}
                  disabled={creating}
                />
                {t("sendResetLink")}
              </label>
              <Button type="submit" className="w-full" disabled={creating}>
                {creating ? t("creatingButton") : t("createButton")}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              {t("listTitle")}
            </CardTitle>
            <p className="text-sm text-muted-foreground">{t("listDescription")}</p>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-sm text-muted-foreground">{t("loading")}</div>
            ) : loadError ? (
              <div className="text-sm text-red-500">{loadError}</div>
            ) : users.length === 0 ? (
              <div className="text-sm text-muted-foreground">{t("empty")}</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("tableEmail")}</TableHead>
                    <TableHead>{t("tableRole")}</TableHead>
                    <TableHead>{t("tableStatus")}</TableHead>
                    <TableHead className="text-right">{t("tableActions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => {
                    const edits = userEdits[user.id] || {
                      role: user.role,
                      disabled: Boolean(user.disabled),
                    };
                    const isSaving = savingUserId === user.id;
                    const isResetting = resettingUserId === user.id;
                    return (
                      <TableRow key={user.id}>
                        <TableCell className="font-mono text-xs">{user.email}</TableCell>
                        <TableCell>
                          <select
                            className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                            value={edits.role}
                            onChange={(e) =>
                              setUserEdits((prev) => ({
                                ...prev,
                                [user.id]: {
                                  role: e.target.value as UserRole,
                                  disabled: edits.disabled,
                                },
                              }))
                            }
                          >
                            <option value="OWNER">{t("roleOwner")}</option>
                            <option value="CEO">{t("roleCeo")}</option>
                            <option value="DEVELOPER">{t("roleDeveloper")}</option>
                            <option value="ADMIN">{t("roleAdmin")}</option>
                          </select>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={edits.disabled}
                              onChange={(e) =>
                                setUserEdits((prev) => ({
                                  ...prev,
                                  [user.id]: {
                                    role: edits.role,
                                    disabled: e.target.checked,
                                  },
                                }))
                              }
                            />
                            {edits.disabled ? t("statusDisabled") : t("statusActive")}
                          </div>
                        </TableCell>
                        <TableCell className="text-right space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleSave(user)}
                            disabled={isSaving}
                          >
                            {isSaving ? t("savingButton") : t("saveButton")}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleResetLink(user)}
                            disabled={isResetting}
                          >
                            {t("resetButton")}
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
