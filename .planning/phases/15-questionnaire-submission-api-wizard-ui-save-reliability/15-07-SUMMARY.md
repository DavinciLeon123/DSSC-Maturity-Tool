---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
plan: 07
subsystem: api
tags: [fastapi, sqlmodel, alembic, jsonb, gap-closure, history]

# Dependency graph
requires:
  - phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
    plan: 06
    provides: "retake_initiative endpoint + dashboard wiring — this plan also edits backend/app/api/v1/initiatives.py (submit_initiative/_to_summary), so it runs in the wave after 15-06"
provides:
  - "Assessment.dimension_scores — a nullable JSONB snapshot column, frozen at submit time"
  - "submit_initiative now computes and persists the per-dimension score snapshot exactly once, against the config as of submission time"
  - "_to_summary/list_assessment_history prefer the frozen snapshot, falling back to live recompute only for legacy submitted rows"
  - "compute_dimension_scores zero-division guard (WR-04)"
  - "REQUIREMENTS.md traceability correction: QSTN-02 and SAVE-03 marked Complete"
affects: [15-VERIFICATION (closes Gap 2 / HIST-02), phase-16-report-and-admin-rebuild]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Snapshot-at-write, prefer-snapshot-at-read: submit_initiative computes and freezes JSON once; every subsequent read prefers the frozen value and only falls back to a live recompute for rows that predate the column (None check), never for rows that have it"
    - "Deep-copied dependency-override config mutation in tests (copy.deepcopy + app.dependency_overrides[get_dssc_questionnaire_config], restored in a finally) to simulate live-config drift without touching the real config file or object"

key-files:
  created:
    - backend/alembic/versions/k2b3c4d5e6f7_assessment_frozen_dimension_scores.py
    - backend/tests/migrations/test_frozen_scores_migration.py
    - backend/tests/api/test_frozen_scores.py
  modified:
    - backend/app/models/assessment.py
    - backend/app/api/v1/initiatives.py
    - backend/app/services/dimension_scoring.py
    - docs/api/openapi.json
    - .planning/REQUIREMENTS.md

key-decisions:
  - "dimension_scores declared list[dict] | None with sa_column=Column(JSONB, nullable=True), mirroring the exact idiom questionnaire_answer_archive.py already established for JSONB columns on this project — no new pattern introduced"
  - "submit_initiative computes the snapshot inside the existing `if assessment:` branch (no new completion gate added) — freezing happens whatever the draft's answer state is at submit time, matching the plan's explicit 'do not add a completion gate' instruction (report endpoints already enforce the 422 gate elsewhere)"
  - "_to_summary's overall_average is guarded (`if scores else 0.0`) for an edge case no test currently exercises (empty categories list) — defensive per the plan's exact wording, not a speculative addition"

requirements-completed: [HIST-02]

coverage:
  - id: D1
    description: "Assessment.dimension_scores nullable JSONB snapshot column + hand-written migration k2b3c4d5e6f7 (chains from j1a2b3c4d5e6, single head) + migration round-trip test"
    requirement: "HIST-02"
    verification:
      - kind: integration
        ref: "backend/tests/migrations/test_frozen_scores_migration.py#test_upgrade_head_from_empty_db_adds_dimension_scores_column"
        status: pass
      - kind: integration
        ref: "backend/tests/migrations/test_frozen_scores_migration.py#test_upgrade_downgrade_upgrade_round_trip_succeeds"
        status: pass
    human_judgment: false
  - id: D2
    description: "submit_initiative snapshots compute_dimension_scores onto Assessment.dimension_scores at submit time; _to_summary prefers the frozen snapshot with a live-recompute fallback for legacy (None) rows; compute_dimension_scores zero-division guard (WR-04)"
    requirement: "HIST-02"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_assessment_history.py#test_assessment_history_ordered_by_version_with_correct_scores (fallback path, dimension_scores=None seeded rows still pass)"
        status: pass
      - kind: unit
        ref: "cd backend && uv run ruff check . && uv run mypy app --ignore-missing-imports"
        status: pass
    human_judgment: false
  - id: D3
    description: "Freeze-proof test: submit through the real HTTP endpoint, mutate the live config via dependency override, assert history returns the ORIGINAL frozen category names/scores not the mutated live config; negative control for the legacy no-snapshot fallback path; REQUIREMENTS.md QSTN-02/SAVE-03 corrected to Complete"
    requirement: "HIST-02"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_frozen_scores.py#test_history_serves_frozen_snapshot_not_mutated_live_config"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_frozen_scores.py#test_history_falls_back_to_live_compute_for_legacy_row_without_snapshot"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-26
