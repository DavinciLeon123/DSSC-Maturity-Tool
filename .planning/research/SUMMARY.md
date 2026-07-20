# Project Research Summary

**Project:** MAMI Compliance Checker — TNO CoE-DSC
**Domain:** Config-driven compliance assessment web application (questionnaire + rule engine + URL verification + report generation)
**Researched:** 2026-02-14
**Confidence:** MEDIUM-HIGH

## Executive Summary

The MAMI Compliance Checker is a bespoke, config-driven GRC tool for DSI initiative owners to self-assess against the MAMI 4x3 compliance framework and receive structured CRITICAL/NON_CRITICAL findings reports. Unlike generic GRC SaaS tools (Vanta, Drata), this must be self-hosted on coe-dsc.nl infrastructure, fully API-first, and extensible by non-developers via visual config editors — there is no commercial product that covers the MAMI framework, making this a build-from-scratch project. The recommended approach is a Python/FastAPI backend with a React/TypeScript SPA frontend, using GoRules ZEN Engine for the rule engine, RJSF for JSON Schema-driven questionnaire rendering, and WeasyPrint for PDF report generation. All major technology choices are verified against current PyPI/npm releases; the stack is cohesive with no version incompatibilities at the recommended versions.

The project has a clear, well-understood architecture: a modular monolith with a config-driven domain at its core — the MAMI framework definition, questionnaire schemas, and scoring rules all live as JSON/YAML files rather than in application code. This is the most critical architectural constraint: every scoring rule, MAMI code mapping, and question must be editable without a code deploy. The build order has clear dependencies — foundation and auth must precede questionnaire, which must precede scoring, which must precede reporting — and following this order ensures each phase is independently testable and deliverable.

The highest-risk areas are the URL check subsystem (SSRF is a real, documented attack vector requiring concrete prevention), questionnaire versioning (missing from most first implementations; causes silent data corruption), and the comply-or-explain answer type (routinely breaks scoring logic if not modelled from the start). None of these are intractable — each has a clear prevention strategy — but all three must be addressed in their respective phases, not as post-MVP hardening. The pilot target of under 50 users keeps infrastructure simple: no Redis, no Celery, no microservices; APScheduler inside FastAPI and pg-boss for job queuing are sufficient and correct for this scale.

---

## Key Findings

### Recommended Stack

The backend is Python 3.11+ with FastAPI 0.129.0 as the API framework, SQLModel 0.0.33 as the ORM (single class serves as both DB model and API schema), PostgreSQL 16+ as the primary database, and Alembic 1.18.4 for migrations. The frontend is Vite 7.3.1 + React 18 + TypeScript 5.x, requiring Node.js 22 LTS. Package management uses `uv` on the Python side (10-100x faster than pip) and standard npm on the frontend. Docker + docker-compose provides the local dev and deployment environment.

The questionnaire layer uses `@rjsf/core` 6.3.1 (Apache 2.0, freely embeddable) for JSON Schema-driven form rendering — critically, the full RJSF stack (renderer + builder) carries no commercial license restrictions, unlike SurveyJS Creator which requires a paid license. The rule engine is GoRules ZEN Engine (`zen-engine` 0.51.0 Python package + `@gorules/jdm-editor` React component): the only open-source Python rule engine with a matching open-source visual editor that stores rules as JSON files. URL checking uses `httpx` 0.28.1 (async) with `APScheduler` 3.11.2 for scheduled re-checks — Celery is explicitly over-engineered for this scale. Reports use Jinja2 templating with `WeasyPrint` 68.1 for HTML-to-PDF conversion.

**Core technologies:**
- Python 3.11+ / FastAPI 0.129.0: async REST API, auto-generates OpenAPI 3.x spec, Pydantic v2 native
- SQLModel 0.0.33: eliminates SQLAlchemy model + Pydantic schema duplication; pin SQLAlchemy to `<2.1.0`
- PostgreSQL 16+: JSONB support for questionnaire config storage; SQLite is dev/test only
- GoRules ZEN Engine 0.51.0: sub-millisecond rule evaluation, JDM JSON files as config, visual editor available
- @rjsf/core 6.3.1: Apache 2.0 JSON Schema form renderer; use `@rjsf/validator-ajv8` (ajv6 is deprecated)
- WeasyPrint 68.1: CSS-fidelity HTML-to-PDF; requires Python 3.10+
- bcrypt (direct): replaces passlib (unmaintained since 2020, crashes on Python 3.13)
- APScheduler 3.11.2 with AsyncIOScheduler: background scheduling without Redis/broker dependency

