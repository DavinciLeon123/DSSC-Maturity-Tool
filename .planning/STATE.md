---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: DSSC Maturity Scan for Dataspaces
status: active
stopped_at: Completed 14-04-PLAN.md
last_updated: "2026-07-24T09:22:11.319Z"
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 13
  completed_plans: 13
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-22)

**Core value:** A dataspace initiative leader can complete the DSSC Maturity Scan and immediately see which of the 6 maturity dimensions need attention, via a clear score, priority ranking, and visual report.
**Current focus:** Phase 14 — scoring-engine-replacement

## Milestone Status

**v1.0 — COMPLETE** (archived 2026-03-15, as MAMI Compliance Checker)

- Archive: `.planning/milestones/v1.0-ROADMAP.md`
- Requirements: `.planning/milestones/v1.0-REQUIREMENTS.md`
- Git tag: `v1.0`
- 35/40 v1 requirements shipped. 5 deferred to future release (EVID-02–05, ADMN-04) — superseded by v2.0 scope.

**v2.0 DSSC Maturity Scan for Dataspaces — IN PROGRESS** (started 2026-07-21)

- Requirements: `.planning/REQUIREMENTS.md` (30 v1 requirements, Phases 13-18)
- Phase 12 (test retrofit) originally planned/executed against a `MaMi-Compliance-Checker` checkout, then relocated to this repo — see `.planning/phases/12-test-retrofit-stabilize-existing-flows/12-RELOCATION-NOTE.md`.
- Note: this repo independently added a 5-workflow CI/CD pipeline + starter test suite (health/privacy-canary/scoring-perf/benchmark) between its 2026-07-20 fork and this milestone landing here — Phase 12's test infra was merged additively into that, not created from scratch.

## Current Position

**Active phase:** 14-scoring-engine-replacement — 4/4 plans executed, phase complete pending verification
**Next phase:** Verify Phase 14, then Phase 15 (Questionnaire Submission API, Wizard UI & Save Reliability)

This session (2026-07-24): Executed Plan 14-04 (ZEN/MoSCoW subsystem deletion + static regression test + openapi regeneration, SCOR-03 — the final plan in Phase 14). Removed the `zen-engine==0.51.0` dependency via `uv remove zen-engine` (pyproject.toml/uv.lock); deleted `backend/app/services/scoring_engine.py`, `config/scoring/mami-scoring.json`, `config/mami-framework.json` via `git rm`. Trimmed `main.py`'s lifespan (removed `import zen`, `app.state.mami_config`, the `scoring_dir`/`loader`/`app.state.zen_engine = zen.ZenEngine(...)` block — surviving DSSC/legacy questionnaire config loads untouched), `deps.py` (removed `get_zen_engine`/`get_mami_config` — `get_dssc_questionnaire_config` untouched), and `mami_config.py` (removed `load_mami_config`/`get_scoring_dir` — `load_dssc_questionnaire_config`/`load_questionnaire_config`/`load_questionnaire_configs` untouched); reworded `Dockerfile`'s stale zen-engine comment without touching the base image. Deleted `tests/benchmark/test_scoring_regression.py`/`tests/perf/test_scoring_perf.py` and their only fixture consumers (`mami_codes`/`make_answers` in `conftest.py`); `test_health.py` now asserts `app.state.dssc_questionnaire_config` instead of the removed `mami_config`/`zen_engine`; logged the Phase 17 (TEST-01) perf/benchmark replacement deferral in `deferred-items.md` (D-08). Added `backend/tests/test_zen_removed.py` — a new static regression test mirroring Phase 13's `test_evidence_removed.py` substring-scan + AST-walk pattern (search tokens built from parts, scan scoped to `backend/app`/`config` only, never `backend/tests`), locking SCOR-03 in place. Regenerated `docs/api/openapi.json`, capturing `ScoreResponse`/`DimensionScore` (14-02), `/report/data`'s `dimension_scores` (14-03), and the simplified `AdminHeatmapResponse` (`FindingRead`/`matrix`/`topic_structure` components gone); confirmed diff-clean on a second export run (docs-freshness gate). App imports cleanly, ruff/mypy/format clean, full staging-onward suite (`pytest tests/ -n auto -m "not perf"`) 91/95 passing (same 4 pre-existing local-only WeasyPrint failures recurring from every prior Phase 13/14 plan touching `reports.py`, unrelated). SCOR-03 marked complete. **Phase 14 is now fully executed (4/4 plans)** — awaiting the verification step before Phase 15 begins.

