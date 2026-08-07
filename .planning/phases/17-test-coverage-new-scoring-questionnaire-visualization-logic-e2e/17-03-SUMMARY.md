---
phase: 17-test-coverage-new-scoring-questionnaire-visualization-logic-e2e
plan: 03
subsystem: E2E Testing / CI-CD Integration
tags: [e2e, playwright, ci-cd, docker-compose, critical-path, automation]
status: complete
completed_date: 2026-08-07
duration_minutes: 45
task_count: 2
commit_count: 2
deviations: none
dependencies:
  requires: []
  provides: [TEST-03, e2e-test-infrastructure, critical-path-coverage]
  affects: [staging-pipeline, main-pipeline, release-readiness]
tech_stack:
  added: [Playwright 1.62.1, wait-on 8.0.0, docker-compose override, GitHub Actions workflow_call]
  patterns: [reusable-workflows, e2e-testing, docker-compose-integration, headless-browser-automation]
key_files:
  created:
    - e2e/package.json
    - e2e/tsconfig.json
    - e2e/playwright.config.ts
    - e2e/docker-compose.e2e.yml
    - e2e/tests/critical-path.spec.ts
    - .github/workflows/e2e-tests.yml
  modified:
    - .github/workflows/staging.yml
    - .github/workflows/main.yml
---

# Phase 17 Plan 03: E2E Playwright Suite (Critical Path) Summary

## Objective

Close Phase 17's TEST-03 requirement: a Chromium-only Playwright E2E suite driving the real critical path (register → answer all 52 questions → submit → view report) through the actual browser UI against the real `docker-compose.yml` stack (db + backend + frontend), running as a new CI job on `staging.yml`/`main.yml` only (never `pr.yml`, mirroring the existing `perf`/`benchmark` marker precedent).

## One-Liner

Playwright E2E suite with critical-path test and reusable CI workflow, integrated into staging (pre-built images) and main (from-source) pipelines, with automatic failure artifact capture (trace/screenshot/logs).

## Execution Summary

### Task 1: E2E Playwright Project Setup

**Commit:** `05fc43a`

Created a new top-level `e2e/` directory (sibling to `frontend/`/`backend/`, entirely outside their tooling scopes):

- **`e2e/package.json`**: Private Playwright project with `@playwright/test ^1.62.1` (verified latest stable version), `wait-on ^8.0.0`, and `typescript ~5.9.3`
- **`e2e/tsconfig.json`**: Isolated TypeScript config (`target: ES2022`, `module: ESNext`, `strict: true`), not part of `frontend/`'s project references
- **`e2e/playwright.config.ts`**: Chromium-only configuration with `timeout: 90_000` (generous for 52 questions across 6 category pages), `retain-on-failure` trace, `only-on-failure` screenshot, GitHub-formatted reporter in CI
- **`e2e/docker-compose.e2e.yml`**: Compose override file adding `image:` refs for backend/frontend (does NOT force rebuild; `docker compose up -d` reuses already-present local images)
- **`e2e/tests/critical-path.spec.ts`**: Single comprehensive test covering the full user journey:
  - Register with consent checkbox
  - Log in
  - Create an initiative
  - Answer all 52 questions across 6 categories (always selecting the 3rd/middle radio option per question)
  - Submit assessment
  - View the generated report (radar chart + priority areas)
  - All locators traced directly against real component source (no `data-testid` exists in codebase); uses role-based, placeholder-based, and type-attribute queries

**Verification:** `cd e2e && npm install && npx tsc --noEmit` — clean compilation with zero errors

### Task 2: Reusable E2E Workflow + CI Integration

**Commit:** `8721182`

Created a reusable workflow and integrated it into staging/main pipelines:

- **`.github/workflows/e2e-tests.yml`** (new reusable workflow):
  - `on: workflow_call` with optional `backend-image` / `frontend-image` inputs (empty = build from source)
  - Creates ephemeral CI `.env` with fixed throwaway values (db user/pw, admin email/pw, secret key)
  - **Staging path** (inputs provided): `docker pull` the pre-built images, then `docker compose -f docker-compose.yml -f e2e/docker-compose.e2e.yml up -d`
  - **Main path** (no inputs): `docker compose up -d --build` from source directly
  - **Readiness:** `npx wait-on http://localhost:8000/health http://localhost:3000 -t 120000` (HTTP-level check, not `docker compose --wait`, because backend/frontend lack healthchecks and would report ready before migrations/seeding complete)
  - **Playwright:** `npm ci`, `npx playwright install --with-deps chromium`, then `npx playwright test`
  - **Failure handling:** Dump `docker compose logs` and upload Playwright report/trace as artifact (14-day retention)
  - **Cleanup:** `docker compose down -v` always (even on success)

- **`.github/workflows/staging.yml`** (edits):
  - **New `e2e` job** (after `docker-build`):
    ```yaml
    e2e:
      needs: docker-build
      uses: ./.github/workflows/e2e-tests.yml
      with:
        backend-image: ${{ needs.docker-build.outputs.backend-image }}
        frontend-image: ${{ needs.docker-build.outputs.frontend-image }}
      secrets: inherit
    ```
  - **Simplified `perf-gate`** job: removed the exit-5 tolerance block (Phase 17-01 now provides dimension-scoring perf tests; the tolerance is dead code)

