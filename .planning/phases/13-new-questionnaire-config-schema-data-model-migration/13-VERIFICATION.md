---
phase: 13-new-questionnaire-config-schema-data-model-migration
verified: 2026-07-23T16:00:00Z
status: passed
score: 5/5 roadmap success criteria verified; both prior gaps confirmed resolved
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: "5/5 roadmap success criteria verified; 1 blocking regression found post-review-fix"
  gaps_closed:
    - "docs/api/openapi.json regenerated via scripts/export_openapi.py matches the committed file (docs-freshness CI gate passes)"
  gaps_remaining: []
  regressions: []
---

# Phase 13: New Questionnaire Config Schema & Data Model Migration Verification Report

**Phase Goal:** The system is driven by a new 52-question/6-category universal questionnaire config, and the database plus all existing v1.0 data have been migrated to support it without data loss.
**Verified:** 2026-07-23T16:00:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure

## Goal Achievement

This is a focused re-verification of the two items the previous pass (2026-07-23T10:30:00Z, `status: gaps_found`) left open. Per the task instructions, the 5 ROADMAP success criteria (config structure, config-driven text, universal questionnaire, v1 data preservation, evidence-subsystem removal) were confirmed true in the prior pass with strong direct evidence and no signal of regression was found while re-checking git history, quality gates, and the full test suite in this pass — they are not re-derived from scratch here.

### Item 1: docs/api/openapi.json staleness (was: blocking regression)

**Claimed fix:** commit `d3762b7` — "docs(13): regenerate openapi.json after review-fix schema/docstring changes" (7 lines changed: `+6/-1`, matching the exact `AdminHeatmapResponse.degraded` field and `submit_initiative` docstring diff the previous verifier identified).

**Verification performed:**
- Ran `cd backend && uv run python scripts/export_openapi.py` against current HEAD.
- Ran `git diff --exit-code -- docs/api/openapi.json` immediately after regeneration.
- **Result: exit code 0, empty diff.** The regenerated file is byte-identical to the committed file.
- `git status --short` in the backend directory showed no modification to `docs/api/openapi.json` after the regeneration (only an unrelated untracked verification-report file from this session).

**Status: ✓ VERIFIED — RESOLVED.** The docs-freshness CI gate (`pr.yml`/`staging.yml`/`main.yml` per CLAUDE.md) will pass on this branch as committed.

### Item 2: CR-02 test coverage gap (was: flagged for human judgment)

**Claimed fix:** commit `058ffc1` — "test(13): CR-02 add DB-level unique-draft-index regression test", adding `test_assessment_unique_draft_index_rejects_concurrent_duplicate` to `backend/tests/migrations/test_v1_archive_migration.py`.

**Verification performed:**
1. **Test exists and is correctly written** — read the full test (lines 228-287 of `test_v1_archive_migration.py`). It:
   - Uses the `alembic_env` fixture, which builds schema via a real `alembic upgrade head` against an isolated Postgres testcontainer (not the shared `conftest.py` `create_all()`-based fixtures) — the exact gap the previous verifier flagged.
   - Seeds a real `user` and `initiative` row, inserts one `draft` `Assessment` for that `initiative_id` (succeeds), then attempts a second `draft` `Assessment` insert for the *same* `initiative_id` inside `pytest.raises(sa.exc.IntegrityError)`.
2. **Matches the migration's actual index definition** — read `alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py` lines 94-110 directly: `op.create_index("uq_assessment_one_draft_per_initiative", "assessment", ["initiative_id"], unique=True, postgresql_where=sa.text("status = 'draft'"))`. This is exactly what the test exercises — same index name in the accompanying comment, same column (`initiative_id`), same uniqueness scope (partial, `status = 'draft'`), and the test's inserted rows both use `status='draft'` (matching the predicate) with the same `initiative_id`.
3. **Passes when run live** — ran (not trusted from SUMMARY):
   ```
   uv run pytest tests/migrations/test_v1_archive_migration.py -x -q
   → 4 passed
   ```
   All 4 tests in the file pass, including the new one, confirming the partial unique index does reject the second concurrent draft insert against a schema built via the real migration path.

**Status: ✓ VERIFIED — RESOLVED.** This closes the previously-flagged human-judgment gap: there is now a permanent, correctly-scoped regression test proving the DB-level concurrency guard actually works against a real migrated schema, not just inferred from deployment configuration.

### Full Backend Quick Suite (re-run live)

```
uv run pytest tests/ -n auto -m "not perf and not benchmark" -q
→ 69 passed, 4 failed
```

