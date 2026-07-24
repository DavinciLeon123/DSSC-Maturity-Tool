# Requirements: DSSC Maturity Scan for Dataspaces (v2.0)

**Defined:** 2026-07-21
**Core Value:** A dataspace initiative leader can complete the DSSC Maturity Scan and immediately see which of the 6 maturity dimensions need attention, via a clear score, priority ranking, and visual report.

## v1 Requirements

Requirements for the v2.0 milestone. Each maps to roadmap phases.

### Questionnaire (QSTN)

- [x] **QSTN-01**: User answers a 52-question assessment organized into 6 categories (dimensions)
- [ ] **QSTN-02**: Each question presents 5 answer options via a horizontal line with radio circles, each mapped to a 1-5 maturity score
- [x] **QSTN-03**: Question and answer-option text (including per-question custom option labels) is fully config-driven — no code deploy required to change content
- [x] **QSTN-04**: Questionnaire is universal — no DSI/Service-Provider (or other) participant-type split
- [x] **QSTN-05**: Real v2.0 question and category content is loaded into config (content pending from user, tracked separately from engineering work)

### Scoring (SCOR)

- [x] **SCOR-01**: Dimension score = sum of answers in that dimension / number of questions in that dimension, range 1.0–5.0
- [x] **SCOR-02**: All questions are equally weighted — no question or category weighting
- [ ] **SCOR-03**: GoRules ZEN Engine and MoSCoW scoring are fully removed, not dual-maintained
- [x] **SCOR-04**: Report/scores are only computed and shown once the full questionnaire is 100% answered (no partial/live scoring)

### Reporting (RPRT)

- [ ] **RPRT-01**: End-of-survey report shows a spider/radar chart visualizing all 6 dimension scores at a glance
- [ ] **RPRT-02**: End-of-survey report shows a sorted priority list (lowest→highest maturity) with dimension name, average score, and color indicator (red 1.0-2.0, orange 2.0-3.5, green 3.5-5.0)
- [ ] **RPRT-03**: Color-band thresholds are defined once in config and shared by both the chart and the priority list (no duplicated logic)
- [ ] **RPRT-04**: Report is available both in-app (live view) and as a mailed PDF (WeasyPrint + Resend), each rendering the same score data via one shared JSON contract

### Retake & History (HIST)

- [ ] **HIST-01**: Retaking the questionnaire creates a new, dated assessment version rather than overwriting or mutating the previous submitted one
- [ ] **HIST-02**: User can view a history of their past assessments and compare maturity scores across versions

### Save Reliability (SAVE)

- [ ] **SAVE-01**: Answers are auto-saved as the user answers each question (debounced), not only on Next/Back navigation or component unmount
- [ ] **SAVE-02**: Save failures are surfaced to the user with a clear retry path — no silent fire-and-forget saves
- [ ] **SAVE-03**: Rate limiting on answer-save requests is keyed per authenticated user, not per client IP
- [ ] **SAVE-04**: Closing the tab or hard-refreshing mid-questionnaire does not silently lose unsaved answers

### Data Migration (MIGR)

- [x] **MIGR-01**: Existing v1.0 MAMI initiative/answer data is preserved read-only for historical reference, not deleted
- [x] **MIGR-02**: The evidence/URL-per-question subsystem from MAMI is removed entirely — no equivalent in the new schema

### Security (SECU)

- [ ] **SECU-01**: JWT auth token moves from localStorage to an httpOnly cookie, with CSRF protection and CORS credentials configured together
- [ ] **SECU-02**: Initiative/user IDs are not enumerable via sequential guessing
- [ ] **SECU-03**: Bare exception handling in flagged areas (per `.planning/codebase/CONCERNS.md`) is replaced with explicit, logged error handling
- [ ] **SECU-04**: Admin actions (user/initiative management, exports) are recorded in a structured audit log

### Admin (ADMN)

- [ ] **ADMN-01**: Admin aggregated view is rebuilt for the new 6-category model (cross-initiative radar/priority visualization), replacing the old 4×3 topic heatmap

### Testing (TEST)

- [ ] **TEST-01**: Backend has pytest unit test coverage for the scoring engine, questionnaire API, and auth flows
- [ ] **TEST-02**: Frontend has Vitest + React Testing Library coverage for wizard save/state logic and report rendering
- [ ] **TEST-03**: Playwright E2E suite covers the critical path: register → answer questionnaire → submit → view report

### Auth (AUTH) — stretch, time permitting

- [ ] **AUTH-01**: Existing self-service password reset flow is reviewed and hardened (already shipped in v1.0 — verify only)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Benchmarking (BNCH)

- **BNCH-01**: User can benchmark their maturity scores against anonymized aggregate/peer data

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| DSI/Service-Provider participant-type split | Replaced by one universal questionnaire (QSTN-04) |
| Evidence/URL-per-question subsystem | Removed entirely — no home in the new 6-category schema, not part of target features (MIGR-02) |
| SSRF / URL-validation hardening | Resolved by removing the evidence subsystem entirely (MIGR-02) — eliminates the user-supplied URL input surface that created the risk |
| Coexistence with MAMI questionnaire | Full replacement per milestone decision, not a second parallel framework |
| Overwrite-in-place retake | Rejected in favor of versioned assessment history (HIST-01) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| QSTN-01 | Phase 13 | Complete |
| QSTN-02 | Phase 15 | Pending |
| QSTN-03 | Phase 13 | Complete |
| QSTN-04 | Phase 13 | Complete |
| QSTN-05 | Phase 13 | Complete |
| SCOR-01 | Phase 14 | Complete |
| SCOR-02 | Phase 14 | Complete |
| SCOR-03 | Phase 14 | Pending |
| SCOR-04 | Phase 14 | Complete |
| RPRT-01 | Phase 16 | Pending |
| RPRT-02 | Phase 16 | Pending |
| RPRT-03 | Phase 16 | Pending |
| RPRT-04 | Phase 16 | Pending |
| HIST-01 | Phase 15 | Pending |
| HIST-02 | Phase 15 | Pending |
| SAVE-01 | Phase 15 | Pending |
| SAVE-02 | Phase 15 | Pending |
| SAVE-03 | Phase 15 | Pending |
| SAVE-04 | Phase 15 | Pending |
| MIGR-01 | Phase 13 | Complete |
| MIGR-02 | Phase 13 | Complete |
| SECU-01 | Phase 18 | Pending |
| SECU-02 | Phase 18 | Pending |
| SECU-03 | Phase 18 | Pending |
| SECU-04 | Phase 18 | Pending |
| ADMN-01 | Phase 16 | Pending |
| TEST-01 | Phase 17 | Pending |
| TEST-02 | Phase 17 | Pending |
| TEST-03 | Phase 17 | Pending |
| AUTH-01 | Phase 18 | Pending |

**Coverage:**

- v1 requirements: 30 total
- Mapped to phases: 30/30 ✓
- Unmapped: 0

**Note:** Phase 12 (Test Retrofit — Stabilize Existing Flows) maps no v1 requirement directly — it is a foundational regression-safety-net phase (auth/admin/PDF-email characterization tests) that protects delivery of Phases 13-18, per research/SUMMARY.md's build-order guidance. All 30 v1 requirements are covered by Phases 13-18.

---
*Requirements defined: 2026-07-21*
*Last updated: 2026-07-22 — relocated from MaMi-Compliance-Checker to this repo (DSSC-Maturity-Tool), the correct fork for this milestone*
