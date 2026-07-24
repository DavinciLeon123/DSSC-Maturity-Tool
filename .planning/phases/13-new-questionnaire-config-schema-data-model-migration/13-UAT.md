---
status: complete
phase: 13-new-questionnaire-config-schema-data-model-migration
source: [13-01-SUMMARY.md, 13-02-SUMMARY.md, 13-03-SUMMARY.md, 13-04-SUMMARY.md]
started: 2026-07-24T07:59:38Z
updated: 2026-07-24T08:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: |
  Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files).
  Start the application from scratch (including running `alembic upgrade head` against a
  fresh database). Server boots without errors, the new `i9d7e6f5a4b3` migration completes
  cleanly (creates assessment/questionnaire_answer_v1_archive, reshapes questionnaire_answer),
  and a primary query (health check or GET /questionnaire/config) returns live data.
result: pass

### 2. Questionnaire config defines 52 questions / 6 categories with override support
expected: config/dssc-questionnaire.json defines exactly 52 questions across exactly 6 categories, with a shared 5-label default_options set (scores 1-5) and one question demonstrating a per-question options override (QSTN-01, QSTN-03, QSTN-05)
result: pass
source: automated
coverage_id: 13-01/D1

### 3. Questionnaire config endpoint is universal
expected: GET /questionnaire/config serves the identical universal config to every authenticated caller regardless of participant_type, returning 200 even with no owned Initiative (QSTN-04)
result: pass
source: automated
coverage_id: 13-01/D2

### 4. Evidence subsystem fully removed from codebase
expected: The evidence/URL-per-question subsystem no longer exists anywhere — no model, no schema, no API router, no frontend file (MIGR-02)
result: pass
source: automated
coverage_id: 13-02/D1

### 5. Former evidence routes return 404
expected: Requests to the former /api/v1/initiatives/{id}/evidence routes return 404, not 405 or 500 (MIGR-02)
result: pass
source: automated
coverage_id: 13-02/D2

### 6. App boots and Phase-12 suite green after evidence removal
expected: The app imports and boots, and the existing Phase-12 suite (auth/admin/reports/report_generator) is green after evidence plumbing is stripped (MIGR-02)
result: pass
source: automated
coverage_id: 13-02/D3

### 7. Admin cascade-delete unaffected by evidence removal
expected: Admin cascade-delete of an Initiative no longer attempts to delete evidence rows and still succeeds (MIGR-02)
result: pass
source: automated
coverage_id: 13-02/D4

### 8. Assessment entity created lazily with correct defaults
expected: A new Assessment table exists with initiative_id FK, integer version, created_at/submitted_at, and a status enum limited to draft/submitted; an Assessment row is created lazily on the first answer write in draft status (QSTN-01)
result: pass
source: automated
coverage_id: 13-03/D1

### 9. questionnaire_answer reshaped to assessment-keyed score model
expected: questionnaire_answer is reshaped to key off assessment_id, carry category_id, and store an integer score (1-5) — no mami_code/initiative_id/3-way enum remains; unique constraint renamed to uq_answer_per_question_v2 (QSTN-01)
result: pass
source: automated
coverage_id: 13-03/D2

### 10. Archive table mirrors old shape and survives hard-delete
expected: questionnaire_answer_v1_archive mirrors the OLD answer shape with no FK to initiative (survives a hard-delete) and an explicit String answer_value column (not a native enum)
result: pass
source: automated
coverage_id: 13-03/D3

### 11. AnswerCreate.score enforces 1-5 range at schema layer
expected: AnswerCreate.score rejects out-of-range values (0, -1, 6, 100) and accepts 1-5 at the Pydantic layer (security V5)
result: pass
source: automated
coverage_id: 13-03/D4

### 12. schema_version defaults and participant_type nullable fallout fixed
expected: Initiative.schema_version defaults to 'v2'; participant_type nullable on Initiative and User with Pydantic/admin-row fallout fixed (InitiativeRead, UserRead, AdminUserRow, AdminInitiativeRow all accept None)
result: pass
source: automated
coverage_id: 13-03/D5

### 13. Answer upsert re-derives ownership, rejects non-owners
expected: Assessment-first upsert endpoint re-derives ownership through Assessment.initiative_id -> Initiative.user_id; a non-owner gets 403 and no Assessment is created as a side effect
result: pass
source: automated
coverage_id: 13-03/D6

### 14. Reports/admin/scoring adapted to new answer shape without raising
expected: reports.py/admin.py/scoring.py adapted to the new answer shape — app imports and the full backend suite runs green; reports/heatmap/scoring degrade to zero findings for new-schema initiatives rather than raising
result: pass
source: automated
coverage_id: 13-03/D7

### 15. Migration creates new schema and reshapes questionnaire_answer with DB-level CHECK
expected: A single hand-written Alembic migration (i9d7e6f5a4b3) chains from h8c6d5e4f3a2 and creates assessment, questionnaire_answer_v1_archive (old shape, sa.String not enum, no FK to initiative), copies existing questionnaire_answer rows verbatim, tags legacy initiatives via schema_version, makes participant_type nullable, and reshapes questionnaire_answer to the new assessment_id/category_id/score shape with a DB-level CHECK(1-5) (MIGR-01)
result: pass
source: automated
coverage_id: 13-04/D1

### 16. Pre-migration rows preserved verbatim and legacy-tagged correctly
expected: Every pre-migration questionnaire_answer row is preserved verbatim (same count, answer_value, initiative_id linkage) in questionnaire_answer_v1_archive after upgrade, and initiatives with archived answers are tagged v1_legacy while an answerless initiative correctly stays v2 (MIGR-01)
result: pass
source: automated
coverage_id: 13-04/D2

### 17. Migration upgrade/downgrade/upgrade round-trip succeeds
expected: alembic upgrade head -> downgrade -1 -> upgrade head succeeds without error against a Postgres testcontainer seeded with pre-migration-shaped data (MIGR-01)
result: pass
source: automated
coverage_id: 13-04/D3

### 18. Docs freshness and full quality gate green
expected: docs/api/openapi.json regenerated via scripts/export_openapi.py matches the committed file (docs-freshness CI gate), and the full local quality gate (ruff, mypy, quick pytest suite) is green
result: pass
source: automated
coverage_id: 13-04/D4

## Summary

total: 18
passed: 18
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
