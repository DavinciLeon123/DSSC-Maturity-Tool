# Phase 17: Test Coverage — New Scoring, Questionnaire & Visualization Logic + E2E - Research

**Researched:** 2026-08-05
**Domain:** Test infrastructure — pytest gap-fill (backend), Vitest+RTL (frontend), Playwright E2E + Docker Compose CI
**Confidence:** HIGH (backend/frontend architecture facts — all verified by direct source read); MEDIUM (Playwright/CI ecosystem specifics — web-verified, cross-referenced 2+ sources, dated Jul–Aug 2026)

## Summary

This phase adds no product code — it closes three coverage gaps (TEST-01/02/03) in an existing, already-substantial test setup. The single most important discovery is architectural, not procedural: **the "radar chart" is not a chart library at all.** `backend/app/services/report_generator.py::generate_radar_svg` hand-builds an SVG string server-side; the frontend's `report.tsx` injects it verbatim via `dangerouslySetInnerHTML`. There is no recharts/visx/nivo/d3 anywhere in `frontend/package.json`. This changes the entire frontend-testing shape for RPRT-01: report.tsx tests never touch chart-math, only (a) that the given SVG string lands in the DOM and (b) that the priority list renders the contract's fields correctly — both pure data-driven DOM assertions against a mocked `fetchReportData` response.

The second major discovery is that `frontend/src/routes/_app/report.tsx`'s `ReportPage` function is **not exported** (only the TanStack Router `Route` object is) — unlike the one existing precedent, `TopNav.tsx`, which does `export function TopNav()`. Writing `report.test.tsx` requires first adding `export` to `function ReportPage()` (and, only if a plan wants to unit-test it in isolation, to `PriorityRow`) — a trivial, safe, one-line prerequisite that must happen before or alongside the test, following the codebase's own established convention.

The third major discovery is a real gap in CONTEXT.md's own premise for the Playwright CI plumbing: `staging.yml`'s `docker-build` job pushes `:staging`-tagged images to `ghcr.io`, but `main.yml`'s `docker-build-and-sbom` job does **not** — it builds with `push: false, load: true`, so the images only ever exist in that one job's local Docker daemon, tagged `mami-checker-*:main-${{ github.sha }}`, never in a registry. CONTEXT.md's plan ("pulls the already-built `:staging`/images from ghcr.io") is accurate for `staging.yml` but does not work as stated for `main.yml`. See Architecture Patterns and Common Pitfalls for the concrete fix.

Finally, there is a standing, explicit, three-times-repeated obligation in `CLAUDE.md` and the CI workflow comments themselves: Phase 14 deleted the only `perf`- and `benchmark`-marked tests (they exercised the now-removed ZEN engine) and left a documented IOU — `.planning/phases/14-scoring-engine-replacement/deferred-items.md` states verbatim "Phase 17 (TEST-01) owns authoring the equal-weight-scoring perf (p95 latency) and benchmark (deterministic output-distribution regression) replacements against `compute_dimension_scores`." This was not mentioned in 17-CONTEXT.md's locked decisions, but it is a real, load-bearing CI obligation (the `perf-gate` job's "treat exit-5 as pass" tolerance exists *only* until this is closed) and belongs in this phase's backend gap-fill list.

**Primary recommendation:** Treat backend as audit + two concrete gap-fill test files (auth-negative-on-new-endpoints + perf/benchmark scoring); treat frontend as two new co-located test files with zero new dependencies and one one-line export fix; build Playwright as a fully separate `e2e/` directory (not nested in `frontend/`) to avoid three distinct, verified tooling collisions; and give `staging.yml` and `main.yml` different image-sourcing strategies for the same reusable E2E logic.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Backend coverage (TEST-01)**
- Phases 12-16 already left substantial backend test coverage behind: `test_dimension_scoring.py` (13 tests incl. all-1s/all-5s edge cases), `test_scoring.py`, `test_questionnaire.py` / `test_questionnaire_answers.py` (17 tests), `test_reports.py` (18 tests), `test_auth.py` (15 tests, from Phase 12).
- Phase 17's backend job is **audit + gap-fill, not a rewrite**: read existing tests against TEST-01's three named areas (scoring engine, questionnaire API, auth flows), identify what's genuinely missing, write only the tests that close real gaps.
- No specific known bugs/pain points to target — trust the audit to surface gaps organically.
- Go straight from audit to writing tests — no separate gap-list review checkpoint with the user before test code is written.
- **Auth scope is extended, not just re-verified**: Phase 12's `test_auth.py` covered register/login/lockout/password-reset against the *old* app shape. Phase 17 must also confirm auth is correctly enforced on the *new, rebuilt* surfaces — e.g. expired/invalid tokens correctly rejected on the new questionnaire-answer and report endpoints, not just the endpoints Phase 12 originally covered.
- No coverage-percentage gate is being introduced on the backend in this phase.

**Frontend coverage (TEST-02)**
- Frontend currently has near-zero test coverage (only `TopNav.test.tsx`) despite Vitest + RTL + jsdom already being installed and wired into CI (`frontend-test` job in pr.yml/staging.yml/main.yml already runs `vitest run --coverage`).
- **Priority is weighted, not even**: `useDebouncedSave` (save/retry/state-machine logic) and `report.tsx` (radar + priority list rendering) get real coverage first. `WizardPage`'s orchestration/navigation and presentational components (`StepPills`, `QuestionCard`, `WelcomeScreen`, `SubsectionLabel`, `AnswerButtonGroup`) get lighter or no coverage in this phase.
- **Mocking strategy**: manual `vi.mock()` on the `lib/*.ts` modules (e.g. mock `saveAnswer` from `lib/questionnaire.ts`, `fetchReportData` from `lib/reports.ts`) — no MSW.
- **Timers**: `useDebouncedSave` tests use Vitest fake timers (`vi.useFakeTimers()` + `vi.advanceTimersByTime()`) to simulate the 1.5s debounce and `[1s, 2s, 4s]` retry backoff instantly.
- **Radar chart testing**: data-driven assertions only (right number of axes/points, band colors match the priority list) — no full-markup/SVG snapshot testing.
- No frontend coverage-percentage gate is being added.

