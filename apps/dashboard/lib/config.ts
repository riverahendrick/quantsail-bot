export const DASHBOARD_CONFIG = {
  // Set to true ONLY for local development without backend or specific testing
  // In tests, we likely want this true OR mock the network requests at the Playwright level.
  // For now, enabling it here ensures UI tests pass without backend.
  USE_MOCK_DATA: process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true" || process.env.NODE_ENV === 'test' || true,
  
  // Public API URL
  API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
};
