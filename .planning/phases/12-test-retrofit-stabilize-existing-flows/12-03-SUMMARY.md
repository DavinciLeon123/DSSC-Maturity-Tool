---
phase: 12-test-retrofit-stabilize-existing-flows
plan: 03
subsystem: testing
tags: [pytest, admin, cascade-delete, csv-export, postgres, access-control]

# Dependency graph
requires:
  - phase: 12-01
    provides: "backend/tests/conftest.py fixtures (postgres_container, engine, session, client, admin_client, user_client) and backend/tests/factories.py plain fixture factories"
provides:
  - "backend/tests/api/test_admin.py — 15 tests: access-control boundary (parametrized 403 across all 7 admin endpoints), list_users/list_initiatives, cascade-delete (DB-level orphan assertions), delete_user 404/403, delete_initiative, CSV export header+row-count, heatmap (lifespan-aware)"
affects: [12-04, 12-05, 17]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Parametrized access-control test over an (method, path) endpoint list — a newly added admin endpoint that forgets require_admin fails the suite automatically"
    - "Cascade-delete assertions query Postgres directly via session.exec(select(...)) against the SAME session instance the dependency-override uses, not merely the HTTP 200 response"

key-files:
  created:
    - backend/tests/api/test_admin.py
  modified: []

key-decisions:
  - "Used a fixed non-existent id (999999) for the DELETE endpoints in the parametrized 403 test — require_admin's dependency check runs before the endpoint body executes regardless of whether the path id exists, so the id value is irrelevant to the 403 assertion"
  - "admin_client and the test's own session fixture are the same pytest-cached instance per test, so cascade-delete assertions after an admin_client.delete(...) call correctly observe the committed state without a second DB connection"

patterns-established:
  - "Admin test file structure: access-control-first (parametrized), then list endpoints, then cascade-delete, then CSV export, then heatmap — mirrors 12-PATTERNS.md's ordering"

requirements-completed: []

coverage:
  - id: D1
    description: "Every admin endpoint rejects a plain USER-role token with 403 (require_admin boundary), parametrized across all 7 endpoints"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_admin.py::test_admin_endpoints_reject_plain_user_token_with_403[...] (7 parametrizations)"
        status: unknown
    human_judgment: true
    rationale: "Cannot execute against real Postgres on this machine — no local Docker daemon (pre-flagged RESEARCH.md A4, confirmed again in Plan 01). Collection-verified only (uv run pytest --collect-only: 15 tests collected, zero import errors) plus manual source-level review against admin.py/deps.py. A human with Docker (or the first CI run once .github/workflows/test.yml lands) must confirm this is green."
  - id: D2
    description: "Deleting a user cascades: zero orphaned QuestionnaireAnswer/EvidenceURL/ComplianceReport rows remain in Postgres"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_admin.py::test_delete_user_cascades_all_child_rows"
        status: unknown
    human_judgment: true
    rationale: "Same Docker-gap reason as D1 — collection-verified and manually reviewed against admin.py's _delete_user_cascade/_delete_initiative_children, not executed against real Postgres on this machine."
  - id: D3
    description: "delete_user returns 404 for a missing user and 403 when the target is an ADMIN"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_admin.py::test_delete_user_missing_returns_404, test_delete_user_target_is_admin_returns_403"
        status: unknown
    human_judgment: true
    rationale: "Same Docker-gap reason as D1."
  - id: D4
    description: "CSV export streams text/csv with the current, exact 9-column header set (D-04 characterization lock) and row count equals seeded answer count"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_admin.py::test_export_dataset_csv_shape"
        status: unknown
    human_judgment: true
    rationale: "Same Docker-gap reason as D1."
  - id: D5
    description: "list_users / list_initiatives raw-SQL endpoints return correct shapes against real Postgres; get_admin_heatmap proves the lifespan-populated app.state.mami_config path (Pitfall 1)"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_admin.py::test_list_users_returns_initiative_and_answer_fields, test_list_initiatives_returns_user_email_and_answer_count, test_admin_heatmap_reflects_submitted_initiatives"
        status: unknown
    human_judgment: true
    rationale: "Same Docker-gap reason as D1 — the heatmap test in particular can only be proven correct end-to-end once it actually runs against the lifespan-fired app.state.mami_config in a Docker-equipped environment (CI or a developer machine with Docker installed)."

duration: ~10min
completed: 2026-07-22
status: complete
---

# Phase 12 Plan 03: Admin Access-Control, Cascade-Delete, CSV Export, Heatmap Tests Summary

**15 admin regression tests in backend/tests/api/test_admin.py — parametrized 403 access-control boundary across all 7 admin endpoints, DB-level cascade-delete orphan assertions, exact-9-column CSV export lock, and lifespan-aware heatmap test — collection-verified clean, execution blocked only by this machine's documented missing Docker daemon**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-07-22T09:29:00Z (approx, per STATE.md)
- **Completed:** 2026-07-22T09:33:44Z
- **Tasks:** 2
- **Files modified:** 1 (new)

