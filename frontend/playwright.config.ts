import { defineConfig, devices } from "@playwright/test";

const backendCmd = process.env.E2E_BACKEND_CMD ?? "python -m uvicorn app.main:app --port 8000";
const reuse = !process.env.CI;

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: { baseURL: "http://localhost:3000", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] }, grep: /@mobile/ },
  ],
  webServer: [
    {
      command: backendCmd,
      cwd: "../backend",
      url: "http://localhost:8000/health",
      reuseExistingServer: reuse,
      timeout: 60_000,
      env: {
        DATABASE_URL: "sqlite+aiosqlite:///./data/e2e.db",
        DEMO_MODE: "true",
        APP_ENV: "dev",
        CORS_ORIGINS: "http://localhost:3000",
        RATE_LIMIT_PER_MINUTE: "1000",
        AUTH_RATE_LIMIT_PER_MINUTE: "200",
      },
    },
    {
      command: "npm run start",
      url: "http://localhost:3000/en",
      reuseExistingServer: reuse,
      timeout: 60_000,
    },
  ],
});
