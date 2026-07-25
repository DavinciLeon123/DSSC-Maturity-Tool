---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
plan: 02
subsystem: api
tags: [fastapi, sqlmodel, pydantic, dimension-scoring, history-endpoint]

# Dependency graph
requires:
  - phase: 14-scoring-engine-replacement
    provides: compute_dimension_scores (assessment_id-agnostic dimension-scoring service)
  - phase: 13-new-questionnaire-config-schema-data-model-migration
    provides: Assessment entity with version/status/submitted_at fields
provides:
  - "GET /initiatives/{initiative_id}/assessments — owner-scoped, version-ordered submitted-assessment history with per-dimension scores"
  - "list_submitted_assessments(session, initiative_id) service helper"
  - "AssessmentSummary Pydantic schema"
affects: [15-05-history-comparison-ui, phase-16-report-rebuild]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Separate query helper for submitted vs. draft assessments (never generalize get_current_assessment) — RESEARCH Pitfall 5"
    - "Private _to_summary response-shaping helper mirrors the existing _to_read convention in initiatives.py"

key-files:
  created:
    - backend/app/schemas/assessment.py
    - backend/tests/api/test_assessment_history.py
  modified:
    - backend/app/services/dimension_scoring.py
    - backend/app/api/v1/initiatives.py

key-decisions:
  - "list_submitted_assessments is a new, separate query from get_current_assessment — draft and submitted-history are different questions per Pitfall 5, not a generalization"
  - "History ordering is by Assessment.version, not submitted_at — deterministic even under identical/rapid-seeded timestamps"

patterns-established:
  - "History/comparison read endpoints reuse compute_dimension_scores per submitted row rather than deriving a parallel scoring path"

requirements-completed: [HIST-02]

coverage:
  - id: D1
    description: "GET /initiatives/{id}/assessments returns owner-scoped, version-ordered submitted assessment history with per-dimension scores"
    requirement: "HIST-02"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_assessment_history.py#test_assessment_history_ordered_by_version_with_correct_scores"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_assessment_history.py#test_assessment_history_empty_list_when_no_submissions"
        status: pass
    human_judgment: false
  - id: D2
    description: "Ownership is re-derived (404 missing initiative, 403 non-owner) before returning any assessment data"
    requirement: "HIST-02"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_assessment_history.py#test_assessment_history_non_owner_forbidden"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_assessment_history.py#test_assessment_history_missing_initiative_returns_404"
        status: pass
    human_judgment: false
  - id: D3
    description: "Draft (unsubmitted retake) assessments never leak into the history list"
    requirement: "HIST-02"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_assessment_history.py#test_assessment_history_excludes_draft_assessment"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-25
status: complete
---

# Phase 15 Plan 02: Assessment History Read Endpoint Summary

**New GET /initiatives/{id}/assessments endpoint returning owner-scoped, version-ordered submitted assessment history with per-dimension scores, built on a new separate list_submitted_assessments query helper (never reusing the draft-only get_current_assessment).**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-25T00:00:00Z (approx, worktree session)
- **Completed:** 2026-07-25
- **Tasks:** 3
- **Files modified:** 4 (2 new, 2 modified)

## Accomplishments
- New `backend/app/schemas/assessment.py` with `AssessmentSummary` (id, version, submitted_at, overall_average, dimension_scores)
- New `list_submitted_assessments(session, initiative_id)` helper in `dimension_scoring.py`, filtering `AssessmentStatus.submitted` and ordering by `version` — a deliberate sibling to (not a generalization of) the existing draft-only `get_current_assessment`
- New `GET /initiatives/{initiative_id}/assessments` route in `initiatives.py`, with ownership re-derivation copied verbatim from `submit_initiative`, plus a new `_to_summary` private helper mirroring the file's `_to_read` convention
- New `backend/tests/api/test_assessment_history.py` with 5 integration tests: empty list, version-ordering + score-correctness, draft-exclusion, non-owner 403, missing-initiative 404

## Task Commits

Each task was committed atomically:

