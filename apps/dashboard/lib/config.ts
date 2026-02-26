const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const DASHBOARD_CONFIG = {
  // Demo mode: bypasses auth, forces mock data. Used for Vercel deployments without backend.
  DEMO_MODE: process.env.NEXT_PUBLIC_DEMO_MODE === "true",

  // Set to true ONLY for local development without backend or specific testing
  USE_MOCK_DATA:
    process.env.NEXT_PUBLIC_DEMO_MODE === "true" ||
    process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true" ||
    process.env.NODE_ENV === "test",

  // Public API URL
  API_URL: apiUrl,

  // Public WS URL
  WS_URL: process.env.NEXT_PUBLIC_WS_URL || `${apiUrl.replace(/^http/, "ws")}/ws`,
};
