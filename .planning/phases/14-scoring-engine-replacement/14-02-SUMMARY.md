---
phase: 14-scoring-engine-replacement
plan: 02
subsystem: api
tags: [fastapi, sqlmodel, postgres, scoring, dssc-questionnaire]

requires:
  - phase: 14-scoring-engine-replacement
    provides: "compute_dimension_scores/assert_assessment_complete/get_current_assessment from dimension_scoring.py (Plan 14-01)"
provides:
  - "POST /api/v1/initiatives/{id}/score returns {initiative_id, dimension_scores:[{category_id, name, score}]}"
  - "The endpoint's first-ever 422 completion gate (SCOR-04) — 200 all-zeros for incomplete assessments is gone"
  - "The endpoint's first-ever automated test coverage (backend/tests/api/test_scoring.py)"
affects: [14-03, 14-04, 16-report-rendering]

tech-stack:
  added: []
  patterns:
    - "Ownership-check-then-completion-gate ordering (404/403 before 422) — the shared pattern all remaining Phase 14 endpoints (reports.py, Plan 14-03) must replicate"

key-files:
  created:
    - backend/tests/api/test_scoring.py
  modified:
    - backend/app/api/v1/scoring.py

key-decisions:
  - "Made score_initiative synchronous (dropped async/await) since nothing awaited once the async ZEN engine call was removed — no other call site depends on it being a coroutine"
  - "Added # type: ignore[arg-type] on the assessment.id -> compute_dimension_scores(assessment_id: int) call, matching the exact existing repo precedent for the same SQLModel Optional-PK mypy limitation (reports.py:39, admin.py:99/101)"
  - "Test file adds test_score_422_when_no_assessment_exists (not explicitly named in the plan's 3-test list) alongside the 3 required behaviors, since assert_assessment_complete's no-draft-assessment path is a distinct code branch worth its own assertion"

patterns-established:
  - "Pattern 3: Route-level completion gate call site - assert_assessment_complete(session, initiative_id, config) called immediately after ownership check, before any scoring/report logic — Plan 14-03 replicates this exact call-site shape across reports.py's 4 endpoints"

requirements-completed: [SCOR-04]

coverage:
  - id: D1
    description: "POST /score returns the new per-dimension shape {initiative_id, dimension_scores:[{category_id, name, score}]} for a fully-answered owned initiative, with no ZEN/MoSCoW fields (findings/severity/status/total_answers/critical_count/non_critical_count) in the response"
    requirement: "SCOR-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_scoring.py#test_score_returns_dimension_scores"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /score returns HTTP 422 with detail 'Questionnaire not fully answered' for an incomplete assessment or when no draft assessment exists at all — replacing the prior HTTP 200 all-zeros behavior"
    requirement: "SCOR-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_scoring.py#test_score_422_when_incomplete"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_scoring.py#test_score_422_when_no_assessment_exists"
        status: pass
    human_judgment: false
  - id: D3
    description: "The ownership check (404/403) runs before the completion-gate 422 — a non-owner requesting another user's incomplete initiative gets 403/404, never 422, so completeness state is never leaked to a non-owner (T-14-01)"
    requirement: "SCOR-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_scoring.py#test_score_ownership_before_completion_gate"
        status: pass
    human_judgment: false

duration: 17min
completed: 2026-07-24
status: complete
---

# Phase 14 Plan 02: Scoring Endpoint Adaptation Summary

**Repurposed `POST /initiatives/{id}/score` to return the new per-dimension shape `{initiative_id, dimension_scores}` computed by Plan 14-01's `dimension_scoring` service, gated by a first-ever SCOR-04 422 completion check, with `backend/tests/api/test_scoring.py` as this endpoint's first automated coverage.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-07-24T08:30Z (approx)
- **Completed:** 2026-07-24T08:47Z
- **Tasks:** 2 completed
- **Files modified:** 2 (1 modified, 1 new)