**Playwright E2E (TEST-03)**
- **Environment**: run the existing `docker-compose.yml` (db + backend + frontend) inside a CI job and point Playwright at `localhost` — not against dev servers, not against the live Railway Integration deployment.
- **Image reuse**: the E2E job depends on `staging.yml`'s/`main.yml`'s existing `docker-build` job and pulls the already-built `:staging`/images from `ghcr.io` rather than rebuilding via `docker compose up --build`.
- **Test data**: fresh, freshly-migrated empty database per run; the E2E test itself drives the real registration flow through the UI (not a pre-seeded user).
- **Browser matrix**: Chromium only.
- **Report verification scope**: assert the in-app report view renders (radar chart + priority list) after submit — do NOT also click through to PDF download/email delivery in this E2E test.
- **Failure debugging**: Playwright's built-in `trace: 'retain-on-failure'` plus screenshot-on-failure, uploaded as a workflow artifact on failure.

**CI gating strategy**
- **E2E does NOT block PRs.** It's added to `staging.yml` and `main.yml` only, mirroring the existing `benchmark`-marker precedent (excluded from `pr.yml`, included from `staging` onward).
- No new coverage-percentage CI gate anywhere (backend or frontend).

### Claude's Discretion
- Exact list of backend gap-fill tests (the audit's findings) — not pre-specified, subject to "trust the audit."
- Whether the new E2E job lives as a new job within `staging.yml`/`main.yml` or a new workflow file included by them — implementation detail.
- Playwright config specifics (test file layout, fixtures, retry count for flaky-test tolerance in CI) not covered above.
- Exact frontend test file organization/naming.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. No new product capabilities were proposed during this discussion.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| TEST-01 | Backend has pytest unit test coverage for the scoring engine, questionnaire API, and auth flows | Concrete gap audit performed against all 9 relevant existing test files (see Architecture Patterns → Pattern 1); scoring-engine zero/partial-answer edge cases already covered by `test_dimension_scoring.py`/`test_scoring.py`; questionnaire submission API already covered by `test_submit_completeness.py`/`test_retake_flow.py`; the two real gaps found are auth-negative tests on new endpoints and the standing perf/benchmark IOU from Phase 14 |
| TEST-02 | Frontend has Vitest + React Testing Library coverage for wizard save/state logic and report rendering | `useDebouncedSave.ts` and `report.tsx` fully read; exact mocking targets (`lib/questionnaire.ts::saveAnswer`, `lib/reports.ts::fetchReportData`) identified; the no-charting-library discovery and the `ReportPage`-not-exported blocker are both load-bearing for how this test gets written |
| TEST-03 | Playwright E2E suite covers the critical path: register → answer questionnaire → submit → view report | Full route/component chain traced end-to-end (register.tsx → login.tsx → dashboard.tsx → questionnaire.tsx → WizardPage.tsx → report.tsx); concrete Playwright locator strategy identified (no `data-testid` anywhere in the codebase); CI image-sourcing asymmetry between staging.yml/main.yml identified and resolved |
</phase_requirements>

## Standard Stack

### Core (already installed — verified against actual lockfiles/config, not assumed)

| Library | Version (installed) | Purpose | Why Standard |
|---------|---------------------|---------|---------------|
| pytest | ≥9.1.1 (`backend/pyproject.toml`) | Backend gap-fill tests | Already the project's test runner |
| pytest-benchmark | ≥4.0.0 | `perf`/`benchmark`-marked scoring tests | Already used by the deleted-but-git-recoverable ZEN perf/benchmark tests; exact same idiom needed for the replacement |
| testcontainers[postgres] | ≥4.14.2 | Real-Postgres `session`/`client` fixtures | Already the sole backend fixture family (`backend/tests/conftest.py`) — no SQLite anywhere |
| Vitest | ^4.1.10 (`frontend/package.json`) | Frontend unit tests | Already wired (`frontend/vitest.config.ts`, `frontend/src/test/setup.ts`) |
| @testing-library/react | ^16.3.2 | Component rendering/queries | Already installed, used by `TopNav.test.tsx` |
| @testing-library/jest-dom | ^7.0.0 | DOM matchers (`toBeInTheDocument` etc.) | Already installed, imported in `src/test/setup.ts` |
| @testing-library/user-event | ^14.6.1 | Simulated user interaction | Already installed, unused so far — first real consumer will be these new tests |
| @vitest/coverage-v8 | ^4.1.10 | `vitest run --coverage` (informational only) | Already wired into `frontend-test` CI job, no gate |

### Supporting — NEW for this phase

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @playwright/test | ^1.62.x (verified latest stable: v1.62.1, released 2026-07-30 — confirm exact patch at implementation time via `npm view @playwright/test version`) | E2E critical-path suite | Not installed anywhere in this repo today — genuinely greenfield |
| wait-on | latest (small, single-purpose) | CI readiness gate for `localhost:8000`/`localhost:3000` before Playwright starts | Purpose-built alternative to a hand-rolled curl/bash retry loop |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual `vi.mock()` on `lib/*.ts` (LOCKED) | MSW (Mock Service Worker) | MSW gives more realistic network-layer mocking but is a new dependency for a codebase with zero test culture before this phase — CONTEXT.md explicitly rejected it |
| Separate top-level `e2e/` dir with its own `package.json` (RECOMMENDED) | Nest Playwright inside `frontend/e2e/` | Nesting risks 3 verified collisions with this repo's *actual* configs (see Common Pitfalls) — not a hypothetical, confirmed by reading `tsconfig.app.json`, `eslint.config.js`, and Vitest's default include glob |
| `wait-on` for CI readiness (RECOMMENDED) | Playwright's own `webServer` config with `reuseExistingServer: true` | `webServer.command` is a required field per Playwright's TypeScript types; using it purely as a "wait for already-running server" mechanism is a documented pattern for local dev (`reuseExistingServer: !process.env.CI`) but its exact behavior when the command is a true no-op is not officially confirmed — `wait-on` is unambiguous and decouples readiness-waiting from Playwright's own config entirely |
| Playwright running natively on the GH Actions runner against Compose's host-published ports (RECOMMENDED) | Playwright running inside its own Docker container on the Compose network | Avoids an entire class of Docker-network-alias pitfalls (`localhost` inside a container isn't the host) for zero benefit here — `docker-compose.yml` already publishes `8000:8000`/`3000:80` to the host, so a runner-native Playwright process reaches them via plain `localhost` |

