import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:3000",
  },
  webServer: {
    command: "pnpm dev",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      PORT: "3000",
      NEXT_PUBLIC_USE_MOCK_DATA: "true",
    },
  },
});
