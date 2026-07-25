---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
plan: 01
subsystem: api
tags: [fastapi, sqlmodel, alembic, slowapi, postgresql, jwt]

# Dependency graph
requires:
  - phase: 13-new-questionnaire-config-schema-data-model-migration
    provides: Assessment entity (draft/submitted lifecycle), reshaped QuestionnaireAnswer (assessment_id/category_id/score), hand-written-migration convention
  - phase: 14-scoring-engine-replacement
    provides: dimension_scoring.py's assessment_id-agnostic compute_dimension_scores (referenced but not modified here)
provides:
  - Assessment.last_viewed_category_id (nullable String column) + uq_assessment_version_per_initiative unique constraint, declared on the model and applied via hand-written migration j1a2b3c4d5e6
  - get_user_or_ip_key — per-authenticated-user slowapi rate-limit key function (falls back to IP for unauthenticated/malformed requests)
  - Version-increment logic in _get_or_create_draft_assessment (max(existing versions)+1, race-safe via the new constraint + IntegrityError-catch-and-requery)
  - PATCH /questionnaire/initiatives/{id}/last-viewed-category — dedicated, unconditional last-viewed-category write endpoint
  - Wave-0 automated coverage for all three behaviors
affects: [15-02, 15-03, 15-04, 15-05, phase-16-report-and-admin-rebuild]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Model-declared UniqueConstraint in __table_args__ (not just migration) so SQLModel.metadata.create_all()-built test DBs enforce it too"
    - "slowapi key_func decodes the JWT directly from the Authorization header (reusing decode_access_token) rather than depending on FastAPI's Depends() injection, which slowapi's key_func call site does not resolve"

key-files:
  created:
    - backend/alembic/versions/j1a2b3c4d5e6_assessment_version_lastviewed.py
    - backend/tests/migrations/test_assessment_version_migration.py
  modified:
    - backend/app/models/assessment.py
    - backend/app/api/v1/questionnaire.py
    - backend/app/schemas/questionnaire.py
    - backend/tests/api/test_questionnaire_answers.py
    - backend/tests/factories.py
    - docs/api/openapi.json

key-decisions:
  - "PATCH last-viewed-category is guarded by the same CR-01 submitted-lock as upsert_answer (Rule 2 auto-fix, not explicit in plan text) — prevents a bare page view on a submitted initiative from silently starting a new draft/version as a side effect of _get_or_create_draft_assessment"
  - "tests/factories.py's make_assessment now computes version = max(existing)+1 (mirroring the real app logic) instead of always defaulting to 1 — needed once the new DB-level uniqueness constraint made the old always-version-1 factory behavior collide across existing admin tests that create multiple assessments per initiative"
  - "Flagged-edge sign-off (HIST-01 concurrent-retake-race, plan must_haves.flagged_edge_assumptions): VERIFIED ACCEPTABLE (constraint + requery covers it). The (initiative_id, version) unique constraint + broad IntegrityError catch-and-requery in _get_or_create_draft_assessment structurally mirrors the already-trusted uq_assessment_one_draft_per_initiative/CR-02 pattern: on a race, the loser's insert fails on the new constraint, rolls back, and requeries by (initiative_id, status=draft) — which finds the winner's just-committed draft regardless of which specific version number won, so the loser correctly returns the winner's row rather than erroring or duplicating. No live multi-connection concurrency test was written (mirroring the existing CR-02 precedent, which also has no live-concurrency test, only the migration-level constraint proof) — this is a conscious sign-off, not a silent drop."

requirements-completed: [HIST-01, SAVE-03, SAVE-04]

