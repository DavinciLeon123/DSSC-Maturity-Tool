import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: 90_000, // generous: 52 questions across 6 category pages, each awaiting a real backend flush on Next/Submit
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  // No webServer block — the CI job's own docker-compose + wait-on steps already guarantee
  // readiness before `playwright test` runs (see e2e-tests.yml); Playwright's own webServer.command
  // is a required field and awkward to use purely as a "wait for an already-running server" check.
});