status: complete
---

# Phase 15 Plan 07: Frozen Assessment History Gap Closure (HIST-02) Summary

**Assessment.dimension_scores is now a frozen JSONB snapshot written exactly once by submit_initiative against the config as of submission time, and the history endpoint prefers that snapshot over a live recompute — proven immutable under live config drift by a real end-to-end test that mutates the live config mid-test via a dependency override.**

## Performance

- **Duration:** ~25 min active execution
- **Completed:** 2026-07-26
- **Tasks:** 3/3 completed
- **Files modified:** 7 (3 created, 4 modified)

## Accomplishments

- Added a nullable JSONB `dimension_scores` column to `Assessment` (`backend/app/models/assessment.py`), mirroring the existing `questionnaire_answer_archive.py` JSONB idiom exactly, plus a hand-written migration `k2b3c4d5e6f7` chaining from `j1a2b3c4d5e6` (confirmed single head) with a full upgrade/downgrade/upgrade round-trip test.
- `submit_initiative` (`backend/app/api/v1/initiatives.py`) now takes a `config` dependency and computes `compute_dimension_scores` exactly once, persisting the result on `assessment.dimension_scores` inside the same transaction that flips the assessment to `submitted` — this is the sole point scores are ever computed for a submitted version.
- `_to_summary` now prefers `a.dimension_scores` when present, falling back to a live `compute_dimension_scores` call only when it is `None` (legacy rows created before this column existed) — proven by `test_assessment_history.py`'s pre-existing seeded (snapshot=None) rows still passing unchanged.
- `compute_dimension_scores` (`backend/app/services/dimension_scoring.py`) now guards its per-category division so a zero-question category yields `0.0` instead of raising `ZeroDivisionError` (WR-04) — this function is now called directly on the submit path, a real user-triggered crash surface.
- New `backend/tests/api/test_frozen_scores.py`: submits through the real `POST /submit` endpoint (after answering all 52 questions via the real `PUT` answer endpoint), asserts the DB-persisted snapshot has 6 entries matching the real config's category names, then mutates a deep-copied config (renamed category + trimmed question list) and installs it via `app.dependency_overrides[get_dssc_questionnaire_config]` for the duration of a single `GET /assessments` call — proving the response still reflects the ORIGINAL frozen names/scores, not the mutated live config. A second test proves the legacy (`dimension_scores=None`) fallback path still works.
- Corrected `.planning/REQUIREMENTS.md` traceability drift flagged by `15-VERIFICATION.md`: QSTN-02 and SAVE-03 changed from `[ ]`/Pending to `[x]`/Complete (both were already fully implemented and tested); HIST-01/HIST-02 left as Complete, unchanged.
- Regenerated `docs/api/openapi.json` (docs-freshness CI gate) — `submit_initiative`'s docstring grew a paragraph describing the new snapshot behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Assessment.dimension_scores snapshot column + migration + migration test** - `ef7f3d0` (feat)
2. **Task 2: Snapshot scores at submit time; read frozen snapshot in history; zero-division guard** - `04d81b0` (feat)
3. **Task 3: Frozen-history test + REQUIREMENTS.md traceability correction** - `a6ce9e7` (test)

