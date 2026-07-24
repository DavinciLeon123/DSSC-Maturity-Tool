---
phase: 14-scoring-engine-replacement
plan: 01
subsystem: api
tags: [fastapi, sqlmodel, postgres, scoring, dssc-questionnaire]

requires:
  - phase: 13-new-questionnaire-config-schema-data-model-migration
    provides: "Assessment entity, reshaped QuestionnaireAnswer (assessment_id/category_id/score), dssc_questionnaire_config cached at startup"
provides:
  - "compute_dimension_scores(session, assessment_id, config) -> list[dict] — equal-weight per-category average, SCOR-01/02"
  - "assert_assessment_complete(session, initiative_id, config) -> Assessment — server-side completion gate, SCOR-04"
  - "get_current_assessment(session, initiative_id) -> Assessment | None — most-recent draft lookup"
affects: [14-02, 14-03, 14-04, 16-report-rendering]

tech-stack:
  added: []
  patterns:
    - "Config-as-source-of-truth for structure (category ids/names/question counts) — never a hardcoded count, mirrors questionnaire.py's valid_categories_by_question idiom"
    - "SQLModel select().group_by() aggregation for per-category sums, matching admin.py's existing GROUP BY idiom"
    - "Single generic 422 detail string for both no-assessment and incomplete-assessment cases (no missing-question-id disclosure)"

key-files:
  created:
    - backend/app/services/dimension_scoring.py
    - backend/tests/services/test_dimension_scoring.py
  modified: []

key-decisions:
  - "Colocated compute_dimension_scores and assert_assessment_complete in one new service module (RESEARCH Open Question 1 recommendation) rather than splitting into two files"
  - "Used the same generic 422 detail (\"Questionnaire not fully answered\") for both the no-draft-assessment and incomplete-assessment cases (RESEARCH Open Question 2 recommendation)"
  - "get_current_assessment filters on AssessmentStatus.draft ordered by created_at desc, matching questionnaire.py's existing draft lookup exactly — deliberately does NOT reuse reports.py's multi-assessment _get_answers_for_initiative join"

patterns-established:
  - "Pattern 1: Dimension Score Computation - per-category equal-weight mean, rounded to 2dp via round(), derived entirely from config['categories']"
  - "Pattern 2: Completion Gate - assert_assessment_complete as the shared 422 gate all five score/report endpoints will call in Plans 02/03"

requirements-completed: [SCOR-01, SCOR-02, SCOR-04]

coverage:
  - id: D1
    description: "compute_dimension_scores returns one entry per config category, in config order, score = round(sum/count, 2) in [1.0, 5.0], with no cross-category weighting"
    requirement: "SCOR-01"
    verification:
      - kind: unit
        ref: "backend/tests/services/test_dimension_scoring.py#test_full_assessment_scores_per_category"
        status: pass
      - kind: unit
        ref: "backend/tests/services/test_dimension_scoring.py#test_full_assessment_all_ones_and_all_fives"
        status: pass
      - kind: unit
        ref: "backend/tests/services/test_dimension_scoring.py#test_precision_rounds_to_two_decimals"
        status: pass
    human_judgment: false
  - id: D2
    description: "No per-question or per-category weight multiplier — a 9-question and an 8-question category answered with the same value score identically"
    requirement: "SCOR-02"
    verification:
      - kind: unit
        ref: "backend/tests/services/test_dimension_scoring.py#test_equal_weight_across_different_question_counts"
        status: pass
    human_judgment: false
  - id: D3
    description: "assert_assessment_complete raises HTTPException(422) when incomplete or when no draft assessment exists; returns the Assessment on success"
    requirement: "SCOR-04"
    verification:
      - kind: unit
        ref: "backend/tests/services/test_dimension_scoring.py#test_incomplete_assessment_raises_422"
        status: pass
      - kind: unit
        ref: "backend/tests/services/test_dimension_scoring.py#test_no_draft_assessment_raises_422"
        status: pass
      - kind: unit
        ref: "backend/tests/services/test_dimension_scoring.py#test_complete_assessment_returns_assessment"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-07-24
status: complete
---

# Phase 14 Plan 01: Dimension-Scoring Service and Completion Gate Summary

