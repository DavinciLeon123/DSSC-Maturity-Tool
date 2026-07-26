---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
plan: 08
subsystem: api
tags: [fastapi, sqlmodel, completeness-gate, gap-closure]

# Dependency graph
requires:
  - phase: 15-questionnaire-submission-api-wizard-ui-save-reliability (plans 15-06/15-07)
    provides: retake_initiative endpoint, Assessment.dimension_scores frozen-snapshot column
provides:
  - "submit_initiative now enforces the same server-side completeness gate (assert_assessment_complete) every other scoring/reporting endpoint already uses, before freezing a permanent dimension_scores snapshot"
affects: [15-verification, future scoring/reporting phases touching submit_initiative]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Completeness gate ordering: ownership 404/403 first, then assert_assessment_complete, before any mutation that would be silently persisted"
    - "Defer status-flip mutations on an ORM object until after a gate that may raise, to avoid a stale in-memory identity-map mutation surviving a rolled-back/uncommitted request"

key-files:
  created:
    - backend/tests/api/test_submit_completeness.py
  modified:
    - backend/app/api/v1/initiatives.py
    - backend/tests/api/test_retake_flow.py
    - docs/api/openapi.json

key-decisions:
  - "Added assert_assessment_complete(session, initiative_id, config) as the first statement inside submit_initiative's existing `if assessment:` draft branch, mirroring scoring.py:50/reports.py exactly"
  - "Rule 1 auto-fix: reordered submit_initiative so `initiative.status = InitiativeStatus.submitted` is set AFTER the draft-assessment gate passes (not before) -- the old ordering mutated the in-memory Initiative object before the gate could veto it; since the mutation was never committed on a 422, production behavior was unaffected (fresh Session per request), but it left a real latent bug reachable by any session-reuse context (proven by the test harness's shared-session fixture) and was required to make the plan's own 'no partial freeze' test pass"

patterns-established:
  - "New endpoint mutations that must not survive a later-raised gate exception should be sequenced after that gate, not just relying on session.commit() never being reached"

requirements-completed: [HIST-02, SCOR-04]

coverage:
  - id: D1
    description: "POST /initiatives/{id}/submit returns 422 'Questionnaire not fully answered' for an incomplete draft and does not freeze/lock anything"
    requirement: SCOR-04
    verification:
      - kind: integration
        ref: "backend/tests/api/test_submit_completeness.py::test_submit_422_when_incomplete"
        status: pass
    human_judgment: false
  - id: D2
    description: "A fully-answered draft submit still returns 200 and freezes the dimension_scores snapshot"
    requirement: HIST-02
    verification:
      - kind: integration
        ref: "backend/tests/api/test_submit_completeness.py::test_submit_200_when_complete"
        status: pass
    human_judgment: false
  - id: D3
    description: "An idempotent re-submit of an already-submitted initiative (no draft remains) stays 200 -- the gate is skipped, not misapplied"
    requirement: SCOR-04
    verification:
      - kind: integration
        ref: "backend/tests/api/test_submit_completeness.py::test_submit_idempotent_resubmit_stays_200"
        status: pass
    human_judgment: false
  - id: D4
    description: "Pre-existing retake happy-path test updated to fully answer the config before submit, and still passes against the new gate"
    requirement: HIST-02
    verification:
      - kind: integration
        ref: "backend/tests/api/test_retake_flow.py::test_submit_then_retake_unlocks_editing_and_creates_v2_draft"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-26
status: complete
---

# Phase 15 Plan 08: Submit-time completeness gate Summary

**Added the missing `assert_assessment_complete` (SCOR-04) completeness gate to `submit_initiative`, closing the single blocking gap from 15-VERIFICATION.md (5/6 truths) where an incomplete draft (e.g. 1 of 52 questions answered) could be submitted and its garbage `dimension_scores` snapshot permanently frozen with no correction path short of a destructive full retake.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-07-26
- **Tasks:** 2 completed
- **Files modified:** 4 (`backend/app/api/v1/initiatives.py`, `backend/tests/api/test_retake_flow.py`, `docs/api/openapi.json`) + 1 created (`backend/tests/api/test_submit_completeness.py`)

