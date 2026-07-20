# Stack Research

**Domain:** Compliance Assessment Web Application (Questionnaire + Rule Engine + URL Checking + Report Generation)
**Project:** MAMI Compliance Checker — TNO CoE-DSC
**Researched:** 2026-02-14
**Confidence:** MEDIUM-HIGH (versions verified via PyPI/npm official sources; framework choices verified via multiple credible sources)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | Stable LTS; WeasyPrint 68.1 requires 3.10+; SQLModel 0.0.33 requires 3.9+; avoids passlib/crypt deprecation on 3.13 |
| FastAPI | 0.129.0 | REST API + OpenAPI | Native async, auto-generates OpenAPI 3.x spec, Pydantic v2 built-in — the de facto standard for Python API-first apps in 2025; chosen over Flask (no native async/OpenAPI) and Django REST (heavier, not API-first) |
| SQLModel | 0.0.33 | ORM + Pydantic models | Single class serves as both DB model and API schema — eliminates SQLAlchemy model + Pydantic schema duplication. Same author as FastAPI; requires SQLAlchemy 2.0.x and Pydantic 2.7+ |
| PostgreSQL | 16+ | Primary database | Production-grade; supports JSONB for questionnaire config storage; scales beyond 50 users; SQLite is acceptable for dev/testing only |
| Alembic | 1.18.4 | DB schema migrations | Standard migration tool for SQLAlchemy/SQLModel; autogenerates migration scripts; required for schema-evolving compliance tools |
| Vite + React + TypeScript | Vite 7.3.1 / React 18 / TS 5.x | Frontend SPA | Vite 7.3.1 is current stable; React+TS is the lowest-risk ecosystem for embedding RJSF form builder and GoRules JDM editor; chosen over Next.js (SSR adds complexity not needed for admin tool under 50 users) |

### Questionnaire Layer

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| @rjsf/core | 6.3.1 | JSON Schema-driven form renderer (React) | Apache 2.0 license, freely embeddable in commercial/government tools. Renders dynamic forms from JSON Schema config — config-driven architecture. Questionnaire definitions stored as JSON in DB, rendered by RJSF on frontend. Latest version 6.3.1 (Feb 2026) |
| @rjsf/utils | 6.3.1 | Shared RJSF utilities | Required companion package |
| @rjsf/validator-ajv8 | 6.3.1 | JSON Schema validation | ajv8 is current; ajv6 deprecated. Validates questionnaire input client-side |
| @rjsf/mui | 6.3.1 | Material UI theme for RJSF | Polished default styling; use if using MUI; swap for @rjsf/bootstrap5 if using Bootstrap |

**Why RJSF over SurveyJS Creator:** SurveyJS Form Library is MIT but Survey Creator (the visual builder) requires a paid commercial license — not suitable for an internal tool. RJSF's entire stack (renderer + builder) is Apache 2.0 / open-source with no commercial restrictions.

### Business Rule Engine

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| zen-engine | 0.51.0 | Business rules execution (Python) | GoRules ZEN Engine: Rust-based, Python bindings. Sub-millisecond evaluation of decision tables and rule graphs. JDM (JSON Decision Model) format — rules stored as JSON files in the repo alongside questionnaire config |
| @gorules/jdm-editor | latest | Visual rule editor (React) | Open-source React component from GoRules — provides a drag-and-drop canvas to edit JDM decision graphs. Embeds directly in admin UI. Apache 2.0 license |

**Why ZEN Engine over alternatives:** `business-rules` (PyPI) is unmaintained. Drools/Camunda are Java-only. Python `rule-engine` libraries (Pyke, Intellect) have no visual editor. ZEN Engine is the only open-source Python rule engine with a matching open-source visual editor that stores rules as JSON files — directly satisfying the "config-driven with visual editor" requirement.

