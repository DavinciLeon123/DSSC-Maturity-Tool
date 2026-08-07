---
phase: 17-test-coverage-new-scoring-questionnaire-visualization-logic-e2e
verified: 2026-08-07T08:15:00Z
status: human_needed
score: 14/14 must-haves verified (automated); 1 item requires live CI confirmation
human_verification:
  - test: "Push this branch's PR to `staging` and confirm the new `e2e` job (in staging.yml, calling the reusable e2e-tests.yml workflow) passes: docker compose builds/pulls, backend+frontend become healthy, and e2e/tests/critical-path.spec.ts runs green end-to-end in a real browser."
    expected: "The `e2e` job appears in the staging.yml GitHub Actions run, docker-compose stack becomes healthy via wait-on, and the Playwright critical-path spec (register -> login -> create initiative -> answer 52 questions -> submit -> view report) passes without needing the retry budget."
    why_human: "Full docker-compose + real-Chromium E2E execution cannot be safely verified in this sandbox: this repo's local dev Docker Compose project already has long-running `backend`/`db` containers under the same project name, so a full `docker compose up --build` here risks colliding with (and potentially corrupting) the developer's live dev stack (confirmed firsthand — see Notes). Static verification (locators traced line-by-line against current component source, TypeScript compiles cleanly, workflow YAML wiring confirmed) gives high confidence, but only a real CI run proves the full stack actually completes the flow."
---

# Phase 17: Test Coverage — New Scoring, Questionnaire & Visualization Logic + E2E Verification Report

**Phase Goal:** The rebuilt scoring engine, questionnaire API, wizard, and report rendering have automated test coverage, and a Playwright suite verifies the critical end-to-end path.
**Verified:** 2026-08-07
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every protected endpoint rejects missing/malformed/expired/deleted-user tokens with 401, proven against 3 representative routes | VERIFIED | `backend/tests/api/test_auth_dependency.py` — ran `uv run pytest tests/api/test_auth_dependency.py -v`: 12/12 pass (3 routes x 4 scenarios), each of the 3 distinct `detail` strings asserted |
| 2 | `compute_dimension_scores` has a p95-latency perf test | VERIFIED | `backend/tests/perf/test_dimension_scoring_perf.py` — ran `uv run pytest tests/ -m perf -q`: 1 passed, p95 ≈0.93ms, well under the 1.0s budget |
| 3 | `compute_dimension_scores` has a deterministic output-distribution regression test | VERIFIED | `backend/tests/benchmark/test_dimension_scoring_regression.py` — ran `uv run pytest tests/ -m benchmark -q`: 1 passed, exact golden-value match |
| 4 | `pr.yml`'s `perf-gate` no longer needs the exit-5 tolerance | VERIFIED | `grep -q "treating as pass" .github/workflows/pr.yml` → no match; job body is a bare `uv run pytest tests/ -m perf -q` |
| 5 | `useDebouncedSave` saves only after the 1.5s debounce window | VERIFIED | `frontend/src/hooks/useDebouncedSave.test.ts` test 1 — ran `npx vitest run`: passes; asserts no call at 500ms, exactly one call at 1500ms |
| 6 | Retry-with-backoff `[1s,2s,4s]` reaches terminal `failed` after 3 retries exhausted | VERIFIED | Test 4 (`enters terminal failed state...`) — 4 total `saveAnswer` calls, final state `failed` |
| 7 | HTTP 429 is a distinct `rate-limited` state, no retry consumed | VERIFIED | Test 5 — `saveAnswer` called exactly once, `rate-limited` reached, zero `retrying` calls |
| 8 | Report page renders server radar SVG + priority list via data-driven DOM assertions, no chart-library mocking | VERIFIED | `frontend/src/routes/_app/report.test.tsx` test 1 passes; asserts SVG `polygon[fill]`, text content, priority row names/scores/color-dot styles |
| 9 | `ReportPage` importable in isolation, matching `TopNav.tsx` export convention | VERIFIED | `frontend/src/routes/_app/report.tsx:97` — `export function ReportPage()`; imported directly in `report.test.tsx` |
| 10 | A Playwright test drives the real critical path through the real UI (register -> login -> initiative -> 52 questions/6 categories -> submit -> report) | VERIFIED (static) | `e2e/tests/critical-path.spec.ts` — every locator (`input[type="email"]`, checkbox, `Register`/`Sign In`/`Register Initiative`/`Start Dataspace Maturity Assessment`/`Begin assessment →`/`Next →`/`Submit assessment →`/`Generate heatmap` button names, `radiogroup`/`radio` roles) traced and confirmed against current `register.tsx`, `login.tsx`, `dashboard.tsx`, `WelcomeScreen.tsx`, `WizardPage.tsx`, `AnswerButtonGroup.tsx`, `report.tsx` source. `cd e2e && npx tsc --noEmit` is clean. **Full browser execution against a live stack not run in this sandbox — see Human Verification.** |
| 11 | E2E suite runs against the real docker-compose stack (db+backend+frontend), never mocked/live-Railway | VERIFIED (static) | `e2e/docker-compose.e2e.yml` overrides `backend`/`frontend` `image:` only (matches base `docker-compose.yml` service names/ports 8000/3000); `e2e-tests.yml` pulls/builds via real `docker compose`, no mocking |
| 12 | E2E job runs on push to staging/main, never blocks a PR | VERIFIED | `grep -n "e2e" .github/workflows/pr.yml` → no match; `staging.yml`/`main.yml` both have an `e2e:` job calling `./.github/workflows/e2e-tests.yml` |
| 13 | `staging.yml` reuses `:staging` images; `main.yml` builds from source | VERIFIED | `staging.yml`'s `e2e` job passes `needs.docker-build.outputs.{backend,frontend}-image`; `main.yml`'s `e2e` job passes no image inputs (defaults `""` trigger the from-source `docker compose up -d --build` path) |
| 14 | A failed E2E run uploads a trace/screenshot artifact | VERIFIED | `e2e/playwright.config.ts`: `trace: 'retain-on-failure'`, `screenshot: 'only-on-failure'`; `e2e-tests.yml` has an `if: failure()` `actions/upload-artifact@v4` step for `e2e/playwright-report` + `e2e/test-results` |