**Critical version constraints:**
- SQLModel 0.0.33 requires SQLAlchemy `>=2.0.14,<2.1.0` — pin explicitly
- SQLModel 0.0.33 requires Pydantic `>=2.7.0` — do NOT mix with Pydantic v1 dependencies
- Vite 7.3.1 requires Node.js 20.19+ or 22.12+ — Node 18 is EOL
- @rjsf/core 6.x supports React 17 or 18 — React 19 not yet confirmed

### Expected Features

The MVP scope is well-defined by the Briefing.md project source of truth and validated against GRC tool landscape research. All P1 features are required for the pilot launch; P2 features activate post-validation when TNO confirms the need.

**Must have (table stakes — P1):**
- User registration + login with USER/ADMIN RBAC — needed to own and persist initiative data
- Initiative registration — the named entity that owns all answers and reports
- Config-driven MAMI questionnaire with save/resume — the core data-collection workflow; auto-save per answer change
- MoSCoW scoring engine (MUST→CRITICAL, SHOULD→NON_CRITICAL, config-overrideable) — the compliance logic
- NOT_APPLICABLE and comply-or-explain answer types — required by MAMI methodology
- HTML compliance report: executive summary + MAMI 4x3 matrix overview + per-code findings — the core output
- CRITICAL/NON_CRITICAL finding classification in report — differentiates from generic survey tools
- Report re-generation on demand — keeps report current with updated answers
- URL evidence subsystem (HTTP status check + keyword presence + explicit consent + snapshot hash/timestamp) — explicit Briefing.md requirement
- Audit log for URL checks and report generation — explicit Briefing.md requirement; insert-only table
- Admin: user list, initiative list, soft delete — minimum admin function
- REST API + OpenAPI 3.x spec — frontend team dependency; blocks parallel FE development
- DB migrations + seed with current MAMI config — required for deployment

**Should have (differentiators — P2, add after pilot validation):**
- PDF export of compliance report — trigger: users request shareable format
- LLM-based URL content analysis — trigger: evidence quality complaints
- Business rules engine + visual editor — trigger: cross-checking requirements documented by TNO
- Visual questionnaire builder (RJSF admin UI) — trigger: TNO needs to update question set themselves
- Admin analytics aggregation heatmap — trigger: 5+ initiatives submitted, TNO wants ecosystem insights

**Defer (v2+):**
- SSO / SAML / OAuth2 — pilot scale doesn't justify complexity
- Multi-initiative per user — single DSI per user sufficient for pilot
- Multi-framework simultaneous mapping — architecture should support it; do not build in MVP
- Real-time collaborative editing — WebSocket complexity far exceeds 5-day scope
- Public benchmarking / anonymized aggregate comparison — privacy implications need stakeholder sign-off

### Architecture Approach

The recommended architecture is a modular monolith (not microservices) with clear package boundaries. The MAMI Framework Service is the dependency root — all other packages import from it, never the reverse. The Questionnaire Engine and Rule Engine are Python packages embedded in the FastAPI process; the URL Check Subsystem runs as a separate async worker process sharing the database. This architecture scales to the 50-user pilot with no additional infrastructure (no Redis, no Celery, no separate rule engine service); the design explicitly supports extraction to microservices at 1K+ users if growth occurs.