**MoSCoW Scoring:** ZEN Engine's decision tables support weighted-score outputs natively — define `Must Have / Should Have / Could Have / Won't Have` scoring rules in the visual editor, ZEN evaluates them at runtime.

### URL Check Subsystem

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| httpx | 0.28.1 | Async HTTP requests | Both sync and async APIs; HTTP/1.1 + HTTP/2; used as the standard async HTTP client in the FastAPI ecosystem. Chosen over aiohttp (async-only, heavier API surface) and requests (sync-only) |
| APScheduler | 3.11.2 | Scheduled URL re-checks | AsyncIOScheduler runs inside the FastAPI process — no separate broker/worker needed. Suitable for <50 users triggering URL checks. Chosen over Celery (requires Redis/RabbitMQ broker — overkill for this scale) |

**URL Check Architecture:** FastAPI endpoint accepts a list of URLs, dispatches async httpx checks (status code + keyword presence via response body search), persists results to DB. APScheduler handles periodic re-checks on a configurable cron schedule.

### Report Generation

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| Jinja2 | 3.x (FastAPI dependency) | HTML report templating | Already a FastAPI transitive dependency; mature templating with loops/conditionals for compliance item tables |
| WeasyPrint | 68.1 | HTML → PDF conversion | Modern CSS support (Flexbox, Grid, page-break); produces publication-quality PDFs from HTML templates; Python 3.10+ required (matches runtime requirement). Actively maintained (July 2025 activity confirmed) |
| Recharts | 3.7.0 | Dashboard charts (React) | React-native SVG charts (not a JS-first lib wrapped for React); declarative component API; MIT license; simpler than Apache ECharts for standard bar/radar charts needed in compliance dashboards |

### Auth & RBAC

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| python-jose | 3.5.0 | JWT token creation and validation | Standard JWT library for FastAPI; supports RS256 and HS256; maintained (May 2025 release) |
| bcrypt | 4.x | Password hashing | Direct bcrypt usage replacing passlib. passlib 1.7.4 (last updated 2020) throws deprecation errors on Python 3.11+ because `crypt` module was removed in Python 3.13. FastAPI's official template (full-stack-fastapi-template) migrated away from passlib to direct bcrypt in late 2024 |
| FastAPI security utilities | built-in | OAuth2 Password Bearer + dependency injection for RBAC | FastAPI's built-in `OAuth2PasswordBearer` + `Depends()` pattern handles USER/ADMIN role checking cleanly without additional libraries |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python package manager and virtualenv | Rust-based, 10-100x faster than pip; `uv sync` replaces `pip install -r requirements.txt`; 2025 standard for new Python projects |
| pytest + httpx | API testing | `httpx.AsyncClient` for async FastAPI endpoint testing; `pytest-asyncio` for async test support |
| docker + docker-compose | Dev environment and deployment | Single `docker-compose.yml` runs API + PostgreSQL + frontend; target deployment matches coe-dsc.nl infrastructure |
| Node.js 22 LTS | Frontend build runtime | Required by Vite 7.3.1 (requires Node 20.19+ or 22.12+) |

---

## Installation

```bash
# --- Python backend ---
# Requires Python 3.11+

# Using uv (recommended)
uv pip install fastapi==0.129.0 sqlmodel==0.0.33 alembic==1.18.4

# Auth
uv pip install "python-jose[cryptography]==3.5.0" bcrypt

# URL checking + scheduling
uv pip install httpx==0.28.1 apscheduler==3.11.2

# Report generation
uv pip install weasyprint==68.1 jinja2

# Rule engine
uv pip install zen-engine==0.51.0

# Dev dependencies
uv pip install --dev pytest pytest-asyncio httpx

# --- Frontend ---
# Requires Node.js 22 LTS

npm create vite@latest frontend -- --template react-ts
cd frontend

# Questionnaire form renderer + builder
npm install @rjsf/core @rjsf/utils @rjsf/validator-ajv8 @rjsf/mui

# Rule editor
npm install @gorules/jdm-editor

# Dashboard charts
npm install recharts