Matches the expected count exactly (68 passed in the prior pass + 1 new CR-02 test = 69 passed). The 4 failures are unchanged and confirmed via direct traceback inspection to be the same pre-existing, already-documented local WeasyPrint `libgobject-2.0-0` native-library gap (`test_mail_report_generates_pdf_and_sends_email`, `test_mail_report_dev_mode_skips_resend_send`, `test_download_report_pdf_returns_pdf_content_type`, `test_download_report_pdf_no_answers_returns_422`, all in `tests/api/test_reports.py`) — the traceback shows `weasyprint/text/ffi.py`'s `_dlopen` failing to load `libgobject-2.0-0`, unrelated to this phase's code.

### Quality Gates (re-run live)

| Gate | Command | Result |
|------|---------|--------|
| ruff | `uv run ruff check .` | All checks passed |
| mypy | `uv run mypy app --ignore-missing-imports` | Success: no issues found in 33 source files |
| docs-freshness | `uv run python scripts/export_openapi.py && git diff --exit-code -- docs/api/openapi.json` | Exit 0, empty diff — PASS |
| Migration suite | `uv run pytest tests/migrations/test_v1_archive_migration.py -x -q` | 4 passed |
| Full quick suite | `uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` | 69 passed, 4 failed (pre-existing WeasyPrint gap) |

### Observable Truths (ROADMAP Success Criteria — carried forward, no regression found)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A single config file defines 52 questions across 6 categories, each with 5 custom-labeled answer options mapped to a 1-5 score | ✓ VERIFIED (prior pass; no changes to `config/dssc-questionnaire.json` since) | Confirmed unchanged via `git log` — no commits touching this file since prior verification. |
| 2 | Editing question text/labels requires only a config edit, no code deploy | ✓ VERIFIED (prior pass; unchanged) | No loader/endpoint changes since prior verification. |
| 3 | The questionnaire is presented identically to every user — no participant-type split remains in schema/models/routing | ✓ VERIFIED (prior pass; unchanged) | `questionnaire.py`'s `GET /questionnaire/config` untouched by the two fix commits reviewed in this pass. |
| 4 | All pre-migration v1.0 MAMI data remains intact and queryable read-only | ✓ VERIFIED — re-confirmed live in this pass | Migration suite re-run live: 4/4 pass (including the new CR-02 test, which itself further hardens MIGR-01's Assessment-table invariants). |
| 5 | The evidence/URL-per-question subsystem no longer exists anywhere in the codebase | ✓ VERIFIED (prior pass; unchanged) | No evidence-related files touched by the two fix commits reviewed in this pass. |

**Score:** 5/5 roadmap success criteria hold; both previously-open gaps confirmed resolved with direct evidence in this pass.

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| QSTN-01 | ✓ SATISFIED | Unchanged since prior pass; confirmed still marked complete in `.planning/REQUIREMENTS.md`. |
| QSTN-03 | ✓ SATISFIED | Unchanged since prior pass. |
| QSTN-04 | ✓ SATISFIED | Unchanged since prior pass. |
| QSTN-05 | ✓ SATISFIED | Unchanged since prior pass. |
| MIGR-01 | ✓ SATISFIED | Strengthened in this pass — migration-verification suite now includes a permanent CR-02 regression test proving the Assessment draft-uniqueness invariant, run live: 4/4 pass. |
| MIGR-02 | ✓ SATISFIED | Unchanged since prior pass. |

No orphaned requirements.

### Anti-Patterns Found

None in the two files touched by the fix commits (`docs/api/openapi.json` — generated JSON, not applicable; `backend/tests/migrations/test_v1_archive_migration.py` — no `TBD`/`FIXME`/`XXX`/`TODO`/placeholder markers, no stub patterns).

### Human Verification Required

None. Both items previously requiring human judgment or blocking automated resolution are now closed with direct, live-run evidence.

### Gaps Summary

Both gaps from the previous verification pass are resolved:

1. **docs/api/openapi.json staleness** — regenerated and committed (`d3762b7`); re-running the export script now produces zero diff against the committed file. The docs-freshness CI gate passes.
2. **CR-02 test coverage** — a new permanent test (`test_assessment_unique_draft_index_rejects_concurrent_duplicate`, commit `058ffc1`) was added, verified to correctly match the migration's actual partial unique index definition (`uq_assessment_one_draft_per_initiative` on `assessment.initiative_id WHERE status = 'draft'`), and passes live against a real `alembic upgrade head`-built schema.

No new regressions were introduced by either fix. The full backend quick suite passes at the expected count (69 passed / 4 failed, the 4 being the unchanged, pre-existing, already-documented local WeasyPrint native-library gap unrelated to this phase). ruff and mypy are both clean.

Phase 13's goal — the system driven by the new 52-question/6-category universal questionnaire config, with the database and all v1.0 data migrated without loss — is achieved and verified in the current codebase. Ready to proceed.

---

_Verified: 2026-07-23T16:00:00Z_
_Verifier: Claude (gsd-verifier)_