**Major components:**
1. MAMI Framework Service — owns the MAMI 4x3 code definitions, categories, dimensions, MoSCoW levels as a JSON config file; loaded at startup; read-only API; all other components import from here
2. Questionnaire Engine — serves versioned JSON Schema to frontend, validates answers, maps answers to MAMI codes; answer rows stored per-question (not as JSON blob) with version stamp
3. Rule Engine Service — GoRules ZEN Engine embedded in API process; loads JDM decision files from disk; produces Finding[] array with severity, rationale, per-code results
4. URL Check Subsystem — async job worker with consent gate; HTTP probe (status + keyword scan) + SHA-256 snapshot; rate-limited per domain; never runs in synchronous request path
5. Report Generator — read-only assembler; queries rule engine findings + URL check results + answers; renders via Jinja2 HTML template; stores HTML snapshot; PDF via WeasyPrint
6. Auth / User Service — JWT (python-jose), bcrypt passwords, RBAC middleware (USER/ADMIN), opaque UUIDs to prevent initiative enumeration
7. Admin Service — protected admin-only routes for user management, initiative listing, analytics aggregations
8. Audit Logger — insert-only audit_log table; application DB user has INSERT but not UPDATE/DELETE

### Critical Pitfalls

1. **Questionnaire versioning gap** — Store `questionnaire_version` on every answer row and every report from day one. Never reload answers against the latest config; always resolve against the version active when answers were saved. Never rename or delete question IDs — mark deprecated instead. This must be designed into the DB schema before the first save endpoint is written.

2. **SSRF via URL check subsystem** — Resolve DNS before fetching; reject RFC 1918, loopback, link-local, and cloud metadata IP ranges. Disable automatic redirect following; validate each redirect destination through the same blocklist. Allow only http/https protocols. Enforce 5-second hard timeout. This is a hard security requirement, not post-MVP hardening — the Capital One breach used this exact vector.

3. **Comply-or-explain answer types silently break scoring** — Define the full answer type enum (YES, NO, NOT_APPLICABLE, COMPLY_OR_EXPLAIN) before writing any scoring logic. For each MoSCoW level, explicitly configure what each type contributes to the score. NOT_APPLICABLE must be excluded from the denominator, not scored as zero. Write unit tests for all four types before building the report generator.

4. **Questionnaire partial save data loss** — Design the answer table as row-per-question (`initiative_id`, `question_id`, `questionnaire_version`, `value`, `updated_at`), not a JSON blob per initiative. Auto-save on each answer change (debounced). Hydrate on page load from the database, not localStorage. Distinguish DRAFT from SUBMITTED states in the data model. This must be established before the first save endpoint is written.

5. **MoSCoW scoring collapse — everything becomes CRITICAL** — Add a config validation rule that warns or hard-fails when more than 50% of questions in any MAMI dimension are classified as MUST. Surface severity distribution prominently in the executive summary so authors self-correct before publishing. Make the CRITICAL default explicit and overrideable in config.

---

## Implications for Roadmap

Based on the combined research, the component dependency graph has a clear bottom-up build order. The architecture file identifies 7 levels; they can be grouped into 5-6 phases for a roadmap that delivers independently testable increments.

### Phase 1: Foundation and Auth
**Rationale:** Auth, RBAC, and the database schema are zero-dependency prerequisites. Nothing else can be built until the DB schema exists (especially the `questionnaire_version` column on answer rows — Pitfall 1). The REST API shell and OpenAPI spec must exist before the frontend team can develop in parallel.
**Delivers:** Running FastAPI server, PostgreSQL database with Alembic migrations, JWT auth with USER/ADMIN roles, RBAC middleware, OpenAPI spec stub, Docker Compose dev environment.
**Addresses:** User registration + login, RBAC, REST API contract (all P1).
**Avoids:** RBAC bypass pitfall (API-level not just UI-level enforcement); opaque UUID initiative IDs (privilege escalation prevention).
**Research flag:** Standard patterns — well-documented FastAPI + SQLModel + Alembic stack; no additional phase research needed.

### Phase 2: MAMI Framework and Questionnaire Core
**Rationale:** The MAMI Framework Service is the dependency root — all subsequent phases import from it. The questionnaire engine (schema + per-question answer storage) must be built before scoring because scoring operates on answers. The row-per-question answer design (Pitfall 5 prevention) must be locked in here.
**Delivers:** MAMI framework JSON config loader + typed API, versioned questionnaire JSON schema (v1), answer persistence endpoints with save/resume, questionnaire version stamping on answer rows, NOT_APPLICABLE and comply-or-explain answer types.
**Addresses:** Initiative registration, config-driven MAMI questionnaire with save/resume, questionnaire version awareness, NOT_APPLICABLE + comply-or-explain (all P1).
**Avoids:** Questionnaire versioning gap (Pitfall 1); partial save data loss (Pitfall 5); comply-or-explain scoring break (Pitfall 6 — define the full answer type enum here).
**Research flag:** Standard patterns for RJSF + FastAPI integration; no additional research needed.

