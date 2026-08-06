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
- [x] **Phase 14: Scoring Engine Replacement** - Equal-weight sum/n scoring replaces GoRules ZEN Engine and MoSCoW entirely (completed 2026-07-24)
- [x] **Phase 15: Questionnaire Submission API, Wizard UI & Save Reliability** - Rebuilt wizard with reliable autosave and versioned retake history (completed 2026-07-26)
- [x] **Phase 16: Report Data Contract, Dual Visualization & Admin Aggregation** - One frozen report contract powering radar chart + priority list in-app, in PDF, and in the admin aggregate view (completed 2026-07-28)
- [x] **Phase 16.1: DSSC Rebrand — Visual Identity, Terminology, PDF Content & Registration Default (INSERTED)** - Replace CoE-DSC colors/logo/wording with DSSC's own across the app and PDF, add submitted answers to the PDF, default new registrations to DSI-only (completed 2026-08-03)
- [x] **Phase 16.2: Content & UX Updates — Frontpage/About Rebrand Copy, Assessment Intro Texts & Question Grouping (INSERTED)** - New DSMA copy for the homepage and About page, a welcome screen before the assessment plus a per-dimension intro text within it, and question grouping into 16 named subsections, all per `Teksten MAMI Tool.pdf` (completed 2026-08-04, pending Railway visual sign-off)
- [x] **Phase 16.3: Bug fixes batch: survey retake, report colors, and PDF (INSERTED)** - Fixed 7 user-reported bugs: retake-save failure, blue questionnaire text, "View Report" showing the wrong survey, PDF initiative label/score-dot clipping/expert-help wording, square button+card corners app-wide, and admin panel completed-assessment counts on both tabs (completed 2026-08-05, Railway visual sign-off confirmed 2026-08-05 — all 7 bugs verified fixed, including the PDF dot-clip render)
- [x] **Phase 16.4: Consent checkbox, 5-tier maturity scale, and report contact CTA (INSERTED)** - Mandatory registration data-consent checkbox (existing test users backfilled as consented), 3-tier -> 5-tier maturity scoring labels (Exploratory/Preparatory/Implementation/Operational/Scaling) everywhere aggregate scoring displays, and a thank-you + mailto:info@dssc.eu contact CTA on the report page (completed 2026-08-05)
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

**Plans**: 4/4 plans executed

Plans:
**Wave 1**

- [x] 14-01-PLAN.md — New dimension-scoring service (equal-weight sum/n) + completion gate + unit tests (Wave 1; SCOR-01, SCOR-02, SCOR-04)

**Wave 2** *(blocked on Wave 1; the two plans run in parallel — disjoint files)*

- [x] 14-02-PLAN.md — Repurpose POST /score to per-dimension shape + 422 completion gate + new test_scoring.py (Wave 2; SCOR-04)
- [x] 14-03-PLAN.md — Adapt report endpoints (dimension_scores field, 422 gate, banner/matrix-builder deletion) + admin /heatmap degrade + tests (Wave 2; SCOR-04)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 14-04-PLAN.md — Delete zen-engine package/config/wiring + legacy tests + static removal test + openapi regen (Wave 3; SCOR-03)

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

**Plans**: 8/8 plans executed

Plans:
**Wave 1** *(backend + frontend plumbing, disjoint file sets — run in parallel)*

- [x] 15-01-PLAN.md — [BLOCKING migration] Assessment version-increment (D-15/HIST-01) + per-user rate-limit key (SAVE-03) + last-viewed-category column/write (D-08) + hand-written Alembic migration ((initiative_id, version) unique constraint + last_viewed_category_id) (Wave 1; HIST-01, SAVE-03, SAVE-04)
- [x] 15-02-PLAN.md — Greenfield GET /initiatives/{id}/assessments history endpoint + AssessmentSummary schema + list_submitted_assessments helper (Wave 1; HIST-02)
- [x] 15-03-PLAN.md — Frontend plumbing rebuild: new questionnaire.ts types + flushAnswerBeacon, useDebouncedSave hook, RadioScale/QuestionCard/StepPills, delete orphaned components (Wave 1; QSTN-02, SAVE-01, SAVE-02)

**Wave 2** *(frontend, depends on Wave 1; two plans run in parallel — disjoint files)*