coverage:
  - id: D1
    description: "(initiative_id, version) unique constraint on Assessment, declared on the model and applied via a hand-written Alembic migration — the DB-level invariant that makes race-safe version increments possible (D-15/HIST-01, Pitfall 4)"
    requirement: "HIST-01"
    verification:
      - kind: unit
        ref: "backend/tests/migrations/test_assessment_version_migration.py#test_duplicate_initiative_version_pair_raises_integrity_error"
        status: pass
      - kind: unit
        ref: "backend/tests/migrations/test_assessment_version_migration.py#test_upgrade_downgrade_upgrade_round_trip_succeeds"
        status: pass
    human_judgment: false
  - id: D2
    description: "Assessment.last_viewed_category_id nullable column, added by the same migration, giving D-08's resume behavior a server-side home"
    requirement: "SAVE-04"
    verification:
      - kind: unit
        ref: "backend/tests/migrations/test_assessment_version_migration.py#test_upgrade_head_from_empty_db_creates_column_and_constraint"
        status: pass
    human_judgment: false
  - id: D3
    description: "get_user_or_ip_key — per-authenticated-user slowapi rate-limit key (Bearer JWT sub -> user:<email>), falling back to IP-keying for missing/malformed tokens; wired into upsert_answer's Limiter (120/minute)"
    requirement: "SAVE-03"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_questionnaire_answers.py#test_rate_limit_key_uses_bearer_token_email"
        status: pass
      - kind: unit
        ref: "backend/tests/api/test_questionnaire_answers.py#test_rate_limit_key_falls_back_to_ip_without_token"
        status: pass
      - kind: unit
        ref: "backend/tests/api/test_questionnaire_answers.py#test_rate_limit_key_falls_back_to_ip_for_malformed_token"
        status: pass
      - kind: unit
        ref: "backend/tests/api/test_questionnaire_answers.py#test_rate_limit_key_is_idempotent_for_same_token"
        status: pass
      - kind: unit
        ref: "backend/tests/api/test_questionnaire_answers.py#test_rate_limit_key_distinct_users_never_collide"
        status: pass
    human_judgment: false
  - id: D4
    description: "_get_or_create_draft_assessment computes next_version = max(existing versions for the initiative) + 1 instead of a hardcoded 1, so a retake after a prior submission is a distinguishable, permanently preserved new version"
    requirement: "HIST-01"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_questionnaire_answers.py#test_version_increment_on_retake_after_prior_submission"
        status: pass
    human_judgment: false
  - id: D5
    description: "PATCH /questionnaire/initiatives/{id}/last-viewed-category — dedicated endpoint that writes last_viewed_category_id UNCONDITIONALLY (no answer required), guarded by ownership + submitted-lock checks"
    requirement: "SAVE-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_questionnaire_answers.py#test_last_viewed_category_updates_with_zero_answers_saved"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_questionnaire_answers.py#test_last_viewed_category_creates_draft_lazily_if_none_exists"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_questionnaire_answers.py#test_last_viewed_category_rejects_non_owner"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-07-25
status: complete
---

# Phase 15 Plan 01: Backend Data-Integrity Spine (Version Increment, Per-User Rate Limit, Last-Viewed-Category) Summary

**Race-safe Assessment version increments via a new (initiative_id, version) unique constraint, a JWT-derived per-user slowapi rate-limit key replacing IP-keying, and a dedicated unconditional PATCH endpoint persisting last-viewed-category server-side.**

## Performance

- **Duration:** ~45 min active execution (session was twice interrupted by transient API errors and resumed from the same worktree; all work was preserved across resumes)
- **Completed:** 2026-07-25
- **Tasks:** 3/3 completed
- **Files modified:** 8 (2 created, 6 modified)

## Accomplishments