Prior session (2026-07-24): Executed Plan 14-03 (report endpoints + admin heatmap adaptation, SCOR-04). Trimmed `backend/app/services/report_generator.py` from 313 to 22 lines — deleted `_build_matrix`/`_build_topic_structure`/`_build_heatmap_rows`/`_build_not_yet_recommendations`/`_build_findings_detail`/`_aggregate_cell`/`_suggest_next_steps`/`_RECOMMENDATIONS`/`_ANSWER_LABEL_MAP` outright (D-01a); `generate_report_data(initiative)` now returns `{"initiative": {...}}` only, `generate_html_report(initiative, generated_at)` renders the unchanged `report.html` with literal `heatmap_rows={}`/`not_yet_recommendations=[]` (D-05, Pitfall 1). Rewrote `backend/app/api/v1/reports.py`: removed `import zen`/`score_all_answers`/`get_mami_config`/`get_zen_engine` and the entire degraded-banner mechanism (`_DEGRADED_SCORING_BANNER_HTML`/`_inject_degraded_banner`/`_degraded_scoring_inputs`, D-05a); all four routes (`/report`, `/report/data` GET+POST, `/report/pdf`, `/report/mail`) now call `assert_assessment_complete` immediately after the ownership check (T-14-01 ordering, SCOR-04); both `/report/data` handlers add `dimension_scores` via `compute_dimension_scores` (D-05); dropped async/await (mirrors Plan 14-02). Rewrote `backend/app/api/v1/admin.py`'s `/heatmap`: removed the orphaned `_build_topic_structure` import, reduced `AdminHeatmapResponse`/`get_admin_heatmap` to a fixed `{degraded: true, cells: []}` response (D-01b). Rewrote all three affected test files (`test_report_generator.py`, `test_reports.py` — rebuilt fixtures to fully answer the real 52-question config since the old n=5 partial-answers fixture now fails the SCOR-04 gate, `test_admin.py`) against the new shapes, plus new dimension_scores/422/ownership-ordering tests. App imports cleanly, ruff/mypy/format clean, full quick suite 87/91 (same 4 pre-existing local-only WeasyPrint failures recurring from Phase 13, unrelated — logged in a new phase-14 `deferred-items.md`). Did NOT regenerate `docs/api/openapi.json` per this plan's explicit prohibition (Plan 14-04 owns it once, after all Wave 2/3 response-model changes land). Ready to execute 14-04 (ZEN/MoSCoW removal + openapi regeneration, the final plan in Phase 14).

Prior session (2026-07-24): Executed Plan 14-02 (scoring endpoint adaptation, D-04/SCOR-04). Rewrote `backend/app/api/v1/scoring.py`: removed `import zen`, `get_mami_config`/`get_zen_engine` deps, `score_all_answers`, `FindingRead`, and all findings/critical-count aggregation; added `ScoreResponse {initiative_id, dimension_scores}`/`DimensionScore {category_id, name, score}` models and a `get_dssc_questionnaire_config` dependency. Route now calls `assert_assessment_complete` (Plan 14-01's new 422 completion gate, SCOR-04 — replaces the prior HTTP 200 all-zeros behavior) then `compute_dimension_scores`, immediately after preserving the existing ownership check (404/403) as the first gate (T-14-01 ordering). Added `backend/tests/api/test_scoring.py` — this endpoint's first-ever automated coverage (4 tests: happy-path/6-dimension-scores, 422-incomplete, 422-no-assessment, ownership-before-completion-gate matching `-k ownership`). App imports cleanly, ruff/mypy/format clean, full quick suite 80/84 (same 4 pre-existing local-only WeasyPrint failures, unrelated). Did NOT regenerate `docs/api/openapi.json` per this plan's explicit prohibition (Plan 14-04 owns it, once, after all Wave 2/3 response-model changes land). SCOR-04 marked complete. Ready to execute 14-03 (reports.py/report_generator.py/admin.py adaptation, runs in parallel with this plan's Wave 2 — disjoint files).