**Installation:**
```bash
# New e2e/ directory, sibling to frontend/ and backend/
mkdir e2e && cd e2e
npm init -y
npm install -D @playwright/test@^1.62.0 wait-on
npx playwright install --with-deps chromium
```

## Architecture Patterns

### Recommended Project Structure

```
DSSC-Maturity-Tool/
├── backend/
│   └── tests/
│       ├── api/
│       │   ├── test_auth_dependency.py      # NEW — gap-fill (see Pattern 1)
│       │   └── ...(existing, unmodified)
│       ├── perf/
│       │   └── test_dimension_scoring_perf.py       # NEW — closes Phase 14's deferred IOU
│       └── benchmark/
│           └── test_dimension_scoring_regression.py  # NEW — closes Phase 14's deferred IOU
├── frontend/
│   └── src/
│       ├── hooks/
│       │   ├── useDebouncedSave.ts
│       │   └── useDebouncedSave.test.ts     # NEW — co-located, matches TopNav.test.tsx convention
│       └── routes/_app/
│           ├── report.tsx                    # MODIFIED — `export` added to `ReportPage`
│           └── report.test.tsx                # NEW — co-located
├── e2e/                                       # NEW — top-level, sibling to frontend/backend
│   ├── package.json
│   ├── playwright.config.ts
│   ├── tsconfig.json
│   ├── docker-compose.e2e.yml                 # override file, image: refs only (see Pattern 3)
│   └── tests/
│       └── critical-path.spec.ts
├── .github/workflows/
│   ├── staging.yml                            # MODIFIED — new `e2e` job
│   └── main.yml                               # MODIFIED — new `e2e` job (different image-sourcing, see Pattern 3)
└── docker-compose.yml                         # UNCHANGED
```

### Pattern 1: Backend gap-fill — concrete audit results, not a re-derivation exercise

Direct reading of all 9 relevant existing test files (`test_dimension_scoring.py`, `test_scoring.py`, `test_questionnaire.py`, `test_questionnaire_answers.py`, `test_submit_completeness.py`, `test_retake_flow.py`, `test_reports.py`, `test_auth.py`, plus `backend/app/core/deps.py`) found:

**Already fully covered — do not duplicate:**
- Scoring engine zero/partial-answer edges: `test_dimension_scoring.py::test_incomplete_assessment_raises_422`, `::test_no_draft_assessment_raises_422`; `test_scoring.py::test_score_422_when_incomplete`, `::test_score_422_when_no_assessment_exists`.
- Questionnaire submission API happy/edge paths: `test_submit_completeness.py` (422-incomplete, 200-complete, idempotent-resubmit) and `test_retake_flow.py` (submit-then-retake creates v2 draft, retake-never-submitted 409, retake-rejects-non-owner).
- Ownership/ownership-then-completion ordering (403 vs 422/404): present across `test_scoring.py`, `test_questionnaire_answers.py`, `test_reports.py`.