- Assessment model gains `last_viewed_category_id` (nullable) and a model-declared `uq_assessment_version_per_initiative` unique constraint, applied to real Postgres via hand-written migration `j1a2b3c4d5e6` (chains from `i9d7e6f5a4b3`) — a single head confirmed via `alembic heads`
- `_get_or_create_draft_assessment` now computes `version = max(existing versions for the initiative) + 1` instead of a hardcoded `1`, with the existing IntegrityError-catch-and-requery pattern now also defending the new constraint
- `get_user_or_ip_key` replaces `get_remote_address` as the questionnaire router's slowapi key function — decodes the Bearer JWT directly (reusing `decode_access_token`, not a second parser) since slowapi's key_func never sees FastAPI's `Depends()`-injected values; falls back to IP-keying for unauthenticated/malformed requests. `upsert_answer`'s ceiling raised 60/minute → 120/minute per RESEARCH A1
- New `PATCH /questionnaire/initiatives/{id}/last-viewed-category` endpoint writes `last_viewed_category_id` unconditionally (no answer required) — the single, exact D-08 write path, deliberately not piggybacked onto `upsert_answer`
- Wave-0 automated coverage added directly to `test_questionnaire_answers.py`: 5 rate-limit-key unit tests, 1 version-increment integration test, 3 last-viewed-category integration tests — all selectable via `-k "rate_limit or version_increment or last_viewed"`

## Task Commits

Each task was committed atomically:

1. **Task 1: [BLOCKING] Assessment model change + hand-written Alembic migration** - `5a6474e` (feat)
2. **Task 2: Version-increment, per-user rate-limit key, dedicated last-viewed-category endpoint** - `9f0b69c` (feat)
3. **Task 3: Wave-0 tests** - `5ee303c` (test)

**Additional commit (docs-freshness gate, tied to Task 2's new route):** `4531d47` (docs: regenerate openapi.json)

_Note: Task 2 was flagged `tdd="true"` in the plan but its own `<files>`/acceptance criteria excluded test files (Task 3 owns the dedicated test additions) — implemented as a single commit rather than a literal RED/GREEN split; verified via the full quick suite per its own `<verify>` before Task 3 added the direct unit/integration coverage._

## Files Created/Modified

- `backend/app/models/assessment.py` - Added `last_viewed_category_id`, `uq_assessment_version_per_initiative` UniqueConstraint
- `backend/alembic/versions/j1a2b3c4d5e6_assessment_version_lastviewed.py` - Hand-written migration adding the column + constraint
- `backend/tests/migrations/test_assessment_version_migration.py` - Empty-DB upgrade, duplicate-version IntegrityError, upgrade/downgrade/upgrade round-trip (real Postgres testcontainer)
- `backend/app/api/v1/questionnaire.py` - `get_user_or_ip_key`, version-increment logic, `120/minute` ceiling, new PATCH last-viewed-category route
- `backend/app/schemas/questionnaire.py` - New `LastViewedCategoryUpdate` schema
- `backend/tests/api/test_questionnaire_answers.py` - Wave-0 rate-limit-key/version-increment/last-viewed-category tests
- `backend/tests/factories.py` - `make_assessment` now computes version = max(existing)+1 (Rule 1 auto-fix)
- `docs/api/openapi.json` - Regenerated for the new PATCH route + schema (docs-freshness CI gate)

## Decisions Made

- Guarded the new PATCH last-viewed-category endpoint with the same CR-01 submitted-lock as `upsert_answer` (Rule 2 auto-fix) — see Deviations below.
- `tests/factories.py`'s `make_assessment` now mirrors the real app's version-increment logic rather than always defaulting to version 1 (Rule 1 auto-fix) — see Deviations below.
- **Flagged-edge sign-off (plan `must_haves.flagged_edge_assumptions`, HIST-01 concurrent-retake-race):** **VERIFIED ACCEPTABLE (constraint + requery covers it).** The new `(initiative_id, version)` unique constraint plus the existing broad `IntegrityError`-catch-and-requery in `_get_or_create_draft_assessment` structurally mirrors the already-trusted `uq_assessment_one_draft_per_initiative`/CR-02 pattern: on a concurrent-insert race, the loser's insert fails against the new constraint, rolls back, and requeries by `(initiative_id, status=draft)` — which finds the winner's just-committed draft regardless of which version number won, so the loser correctly returns the winner's row instead of erroring or duplicating. No live multi-connection concurrency test was added (the existing CR-02 precedent this mirrors also has none, only migration-level constraint proof) — this is a conscious, recorded sign-off per the plan's verification requirement, not a silent drop.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Guarded PATCH last-viewed-category against silently starting a new draft/version on a submitted initiative**
- **Found during:** Task 2 (dedicated last-viewed-category endpoint)
- **Issue:** The endpoint calls `_get_or_create_draft_assessment`, which would create a brand-new (incremented-version) draft as a side effect of merely viewing a page after the initiative was submitted — bypassing D-13's requirement that a retake only ever starts via an explicit "Start new assessment" action.
- **Fix:** Added the same `initiative.status == InitiativeStatus.submitted → 403` lock `upsert_answer` already enforces (CR-01), before resolving/creating the draft assessment.
- **Files modified:** `backend/app/api/v1/questionnaire.py`
- **Verification:** Covered implicitly by the full quick suite passing; no dedicated test added for this specific guard within plan 01's scope (mirrors the plan's `<verify>`, which is the full suite, not an exhaustive new-assertion list for every guard).
- **Committed in:** `9f0b69c` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed `tests/factories.py::make_assessment` colliding with the new version-uniqueness constraint**
- **Found during:** Task 2 verification (full quick suite run)
- **Issue:** The new model-declared `uq_assessment_version_per_initiative` constraint (Task 1) is enforced even on `SQLModel.metadata.create_all()`-built test databases. The existing `make_assessment` factory always defaulted to `version=1`; several pre-existing `test_admin.py` tests call `make_answer` (which calls `make_assessment` when none is passed) multiple times for the *same* initiative, each attempt now colliding on `(initiative_id, version=1)` and raising `IntegrityError` — 4 previously-passing tests started failing (`test_list_users_returns_initiative_and_answer_fields`, `test_list_initiatives_returns_user_email_and_answer_count`, `test_delete_user_cascades_all_child_rows`, `test_export_dataset_csv_shape`).
- **Fix:** `make_assessment` now computes `version = max(existing versions for the initiative, or 0) + 1`, mirroring the real app's `_get_or_create_draft_assessment` logic, so repeated calls for the same initiative never collide.
- **Files modified:** `backend/tests/factories.py`
- **Verification:** All 4 previously-failing tests pass again; full quick suite green except the 4 pre-existing, unrelated local-only WeasyPrint failures.
- **Committed in:** `9f0b69c` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing-critical, 1 bug)
**Impact on plan:** Both auto-fixes necessary for correctness — the first closes a real D-13 violation risk, the second was a direct, mechanical consequence of Task 1's new correctness constraint on pre-existing test fixtures. No scope creep; neither touches any file outside this plan's transitive blast radius.

