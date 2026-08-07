import { test, expect } from '@playwright/test';

// TEST-03: the one critical-path E2E test this phase requires — register, answer the full
// 52-question assessment, submit, view the report. Runs against the real docker-compose stack
// (see e2e-tests.yml), never mocked. No data-testid exists anywhere in this codebase (confirmed
// via repo-wide grep, 17-RESEARCH.md) — every locator below is role/placeholder/type-attribute
// based, traced directly against the real component source.
test('critical path: register -> answer questionnaire -> submit -> view report', async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;
  const password = 'Str0ngPassw0rd!123';

  // ---- Register --------------------------------------------------------
  await page.goto('/register');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Register' }).click();
  await page.waitForURL('**/login');

  // ---- Login -------------------------------------------------------------
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await page.waitForURL('**/dashboard');

  // ---- Register initiative ------------------------------------------------
  // Sector is an antd <Select>: the visible "Select a sector..." placeholder is a decorative
  // <div>, not the actual click target — an invisible role="combobox" <input> sits on top of it
  // and intercepts pointer events, so clicking the placeholder text times out. Target the
  // combobox itself, matching how Ant Design's own accessibility markup exposes it.
  await page.getByPlaceholder('Enter initiative name').fill('E2E Test Initiative');
  await page.getByRole('combobox').click();
  await page.getByRole('option', { name: 'Healthcare' }).click();
  await page.getByRole('button', { name: 'Register Initiative' }).click();

  // ---- Start the assessment (fresh draft -> straight to /questionnaire, no retake confirm) ---
  await page.getByRole('button', { name: 'Start Dataspace Maturity Assessment' }).click();
  await page.waitForURL('**/questionnaire');

  // ---- Welcome screen (always shown for a fresh draft) -------------------
  await page.getByRole('button', { name: 'Begin assessment →' }).click();

  // ---- Answer all 6 category pages, always the 3rd (middle) option per question ------------
  for (let categoryPage = 0; categoryPage < 6; categoryPage++) {
    // handleNext() is async (awaits a real backend flush before navigating) — wait for the new
    // category's radiogroups to actually render before re-querying, a genuine race otherwise.
    await expect(page.getByRole('radiogroup').first()).toBeVisible();
    const groups = await page.getByRole('radiogroup').all();
    for (const group of groups) {
      await group.getByRole('radio').nth(2).click();
    }
    const isLastCategory = categoryPage === 5;
    const buttonName = isLastCategory ? 'Submit assessment →' : 'Next →';
    await page.getByRole('button', { name: buttonName }).click();
  }

  // ---- Post-submit: generate + view report --------------------------------
  await expect(page.getByText('Thanks for completing the survey.')).toBeVisible();
  await page.getByRole('button', { name: 'Generate heatmap' }).click();
  await page.waitForURL('**/report');

  // ---- Report renders (radar chart + priority list) — structural assertions only; ----------
  // ---- per-row/attribute detail is covered by Plan 17-02's Vitest report.test.tsx. ---------
  await expect(page.getByText('Maturity radar')).toBeVisible();
  await expect(page.getByText('Priority areas')).toBeVisible();
  await expect(page.locator('svg').first()).toBeVisible();
});
