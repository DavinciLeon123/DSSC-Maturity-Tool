---
phase: 13-new-questionnaire-config-schema-data-model-migration
plan: 03
subsystem: database
tags: [sqlmodel, fastapi, postgres, data-model-migration, assessment-entity]

requires:
  - phase: 13-01
    provides: "Universal config/dssc-questionnaire.json (52 questions/6 categories) served via GET /questionnaire/config"
  - phase: 13-02
    provides: "Evidence subsystem fully removed; admin.py/reports.py/report_generator.py left importable against the OLD answer shape"
provides:
  - "New Assessment entity (draft/submitted lifecycle, created lazily on first answer, D-06/D-07)"
  - "New QuestionnaireAnswerV1Archive model — read-only mirror of the pre-migration v1.0 answer shape, no FK to initiative (D-01/A2)"
  - "Reshaped questionnaire_answer keyed by assessment_id/category_id/score (1-5), replacing initiative_id/mami_code/answer_value (D-02)"
  - "Initiative.schema_version (default 'v2', D-03); nullable participant_type on Initiative and User (D-12)"
  - "Assessment-first PUT/GET answer endpoints with ownership re-derivation (security V4)"
  - "reports.py/admin.py/scoring.py adapted to the new answer shape — app imports/boots, degrade to zero findings for new-schema initiatives instead of raising (documented interim Phase 13->14 gap)"
affects: [13-04, 14-scoring-engine-replacement, 15-wizard-autosave-history, 16-report-visualization]

tech-stack:
  added: []
  patterns:
    - "Assessment-first answer keying: every new-schema answer write round-trips through an Assessment row (structurally enforced by the FK) — Phase 14/15/16's join point"
    - "Degrade-not-crash for downstream consumers of a reshaped table: when a column shape changes out from under old readers, adapt each reader to a safe empty/zero result with an inline comment, rather than leaving an AttributeError landmine"

key-files:
  created:
    - backend/app/models/assessment.py
    - backend/app/models/questionnaire_answer_archive.py
    - backend/tests/schemas/test_questionnaire_schemas.py
    - backend/tests/api/test_questionnaire_answers.py
  modified:
    - backend/app/models/questionnaire.py
    - backend/app/models/initiative.py
    - backend/app/models/user.py
    - backend/app/db/base.py
    - backend/app/schemas/questionnaire.py
    - backend/app/schemas/initiative.py
    - backend/app/schemas/auth.py
    - backend/app/api/v1/questionnaire.py
    - backend/app/api/v1/admin.py
    - backend/app/api/v1/reports.py
    - backend/app/api/v1/scoring.py
    - backend/app/api/v1/initiatives.py
    - backend/tests/factories.py
    - backend/tests/api/test_admin.py
    - backend/tests/api/test_reports.py
    - docs/api/openapi.json
    - .planning/phases/13-new-questionnaire-config-schema-data-model-migration/deferred-items.md

key-decisions:
  - "AssessmentStatus is (str, Enum) draft/submitted; version is an int counter (default 1) plus existing created_at/submitted_at timestamps — satisfies Phase 15's 'dated version' need without a redundant field (RESEARCH Open Question 1)"
  - "Initiative's legacy-tag column is named schema_version: str ('v2' default) rather than a boolean is_legacy, leaving room for a future v3 (D-03)"
  - "Archive table (QuestionnaireAnswerV1Archive) is a real SQLModel table=True class, importable/queryable, registered in db/base.py — not just a raw Alembic table (RESEARCH Open Question 2)"
  - "followup_selections/followup_other/rationale dropped entirely from the LIVE answer shape (kept only in the archive model, which mirrors the old shape verbatim) — no non-removed code path referenced them after the reshape"
  - "No hard 422 guard added for new-schema initiatives hitting report/heatmap/score endpoints (Assumption A3) — degrade to zero findings/an all-zero heatmap instead, documented inline at every degraded site as a known Phase 13->14 gap, not a real 'compliant' signal"
  - "scoring.py (app/api/v1/scoring.py) was NOT in this plan's file list but directly used QuestionnaireAnswer.initiative_id/.mami_code/.answer_value — reshaping the model would have left this live, registered endpoint raising AttributeError at runtime. Fixed as a Rule 1 auto-fix, mirroring reports.py's exact degradation treatment."
  - "initiatives.py::_to_read's participant_type.value access was NOT in this plan's file list but is a direct, immediate consequence of making Initiative.participant_type nullable (Task 2) — guarded with `if initiative.participant_type else None` (Rule 1 auto-fix) so the InitiativeRead schema's new `str | None` claim is actually true end-to-end, not just cosmetic"
  - "schemas/auth.py::UserRead.participant_type was NOT in the plan's explicit fallout list (RESEARCH Pitfall 5 named only InitiativeRead/AdminUserRow/AdminInitiativeRow) but mypy caught the same class of bug immediately after User.participant_type became nullable — fixed to str | None (Rule 1 auto-fix)"
  - "Did NOT change auth.py's /register endpoint or initiatives.py's create_initiative to stop writing participant_type from user input — D-12 says 'new Initiatives/Users never set it' but changing the registration/creation API contract (removing/ignoring a field the frontend still sends) is a bigger structural change than this plan's explicit file/task list calls for; deferred as a flagged assumption rather than silently expanded or silently ignored. Current behavior: the column is nullable (accepts None safely everywhere it's read), but registration/creation still populate it from request input, matching this plan's precise scope (only the 5 fallout sites RESEARCH Pitfall 5 named + auth.py's own equivalent one)."

