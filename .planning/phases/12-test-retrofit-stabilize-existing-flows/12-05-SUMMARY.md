---
phase: 12-test-retrofit-stabilize-existing-flows
plan: 05
subsystem: testing
tags: [vitest, testing-library, jsdom, github-actions, ci, pytest, uv, testcontainers]

requires:
  - phase: 12-02
    provides: backend/tests/api/test_auth.py (auth regression suite the backend-tests CI job runs)
  - phase: 12-03
    provides: backend/tests/api/test_admin.py (admin cascade-delete/CSV/heatmap regression suite)
  - phase: 12-04
    provides: backend/tests/api/test_reports.py + tests/services/test_report_generator.py (PDF/email regression suite)
provides:
  - .github/workflows/test.yml — first CI in this repo (Test Suite: backend-tests + frontend-tests)
  - frontend/vitest.config.ts + frontend/src/test/setup.ts — frontend Vitest harness
  - frontend/src/components/layout/TopNav.test.tsx — deterministic frontend smoke test
affects: [13-config-schema-migration, 14-scoring-engine-replacement, 15-questionnaire-wizard, 16-report-contract, 17-test-coverage-e2e, 18-security-hardening]

tech-stack:
  added: ["vitest@4.1.10", "@vitest/coverage-v8@4.1.10", "jsdom@29.1.1", "@testing-library/react@16.3.2", "@testing-library/jest-dom@7.0.0", "@testing-library/user-event@14.6.1", "GitHub Actions (astral-sh/setup-uv@v7, actions/setup-node@v7, actions/checkout@v7)"]
  patterns: ["Vitest config via mergeConfig reusing vite.config.ts's plugin array (no diverging TanStackRouterVite config)", "Mock @tanstack/react-router hooks + api client at module boundary for deterministic smoke tests", "testcontainers-provisioned Postgres in CI (no GH Actions services: block)"]

key-files:
  created:
    - .github/workflows/test.yml
    - frontend/vitest.config.ts
    - frontend/src/test/setup.ts
    - frontend/src/components/layout/TopNav.test.tsx
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/.gitignore

key-decisions:
  - "Frontend package legitimacy audit (Task 1 blocking-human checkpoint) approved as-presented — no substitutions"
  - "vitest.config.ts uses Vitest's recommended mergeConfig(viteConfig, ...) pattern rather than duplicating the plugin array"
  - "TopNav smoke test mocks @tanstack/react-router (useNavigate, Link) and the local api client module rather than wiring a real router/network layer — CI-wiring smoke test per RESEARCH.md Open Question 1; deep interaction testing deferred to Phase 17"
  - "Added coverage/ to frontend/.gitignore (Rule 3 — generated vitest --coverage output was untracked after local verification runs)"

patterns-established:
  - "Vitest config composes vite.config.ts via mergeConfig — future frontend test config changes should extend this file, not create a second diverging config"
  - "Component smoke tests mock router hooks + api client at the module boundary (vi.mock) rather than requiring full provider/router wiring — reusable for Phase 17's broader frontend test suite"

requirements-completed: []

coverage:
  - id: D1
    description: "Frontend Vitest harness (config + jsdom setup) runs a deterministic green smoke test locally and in CI"
    verification:
      - kind: unit
        ref: "frontend/src/components/layout/TopNav.test.tsx#TopNav > renders the navigation header deterministically"
        status: pass
    human_judgment: false
  - id: D2
    description: "GitHub Actions workflow (.github/workflows/test.yml) with backend-tests and frontend-tests jobs, correctly structured per RESEARCH.md draft (no services: block, no hardcoded secrets)"
    verification:
      - kind: other
        ref: "uv run python -c \"import yaml; ...\" workflow YAML parse + jobs/services assertions — workflow-ok"
        status: pass
    human_judgment: true
    rationale: "The workflow's actual green/red outcome can only be proven by GitHub Actions itself running on a Docker-enabled runner — this local machine has no Docker daemon (RESEARCH.md A4), so the backend-tests job's testcontainers-Postgres path was verified structurally (YAML shape, no services: block, correct commands) but not executed end-to-end. Per plan's user_setup note, the developer must confirm the first Actions run for 'Test Suite' passes both jobs on the PR."