**Score:** 14/14 truths pass automated/static verification; truth #10/#11's full live-browser execution is flagged for CI confirmation (see below), consistent with the plan's own stated verification boundary.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/tests/api/test_auth_dependency.py` | Parametrized 401 coverage for `get_current_user` | VERIFIED | 12 tests, all pass; substantive (127 lines, real assertions, no stubs) |
| `backend/tests/perf/test_dimension_scoring_perf.py` | `pytest.mark.perf` p95-latency test | VERIFIED | `pytestmark = pytest.mark.perf`; passes, collects exactly 1 test |
| `backend/tests/benchmark/test_dimension_scoring_regression.py` | `pytest.mark.benchmark` deterministic regression | VERIFIED | `pytestmark = pytest.mark.benchmark`; passes, collects exactly 1 test |
| `.github/workflows/pr.yml` | perf-gate exit-5 tolerance removed | VERIFIED | Simplified to a single `run:` line; no "treating as pass" anywhere |
| `CLAUDE.md` | perf-gate note reflects Phase 17 resolution | VERIFIED | Line 37: "Resolved (Phase 17): ..." replacing the "Temporarily tolerant" note |
| `frontend/src/routes/_app/report.tsx` | Exported `ReportPage` | VERIFIED | `export function ReportPage()` present |
| `frontend/src/routes/_app/report.test.tsx` | Data-driven DOM assertions | VERIFIED | 2 tests (happy path + error path), both pass |
| `frontend/src/hooks/useDebouncedSave.test.ts` | Fake-timer debounce/retry/rate-limit coverage | VERIFIED | 5 tests, all pass, `vi.useFakeTimers` used throughout |
| `e2e/tests/critical-path.spec.ts` | register->questionnaire->submit->report spec | VERIFIED | `test(...)` present; type-checks; locators source-traced |
| `e2e/playwright.config.ts` | Chromium-only, trace/screenshot config | VERIFIED | `projects: [{ name: 'chromium', ... }]`; trace/screenshot config present |
| `.github/workflows/e2e-tests.yml` | Reusable `workflow_call` job | VERIFIED | `on: workflow_call`, full docker-compose + wait-on + playwright + artifact-upload pipeline |
| `.github/workflows/staging.yml` | `e2e` job wired to `docker-build` outputs | VERIFIED | `needs: docker-build`, passes `backend-image`/`frontend-image` |
| `.github/workflows/main.yml` | `e2e` job building from source | VERIFIED | `needs: [backend-lint, backend-typecheck, ...]`, no image inputs |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `test_auth_dependency.py` | `app/core/deps.py::get_current_user` | `client` TestClient against real routes | WIRED | 12/12 requests return 401 with the correct `detail` string per code path |
| `test_dimension_scoring_perf.py` | `app/services/dimension_scoring.py::compute_dimension_scores` | `benchmark()` wrapper, direct call | WIRED | Confirmed via actual test run + p95 stats extraction |
| `useDebouncedSave.test.ts` | `frontend/src/lib/questionnaire.ts::saveAnswer` | `vi.mock('../lib/questionnaire')` | WIRED | Mock intercepts real import path; verified against actual `useDebouncedSave.ts` retry/backoff/429 logic, which matches test assumptions exactly |
| `report.test.tsx` | `frontend/src/lib/reports.ts::fetchReportData` | `vi.mock('../../lib/reports')` | WIRED | Mock intercepts real import path; component renders mocked contract correctly |
| `staging.yml` | `.github/workflows/e2e-tests.yml` | `uses:` + `needs.docker-build.outputs.*` | WIRED | Confirmed in file; not yet exercised by a real CI run (see human verification) |
| `e2e-tests.yml` | `e2e/tests/critical-path.spec.ts` | `npx playwright test` against `docker compose` stack | WIRED (static) | Confirmed in file; runtime pass not exercised in this sandbox |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TEST-01 | 17-01-PLAN.md | Backend pytest coverage for scoring engine, questionnaire API, auth flows | SATISFIED | New auth-negative + perf/benchmark tests, on top of pre-existing `test_dimension_scoring.py` (incl. zero/partial-answer 422 edge cases already covered per Phase 12), `test_questionnaire.py`, `test_submit_completeness.py`, `test_auth.py` |
| TEST-02 | 17-02-PLAN.md | Frontend Vitest+RTL coverage for wizard save/state logic and report rendering | SATISFIED | `useDebouncedSave.test.ts` (5 tests) + `report.test.tsx` (2 tests), all pass |
| TEST-03 | 17-03-PLAN.md | Playwright E2E suite covers critical path | SATISFIED (pending live CI confirmation) | `e2e/tests/critical-path.spec.ts` + reusable CI wiring; static verification complete, live run not yet exercised |