- **`.github/workflows/main.yml`** (edits):
  - **New `e2e` job** (after quality gates, independent of `docker-build-and-sbom`):
    ```yaml
    e2e:
      needs: [backend-lint, backend-typecheck, frontend-lint, frontend-typecheck, frontend-test, test]
      uses: ./.github/workflows/e2e-tests.yml
      secrets: inherit
    ```
    (No image inputs → builds from source)
  - **Simplified `perf-gate`** job: same exit-5 tolerance removal as staging.yml

**Verification:** `grep -q "e2e-tests.yml" .github/workflows/staging.yml .github/workflows/main.yml` ✓ and `! grep -q "treating as pass" .github/workflows/staging.yml .github/workflows/main.yml` ✓

## Deviations from Plan

None — plan executed exactly as specified.

## Success Criteria Met

- ✓ `e2e/` exists as a fully isolated top-level Playwright project (own `package.json`, `tsconfig.json`, no collision with `frontend/`'s Vitest/ESLint/tsc scope)
- ✓ `e2e/tests/critical-path.spec.ts` drives register → login → initiative creation → answer all 52 questions → submit → view report through real UI locators traced directly against source
- ✓ Reusable `.github/workflows/e2e-tests.yml` runs the suite against real `docker compose` stack with correct HTTP-level readiness waiting and failure-artifact upload
- ✓ `staging.yml` pulls already-pushed `:staging` images via `docker-build`'s outputs; `main.yml` builds from source (no registry push path)
- ✓ Neither `pr.yml` nor any PR-triggered job gains the `e2e` job — it only runs on push to `staging`/`main`
- ✓ The perf-gate exit-5 tolerance is fully removed from both workflows (matching Phase 17-01's `pr.yml` change)
- ✓ TEST-03 requirement satisfied

## Key Implementation Notes

1. **E2E directory isolation:** Placed at repo root (`e2e/`), not inside `frontend/`, to avoid conflicts with Vitest's include-globs, ESLint's file scopes, and `tsconfig.app.json` project references — confirmed via 17-RESEARCH.md's Pitfall 1.

2. **Image-sourcing without rebuilding:** The `e2e/docker-compose.e2e.yml` override file adding `image:` refs does NOT force a rebuild — `docker compose up -d` (no `--build` flag) reuses already-present local images directly. This is Docker Compose's documented behavior when `build:` and `image:` coexist in the same service.

3. **Docker readiness:** `docker compose up --wait` alone is insufficient because `docker-compose.yml` only healthchecks the `db` service; backend/frontend containers report ready the instant their process starts, well before `alembic upgrade head` and admin-seed finish. Using `wait-on` against the HTTP endpoints is the correct pattern.

4. **Staging vs. Main paths:** `staging.yml`'s `docker-build` job pushes real `:staging`-tagged images to `ghcr.io` — the e2e job pulls and reuses them. `main.yml`'s `docker-build-and-sbom` job builds with `push: false, load: true` — those images exist only in that job's ephemeral Docker daemon and are NOT reachable from a separate `e2e` job. The reusable workflow handles both patterns cleanly via optional inputs.

5. **Playwright configuration:** Chromium only (no WebKit/Firefox), `timeout: 90_000ms` (generous for a full 52-question assessment), `forbidOnly` in CI (fails if `.only` is left), `retries: 2` in CI (transient failures are expected in E2E), `workers: 1` in CI (pytest-benchmark precedent: single worker for timing-sensitive tests).

6. **Failure diagnostics:** Playwright's `retain-on-failure` trace and `only-on-failure` screenshot are uploaded as artifacts, plus `docker compose logs` dump — sufficient for debugging without local repro.

## Related Plans / Dependencies

- **Depends on:** 17-01 (dimension-scoring perf tests, unblocks perf-gate simplification)
- **Affects:** Overall release readiness (TEST-03 was a TEST-phase blocker); CI/CD pipeline execution patterns
- **Follows from:** 17-RESEARCH.md's pitfall analysis and 17-CONTEXT.md's architecture guidance

## Files Changed

### Created (5 in e2e/, 1 in workflows/)
- `e2e/package.json` — Project manifest with Playwright 1.62.1
- `e2e/tsconfig.json` — TypeScript config, isolated
- `e2e/playwright.config.ts` — Chromium-only, CI-friendly config
- `e2e/docker-compose.e2e.yml` — Service image overrides
- `e2e/tests/critical-path.spec.ts` — Critical-path test (52 questions, full user flow)
- `.github/workflows/e2e-tests.yml` — Reusable workflow for both staging (pre-built) and main (from-source)

### Modified (2)
- `.github/workflows/staging.yml` — Added `e2e` job, simplified perf-gate
- `.github/workflows/main.yml` — Added `e2e` job, simplified perf-gate

## Test Coverage

Per the plan, the E2E suite is the authorization mechanism — full runtime verification (real browser against real docker-compose stack) happens only in CI once this branch is pushed. This follows the established precedent for Docker-dependent tests (e.g., WeasyPrint PDF generation in `tests/api/test_reports.py`).

Local verification (`cd e2e && npm install && npx tsc --noEmit`) confirms project setup and TypeScript type-checking. Full end-to-end verification (browser automation, database interactions, API calls) is CI-gated.

## Next Steps

- Merge this feature branch into `staging` (PR required)
- CI runs: `staging.yml` should execute the new `e2e` job after `docker-build`, pulling the `:staging` images
- On successful merge to `staging`, the Integration environment auto-deploys and can be manually tested
- Further E2E test additions (additional critical paths, happy-path variants, error scenarios) are out of Phase 17-03's scope and belong to future phases or ongoing maintenance