### Phase 3: Scoring Engine and Findings
**Rationale:** Rule engine (GoRules ZEN) depends on validated answers from Phase 2. This phase delivers the first end-to-end data flow: answer → MoSCoW score → CRITICAL/NON_CRITICAL finding. MoSCoW scoring config validation (Pitfall 3) must be implemented here before any real MAMI config content is authored.
**Delivers:** GoRules ZEN Engine embedded in FastAPI, JDM decision files for MAMI scoring, MamiAnswerMapping evaluator, Finding[] output with severity and rationale, config validator (warns when >50% MUST), CRITICAL override capability in config.
**Addresses:** MoSCoW scoring engine, CRITICAL/NON_CRITICAL classification (P1).
**Avoids:** MoSCoW scoring collapse (Pitfall 3); comply-or-explain breaks scoring (Pitfall 6 — verified with all four answer types).
**Research flag:** GoRules ZEN Python bindings and JDM format are less documented than mainstream libraries; recommend `/gsd:research-phase` for GoRules integration specifics before this phase is planned.

### Phase 4: Report Generation
**Rationale:** Report Generator depends on Rule Engine findings (Phase 3) and the questionnaire answers (Phase 2). This phase completes the first full user flow: register → answer → generate report → view report. HTML first; PDF bolts on via WeasyPrint after HTML is validated.
**Delivers:** Jinja2 HTML report template (executive summary + MAMI 4x3 matrix overview + per-code findings), report snapshot storage (stored HTML, not live computation on GET), report re-generation endpoint, PDF export via WeasyPrint, questionnaire version resolved at report generation time.
**Addresses:** HTML compliance report, CRITICAL/NON_CRITICAL findings in report, report re-generation, executive summary section (all P1); PDF export (P2 — delivered here since WeasyPrint is already available).
**Avoids:** Monolithic report object anti-pattern (GET /report returns stored snapshot, not live recomputation); version mismatch (report records the questionnaire version and rule set version at generation time).
**Research flag:** WeasyPrint CSS fidelity with compliance report content needs testing; standard pattern otherwise.

### Phase 5: URL Check Subsystem
**Rationale:** URL checking depends on the consent model (requires auth from Phase 1 and initiative context from Phase 2) and integrates into reports (Phase 4). It is isolated from the critical path of phases 1-4, making it safe to defer. SSRF prevention (Pitfall 2) is the highest-security-risk implementation in the project and must be built correctly before the endpoint is reachable.
**Delivers:** Consent record model (per URL+initiative), URL submission endpoint (consent-required), async job worker (APScheduler / pg-boss), HTTP probe worker (httpx with SSRF prevention: IP blocklist, redirect validation, 5s timeout, protocol allowlist), SHA-256 snapshot storage, URL check result written to DB, audit log entry per URL check.
**Addresses:** URL evidence subsystem, audit log (both P1).
**Avoids:** SSRF attack (Pitfall 2 — IP blocklist on DNS resolution, disabled auto-redirects, protocol allowlist); synchronous URL probing in request path (performance trap); audit log not insert-only (security mistake).
**Research flag:** SSRF prevention implementation specifics (httpx configuration for redirect control and timeout enforcement) warrant a brief research spike at the start of this phase.

### Phase 6: Admin Dashboard and Analytics
**Rationale:** Admin service depends on all preceding data (users, initiatives, answers, reports, URL checks). The aggregate heatmap has no meaningful data until multiple initiatives are submitted — building the UI early is fine but it matures with data.
**Delivers:** Admin user management (list, soft delete), admin initiative listing (filter/sort/search), aggregate analytics heatmap (MAMI code x initiative count x score), admin UI with Recharts dashboard.
**Addresses:** Admin user management, admin initiative listing, admin analytics heatmap (P1 for management; P2 for heatmap).
**Avoids:** Admin dashboard with write DB permissions (read-only analytics DB user); admin heatmap full table scan on every load (aggregate on schedule or trigger + TTL cache).
**Research flag:** Standard patterns; no additional research needed.