## Accomplishments
- Task 1: Parametrized access-control test asserting a plain USER-role token gets 403 (with the exact `"Admin access required"` detail) on all 7 admin endpoints — GET `/users`, GET `/initiatives`, GET `/export`, GET `/heatmap`, DELETE `/users/{id}`, DELETE `/initiatives/{id}`, POST `/reset-demo` — pinning T-12-03-PRIV. `list_users`/`list_initiatives` tests assert the documented row shapes (`initiative_name`/`initiative_status`/`answer_count` and `user_email`/`answer_count`) against seeded, production-shaped fixture data.
- Task 2: Cascade-delete test seeds a user with an initiative plus `QuestionnaireAnswer`/`EvidenceURL`/`ComplianceReport` rows, deletes via `admin_client`, and asserts **zero** orphaned rows remain in all three child tables via direct `session.exec(select(...))` queries — not merely the 200 response (T-12-03-CASCADE). `delete_user` 404 (missing user) and 403 (ADMIN target, T-12-03-ADMINDEL) are covered, as is `delete_initiative` (children removed, owning user survives). CSV export test locks the current exact 9-column header and asserts row count equals the seeded answer count (D-04). Heatmap test runs through the lifespan-aware `admin_client` and asserts `total_submitted`/`matrix`/`topic_structure` (Pitfall 1).
- All 15 tests collect cleanly with zero import errors (`uv run pytest tests/api/test_admin.py --collect-only -q`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Admin access-control + list endpoint tests** - `16bd278` (test)
2. **Task 2: Cascade-delete + CSV export + heatmap tests** - `9d6a2be` (test)

## Files Created/Modified
- `backend/tests/api/test_admin.py` - 15 tests covering access-control (parametrized 403), list_users, list_initiatives, cascade-delete (DB-level orphan assertions), delete_user 404/403, delete_initiative, CSV export shape, and heatmap (lifespan-dependent)

## Decisions Made
- Used a fixed non-existent id (`999999`) for the DELETE endpoints in the parametrized 403 test, since `require_admin`'s dependency short-circuits before the endpoint body (and its `session.get(...)` lookup) ever runs — the id value doesn't affect the 403 assertion.
- Relied on pytest's per-test fixture caching: `admin_client` and the test's directly-requested `session` fixture resolve to the same underlying `Session` instance for a given test, so cascade-delete assertions immediately after an `admin_client.delete(...)` call see the committed DB state without needing a second connection or explicit refresh.

## Deviations from Plan

None - plan executed exactly as written. Per the plan's own read_first/action guidance, no bugs or surprising behavior were discovered while writing these tests against the source in `admin.py`/`deps.py` (D-04 backlog: none to log).

## Issues Encountered

**Environment gap (pre-documented, not a code defect):** This execution machine has no Docker daemon installed (confirmed via the same `docker.errors.DockerException: Error while fetching server API version: ... FileNotFoundError` symptom Plan 01's SUMMARY already documented as RESEARCH.md Environment Availability item A4). `uv run pytest tests/api/test_admin.py -x -q` and the narrower `-k "access or forbidden or list"` invocation both fail immediately at the session-scoped `postgres_container` fixture's container-startup step, before any test body executes — this is identical for every test in the file, not specific to any assertion. No fabricated pass is claimed here.

**Evidence gathered instead of a live green run:**
- `uv run pytest tests/api/test_admin.py --collect-only -q` — **15 tests collected, zero import/collection errors** (confirms fixture imports, factory imports, and model imports are all structurally correct).
- `uv run python -m py_compile tests/api/test_admin.py` — compiles cleanly.
- Manual line-by-line review of every assertion against `backend/app/api/v1/admin.py` (full file) and `backend/app/core/deps.py::require_admin` — response shapes, status codes, and detail strings in the tests match the source exactly (e.g., `"Admin access required"`, `"Cannot delete admin users"`, `"User not found"`, the exact 9-column CSV header list).

A human with Docker (or the first CI run once `.github/workflows/test.yml` lands, per D-02/Plan 05) must confirm `uv run pytest tests/api/test_admin.py -x` is green end-to-end. This is the same class of unverified-but-structurally-sound claim Plan 01 and Plan 02 already carry forward for this machine.

## User Setup Required

None new — the existing Docker Desktop/Colima/Podman local-setup requirement documented in `backend/tests/README.md` (Plan 01) covers this plan's tests too; no additional external tooling is needed.

## Next Phase Readiness
- `backend/tests/api/test_admin.py` is structurally complete and import-clean; ready to run green as soon as a Docker-equipped environment (developer machine or CI) executes it.
- Success criterion #2 (admin user/initiative management, cascade-delete, CSV export covered by automated tests) is met at the code-authoring level; end-to-end verification is deferred to Wave 3's CI stand-up (Plan 05) or a developer machine with Docker.
- No blockers for Plan 04 (report/PDF/email tests) — it depends on 12-01's fixtures only, same as this plan.

## Backlog items discovered (D-04)

None — no bugs or surprising behavior were discovered while writing these characterization tests. Current `admin.py` behavior (access-control 403s, cascade-delete FK ordering, 404/403 delete_user branches, CSV column set, heatmap shape) matches the plan's expectations exactly.

## Known Stubs

None — no hardcoded empty/placeholder values reach any UI or API response in this test-only plan.

## Self-Check: PASSED

- FOUND: backend/tests/api/test_admin.py
- FOUND commit 16bd278 (Task 1)
- FOUND commit 9d6a2be (Task 2)

---
*Phase: 12-test-retrofit-stabilize-existing-flows*
*Completed: 2026-07-22*
