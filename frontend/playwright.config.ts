import { defineConfig } from "@playwright/test";

// runs against the real stack: fastapi on :8000 + built next app on :3000.
// servers already running are reused; missing ones are started briefly.
// sqlite would be hermetic, but dev-mode hydration races make next start
// (prebuilt, instant hydration) the stable choice — tests use unique orgs.
export default defineConfig({
  testDir: "tests/e2e",
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: "http://localhost:3000",
    actionTimeout: 30_000,
    navigationTimeout: 60_000,
  },
  webServer: [
    {
      command: "..\\backend\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000",
      url: "http://localhost:8000/health",
      cwd: "..\\backend",
      reuseExistingServer: true,
      timeout: 90_000,
    },
    {
      command: "npx next start -p 3000",
      url: "http://localhost:3000/login",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
