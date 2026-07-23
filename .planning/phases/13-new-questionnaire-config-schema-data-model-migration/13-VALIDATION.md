---
phase: 13
slug: new-questionnaire-config-schema-data-model-migration
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-22
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1+, pytest-xdist (`-n auto`), testcontainers[postgres] 4.14.2+ |
| **Config file** | `backend/pyproject.toml` (pytest config + `perf`/`benchmark` marker registration); `backend/tests/conftest.py` for fixtures |
| **Quick run command** | `uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` (CLAUDE.md local quality gate) |
| **Full suite command** | `uv run pytest tests/ -n auto -m "not perf"` (staging.yml — includes benchmark) |
| **Estimated runtime** | Not measured in RESEARCH.md — existing suite runtime is not baselined; the new migration test must stay fast (schema-only, no large data volumes) so it can run in the default (non-perf/benchmark) gate |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` (existing CLAUDE.md gate)
- **After every plan wave:** Full suite including the new migration-verification test (not perf/benchmark-marked, so it also runs in the quick gate)
- **Before `/gsd-verify-work`:** Full suite green, plus a scripted check that `alembic upgrade head` then `alembic downgrade -1` both succeed against a testcontainer seeded with realistic pre-migration row counts
- **Max feedback latency:** Not explicitly bounded by CONTEXT.md; keep the migration test itself in the seconds range (schema-only operations, no bulk data)

---

## Per-Task Verification Map

Task IDs are TBD — filled in by the planner as PLAN.md tasks are created. Verification below maps directly to the phase's REQ-IDs per RESEARCH.md's Phase Requirements → Test Map.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01/Task 3 | 13-01-PLAN | 1 | QSTN-01 | — | Config exposes 52 questions across 6 categories | unit | `pytest tests/services/test_dssc_config.py::test_all_52_questions_present -x` | ✅ | ✅ green |
| 13-01/Task 3 | 13-01-PLAN | 1 | QSTN-03 | — | Config-driven labels — editing JSON changes served content, no code branches on content | unit | `pytest tests/services/test_dssc_config.py::test_config_is_pure_data_no_hardcoded_labels -x` | ✅ | ✅ green |
| 13-01/Task 3 | 13-01-PLAN | 1 | QSTN-04 | T-13-01 (cross-initiative access) | `GET /questionnaire/config` returns identical config regardless of participant_type; separately, PUT/GET answer endpoints re-derive ownership through `Initiative.user_id` | integration | `pytest tests/api/test_questionnaire.py::test_config_endpoint_universal -x` + `pytest tests/api/test_questionnaire_answers.py::test_upsert_answer_rejects_non_owner -x` | ✅ | ✅ green |
| 13-01/Task 3 | 13-01-PLAN | 1 | QSTN-05 | — | Placeholder content stubs all 52 questions (structural check) | unit | `pytest tests/services/test_dssc_config.py::test_all_52_questions_present -x` | ✅ | ✅ green |
| 13-04/Task 2 | 13-04-PLAN | 4 | MIGR-01 | T-13-03 | Pre-migration v1.0 data intact, queryable, read-only in archive table after upgrade; upgrade/downgrade/upgrade round-trip succeeds | integration (migration) | `pytest tests/migrations/test_v1_archive_migration.py -x` | ✅ | ✅ green |
| 13-02/Task 3 | 13-02-PLAN | 2 | MIGR-02 | T-13-06 | Evidence subsystem fully absent (no table, no route, no frontend file, no import) | integration + static check | `pytest tests/api/test_evidence_removed.py -x` | ✅ | ✅ green |
| 13-03/Task 2 | 13-03-PLAN | 3 | — (security) | T-13-02 / T-13-02b | `score` field rejects values outside 1-5 at both Pydantic and DB layers | unit + migration | `pytest tests/schemas/test_questionnaire_schemas.py -x` + `pytest tests/migrations/test_v1_archive_migration.py::test_upgrade_preserves_seeded_v1_answers_and_tags_legacy_initiatives -x` (asserts DB CHECK rejects out-of-range insert) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Beyond-plan coverage found during audit:** `tests/api/test_questionnaire_answers.py` (not listed in the original Wave 0 plan) covers the full assessment-first upsert flow — lazy draft creation, upsert-not-duplicate, owner-scoped reads, empty-assessment reads, and non-owner rejection (T-13-01). All 5 tests green.

---

## Wave 0 Requirements

- [x] `tests/services/test_dssc_config.py` — covers QSTN-01/03/05 (config shape, 52 questions, 6 categories, per-question label overrides)
- [x] `tests/api/test_questionnaire.py` — covers QSTN-04 (universal config endpoint, no participant_type branching)
- [x] `tests/migrations/test_v1_archive_migration.py` — covers MIGR-01: fresh-DB `alembic upgrade head`, seeded-DB upgrade preserving archive rows + legacy tagging, concurrent-draft unique-index guard, and upgrade/downgrade/upgrade round-trip. New `tests/migrations/` category, isolated testcontainer per test (not the shared session-scoped fixtures).
- [x] `tests/api/test_evidence_removed.py` — covers MIGR-02 (evidence routes return 404, not 500; no `EvidenceURL` import survives — verified by both source-scan and AST walk)
- [x] `tests/factories.py`, `tests/api/test_admin.py`, `tests/api/test_reports.py`, `tests/services/test_report_generator.py` — updated to remove `make_evidence`/`EvidenceURL`/`evidence_by_code` usage; existing Phase-12 tests keep collecting and passing
- [x] `tests/schemas/test_questionnaire_schemas.py` — covers the security contribution's `score: Field(ge=1, le=5)` validation
- [x] (beyond plan) `tests/api/test_questionnaire_answers.py` — covers the assessment-first upsert flow and ownership re-derivation (T-13-01), not originally listed in Wave 0

*Wave 0 must land before the success-criterion test files can execute — this phase adds the first migration-verification infrastructure this repo has ever had (Pitfall 2 in RESEARCH.md).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `docs/api/openapi.json` regenerated and committed | Project constraint (CLAUDE.md `docs-freshness` gate) | CI gate, not a pytest assertion | `uv run python scripts/export_openapi.py` then `git diff --exit-code docs/api/openapi.json` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (confirmed by gsd-plan-checker across all 4 PLAN.md files)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test_dssc_config.py/test_questionnaire.py → 13-01; test_evidence_removed.py + factory/test updates → 13-02; test_questionnaire_schemas.py → 13-03; tests/migrations/test_v1_archive_migration.py → 13-04)
- [x] No watch-mode flags
- [x] Feedback latency acceptable (migration test stays in the seconds range)
- [x] `nyquist_compliant: true` set in frontmatter

`wave_0_complete` stays `false` until execution actually lands the test files above — this sign-off certifies the plans' *design* is Nyquist-compliant, not that the tests exist yet.

---

## Validation Audit 2026-07-23

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 7 (all planned Wave 0 test files confirmed present + green; 1 bonus file found beyond plan) |
| Escalated | 0 |

All 7 planned requirement rows (QSTN-01/03/04/05, MIGR-01, MIGR-02, security score-range) map to real test files that exist and pass: `tests/services/test_dssc_config.py`, `tests/api/test_questionnaire.py`, `tests/api/test_questionnaire_answers.py`, `tests/migrations/test_v1_archive_migration.py`, `tests/api/test_evidence_removed.py`, `tests/schemas/test_questionnaire_schemas.py`. Ran the full relevant set (`tests/services/test_dssc_config.py tests/api/test_questionnaire.py tests/api/test_questionnaire_answers.py tests/api/test_evidence_removed.py tests/migrations/test_v1_archive_migration.py tests/schemas/test_questionnaire_schemas.py tests/api/test_admin.py tests/api/test_reports.py tests/services/test_report_generator.py`): 52 passed. The 4 unrelated failures in `test_reports.py` (PDF-mail/download tests) are a pre-existing local-environment gap — WeasyPrint cannot load `libgobject-2.0-0` on this machine — not a phase-13 regression or Nyquist gap; CI's Docker-built images carry the full Cairo/Pango/GObject toolchain WeasyPrint needs. `wave_0_complete` flips to `true` and `status: validated`.

**Approval:** approved 2026-07-22 (gsd-plan-checker: 0 blockers)
