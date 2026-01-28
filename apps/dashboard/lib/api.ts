import { auth } from "./firebase";
import { DASHBOARD_CONFIG } from "./config";

// Mock data responses for development (only used when explicitly enabled)
function getMockResponse<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // Return empty responses - no mock data
  const mocks: Record<string, unknown> = {
    "/v1/users": [],
    "/v1/events": [],
    "/v1/exchanges/binance/keys/status": { keys: [] }
  };

  return Promise.resolve((mocks[endpoint] || {}) as T);
}

async function getHeaders() {
  const user = auth.currentUser;
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (user) {
    const token = await user.getIdToken();
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function fetchPrivate<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // If Mock Data is enabled, return mock responses
  if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
    return getMockResponse<T>(endpoint, options);
  }
  
  const headers = await getHeaders();
  const url = `${DASHBOARD_CONFIG.API_URL}${endpoint}`;
  
  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers: { ...headers, ...options.headers },
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown network error";
    throw new Error(`Network error calling ${url}. Is the API running and reachable? ${message}`);
  }

  if (!res.ok) {
      const errorText = await res.text();
      let errorJson;
      try {
          errorJson = JSON.parse(errorText);
      } catch {
          errorJson = {};
      }
      throw new Error(errorJson.detail?.message || errorJson.detail || `API Error ${res.status}: ${errorText}`);
  }
  
  return res.json() as Promise<T>;
}

// --- Config ---

export interface BotConfig {
    strategies: Record<string, unknown>;
    execution: Record<string, unknown>;
    risk: Record<string, unknown>;
    symbols: Record<string, unknown>;
    breakers: Record<string, unknown>;
    daily: Record<string, unknown>;
}

export interface ConfigVersion {
    version: number;
    config_hash: string;
    is_active: boolean;
    created_at: string;
    config_json: BotConfig;
}

export async function getBotConfig() {
    return fetchPrivate<ConfigVersion>("/v1/config");
}

export async function createConfigVersion(config: BotConfig) {
    return fetchPrivate<ConfigVersion>("/v1/config/versions", {
        method: "POST",
        body: JSON.stringify({ config_json: config }),
    });
}

export async function activateConfig(version: number) {
    return fetchPrivate(`/v1/config/activate/${version}`, {
        method: "POST",
    });
}

// --- Exchange Keys ---

export interface ExchangeKey {
    id: string;
    exchange: string;
    label: string | null;
    key_version: number;
    created_at: string;
    revoked_at: string | null;
    is_active: boolean;
}

export async function getKeys() {
    return fetchPrivate<ExchangeKey[]>("/v1/exchanges/binance/keys/status");
}

export async function addKey(label: string, apiKey: string, secretKey: string) {
    return fetchPrivate<ExchangeKey>("/v1/exchanges/binance/keys", {
        method: "POST",
        body: JSON.stringify({ label, api_key: apiKey, secret_key: secretKey }),
    });
}

export async function revokeKey(id: string) {
    return fetchPrivate(`/v1/exchanges/binance/keys/${id}`, {
        method: "DELETE",
    });
}

export async function updateKey(id: string, updates: { label?: string; api_key?: string; secret_key?: string }) {
    return fetchPrivate<ExchangeKey>(`/v1/exchanges/binance/keys/${id}`, {
        method: "PATCH",
        body: JSON.stringify(updates),
    });
}

export async function activateKey(id: string) {
    return fetchPrivate(`/v1/exchanges/binance/keys/${id}/activate`, {
        method: "POST",
    });
}

// --- Users (Owner Only) ---

export type UserRole = "OWNER" | "CEO" | "DEVELOPER" | "ADMIN";

export interface ManagedUser {
    id: string;
    email: string;
    role: UserRole;
    created_at: string;
    disabled?: boolean | null;
    password_reset_link?: string | null;
}

export async function listUsers() {
    return fetchPrivate<ManagedUser[]>("/v1/users");
}

export async function createUser(email: string, role: UserRole, sendResetLink: boolean) {
    return fetchPrivate<ManagedUser>("/v1/users", {
        method: "POST",
        body: JSON.stringify({ email, role, send_reset_link: sendResetLink }),
    });
}

export async function updateUser(
    id: string,
    updates: { role?: UserRole; disabled?: boolean; sendResetLink?: boolean }
) {
    return fetchPrivate<ManagedUser>(`/v1/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
            role: updates.role,
            disabled: updates.disabled,
            send_reset_link: updates.sendResetLink,
        }),
    });
}

// --- Bot Control ---

export interface ArmResponse {
    arming_token: string;
    expires_in_seconds: number;
}

export async function armBot() {
    return fetchPrivate<ArmResponse>("/v1/bot/arm", { method: "POST" });
}

export async function startBot(mode: "dry-run" | "live", armingToken?: string) {
    return fetchPrivate("/v1/bot/start", {
        method: "POST",
        body: JSON.stringify({ mode, arming_token: armingToken }),
    });
}

export async function stopBot() {
    return fetchPrivate("/v1/bot/stop", { method: "POST" });
}

export async function pauseEntries() {
    return fetchPrivate("/v1/bot/pause_entries", { method: "POST" });
}

export async function resumeEntries() {
    return fetchPrivate("/v1/bot/resume_entries", { method: "POST" });
}

// --- Data ---

export async function getPrivateEvents() {
    return fetchPrivate<unknown[]>("/v1/events");
}