Prior session (2026-07-24): Executed Plan 14-01 (dimension-scoring service + completion gate, SCOR-01/02/04). Created `backend/app/services/dimension_scoring.py` (`compute_dimension_scores`, `assert_assessment_complete`, `get_current_assessment`, plus config-comprehension helpers), purely additive — no existing file modified. Added `backend/tests/services/test_dimension_scoring.py` (7 unit tests against the real-Postgres `session` fixture, driven from the real `config/dssc-questionnaire.json`, no hardcoded question ids), covering SCOR-01 (equal-weight average, 1.0/5.0 boundary, 2dp rounding precision), SCOR-02 (9-question vs 8-question categories average identically, proving no cross-category weighting), and SCOR-04 (422 on incomplete/no-draft-assessment, successful gate returns the Assessment). App imports cleanly, ruff/mypy/format clean, `docs/api/openapi.json` regenerated with zero diff (no schema changed). 76/80 backend tests pass (same 4 pre-existing local-only WeasyPrint failures as every prior Phase 13 plan, unrelated). SCOR-01/02/04 marked complete. Ready to execute 14-02 (adapt `scoring.py`'s `/score` endpoint to call the new service, D-04).

Prior session (2026-07-22): Relocated Phase 12 + v2.0 milestone docs from `MaMi-Compliance-Checker` to this repo; merged test infra (conftest.py, pyproject.toml, backend/tests/api+services, frontend Vitest) additively into this repo's pre-existing CI/test setup; fixed a WeasyPrint native-library gap in all 4 pytest-running CI workflows; opened PR #1 into `staging`, merged after CI confirmed all 41 backend tests + frontend-test green (PR Checks run 29923476874, post-merge Staging CI/CD run 29923588482). Phase 12 marked complete. User also disabled the 2-approval requirement on `main`'s branch protection (was blocking solo-maintainer merges — see CLAUDE.md).

Prior session (2026-07-22): Planned Phase 13 (New Questionnaire Config Schema & Data Model Migration). Researched migration mechanics, pattern-mapped the codebase, and produced 4 plans across 4 strictly sequential waves (13-01 config/loader → 13-02 evidence removal → 13-03 data model reshape → 13-04 Alembic migration + verification). Plan-checker passed with 0 blockers. Planner agent hit 2 transient API connection errors mid-run and was resumed via SendMessage rather than restarted from scratch — final output verified consistent across the resumed session. UI safety gate false-positive-fired (RESEARCH.md mentions deleting 2 frontend files) and was overridden — confirmed by plan-checker as a pure orphan-file deletion, no hidden UI work.

Prior session (2026-07-23): Executed Plan 13-01 (universal questionnaire config schema). Authored `config/dssc-questionnaire.json` (52 questions/6 categories, shared default_options + one override), added `load_dssc_questionnaire_config()`/`get_dssc_questionnaire_config()`/lifespan cache, and rewired `GET /questionnaire/config` to serve the universal config with no participant_type branch and no Initiative-existence gate (assumption A1 decision). Added 4 new tests (all pass); regenerated `docs/api/openapi.json` for the docs-freshness CI gate. One pre-existing, unrelated local-env gap (WeasyPrint native library missing on this Mac, not caused by this plan) logged in `deferred-items.md` rather than fixed. QSTN-01/03/04/05 marked complete.

Prior session (2026-07-23): Executed Plan 13-02 (evidence subsystem removal, MIGR-02). Deleted `backend/app/models/evidence.py`, `backend/app/schemas/evidence.py`, `backend/app/api/v1/evidence.py`, and both frontend files (`lib/evidence.ts`, `EvidenceInput.tsx`) outright per D-11 — no archive step. Stripped all `EvidenceURL` imports/usages from `admin.py` (cascade-delete), `reports.py` (5 call sites), and `report_generator.py` (dropped the `evidence_by_code` parameter from 3 functions), plus updated `tests/factories.py`/`test_admin.py`/`test_report_generator.py` to match. Added `test_evidence_removed.py` (route-404 + static-absence via substring scan + AST walk, class name built from parts to avoid self-matching). App imports cleanly, ruff/mypy clean, frontend tsc/eslint clean, 44/48 backend tests pass (same 4 pre-existing local WeasyPrint failures as 13-01, unrelated). Fixed one stale doc reference (`tests/README.md` still named the deleted model) and regenerated `docs/api/openapi.json` for docs-freshness. MIGR-02 marked complete. Ready to execute 13-03 (Assessment/answer-model reshape).

Prior session (2026-07-23): Executed Plan 13-03 (Assessment entity, answer reshape, D-01/D-02/D-03/D-06/D-07/D-12). Added `backend/app/models/assessment.py` (`Assessment`/`AssessmentStatus`, draft/submitted lifecycle) and `backend/app/models/questionnaire_answer_archive.py` (`QuestionnaireAnswerV1Archive`, no FK to initiative, explicit String `answer_value`). Reshaped `QuestionnaireAnswer` to `assessment_id`/`category_id`/`score` (1-5), removing `mami_code`/`initiative_id`/the 3-way enum entirely; renamed unique constraint to `uq_answer_per_question_v2`. Added `Initiative.schema_version` (default "v2") and made `participant_type` nullable on `Initiative`/`User`, fixing Pydantic/admin-row fallout (`InitiativeRead`, `UserRead`, `AdminUserRow`, `AdminInitiativeRow`). Extended the PUT/GET answer endpoints to an assessment-first flow (lazy draft `Assessment` creation, ownership re-derived through `Assessment.initiative_id -> Initiative.user_id`, security V4). Adapted `admin.py`/`reports.py` and, as a Rule 1 auto-fix not in the plan's file list, `scoring.py` (all three would otherwise raise `AttributeError` against the reshaped model) to degrade to zero findings/an all-zero heatmap for new-schema initiatives rather than crashing — documented inline as a known Phase 13->14 interim gap (RESEARCH Pitfall 3/Assumption A3), not a real "compliant" signal. Added 21 new tests (`tests/schemas/test_questionnaire_schemas.py`, `tests/api/test_questionnaire_answers.py`); updated `tests/factories.py`/`test_admin.py`/`test_reports.py` for the new shape. App imports cleanly, ruff/mypy/format all clean, 65/69 backend tests pass (same 4 pre-existing local WeasyPrint failures as 13-01/13-02, unrelated, now recurring a third time — logged in `deferred-items.md`). Regenerated `docs/api/openapi.json`. QSTN-01 re-confirmed complete; MIGR-01 deliberately NOT marked complete — the actual v1.0 data migration is 13-04's job. Ready to execute 13-04 (Alembic migration + verification, the final plan in this phase).

This session (2026-07-23): Executed Plan 13-04 (hand-written archive-table-split Alembic migration + BLOCKING migration-verification test, MIGR-01 — the final plan in Phase 13). Wrote `backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py`, chained from head `h8c6d5e4f3a2`: creates `assessment`, creates `questionnaire_answer_v1_archive` (old shape, explicit `sa.String()` for `answer_value` — never a native Postgres ENUM, RESEARCH Pitfall 1; deliberately no FK to `initiative.id`, D-01/A2), copies every existing `questionnaire_answer` row into the archive verbatim, adds `initiative.schema_version` and tags initiatives with archived answers `'v1_legacy'` (leaving answerless initiatives at `'v2'`), makes `participant_type` nullable on `initiative`/`user` (D-12), then drops and recreates `questionnaire_answer` with the new `assessment_id`/`category_id`/`score` shape plus a DB-level `CHECK(score BETWEEN 1 AND 5)` (security V5). `downgrade()` reverses every step in dependency-safe order, documented as lossy for new-shape answers written after upgrade (same precedent as `f6a4b3c2d1e9`). Added `backend/tests/migrations/` — the first migration-verification test category in this repo, using isolated per-test `PostgresContainer` fixtures (not the shared session-scoped `postgres_container`/`engine`) to run `alembic.command.upgrade`/`downgrade` programmatically against the real upgrade path (RESEARCH Pitfall 2, previously zero coverage since `conftest.py` only ever used `SQLModel.metadata.create_all()`). Three tests all pass: empty-DB upgrade creates the new tables/shape; seeded-DB upgrade preserves archive row count/content/linkage exactly and tags legacy initiatives correctly (including the answerless-initiative-stays-'v2' edge); upgrade/downgrade/upgrade round-trip succeeds against seeded data. `docs/api/openapi.json` regenerated with zero diff (no Pydantic schema changed this plan). Full quality gate green: ruff/mypy clean, 68/72 backend tests pass (same 4 pre-existing local WeasyPrint failures, unrelated, recurring a fourth time — logged in `deferred-items.md`). MIGR-01 marked complete. **Phase 13 is now fully complete (4/4 plans)** — Phase 14 (scoring engine replacement) is unblocked.

## Accumulated Context

### Tech Stack

- Backend: Python/FastAPI + SQLModel + PostgreSQL + GoRules ZEN Engine + WeasyPrint + Resend SDK
- Frontend: React/Vite + TanStack Router + antd v6
- Deployment: Railway (Docker Compose), staging + production
- Auth: JWT (24h), bcrypt, localStorage key `mami_access_token`
- Testing (this repo, added 2026-07-20 to 2026-07-22): backend — ruff/mypy/pytest-xdist/pytest-benchmark/pip-audit + testcontainers[postgres]/faker/pytest-asyncio/pytest-mock/pytest-cov (Phase 12); frontend — Vitest + Testing Library (Phase 12, net new)
- CI/CD: 5 GitHub Actions workflows (pr/staging/main/release/security), branch model `feature/*` → `staging` (protected) → `main` (protected, PR + CI only — 2-approval rule dropped 2026-07-22, see below) → tag release

### Key Decisions

- [Phase 12, complete]: PR #1 merged 2026-07-22 — all 41 backend tests + frontend-test confirmed green in CI (PR Checks + post-merge Staging CI/CD), resolving the only open gap (G-12-1, WeasyPrint system-library fix)
- [2026-07-22]: Dropped `main`'s 2-approval branch protection rule (the "4-eye principle") at the repo owner's request — this repo has one collaborator, and the rule was blocking the owner's own merges (flagged as an expected friction point in CLAUDE.md's original setup notes). `main` now requires PR + CI only, same gate as `staging`.
- [Phase 12, this PR]: Merged Phase 12's Postgres-testcontainer test infra additively into this repo's pre-existing conftest.py/pyproject.toml rather than overwriting — no fixture-name or dependency collisions existed
- [Phase 12, this PR]: Skipped creating a redundant test_smoke.py — this repo's existing test_health.py already proved the lifespan-aware TestClient chain; enhanced it with the one additional app.state assertion instead
- [Phase 12, this PR]: Added a `frontend-test` job to the existing pr.yml/staging.yml/main.yml/release.yml rather than a new standalone test.yml — this repo had no frontend test job at all before Phase 12
- [Phase 12, this PR]: Discovered and fixed a WeasyPrint native-library gap (libgobject-2.0-0 / Pango) in all 4 CI workflows that run pytest — pre-existing runtime dependency, never exercised by CI before test_reports.py existed
- [Phase 01-02]: LOWER(participant_type) = :ptype — case-insensitive filter avoids DB migration for DSI/SP casing
- [Phase 01-02]: SP tab lazy fetch with spFetched guard — avoids unnecessary API call on heatmap page load
- [Phase 01-02]: antd v6 styles={{ body }} replaces deprecated bodyStyle on Card component
- [Phase 01-01]: Keep initiativeId in state (not local var) — handleMail reads it outside the merged effect
- [Phase 01-01]: useRef pattern for unmount save in WizardPage — avoids stale closure without breaking unmount-only semantics
- [Phase 01-01]: fire-and-forget (void) on unmount save — component is gone, errors cannot be surfaced
- SQLModel requires SQLAlchemy <2.1.0 — pinned explicitly
- bcrypt direct (not passlib), PyJWT (not python-jose)
- JWT sub = user email, 24h expiry, localStorage for persistence
- TanStack Router: _app.tsx flat layout (not _app/_layout.tsx — path conflict)
- routeTree.gen.ts committed to repo (manually updated before tsc build)
- Initiative one-per-user: API 409 + DB unique index
- Docker venv at /opt/venv (not /app/.venv) to avoid volume mount shadowing
- JDM hitPolicy first — rules are mutually exclusive for single-answer evaluation
- Single-answer ZEN evaluation pattern — engine.evaluate() called once per answer
- Config file path resolved via Path(__file__).parent chain
- FastAPI lifespan pattern for all startup singletons stored in app.state
- pg_insert on_conflict_do_update for questionnaire answers — PostgreSQL upsert
- RJSF fully removed (Phase 04-01) — replaced by custom wizard components
- asyncio.gather() for concurrent ZEN evaluation
- Named import { api } pattern for all frontend API libs
- Evidence is simple URL storage (no crawling) — deferred to future release
- Phase 3.1 INSERTED: DSI/SP participant type required after requirements change
- New answer format: YES / NOT_THERE_YET / NOT_APPLICABLE
- Two questionnaire configs: dsi-questionnaire-v2.json and sp-questionnaire-v2.json (v3.0 real questions)
- participant_type stored on User model (set at registration)
- Jinja2 FileSystemLoader from templates/ dir
- Blob URL approach for report viewing — POST returns HTML, frontend creates Blob URL
- Password reset token: secrets.token_urlsafe(32) plain string, one-time use
- [Phase 07]: antd ConfigProvider: colorPrimary #06004f (navy), colorSuccess #399e5a (green), Rubik font
- [Phase 08]: GET /report/data regenerates scoring on-the-fly from stored answers
- [Phase 09]: contact_name/contact_email/organization made Optional in Initiative model
- [Phase 10]: DB pool: pool_size=15, max_overflow=25 (total 40) for 100-user concurrency
- [Phase 11]: WeasyPrint import deferred inside _send_report_email for lazy loading
- [Phase 11]: PDF attachment uses list(pdf_bytes) per Resend Python SDK spec
- [Phase 11]: isoformat() + 'Z' replaces strftime for generated_at — required for Railway/Linux
- [Phase 11]: antd v6 Collapse uses items prop (not Collapse.Panel)
- [Phase 11]: handleMail uses localStorage key 'mami_access_token' + VITE_API_URL

