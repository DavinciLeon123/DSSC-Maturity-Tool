# Phase 17: Test Coverage — New Scoring, Questionnaire & Visualization Logic + E2E - Context

**Gathered:** 2026-08-04
**Status:** Ready for planning

<domain>
## Phase Boundary

The rebuilt scoring engine, questionnaire API, wizard, and report rendering get automated test coverage, and a Playwright suite verifies the critical end-to-end path (register → answer questionnaire → submit → view report). This phase does NOT add new product capabilities — it closes coverage gaps and stands up E2E infrastructure that doesn't exist yet.

</domain>

<decisions>
## Implementation Decisions

### Backend coverage (TEST-01)
- Phases 12-16 already left substantial backend test coverage behind as a side effect of their own plans: `test_dimension_scoring.py` (13 tests incl. all-1s/all-5s edge cases), `test_scoring.py`, `test_questionnaire.py` / `test_questionnaire_answers.py` (17 tests), `test_reports.py` (18 tests), `test_auth.py` (15 tests, from Phase 12).
- Phase 17's backend job is **audit + gap-fill, not a rewrite**: read existing tests against TEST-01's three named areas (scoring engine, questionnaire API, auth flows), identify what's genuinely missing, write only the tests that close real gaps.
- No specific known bugs/pain points to target — trust the audit to surface gaps organically (no pre-briefed edge cases beyond what TEST-01 already names).
- Go straight from audit to writing tests — no separate gap-list review checkpoint with the user before test code is written.
- **Auth scope is extended, not just re-verified**: Phase 12's `test_auth.py` covered register/login/lockout/password-reset against the *old* app shape. Phase 17 must also confirm auth is correctly enforced on the *new, rebuilt* surfaces — e.g. expired/invalid tokens correctly rejected on the new questionnaire-answer and report endpoints, not just the endpoints Phase 12 originally covered.
- No coverage-percentage gate is being introduced on the backend in this phase — coverage is about existence/correctness of tests, not enforcing a numeric threshold.

### Frontend coverage (TEST-02)
- Frontend currently has near-zero test coverage (only `TopNav.test.tsx`) despite Vitest + RTL + jsdom already being installed and wired into CI (`frontend-test` job in pr.yml/staging.yml/main.yml already runs `vitest run --coverage`).
- **Priority is weighted, not even**: `useDebouncedSave` (save/retry/state-machine logic) and `report.tsx` (radar + priority list rendering) get real coverage first — they map directly to TEST-02's literal wording ("wizard's save/state logic" and "the report's rendering"). `WizardPage`'s orchestration/navigation and presentational components (`StepPills`, `QuestionCard`, `WelcomeScreen`, `SubsectionLabel`, `AnswerButtonGroup`) get lighter or no coverage in this phase.
- **Mocking strategy**: manual `vi.mock()` on the `lib/*.ts` modules (e.g. mock `saveAnswer` from `lib/questionnaire.ts`, `fetchReportData` from `lib/reports.ts`) — no MSW. Matches the small scale of this frontend and avoids adding a new dependency for a codebase with no test culture yet.
- **Timers**: `useDebouncedSave` tests use Vitest fake timers (`vi.useFakeTimers()` + `vi.advanceTimersByTime()`) to simulate the 1.5s debounce and `[1s, 2s, 4s]` retry backoff instantly — not real waits.
- **Radar chart testing**: data-driven assertions only (right number of axes/points, band colors match the priority list) — no full-markup/SVG snapshot testing (generated SVG paths make bad, unreviewable diffs).
- No frontend coverage-percentage gate is being added — `vitest run --coverage` stays informational (matches current CI behavior; no new gate type introduced in this phase).

