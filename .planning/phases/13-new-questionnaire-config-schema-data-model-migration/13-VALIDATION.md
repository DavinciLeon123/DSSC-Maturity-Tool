---
phase: 13
slug: new-questionnaire-config-schema-data-model-migration
status: approved
nyquist_compliant: true
wave_0_complete: false
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
| TBD | TBD | TBD | QSTN-01 | — | Config exposes 52 questions across 6 categories | unit | `pytest tests/services/test_dssc_config.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | QSTN-03 | — | Config-driven labels — editing JSON changes served content, no code branches on content | unit | `pytest tests/services/test_dssc_config.py::test_config_is_pure_data_no_hardcoded_labels -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | QSTN-04 | T-13-01 (cross-assessment access) | `GET /questionnaire/config` returns identical config regardless of participant_type; ownership check preserved when re-keyed to assessment_id | integration | `pytest tests/api/test_questionnaire.py::test_config_endpoint_universal -x` | ❌ W0 (file doesn't exist) | ⬜ pending |
| TBD | TBD | TBD | QSTN-05 | — | Placeholder content stubs all 52 questions (structural check) | unit | `pytest tests/services/test_dssc_config.py::test_all_52_questions_present -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | MIGR-01 | — | Pre-migration v1.0 data intact, queryable, read-only in archive table after upgrade | integration (migration) | `pytest tests/migrations/test_v1_archive_migration.py -x` | ❌ W0 — new `tests/migrations/` category | ⬜ pending |
| TBD | TBD | TBD | MIGR-02 | — | Evidence subsystem fully absent (no table, no route, no frontend file, no import) | integration + static check | `pytest tests/api/test_evidence_removed.py -x` + `grep -r EvidenceURL backend/app` returns nothing | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | — (security) | T-13-02 (score out-of-range) | `score` field rejects values outside 1-5 at both Pydantic and DB layers | unit | `pytest tests/schemas/test_questionnaire_schemas.py::test_score_range_validation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_dssc_config.py` — covers QSTN-01/03/05 (config shape, 52 questions, 6 categories, per-question label overrides)
- [ ] `tests/api/test_questionnaire.py` — covers QSTN-04 (universal config endpoint, no participant_type branching) — does not currently exist
- [ ] `tests/migrations/test_v1_archive_migration.py` — covers MIGR-01: (1) fresh-DB `alembic upgrade head` via `alembic.command.upgrade(config, "head")` against an empty testcontainer, and (2) a seeded-DB run with pre-migration-shaped rows (raw SQL, since the model will already be redefined) asserting row counts/content land correctly in `questionnaire_answer_v1_archive` and `initiative.schema_version` is tagged — new test category, no `tests/migrations/` dir exists today. Use an isolated container/session scope, not the shared session-scoped `postgres_container`/`engine` fixtures (those already have `create_all()` applied and are not a clean upgrade-path slate).
- [ ] `tests/api/test_evidence_removed.py` — covers MIGR-02 (evidence routes return 404, not 500; no `EvidenceURL` import survives)
- [ ] Update (not create) `tests/factories.py`, `tests/api/test_admin.py`, `tests/api/test_reports.py`, `tests/services/test_report_generator.py` — remove `make_evidence`/`EvidenceURL`/`evidence_by_code` usage so existing Phase-12 tests keep collecting and passing
- [ ] `tests/schemas/test_questionnaire_schemas.py` (or nearest existing schema test file) — covers the security contribution's `score: Field(ge=1, le=5)` validation

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

**Approval:** approved 2026-07-22 (gsd-plan-checker: 0 blockers)
