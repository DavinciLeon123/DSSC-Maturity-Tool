---
phase: 13-new-questionnaire-config-schema-data-model-migration
plan: 04
subsystem: database
tags: [alembic, postgres, sqlmodel, data-migration, testcontainers, migr-01]

requires:
  - phase: 13-03
    provides: "Assessment/QuestionnaireAnswerV1Archive/reshaped QuestionnaireAnswer SQLModel target shapes this migration's DDL must produce"
provides:
  - "Hand-written Alembic migration (i9d7e6f5a4b3, chains from h8c6d5e4f3a2) that creates assessment, creates questionnaire_answer_v1_archive, copies every pre-migration questionnaire_answer row into it verbatim, tags legacy initiatives via schema_version, makes participant_type nullable, and reshapes questionnaire_answer to assessment_id/category_id/score with a DB-level 1-5 CHECK constraint"
  - "backend/tests/migrations/ — the first migration-verification test category in this repo, exercising the real alembic upgrade head path against isolated Postgres testcontainers (not SQLModel.metadata.create_all())"
affects: [14-scoring-engine-replacement, 15-wizard-autosave-history, 16-report-visualization]

tech-stack:
  added: []
  patterns:
    - "Migration-verification via isolated testcontainer + alembic.command.upgrade/downgrade, function-scoped per test (never the shared session-scoped postgres_container/engine fixture) — new pattern this repo's future migrations should reuse"
    - "Archive-table-split migration (create new-shape table, copy old rows into a shape-preserving archive with no FK back to the parent, tag a cheap filter column, then drop+recreate) for schema reshapes too large for op.alter_column"

key-files:
  created:
    - backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py
    - backend/tests/migrations/__init__.py
    - backend/tests/migrations/test_v1_archive_migration.py
  modified:
    - .planning/phases/13-new-questionnaire-config-schema-data-model-migration/deferred-items.md

key-decisions:
  - "Revision id used exactly as the plan's assumption specified (i9d7e6f5a4b3, down_revision h8c6d5e4f3a2) — hand-written, not alembic revision --autogenerate, matching every prior data-transforming migration in this repo's history"
  - "Migration test fixture spins up a fresh PostgresContainer per test (3 containers total across the file) rather than sharing one module-scoped container with schema resets between tests — simpler and correctness-first, since this test category's job is proving the real upgrade path works, not raw speed; it still runs well under a second per test and stays out of the perf/benchmark markers"
  - "Seeded-DB test uses raw SQL INSERT (not the SQLModel model, which 13-03 already reshaped and can no longer express the old columns) against the OLD schema reached by upgrading only to h8c6d5e4f3a2 first, exactly as the plan's key_links section specified"
  - "docs/api/openapi.json regenerated but produced zero diff — this plan changes no Pydantic schema, only the DB migration and its own test suite, so the docs-freshness gate needed no commit"

patterns-established:
  - "Any future full-reshape migration (not a simple ALTER) in this repo should get its own tests/migrations/test_*.py using the isolated-testcontainer + alembic.command pattern established here, rather than relying on conftest.py's create_all()-based schema"

requirements-completed: [MIGR-01]

coverage:
  - id: D1
    description: "A single hand-written Alembic migration (i9d7e6f5a4b3) chains from h8c6d5e4f3a2 and creates assessment, questionnaire_answer_v1_archive (old shape, sa.String not enum, no FK to initiative), copies existing questionnaire_answer rows verbatim, tags legacy initiatives via schema_version, makes participant_type nullable, and reshapes questionnaire_answer to the new assessment_id/category_id/score shape with a DB-level CHECK(1-5)"
    requirement: "MIGR-01"
    verification:
      - kind: integration
        ref: "backend/tests/migrations/test_v1_archive_migration.py::test_upgrade_head_from_empty_db_creates_new_tables"
        status: pass
      - kind: unit
        ref: "cd backend && uv run python -c \"from alembic.config import Config; from alembic.script import ScriptDirectory; ...\" (single head, chains from h8c6d5e4f3a2)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every pre-migration questionnaire_answer row is preserved verbatim (same count, answer_value, initiative_id linkage) in questionnaire_answer_v1_archive after upgrade, and initiatives with archived answers are tagged v1_legacy while an answerless initiative correctly stays v2 (the MIGR-01 zero-answers edge)"
    requirement: "MIGR-01"
    verification:
      - kind: integration
        ref: "backend/tests/migrations/test_v1_archive_migration.py::test_upgrade_preserves_seeded_v1_answers_and_tags_legacy_initiatives"
        status: pass
    human_judgment: false
  - id: D3
    description: "alembic upgrade head -> downgrade -1 -> upgrade head succeeds without error against a Postgres testcontainer seeded with pre-migration-shaped data"
    requirement: "MIGR-01"
    verification:
      - kind: integration
        ref: "backend/tests/migrations/test_v1_archive_migration.py::test_upgrade_downgrade_upgrade_round_trip_succeeds"
        status: pass
    human_judgment: false
  - id: D4
    description: "docs/api/openapi.json regenerated via scripts/export_openapi.py matches the committed file (docs-freshness CI gate), and the full local quality gate (ruff, mypy, quick pytest suite) is green"
    verification:
      - kind: integration
        ref: "cd backend && uv run python scripts/export_openapi.py && git diff --exit-code ../docs/api/openapi.json (clean) + uv run ruff check . && uv run ruff format --check . && uv run mypy app --ignore-missing-imports (0 errors) + uv run pytest tests/ -n auto -m 'not perf and not benchmark' -q (68 passed; 4 pre-existing local WeasyPrint failures, unrelated)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-23
