# MAMI Compliance Checker → DSSC Maturity Scan for Dataspaces

## What This Is

A web-based compliance assessment tool for TNO CoE-DSC that lets Data Sharing Initiative (DSI) leaders and Service Providers (SPs) evaluate their initiative against the MAMI (Minimal Agreements for Maximal Interoperability) framework. Users fill in a config-driven 27-question questionnaire mapped to MAMI's 4×3 matrix and receive a live interoperability heatmap, a mailed PDF report with recommendations, and guidance for expert follow-up with CoE-DSC.

This repository (`DSSC-Maturity-Tool`) is the fork where the MAMI Compliance Checker is being retrofitted into the **DSSC Maturity Scan for Dataspaces** — see "Current Milestone" below.

## Current State

**Shipped: v1.0** (2026-03-15, as MAMI Compliance Checker)

The application is production-deployed on Railway and demo-ready for events with up to 100 simultaneous users.

**What's live:**
- User registration + JWT auth with ADMIN/USER RBAC
- DSI and SP participant types, each with 27-question config-driven MAMI questionnaire (v3.0)
- Yes / Not there yet / N/A answer format with multi-select follow-ups
- MoSCoW scoring (GoRules ZEN Engine) → CRITICAL/NON_CRITICAL findings
- Live interoperability heatmap (topic-level, 4 categories × 3 dimensions)
- Mail PDF report via WeasyPrint + Resend with per-code recommendations
- Admin panel: user/initiative management, CSV export, demo reset, aggregated heatmap
- Self-service password reset via Resend email
- Mobile-responsive wizard and report pages
- Figma-matched UI: navy #06004f, green #399e5a, Rubik font, antd v6

**Since forking from MAMI Compliance Checker (2026-07-20), independently of the v2.0 milestone below**, this repo also added: a 5-workflow CI/CD pipeline (PR checks, staging, main, release, security), ruff/mypy quality gates, a starter test suite (health check, privacy canary, scoring perf/benchmark regression), dependency vulnerability remediation, and branch protection. See `CLAUDE.md` for the full branch model and CI details.

**Phase 13 complete (2026-07-23):** The data layer now serves the new universal 52-question/6-category DSSC config (`config/dssc-questionnaire.json`) with no DSI/SP participant-type split, a new `Assessment` draft/submitted lifecycle entity, and a reshaped `questionnaire_answer` (assessment_id/category_id/1-5 score). All pre-migration v1.0 answer data is preserved read-only in a new archive table via a hand-written Alembic migration; the evidence/URL-per-question subsystem is fully removed. The old MAMI/ZEN scoring path and wizard/report frontend still read the OLD answer shape and are intentionally untouched pending Phase 14 (scoring engine replacement) and Phases 15/16 (wizard + report rebuild) — new-schema initiatives currently degrade to zero-findings/all-zero results on those legacy endpoints, a documented interim gap, not a defect.

**Phase 14 complete (2026-07-24):** GoRules ZEN Engine and MoSCoW scoring are fully deleted from the codebase (package dependency, `scoring_engine.py`, both MAMI config files, all lifespan/dependency wiring) — a static regression test (`test_zen_removed.py`) locks the removal in place. All five score/report endpoints (`/score`, `/report`, `/report/data`, `/report/pdf`, `/report/mail`) plus admin `/heatmap` now compute maturity via the new equal-weight per-dimension averaging service (`dimension_scoring.py`, sum(answers)/n) and enforce a server-side completion gate (422 on incomplete assessments) before scoring. `/admin/heatmap` is reduced to a fixed degraded response pending its Phase 16 rebuild. Frontend `scoring.ts`/`FindingsPanel.tsx` still contain orphaned MoSCoW-shaped types (unused, not imported) — a deliberate, user-approved deferral to Phases 15/16, not an oversight.

**Tech stack:** Python/FastAPI + SQLModel + PostgreSQL + React/Vite + WeasyPrint + Resend SDK · Deployed: Railway

## Core Value

A DSI leader can register, complete the MAMI questionnaire, and receive a clear compliance report showing where their initiative stands against the framework — turning a complex standard into actionable guidance. (This will evolve to a dataspace-maturity framing as the v2.0 milestone lands.)

## Current Milestone: v2.0 DSSC Maturity Scan for Dataspaces

**Goal:** Retrofit the MAMI Compliance Checker into a DSSC Maturity Scan for Dataspaces — replacing MAMI's 27-question/4×3 questionnaire and MoSCoW/GoRules scoring with a new 52-question/6-category equal-weighted maturity assessment, a dual-visualization report, security hardening, and automated/E2E test coverage.

