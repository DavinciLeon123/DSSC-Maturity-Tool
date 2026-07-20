---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: MAMI Compliance Checker v1.0
status: active
last_updated: "2026-03-15T20:17:00.000Z"
progress:
  total_phases: 12
  completed_phases: 11
  total_plans: 37
  completed_plans: 38
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** A DSI leader can register, complete the MAMI questionnaire, and receive a clear compliance report showing where their initiative stands against the framework.
**Current focus:** Phase 01 (new cycle) bugfix phase — retake-questionnaire save, CSV follow-up, separate DSI/SP heatmaps.

## Milestone Status

**v1.0 — COMPLETE** (archived 2026-03-15)

- Archive: `.planning/milestones/v1.0-ROADMAP.md`
- Requirements: `.planning/milestones/v1.0-REQUIREMENTS.md`
- Git tag: `v1.0`
- 35/40 v1 requirements shipped. 5 deferred to future release (EVID-02–05, ADMN-04).

## Current Position

**Active phase:** 01-bugfix-retake-questionnaire-save-csv-missing-follow-up-selections-separate-dsi-sp-aggregated-heatmaps
**Current plan:** 01-02 COMPLETE. All plans in phase complete.

Last session (2026-03-15): Completed 01-02-PLAN.md — CSV followup_selections column fix + DSI/SP tabbed heatmap.

## Accumulated Context

### Tech Stack

- Backend: Python/FastAPI + SQLModel + PostgreSQL + GoRules ZEN Engine + WeasyPrint + Resend SDK
- Frontend: React/Vite + TanStack Router + antd v6
- Deployment: Railway (Docker Compose), staging + production
- Auth: JWT (24h), bcrypt, localStorage key `mami_access_token`

### Key Decisions

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
