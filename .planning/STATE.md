---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: DSSC Maturity Scan for Dataspaces
status: active
stopped_at: Completed 13-01-PLAN.md
last_updated: "2026-07-23T06:57:49.462Z"
progress:
  total_phases: 2
  completed_phases: 1
  total_plans: 9
  completed_plans: 6
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-22)

**Core value:** A dataspace initiative leader can complete the DSSC Maturity Scan and immediately see which of the 6 maturity dimensions need attention, via a clear score, priority ranking, and visual report.
**Current focus:** Phase 13 — new-questionnaire-config-schema-data-model-migration

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

**Active phase:** 13-new-questionnaire-config-schema-data-model-migration — Plan 13-01 COMPLETE, 13-02 next (wave 2 of 4, sequential)
**Next phase:** 14-scoring-engine-replacement — blocked on Phase 13

Last session (2026-07-22): Relocated Phase 12 + v2.0 milestone docs from `MaMi-Compliance-Checker` to this repo; merged test infra (conftest.py, pyproject.toml, backend/tests/api+services, frontend Vitest) additively into this repo's pre-existing CI/test setup; fixed a WeasyPrint native-library gap in all 4 pytest-running CI workflows; opened PR #1 into `staging`, merged after CI confirmed all 41 backend tests + frontend-test green (PR Checks run 29923476874, post-merge Staging CI/CD run 29923588482). Phase 12 marked complete. User also disabled the 2-approval requirement on `main`'s branch protection (was blocking solo-maintainer merges — see CLAUDE.md).

Prior session (2026-07-22): Planned Phase 13 (New Questionnaire Config Schema & Data Model Migration). Researched migration mechanics, pattern-mapped the codebase, and produced 4 plans across 4 strictly sequential waves (13-01 config/loader → 13-02 evidence removal → 13-03 data model reshape → 13-04 Alembic migration + verification). Plan-checker passed with 0 blockers. Planner agent hit 2 transient API connection errors mid-run and was resumed via SendMessage rather than restarted from scratch — final output verified consistent across the resumed session. UI safety gate false-positive-fired (RESEARCH.md mentions deleting 2 frontend files) and was overridden — confirmed by plan-checker as a pure orphan-file deletion, no hidden UI work.

This session (2026-07-23): Executed Plan 13-01 (universal questionnaire config schema). Authored `config/dssc-questionnaire.json` (52 questions/6 categories, shared default_options + one override), added `load_dssc_questionnaire_config()`/`get_dssc_questionnaire_config()`/lifespan cache, and rewired `GET /questionnaire/config` to serve the universal config with no participant_type branch and no Initiative-existence gate (assumption A1 decision). Added 4 new tests (all pass); regenerated `docs/api/openapi.json` for the docs-freshness CI gate. One pre-existing, unrelated local-env gap (WeasyPrint native library missing on this Mac, not caused by this plan) logged in `deferred-items.md` rather than fixed. QSTN-01/03/04/05 marked complete. Ready to execute 13-02 (evidence subsystem removal).

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

**Last session:** 2026-07-23T06:57:49.458Z
**Stopped at:** Completed 13-01-PLAN.md
**Resume file:** None

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 13 P01 | 25min | 3 tasks | 9 files |

## Decisions

- [Phase 13-01]: Dropped participant_type-driven 404-if-no-Initiative gate on GET /questionnaire/config per assumption A1 — the universal config needs no Initiative to resolve
- [Phase 13-01]: Kept old MAMI/ZEN config loaders (load_questionnaire_config/load_questionnaire_configs) untouched — additive change per the Phase 14 boundary