# Dev dependencies
npm install -D typescript @types/react @types/node
```

---

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative |
|----------|-------------|-------------|-------------------------|
| API framework | FastAPI | Django REST Framework | If the project needs Django's admin panel, ORM batteries, or the team is already on Django |
| API framework | FastAPI | Flask | Never for new API-first projects — Flask has no native OpenAPI or async |
| ORM | SQLModel | SQLAlchemy directly | If you need complex ORM features not yet in SQLModel; SQLModel is a thin layer so migration is trivial |
| Database | PostgreSQL | SQLite | Dev/local testing only; SQLite has no JSONB and no concurrent writes |
| Questionnaire builder | @rjsf/core 6.x | SurveyJS Form Library (renderer only) | If visual drag-drop builder is not needed and MIT license is sufficient; SurveyJS renders beautifully but creator needs paid license |
| Rule engine | GoRules ZEN | Custom if/else Python | Only if rules are static and never change — ZEN Engine is the right choice when non-technical admins need to edit rules |
| HTTP client | httpx | aiohttp | Only if you need a persistent HTTP server component; aiohttp is heavier and provides its own server |
| Background tasks | APScheduler | Celery + Redis | Only if concurrent URL checks exceed ~100 per minute and need distributed workers; not applicable at <50 users |
| PDF generation | WeasyPrint | ReportLab / xhtml2pdf | ReportLab has a lower-level API (draw primitives); xhtml2pdf has limited CSS support. WeasyPrint gives best CSS fidelity for designed reports |
| Password hashing | bcrypt | argon2-cffi (pwdlib) | pwdlib with Argon2 is slightly more modern but bcrypt is battle-tested and directly recommended by FastAPI maintainers' own template |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| passlib | Unmaintained since 2020; throws `DeprecationWarning` on Python 3.11 and crashes on Python 3.13 (crypt module removed); FastAPI's official full-stack template already migrated away from it | bcrypt directly or pwdlib |
| react-jsonschema-form (original npm package) | Last published 6 years ago; the project migrated to the `@rjsf/*` scoped packages | @rjsf/core 6.3.1 |
| Create React App | Officially deprecated; Vite 7.x provides the same DX with 58% faster startup | Vite 7.3.1 |
| Drools / OpenL Tablets | Java-only rule engines; no Python SDK | GoRules ZEN Engine |
| Celery (for this project) | Requires Redis or RabbitMQ broker, adds operational complexity; correct choice for distributed task queues at scale but unjustified for <50 users | APScheduler 3.11.2 with AsyncIOScheduler |
| ReportLab | Lower-level PDF drawing API; requires manual layout calculations; WeasyPrint renders HTML/CSS directly | WeasyPrint 68.1 + Jinja2 |
| LimeSurvey / Formstack | External SaaS products; cannot be embedded in the coe-dsc.nl stack or API-controlled programmatically | @rjsf/core + GoRules ZEN |

---

## Stack Patterns by Variant

**If SQLite is used for local dev:**
- Replace `postgresql+asyncpg://` with `sqlite+aiosqlite:///./dev.db` in SQLModel engine config
- Add `aiosqlite` to dev dependencies
- Do not use JSONB column type in dev (SQLite has no JSONB; store JSON as TEXT)

**If report output is HTML-only (no PDF):**
- Drop WeasyPrint from dependencies
- Use Jinja2 with `HTMLResponse` from FastAPI directly
- PDFs can be added later as WeasyPrint wraps the same Jinja2 template

**If visual questionnaire builder is skipped (Phase 1 MVP):**
- Skip @rjsf/core; store questionnaire JSON configs as static YAML/JSON files in the repo
- Render forms client-side with plain React forms using react-hook-form
- Add @rjsf/core visual builder in Phase 2 when admin needs to create new questionnaires

**If admin has no need to edit rules visually:**
- Skip @gorules/jdm-editor from frontend
- Keep zen-engine Python backend — load JDM JSON files from filesystem or DB
- Rules can be hand-edited as JSON and version-controlled in git

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| SQLModel 0.0.33 | SQLAlchemy >=2.0.14,<2.1.0 | SQLAlchemy 2.1.x not yet supported — pin SQLAlchemy to `<2.1.0` |
| SQLModel 0.0.33 | Pydantic >=2.7.0 | Pydantic v1 support was dropped — do NOT mix with libraries requiring Pydantic v1 |
| FastAPI 0.129.0 | Starlette >=0.40.0,<1.0.0 | FastAPI pins Starlette automatically; do not install Starlette independently |
| WeasyPrint 68.1 | Python 3.10, 3.11, 3.12, 3.13 | Requires Python >=3.10; incompatible with Python 3.9 |
| @rjsf/core 6.x | React 17 or 18 | React 19 support not yet confirmed — use React 18 |
| python-jose 3.5.0 | Python 3.9+ | Works with cryptography backend (recommended) or pycryptodome |
| APScheduler 3.11.2 | Python 3.8+ | Use `AsyncIOScheduler` for FastAPI async integration; do NOT use `BackgroundScheduler` in async context |
| Vite 7.3.1 | Node.js 20.19+ or 22.12+ | Node 18 is EOL as of April 2025; use Node 22 LTS |

---

## Sources

- FastAPI 0.129.0 — https://pypi.org/pypi/fastapi/json (verified, HIGH confidence)
- SQLModel 0.0.33 — https://pypi.org/pypi/sqlmodel/json (verified, HIGH confidence)
- httpx 0.28.1 — https://pypi.org/pypi/httpx/json (verified, HIGH confidence)
- zen-engine 0.51.0 — https://pypi.org/pypi/zen-engine/json (verified, HIGH confidence)
- WeasyPrint 68.1 — https://pypi.org/pypi/weasyprint/json (verified, HIGH confidence)
- python-jose 3.5.0 — https://pypi.org/pypi/python-jose/json (verified, HIGH confidence)
- Alembic 1.18.4 — https://pypi.org/pypi/alembic/json (verified, HIGH confidence)
- APScheduler 3.11.2 — https://pypi.org/pypi/apscheduler/json (verified, HIGH confidence)
- @rjsf/core 6.3.1 — https://www.npmjs.com/package/@rjsf/core (WebSearch confirmed, MEDIUM confidence)
- Vite 7.3.1 — https://vite.dev/releases (WebSearch confirmed, MEDIUM confidence)
- Recharts 3.7.0 — https://www.npmjs.com/package/recharts (WebSearch confirmed, MEDIUM confidence)
- GoRules ZEN Engine visual editor — https://gorules.io/ and https://docs.gorules.io/developers/sdks/python (MEDIUM confidence)
- passlib deprecation — https://github.com/fastapi/fastapi/discussions/11773 and https://github.com/fastapi/full-stack-fastapi-template/pull/1539 (MEDIUM confidence, multiple sources agree)
- SurveyJS Creator commercial license — https://surveyjs.io/licensing (HIGH confidence, official source)
- FastAPI + SQLModel + Alembic pattern — https://testdriven.io/blog/fastapi-sqlmodel/ (MEDIUM confidence, verified against official docs)
- httpx vs aiohttp comparison — https://www.speakeasy.com/blog/python-http-clients-requests-vs-httpx-vs-aiohttp (MEDIUM confidence)
- APScheduler vs Celery for FastAPI — https://procodebase.com/article/mastering-background-tasks-and-scheduling-in-fastapi (LOW confidence, WebSearch only; pattern aligns with FastAPI official docs on BackgroundTasks)
- WeasyPrint + Jinja2 PDF workflow — https://joshkaramuth.com/blog/generate-good-looking-pdfs-weasyprint-jinja2/ (MEDIUM confidence, multiple sources agree)

---

*Stack research for: Compliance Assessment Web Application (MAMI Checker)*
*Researched: 2026-02-14*
