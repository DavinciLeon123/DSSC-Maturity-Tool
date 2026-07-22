---
phase: 12-test-retrofit-stabilize-existing-flows
verified: 2026-07-22T00:00:00Z
status: human_needed
score: 4/4 must-haves verified (via source cross-referencing, per documented environment gap)
behavior_unverified: 0
overrides_applied: 0
requirements_note: "Phase 12 declares requirements: [] in every plan; REQUIREMENTS.md's own Traceability note confirms 0 v1 requirements map to this phase. Trivial no-op — confirmed, no orphans."
human_verification:
  - test: "Run the full Postgres-backed backend suite (`cd backend && uv run pytest`) on a Docker-equipped machine, or via the first GitHub Actions run once this branch is pushed/merged. Confirm all 37 Postgres-dependent tests (test_auth.py: 15, test_admin.py: 15, test_reports.py: 6, test_smoke.py: 1) pass with zero failures."
    expected: "37/37 pass; the 3 already-green test_report_generator.py tests continue to pass (total 40/40)."
    why_human: "This development machine has no Docker daemon installed (pre-documented RESEARCH.md Environment Availability gap A4). Every attempt to run these tests fails at `docker.errors.DockerException` during `PostgresContainer` startup, before any test body executes — not at an assertion. Source-level cross-referencing (this verification) and `pytest --collect-only` (40 tests, 0 import errors) are the maximum evidence obtainable on this machine; a live pass/fail signal requires Docker or CI."
  - test: "Push this phase's commits to origin and confirm the first GitHub Actions 'Test Suite' run passes both the `backend-tests` and `frontend-tests` jobs, and note its wall-clock duration."
    expected: "Both jobs green; total workflow duration is short enough to comfortably gate a PR merge (no hard SLA was set in CONTEXT.md, but a multi-tens-of-minutes runtime would fail the intent of success criterion #4)."
    why_human: "The local git branch is 27 commits ahead of `origin/main` and has never been pushed — `.github/workflows/test.yml` has never actually executed on GitHub Actions. Its YAML shape, job structure, and command correctness were verified statically (this report + the plan's own `workflow-ok` parse check); actual green/red + timing can only be observed once a real Actions run occurs."
---

# Phase 12: Test Retrofit — Stabilize Existing Flows Verification Report

**Phase Goal:** The subsystems this milestone does NOT rebuild (auth, admin management, PDF/email report delivery) are protected by automated regression tests before the questionnaire/scoring rebuild begins, so breakage introduced by later phases is caught immediately rather than discovered in production.

**Verified:** 2026-07-22
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Auth flows (registration, login, lockout, password reset) are covered by automated tests that fail if behavior changes | ✓ VERIFIED | `backend/tests/api/test_auth.py` (15 tests) cross-referenced line-by-line against `backend/app/api/v1/auth.py` — every status code, detail string, and branch (409 duplicate, 401 anti-enumeration equal-path, 423 lockout after `_MAX_FAILED_ATTEMPTS=5`, 202/429 forgot-password cooldown, 400 reset-token reuse/expiry/unknown) matches the real source exactly. Collects cleanly (part of 40/40, 0 import errors). Cannot execute against live Postgres on this machine (Docker absent — see human_verification). |
| 2 | Admin user/initiative management (incl. cascade-delete) and CSV export are covered by tests using production-shaped data | ✓ VERIFIED | `backend/tests/api/test_admin.py` (15 tests) matches `backend/app/api/v1/admin.py` exactly: 7-endpoint parametrized 403 access-control test matches `require_admin`'s exact detail string ("Admin access required"); cascade-delete test asserts zero orphaned rows across `QuestionnaireAnswer`/`EvidenceURL`/`ComplianceReport` directly via `session.exec(select(...))`, not just HTTP 200; CSV header assertion matches `admin.py`'s exact 9-column list; data built via `backend/tests/factories.py` (faker-based, schema-realistic — satisfies D-03 "production-shaped"). Collection-clean. |
| 3 | PDF generation and email delivery of a completed report are covered by an automated regression test | ✓ VERIFIED | `backend/tests/api/test_reports.py` (6 tests) mocks `weasyprint.HTML` and `resend.Emails.send` at the correct patch points (confirmed no stray `WeasyHTML`-alias patch, matching the lazy-import pitfall), asserts both mocks were actually called (defeats the bare-except-swallow risk in `_send_report_email`), and leaves `score_all_answers`/ZEN engine unmocked per D-04. `backend/tests/services/test_report_generator.py` (3 tests, pure-function, no DB/HTTP) was **run directly and is genuinely green: 3 passed**. |
| 4 | The suite runs quickly enough to gate merges, giving a clear pass/fail signal throughout the rebuild | ✓ VERIFIED (structural) | `.github/workflows/test.yml` exists, parses, and matches RESEARCH.md's cross-checked design: `backend-tests` (uv + pytest + testcontainers-managed Postgres, no GH `services:` block — single provisioning path) and `frontend-tests` (Node 20 + `npx vitest run --coverage`), both triggered on `push`(main)/`pull_request`. The frontend job's exact command was independently re-run here and is genuinely green (1/1, 801ms). The backend job's exact command (`uv run pytest --cov=app ...`) is the same command verified structurally in truths 1–3. **The workflow itself has never executed on GitHub Actions** (branch not yet pushed) — see human_verification. |