duration: 25min
completed: 2026-07-22
status: complete
---

# Phase 12 Plan 05: CI Bootstrap + Frontend Vitest Harness Summary

**Stood up the repo's first GitHub Actions CI (backend pytest via testcontainers-Postgres + frontend Vitest) and wired a deterministic Vitest smoke test so the frontend CI job runs real content instead of no-opping.**

## Performance

- **Duration:** ~25 min (continuation from Task 1's blocking-human checkpoint, which was approved by the human before this session)
- **Completed:** 2026-07-22T09:52:47Z
- **Tasks:** 3 (Task 1: checkpoint, approved in a prior session; Task 2 + Task 3: executed this session)
- **Files modified:** 8 (5 new, 3 modified)

## Accomplishments
- Installed the audited frontend dev dependencies at exact pinned versions (vitest 4.1.10, @vitest/coverage-v8 4.1.10, jsdom 29.1.1, @testing-library/react 16.3.2, @testing-library/jest-dom 7.0.0, @testing-library/user-event 14.6.1) — `package-lock.json` confirmed to resolve these exact versions from the standard npmjs.org registry, no unexpected substitute
- Created `frontend/vitest.config.ts` (jsdom environment, globals, setupFiles) via Vitest's `mergeConfig(viteConfig, ...)` pattern — reuses `vite.config.ts`'s `TanStackRouterVite` + `react()` plugin array and `/api` proxy without duplicating/diverging them
- Added `frontend/src/components/layout/TopNav.test.tsx`, a deterministic render smoke test (mocks the api client and `@tanstack/react-router` hooks) — `npx vitest run` and `npx vitest run --coverage` both pass locally (1/1 tests green)
- Added a `"test": "vitest run"` script to `frontend/package.json`
- Created `.github/workflows/test.yml` — `Test Suite` workflow with `backend-tests` (uv + pytest + coverage, no `services:` block since testcontainers provisions its own Postgres) and `frontend-tests` (Node 20 + Vitest) jobs, triggered on `push` (main) and `pull_request`

## Task Commits

Each task was committed atomically:

1. **Task 1: Frontend package legitimacy verification before npm install (T-12-SC)** — checkpoint only, no commit (approved by human in a prior session; see Checkpoint History below)
2. **Task 2: Frontend Vitest config + deterministic smoke test** - `3e24d04` (feat)
3. **Task 3: GitHub Actions workflow (backend + frontend jobs)** - `91bc7cc` (feat)

_Note: Task 1 is a pure `checkpoint:human-verify` gate with no file changes — nothing to commit for it._

## Checkpoint History

**Task 1 (checkpoint:human-verify, gate="blocking-human"):** Presented the RESEARCH.md "Package Legitimacy Audit" frontend rows (vitest, @vitest/coverage-v8, jsdom, @testing-library/react, @testing-library/jest-dom, @testing-library/user-event) with their canonical GitHub orgs and pinned versions. Human responded "approved" with no changes to package names or versions. Task 2's `npm install` then ran exactly those versions — confirmed via `package-lock.json` inspection (all 6 packages resolved to the audited version + `registry.npmjs.org` tarball URL).

## Files Created/Modified
- `frontend/vitest.config.ts` - Vitest config; jsdom environment, globals, setupFiles, reuses vite.config.ts plugins via mergeConfig
- `frontend/src/test/setup.ts` - imports `@testing-library/jest-dom/vitest` matchers
- `frontend/src/components/layout/TopNav.test.tsx` - deterministic render smoke test for TopNav, mocking api client + router hooks
- `frontend/package.json` - added `"test": "vitest run"` script + 6 new devDependencies
- `frontend/package-lock.json` - resolved frontend dev dependency tree (audited versions confirmed)
- `frontend/.gitignore` - added `coverage/` (generated vitest --coverage output)
- `.github/workflows/test.yml` - new; `Test Suite` workflow, `backend-tests` + `frontend-tests` jobs

## Decisions Made
- Used Vitest's recommended `mergeConfig(viteConfig, defineConfig({ test: {...} }))` pattern in `vitest.config.ts` rather than re-declaring the plugin array by hand — guarantees the two configs cannot diverge as `vite.config.ts` evolves
- Mocked `@tanstack/react-router`'s `useNavigate`/`Link` and the local `../../lib/api` module in the TopNav smoke test rather than standing up a real router/query-client network layer — keeps the test deterministic and fast, consistent with RESEARCH.md Open Question 1's recommendation that Phase 12 only needs CI-wiring, not deep interaction coverage (that's Phase 17/TEST-02)
- Kept `.github/workflows/test.yml` a direct, unmodified application of RESEARCH.md's Code Examples draft (action versions, structure, env) since it was already cross-checked against GitHub/astral-sh/Docker docs during research

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `coverage/` to `frontend/.gitignore`**
- **Found during:** Task 3 verification (ran `npx vitest run --coverage` locally to confirm the frontend CI job's exact command works)
- **Issue:** Running `--coverage` locally generated an untracked `frontend/coverage/` directory that would otherwise be left as stray untracked output
- **Fix:** Added `coverage` to `frontend/.gitignore`
- **Files modified:** `frontend/.gitignore`
- **Verification:** `git status --short` shows no untracked files after the addition
- **Committed in:** `91bc7cc` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking/housekeeping)
**Impact on plan:** No scope creep — purely a generated-artifact hygiene fix surfaced by locally reproducing the CI frontend job's exact command.

## Issues Encountered
- This machine has no Docker daemon installed (pre-documented gap, RESEARCH.md Assumption A4), so the `backend-tests` job's testcontainers-Postgres path could not be executed end-to-end locally. Mitigated by: (1) confirming `uv run pytest --collect-only -q` collects all 40 backend tests without import/config errors, and (2) structurally validating the workflow YAML (`workflow-ok` assertion: both jobs present, no `services:` block on `backend-tests`, correct pytest/vitest invocations, no hardcoded secrets). The actual green/red CI outcome must be confirmed by the developer on the first real GitHub Actions run per the plan's `user_setup` note.

## User Setup Required

**External services require manual configuration.**
- **Service:** github-actions
- **Why:** First CI in this repo (D-02). No dashboard config is strictly required — the workflow triggers on `push`/`pull_request` automatically once merged — but the developer should confirm GitHub Actions is enabled for the repository.
- **Action needed:** Confirm the first Actions run for `Test Suite` passes both jobs (`backend-tests`, `frontend-tests`) on the PR. Location: GitHub repo → Actions tab.

## Next Phase Readiness
- Phase 12 (test-retrofit-stabilize-existing-flows) is now fully complete: all 5 plans executed (backend test infra + auth/admin/report regression suites in Plans 01-04, CI + frontend Vitest harness in this plan).
- ROADMAP.md Phase 12 success criterion #4 is structurally satisfied (workflow exists, both jobs correctly configured); full end-to-end proof requires the first real GitHub Actions run, which the developer must confirm per the `user_setup` note above.
- Phases 13-18 now have an automated safety net gating merges — any regression to auth, admin cascade-delete/CSV export, or PDF/email report delivery introduced by the upcoming questionnaire/scoring/report rebuild will be caught by `backend-tests`, and any frontend build/render breakage will be caught by `frontend-tests` (currently the wired-but-minimal TopNav smoke test; Phase 17 expands frontend coverage).
- No blockers for Phase 13.

---
*Phase: 12-test-retrofit-stabilize-existing-flows*
*Completed: 2026-07-22*

## Self-Check: PASSED

All created files verified present on disk; both task commits (`3e24d04`, `91bc7cc`) verified present in git history.