### Phase 7: Visual Editors (Post-Pilot)
**Rationale:** Visual editors (RJSF questionnaire builder + GoRules JDM editor) are P2 features that activate when TNO needs to update the MAMI question set themselves. They are UX layers on top of the config formats already established in Phases 2-3. The config schema must be stable (finalized in Phase 2) before the builder can be built.
**Delivers:** RJSF admin form builder (generates questionnaire JSON schema + MAMI code mappings), GoRules JDM Editor React component (admin-facing visual rule editor with save via PUT /admin/rules/{key}), rule engine test/debug mode (sample payload evaluation with per-rule trace output).
**Addresses:** Visual questionnaire builder, business rules engine + visual editor (both P2).
**Avoids:** Visual rule editor as black box (Pitfall 4 — trace output surfaced in admin panel); visual builder output treated as display config only (builder output IS the authoritative schema, must be versioned).
**Research flag:** GoRules JDM Editor React component embedding and save-back API pattern needs research; SurveyJS Creator is excluded (paid license); recommend `/gsd:research-phase` for RJSF builder integration before this phase is planned.

### Phase Ordering Rationale

- **Dependency graph drives order:** MAMI Framework → Questionnaire → Scoring → Report is a hard dependency chain with no shortcuts. Phases 1-4 must be sequential.
- **URL checks are isolated:** The URL subsystem integrates into reports as evidence but is not on the critical path for the first working report. Deferring to Phase 5 allows Phases 1-4 to deliver the core user value without the SSRF complexity blocking progress.
- **Admin is additive:** Admin endpoints read from all data tables but do not produce data used by other components. Phase 6 can be developed partly in parallel with Phase 5.
- **Visual editors are UX on top of stable config:** They must wait for the underlying config schema to be finalized and stable. Phase 7 should not begin until Phase 2 config schemas are confirmed unchanged.
- **Pitfall prevention is woven into phase assignments:** Each pitfall maps to a specific phase where it must be prevented, not retroactively fixed.

### Research Flags

Phases needing deeper research before planning:
- **Phase 3 (Scoring Engine):** GoRules ZEN Python SDK, JDM decision file format, and trace output API are less documented than mainstream Python libraries. Recommend `/gsd:research-phase` for GoRules integration specifics including: Python `zen-engine` API surface, JDM file structure for weighted scoring, and how to wire trace output into FastAPI responses.
- **Phase 7 (Visual Editors):** RJSF admin builder integration (generating questionnaire JSON + MAMI code mapping metadata), save-back API pattern for JDM Editor (PUT /admin/rules/{key}), and versioning workflow for visual-editor-produced schemas need research. Recommend `/gsd:research-phase` before this phase is planned.