### Playwright E2E (TEST-03)
- **Environment**: run the existing `docker-compose.yml` (db + backend + frontend) inside a CI job and point Playwright at `localhost` — not against dev servers, not against the live Railway Integration deployment. Self-contained and exercises the same built-image topology that ships.
- **Image reuse**: the E2E job depends on `staging.yml`'s/`main.yml`'s existing `docker-build` job and pulls the already-built `:staging`/images from `ghcr.io` rather than rebuilding via `docker compose up --build` — avoids building the same images twice in one workflow run and tests the exact images that would ship.
- **Test data**: fresh, freshly-migrated empty database per run; the E2E test itself drives the real registration flow through the UI (not a pre-seeded user) — this matches TEST-03's literal wording ("register → answer questionnaire → submit → view report") and means the "register" step is actually exercised, not skipped.
- **Browser matrix**: Chromium only. This is critical-path E2E, not cross-browser compatibility testing; extend later only if a browser-specific bug ever surfaces.
- **Report verification scope**: assert the in-app report view renders (radar chart + priority list) after submit — do NOT also click through to PDF download/email delivery in this E2E test. PDF generation and email delivery already have backend regression coverage from Phase 12 (`test_reports.py` / report_generator tests); re-verifying that through the browser would be redundant with already-covered territory.
- **Failure debugging**: Playwright's built-in `trace: 'retain-on-failure'` plus screenshot-on-failure, uploaded as a workflow artifact on failure — standard setup so a CI failure is debuggable without local repro.

### CI gating strategy
- **E2E does NOT block PRs.** It's added to `staging.yml` and `main.yml` only, mirroring the existing `benchmark`-marker precedent (excluded from `pr.yml` to keep PR feedback fast, included from `staging` onward so regressions are still caught before they reach a protected/shared branch). This means a broken critical path is caught on merge to `staging`, not before — an explicit tradeoff the user chose over the "PR-blocking" default option.
- No new coverage-percentage CI gate anywhere (backend or frontend) — this phase is about tests existing and passing, not about introducing a new enforcement mechanism.

### Claude's Discretion
- Exact list of backend gap-fill tests (the audit's findings) — not pre-specified, subject to "trust the audit."
- Whether the new E2E job lives as a new job within `staging.yml`/`main.yml` or a new workflow file included by them — implementation detail.
- Playwright config specifics (test file layout, fixtures, retry count for flaky-test tolerance in CI) not covered above.
- Exact frontend test file organization/naming.

</decisions>

<specifics>
## Specific Ideas

No specific product references or "make it feel like X" moments — this is a pure test-infrastructure phase. The one clear precedent to follow is this repo's own existing `perf`/`benchmark` marker pattern (documented in CLAUDE.md) for keeping PR feedback fast while still gating shared branches — the user explicitly extended that same pattern to E2E rather than blocking every PR.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/tests/conftest.py` — existing testcontainers Postgres + lifespan-aware TestClient + factories pattern (from Phase 12); new backend gap-fill tests should follow this, not invent a new fixture style.
- `frontend/vitest.config.ts` + `frontend/src/test/setup.ts` — Vitest/RTL/jsdom already wired; `TopNav.test.tsx` is the only existing example of the test style to follow.
- `docker-compose.yml` (root) — full stack (db/backend/frontend) already defined and buildable; this is what the E2E job will run against.
- `.github/workflows/staging.yml` / `main.yml` — already have a `docker-build` job producing `:staging`/tagged images pushed to `ghcr.io`; the new E2E job should depend on and reuse these rather than rebuilding.

### Established Patterns
- `perf`/`benchmark` pytest markers (backend/pyproject.toml) + their differential inclusion across `pr.yml` (excluded) vs `staging.yml`/`main.yml` (included) — the precedent the user chose to replicate for Playwright E2E gating.
- `frontend-test` job already exists in all three quality-gate workflows (`pr.yml`, `staging.yml`, `main.yml`) running `npx vitest run --coverage` — coverage is collected for visibility but nothing currently fails below a threshold; Phase 17 keeps that as-is.

### Integration Points
- Backend gap-fill tests land in the existing `backend/tests/api/`, `backend/tests/services/` structure (test_scoring.py, test_questionnaire_answers.py, test_auth.py, etc. already exist there).
- New frontend tests land alongside `useDebouncedSave.ts` and `report.tsx` (or in a co-located/`__tests__` structure matching whatever `TopNav.test.tsx` already establishes).
- New Playwright suite is a greenfield addition — no existing `playwright.config.ts` or e2e test directory anywhere in the repo yet.
- New E2E CI job is added to `.github/workflows/staging.yml` and `.github/workflows/main.yml`, positioned after (depending on) the existing `docker-build` job.

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. No new product capabilities were proposed during this discussion.

</deferred>

---

*Phase: 17-test-coverage-new-scoring-questionnaire-visualization-logic-e2e*
*Context gathered: 2026-08-04*