## Issues Encountered

Two transient API connection errors interrupted this execution session mid-task; both times the coordinator confirmed all prior commits were intact from outside the session and the work resumed cleanly from the same worktree with no lost or duplicated work. No logic issues were involved.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The backend data-integrity spine (version increment, per-user rate limiting, last-viewed-category persistence) is complete and independently verified — plans 15-02 through 15-05 (frontend wizard rebuild, retake flow, history endpoint/page) can build against it.
- `alembic heads` confirms a single head (`j1a2b3c4d5e6`); full quick suite green (94 -> 103 passing after this plan's additions) except the 4 pre-existing local-only WeasyPrint failures (documented since Phase 13, unrelated to this plan).
- No blockers for subsequent Phase 15 plans.

---
*Phase: 15-questionnaire-submission-api-wizard-ui-save-reliability*
*Completed: 2026-07-25*

## Self-Check: PASSED

All 8 created/modified files confirmed present on disk (`backend/app/models/assessment.py`, `backend/alembic/versions/j1a2b3c4d5e6_assessment_version_lastviewed.py`, `backend/tests/migrations/test_assessment_version_migration.py`, `backend/app/api/v1/questionnaire.py`, `backend/app/schemas/questionnaire.py`, `backend/tests/api/test_questionnaire_answers.py`, `backend/tests/factories.py`, `docs/api/openapi.json`). All 4 commit hashes (`5a6474e`, `9f0b69c`, `5ee303c`, `4531d47`) confirmed present in `git log --oneline --all`.