**Genuine gap #1 — auth enforcement on new endpoints (exactly what CONTEXT.md flagged):**
`backend/app/core/deps.py::get_current_user` is the single shared dependency behind every protected endpoint (`oauth2_scheme` → `decode_access_token` → 401 "Invalid or expired token" on failure, or "User not found" if the token's subject no longer exists). **No test file anywhere in `backend/tests/` exercises a missing Authorization header, a malformed bearer token, an expired token, or a token for a deleted user against any endpoint.** Every existing test either calls `_login()` first (fully authenticated) or uses a *second, different, still-valid* user's token to assert 403 (ownership), never a request with no/bad token to assert 401. This is a single shared dependency, so one parametrized test file closes it for every endpoint at once — do not duplicate per-router.

**Genuine gap #2 — perf/benchmark scoring coverage (explicit, repeated obligation, not optional):**
`.planning/phases/14-scoring-engine-replacement/deferred-items.md` (Plan 14-04) states verbatim: *"Phase 17 (TEST-01) owns authoring the equal-weight-scoring perf (p95 latency) and benchmark (deterministic output-distribution regression) replacements against `compute_dimension_scores`, mirroring the deleted tests' shape but driven by `config/dssc-questionnaire.json`."* `CLAUDE.md` repeats this three times (in its own body text and in `pr.yml`/`staging.yml`/`main.yml`'s `perf-gate` job comments) and explicitly ties the CI tolerance ("exit code 5 = pass") to this being unclosed. **The deleted originals are recoverable from git** — see Code Examples below; they used a `make_answers(N)` in-memory fixture that no longer exists (Phase 14 deleted it alongside the ZEN engine), so the replacement must build its input via the *current* DB-backed factories (`make_user`/`make_initiative`/`make_assessment`/`make_answer` from `tests/factories.py`) and call `compute_dimension_scores(session, assessment.id, config)` — this makes the benchmark's setup a real DB round-trip too (representative of production, and `pytest-benchmark`'s `benchmark()` wrapper only times the call passed to it, not fixture setup, so this doesn't corrupt the timing).

### Pattern 2: Frontend — data-driven report.tsx testing (no chart library exists)

`report.tsx` receives `data.radar_chart_svg` (a complete `<svg>...</svg>` string built server-side by `generate_radar_svg` in `report_generator.py`) and renders it via `dangerouslySetInnerHTML`. There is **no recharts/visx/nivo/d3/chart.js** anywhere in `frontend/package.json` — confirmed by direct grep, not inference. This means:

- **Do not** design tests around mocking a charting library's props/render output — there isn't one.
- **Do** mock `fetchReportData` (from `frontend/src/lib/reports.ts`) to return a fixed `ReportContract` object whose `radar_chart_svg` field is a small, hand-written SVG fixture string (e.g. containing a known number of `<text>`/`<polygon>` elements with known `fill`/`stroke` attributes), then assert against the *rendered DOM* via `container.querySelectorAll('svg text')`, `container.querySelector('svg polygon')?.getAttribute('fill')`, etc. — real jsdom DOM queries, matching CONTEXT.md's "data-driven assertions only" instruction exactly.
- **Do** assert the priority list separately: render with a fixed `priority_list` array in the mocked contract, then assert each row's name/band_label/score text and the color-dot's inline `background` style match the fixture data, in the same sorted order the contract provided (the component does not re-sort — sorting happens server-side in `build_priority_list`).
- **jsdom SVG caveat** (verified via jsdom's own GitHub issues + a React Testing Library issue thread): jsdom does not implement `getBBox()` or perform real SVG layout — attribute/text-content queries work fine (what this component needs), but any assertion depending on computed geometry/bounding boxes will not work in jsdom and must not be attempted.

**Blocker to resolve first:** `function ReportPage()` in `report.tsx` is not exported (only `export const Route = createFileRoute(...)` is). The one existing precedent in this codebase, `TopNav.tsx`, *is* exported (`export function TopNav()`) specifically so `TopNav.test.tsx` can `import { TopNav } from './TopNav'`. The plan must add `export` to `function ReportPage()` (a trivial, behavior-neutral change) before or as part of writing `report.test.tsx`.

### Pattern 3: E2E CI — staging.yml and main.yml need *different* image-sourcing, not identical jobs

Direct reading of both workflow files found an asymmetry CONTEXT.md's phrasing glosses over:

- **`staging.yml`**'s `docker-build` job *does* push real images: `ghcr.io/<owner>/<repo>-backend:staging` and `...-frontend:staging`. A separate `e2e` job with `needs: docker-build` can `docker pull` these tags directly — CONTEXT.md's plan works exactly as stated here.
- **`main.yml`**'s `docker-build-and-sbom` job does **not** push anywhere — `docker/build-push-action@v6` is called with `push: false, load: true`, producing images that exist only in that job's own local Docker daemon, tagged `mami-checker-backend:main-${{ github.sha }}` / `mami-checker-frontend:main-${{ github.sha }}`. A separate `e2e` job on a fresh runner cannot see these — GitHub Actions jobs do not share a Docker daemon or filesystem.

**Recommended fix (two valid options, pick one per workflow):**
1. **For `main.yml` (recommended): give the `e2e` job its own independent `docker compose up --build`.** `main.yml` pushes to `main` infrequently (gated by a `staging`-branch PR having already passed, then a second PR into `main`), so the extra build time is acceptable, and it keeps job failure signals clean — a Playwright failure shows up as the `e2e` job failing, not muddying `docker-build-and-sbom`'s SBOM-generation responsibility.
2. **For `staging.yml`: `needs: docker-build`, pull the pushed `:staging` tags.** This matches CONTEXT.md's stated intent and genuinely avoids a duplicate build on the much-more-frequent `staging` push trigger.

**To avoid duplicating the ~40 lines of "start compose, wait for readiness, run playwright, upload artifacts on failure" between the two workflows**, factor the E2E steps into a **reusable workflow** (`on: workflow_call`) — e.g. `.github/workflows/e2e-tests.yml` — taking `backend-image`/`frontend-image` as optional string inputs (empty = build from source via `docker compose up --build`, non-empty = pull-and-run via a Compose override). Both `staging.yml` and `main.yml` then have a short `e2e: uses: ./.github/workflows/e2e-tests.yml with: {...}` job. This is a standard, officially-supported GitHub Actions pattern for exactly this kind of near-duplicate job across two trigger workflows.

**Image reference without touching `docker-compose.yml`'s `build:` blocks:** create `e2e/docker-compose.e2e.yml` as a Compose override (`docker compose -f docker-compose.yml -f e2e/docker-compose.e2e.yml up -d`) that replaces `backend`/`frontend`'s `build:` key with `image: ${E2E_BACKEND_IMAGE}` / `image: ${E2E_FRONTEND_IMAGE}` — the base `docker-compose.yml` stays completely unmodified (no risk to the existing local-dev workflow), and the two env vars are set differently per calling workflow (ghcr tag for staging, locally-built tag for main).

### Pattern 4: Playwright locator strategy — no `data-testid` exists anywhere in this codebase

Confirmed via repo-wide grep: zero `data-testid` attributes exist in `frontend/src`. The wizard's answer controls (`AnswerButtonGroup.tsx`) use `role="radiogroup"` wrapping five `role="radio"` buttons, each with an identical-looking accessible label per score position across *every* question (e.g. every question's 3rd option might be labeled differently per question in real DSSC content, but cannot be assumed unique) — so `getByRole('radio', { name: ... })` is not reliably unique across a page with 6-11 questions. The robust, add-nothing-to-source pattern: iterate `page.getByRole('radiogroup')` (one per question on the current category page) and click a fixed-index option (e.g. `.getByRole('radio').nth(2)`, the middle/3rd option) within each — see Code Examples.

### Anti-Patterns to Avoid
- **Snapshot-testing the radar SVG's raw markup:** explicitly rejected by CONTEXT.md — generated SVG coordinate strings (`points="123.4,56.7 ..."`) make unreviewable diffs. Assert structural/attribute facts only (element counts, colors, text content).
- **Testing `useDebouncedSave` with real `setTimeout`/real waits:** locked to `vi.useFakeTimers()` — a real-timers version of this test would need 1.5s + up to 7s of retry backoff per test case, making the suite slow and CI-flaky.
- **Building a custom bash/curl polling loop for "wait until docker compose services respond":** don't hand-roll this — see Don't Hand-Roll below.
- **Running Playwright inside its own Docker container on the Compose network:** adds a real class of "container can't resolve `localhost`" pitfalls for zero benefit, since ports are already host-published.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Wait for `localhost:8000`/`localhost:3000` to be ready in CI before Playwright starts | A bash `while ! curl ...; do sleep 1; done` retry loop | `wait-on` (npm package) — `npx wait-on http://localhost:8000/health http://localhost:3000 -t 120000` | Purpose-built, handles timeout/backoff correctly, one line instead of a fragile inline script |
| Debounce/retry-backoff testing without real waits | Manually mocking `setTimeout`/`Date.now()` | Vitest's built-in `vi.useFakeTimers()` + `vi.advanceTimersByTime()` | Already the documented, locked approach; native to the test runner already installed |
| Server-rendered SVG assertions | A DOM diffing / snapshot library | Plain jsdom DOM queries (`container.querySelectorAll`, `getAttribute`) via RTL's `container` | jsdom + RTL already fully sufficient for attribute/text assertions; no new dependency needed |
| Duplicating E2E CI steps across `staging.yml` and `main.yml` | Copy-pasted ~40-line job blocks in both files | A reusable workflow (`on: workflow_call`) | Single source of truth for the Playwright execution steps; officially supported GH Actions feature, already implicitly the pattern this repo favors (shared quality-gate jobs are already near-identical across `pr.yml`/`staging.yml`/`main.yml` — a reusable workflow is the natural next step, not a new idiom) |
| Per-endpoint auth-negative tests | 6+ near-duplicate "no token → 401" tests, one per router | One parametrized test file against `get_current_user`'s shared dependency, exercised through a small representative sample of protected endpoints (one from questionnaire, one from scoring, one from reports) | `get_current_user` is a single shared FastAPI dependency — testing it once per distinct *code path* (missing header / malformed token / expired token / deleted user) against a couple of representative routes proves the dependency works; it does not need re-proving per router |

**Key insight:** every "don't hand-roll" item above already has an established idiom either in this exact codebase (fake timers pattern already decided, RTL `container` queries need nothing new) or as a small, focused, single-purpose tool (`wait-on`) rather than a hand-rolled script — consistent with this repo's own stated philosophy in `CLAUDE.md` of using "cheap, reusable patterns" over one-off scripts (e.g. its docs-freshness gate).

## Common Pitfalls

### Pitfall 1: Nesting Playwright inside `frontend/` collides with three real, already-verified configs
**What goes wrong:** Vitest picks up Playwright's `*.spec.ts` files and tries to run them as unit tests (crashing on `import { test } from '@playwright/test'` inside a jsdom environment with no browser); ESLint's `frontend/eslint.config.js` (`files: ['**/*.{ts,tsx}']`, no exclusion for an e2e folder) lints Playwright test files against React/Vitest rules that don't apply; `tsc -b --noEmit`'s `tsconfig.app.json` (`include: ["src"]`) would be extended awkwardly to also cover e2e types, risking Vitest's `globals: true` ambient `test`/`expect` colliding with `@playwright/test`'s own `test`/`expect` imports in the same TS project (a documented class of issue: global-scope `test`/`expect`/`describe`/`it` identifier clashes between test frameworks sharing a `tsconfig`).
**Why it happens:** Vitest's default `include` glob (`**/*.{test,spec}.?(c|m)[jt]s?(x)`) and ESLint's `files: ['**/*.{ts,tsx}']` are both unscoped beyond their working directory (`frontend/`) — anything placed inside that tree is in scope by default.
**How to avoid:** Put the whole Playwright suite in a **top-level `e2e/` directory, sibling to `frontend/` and `backend/`**, with its own `package.json`, `tsconfig.json`, and `playwright.config.ts` — entirely outside every existing tool's scan root. Confirmed via direct inspection of this repo's actual `tsconfig.app.json`, `eslint.config.js`, and `vitest.config.ts` — not a generic warning.
**Warning signs:** `npx vitest run` in CI suddenly takes much longer or errors on files it's never seen; `eslint .` in `frontend/` reports errors in a file that has nothing to do with React.

### Pitfall 2: `main.yml` has no registry-pushed image to pull for E2E
**What goes wrong:** An `e2e` job added to `main.yml` that tries to `docker pull ghcr.io/.../backend:main` (mirroring `staging.yml`'s pattern) will fail — no such tag is ever pushed by `main.yml`'s `docker-build-and-sbom` job (`push: false`).
**Why it happens:** `main.yml` was deliberately designed to build-but-not-publish (its docstring/comment: "no registry push — `main` deploys manually"), unlike `staging.yml`.
**How to avoid:** See Architecture Patterns Pattern 3 — give `main.yml`'s `e2e` job its own `docker compose up --build` rather than trying to reuse `docker-build-and-sbom`'s locally-loaded images (which live in a different job/runner and aren't reachable anyway).
**Warning signs:** `docker pull` step fails with "manifest unknown" / 404 in the `main.yml` E2E job specifically (while the identical step in `staging.yml` works fine).

### Pitfall 3: `report.tsx`'s component isn't exported
**What goes wrong:** `import { ReportPage } from '../../routes/_app/report'` fails at compile time — `ReportPage` doesn't exist as a named export.
**Why it happens:** File-based TanStack Router routes only need to export `Route`; the component function itself has no reason to be exported unless something outside the route file needs to import it directly (which nothing did, until now).
**How to avoid:** Add `export` to `function ReportPage()` before writing `report.test.tsx` — safe, behavior-neutral, and matches the existing `TopNav.tsx` precedent exactly.
**Warning signs:** TypeScript error "Module has no exported member 'ReportPage'" the moment the test file is written.

### Pitfall 4: Vitest fake timers + async `saveAnswer` calls inside `useDebouncedSave` — microtask/macrotask ordering
**What goes wrong:** After `vi.advanceTimersByTime(1500)` fires the debounce timeout, the `saveAnswer` mock's returned Promise (a microtask) hasn't necessarily resolved yet when the next assertion runs — fake timers only fast-forward macrotasks (`setTimeout`), they do not flush pending microtasks (Promise `.then()` chains) still waiting for the call stack to unwind. A retry-backoff test (`await new Promise(resolve => setTimeout(resolve, RETRY_DELAYS_MS[attempt]))` inside `saveWithRetry`) has *both* a Promise wrapping a `setTimeout` — advancing the timer alone can leave assertions racing the promise microtask queue.
**Why it happens:** This is a well-documented general Vitest/Jest fake-timer pitfall, not specific to this codebase, but `useDebouncedSave.ts`'s exact shape (an async retry loop mixing `await saveAnswer(...)` with `await new Promise((resolve) => setTimeout(resolve, ...))`) is precisely the shape that triggers it.
**How to avoid:** After each `vi.advanceTimersByTime(...)` call intended to cross a debounce or retry-delay boundary, `await` a microtask flush (e.g. `await vi.waitFor(() => expect(mockSaveAnswer).toHaveBeenCalledTimes(n))`, or `await Promise.resolve()` / `await null` between timer advances) before asserting on `onStateChange` call state. Wrap timer-advancing calls that trigger React state updates in `act()` (via `@testing-library/react`'s `act` or RTL's own internal batching) to avoid the "not wrapped in act(...)" console warning.
**Warning signs:** Flaky assertions that pass/fail depending on unrelated timing; a `act()` warning in test output even though the code "looks" synchronous.

### Pitfall 5: jsdom's incomplete SVG support
**What goes wrong:** Any test attempting `element.getBBox()`, real layout/computed-position assertions, or anything depending on SVG rendering geometry silently fails or throws — jsdom does not implement these (confirmed via jsdom's own tracked GitHub issues, still open as of the versions available today).
**Why it happens:** jsdom is a DOM implementation, not a rendering engine — it doesn't do layout, so SVG geometry APIs that require actual rendering have no meaningful value to return.
**How to avoid:** Stick to what CONTEXT.md already mandates — attribute and text-content assertions only (`getAttribute('fill')`, `textContent`, element `querySelectorAll` counts). Never assert on computed bounding boxes/positions in these tests.
**Warning signs:** `TypeError: element.getBBox is not a function` or similar in test output.

### Pitfall 6: Docker Compose readiness — only the `db` service has a healthcheck
**What goes wrong:** `docker-compose.yml` only defines a `healthcheck` on the `db` service; `backend` and `frontend` have none. `docker compose up --wait` (Compose's own built-in "block until healthy" flag) treats services with no healthcheck as "ready" the instant the container process starts — which for `backend` is well before `alembic upgrade head && python scripts/create_admin.py && fastapi run ...` has actually finished and port 8000 is accepting connections.
**Why it happens:** `docker-compose.yml` was written for local dev, where a developer visually waits; it was never designed as a CI readiness gate.
**How to avoid:** Don't rely on `docker compose up --wait` alone. Do `docker compose up -d` (or the override-file equivalent), then a *separate* explicit HTTP-level readiness check — `wait-on` against `http://localhost:8000/health` (confirmed to exist at `backend/app/main.py:66`) and `http://localhost:3000` (nginx serving `index.html`) — before invoking `npx playwright test`.
**Warning signs:** E2E job intermittently fails on `register()`'s first request with connection-refused, especially when the runner is under load (backend's `alembic upgrade head` + admin-seed startup sequence takes longer than a fixed short sleep would assume).

### Pitfall 7: docker-compose.yml requires a full `.env` (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`) or the backend container fails to boot
**What goes wrong:** `backend/scripts/create_admin.py` (run automatically by the Docker `CMD`) reads `settings.ADMIN_EMAIL`/`settings.ADMIN_PASSWORD` via pydantic-settings with no defaults shown in `.env.example` — an incomplete env will crash the container at startup (pydantic-settings validation error, or a downstream `NoneType` failure), which then just looks like "readiness never happens" rather than a clear config error.
**How to avoid:** The CI job must write a full `.env` (or export all five vars) matching `.env.example`'s keys before `docker compose up`, using fixed throwaway CI-only values (never production secrets) — the Postgres container itself is fresh/ephemeral per run anyway.
**Warning signs:** `wait-on` (Pitfall 6) times out entirely, and `docker compose logs backend` (captured as a debugging step / artifact on failure) shows a startup crash, not a slow-start.

## Code Examples

### Backend: perf test — mirrors the deleted `test_scoring_perf.py` shape (recovered from git history, commit `00e6f01e78^`), now DB-backed
```python
# Source: this repo's own git history (backend/tests/perf/test_scoring_perf.py,
# deleted in commit 00e6f01e780d40f293664589384a140a8ce0fdc5) + current
# backend/tests/factories.py + backend/tests/services/test_dimension_scoring.py idiom
import pytest
from app.services.dimension_scoring import compute_dimension_scores
from app.services.mami_config import load_dssc_questionnaire_config
from tests.factories import make_answer, make_assessment, make_initiative, make_user

pytestmark = pytest.mark.perf

P95_BUDGET_SECONDS = 1.0  # starter threshold — tune once real SLOs are known


def test_compute_dimension_scores_p95(benchmark, session):
    config = load_dssc_questionnaire_config()
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)
    for cat in config["categories"]:
        for question in cat["questions"]:
            make_answer(
                session, initiative=initiative, assessment=assessment,
                question_id=question["id"], category_id=cat["id"], score=3,
            )

    def run():
        return compute_dimension_scores(session, assessment.id, config)

    benchmark(run)

    sorted_runs = benchmark.stats.stats.sorted_data
    p95 = sorted_runs[min(len(sorted_runs) - 1, int(len(sorted_runs) * 0.95))]
    assert p95 < P95_BUDGET_SECONDS
```

### Backend: benchmark (deterministic regression) test — output-distribution replacement
```python
# Source: same deleted-file lineage as above, adapted — the old test locked in
# ZEN "severity" counts (CRITICAL/NON_CRITICAL); compute_dimension_scores has no
# severity concept, so the golden assertion becomes exact per-category scores.
import pytest
from app.services.dimension_scoring import compute_dimension_scores
from app.services.mami_config import load_dssc_questionnaire_config
from tests.factories import make_answer, make_assessment, make_initiative, make_user

pytestmark = pytest.mark.benchmark


def test_compute_dimension_scores_output_distribution(session):
    config = load_dssc_questionnaire_config()
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)
    # Deterministic, varied-by-category-index scoring pattern (not all-3s,
    # which would trivially pass even a broken per-category average).
    for cat_idx, cat in enumerate(config["categories"]):
        score = (cat_idx % 5) + 1
        for question in cat["questions"]:
            make_answer(
                session, initiative=initiative, assessment=assessment,
                question_id=question["id"], category_id=cat["id"], score=score,
            )

    scores = compute_dimension_scores(session, assessment.id, config)

    # Golden values for this fixed synthetic pattern — regenerate deliberately
    # (not silently) if compute_dimension_scores's averaging logic changes.
    by_id = {s["category_id"]: s["score"] for s in scores}
    assert by_id == {cat["id"]: float((i % 5) + 1) for i, cat in enumerate(config["categories"])}
```

### Backend: auth-negative test against the shared dependency
```python
# Source: backend/app/core/deps.py (get_current_user) read directly —
# no equivalent test exists anywhere in backend/tests/ today.
import pytest

@pytest.mark.parametrize("headers", [
    {},  # no Authorization header at all
    {"Authorization": "Bearer not-a-real-jwt"},  # malformed token
])
def test_questionnaire_answers_rejects_missing_or_invalid_token(client, session, headers):
    from tests.factories import make_initiative, make_user
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    client.headers.update(headers)

    response = client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/q-1-1",
        json={"question_id": "q-1-1", "category_id": "cat-1", "score": 3},
    )
    assert response.status_code == 401
```

### Frontend: `useDebouncedSave` fake-timer test (debounce boundary)
```typescript
// Source: pattern verified against Vitest's official fake-timer docs +
// this repo's frontend/src/hooks/useDebouncedSave.ts exact shape
import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useDebouncedSave } from './useDebouncedSave';

vi.mock('../lib/questionnaire', () => ({
  saveAnswer: vi.fn(),
}));
import { saveAnswer } from '../lib/questionnaire';

describe('useDebouncedSave', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('saves after the 1.5s debounce window, not before', async () => {
    const onStateChange = vi.fn();
    vi.mocked(saveAnswer).mockResolvedValue({} as never);
    const { result } = renderHook(() => useDebouncedSave(1, onStateChange));

    act(() => result.current.schedule('q-1', 'cat-1', 4));
    expect(saveAnswer).not.toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(1500);
      await Promise.resolve(); // flush the microtask queue fake timers don't touch
    });

    expect(saveAnswer).toHaveBeenCalledWith(1, 'q-1', {
      question_id: 'q-1', category_id: 'cat-1', score: 4,
    });
  });
});
```

### Frontend: `report.tsx` data-driven radar assertion
```typescript
// Source: this repo's actual ReportContract shape (frontend/src/lib/reports.ts)
// and generate_radar_svg's actual output shape (backend/app/services/report_generator.py)
vi.mock('../../lib/reports', () => ({ fetchReportData: vi.fn() }));
import { fetchReportData } from '../../lib/reports';

const fixtureSvg =
  '<svg viewBox="0 0 320 320" xmlns="http://www.w3.org/2000/svg">' +
  '<polygon points="1,1 2,2 3,3" fill="#76b82a" stroke="#76b82a" stroke-width="2"/>' +
  '<text x="1" y="1" fill="#008ecf">Dimension A</text>' +
  '</svg>';

vi.mocked(fetchReportData).mockResolvedValue({
  assessment_id: 1, version: 1,
  initiative: { name: 'Test', organization: null, contact_name: null, participant_type: null },
  dimension_scores: [],
  priority_list: [{ category_id: 'cat-1', name: 'Dimension A', score: 4.2, band_id: 'green', band_label: 'Scaling', band_color: '#76b82a' }],
  radar_chart_svg: fixtureSvg,
  maturity_bands: [],
});

// after render + awaiting the fetch:
const polygon = container.querySelector('svg polygon');
expect(polygon?.getAttribute('fill')).toBe('#76b82a');
expect(screen.getByText('Dimension A')).toBeInTheDocument(); // priority list row
```

### Playwright: radiogroup-index locator strategy (no data-testid exists)
```typescript
// Source: frontend/src/components/questionnaire/AnswerButtonGroup.tsx read directly —
// role="radiogroup" wrapping role="radio" buttons, no test-id anywhere in the codebase
async function answerAllQuestionsOnCurrentPage(page: import('@playwright/test').Page) {
  const groups = await page.getByRole('radiogroup').all();
  for (const group of groups) {
    await group.getByRole('radio').nth(2).click(); // always the 3rd (middle) option
  }
}
```

### playwright.config.ts — CI settings honoring CONTEXT.md's locked decisions
```typescript
// Source: Playwright official docs (playwright.dev/docs/test-configuration,
// playwright.dev/docs/ci) cross-referenced with CONTEXT.md's locked trace/screenshot decision
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',       // CONTEXT.md locked decision
    screenshot: 'only-on-failure',    // CONTEXT.md locked decision (exact Playwright value)
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }], // Chromium only, CONTEXT.md locked
  // No webServer block — docker compose + wait-on (a separate CI step) already
  // guarantee readiness before `playwright test` runs; see Don't Hand-Roll.
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-------------------|---------------|--------|
| ZEN rules-engine scoring (`scoring_engine.py`, MoSCoW findings) | Equal-weight average per dimension (`dimension_scoring.py::compute_dimension_scores`) | Phase 14 (2026-07-24) | Old perf/benchmark tests for the ZEN path were deleted, not migrated — this phase writes their true replacements, not a resurrection of the old shape |
| N/A (no charting library was ever added) | Server-rendered SVG string, injected via `dangerouslySetInnerHTML` | Phase 16 (RPRT-01/D-01/D-02) | Frontend chart testing is data-in-DOM assertion, never chart-library-prop assertion |
| `Playwright ~1.4x` (older training-data assumption) | v1.62.1 stable (2026-07-30), Docker image `mcr.microsoft.com/playwright:v1.62.0-noble` | Confirmed via 2 independent sources (GitHub releases page + WebSearch cross-reference) | Pin `^1.62.0` at implementation time, re-verify exact patch via `npm view` since this moves fast |

**Deprecated/outdated:**
- Any research instinct to reach for `factory_boy` for backend fixtures — this repo deliberately uses plain factory functions (`tests/factories.py`'s own docstring: "NOT factory_boy — per D-03/RESEARCH.md Alternatives Considered"). Follow the existing convention exactly; do not introduce factory_boy.
- Any instinct to reach for MSW for frontend network mocking — explicitly locked out by CONTEXT.md for this phase.

## Open Questions

1. **Exact `@playwright/test` patch version to pin**
   - What we know: v1.62.1 was the latest stable release as of 2026-07-30, confirmed via two independent sources (GitHub releases page, general web search cross-reference).
   - What's unclear: whether a newer patch has shipped between this research (2026-08-05) and actual plan execution.
   - Recommendation: run `npm view @playwright/test version` at implementation time and pin that exact resolved version in `e2e/package.json` rather than trusting this document's number verbatim.

2. **Whether `main.yml`'s E2E job should rebuild via `docker compose up --build` or be given a registry push**
   - What we know: `main.yml` currently never pushes images anywhere (deliberate, per its own comments — "main deploys manually"); adding a `docker-build`-style push job to `main.yml` would be a meaningful behavior change to a workflow outside this phase's stated scope.
   - What's unclear: whether the phase owner would prefer to extend `main.yml` to also push a `:main-<sha>` tag to ghcr (enabling pull-based reuse there too) vs. accepting the extra build cost of a from-source `docker compose up --build` in the `e2e` job.
   - Recommendation: default to the from-source rebuild (Pattern 3, option 1) since it requires zero changes to `main.yml`'s existing publish behavior and keeps this phase's blast radius to "add an e2e job," not "change main's deployment posture."

3. **Whether the last category's "Next" button relabels to "Submit"**
   - What we know: `WizardPage.tsx`'s `handleNext()` calls `submitMutation.mutateAsync()` when `isLastCategory` is true — functionally it submits — but the exact button *label* text on the last category page wasn't fully confirmed in the portion of the file read (render logic for the Next/Back button row was beyond the read window).
   - What's unclear: the literal accessible name Playwright should target for the last click of the critical path (`Next` vs `Submit` vs something else).
   - Recommendation: the plan/execution step should grep `WizardPage.tsx` for the Next/Back button JSX directly before writing the E2E spec's final-step locator, or use a position/role-based locator (`page.getByRole('button').last()` within the question-card panel) that doesn't depend on exact label text.

## Sources

### Primary (HIGH confidence — direct repo inspection)
- `backend/pyproject.toml`, `frontend/package.json` — exact installed versions
- `backend/tests/conftest.py`, `backend/tests/factories.py` — fixture idiom to follow
- `backend/tests/api/test_auth.py`, `test_questionnaire_answers.py`, `test_reports.py`, `test_scoring.py`, `test_submit_completeness.py`, `test_retake_flow.py`, `backend/tests/services/test_dimension_scoring.py`, `test_dssc_config.py` — full gap audit
- `backend/app/core/deps.py` — `get_current_user` shared-dependency shape (the auth gap)
- `backend/app/services/report_generator.py` — confirms server-rendered-SVG architecture, no chart library
- `frontend/src/routes/_app/report.tsx`, `frontend/src/hooks/useDebouncedSave.ts`, `frontend/src/lib/reports.ts`, `frontend/src/lib/questionnaire.ts`, `frontend/src/lib/api.ts` — exact mocking targets and the `ReportPage` export gap
- `frontend/src/components/questionnaire/*.tsx` — full critical-path UI trace (register → login → dashboard → questionnaire → wizard → report), radiogroup/radio role structure, no `data-testid` anywhere
- `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`, `frontend/tsconfig.app.json`, `frontend/eslint.config.js` — the three tooling-scope facts behind the "put e2e/ outside frontend/" recommendation
- `.github/workflows/pr.yml`, `staging.yml`, `main.yml` — exact existing CI job structure, and the staging/main image-push asymmetry
- `docker-compose.yml`, `frontend/Dockerfile`, `backend/Dockerfile`, `frontend/nginx.conf`, `.env.example`, `backend/scripts/create_admin.py` — CI env/readiness requirements
- `.planning/phases/14-scoring-engine-replacement/deferred-items.md` + `git show 00e6f01e78^:...` — the perf/benchmark IOU and the exact deleted-test shape to mirror
- `CLAUDE.md` (repo root) — CI workflow structure, perf/benchmark marker precedent, existing philosophy notes

### Secondary (MEDIUM confidence — WebSearch/WebFetch, cross-referenced 2+ sources where possible)
- [Continuous Integration | Playwright](https://playwright.dev/docs/ci) — official CI recommendations (workers=1, sharding over parallelism, Docker image usage)
- [Playwright Test Configuration](https://playwright.dev/docs/test-configuration) — official retries/trace/baseURL guidance
- [Playwright webServer docs](https://playwright.dev/docs/test-webserver) — confirms `command` is required, `reuseExistingServer` semantics (informed the decision to use `wait-on` instead)
- [Playwright GitHub Releases](https://github.com/microsoft/playwright/releases) — v1.62.1 (2026-07-30) as latest stable, cross-referenced against `mcr.microsoft.com/playwright:v1.62.0-noble` mentioned in official CI docs
- [Docker Compose `--wait` flag / `--wait-timeout`](https://lours.me/posts/compose-tip-051-up-wait/) + [docker/compose#10269](https://github.com/docker/compose/issues/10269) — confirms `--wait` semantics and that services without healthchecks are considered immediately ready (the basis for Pitfall 6)
- jsdom SVG limitations: [jsdom/jsdom#918](https://github.com/jsdom/jsdom/issues/918), [jsdom/jsdom#1423](https://github.com/jsdom/jsdom/issues/1423), [testing-library/react-testing-library#651](https://github.com/testing-library/react-testing-library/issues/651) — multiple independent, long-standing tracked issues confirming `getBBox()`/layout are not implemented
- Vitest fake-timer + async pitfalls: cross-referenced across [testdouble.com](https://testdouble.com/insights/jest-timers-vs-waitfor-debounced-inputs), [hy2k.dev](https://hy2k.dev/en/blog/2025/10-03-vitest-fake-timers-debounced-solidjs-search/), and general Medium/dev.to sources — consistent microtask/macrotask-ordering warning across sources

### Tertiary (LOW confidence — single source or general community consensus, flagged for validation)
- Exact recommended CI retry count (1-2) and the "reusable workflow" DRY pattern as *the* idiomatic fix for the staging/main duplication — sound general GitHub Actions advice, but not verified against this specific repo's own prior precedent for reusable workflows (this repo has none today; it currently accepts near-duplicate job blocks across `pr.yml`/`staging.yml`/`main.yml`, so a reusable workflow would be a genuinely new pattern for this codebase, not a continuation of an existing one — flagged for the planner's judgment call, not asserted as mandatory).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all "already installed" versions read directly from lockfiles/config; Playwright version cross-referenced from 2 independent live sources
- Architecture: HIGH for backend/frontend (all directly read source); MEDIUM for the Playwright/Docker-Compose CI plumbing (grounded in this repo's actual workflow YAML, but the "reusable workflow" DRY recommendation and the `wait-on`-vs-`webServer` choice rest partly on general Playwright/GH Actions ecosystem convention, not repo-specific precedent)
- Pitfalls: HIGH for the 5 repo-specific pitfalls (unexported `ReportPage`, tsconfig/eslint/vitest scope collision, staging/main image asymmetry, missing backend/frontend healthchecks, required `.env` for backend boot) — all directly verified against actual files; MEDIUM for the general Vitest fake-timer microtask-ordering pitfall and jsdom SVG limitations (well-documented ecosystem-wide, not specific to this repo, but directly relevant to this phase's exact test shapes)

**Research date:** 2026-08-05
**Valid until:** ~30 days for the backend/frontend architecture facts (stable, only changes if this codebase changes); ~7-14 days for the exact Playwright version pin (fast-moving ecosystem) — re-verify `@playwright/test`'s latest version at implementation time regardless of this document's age