patterns-established:
  - "Assessment-first: any future assessment_id-keyed endpoint must re-derive ownership through Assessment.initiative_id -> Initiative.user_id, never trust assessment_id alone (security V4)"
  - "When a live table's column shape changes and downstream readers can't be rebuilt this same phase (scoring math is Phase 14's job), adapt them to degrade to a safe empty/zero result with an inline code comment marking the interim gap — do not leave AttributeErrors or silently claim a false-positive 'compliant' result"

requirements-completed: [QSTN-01]

coverage:
  - id: D1
    description: "A new Assessment table exists with initiative_id FK, integer version, created_at/submitted_at, and a status enum limited to draft/submitted; an Assessment row is created lazily on the first answer write in draft status"
    requirement: "QSTN-01"
    verification:
      - kind: unit
        ref: "backend/tests/schemas/test_questionnaire_schemas.py#test_assessment_defaults_to_draft_status_and_version_one"
        status: pass
      - kind: unit
        ref: "backend/tests/schemas/test_questionnaire_schemas.py#test_assessment_status_constrained_to_draft_or_submitted"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_questionnaire_answers.py#test_upsert_answer_creates_draft_assessment_lazily"
        status: pass
    human_judgment: false
  - id: D2
    description: "questionnaire_answer is reshaped to key off assessment_id, carry category_id, and store an integer score (1-5) — no mami_code/initiative_id/3-way enum remains; unique constraint renamed to uq_answer_per_question_v2"
    requirement: "QSTN-01"
    verification:
      - kind: unit
        ref: "backend/tests/schemas/test_questionnaire_schemas.py#test_questionnaire_answer_table_has_new_shape"
        status: pass
      - kind: unit
        ref: "backend/tests/schemas/test_questionnaire_schemas.py#test_answer_read_from_attributes_reflects_new_shape"
        status: pass
    human_judgment: false
  - id: D3
    description: "questionnaire_answer_v1_archive mirrors the OLD answer shape with no FK to initiative (survives a hard-delete) and an explicit String answer_value column (not a native enum)"
    verification:
      - kind: unit
        ref: "backend/tests/schemas/test_questionnaire_schemas.py#test_archive_table_has_no_initiative_fk"
        status: pass
      - kind: unit
        ref: "backend/tests/schemas/test_questionnaire_schemas.py#test_archive_answer_value_is_explicit_string_column_not_enum"
        status: pass
    human_judgment: false
  - id: D4
    description: "AnswerCreate.score rejects out-of-range values (0, -1, 6, 100) and accepts 1-5 at the Pydantic layer (security V5)"
    verification:
      - kind: unit
        ref: "backend/tests/schemas/test_questionnaire_schemas.py#test_answer_create_rejects_out_of_range_scores"
        status: pass
      - kind: unit
        ref: "backend/tests/schemas/test_questionnaire_schemas.py#test_answer_create_accepts_in_range_scores"
        status: pass
    human_judgment: false
  - id: D5
    description: "Initiative.schema_version defaults to 'v2'; participant_type nullable on Initiative and User with Pydantic/admin-row fallout fixed (InitiativeRead, UserRead, AdminUserRow, AdminInitiativeRow all accept None)"
    verification:
      - kind: unit
        ref: "mypy app --ignore-missing-imports (0 errors) + backend/tests/api/test_admin.py suite (pass)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Assessment-first upsert endpoint re-derives ownership through Assessment.initiative_id -> Initiative.user_id; a non-owner gets 403 and no Assessment is created as a side effect"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_questionnaire_answers.py#test_upsert_answer_rejects_non_owner"
        status: pass
    human_judgment: false
  - id: D7
    description: "reports.py/admin.py/scoring.py adapted to the new answer shape — app imports and the full backend suite runs green (SQLModel.metadata.create_all, conftest bypasses Alembic); reports/heatmap/scoring degrade to zero findings for new-schema initiatives rather than raising"
    verification:
      - kind: integration
        ref: "uv run python -c 'import app.main' + uv run pytest tests/ -n auto -m 'not perf and not benchmark' -q (65 passed; 4 pre-existing local WeasyPrint failures, unrelated, tracked in deferred-items.md)"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-07-23