**Additional commit (docs-freshness gate, tied to Task 2's docstring change):** `684f7ba` (docs: regenerate openapi.json)

## Files Created/Modified

- `backend/app/models/assessment.py` - Added nullable JSONB `dimension_scores` column; extended module docstring
- `backend/alembic/versions/k2b3c4d5e6f7_assessment_frozen_dimension_scores.py` - New hand-written migration, chains from `j1a2b3c4d5e6`
- `backend/tests/migrations/test_frozen_scores_migration.py` - New migration round-trip test (2 tests)
- `backend/app/api/v1/initiatives.py` - `submit_initiative` now snapshots scores at submit time; `_to_summary` prefers the frozen snapshot with a legacy fallback
- `backend/app/services/dimension_scoring.py` - `compute_dimension_scores` zero-division guard (WR-04)
- `backend/tests/api/test_frozen_scores.py` - New freeze-proof test file (2 tests: positive freeze proof + negative legacy-fallback control)
- `docs/api/openapi.json` - Regenerated for `submit_initiative`'s docstring change
- `.planning/REQUIREMENTS.md` - QSTN-02 and SAVE-03 corrected from Pending to Complete

## Decisions Made

- `dimension_scores` declared exactly like `questionnaire_answer_archive.py`'s existing JSONB idiom (`sa_column=Column(JSONB, nullable=True)`) — no new column-declaration pattern introduced.
- The snapshot is computed inside `submit_initiative`'s existing `if assessment:` branch with no new completion gate — deliberately matching the plan's explicit instruction that a completion gate is out of scope here (the report endpoints already enforce a 422 gate independently).
- `_to_summary`'s `overall_average` computation is guarded against an empty `scores` list (`if scores else 0.0`) per the plan's exact wording — defensive, not exercised by any current test since every category always has at least one question in the real config.

## Deviations from Plan

None — plan executed exactly as written. All three tasks' actions, acceptance criteria, and the threat model's three mitigations (T-15-07-01/02/03) were implemented precisely as specified.

## Issues Encountered

None. The one required follow-up (regenerating `docs/api/openapi.json` after `submit_initiative`'s docstring grew a HIST-02 paragraph) was anticipated by the plan's own docs-freshness precedent from prior phases and committed separately per the established convention.

## User Setup Required

None - no external service configuration required.

## Verification Results

- `cd backend && uv run ruff check . && uv run ruff format . --check && uv run mypy app --ignore-missing-imports` — all clean.
- `cd backend && uv run pytest tests/migrations/test_frozen_scores_migration.py tests/api/test_frozen_scores.py tests/api/test_assessment_history.py -q` — 9 passed (new tests pass AND the existing history test still passes via the legacy-fallback path).
- `cd backend && uv run pytest tests/api/test_retake_flow.py tests/api/test_questionnaire_answers.py -q` — 20 passed (submit_initiative's new `config` dependency does not break the 15-06 retake flow tests).
- No other migration chains from `k2b3c4d5e6f7` (confirmed via grep across `alembic/versions/`) — it is the single current head.
- Full backend quick suite (`pytest tests/ -n auto -m "not perf and not benchmark"`): 118 passed, 4 failed — the 4 failures are the pre-existing, local-only WeasyPrint native-library gap (`libgobject-2.0-0`) documented since Phase 13 in every prior phase's summaries/deferred-items.md, unrelated to this plan.

## Next Phase Readiness

- Gap 2 (CR-02, frozen assessment-history scores / HIST-02) from `15-VERIFICATION.md` is closed: a submitted assessment's history-listed dimension scores and category names now stay fixed after the live config changes, proven by a real end-to-end test that mutates the live config mid-test.
- Combined with 15-06's HIST-01 closure (retake flow), both gaps `15-VERIFICATION.md` flagged as blocking are now resolved — Phase 15's goal ("every full completion creates a new, permanently preserved assessment version the user can return to") is fully satisfied pending re-verification.
- No blockers for the phase-15 verification re-run or Phase 16 (report and admin rebuild).

---
*Phase: 15-questionnaire-submission-api-wizard-ui-save-reliability*
*Completed: 2026-07-26*

## Self-Check: PASSED

All 8 created/modified files confirmed present on disk (`backend/app/models/assessment.py`, `backend/alembic/versions/k2b3c4d5e6f7_assessment_frozen_dimension_scores.py`, `backend/tests/migrations/test_frozen_scores_migration.py`, `backend/app/api/v1/initiatives.py`, `backend/app/services/dimension_scoring.py`, `backend/tests/api/test_frozen_scores.py`, `.planning/REQUIREMENTS.md`, this SUMMARY.md). All 5 commit hashes (`ef7f3d0`, `04d81b0`, `a6ce9e7`, `684f7ba`, and this file's own commit `bef5738`) confirmed present in `git log --oneline`.