status: complete
---

# Phase 13 Plan 04: Alembic Archive-Table-Split Migration + Verification Summary

**Hand-written Alembic migration (i9d7e6f5a4b3) implementing the archive-table-split pattern — creates `assessment`, archives every pre-migration `questionnaire_answer` row verbatim into `questionnaire_answer_v1_archive`, tags legacy initiatives, and reshapes `questionnaire_answer` to `assessment_id`/`category_id`/`score` with a DB-level 1-5 CHECK — proven against three isolated Postgres testcontainers, the first migration-verification tests in this repo.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-23T09:38:00Z
- **Completed:** 2026-07-23T09:47:25Z
- **Tasks:** 3 completed
- **Files modified:** 3 created, 1 modified (deferred-items.md)

## Accomplishments
- Wrote `backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py` — a single hand-written migration (no autogenerate, per RESEARCH Anti-Patterns) chained from head `h8c6d5e4f3a2`. `upgrade()` creates `assessment` (D-06/D-07 shape), creates `questionnaire_answer_v1_archive` mirroring the OLD `questionnaire_answer` columns exactly (`answer_value` as explicit `sa.String()`, never a native Postgres ENUM — RESEARCH Pitfall 1; no FK to `initiative.id` — D-01/A2), copies every existing row verbatim via `op.execute INSERT ... SELECT`, adds `initiative.schema_version` (server_default `'v2'`) and tags initiatives with archived answers `'v1_legacy'`, makes `initiative.participant_type`/`user.participant_type` nullable (D-12), then drops and recreates `questionnaire_answer` with the new `assessment_id`/`category_id`/`score` shape, a `uq_answer_per_question_v2` unique constraint, and a `ck_answer_score_range` CHECK (`score BETWEEN 1 AND 5`, security V5 defense-in-depth). Does not touch `compliance_report` or `evidence_url` (D-05/Pitfall 4). `downgrade()` reverses every step in dependency-safe order (new answer table -> old-shape recreate + archive restore -> archive drop -> assessment drop), documented as lossy for any new-shape answers written after the original upgrade (same accepted lossiness precedent as `f6a4b3c2d1e9`).
- Added `backend/tests/migrations/__init__.py` and `test_v1_archive_migration.py` — the **first migration-verification test category in this repo** (RESEARCH Pitfall 2: `conftest.py` bypasses Alembic entirely via `create_all()`, so no test today had ever exercised the real `alembic upgrade head` path). Built an `alembic_env` fixture that spins up a fresh, isolated `PostgresContainer` per test (deliberately not the shared session-scoped `postgres_container`/`engine` fixtures) and points Alembic at it by setting the `DATABASE_URL` env var `env.py` reads at run time, then runs `alembic.command.upgrade`/`downgrade` programmatically. Three tests: (1) empty-DB upgrade creates all new tables with the new answer shape and no `mami_code`/`initiative_id`; (2) seeded-DB upgrade (raw-SQL pre-migration rows across 3 initiatives, 2 with answers/1 without) preserves archive row count/content/linkage exactly and tags only the answered initiatives `'v1_legacy'`, correctly leaving the answerless one at `'v2'` (the MIGR-01 zero-answers edge, explicitly asserted); (3) `upgrade -> downgrade -> upgrade` round-trip against seeded data succeeds and the seeded rows survive the full trip. Not perf/benchmark-marked — runs in the default fast gate.
- Ran `uv run python scripts/export_openapi.py`: zero diff (this plan changes no Pydantic schema, only the migration and its own tests), so the docs-freshness gate needed no commit. Ran the full local quality gate: `ruff check`/`ruff format --check`/`mypy app --ignore-missing-imports` all clean; `pytest tests/ -n auto -m "not perf and not benchmark" -q` — 68 passed, the same 4 pre-existing local WeasyPrint/`libgobject-2.0-0` failures in `test_reports.py` recurring a fourth consecutive plan (unrelated to this plan's changes — confirmed via traceback, logged in `deferred-items.md`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Hand-write the archive-table-split Alembic migration (chained from h8c6d5e4f3a2)** - `4708409` (feat)
2. **Task 2: [BLOCKING] Migration-verification test against an isolated testcontainer (MIGR-01)** - `acc9d17` (test)
3. **Task 3: Regenerate docs/api/openapi.json (docs-freshness CI gate) + full quality gate** - `1443eb1` (docs)

**Plan metadata:** committed separately per final_commit step.

## Files Created/Modified
- `backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py` - the phase's core migration (assessment + archive-table-split + reshape)
- `backend/tests/migrations/__init__.py` - new test package
- `backend/tests/migrations/test_v1_archive_migration.py` - 3 tests: empty-DB upgrade, seeded-DB preservation/tagging, upgrade/downgrade/upgrade round-trip
- `.planning/phases/13-new-questionnaire-config-schema-data-model-migration/deferred-items.md` - logged the 4th recurrence of the pre-existing local WeasyPrint gap

## Decisions Made
- Used the plan's proposed revision id (`i9d7e6f5a4b3`) verbatim rather than letting `alembic revision` auto-generate a hash — the file was hand-authored directly (no autogenerate command run at all), matching RESEARCH's explicit prohibition against relying on autogenerate for this reshape (`env.py` sets no `compare_type`).
- Each of the 3 migration tests gets its own fresh `PostgresContainer` (3 containers total for the file) rather than a single module-scoped container with manual schema resets between tests — simpler to reason about correctness for a new, high-stakes test category, and still fast (~5-6s for all 3 combined), well within the "not perf/benchmark" quick gate.
- The seeded-DB and round-trip tests upgrade only to `h8c6d5e4f3a2` first, then insert OLD-shaped rows via raw SQL (matching the plan's key_links note that the reshaped SQLModel model can no longer express the pre-migration column shape), before upgrading the rest of the way to `head`.
- No commit needed for `docs/api/openapi.json` — regenerating it produced a byte-identical file, confirming this plan introduced no Pydantic-schema-visible change (expected: it's a pure DB-migration + test plan).

## Deviations from Plan

None - plan executed exactly as written. The migration's structure, column shapes, constraint names, and the three-test verification suite all match the plan's `must_haves`/`key_links`/`action` text directly; no bugs, missing functionality, blocking issues, or architectural changes were discovered during implementation.

## Issues Encountered

Same pre-existing, unrelated local-environment gap from Plans 13-01/13-02/13-03 recurred a fourth time: 4 tests in `backend/tests/api/test_reports.py` fail locally with `OSError: cannot load library 'libgobject-2.0-0'` (WeasyPrint/Pango native dependency, present in CI's Docker images per CLAUDE.md's documented fix but absent on this macOS dev machine). This plan touches only `backend/alembic/versions/` and `backend/tests/migrations/`, neither of which is imported by `reports.py`/`report_generator.py` — confirmed via the same WeasyPrint/cffi import failure trace as the prior 3 plans. Logged in `deferred-items.md` under a new "Plan 13-04" section rather than fixed (out of scope, CI is the authoritative signal). All 68 other tests pass, including this plan's own 3 new migration-verification tests (the BLOCKING gate).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 13 (New Questionnaire Config Schema & Data Model Migration) is now **complete** — this was the final plan (wave 4 of 4). MIGR-01 is fully satisfied: the archive-table-split migration is hand-written, chains cleanly from the prior head, and is proven — not just assumed — to preserve every pre-migration row verbatim and tag legacy initiatives correctly, against a real Postgres upgrade path rather than `SQLModel.metadata.create_all()`. Combined with 13-01 (universal config), 13-02 (evidence removal), and 13-03 (Assessment entity + answer reshape), the full v2 schema foundation is now durable, deployed-shape-correct, and safe to run at container startup (`alembic upgrade head`).

Phase 14 (scoring engine replacement) can now proceed: it inherits a stable `Assessment`-keyed `questionnaire_answer` table (1-5 score, `category_id`), a populated (once real legacy data exists) `questionnaire_answer_v1_archive` for historical reference, and `Initiative.schema_version` as a cheap legacy-vs-new filter. Phase 14/16's known interim gap (reports/heatmap/score degrading to zero findings for new-schema initiatives, documented in 13-03's SUMMARY) remains exactly as that plan left it — this plan did not touch `reports.py`/`admin.py`/`scoring.py`.

No blockers for Phase 14.

## Self-Check: PASSED

All created files confirmed on disk (`backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py`, `backend/tests/migrations/__init__.py`, `backend/tests/migrations/test_v1_archive_migration.py`, this SUMMARY) and all 3 task commits (`4708409`, `acc9d17`, `1443eb1`) confirmed present in `git log`.

---
*Phase: 13-new-questionnaire-config-schema-data-model-migration*
*Completed: 2026-07-23*