status: complete
---

# Phase 13 Plan 03: Assessment Entity, Answer Reshape & Data Model Migration Summary

**New Assessment entity (draft/submitted lifecycle, created lazily on first answer) and a reshaped assessment_id/category_id/score answer table replace the initiative_id/mami_code/3-way-enum shape, with a read-only v1 archive model, a schema_version tag on Initiative, nullable participant_type, and reports.py/admin.py/scoring.py adapted to degrade to zero findings for new-schema initiatives instead of raising.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-07-23T09:15:00Z
- **Completed:** 2026-07-23T09:50:00Z
- **Tasks:** 3 completed
- **Files modified:** 18 modified/regenerated, 4 created

## Accomplishments
- Added `backend/app/models/assessment.py` (`Assessment` + `AssessmentStatus`, D-06/D-07) and `backend/app/models/questionnaire_answer_archive.py` (`QuestionnaireAnswerV1Archive`, D-01) — both registered in `db/base.py` for `create_all`/Alembic autogenerate.
- Reshaped `backend/app/models/questionnaire.py::QuestionnaireAnswer` to `assessment_id`/`category_id`/`score` (1-5, `Field(ge=1, le=5)`), renamed the unique constraint to `uq_answer_per_question_v2`, and reshaped `backend/app/schemas/questionnaire.py::AnswerCreate`/`AnswerRead` to match (security V5 — Pydantic-layer score bounds).
- Added `Initiative.schema_version` (default `"v2"`, D-03) and made `participant_type` nullable on `Initiative` and `User` (D-12) — fixed the Pydantic/admin-row fallout across `InitiativeRead`, `UserRead`, `AdminUserRow`, `AdminInitiativeRow` (RESEARCH Pitfall 5).
- Extended `backend/app/api/v1/questionnaire.py`'s PUT/GET answer endpoints to the assessment-first flow: look up or lazily create a draft `Assessment` before upserting, re-deriving ownership through `Assessment.initiative_id -> Initiative.user_id` (security V4) — same `pg_insert(...).on_conflict_do_update(...)` shape as before, now keyed by the v2 constraint.
- Adapted `admin.py` (raw-SQL answer counts/CSV export/heatmap now join through `assessment`; cascade-delete removes assessments+answers before the initiative), `reports.py` (all 5 answer-reading call sites rewritten; degrades to zero findings/recommendations for new-schema initiatives, documented inline as a known Phase 13->14 gap per Assumption A3), and `scoring.py` (same treatment — Rule 1 auto-fix, this file wasn't in the plan's list but would have broken at runtime).
- Updated `tests/factories.py` (`make_answer`/new `make_assessment`), `tests/api/test_admin.py` (assessment-join queries, new CSV header), `tests/api/test_reports.py` (new-shape fixture); added `tests/schemas/test_questionnaire_schemas.py` (16 tests: score bounds, table shape, archive no-FK/explicit-String checks) and `tests/api/test_questionnaire_answers.py` (5 tests covering the assessment-first flow + ownership, a pre-existing coverage gap for this endpoint).
- Regenerated `docs/api/openapi.json` (Rule 3 auto-fix — docs-freshness CI gate).

## Task Commits

Each task was committed atomically:

1. **Task 1: New Assessment + archive models, db/base registry, reshaped answer schema** - `1dbf341` (feat)
2. **Task 2: Reshape QuestionnaireAnswer, schema_version + nullable participant_type, Pydantic/admin-row fallout** - `35ac861` (feat)
3. **Task 3: Assessment-first upsert flow + adapt reports/admin/scoring to new shape** - `0fcf0dd` (feat)