## Accomplishments
- `submit_initiative` now calls `assert_assessment_complete(session, initiative_id, config)` inside its existing draft branch, before the status flip and before `compute_dimension_scores`, mirroring `scoring.py:50`/`reports.py`'s established completion-gate pattern.
- An incomplete draft submit now returns 422 `"Questionnaire not fully answered"` and freezes nothing; a fully-answered draft submit still returns 200 and freezes the snapshot exactly as before; an idempotent re-submit (no draft) still returns 200 since the gate only runs inside the `if assessment:` branch.
- New `backend/tests/api/test_submit_completeness.py` proves all three behaviors via the real HTTP `PUT`/`POST` endpoints (no direct DB status flips), including a proof that an incomplete submit does NOT partially lock the initiative (a subsequent answer PUT still returns 200, not 403).
- Fixed the one pre-existing test that the new gate would otherwise break: `test_retake_flow.py::test_submit_then_retake_unlocks_editing_and_creates_v2_draft` (and `test_retake_rejects_non_owner`'s owner submit) now fully answer the config via the real `PUT` endpoint before submitting.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the completeness gate to submit_initiative** - `f47000d` (feat)
2. **Task 2: Add 422 regression test and fix the pre-existing retake happy-path test** - `4fcdfe6` (test, includes a Rule 1 reorder fix to `initiatives.py`)

**Docs-freshness:** `ad6ea31` (docs: regenerate openapi.json — submit_initiative's docstring addition changed its route description field, no schema change)

**Plan metadata:** committed separately per the executor contract (STATE.md/ROADMAP.md/REQUIREMENTS.md/this SUMMARY).

_Note: Task 2's commit also contains a small Rule 1 bug fix to `initiatives.py` discovered while verifying Task 2's tests — see Deviations below._

## Files Created/Modified
- `backend/app/api/v1/initiatives.py` - `submit_initiative` gains the `assert_assessment_complete` gate call and import; the `initiative.status` mutation was reordered to run only after the gate passes (Rule 1 fix)
- `backend/tests/api/test_submit_completeness.py` - new: 422-on-incomplete, 200-on-complete, idempotent-resubmit-stays-200
- `backend/tests/api/test_retake_flow.py` - happy-path test (and the non-owner test's owner submit) now fully answer the config before submit
- `docs/api/openapi.json` - regenerated for the docstring-driven description-field change (docs-freshness CI gate)

## Decisions Made
- Placed the gate call as the first statement inside the existing `if assessment:` branch exactly as the plan specified (no unconditional top-of-function call), preserving the idempotent re-submit's 200.
- Rule 1 auto-fix: reordered `initiative.status = InitiativeStatus.submitted` / `session.add(initiative)` to run AFTER the draft-assessment gate block, not before. Rationale: the old ordering mutated the in-memory `Initiative` ORM object unconditionally before the gate could veto the request. Since a raised `HTTPException` prevents `session.commit()`, this mutation was never persisted to the database in production (each request gets a fresh `Session` via `with Session(engine) as session: yield session`, so a subsequent request never sees it). However, in the test harness's function-scoped `session` fixture — shared across every request within one test via SQLAlchemy's identity map — the mutated-but-uncommitted `Initiative.status` attribute *did* remain visible to a later request in the same test, which would have incorrectly 403'd a subsequent answer PUT after a 422 submit, breaking the plan's own required "no partial freeze" assertion. Reordering the mutation to only happen once the gate has already passed eliminates this latent risk entirely (no behavior change for the happy path — status is still set exactly once per successful submit) rather than working around it purely in test code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reordered `initiative.status` mutation to occur after the completeness gate**
- **Found during:** Task 2 (writing `test_submit_422_when_incomplete`'s "did not lock the initiative" assertion)
- **Issue:** `submit_initiative` set `initiative.status = InitiativeStatus.submitted` unconditionally at the top of the function, before the newly-added completeness gate could raise. The mutation was never committed on a 422 (correct end-state), but left the in-memory ORM object incorrectly mutated for the remainder of any session that outlives the failed request — a real latent correctness risk in any session-reuse context, and the exact scenario the plan's own acceptance criteria required proving false.
- **Fix:** Moved the `initiative.status`/`initiative.updated_at`/`session.add(initiative)` block to run after the `if assessment: assert_assessment_complete(...)` block, so the mutation is only ever applied once the gate (if applicable) has already passed.
- **Files modified:** `backend/app/api/v1/initiatives.py`
- **Verification:** `test_submit_422_when_incomplete`'s subsequent-PUT-returns-200 assertion passes; full `if assessment:`-branch and idempotent-resubmit behavior unchanged and still green.
- **Committed in:** `4fcdfe6` (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug fix)
**Impact on plan:** Necessary for correctness and to satisfy the plan's own required test assertion. No scope creep — `retake_initiative`, `list_assessment_history`, `_to_summary`, `_to_read`, the `dimension_scores` column, and migration `k2b3c4d5e6f7` were not touched.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The single blocking gap from 15-VERIFICATION.md (2026-07-26, gaps_found, 5/6 truths) is now closed; all 6 truths should hold on re-verification.
- Full local quality gate green: ruff/mypy clean, 121/125 backend tests pass (same 4 pre-existing local-only WeasyPrint `libgobject-2.0-0` failures in `test_reports.py` recurring across every prior Phase 12-15 session on this machine — CI has the native library installed and passes; unrelated to this plan's scope).
- No blockers for closing out Phase 15.

---
*Phase: 15-questionnaire-submission-api-wizard-ui-save-reliability*
*Completed: 2026-07-26*

## Self-Check: PASSED

- FOUND: backend/app/api/v1/initiatives.py
- FOUND: backend/tests/api/test_submit_completeness.py
- FOUND: backend/tests/api/test_retake_flow.py
- FOUND: .planning/phases/15-questionnaire-submission-api-wizard-ui-save-reliability/15-08-SUMMARY.md
- FOUND: f47000d (feat commit)
- FOUND: 4fcdfe6 (test commit)
- FOUND: ad6ea31 (docs commit)
