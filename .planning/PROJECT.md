# MAMI Compliance Checker

## What This Is

A web-based compliance assessment tool for TNO CoE-DSC that lets Data Sharing Initiative (DSI) leaders and Service Providers (SPs) evaluate their initiative against the MAMI (Minimal Agreements for Maximal Interoperability) framework. Users fill in a config-driven 27-question questionnaire mapped to MAMI's 4×3 matrix and receive a live interoperability heatmap, a mailed PDF report with recommendations, and guidance for expert follow-up with CoE-DSC.

## Current State

**Shipped: v1.0** (2026-03-15)

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

**Tech stack:** Python/FastAPI + SQLModel + PostgreSQL + React/Vite + GoRules ZEN Engine + WeasyPrint + Resend SDK · Deployed: Railway

## Core Value

A DSI leader can register, complete the MAMI questionnaire, and receive a clear compliance report showing where their initiative stands against the framework — turning a complex standard into actionable guidance.

## Next Milestone Goals

No immediate next milestone defined. Potential future work:

- URL crawling subsystem: consent-gated HTTP checks, keyword presence, SHA-256 snapshots, SSRF protection, rate limiting (EVID-02–05)
- Audit logging for URL checks and report generation (ADMN-04)
- Browser-downloadable PDF report button (complement to current email delivery)
- Questionnaire visual builder (WYSIWYG admin editor)
- Business rules engine with visual editor

<details>
<summary>v1.0 Requirements (shipped)</summary>

Full archived requirements: `.planning/milestones/v1.0-REQUIREMENTS.md`
Full archived roadmap: `.planning/milestones/v1.0-ROADMAP.md`

35/40 v1 requirements shipped. 5 deferred (EVID-02–05, ADMN-04).

</details>

## Context

**MAMI Framework Structure:**
- 4 categories: Scheme management, Participants management, Data management, Services management
- 3 dimensions: Human readable/actionable, Machine readable/actionable, Trust Anchors
- 27 specific recommendation codes (HRA/MRA/TA × 1.1–4.2)

**Organizational Context:**
- Built for TNO Centre of Expertise for Data Sharing and Cloud (CoE-DSC)
- Production: https://www.coe-dsc.nl (Railway)
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
| Questionnaire engine | GoRules ZEN Engine (single-answer evaluation pattern) |
| Config-driven questionnaire | JSON configs per participant type — no code deploys for question changes |
| Report delivery | HTML in-app + PDF via email (WeasyPrint + Resend) — no browser download yet |
| URL crawling | Deferred — simple URL storage only for v1.0 |
| Deployment | Railway (Docker Compose), staging + production environments |
| DB | PostgreSQL + SQLModel + Alembic; pool_size=15, max_overflow=25 |

## Constraints

- **Modularity**: MAMI framework, questionnaire, scoring logic, and presentation are separate, swappable modules
- **Config-driven**: Questionnaire structure, scoring rules, and MAMI mappings configurable without code changes
- **API-first**: All functionality accessible via REST API with OpenAPI documentation
- **Branding**: Uses coe-dsc.nl color scheme (navy #06004f, green #399e5a, Rubik font)

---
*Last updated: 2026-03-15 after v1.0 milestone completion*