**Plan metadata:** committed separately per final_commit step.

## Files Created/Modified
- `backend/app/models/assessment.py` - new `Assessment` (SQLModel table) + `AssessmentStatus` enum
- `backend/app/models/questionnaire_answer_archive.py` - new `QuestionnaireAnswerV1Archive` (read-only v1 shape mirror)
- `backend/app/models/questionnaire.py` - `QuestionnaireAnswer` reshaped to `assessment_id`/`category_id`/`score`
- `backend/app/models/initiative.py` - `schema_version` column; `participant_type` nullable
- `backend/app/models/user.py` - `participant_type` nullable
- `backend/app/db/base.py` - registers `Assessment`/`QuestionnaireAnswerV1Archive`
- `backend/app/schemas/questionnaire.py` - `AnswerCreate`/`AnswerRead` reshaped, score `ge=1, le=5`
- `backend/app/schemas/initiative.py` - `InitiativeRead.participant_type: str | None`
- `backend/app/schemas/auth.py` - `UserRead.participant_type: str | None`
- `backend/app/api/v1/questionnaire.py` - assessment-first upsert/get-answers flow
- `backend/app/api/v1/admin.py` - assessment-joined raw SQL, cascade-delete, CSV header, degraded heatmap
- `backend/app/api/v1/reports.py` - assessment-joined answer fetch, degraded scoring/rendering inputs
- `backend/app/api/v1/scoring.py` - same degradation treatment as reports.py (Rule 1 auto-fix)
- `backend/app/api/v1/initiatives.py` - guarded `participant_type.value` access (Rule 1 auto-fix)
- `backend/tests/factories.py` - `make_answer`/new `make_assessment` for the new shape
- `backend/tests/api/test_admin.py` - assessment-join queries, new CSV header assertion
- `backend/tests/api/test_reports.py` - new-shape fixture, updated module docstring
- `backend/tests/schemas/test_questionnaire_schemas.py` - new (16 tests)
- `backend/tests/api/test_questionnaire_answers.py` - new (5 tests)
- `docs/api/openapi.json` - regenerated (docs-freshness CI gate)
- `.planning/phases/13-new-questionnaire-config-schema-data-model-migration/deferred-items.md` - logged the recurring pre-existing local WeasyPrint gap