**New pure-Python `dimension_scoring.py` service computing equal-weight per-category averages over `QuestionnaireAnswer` rows, plus a server-side 422 completion gate — both derived entirely from `config/dssc-questionnaire.json`, zero existing files touched.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-07-24T08:28Z (approx, following prior session's context load)
- **Completed:** 2026-07-24T08:41Z
- **Tasks:** 2 completed
- **Files modified:** 2 (both new)

## Accomplishments
- Created `backend/app/services/dimension_scoring.py` with `get_current_assessment`, `assert_assessment_complete`, `compute_dimension_scores`, and three private config-comprehension helpers (`_full_question_ids`, `_category_question_counts`, `_category_names`) — no FastAPI route, pure service module per D-03.
- Created `backend/tests/services/test_dimension_scoring.py` with 7 unit tests covering SCOR-01 (equal-weight average, boundary 1.0/5.0, 2dp rounding precision), SCOR-02 (9-question vs 8-question categories average identically), and SCOR-04 (422 on incomplete assessment, 422 on no draft assessment, successful gate returns the Assessment).
- All structure (question ids, category ids/names, per-category question counts) is derived from the `config` dict passed at call time — no hardcoded `52` or `9/9/9/9/8/8` anywhere in the new module (verified by grep, part of the plan's acceptance criteria).
- App still imports cleanly; full quick test suite stays green (same 4 pre-existing local-only WeasyPrint failures as every prior Phase 13 plan, unrelated to this change).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the dimension-scoring service (compute_dimension_scores + completion gate)** - `05f3acf` (feat)
2. **Task 2: Unit-test the scoring service and completion gate (SCOR-01/02/04)** - `0181377` (test)

**Plan metadata:** (this commit) `docs(14-01): complete dimension-scoring-service-and-completion-gate plan`

## Files Created/Modified
- `backend/app/services/dimension_scoring.py` - New service: `compute_dimension_scores`, `assert_assessment_complete`, `get_current_assessment`, plus `_full_question_ids`/`_category_question_counts`/`_category_names` helpers
- `backend/tests/services/test_dimension_scoring.py` - 7 unit tests against the real-Postgres `session` fixture and `make_assessment`/`make_answer`/`make_initiative`/`make_user` factories, driven from the real `config/dssc-questionnaire.json` (no hardcoded question ids)

## Decisions Made
- Colocated both the scoring computation and the completion gate in one new module (`dimension_scoring.py`) rather than splitting into two files — matches RESEARCH.md's Open Question 1 recommendation, keeps the five downstream call sites (Plans 02/03) to a single import line.
- Reused one identical 422 detail string (`"Questionnaire not fully answered"`) for both the "no draft assessment exists" and "assessment incomplete" cases, per RESEARCH.md's Open Question 2 recommendation and the threat-model mitigation for T-14-02 (no missing-question-id disclosure).
- Added `# type: ignore[attr-defined]` on the `Assessment.created_at.desc()` call, matching the existing precedent already used identically in `questionnaire.py` (3 occurrences) and `initiatives.py` (1 occurrence) for the same SQLModel-datetime-column mypy limitation — not a new pattern, just following what's already in the codebase.

## Deviations from Plan

None - plan executed exactly as written. The two tasks matched the plan's `<action>` specifications near-verbatim (RESEARCH.md's Pattern 1/Pattern 2 reference implementations were copied with only the mypy `type: ignore` addition, which follows existing repo convention rather than being a new decision).

## Issues Encountered
None. Docker/testcontainers-backed `session` fixture was available locally, so the full real-Postgres unit test suite ran without needing to skip or mock anything.

## User Setup Required

None - no external service configuration required. This plan adds no new dependency, no new environment variable, and no new endpoint.

## Next Phase Readiness

- `dimension_scoring.py`'s three public functions (`compute_dimension_scores`, `assert_assessment_complete`, `get_current_assessment`) are ready for Plan 02 (`scoring.py` adaptation) and Plan 03 (`reports.py` adaptation) to import and wire into the five existing score/report endpoints.
- No existing file was modified this plan — the app remains importable and the full quick test suite (`pytest tests/ -n auto -m "not perf and not benchmark"`) stays at 76/80 passing, identical to the pre-plan baseline (same 4 pre-existing local WeasyPrint failures, unrelated).
- `docs/api/openapi.json` regenerated with zero diff, confirming this plan changed no Pydantic response schema or route (purely additive service + test).
- Plan 04's ZEN/MoSCoW removal work can now proceed once Plans 02/03 have moved every call site off the deleted code paths onto this new service.

---
*Phase: 14-scoring-engine-replacement*
*Completed: 2026-07-24*

## Self-Check: PASSED

- FOUND: backend/app/services/dimension_scoring.py
- FOUND: backend/tests/services/test_dimension_scoring.py
- FOUND: commit 05f3acf
- FOUND: commit 0181377
