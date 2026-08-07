---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
plan: 06
subsystem: api
tags: [fastapi, sqlmodel, react, retake, gap-closure]

# Dependency graph
requires:
  - phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
    plan: 01
    provides: "_get_or_create_draft_assessment — the race-safe version-increment helper reused here"
provides:
  - "POST /initiatives/{id}/retake — the missing state transition that resets Initiative.status from submitted back to draft and creates a version-incremented blank draft Assessment"
  - "Dashboard confirm dialog now performs the real unlock before navigating to /questionnaire"
  - "Real end-to-end test coverage (submit -> 403 -> retake -> 200) proving the retake flow works through the actual HTTP path"
affects: [15-VERIFICATION (closes Gap 1 / HIST-01), phase-16-report-and-admin-rebuild]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-module reuse of a private helper (_get_or_create_draft_assessment) via direct import from questionnaire.py into initiatives.py rather than duplicating version-increment logic — verified no circular import (questionnaire.py does not import initiatives.py)"
    - "antd Modal.confirm onOk re-throws on failure to keep the dialog open (async onOk semantics), mirroring the existing handleGenerateReport try/catch/reportError convention rather than introducing a new error-display pattern"

key-files:
  created:
    - backend/tests/api/test_retake_flow.py
  modified:
    - backend/app/api/v1/initiatives.py
    - frontend/src/routes/_app/dashboard.tsx
    - docs/api/openapi.json

key-decisions:
  - "retake_initiative reuses _get_or_create_draft_assessment verbatim rather than duplicating the version-increment/race-safety logic — the initiative.status reset and the new draft insert commit atomically in the same session/transaction (the helper performs its own commit)"
  - "Task 3 was flagged tdd=\"true\" in the plan but its own scope is solely to add the end-to-end test — the endpoint (Task 1) and frontend wiring (Task 2) were already implemented and committed first, mirroring the exact precedent set by 15-01's Task 2/Task 3 split (implemented as a single test commit rather than a literal RED/GREEN split, since the behavior under test was not new when the test was written)"

requirements-completed: [HIST-01]

coverage:
  - id: D1
    description: "POST /initiatives/{id}/retake — ownership re-derived (404/403), 409 guard if not currently submitted, resets Initiative.status to draft and creates a version-incremented blank draft Assessment via the reused _get_or_create_draft_assessment"
    requirement: "HIST-01"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_retake_flow.py#test_submit_then_retake_unlocks_editing_and_creates_v2_draft"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_retake_flow.py#test_retake_on_never_submitted_initiative_returns_409"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_retake_flow.py#test_retake_rejects_non_owner"
        status: pass
    human_judgment: false
  - id: D2
    description: "Dashboard confirm dialog (handleStartOrRetake) awaits POST /retake before navigating; failed retake keeps the dialog open via a re-thrown promise and surfaces an error through the existing reportError/Alert convention"
    requirement: "HIST-01"
    verification:
      - kind: unit
        ref: "npx tsc -b --noEmit (frontend) — clean"
        status: pass
      - kind: unit
        ref: "npx eslint src/routes/_app/dashboard.tsx — clean"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-26
status: complete
---

# Phase 15 Plan 06: Retake Flow Gap Closure (HIST-01) Summary

**Adds the missing `POST /initiatives/{id}/retake` endpoint that resets `Initiative.status` from `submitted` back to `draft` and creates a version-incremented blank draft `Assessment` via the reused `_get_or_create_draft_assessment` helper, wires the dashboard's confirm dialog to call it before navigating, and closes the verifier-flagged gap with a real end-to-end HTTP test (submit -> 403 -> retake -> 200).**

## Performance