## Decisions Made
- `AssessmentStatus` mirrors `InitiativeStatus`'s existing `(str, Enum)` style (draft/submitted); `version: int` (default 1) plus existing `created_at`/`submitted_at` timestamps satisfy Phase 15's "dated version" need without a redundant field (RESEARCH Open Question 1 recommendation, adopted as-is).
- `Initiative`'s legacy tag is `schema_version: str` (`"v2"` default), not a boolean `is_legacy` — leaves room for a future v3 (D-03).
- `QuestionnaireAnswerV1Archive` is defined as a real SQLModel `table=True` class (not just a raw Alembic table) — importable/queryable, registered in `db/base.py`, per RESEARCH Open Question 2's recommendation.
- Dropped `followup_selections`/`followup_other`/`rationale` entirely from the LIVE answer shape (task 2's action text: "keep only if still referenced by a non-removed code path; otherwise drop") — no non-removed code path referenced them after `reports.py`'s degradation; they live on, verbatim, in the archive model only.
- No hard 422 guard for new-schema initiatives hitting report/heatmap/score endpoints (Assumption A3, discretionary) — degrade to zero findings/all-zero heatmap instead, with an inline code comment at every degraded site flagging it as a known Phase 13->14 interim limitation, not a real "compliant" signal.
- **scoring.py fixed as a Rule 1 auto-fix, not in the plan's file list:** `app/api/v1/scoring.py` directly used `QuestionnaireAnswer.initiative_id`/`.mami_code`/`.answer_value` and is a live, registered endpoint (`POST /initiatives/{id}/score`) — reshaping the model without touching it would have left a runtime `AttributeError` landmine on first real call. Adapted with the identical degrade-to-zero-findings treatment as `reports.py`.
- **initiatives.py + schemas/auth.py fixed as Rule 1 auto-fixes, not in the plan's explicit fallout list:** RESEARCH Pitfall 5 named only `InitiativeRead`/`AdminUserRow`/`AdminInitiativeRow` as needing the `str | None` fix, but making `Initiative.participant_type`/`User.participant_type` nullable (Task 2's own change) immediately breaks `initiatives.py::_to_read`'s unconditional `.value` access and mypy-flags `schemas/auth.py::UserRead.participant_type: str` as an argument-type mismatch. Both fixed in the same pass since they're a direct, unavoidable consequence of Task 2's own edit, not new scope.
- **Did NOT touch `auth.py`'s `/register` endpoint or `initiatives.py`'s `create_initiative`** to stop writing `participant_type` from request input, despite D-12's "new Initiatives/Users never set it" phrasing. Changing the registration/creation API contract (ignoring a field the frontend still actively sends) is a larger structural change than the plan's precise file/task list calls for (RESEARCH Pitfall 5 and Task 2's action text name only the read-side fallout). Flagged here as a deliberate scope decision, not silently expanded or silently dropped — a future phase can revisit if truly required.
- **MIGR-01 requirement NOT marked complete**, despite being listed in this plan's frontmatter `requirements: [QSTN-01, MIGR-01]`. Only `QSTN-01` is marked complete this plan (via `requirements mark-complete`) — MIGR-01 ("existing v1.0 MAMI initiative/answer data is preserved read-only") is the actual data migration + verification, explicitly scoped to 13-04 per this plan's own objective text ("The actual migration is 13-04; this plan defines the models/schemas") and success_criteria ("MIGR-01 foundation; migration itself is 13-04"). Marking it complete now — before any real legacy data has been copied into the archive table — would be inaccurate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adapted app/api/v1/scoring.py to the new answer shape**
- **Found during:** Task 3 (mypy full-app scan after the model reshape)
- **Issue:** `scoring.py` (not in this plan's `files_modified` list) directly queries `QuestionnaireAnswer.initiative_id` and reads `.mami_code`/`.answer_value` on each row for its live, registered `POST /initiatives/{id}/score` endpoint — none of these attributes exist after the Task 2 reshape. Left unfixed, this endpoint would `AttributeError` on first real call.
- **Fix:** Rewired the answer query through `Assessment` (mirroring `reports.py`'s new `_get_answers_for_initiative` pattern) and degraded scoring input to an empty list with an inline comment documenting the Phase 13->14 interim gap (same treatment as `reports.py`, Assumption A3).
- **Files modified:** `backend/app/api/v1/scoring.py`
- **Commit:** `0fcf0dd` (Task 3)

**2. [Rule 1 - Bug] Guarded initiatives.py::_to_read's participant_type.value access**
- **Found during:** Task 2 (after making `Initiative.participant_type` nullable)
- **Issue:** `_to_read` unconditionally calls `i.participant_type.value` — a latent `AttributeError` the moment any initiative's `participant_type` is actually `None` (which the schema now explicitly allows and `InitiativeRead.participant_type: str | None` claims to support).
- **Fix:** Changed to `i.participant_type.value if i.participant_type else None`.
- **Files modified:** `backend/app/api/v1/initiatives.py`
- **Commit:** `35ac861` (Task 2)

**3. [Rule 1 - Bug] Made schemas/auth.py::UserRead.participant_type nullable**
- **Found during:** Task 2 (mypy caught `Argument "participant_type" ... incompatible type "str | None"; expected "str"` at both `auth.py` call sites immediately after `User.participant_type` became nullable)
- **Issue:** `UserRead.participant_type: str` was not in RESEARCH Pitfall 5's explicit fallout list (which named only the Initiative-side schemas), but is the exact same class of bug on the User side.
- **Fix:** Changed to `str | None`.
- **Files modified:** `backend/app/schemas/auth.py`
- **Commit:** `35ac861` (Task 2)

**4. [Rule 3 - Blocking CI issue] Regenerated docs/api/openapi.json**
- **Found during:** Task 3 (post-implementation CI-gate check, same pattern as 13-01/13-02)
- **Issue:** `AnswerCreate`/`AnswerRead`/`InitiativeRead`/`UserRead`/`AdminUserRow`/`AdminInitiativeRow` all changed shape this plan; `docs-freshness` (pr.yml) hard-fails on any diff against a freshly regenerated file.
- **Fix:** Ran `uv run python scripts/export_openapi.py` and committed the resulting diff.
- **Files modified:** `docs/api/openapi.json`
- **Commit:** `0fcf0dd` (Task 3)

---

**Total deviations:** 4 auto-fixed (3 Rule 1 — bugs directly caused by this plan's own reshape, none pre-existing; 1 Rule 3 — blocking CI issue).
**Impact on plan:** All necessary for correctness/CI. No scope creep beyond what Task 2's own nullability change and Task 3's own reshape immediately, unavoidably broke — no new features added, no architectural changes made.

## Known Stubs / Interim Gaps

None of these are "stubs" in the sense of incomplete UI wiring (this is a backend-only, schema-and-migration phase — no frontend touched). However, per the plan's explicit prohibition, the following interim gap is flagged and documented (not hidden):

- **Report/heatmap/score endpoints degrade to zero findings for new-schema (v2) initiatives.** `reports.py`'s `/report`, `/report/data`, `/report/pdf`, `/report/mail`, `admin.py`'s `/heatmap`, and `scoring.py`'s `/score` all still run without raising, but produce zero findings / an all-zero heatmap for any initiative whose answers use the new `assessment_id`/`category_id`/`score` shape — the legacy MAMI-code-keyed ZEN/MoSCoW scoring engine has no valid input shape for them (RESEARCH Pitfall 3, Assumption A3). This is documented inline at every degraded call site with a code comment. **This is NOT a real "fully compliant" signal** — real per-assessment scoring against the new DSSC config is explicitly Phase 14 (scoring engine replacement) and Phase 16 (report contract)'s job, not this plan's.
- **Frontend still targets the OLD answer/config shape** (`mami_code`/`answer_value` referenced in `QuestionCard.tsx`, `WizardPage.tsx`, `FindingsPanel.tsx`, `lib/questionnaire.ts`, `lib/scoring.ts`, `routes/_app/report.tsx`) — unchanged since 13-01's SUMMARY flagged the same fact; wizard/report UI rebuild is explicitly Phase 15/16's job, out of scope for this backend-only plan.

## Issues Encountered

Same pre-existing, unrelated local-environment gap from Plans 13-01/13-02 recurred a third time: 4 tests in `backend/tests/api/test_reports.py` (`test_mail_report_generates_pdf_and_sends_email`, `test_mail_report_dev_mode_skips_resend_send`, `test_download_report_pdf_returns_pdf_content_type`, `test_download_report_pdf_no_answers_returns_422`) fail locally with `OSError: cannot load library 'libgobject-2.0-0'` (WeasyPrint/Pango native dependency, present in CI's Docker images per CLAUDE.md's documented fix but absent on this macOS dev machine). Confirmed via traceback that the failure is the unconditional `from weasyprint import HTML as WeasyHTML` import (unchanged position from the pre-Phase-13 code) failing before any of this plan's changed code paths run — not a regression. Logged in `deferred-items.md` under a new "Plan 13-03" section. All other 65 tests pass, including this plan's 21 new tests (16 in `test_questionnaire_schemas.py`, 5 in `test_questionnaire_answers.py`).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The Assessment-first schema (`assessment` table joining `initiative` <-> `questionnaire_answer`) is now the stable foundation Phase 14 (per-assessment scoring), Phase 15 (autosave/retake/history), and Phase 16 (per-assessment report contract) all key off, per CONTEXT.md's load-bearing note. The v1 archive model exists and is importable/queryable but is NOT yet populated with real legacy data — that data copy (plus the `CHECK (score BETWEEN 1 AND 5)` DB-level constraint mentioned in the threat register) is 13-04's job, the next and final plan in this phase. `reports.py`/`admin.py`/`scoring.py` are intentionally left in a documented degraded (not broken) state for new-schema initiatives — Phase 14/16 replace the actual scoring/report logic, not this plan.

No blockers for 13-04. Note for that plan's own execution: the models this plan added (`Assessment`, `QuestionnaireAnswerV1Archive`) and the reshaped `QuestionnaireAnswer` are the exact target shape the migration must produce via `op.create_table`/`op.execute` — this SUMMARY's `test_questionnaire_schemas.py` tests can serve as a cross-check that the migration's hand-written DDL matches what `SQLModel.metadata.create_all()` already builds in tests.

## Self-Check: PASSED

All created files confirmed on disk (`backend/app/models/assessment.py`, `backend/app/models/questionnaire_answer_archive.py`, `backend/tests/schemas/__init__.py`, `backend/tests/schemas/test_questionnaire_schemas.py`, `backend/tests/api/test_questionnaire_answers.py`, this SUMMARY) and all 3 task commits (`1dbf341`, `35ac861`, `0fcf0dd`) confirmed present in `git log`.

---
*Phase: 13-new-questionnaire-config-schema-data-model-migration*
*Completed: 2026-07-23*