1. **Task 1: AssessmentSummary schema + list_submitted_assessments helper (Pitfall 5)** - `97f72a0` (feat)
2. **Task 2: GET /initiatives/{id}/assessments history route (HIST-02, D-16, V4)** - `cb6b9b6` (feat)
3. **Task 3: Wave-0 integration tests for the history endpoint (HIST-02)** - `f0c161d` (test)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `backend/app/schemas/assessment.py` - New `AssessmentSummary` Pydantic schema (plain BaseModel, no ORM config — assembled by hand in the route)
- `backend/app/services/dimension_scoring.py` - Added `list_submitted_assessments`, a new sibling query to `get_current_assessment`; `get_current_assessment`/`compute_dimension_scores` left byte-for-byte unchanged
- `backend/app/api/v1/initiatives.py` - Added `GET /{initiative_id}/assessments` route + `_to_summary` helper; new imports for `get_dssc_questionnaire_config`, `AssessmentSummary`, `compute_dimension_scores`, `list_submitted_assessments`
- `backend/tests/api/test_assessment_history.py` - New file, 5 tests covering empty/ordering/ownership/draft-exclusion/score-correctness cases

## Decisions Made
- Kept `list_submitted_assessments` as a wholly separate query rather than parameterizing `get_current_assessment` by status — per RESEARCH Pitfall 5, draft ("what am I filling in now") and submitted-history ("what have I finished") are different questions, and conflating them risked surfacing an in-progress retake as a completed version.
- Ordered the history response by `Assessment.version` (not `submitted_at`) — deterministic even if two rows share an identical or out-of-order `submitted_at` (e.g. rapid test seeding or clock skew).
- Test file constructs `Assessment` rows directly (not via the `make_assessment` factory, which only builds draft-default rows with no `version` parameter) to seed distinct submitted versions without touching `tests/factories.py`, which was outside this plan's file list.

## Deviations from Plan

None - plan executed exactly as written. One minor implementation-detail addition not spelled out in the plan's action text: wrapped the `session.exec(...).all()` result in `list(...)` inside `list_submitted_assessments` to satisfy the declared `list[Assessment]` return type against SQLAlchemy's `Sequence[Assessment]` runtime type (mypy caught this; not a deviation from behavior, just a type-annotation correctness fix, Rule 1).

## Issues Encountered
None.

## Flagged-Edge Sign-Off

Per the plan's `verification` section, the `[EDGE UNRESOLVED]` item flagged in `must_haves.flagged_edge_assumptions` requires an explicit disposition:

> "ordering ties (two versions with an identical submitted_at, e.g. rapid test seeding) resolve by version, but the broader 'what if two versions are equal on every dimension' comparison-semantics question is surfaced here rather than asserted"

**Disposition: verified acceptable (tie resolved by version).** The implemented route orders `list_submitted_assessments` by `Assessment.version`, never by `submitted_at` — so identical or out-of-order `submitted_at` timestamps (rapid seeding, clock skew) cannot produce an ambiguous ordering; `version` is a strictly monotonic per-initiative sequence and is asserted directly in `test_assessment_history_ordered_by_version_with_correct_scores` (which deliberately seeds v2 with an *earlier* `submitted_at` than v1 to prove ordering ignores timestamp). The broader "two versions with identical dimension scores across the board" question is a display/comparison-semantics concern for the frontend comparison table (Plan 15-05, D-16b) — it is not a backend data-correctness defect: the endpoint correctly returns two distinct, independently-scored rows regardless of whether their computed values happen to coincide. Carried forward as context for 15-05, not as an open backend item.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The read-side data contract for HIST-01/HIST-02 (`GET /initiatives/{id}/assessments`) is complete and tested, ready for Plan 15-05's frontend history list + comparison table to consume directly. No blockers. Note that this plan did not touch HIST-01's version-increment write-side logic (`_get_or_create_draft_assessment`'s `version=1` hardcode) or the `(initiative_id, version)` unique constraint — those are explicitly Plan 15-01's scope, executed in parallel in this wave.

---
*Phase: 15-questionnaire-submission-api-wizard-ui-save-reliability*
*Completed: 2026-07-25*

## Self-Check: PASSED

- FOUND: backend/app/schemas/assessment.py
- FOUND: backend/tests/api/test_assessment_history.py
- FOUND: commit 97f72a0
- FOUND: commit cb6b9b6
- FOUND: commit f0c161d