### Roadmap Evolution

- v2.0 milestone "DSSC Maturity Scan for Dataspaces" (Phases 12-18) started 2026-07-21 — relocated to this repo 2026-07-22 after being planned/executed against a `MaMi-Compliance-Checker` checkout by mistake (see 12-RELOCATION-NOTE.md)
- This repo independently added CI/CD (5 workflows) + a starter test suite between its 2026-07-20 fork and the v2.0 milestone landing here — not part of either milestone's planned scope, done in parallel
- Phase 6 added: Demo readiness (admin, password reset, 50-user scalability)
- Phase 7 added: Figma design implementation
- Phase 8 added: Figma design cleanup and compliance report styling
- Phase 9 added: UX improvements, dashboard registration, responsive design, expanded heatmap
- Phase 10 added: Polish, 100-user scalability, admin aggregated heatmap
- Phase 11 added: Recommendations drawer, mail report, invalid date fix, homepage images, mobile portrait fix
- Phase 5 (Admin, Crawling, PDF): never executed — admin delivered in Phase 6, PDF in Phase 11, crawling deferred
- Phase 1 (new cycle) added: Bugfix retake-questionnaire save, CSV missing follow-up selections, separate DSI/SP aggregated heatmaps

### Blockers/Concerns

- coe-dsc.nl deployment specifics: validate with TNO stakeholder
- URL crawling (EVID-02–05) deferred — requires SSRF protection, consent gate, snapshot storage
- Audit logging (ADMN-04) deferred — tied to URL crawling infrastructure