Phases with standard, well-documented patterns (skip research-phase):
- **Phase 1 (Foundation):** FastAPI + SQLModel + Alembic + JWT RBAC is a well-documented stack with official tutorials and a reference template (full-stack-fastapi-template).
- **Phase 2 (Questionnaire):** RJSF form rendering + FastAPI answer persistence is a standard JSON Schema form integration.
- **Phase 4 (Reports):** Jinja2 HTML templates + WeasyPrint PDF is a documented workflow with multiple tutorials.
- **Phase 6 (Admin):** Standard CRUD admin endpoints + Recharts dashboard components; no novel integrations.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All Python packages verified against PyPI JSON API with exact versions; npm packages confirmed via WebSearch against official npm registry; version compatibility constraints explicitly verified |
| Features | MEDIUM-HIGH | Table stakes derived from multiple GRC tool sources cross-referenced; P1/P2 split grounded in Briefing.md as authoritative project source of truth; MAMI-specific features have no external comparators to validate against |
| Architecture | MEDIUM-HIGH | Component boundaries and data flows derived from official framework docs (GoRules, RJSF, Microsoft Azure architecture guidance); build order derived from dependency analysis; some lower-level integration specifics (GoRules ZEN Python API, pg-boss configuration) are MEDIUM confidence |
| Pitfalls | MEDIUM-HIGH | SSRF pitfall: HIGH confidence (OWASP + PortSwigger official sources); questionnaire versioning pitfall: MEDIUM confidence (official form framework docs); scoring/comply-or-explain pitfalls: MEDIUM confidence (multiple sources agree); visual editor black-box pitfall: MEDIUM confidence |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **GoRules ZEN Python SDK depth:** The `zen-engine` Python bindings are verified as current (0.51.0) and functional, but the detailed API surface for trace output, JDM file hot-reloading, and Python-specific patterns is not deeply documented in open sources. Address via Phase 3 research spike before implementation begins.
- **RJSF admin builder for MAMI code mapping metadata:** RJSF 6.x supports custom field metadata (uiSchema, extraFormats), but the exact mechanism for attaching MAMI code IDs and MoSCoW levels to question definitions in the visual builder has not been validated against the actual RJSF 6.x API. Address via Phase 7 research spike.
- **pg-boss vs in-process APScheduler for URL check jobs:** APScheduler is recommended for the MVP (no Redis dependency), but pg-boss (Postgres-backed job queue) is mentioned in architecture research as the alternative for under-50-users scale. The choice affects worker process design. Address during Phase 5 planning by confirming whether APScheduler's AsyncIOScheduler within the FastAPI process is sufficient or whether a separate worker process is needed.
- **coe-dsc.nl deployment specifics:** Infrastructure at coe-dsc.nl (container host, reverse proxy, TLS termination) is not captured in research. The Docker Compose setup is appropriate but deployment specifics may require adjustment. Flag for TNO stakeholder validation before Phase 1 is completed.

---

## Sources

### Primary (HIGH confidence)
- PyPI JSON API — FastAPI 0.129.0, SQLModel 0.0.33, httpx 0.28.1, zen-engine 0.51.0, WeasyPrint 68.1, python-jose 3.5.0, Alembic 1.18.4, APScheduler 3.11.2 versions verified
- OWASP SSRF Prevention Cheat Sheet — https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- PortSwigger SSRF tutorial — https://portswigger.net/web-security/ssrf
- SurveyJS Creator commercial license — https://surveyjs.io/licensing (confirmed: Creator requires paid license)
- Briefing.md — project source of truth for MAMI-specific requirements
- Microsoft Azure Web-Queue-Worker Architecture — https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/web-queue-worker

### Secondary (MEDIUM confidence)
- FastAPI + SQLModel + Alembic pattern — https://testdriven.io/blog/fastapi-sqlmodel/
- GoRules ZEN Engine Python SDK — https://docs.gorules.io/developers/sdks/python
- GoRules JDM Editor React component — https://github.com/gorules/jdm-editor
- WeasyPrint + Jinja2 PDF workflow — https://joshkaramuth.com/blog/generate-good-looking-pdfs-weasyprint-jinja2/
- @rjsf/core 6.3.1 — https://www.npmjs.com/package/@rjsf/core
- Vite 7.3.1 — https://vite.dev/releases
- passlib deprecation (FastAPI migration to bcrypt) — https://github.com/fastapi/fastapi/discussions/11773
- GRC tool landscape — Cynomi, Workstreet, ConductorOne, Sprinto sources (multiple sources agree on table stakes)
- SurveyJS Backend Integration — https://surveyjs.io/documentation/backend-integration
- Audit trail immutability — whisperit.ai + hubifi.com (multiple sources agree)

### Tertiary (LOW confidence, needs validation)
- APScheduler vs Celery for FastAPI background tasks — https://procodebase.com/article/mastering-background-tasks-and-scheduling-in-fastapi (pattern aligns with FastAPI official docs; implementation details need verification)
- GoRules trace output wiring in admin UI — inferred from GoRules docs; not validated with working code sample
- pg-boss Postgres-backed job queue for URL worker — pattern consistent with multiple sources; specific configuration not validated

---

*Research completed: 2026-02-14*
*Ready for roadmap: yes*