**Target features:**
- New 52-question / 6-category DSSC questionnaire replacing MAMI entirely (config-driven, per-question custom 5 answer-option labels, each mapped to 1-5)
- Horizontal-line radio-circle answer UI (5 discrete positions per question)
- Equal-weight dimension scoring: dimension score = sum(answers)/n, range 1.0–5.0 — replaces GoRules MoSCoW engine
- End-of-survey report: spider/radar chart (all 6 dimensions at a glance) + sorted priority list (lowest→highest maturity, red/orange/green color bands: 1.0-2.0 / 2.0-3.5 / 3.5-5.0)
- Security hardening pass, scoped from `.planning/codebase/CONCERNS.md` (JWT-in-localStorage, sequential ID enumeration, bare exception handling, missing audit logging, missing URL validation)
- Automated unit tests + Playwright E2E suite for the *rebuilt* subsystems (Phase 17) — building on top of, not replacing, the characterization/regression coverage Phase 12 adds for what ISN'T being rebuilt (auth, admin, PDF/email) and the health/privacy/scoring-perf suite this repo already had before this milestone started
- Password reset review/hardening (already shipped in v1.0 — verify & harden, not build from scratch)

**Note:** This milestone's "DSSC Maturity Scan for Dataspaces" scope — and the requirements/roadmap below — were originally planned and Phase 12 executed against a checkout of this same codebase in a different repository (`MaMi-Compliance-Checker`), before being relocated here to the correct fork. The technical content (research, patterns, test code) is unchanged by the relocation; only the repository and CI integration were adapted — see `.planning/phases/12-test-retrofit-stabilize-existing-flows/12-RELOCATION-NOTE.md`.

**Superseded candidates:** MAMI's URL crawling subsystem (EVID-02–05), audit logging (ADMN-04), and questionnaire visual builder — previously listed in this repo's `ROADMAP.md` as candidate future work — are superseded by this milestone's scope unless explicitly revived during requirements gathering.

<details>
<summary>v1.0 Requirements (shipped)</summary>

Full archived requirements: `.planning/milestones/v1.0-REQUIREMENTS.md`
Full archived roadmap: `.planning/milestones/v1.0-ROADMAP.md`

35/40 v1 requirements shipped. 5 deferred (EVID-02–05, ADMN-04) — superseded by v2.0 scope above.

</details>

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

## Context

**MAMI Framework Structure:**
- 4 categories: Scheme management, Participants management, Data management, Services management
- 3 dimensions: Human readable/actionable, Machine readable/actionable, Trust Anchors
- 27 specific recommendation codes (HRA/MRA/TA × 1.1–4.2)

**Organizational Context:**
- Built for TNO Centre of Expertise for Data Sharing and Cloud (CoE-DSC)
- Production: https://www.coe-dsc.nl (Railway, MAMI Compliance Checker v1.0)
- Pilot scale: up to 100 simultaneous users

**Design Philosophy:**
- Modular: questionnaire, scoring, and presentation are independent layers
- Config-driven: question changes require no code deploys (edit JSON configs)
- API-first: all functionality via REST API with OpenAPI docs at /docs

## Key Decisions (Settled)

| Decision | Outcome |
|----------|---------|
| Full-stack MVP | FastAPI + React/Vite (TanStack Router, antd v6) |
| Self-contained auth | JWT (24h), bcrypt, localStorage — no OAuth |
| Questionnaire engine (v1.0) | GoRules ZEN Engine (single-answer evaluation pattern) — **replaced in Phase 14** |
| Scoring engine (v2.0, Phase 14) | Equal-weight per-dimension averaging (sum(answers)/n, no rules engine) — replaces GoRules ZEN Engine/MoSCoW entirely; server-side completion gate (422) blocks scoring on incomplete assessments |
| Config-driven questionnaire | JSON configs per participant type — no code deploys for question changes |
| Report delivery | HTML in-app + PDF via email (WeasyPrint + Resend) — no browser download yet |
| URL crawling | Deferred — simple URL storage only for v1.0 |
| Deployment | Railway (Docker Compose), staging + production environments |
| DB | PostgreSQL + SQLModel + Alembic; pool_size=15, max_overflow=25 |
| Test infra (this repo, pre-v2.0) | ruff/mypy/pytest-xdist/pytest-benchmark + health/privacy-canary/scoring-perf suite, 5-workflow CI/CD, branch protection on `staging`/`main` |
| Test infra (v2.0 Phase 12, this PR) | Real-Postgres testcontainers for auth/admin/reports characterization tests — merged additively into the pre-existing conftest.py/pyproject.toml above |

## Constraints

- **Modularity**: MAMI framework, questionnaire, scoring logic, and presentation are separate, swappable modules
- **Config-driven**: Questionnaire structure, scoring rules, and MAMI mappings configurable without code changes
- **API-first**: All functionality accessible via REST API with OpenAPI documentation
- **Branding**: Uses coe-dsc.nl color scheme (navy #06004f, green #399e5a, Rubik font)

---
*Last updated: 2026-07-24 — Phase 14 (scoring engine replacement) complete*