- **Duration:** ~20 min active execution
- **Completed:** 2026-07-26
- **Tasks:** 3/3 completed
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- New `POST /initiatives/{id}/retake` route in `backend/app/api/v1/initiatives.py`: re-derives ownership (404/403), rejects retake on a non-submitted initiative (409, D-13), resets `Initiative.status` to `draft`, and reuses `_get_or_create_draft_assessment` (imported from `questionnaire.py`, verified no circular import) to atomically create the next version-incremented blank draft `Assessment` in the same transaction.
- Dashboard's `handleStartOrRetake` submitted-branch `Modal.confirm.onOk` is now async: calls `await api.post('/initiatives/{id}/retake')`, navigates to `/questionnaire` only on success, and on failure surfaces an error via the existing `reportError`/`Alert` convention while re-throwing so antd keeps the confirm dialog open instead of navigating into a still-locked questionnaire.
- `backend/tests/api/test_retake_flow.py` (new file, 3 tests): a real end-to-end HTTP test that PUTs an answer, calls the actual `POST /submit`, asserts a subsequent PUT now 403s (proving the lock is real, unlike the prior test's direct-DB-flip bypass), calls the actual `POST /retake`, and asserts the PUT now succeeds (200) on a new v2 draft while the original v1 submitted row and `Initiative.status` behave exactly as specified. Plus a 409 guard test and a 403 ownership test.
- `docs/api/openapi.json` regenerated for the new route (docs-freshness CI gate).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add POST /initiatives/{id}/retake endpoint** - `8f14eb0` (feat)
2. **Task 2: Wire dashboard confirm dialog to call POST /retake** - `1f90581` (feat)
3. **Task 3: End-to-end retake test** - `20381dc` (test)

**Additional commit (docs-freshness gate, tied to Task 1's new route):** `4446319` (docs: regenerate openapi.json)

_Note: Task 3 was flagged `tdd="true"` in the plan but its scope is solely the test file — the endpoint (Task 1) and dashboard wiring (Task 2) were implemented and committed first, per the plan's own task ordering. This mirrors the exact precedent 15-01's SUMMARY documented for its own Task 2/Task 3 split: implemented as a single test commit against already-existing behavior rather than a literal RED/GREEN split, since there was no "new, currently-failing behavior" left to drive with a failing test at the point Task 3 ran._

## Files Created/Modified

- `backend/app/api/v1/initiatives.py` - New `retake_initiative` route (`POST /{initiative_id}/retake`), new import of `_get_or_create_draft_assessment` from `questionnaire.py`
- `frontend/src/routes/_app/dashboard.tsx` - `handleStartOrRetake`'s submitted-branch `onOk` now awaits the retake call before navigating
- `backend/tests/api/test_retake_flow.py` - New end-to-end test file (3 tests: happy path, 409 guard, 403 ownership)
- `docs/api/openapi.json` - Regenerated for the new route (docs-freshness CI gate)

## Decisions Made

- `retake_initiative` reuses `_get_or_create_draft_assessment` verbatim (no duplicated version-increment/race-safety logic) — the helper's own commit atomically persists both the `Initiative.status` reset and the new draft `Assessment` insert in one transaction.
- The frontend's failure path re-throws inside `onOk` so antd's `Modal.confirm` keeps the dialog open on a failed retake, rather than closing and silently leaving the user on the dashboard with no feedback.

## Deviations from Plan

None — plan executed exactly as written. The endpoint signature, guard ordering (404 -> 403 -> 409), reuse of `_get_or_create_draft_assessment`, dashboard wiring, and all three specified tests (happy path / 409 guard / 403 ownership) match the plan's `<action>`/`<behavior>` blocks precisely.

## Issues Encountered

None. `npm install` was required in the frontend worktree before `tsc`/`eslint` could run (fresh worktree checkout, no `node_modules` present) — a one-time setup step, not a deviation from the plan's scope.

## User Setup Required

None - no external service configuration required.

## Verification Results

- `cd backend && uv run ruff check . && uv run mypy app --ignore-missing-imports && uv run pytest tests/api/test_retake_flow.py tests/api/test_questionnaire_answers.py -q` — all green (20 passed).
- `cd frontend && npx tsc -b --noEmit && npx eslint src/routes/_app/dashboard.tsx` — clean.
- `cd backend && uv run python -c "import app.main"` — imports cleanly, no circular import.
- Full backend quick suite (`pytest tests/ -n auto -m "not perf and not benchmark"`): 114 passed, 4 failed — the 4 failures are the pre-existing, local-only WeasyPrint native-library gap documented since Phase 13 in every prior phase's summaries/deferred-items.md, unrelated to this plan.

## Next Phase Readiness

- HIST-01 (Gap 1 from `15-VERIFICATION.md`) is closed: a user who submits, confirms "Start new assessment", and lands on `/questionnaire` no longer 403s on the first answer save — the version-increment machinery this phase's migration exists for is now reachable through the real UI/API path, proven end-to-end.
- Gap 2 (CR-02, frozen assessment-history scores / HIST-02) is a separate, already-planned gap-closure plan (15-07) — out of scope for this plan.
- No blockers for 15-07 or subsequent phase-15 verification re-run.

---
*Phase: 15-questionnaire-submission-api-wizard-ui-save-reliability*
*Completed: 2026-07-26*

## Self-Check: PASSED

All 4 created/modified files confirmed present on disk (`backend/app/api/v1/initiatives.py`, `frontend/src/routes/_app/dashboard.tsx`, `backend/tests/api/test_retake_flow.py`, `docs/api/openapi.json`). All 4 commit hashes (`8f14eb0`, `1f90581`, `20381dc`, `4446319`) confirmed present in `git log --oneline --all`.
