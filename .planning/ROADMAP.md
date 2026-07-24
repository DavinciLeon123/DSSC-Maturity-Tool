# Roadmap: MAMI Compliance Checker → DSSC Maturity Scan for Dataspaces

## Milestones

- ✅ **v1.0 MAMI Compliance Checker** - Phases 1-11 (shipped 2026-03-15)
- 📋 **v2.0 DSSC Maturity Scan for Dataspaces** - Phases 12-18 (planned)

## Overview

v2.0 retrofits the shipped MAMI Compliance Checker into a DSSC Maturity Scan: the 27-question/4x3 MAMI questionnaire and GoRules/MoSCoW scoring are replaced end-to-end by a 52-question/6-category equal-weight maturity assessment, a frozen report data contract driving dual radar-chart + priority-list rendering (in-app and PDF), versioned retake history, save-reliability hardening, security hardening, and characterization + new-logic test coverage. The build order is a strict dependency chain: stabilize what already works, replace the config schema and data model, replace the scoring engine, rebuild the questionnaire-taking subsystem, freeze the report contract and build its consumers, then test the new logic and harden security last.

**Note on Phase 12 and this repo's pre-existing test/CI infrastructure:** this repo (forked from MAMI Compliance Checker on 2026-07-20) had already independently added a 5-workflow CI/CD pipeline and a starter test suite (health check, privacy canary, scoring perf/benchmark) before this milestone's Phase 12 was planned. Phase 12 was originally planned and executed against a checkout of the same codebase in a different repository, then relocated here and merged additively into the pre-existing conftest.py/pyproject.toml/CI workflows — see `.planning/phases/12-test-retrofit-stabilize-existing-flows/12-RELOCATION-NOTE.md`.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)
- Continuous across milestones — v2.0 continues from v1.0's last phase (11), starting at 12

<details>
<summary>✅ v1.0 MAMI Compliance Checker (Phases 1-11) - SHIPPED 2026-03-15</summary>

Full archive: [`.planning/milestones/v1.0-ROADMAP.md`](.planning/milestones/v1.0-ROADMAP.md)
Requirements: [`.planning/milestones/v1.0-REQUIREMENTS.md`](.planning/milestones/v1.0-REQUIREMENTS.md)

35/40 v1 requirements shipped. 5 deferred (EVID-02–05, ADMN-04) — superseded by v2.0 scope per PROJECT.md.

</details>

- [x] **Phase 12: Test Retrofit — Stabilize Existing Flows** - Regression safety net for auth, admin, and PDF/email delivery, in place before the rebuild touches anything (Complete 2026-07-22)
- [x] **Phase 13: New Questionnaire Config Schema & Data Model Migration** - 52-question/6-category universal config plus a hand-reviewed migration that preserves v1.0 data (Complete 2026-07-23)
- [ ] **Phase 14: Scoring Engine Replacement** - Equal-weight sum/n scoring replaces GoRules ZEN Engine and MoSCoW entirely
- [ ] **Phase 15: Questionnaire Submission API, Wizard UI & Save Reliability** - Rebuilt wizard with reliable autosave and versioned retake history
- [ ] **Phase 16: Report Data Contract, Dual Visualization & Admin Aggregation** - One frozen report contract powering radar chart + priority list in-app, in PDF, and in the admin aggregate view
- [ ] **Phase 17: Test Coverage — New Scoring, Questionnaire & Visualization Logic + E2E** - Automated coverage for the rebuilt subsystems, plus a critical-path Playwright suite
- [ ] **Phase 18: Security Hardening & Password Reset Review** - httpOnly-cookie auth + CSRF, ID-enumeration fix, explicit error handling, admin audit log, password-reset verification

## Phase Details

### Phase 12: Test Retrofit — Stabilize Existing Flows