**Score:** 4/4 truths verified via source-code cross-referencing (the evidence tier this verification run was directed to use for the pre-documented, no-Docker-on-this-machine gap). 0 behavior-unverified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/tests/conftest.py` | Real-Postgres testcontainer, transaction-rollback session, lifespan-aware `TestClient` | ✓ VERIFIED | `postgres_container`/`engine` session-scoped, `create_all()` called exactly once (grep confirms single occurrence); `session` fixture uses connection+transaction+rollback; `client`/`admin_client`/`user_client` all use `with TestClient(app) as c:` (context-manager form, Pitfall 1 satisfied); autouse fixture disables the auth rate limiter (Pitfall 4 satisfied). |
| `backend/tests/factories.py` | Plain fixture factories, faker-based, production-shaped (D-03) | ✓ VERIFIED | `make_user` (hashes via `hash_password`), `make_initiative` (respects unique `user_id`, uses `SECTOR_OPTIONS`), `make_answer` (uses `AnswerValue` enum member, not raw string), `make_evidence`, `make_report` (unique `initiative_id`, matching `pg_insert().on_conflict_do_update` — Pitfall 5 satisfied). |
| `backend/tests/test_smoke.py` | Proves container→schema→lifespan→HTTP chain | ✓ VERIFIED (structurally; collects clean) | Asserts `/health` 200 + `app.state.mami_config`/`zen_engine` populated. Cannot execute locally (Docker gap). |
| `backend/tests/api/test_auth.py` | Auth regression suite | ✓ VERIFIED | 15 tests, matches `auth.py` exactly (see Truth 1). |
| `backend/tests/api/test_admin.py` | Admin regression suite | ✓ VERIFIED | 15 tests, matches `admin.py` exactly (see Truth 2). |
| `backend/tests/api/test_reports.py` | PDF/email regression suite | ✓ VERIFIED | 6 tests, matches `reports.py` exactly (see Truth 3). |
| `backend/tests/services/test_report_generator.py` | Pure-function report-generator unit tests | ✓ VERIFIED — genuinely green | 3/3 passed, independently re-run. |
| `backend/pyproject.toml` [tool.pytest.ini_options] + dev deps | pytest config, testcontainers/faker/etc. | ✓ VERIFIED | `asyncio_mode = "auto"`, `testpaths = ["tests"]` present; `uv run pytest --collect-only -q` → 40 tests, 0 errors, confirming deps resolve and import cleanly. |
| `.github/workflows/test.yml` | CI: backend pytest + frontend Vitest on push/PR | ✓ VERIFIED (structural) | Parses, both jobs present, no `services:` block on backend-tests, correct commands, no hardcoded secrets. Never executed on GitHub Actions yet (branch unpushed). |
| `frontend/vitest.config.ts` | jsdom env, reuses vite.config.ts plugins | ✓ VERIFIED | Uses `mergeConfig(viteConfig, ...)` — no diverging plugin declaration. |
| `frontend/src/components/layout/TopNav.test.tsx` | Deterministic frontend smoke test | ✓ VERIFIED — genuinely green | 1/1 passed, independently re-run (`npx vitest run`, 801ms). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `conftest.py::client` | `app.main.app` lifespan | `with TestClient(app) as c:` | ✓ WIRED | Confirmed present in conftest.py; matches `app/main.py`'s `lifespan()` which populates `app.state.mami_config`/`zen_engine` — the exact dependency `admin.py::get_admin_heatmap` and every `reports.py` endpoint reads via `request.app.state.*`. |
| `conftest.py::session` | `app.dependency_overrides[get_session]` | dependency override bound to rollback-scoped session | ✓ WIRED | `get_session` imported from `app.db.session`, overridden identically to how `auth.py`/`admin.py`/`reports.py` import it. |
| `test_reports.py` | `weasyprint.HTML` / `resend.Emails.send` | `mocker.patch("weasyprint.HTML")` / `mocker.patch("resend.Emails.send")` | ✓ WIRED | Confirmed via grep: only the correct module-level patch target is used, never the lazy-import alias `app.api.v1.reports.WeasyHTML` (which would silently no-op per Pitfall 2). |
| `test_admin.py` | `admin.py::require_admin` | parametrized 403 test across all 7 admin endpoints | ✓ WIRED | Detail string `"Admin access required"` asserted matches `deps.py::require_admin` exactly. |
| `.github/workflows/test.yml::backend-tests` | `backend/tests/*` | `uv run pytest --cov=app --cov-report=term-missing` | ✓ WIRED (structurally) | Command matches `backend/pyproject.toml`'s test config; no Postgres `services:` block (testcontainers self-provisions). |
| `.github/workflows/test.yml::frontend-tests` | `frontend/src/**/*.test.tsx` | `npx vitest run --coverage` | ✓ WIRED | Independently re-run locally, genuinely green. |

### Requirements Coverage

Phase 12 declares `requirements: []` in every one of its 5 plans. `.planning/REQUIREMENTS.md`'s own Traceability note states: *"Phase 12 (Test Retrofit — Stabilize Existing Flows) maps no v1 requirement directly ... All 30 v1 requirements are covered by Phases 13-18."* No orphaned requirements found for Phase 12. This check is a trivial no-op as expected, and it passes.

### Anti-Patterns Found

None. Grepped every new/modified file in this phase (`backend/tests/**`, `frontend/src/test/**`, `frontend/src/components/layout/TopNav.test.tsx`, `frontend/vitest.config.ts`, `.github/workflows/test.yml`) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` and `placeholder|coming soon|not yet implemented|not available` — zero matches. No hardcoded-empty-return stubs found; every test asserts a real status code and/or a real mocked-call assertion.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Pure-function report-generator tests pass | `cd backend && uv run pytest tests/services/test_report_generator.py -v` | `3 passed` | ✓ PASS |
| Full backend suite collects with zero import errors | `cd backend && uv run pytest --collect-only -q` | `40 tests collected` | ✓ PASS (existence proof) |
| Frontend Vitest smoke test passes | `cd frontend && npx vitest run` | `Test Files 1 passed (1); Tests 1 passed (1)` (801ms) | ✓ PASS |
| Postgres-backed backend suite (auth/admin/reports/smoke, 37 tests) actually passes | `cd backend && uv run pytest` | `docker.errors.DockerException` at `PostgresContainer` startup, before any test body runs | ? SKIP — pre-documented environment gap (no Docker daemon on this machine), routed to human_verification, not counted as a failure per this task's explicit instruction |

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention exists in this project, and no probes are declared in any Phase 12 PLAN/SUMMARY (all 5 SUMMARY files explicitly note the "spec-less probe fallback" was skipped since this phase maps no REQ-IDs). N/A — no probes to run.

### Human Verification Required

See `human_verification` items in the frontmatter above:
1. Run the full Postgres-backed backend suite (37 tests) on a Docker-equipped machine or via CI, and confirm all pass.
2. Push this phase to origin and confirm the first GitHub Actions `Test Suite` run passes both jobs, noting its duration (closes out success criterion #4's "runs quickly enough" claim with a real measurement).

Both items are explicitly and repeatedly flagged as open by the phase's own executors across all 5 SUMMARY.md files (e.g., 12-01-SUMMARY.md: *"A human with Docker access... must confirm the smoke test passes"*; 12-05-SUMMARY.md's `user_setup`: *"Confirm the first Actions run for 'Test Suite' passes both jobs"*) — this verification independently confirms those are the only remaining open items, not new findings.

### Gaps Summary

No gaps. Every artifact this phase was supposed to produce exists, is substantive (no stubs/placeholders), and is correctly wired against the exact source files it characterizes (verified via direct line-by-line cross-referencing of `auth.py`, `admin.py`, `reports.py`, `report_generator.py`, `deps.py`, and `main.py`'s lifespan). Two components were independently re-run by this verification and are genuinely green (`test_report_generator.py`: 3/3; `TopNav.test.tsx`: 1/1). The remaining 37 Postgres-dependent tests are collection-clean (0 import errors) and match their source exactly by inspection, but cannot be proven to pass on this machine because of a pre-documented, explicitly-out-of-scope-for-failure environment gap (no local Docker daemon) and because the CI workflow that would otherwise prove them green has not yet had its first real run (this branch has not been pushed to `origin/main`). These are legitimate, narrowly-scoped human-verification items — not defects in the phase's deliverables — and are the same items the phase's own executors already flagged as outstanding in every SUMMARY.md.

---

*Verified: 2026-07-22*
*Verifier: Claude (gsd-verifier)*