- [x] 15-04-PLAN.md — WizardPage rebuild: debounced autosave + retry/terminal-block (SAVE-01/02) + beforeunload keepalive flush + resume-at-last-category (SAVE-04/D-08) + category-per-page nav (Wave 2; SAVE-01, SAVE-02, SAVE-04, HIST-01)
- [x] 15-05-PLAN.md — History page (/assessments list + comparison table, HIST-02) + dashboard history link + confirmed retake dialog (D-13/D-17) (Wave 2; HIST-02, HIST-01)

**Gap Closure** *(from 15-VERIFICATION.md — 2 blocking gaps; plans 15-06/15-07 added 2026-07-26; plan 15-08 added 2026-07-26 for the re-verification's new blocking finding)*

- [x] 15-06-PLAN.md — Retake made functional end-to-end: POST /initiatives/{id}/retake resets Initiative.status + creates version-incremented blank draft; dashboard confirm dialog wired; real submit→retake→save e2e test (Gap 1; HIST-01)
- [x] 15-07-PLAN.md — Frozen score history: Assessment.dimension_scores JSONB snapshot column + migration, snapshot at submit, snapshot-preferring history read, zero-division guard, config-drift test, REQUIREMENTS.md traceability fix (Gap 2; HIST-02)
- [x] 15-08-PLAN.md — Submit completeness gate: submit_initiative calls assert_assessment_complete before freezing dimension_scores (422 on incomplete draft, mirroring scoring.py/reports.py); new 422 regression test + fix pre-existing retake test to answer full config (Gap 3; HIST-02, SCOR-04)

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

**Plans**: 5/5 plans executed (4 core + 1 gap-closure)
**Status**: Complete — 16-05 closed both G-16-1/G-16-2 gaps from 16-UAT.md, human-confirmed on a real WeasyPrint render via the Railway Integration deployment

Plans:
**Wave 1**

- [x] 16-01-PLAN.md — Report-contract foundation: maturity_bands config key + get_maturity_band/build_priority_list/generate_radar_svg/build_report_contract + schemas/report.py + unit tests (Wave 1; RPRT-01/02/03)

**Wave 2** *(depends on 16-01; the two plans run in parallel — disjoint files)*

- [x] 16-02-PLAN.md — reports.py rebuilt on the frozen contract: resolve_report_assessment (fix draft-scoped 422 bug), assessment_id per-version viewing, admin bypass, drop ComplianceReport, rebuild report.html + submitted-lifecycle tests (Wave 2; RPRT-04/01/02)
- [x] 16-03-PLAN.md — Admin aggregation: admin_aggregation.py latest-submitted-per-initiative + org-average radar + empty guard, /admin/heatmap rebuilt with real response models + tests (Wave 2; ADMN-01)

**Wave 3** *(depends on 16-02 + 16-03)*

- [x] 16-04-PLAN.md — Frontend consumers: report.tsx radar SVG + priority list (per-version), admin.heatmap.tsx org radar + per-initiative table, reports.ts contract fetch, openapi.json regen (Wave 3; RPRT-01/02/04, ADMN-01)

**Gap Closure** *(from 16-UAT.md — 2 major visual gaps found in human verification; plan 16-05 added 2026-07-28)*

- [x] 16-05-PLAN.md — Report-rendering fixes: position-aware radar axis text-anchor + widened viewBox (G-16-1, clipped labels in browser + PDF) and flattened single-level flex priority-row/legend with fixed-width right-aligned score column (G-16-2, PDF score misalignment + legend wrap) + backend regression tests + human WeasyPrint visual confirmation (RPRT-01/02/04)

**UI hint**: yes

### Phase 16.4: Consent checkbox, 5-tier maturity scale, and report contact CTA (INSERTED)

**Goal:** Ship 3 user-requested changes: (1) registration requires ticking a mandatory data-collection consent checkbox before an account can be created, with existing test users backfilled as consented; (2) the final maturity scoring's 3-tier label system ("Needs Attention"/"Developing"/"Mature") is replaced with a 5-tier scale (Exploratory 1.00-1.49, Preparatory 1.50-2.49, Implementation 2.50-3.49, Operational 3.50-4.49, Scaling 4.50-5.00) everywhere aggregate scoring is displayed; (3) the completed-assessment report page shows a thank-you message with a mailto:info@dssc.eu contact/feedback button.
**Requirements**: TBD (phase-local pseudo-IDs REQ-1/REQ-2/REQ-3 used in plan frontmatter, mapped 1:1 to the 3 changes above — see 16.4-RESEARCH.md's Phase Requirements table)
**Depends on:** Phase 16
**Plans:** 3/3 plans complete

Plans:
**Wave 1** *(3 plans, disjoint files, run in parallel — verified no file overlap: consent touches auth/user/register.tsx; tier scale touches config/report_generator.py/reports.py/report.html/its own test file; CTA touches only report.tsx)*

- [x] 16.4-01-PLAN.md — Consent checkbox: single-step Alembic migration (`data_consent` NOT NULL DEFAULT true) + User model + UserCreate validator (422 on false/missing) + register() wiring + register.tsx required checkbox + openapi regen (Wave 1; REQ-1)
- [x] 16.4-02-PLAN.md — 5-tier maturity scale: new `maturity_tiers` config array + `get_maturity_tier()` + `build_priority_list()`'s band_label re-sourced (band_color/band_id unchanged) + PDF's new separate 5-tier text legend + rewritten `test_maturity_band_same_for_both_callers` (Wave 1; REQ-2)
- [x] 16.4-03-PLAN.md — Report page CTA: thank-you text + mailto:info@dssc.eu Button on report.tsx, in-app only per D-04 (Wave 1; REQ-3)

### Phase 16.3: Bug fixes batch: survey retake, report colors, and PDF (INSERTED)

**Goal:** Fix 7 user-reported bugs: (1) retaking the questionnaire fails to save because the retake isn't registered as a new assessment, (2) questionnaire question/answer text renders blue instead of black, (3) "View Report" always shows/downloads the newest survey instead of the one the user selected, (4) PDF report is missing a "For the initiative:" label before the DSI name, (5a) PDF report's score status dot (green/orange/red) is visually clipped, (5b) PDF "Get expert help" box says "Centre of Excellence" instead of "Data Spaces Support Centre", (6) buttons AND cards app-wide have rounded corners but DSSC's brand style (dssc.eu) uses square corners, (7) Admin Panel's "Answers per user" should show completed-assessment count instead of raw answer count on both the Dataspace Maturity Assessments tab and the Users tab, plus an indicator for an in-progress next assessment.
**Requirements**: TBD (phase-local pseudo-IDs BUG-01/02/03/04/05A/05B/06/07 used in plan frontmatter, mapped 1:1 to the 7 bugs above)
**Depends on:** Phase 16
**Plans:** 6/6 plans complete

Plans:
**Wave 1** *(5 plans, disjoint files, run in parallel)*

- [x] 16.3-01-PLAN.md — Retake-save fix: shared useStartOrRetakeAssessment hook wired into TopNav + Dashboard + a questionnaire.tsx defense-in-depth guard (Wave 1; BUG-01)
- [x] 16.3-02-PLAN.md — Questionnaire text color: QuestionCard.tsx + AnswerButtonGroup.tsx blue-to-black (Wave 1; BUG-02)
- [x] 16.3-03-PLAN.md — "View Report" assessment_id fix in assessments.tsx, matching the already-proven admin.heatmap.tsx pattern (Wave 1; BUG-03)
- [x] 16.3-04-PLAN.md — PDF report.html: "For the initiative:" label, flattened WeasyPrint-safe answers-row (score-dot clipping), "Data Spaces Support Centre" wording + human-verify checkpoint (Wave 1; BUG-04, BUG-05A, BUG-05B)
- [x] 16.3-05-PLAN.md — Admin panel completed-assessment count + in-progress indicator on both the Assessments and Users tabs (backend query rewrite + rewritten tests + frontend columns) (Wave 1; BUG-07)

**Wave 2** *(blocked on Wave 1 completion — touches files 16.3-01/02/03/05 already modified)*

- [x] 16.3-06-PLAN.md — Square corners (buttons + cards, D-01): theme.ts component-scoped Button/Card radius + ~53 inline-style edits across 17 files (Wave 2, depends on 16.3-01, 16.3-02, 16.3-03, 16.3-05; BUG-06)

### Phase 16.1: DSSC Rebrand — Visual Identity, Terminology, PDF Content & Registration Default (INSERTED)

**Goal**: The tool is fully rebranded from CoE-DSC to DSSC (colors, logo, wording — including "Questionnaire" → "Dataspace Maturity Assessment") across the app and the PDF report, the PDF report includes the initiative's actual submitted answers alongside the scores, and new registrations default to DSI only (with the Service-Provider option removable/restorable without a data-model change).
**Depends on**: Phase 16
**Requirements**: BRAND-01, BRAND-02, BRAND-03, RPRT-05, REG-01
**Success Criteria** (what must be TRUE):

  1. No CoE-DSC colors, logo, or wording remain anywhere in the app (homepage, About page, Dashboard, and every other page) — replaced with DSSC's own visual identity.
  2. User-facing terminology reflects DSSC naming throughout, including "Questionnaire" renamed to "Dataspace Maturity Assessment" wherever it appears to the user.
  3. The mailed/downloaded PDF report's branding and wording match the new DSSC identity, consistent with the in-app rebrand.
  4. The PDF report shows the initiative's actual submitted answers (per question), not only the aggregate dimension scores and priority list.
  5. The registration screen no longer offers a "Service Provider" option — new accounts register as DSI by default — and the option can be restored later without a data-model change (the underlying participant-type field/enum is not deleted, only the UI choice is hidden).

**Plans**: 4/4 plans executed

Plans:
**Wave 1**

- [x] 16.1-01-PLAN.md — Frontend color/font/logo swap: theme.ts + globals.css + index.html central tokens, DSSC logo asset copy, ~19 component/route files' hardcoded hex/Rubik recolor + logo import swaps (Wave 1; BRAND-01)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 16.1-02-PLAN.md — Backend PDF rebrand + new submitted-answers section + MAMI/CoE-DSC/Questionnaire wording removal across backend and frontend (Wave 2, depends on 16.1-01; BRAND-02, BRAND-03, RPRT-05)
- [x] 16.1-03-PLAN.md — Registration feature flag: hide the DSI/SP toggle in register.tsx (default DSI), fix TopNav.test.tsx's alt-text assertion (Wave 2, depends on 16.1-01; REG-01)

**Gap-Closure Wave 1** *(verification found 84 residual old-branding instances across 10 files; Plans 01–02 claimed complete but grep verification disproved)*

- [x] 16.1-04-PLAN.md — Fix 51 remaining 'Rubik' font references + 33 remaining old hex colors (#399e5a, rgba(6,0,79,...)) across 9 broken frontend route files + 1 backend filename string in reports.py (BRAND-01, BRAND-02, BRAND-03)

### Phase 16.2: Content & UX Updates — Frontpage/About Rebrand Copy, Assessment Intro Texts & Question Grouping (INSERTED)

**Goal**: The homepage, About page, and assessment wizard reflect the new DSMA copy, structure, and grouping specified in `Teksten MAMI Tool.pdf`, so the tool's content and question flow match the finalized wording before test-coverage and security-hardening work begins.
**Depends on**: Phase 16.1
**Requirements**: TBD
**Success Criteria** (what must be TRUE):

  1. The homepage ("Hoofdpagina") shows the new DSMA copy from the PDF — including the MAMI → DSMA rebrand of headings, CTAs, and body text — and any specified color changes.
  2. The About page shows the new "About Data Space Maturity Assessment Tool" copy from the PDF, and any specified color changes.
  3. The assessment opens with an introductory/welcome screen (the PDF's "Voorblad questionnaire" copy: Welcome, What you will assess, What you will receive, Before you start, Time required) before any question is shown.
  4. Each of the 6 maturity-dimension pages (Governance, Business, Legal, Interoperability, Control over Data & Trust, Value Creation) opens with its own introductory text, exactly as specified in the PDF's "Assessment tool" table (items 14–19).
  5. The 52 questions are grouped under the 16 named subsections given in the PDF's "Secties questionnaire" table (e.g. Q1-4 "Governance Framework Establishment" … Q48-52 "Adoption Level"), each with a visible sub-header.

**Plans**: 6/6 plans executed

Plans:
**Wave 1**

- [x] 16.2-01-PLAN.md — Font/color/logo foundation: self-hosted Jost + dssc.eu tokens (globals.css/theme.ts) + logo asset replacement + mechanical 'Open Sans'→Jost replace across 18 files (Wave 1)
- [x] 16.2-04-PLAN.md — Config content: per-category `intro` + `subsections` added to dssc-questionnaire.json, `Subsection` type added to questionnaire.ts (Wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 16.2-02-PLAN.md — Homepage + Footer: new DSMA copy, dssc.eu hero gradient/logo/ink text, dark-navy footer (Wave 2, depends on 16.2-01)
- [x] 16.2-03-PLAN.md — About page: new copy (2 paragraphs) + app-wide dssc.eu background wash via _app.tsx (Wave 2, depends on 16.2-01)
- [x] 16.2-05-PLAN.md — Wizard UI: gated welcome screen (fixes Pitfall 1 resume-position bug), dimension-intro box, 16-subsection question grouping (Wave 2, depends on 16.2-01, 16.2-04)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 16.2-06-PLAN.md — Human visual/behavioral verification checkpoint covering all 5 success criteria (Wave 3, depends on 16.2-02, 16.2-03, 16.2-05) — conditional approval; user deferred literal click-through to the Railway Integration deployment (see 16.2-06-SUMMARY.md)

### Phase 17: Test Coverage — New Scoring, Questionnaire & Visualization Logic + E2E

**Goal**: The rebuilt scoring engine, questionnaire API, wizard, and report rendering have automated test coverage, and a Playwright suite verifies the critical end-to-end path.
**Depends on**: Phase 14, Phase 15, Phase 16
**Requirements**: TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):

  1. Backend pytest coverage exists for the scoring engine (including zero/partial-answer edge cases), the questionnaire submission API, and auth flows.
  2. Frontend Vitest + React Testing Library coverage exists for the wizard's save/state logic and the report's rendering (radar chart + priority list).
  3. A Playwright E2E suite runs the critical path — register, answer the full questionnaire, submit, view the report — and passes in CI.

**Plans**: 3 plans

Plans:
**Wave 1** *(3 plans, disjoint files, run in parallel — backend gap-fill touches only backend/tests/**, pr.yml, CLAUDE.md; frontend coverage touches only report.tsx/report.test.tsx/useDebouncedSave.test.ts; E2E touches only e2e/**, e2e-tests.yml, staging.yml, main.yml)*

- [ ] 17-01-PLAN.md — Backend gap-fill: auth-negative dependency test (missing/malformed/expired token, deleted user) against 3 representative routes + perf/benchmark coverage for compute_dimension_scores (closes Phase 14's deferred IOU) + pr.yml perf-gate exit-5-tolerance cleanup (Wave 1; TEST-01)
- [ ] 17-02-PLAN.md — Frontend coverage: useDebouncedSave fake-timer tests (debounce/retry-backoff/rate-limit) + report.tsx radar-SVG/priority-list data-driven tests (ReportPage export fix included) (Wave 1; TEST-02)
- [ ] 17-03-PLAN.md — Playwright E2E: new top-level e2e/ critical-path suite (register→questionnaire→submit→report) + reusable e2e-tests.yml CI workflow wired into staging.yml (pulls :staging images) and main.yml (builds from source) (Wave 1; TEST-03)

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
| 14. Scoring Engine Replacement | v2.0 | 4/4 | Complete    | 2026-07-24 |
| 15. Questionnaire Submission API, Wizard UI & Save Reliability | v2.0 | 8/8 | Complete    | 2026-07-26 |
| 16. Report Data Contract, Dual Visualization & Admin Aggregation | v2.0 | 5/5 | Complete    | 2026-07-28 |
| 16.1. DSSC Rebrand — Visual Identity, Terminology, PDF Content & Registration Default | v2.0 | 4/4 | Complete    | 2026-08-03 |
| 16.2. Content & UX Updates — Frontpage/About Rebrand Copy, Assessment Intro Texts & Question Grouping | v2.0 | 6/6 | In Progress | - |
| 17. Test Coverage — New Logic + E2E | v2.0 | 0/3 | Planned | - |
| 18. Security Hardening & Password Reset Review | v2.0 | 0/TBD | Not started | - |