## Session

**Last session:** 2026-07-24T09:12:00.000Z
**Stopped at:** Completed 14-04-PLAN.md
**Resume file:** None

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 13 P01 | 25min | 3 tasks | 9 files |
| Phase 13 P02 | 20min | 3 tasks | 16 files |
| Phase 13 P03 | 35min | 3 tasks | 22 files |
| Phase 13 P04 | 20min | 3 tasks | 3 files |
| Phase 14 P01 | 13min | 2 tasks | 2 files |
| Phase 14 P02 | 17min | 2 tasks | 2 files |
| Phase 14 P03 | 22min | 3 tasks | 6 files |
| Phase 14 P04 | 12min | 3 tasks | 11 files |

## Decisions

- [Phase 13-01]: Dropped participant_type-driven 404-if-no-Initiative gate on GET /questionnaire/config per assumption A1 — the universal config needs no Initiative to resolve
- [Phase 13-01]: Kept old MAMI/ZEN config loaders (load_questionnaire_config/load_questionnaire_configs) untouched — additive change per the Phase 14 boundary
- [Phase 13-02]: Evidence data dropped outright, no archive step, per D-11 — evidence_url table itself is dropped in the 13-04 migration; this plan only removed the application-layer plumbing
- [Phase 13-02]: Dropped the evidence_by_code parameter entirely from report_generator.py's three functions (smaller-diff option) rather than passing {} inline at each call site
- [Phase 13-03]: New Assessment entity + questionnaire_answer_v1_archive model added; QuestionnaireAnswer reshaped to assessment_id/category_id/score (1-5) — mami_code/initiative_id/3-way enum removed from the live table, preserved verbatim in the archive model (D-01/D-02/D-06/D-07)
- [Phase 13-03]: Initiative.schema_version added (default "v2"); participant_type made nullable on Initiative and User (D-12) — Pydantic/admin-row fallout fixed across InitiativeRead/UserRead/AdminUserRow/AdminInitiativeRow
- [Phase 13-03]: scoring.py adapted as a Rule 1 auto-fix (not in the plan's file list) — reshaping QuestionnaireAnswer would have left this live endpoint raising AttributeError at runtime; given the same degrade-to-zero-findings treatment as reports.py
- [Phase 13-03]: No hard 422 guard added for new-schema initiatives hitting report/heatmap/score endpoints (Assumption A3) — degrades to zero findings/all-zero heatmap instead, documented inline as a known Phase 13->14 interim gap
- [Phase 13-03]: MIGR-01 requirement NOT marked complete despite being in this plan's frontmatter — the actual v1.0 data migration/preservation is 13-04's job; only QSTN-01 marked complete this plan
- [Phase 13-03]: Did not change auth.py's /register or initiatives.py's create_initiative to stop writing participant_type from user input — kept out of scope pending a future explicit ask, since it would change the registration API contract beyond this plan's file/task list
- [Phase 13-04]: Hand-wrote the archive-table-split Alembic migration (i9d7e6f5a4b3, chains from h8c6d5e4f3a2) exactly per RESEARCH Pattern 2 — no autogenerate; used the plan's proposed revision id verbatim
- [Phase 13-04]: Added backend/tests/migrations/ — the first migration-verification test category in this repo, using isolated per-test PostgresContainer fixtures (not the shared session-scoped fixture) to prove the real alembic upgrade/downgrade path against seeded pre-migration data
- [Phase 13-04]: MIGR-01 marked complete — Phase 13 fully complete (4/4 plans); Phase 14 unblocked
- [Phase 14-01]: Colocated compute_dimension_scores and assert_assessment_complete in one new dimension_scoring.py service module rather than splitting into two files
- [Phase 14-01]: Reused one identical 422 detail ("Questionnaire not fully answered") for both no-draft-assessment and incomplete-assessment cases (T-14-02 mitigation)
- [Phase 14-02]: Made score_initiative synchronous (dropped async/await) — nothing awaits once the ZEN engine call was removed
- [Phase 14-02]: Added # type: ignore[arg-type] on assessment.id -> compute_dimension_scores, matching existing repo precedent (reports.py:39, admin.py:99/101) for the same SQLModel Optional-PK mypy limitation
- [Phase 14-03]: Dropped async/await from all four report routes — mirrors scoring.py's Plan 14-02 precedent, nothing awaits once score_all_answers is gone
- [Phase 14-03]: Rebuilt test_reports.py's fixtures to fully answer the real 52-question config (mirroring test_scoring.py's pattern) since the old partial-answers fixture now fails the SCOR-04 completion gate with 422
- [Phase 14-04]: Built test_zen_removed.py's search tokens from string-concatenation parts (Phase 13 test_evidence_removed.py precedent) even though the scan never touches backend/tests — extra guard against a future refactor widening scan scope
- [Phase 14-04]: Deliberately excluded a bare "mami_config" substring scan from the static removal test — mami_config.py survives with legitimate load_dssc_questionnaire_config/load_questionnaire_config(s) loaders; only the specific removed symbols are asserted absent
- [Phase 14-04]: SCOR-03 marked complete — Phase 14 fully executed (4/4 plans), awaiting verification before Phase 15
