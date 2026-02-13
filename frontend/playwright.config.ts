import { defineConfig, devices } from '@playwright/test';

const backendCommand =
  process.env.PLAYWRIGHT_BACKEND_CMD ??
  'DEMO_FORCE_FALLBACK=1 ../venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000';

/**
 * Playwright configuration for Mini-Lakebed Demo E2E tests.
 *
 * Tests run against the local frontend (port 5173) and backend (port 8000).
 * Both servers must be running before executing tests.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // Run sequentially to avoid session conflicts
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Single worker to ensure session isolation
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report' }]
  ],

  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  /* Configure timeouts */
  timeout: 60000, // 60s per test (LLM responses can be slow)
  expect: {
    timeout: 30000, // 30s for expect assertions
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Run local servers before starting tests */
  webServer: [
    {
      command: backendCommand,
      cwd: '../backend',
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  ],
});
