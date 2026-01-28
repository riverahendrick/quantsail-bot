const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const DASHBOARD_CONFIG = {
  // Set to true ONLY for local development without backend or specific testing
  // In tests, we likely want this true OR mock the network requests at the Playwright level.
  USE_MOCK_DATA:
    process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true" ||
    process.env.NODE_ENV === "test",

  // Public API URL
  API_URL: apiUrl,

  // Public WS URL
  WS_URL: process.env.NEXT_PUBLIC_WS_URL || `${apiUrl.replace(/^http/, "ws")}/ws`,
};