## Accomplishments
- Rewrote `backend/app/api/v1/scoring.py`: removed `import zen`, `get_mami_config`/`get_zen_engine` deps, `score_all_answers`, the `FindingRead` model, and all findings/critical-count aggregation logic. Route now depends on `get_dssc_questionnaire_config` and calls `assert_assessment_complete` then `compute_dimension_scores` from Plan 14-01's service.
- New `ScoreResponse {initiative_id, dimension_scores: list[DimensionScore]}` and `DimensionScore {category_id, name, score}` models replace the old ZEN/MoSCoW `FindingRead`-based shape.
- Preserved the existing ownership check (404 when missing, 403 when not owned) as the first gate, exactly as before — the new 422 completion gate only runs after it, so ordering can't leak completeness state to a non-owner.
- Added `backend/tests/api/test_scoring.py` (4 tests, first-ever automated coverage for this endpoint): happy-path (200, 6 dimension_scores entries, each in [1.0, 5.0], old ZEN/MoSCoW keys absent), 422-when-incomplete, 422-when-no-assessment-exists, and ownership-before-completion-gate (matches `-k ownership`).
- App imports cleanly; ruff/mypy/format clean across the whole `app/` tree; full quick suite (`pytest tests/ -n auto -m "not perf and not benchmark"`) stays at 80/84 passing — same 4 pre-existing local-only WeasyPrint failures as every prior Phase 13/14 plan, unrelated to this change.

## Task Commits

Each task was committed atomically:

1. **Task 1: Repurpose POST /score to the per-dimension shape with the completion gate** - `52333f3` (feat)
2. **Task 2: Add integration tests for /score (happy-path, 422, ownership-first)** - `9ebd2c0` (test)

**Plan metadata:** (this commit) `docs(14-02): complete scoring-endpoint-adaptation plan`

## Files Created/Modified
- `backend/app/api/v1/scoring.py` - Modified in place: new `ScoreResponse`/`DimensionScore` models, `assert_assessment_complete`/`compute_dimension_scores` call, `get_dssc_questionnaire_config` dependency; all ZEN/MoSCoW code removed
- `backend/tests/api/test_scoring.py` - New: 4 integration tests (happy-path, 422-incomplete, 422-no-assessment, ownership-first-ordering)

## Decisions Made
- Made `score_initiative` synchronous (dropped `async`/`await`) since nothing in the new body awaits anything — the only prior `await` was the removed ZEN engine call. No caller depends on this being a coroutine.
- Added `# type: ignore[arg-type]` on `compute_dimension_scores(session, assessment.id, config)` for the SQLModel Optional-int-PK mypy limitation — matches the identical existing precedent in `reports.py:39` and `admin.py:99/101`, not a new pattern.
- Added a fourth test (`test_score_422_when_no_assessment_exists`) beyond the plan's 3 named behaviors, since "no draft assessment at all" and "incomplete assessment" are distinct branches inside `assert_assessment_complete` worth separately asserting.

## Deviations from Plan

None - plan executed exactly as written. The two tasks matched the plan's `<action>` specifications; the two decisions above are direct, unavoidable side effects of the specified change (removing the only `await` call; the existing repo's mypy-ignore convention for the same known limitation) and the one added test extends coverage without changing scope.

## Issues Encountered
None. `uv run ruff format` reformatted one line in the new test file (a `assert all(...)` line exceeding the configured line length) — auto-applied, re-verified clean, no logic change.

## User Setup Required

None - no external service configuration required. This plan modifies an existing endpoint and adds tests only.

## Next Phase Readiness

- `scoring.py` no longer imports `zen`/`get_mami_config`/`get_zen_engine`/`score_all_answers` — Plan 14-03 (parallel, `reports.py`/`report_generator.py`/`admin.py`) is unaffected since it touches disjoint files; both plans leave `deps.py`'s now-unused ZEN dependency definitions in place for Plan 14-04 to delete.
- The app stays importable at the end of this wave; `docs/api/openapi.json` was deliberately NOT regenerated here (schema changed — `ScoreResponse`/`DimensionScore` — but Plan 14-04 regenerates it once, after all Wave 2/3 response-model changes land, per this plan's explicit prohibition).
- The ownership-then-completion-gate call-site pattern established here (`assert_assessment_complete(session, initiative_id, config)` immediately after the ownership check) is the exact shape Plan 14-03 replicates across `reports.py`'s 4 endpoints.
- SCOR-04 marked complete.

---
*Phase: 14-scoring-engine-replacement*
*Completed: 2026-07-24*

## Self-Check: PASSED

- FOUND: backend/app/api/v1/scoring.py
- FOUND: backend/tests/api/test_scoring.py
- FOUND: commit 52333f3
- FOUND: commit 9ebd2c0
