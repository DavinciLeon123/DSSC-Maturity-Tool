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
  // Sector is an antd <Select>. rc-select renders TWO separate trees for its dropdown: a hidden,
  // zero-size role="listbox"/role="option" shadow copy (height:0; overflow:hidden) that exists
  // purely for accessibility semantics, and the actual visible/clickable rows in a completely
  // separate rc-virtual-list tree as plain <div class="ant-select-item-option" title="...">  with
  // no ARIA role at all. getByRole('option', ...) always matches the hidden shadow node — confirmed
  // by dumping the live DOM (dropdown HTML) locally, not a guess. Target the real virtual-list row
  // by its title attribute instead.
  await page.getByPlaceholder('Enter initiative name').fill('E2E Test Initiative');
  await page.getByRole('combobox').click();
  await page.locator('.ant-select-item-option[title="Healthcare"]').click();
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

    const isLastCategory = categoryPage === 5;
    const buttonName = isLastCategory ? 'Submit assessment →' : 'Next →';
    const nextButton = page.getByRole('button', { name: buttonName });

    // Questions render progressively — querying radiogroups right after only the first one
    // appears can miss ones that mount a beat later (confirmed live: a category with 9
    // questions was sometimes only 8-strong on the first query). Re-query and answer any
    // still-unchecked radiogroup across a few passes until the button the app itself only
    // enables once every question is answered actually reports enabled — the real success
    // signal, rather than trusting a single query pass or a hardcoded count.
    for (let pass = 0; pass < 5 && !(await nextButton.isEnabled()); pass++) {
      const groups = await page.getByRole('radiogroup').all();
      for (const group of groups) {
        const radio = group.getByRole('radio').nth(2);
        if (!(await radio.isChecked())) {
          await radio.click();
        }
      }
    }
    await nextButton.click();
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