**Goal**: The subsystems this milestone does NOT rebuild (auth, admin management, PDF/email report delivery) are protected by automated regression tests before the questionnaire/scoring rebuild begins, so breakage introduced by later phases is caught immediately rather than discovered in production.
**Depends on**: Nothing (first phase of this milestone)
**Requirements**: None (foundational safety-net phase — no v1 requirement names this directly; it exists to protect delivery of Phases 13-18, per research/SUMMARY.md's build-order guidance)
**Success Criteria** (what must be TRUE):

  1. Auth flows (registration, login, account lockout, password reset) are covered by automated tests that fail if their behavior changes.
  2. Admin user/initiative management (including cascade-delete) and CSV export are covered by automated tests using current production-shaped data.
  3. PDF generation and email delivery of a completed report are covered by an automated regression test.
  4. This suite runs quickly enough to execute before merging each subsequent phase's changes, giving a clear pass/fail signal throughout the rebuild.

**Plans**: 5/5 plans executed (originally against a MaMi-Compliance-Checker checkout; merged here into this repo's existing test/CI infrastructure via `feature/test-retrofit-auth-admin-reports`, PR #1, merged 2026-07-22)
**Status**: Complete — CI confirmed all 41 backend tests + frontend-test green on both the PR run and the post-merge `staging` run (~3 min total workflow wall-clock)

**Wave 1**

- [x] 12-01-PLAN.md — Backend test infrastructure: testcontainers Postgres, lifespan-aware TestClient, factories, pytest config (Wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 12-02-PLAN.md — Auth regression tests: register/login/lockout/password-reset (Wave 2)
- [x] 12-03-PLAN.md — Admin regression tests: access control, cascade-delete, CSV export, heatmap (Wave 2)
- [x] 12-04-PLAN.md — PDF/email report regression tests + report_generator unit tests (Wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 12-05-PLAN.md — GitHub Actions CI + frontend Vitest wiring (Wave 3; superseded locally by merging into this repo's existing 5-workflow pipeline instead of adding a redundant `test.yml`)

### Phase 13: New Questionnaire Config Schema & Data Model Migration

**Goal**: The system is driven by a new 52-question/6-category universal questionnaire config, and the database plus all existing v1.0 data have been migrated to support it without data loss.
**Depends on**: Phase 12
**Requirements**: QSTN-01, QSTN-03, QSTN-04, QSTN-05, MIGR-01, MIGR-02
**Success Criteria** (what must be TRUE):

  1. A single config file defines 52 questions across 6 categories, each with 5 custom-labeled answer options mapped to a 1-5 score — placeholder/dummy content is sufficient to validate the schema, and swapping in the real content later (QSTN-05, pending from the user) requires no schema or engine change.
  2. Editing question text, category names, or answer-option labels requires only a config edit — no code deploy.
  3. The questionnaire is presented identically to every user — no DSI/Service-Provider (or other) participant-type split remains in the schema, models, or routing.
  4. All pre-migration v1.0 MAMI initiative and answer data remains intact and queryable read-only after the migration runs.
  5. The evidence/URL-per-question subsystem (tables, endpoints, UI) no longer exists anywhere in the codebase.

**Plans**: 4/4 plans executed

Plans:
**Wave 1**

- [x] 13-01-PLAN.md — New universal 52-question/6-category config + single-file loader + universal config endpoint (Wave 1; QSTN-01/03/04/05)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 13-02-PLAN.md — Remove evidence/URL subsystem entirely; strip evidence plumbing, keep suite green (Wave 2; MIGR-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 13-03-PLAN.md — New Assessment + v1 archive models, reshaped 1-5-score answer, schema_version, nullable participant_type, assessment-first upsert (Wave 3; QSTN-01, MIGR-01)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 13-04-PLAN.md — Hand-written archive-split Alembic migration + BLOCKING migration-verification test + openapi regen (Wave 4; MIGR-01)

### Phase 14: Scoring Engine Replacement

**Goal**: Maturity scores are computed via simple equal-weight averaging per dimension, with GoRules ZEN Engine and MoSCoW findings completely removed.
**Depends on**: Phase 13
**Requirements**: SCOR-01, SCOR-02, SCOR-03, SCOR-04
**Success Criteria** (what must be TRUE):

  1. Each dimension's score is computed as sum(answers in that dimension) / number of questions in that dimension, shown as a value between 1.0 and 5.0.
  2. No question or category carries more weight than another anywhere in the scoring logic or config.
  3. GoRules ZEN Engine, its rule configs, and MoSCoW-based findings no longer exist anywhere in the codebase or dependency manifest.
  4. A user only sees computed dimension scores/report after every question has been answered — no partial or live scoring is shown mid-questionnaire.

**Plans**: 2/4 plans executed

Plans:
**Wave 1**

- [x] 14-01-PLAN.md — New dimension-scoring service (equal-weight sum/n) + completion gate + unit tests (Wave 1; SCOR-01, SCOR-02, SCOR-04)

**Wave 2** *(blocked on Wave 1; the two plans run in parallel — disjoint files)*

- [x] 14-02-PLAN.md — Repurpose POST /score to per-dimension shape + 422 completion gate + new test_scoring.py (Wave 2; SCOR-04)
- [ ] 14-03-PLAN.md — Adapt report endpoints (dimension_scores field, 422 gate, banner/matrix-builder deletion) + admin /heatmap degrade + tests (Wave 2; SCOR-04)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 14-04-PLAN.md — Delete zen-engine package/config/wiring + legacy tests + static removal test + openapi regen (Wave 3; SCOR-03)

### Phase 15: Questionnaire Submission API, Wizard UI & Save Reliability

**Goal**: A user can take the full 52-question questionnaire through a rebuilt wizard whose answers save reliably in the background, and every full completion creates a new, permanently preserved assessment version the user can return to.
**Depends on**: Phase 13
**Requirements**: QSTN-02, SAVE-01, SAVE-02, SAVE-03, SAVE-04, HIST-01, HIST-02
**Success Criteria** (what must be TRUE):

  1. Each question presents its 5 answer options as a horizontal line of radio circles (config-driven labels), each mapped to a 1-5 score.
  2. Answers auto-save in the background within a few seconds of being selected (debounced), without requiring Next/Back navigation, and save-request rate limiting is keyed per authenticated user so it never blocks a user's own legitimate activity.
  3. If an autosave fails, the user sees a clear, visible error with a retry action — never a silent lost save.
  4. Closing the tab or hard-refreshing mid-questionnaire does not lose previously-saved answers when the user returns to resume.
  5. Retaking the questionnaire creates a new, dated assessment version rather than overwriting the previous one, and the user can view and compare maturity scores across their past versions.

**Plans**: TBD
**UI hint**: yes

### Phase 16: Report Data Contract, Dual Visualization & Admin Aggregation

**Goal**: Completed assessments produce one frozen report data contract that powers a radar chart and a sorted priority list identically in-app and in the mailed PDF, and the admin view aggregates this same 6-dimension data across initiatives.
**Depends on**: Phase 14, Phase 15
**Requirements**: RPRT-01, RPRT-02, RPRT-03, RPRT-04, ADMN-01
**Success Criteria** (what must be TRUE):

  1. On completing the questionnaire, the user sees a radar/spider chart showing all 6 dimension scores at a glance.
  2. The same report shows a sorted priority list (lowest-to-highest maturity) with dimension name, average score, and a red/orange/green color indicator.
  3. The color-band thresholds (1.0-2.0 / 2.0-3.5 / 3.5-5.0) are defined in exactly one place in config and produce identical banding in both the chart and the priority list.
  4. The user can view this report in-app and receive the same report as a mailed PDF, both rendered from one shared JSON data contract rather than two independently computed views.
  5. An admin can view an aggregated radar/priority view across initiatives using the new 6-category model, replacing the old 4x3 topic heatmap.

**Plans**: TBD
**UI hint**: yes

### Phase 17: Test Coverage — New Scoring, Questionnaire & Visualization Logic + E2E

**Goal**: The rebuilt scoring engine, questionnaire API, wizard, and report rendering have automated test coverage, and a Playwright suite verifies the critical end-to-end path.
**Depends on**: Phase 14, Phase 15, Phase 16
**Requirements**: TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):

  1. Backend pytest coverage exists for the scoring engine (including zero/partial-answer edge cases), the questionnaire submission API, and auth flows.
  2. Frontend Vitest + React Testing Library coverage exists for the wizard's save/state logic and the report's rendering (radar chart + priority list).
  3. A Playwright E2E suite runs the critical path — register, answer the full questionnaire, submit, view the report — and passes in CI.

**Plans**: TBD

### Phase 18: Security Hardening & Password Reset Review

**Goal**: The application's auth-token storage, ID exposure, error handling, and admin auditability are hardened to production-security standards, and the existing password-reset flow is verified sound.
**Depends on**: Phase 12, Phase 16
**Requirements**: SECU-01, SECU-02, SECU-03, SECU-04, AUTH-01
**Success Criteria** (what must be TRUE):

  1. The JWT auth token is stored in an httpOnly cookie (not localStorage), with CSRF protection and CORS credentials configured together, and login plus PDF/CSV download paths keep working under the new model.
  2. Initiative and user records can no longer be enumerated by guessing sequential IDs.
  3. Flagged bare-except blocks (per `.planning/codebase/CONCERNS.md`) are replaced with explicit, logged error handling.
  4. Admin actions (user/initiative management, exports) are recorded in a structured, queryable audit log.
  5. The self-service password-reset flow has been reviewed end-to-end, with any hardening gaps fixed (or confirmed already sound).

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 12 → 13 → 14 → 15 → 16 → 17 → 18

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-11. MAMI Compliance Checker | v1.0 | - | Complete | 2026-03-15 |
| 12. Test Retrofit — Stabilize Existing Flows | v2.0 | 5/5 | Complete | 2026-07-22 |
| 13. New Questionnaire Config Schema & Data Model Migration | v2.0 | 4/4 | Complete    | 2026-07-23 |
| 14. Scoring Engine Replacement | v2.0 | 2/4 | In Progress|  |
| 15. Questionnaire Submission API, Wizard UI & Save Reliability | v2.0 | 0/TBD | Not started | - |
| 16. Report Data Contract, Dual Visualization & Admin Aggregation | v2.0 | 0/TBD | Not started | - |
| 17. Test Coverage — New Logic + E2E | v2.0 | 0/TBD | Not started | - |
| 18. Security Hardening & Password Reset Review | v2.0 | 0/TBD | Not started | - |
