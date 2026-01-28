import { auth } from "./firebase";
import { DASHBOARD_CONFIG } from "./config";

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
  // If Mock Data is forced true and we are in early dev, maybe return mocks?
  // GLOBAL_RULES says "Never use mock data" except behind toggle.
  // We assume the caller handles the toggle logic or we pass it through.
  // Ideally, the backend is running.
  
  const headers = await getHeaders();
  const url = `${DASHBOARD_CONFIG.API_URL}${endpoint}`;
  
  const res = await fetch(url, {
    ...options,
    headers: { ...headers, ...options.headers },
  });

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
    strategies: any;
    execution: any;
    risk: any;
    symbols: any;
    breakers: any;
    daily: any;
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
    return fetchPrivate<any[]>("/v1/events");
}