No orphaned requirements: REQUIREMENTS.md's Traceability table maps TEST-01/02/03 to Phase 17, and all three appear in exactly one plan's `requirements:` frontmatter each. (Note: REQUIREMENTS.md's checkbox list and Traceability-table `Status` column for TEST-01/02/03 still read `[ ]`/`Pending` as of this verification — expected, since that file is updated at phase-completion bookkeeping time, not mid-verification; not a functional gap.)

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `e2e/` (whole dir) | — | No `e2e/.gitignore` — `e2e/node_modules/` and `e2e/package-lock.json` are untracked-but-not-ignored (confirmed via `git status`) | ⚠️ Warning | A future `git add -A`/`git add e2e/` could accidentally stage hundreds of `node_modules` files. `frontend/.gitignore` has its own `node_modules` entry; `e2e/` has no equivalent. Not a functional blocker — recommend adding `e2e/.gitignore` (node_modules, playwright-report/, test-results/) before merge. |
| `CLAUDE.md` | 27 | Still says "The 5 GitHub Actions workflows" — `.github/workflows/` now has 6 files (`e2e-tests.yml` added) | ℹ️ Info | Defensible either way since `e2e-tests.yml` is a reusable `workflow_call`-only sub-workflow, not an independently-triggered one — but worth a maintainer's judgment call, not a functional issue. |

No blocker-level anti-patterns (TODO/FIXME/placeholder/stub returns) found in any of the 13 new/modified files reviewed.

### Human Verification Required

### 1. Live CI run of the `e2e` job on `staging`

**Test:** Push this branch through a PR into `staging` and watch the `e2e` job (added to `staging.yml`, calling the reusable `.github/workflows/e2e-tests.yml`) run to completion.
**Expected:** Docker images are pulled (`:staging` tags from `docker-build`), the stack becomes healthy via `wait-on` against `/health` and `:3000`, and `e2e/tests/critical-path.spec.ts` passes — register, login, create initiative, answer all 52 questions across 6 categories, submit, and view the report, all through the real browser UI.
**Why human:** This sandbox's local Docker environment already runs this same repo's `docker-compose.yml` project under long-running dev containers (`dssc-maturity-tool-backend-1`/`dssc-maturity-tool-db-1`, up for 3 days). Attempting a full local `docker compose up --build` here collides on the same Compose project name as that live dev stack. I started this once to get real confidence, then aborted after confirming it hadn't yet reached the container-recreation step (killed the build process, restored the original `.env`, and confirmed the pre-existing `backend`/`db` containers were untouched and `/health` still returns 200) — see Notes below. Every locator in `critical-path.spec.ts` was instead traced line-by-line against the actual current component source (`register.tsx`, `login.tsx`, `dashboard.tsx`, `WelcomeScreen.tsx`, `WizardPage.tsx`, `AnswerButtonGroup.tsx`, `report.tsx`) and matches exactly, and `npx tsc --noEmit` on `e2e/` is clean — but only a real isolated CI run (or a local run in an isolated Compose project) proves the full stack completes without a runtime surprise (timing, readiness-wait edge case, etc.).

## Gaps Summary

No blocking gaps. All 3 plans' must-haves are verified against the actual codebase, not just SUMMARY claims — every backend/frontend test file was executed directly (not just read), all passed, and every E2E locator was cross-checked against live component source rather than trusted from the plan's own interface notes. The only open item is the live-CI confirmation of the new `e2e` GitHub Actions job, which is an explicit, pre-acknowledged verification boundary in 17-03-PLAN.md itself ("Full runtime verification happens in CI once this branch is pushed... Docker-Compose + real-browser E2E execution cannot be fully proven inside this planning/execution sandbox") — not a shortcut taken during this verification pass. Two minor, non-blocking hygiene items are noted above (missing `e2e/.gitignore`; CLAUDE.md's "5 workflows" count).

## Notes

During verification, an attempt was made to run the E2E suite locally against a real `docker compose up --build` to obtain full runtime confidence. This was aborted partway through after recognizing the local Docker Compose project name collides with this machine's existing long-running dev stack for the same repo. Sequence, for the record: overwrote root `.env` with throwaway CI-style values (mirroring `e2e-tests.yml`'s own approach) -> started `docker compose up -d --build` in the background -> recognized the collision risk -> restored the original `.env` from a local backup -> located and killed the in-flight `docker-compose`/`docker-buildx` processes -> confirmed via `docker compose ps -a` and `curl http://localhost:8000/health` that the pre-existing `backend`/`db` containers were never recreated and remained healthy throughout, and confirmed byte-for-byte that `.env` matches its pre-verification content. No lasting changes were made to the running environment. This is flagged transparently rather than silently retried, per this exercise's own "do not trust claims, verify against the real codebase" mandate — but a live CI run remains the safer and more conclusive way to close this last item.

---

_Verified: 2026-08-07_
_Verifier: Claude (gsd-verifier)_
