# Phase 12: Test Retrofit — Stabilize Existing Flows - Research

**Researched:** 2026-07-22
**Domain:** Backend/frontend test-infrastructure retrofit (pytest + Testcontainers-Postgres + Vitest) and CI bootstrap (GitHub Actions) for a FastAPI/SQLModel/React codebase with zero existing test coverage
**Confidence:** HIGH

## Summary

This phase adds the *first* automated tests this codebase has ever had, targeting exactly three subsystems the v2.0 rebuild will not touch this milestone: auth (`backend/app/api/v1/auth.py`), admin user/initiative management (`backend/app/api/v1/admin.py`), and PDF/email report delivery (`backend/app/api/v1/reports.py` + `backend/app/services/report_generator.py`). Per D-01, tests run against a real Postgres instance via `testcontainers-python`'s `PostgresContainer`, not SQLite — this is a hard requirement because `admin.py` uses raw SQL against Postgres-native features (native `ENUM` on `questionnaire_answer.answer_value`, `pg_insert().on_conflict_do_update()` in `reports.py`) that SQLite cannot faithfully emulate. Per D-02, this is also the phase that creates `.github/` from scratch — no CI exists today.

The central technical wrinkle specific to this codebase: `app.state.zen_engine` and `app.state.mami_config` are populated only by the FastAPI `lifespan` context manager in `backend/app/main.py`, and `admin.py::get_admin_heatmap` and `reports.py`'s report endpoints read `request.app.state.*` directly (not exclusively via `Depends()`). Tests MUST instantiate `TestClient` as a context manager (`with TestClient(app) as client:`) so the lifespan fires and `app.state` is populated with the real `mami-framework.json`/ZEN-engine config — dependency-override alone is insufficient for the admin heatmap endpoint. Because the report/email code path calls the *current* ZEN/MoSCoW scoring engine (not yet replaced — that happens in Phase 14), report/PDF/email tests exercise this real scoring path end-to-end rather than mocking it; only WeasyPrint's `write_pdf()` and Resend's `Emails.send()` are mocked.

**Primary recommendation:** Use `testcontainers-python`'s `PostgresContainer` in a session-scoped pytest fixture as the single source of a real Postgres instance for both local dev and CI (GitHub Actions `ubuntu-latest` runners have Docker preinstalled — no separate `services:` Postgres block is needed, avoiding two parallel DB-provisioning code paths). Build schema via `SQLModel.metadata.create_all(engine)` once per test session (not via Alembic — Alembic revision history isn't the object under test here), wrap each test function in a savepoint/transaction that rolls back for isolation, and use plain pytest fixtures (not `factory_boy`) for the small, hand-authored production-shaped fixture set this phase needs — factory_boy earns its complexity at higher fixture volumes/variation than a characterization-test phase requires.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (Test Database Strategy):** Backend tests run against a real Postgres instance (test container/docker), not SQLite in-memory. Rationale: `admin.py` uses raw SQL and Postgres-native features (native ENUM type, `pg_insert().on_conflict_do_update()` upsert) that SQLite cannot faithfully reproduce — and Phase 13 changes the exact `answer_value` ENUM column this suite needs to catch regressions in. TESTING.md's original SQLite suggestion is superseded by this decision for this project.
- **D-02 (CI Integration):** This phase stands up CI (GitHub Actions) from scratch — no `.github/` directory exists today. The regression suite must run automatically on every PR/push, not just locally. Scope: a workflow that spins up Postgres (service container or equivalent), runs backend pytest and frontend Vitest, and fails the check on any regression.
- **D-03 (Test Data Strategy):** Use synthetic, factory-built fixtures modeled on the production schema shape (multiple initiatives/answers/evidence rows per user) rather than a sanitized export of real production data. "Production-shaped" means schema-realistic fixture data, not an actual data export.
- **D-04 (Bugs Discovered While Writing Tests):** Characterize-only scope. If writing these tests surfaces existing bugs unrelated to the wizard/save issues already scoped for Phase 15, pin the current (even if imperfect) behavior as the test baseline and log the bug as a backlog item — do not fix it inline. Exception: never intentionally test-lock a bug as "correct forever" without logging it clearly for a future phase to decide on.

### Claude's Discretion

- Exact GitHub Actions workflow structure (single job vs. matrix, Postgres service container config, caching strategy for pip/npm) — no specific CI YAML shape was discussed. **This research resolves it: single job for backend, single job for frontend, testcontainers (not a GH `services:` block) for Postgres — see Architecture Patterns.**
- Specific fixture factory design (`pytest` fixtures vs. `factory_boy`) — left to planning. **This research resolves it: plain pytest fixtures — see Standard Stack / Alternatives Considered.**

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. Fixing bugs discovered during this phase's test-writing is explicitly deferred per D-04 (logged as backlog items, not lost).

## Phase Requirements

No REQ-IDs from `.planning/REQUIREMENTS.md` map to this phase — it is a foundational safety-net phase with no v1 requirement of its own (confirmed in REQUIREMENTS.md's Traceability note: "Phase 12 ... maps no v1 requirement directly"). Planning should instead trace tasks to the four ROADMAP.md success criteria listed in the phase description (auth coverage, admin/CSV coverage, PDF/email coverage, CI speed/signal), not to REQ-IDs.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Auth regression tests (register/login/lockout/reset) | API / Backend | Database | `auth.py` endpoints are pure FastAPI route handlers backed by Postgres (`User` model); no frontend logic under test here |
| Admin cascade-delete + CSV export tests | API / Backend | Database | `admin.py` raw-SQL endpoints operate directly against Postgres; testing them without a real Postgres instance (D-01) would test a fiction |
| PDF/email regression test | API / Backend | External service boundary (mocked) | `report_generator.py` + WeasyPrint run in-process; Resend is an external HTTP boundary that must be mocked, not hit live |
| Test database provisioning | CI / Local tooling | Database | `testcontainers-python` and/or GH Actions Docker daemon — infrastructure tier, not app code |
| CI orchestration (GitHub Actions) | CI / Local tooling | — | New `.github/workflows/*.yml`; no application-tier code |
| Frontend component/unit tests (Vitest) | Browser / Client | — | Out of primary scope for Phase 12 per CONTEXT.md ("No questionnaire, scoring, or wizard code is touched") — CI wiring for Vitest is in scope (D-02) even though no new frontend test *content* is mandated by success criteria 1-3 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pytest` | 9.1.1 | Backend test runner | Ecosystem standard for Python; already the plan in `.planning/codebase/TESTING.md` and `.planning/research/STACK.md`. [VERIFIED: PyPI registry] |
| `pytest-asyncio` | 1.4.0 | Async test support | `reports.py` endpoints are `async def` (they `await score_all_answers(...)`); set `asyncio_mode = "auto"` in `pyproject.toml` so async test functions run without per-test markers. [VERIFIED: PyPI registry] |
| `pytest-cov` | 7.1.0 | Coverage reporting | Matches the 70%/90%(security-critical) targets in TESTING.md. [VERIFIED: PyPI registry] |
| `pytest-mock` | 3.15.1 | Mocking (`mocker` fixture) | For mocking Resend's `Emails.send` and WeasyPrint's `write_pdf` — avoids real network/PDF-render calls in CI. [VERIFIED: PyPI registry] |
| `testcontainers` (`testcontainers[postgres]`) | 4.14.2 | Ephemeral real-Postgres instance for tests | Implements D-01 directly — spins up `postgres:16-alpine` (matching `docker-compose.yml`'s pinned image) in a Docker container per test session, giving true Postgres semantics (native ENUM, `ON CONFLICT`) that SQLite cannot. Official `testcontainers-python` org repo, actively maintained. [VERIFIED: PyPI registry + GitHub org repo] |
| `vitest` | 4.1.10 | Frontend test runner (CI wiring only, per D-02) | Peer dep `vite: "^6.0.0 \|\| ^7.0.0 \|\| ^8.0.0"` matches this project's Vite 7.3.1 exactly; already the confirmed choice in `.planning/research/STACK.md`. [VERIFIED: npm registry] |
| `@testing-library/react` | 16.3.2 | Component test utilities (CI wiring only) | Peer dep confirms React 19 support (`react: "^18.0.0 \|\| ^19.0.0"`). [VERIFIED: npm registry] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` | 0.28.1 | Async HTTP client for backend tests | Only if a test needs true async concurrency or must exercise FastAPI lifespan via `ASGITransport` outside `TestClient`. For the majority of this phase's endpoint tests, synchronous `fastapi.testclient.TestClient` (httpx-based since FastAPI ≥0.115) is sufficient and simpler. [VERIFIED: PyPI registry] |
| `faker` | 40.32.0 | Realistic fake data generation for fixtures | Pairs with plain pytest fixtures to generate schema-realistic (D-03) emails/names/organizations without hardcoding repetitive literals across fixture functions. [VERIFIED: PyPI registry] |
| `@vitest/coverage-v8` | 4.1.10 | Frontend coverage (CI wiring only) | V8-native coverage, no extra instrumentation step. [VERIFIED: npm registry] |
| `jsdom` | 29.1.1 | DOM environment for Vitest (CI wiring only) | Broader DOM-spec coverage than `happy-dom`; matters if any antd v6 component test is added later. [VERIFIED: npm registry] |
| `@testing-library/jest-dom` | 7.0.0 | Extra Vitest/Jest-compatible matchers | Only needed once actual component tests exist — not required for Phase 12's CI-wiring-only frontend scope, but install now so Phase 17 doesn't need a second setup pass. [VERIFIED: npm registry] |
| `@testing-library/user-event` | 14.6.1 | Realistic interaction simulation | Same rationale as above — install now for CI parity with the Phase 17 stack. [VERIFIED: npm registry] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `testcontainers-python` (session-scoped, spun up by pytest itself) | GitHub Actions `services:` Postgres block + local `docker-compose up db` | GH `services:` requires maintaining Postgres config twice (workflow YAML + docker-compose.yml) and gives local devs a *different* provisioning path (manual `docker compose up`) than CI (automatic service container) — two code paths to keep in sync. Testcontainers unifies both into one Python fixture; the only real downside is a few extra seconds per CI run to pull/start the Postgres image (mitigated by GH Actions' layer caching of the `postgres:16-alpine` image across runs). |
| Plain pytest fixtures for test data (D-03) | `factory_boy` (`SQLAlchemyModelFactory` + SQLModel session) | `factory_boy` pays off once you need many *variations* of the same model shape across dozens of tests (traits, sub-factories, `RelatedFactory`). This phase's fixture surface is small and fixed (a handful of users/initiatives/answers/evidence rows per success criterion) — plain fixtures plus `faker` for realistic values keep the setup legible without adding a new DSL to a codebase that has zero test infrastructure today. Revisit `factory_boy` in Phase 17 if the new-scoring test suite needs many answer-set permutations. |
| `httpx.AsyncClient` as the default test client | `fastapi.testclient.TestClient` (sync) | `TestClient` already wraps httpx since FastAPI ≥0.115 and is simpler for the large majority of this phase's endpoint tests (register, login, lockout, cascade-delete, CSV export, PDF/email). Reserve `httpx.AsyncClient(transport=ASGITransport(app=app))` + `asgi-lifespan`'s `LifespanManager` only if a specific test needs concurrent-request racing. |
| `SQLModel.metadata.create_all()` for test schema | Running real Alembic migrations (`alembic upgrade head`) against the testcontainer | Running actual migrations is more production-faithful and would catch migration bugs, but this phase's job is characterizing *current app behavior*, not migration correctness — `create_all()` is faster per test-session start and avoids coupling this test suite's setup time to the (currently 10-migration-deep, soon-to-add-more) Alembic history. Reconsider real migrations specifically for Phase 13's ENUM→data-model change, where the migration itself is the thing being verified (per PITFALLS.md Pitfall 3). |

**Installation:**
```bash
# Backend (from backend/)
uv add --dev pytest pytest-asyncio pytest-cov pytest-mock httpx faker
uv add --dev "testcontainers[postgres]"

# Frontend (from frontend/)
npm install -D vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

**Version verification:** All versions above were confirmed live against the PyPI JSON API (`https://pypi.org/pypi/<pkg>/json`) and `npm view <pkg> version` on 2026-07-22 — see the Package Legitimacy Audit below for per-package registry/repo/downloads data.

## Package Legitimacy Audit

| Package | Registry | Age (first vs. latest publish) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|---------------------------------|-----------|--------------|---------|-------------|
| `pytest` | PyPI | Multi-year project (latest release 2026-06-19) | Not exposed by PyPI download-stats API (checker signal: `unknown-downloads`) | `github.com/pytest-dev/pytest` | SUS (checker) | **Approved — false-positive.** PyPI ecosystem downloads are not exposed to the legitimacy checker at all (every PyPI package in this audit hits the same `unknown-downloads` reason); this is a checker-ecosystem limitation, not a per-package signal. `pytest-dev` org, canonical Python test-runner, already the confirmed choice in `.planning/research/STACK.md`. No checkpoint needed. |
| `pytest-asyncio` | PyPI | Multi-year (latest 2026-05-26) | `unknown-downloads` (same limitation) | `github.com/pytest-dev/pytest-asyncio` | SUS (checker) | **Approved — false-positive**, same reasoning. |
| `pytest-cov` | PyPI | Multi-year (latest 2026-03-21) | `unknown-downloads` | No `repoUrl` returned by checker (PyPI metadata field gap — repo is `github.com/pytest-dev/pytest-cov`, confirmed via WebSearch) | SUS (checker) | **Approved — false-positive.** Verify repo URL manually if in doubt: `github.com/pytest-dev/pytest-cov`. |
| `pytest-mock` | PyPI | Multi-year (latest 2025-09-16) | `unknown-downloads` | `github.com/pytest-dev/pytest-mock/` | SUS (checker) | **Approved — false-positive.** |
| `httpx` | PyPI | Multi-year (latest 2024-12-06) | `unknown-downloads` | `github.com/encode/httpx` | SUS (checker) | **Approved — false-positive.** `encode` org (also maintains Starlette/Uvicorn — FastAPI's own stack). |
| `faker` | PyPI | Multi-year, very frequent releases (latest 2026-07-20 — 2 days before this research) | `unknown-downloads` | `github.com/joke2k/faker` | SUS (checker: `too-new`, `unknown-downloads`) | **Approved — false-positive.** "too-new" reflects the *latest patch's* publish date (faker ships near-weekly locale/data updates), not the package's actual age (10+ years). Pin an exact version in `pyproject.toml` (`faker==40.32.0`) rather than accepting floating `*` to avoid picking up a same-day release untested by this research. |
| `testcontainers` (`testcontainers[postgres]`) | PyPI | Latest 2026-03-18 | `unknown-downloads` | `github.com/testcontainers/testcontainers-python` | SUS (checker) | **Approved — false-positive.** Official `testcontainers` GitHub org (same org publishing Java/Go/Node testcontainers variants used industry-wide), canonical answer for D-01's real-Postgres-in-tests requirement. |
| `vitest` | npm | Latest 2026-07-06 | 79.3M/week | `github.com/vitest-dev/vitest` | SUS (checker: `too-new`) | **Approved — false-positive.** 79M weekly downloads contradicts any legitimacy concern; "too-new" is purely the latest-release-date heuristic on a package that ships frequent point releases. |
| `@vitest/coverage-v8` | npm | Latest 2026-07-06 | 30.3M/week | `github.com/vitest-dev/vitest` (monorepo) | SUS (checker: `too-new`) | **Approved — false-positive**, same reasoning as `vitest`. |
| `jsdom` | npm | Latest 2026-04-30 | 82.2M/week | `github.com/jsdom/jsdom` | OK | Approved. |
| `@testing-library/react` | npm | Latest 2026-01-19 | 47.6M/week | `github.com/testing-library/react-testing-library` | OK | Approved. |
| `@testing-library/jest-dom` | npm | Latest 2026-07-20 (2 days before this research) | 53.3M/week | `github.com/testing-library/jest-dom` | SUS (checker: `too-new`) | **Approved — false-positive**, same "frequent releases on a huge package" pattern as `vitest`. |
| `@testing-library/user-event` | npm | Latest 2025-01-21 | 41.3M/week | `github.com/testing-library/user-event` | OK | Approved. |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]` by the automated checker:** all PyPI packages in this audit (checker-wide `unknown-downloads` limitation for the PyPI ecosystem) plus `vitest`, `@vitest/coverage-v8`, `@testing-library/jest-dom` on npm (all flagged solely for a recent *latest-version* publish date despite tens of millions of weekly downloads). **None of these represent a real legitimacy concern** — every flagged package has a canonical, matching GitHub org/repo and (where the ecosystem exposes it) download counts in the tens of millions per week. Per protocol these are still SUS verdicts from the mechanical checker; the planner should add a single lightweight `checkpoint:human-verify` covering "confirm `uv add`/`npm install` output matches the versions/repos in this table" before the first install task, rather than one checkpoint per package — the audit above already provides the verification evidence.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  GitHub Actions Workflow (.github/workflows/test.yml)               │
│  Trigger: push, pull_request                                        │
│                                                                       │
│  ┌───────────────────────┐        ┌───────────────────────────────┐ │
│  │ Job: backend-tests    │        │ Job: frontend-tests            │ │
│  │ runs-on: ubuntu-latest│        │ runs-on: ubuntu-latest         │ │
│  │ (Docker preinstalled) │        │                                 │ │
│  │                       │        │  actions/setup-node (Node 20)  │ │
│  │ astral-sh/setup-uv    │        │  npm ci (cached)               │ │
│  │  → uv sync --locked   │        │  npm test -- --run             │ │
│  │                       │        │  (Vitest, no watch mode in CI) │ │
│  │ pytest                │        └───────────────────────────────┘ │
│  │  ├─ conftest.py       │                                          │
│  │  │   session fixture: │                                          │
│  │  │   PostgresContainer│◄── testcontainers spins up its own       │
│  │  │   ("postgres:16-   │    Docker container via the runner's     │
│  │  │    alpine")        │    already-present Docker daemon —       │
│  │  │                    │    no GH Actions `services:` block used  │
│  │  ├─ SQLModel.metadata │                                          │
│  │  │   .create_all()    │                                          │
│  │  ├─ per-test fixtures │                                          │
│  │  │   (users, initiat- │                                          │
│  │  │    ives, answers)  │                                          │
│  │  │                    │                                          │
│  │  ├─ TestClient(app)   │──► FastAPI app.lifespan fires:            │
│  │  │   as context mgr   │    app.state.mami_config,                 │
│  │  │                    │    app.state.zen_engine populated         │
│  │  │                    │    from real config/ files                │
│  │  │                    │                                          │
│  │  ├─ auth tests ───────┼──► register/login/lockout/reset           │
│  │  ├─ admin tests ──────┼──► cascade-delete, CSV export, list users │
│  │  └─ report tests ─────┼──► generate → mock WeasyPrint.write_pdf   │
│  │                       │    → mock resend.Emails.send              │
│  │                       │    → assert both called with right args   │
│  └───────────────────────┘                                          │
│                                                                       │
│  Both jobs must pass → PR merge check green                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
backend/
├── app/                        # unchanged
├── pyproject.toml              # add [tool.pytest.ini_options] + test deps
└── tests/
    ├── conftest.py              # postgres_container, engine, session, client fixtures
    ├── factories.py             # plain fixture factory functions (not factory_boy)
    ├── api/
    │   ├── test_auth.py         # register, login, lockout, forgot/reset password
    │   ├── test_admin.py        # list_users, cascade-delete, CSV export, reset-demo
    │   └── test_reports.py      # generate_report, download_report_pdf, mail_report
    └── services/
        └── test_report_generator.py   # generate_html_report/_data unit-level, no HTTP

frontend/
├── vitest.config.ts             # new — jsdom environment, globals: true
└── src/                         # co-located *.test.tsx as tests are added (Phase 17 scope)

.github/
└── workflows/
    └── test.yml                 # backend-tests + frontend-tests jobs
```

### Pattern 1: Session-scoped real-Postgres fixture via testcontainers

**What:** One `PostgresContainer` per pytest session, one SQLAlchemy engine bound to it, per-test transactional isolation via nested transaction + rollback.
**When to use:** Every backend test in this phase (D-01 mandates real Postgres for all of them, not just the admin/ENUM-touching ones, for consistency and to avoid a two-database-backend test suite).
**Example:**
```python
# backend/tests/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def engine(postgres_container):
    url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql"
    )
    eng = create_engine(url)
    SQLModel.metadata.create_all(eng)
    return eng

@pytest.fixture
def session(engine):
    """Each test runs inside its own connection + outer transaction,
    rolled back at teardown — keeps tests isolated without recreating
    tables (and without hitting the ENUM drop/recreate pitfall below)."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(session, monkeypatch):
    from app.main import app
    from app.db.session import get_session

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    # Use TestClient as a context manager so app.lifespan() actually
    # runs and populates app.state.mami_config / app.state.zen_engine —
    # required because admin.py and reports.py read request.app.state
    # directly, not only via Depends().
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

### Pattern 2: Characterization test for existing (imperfect) behavior — per D-04

**What:** Assert on the CURRENT status code/response shape, even if it reveals a latent bug, and separately log a backlog item for anything genuinely wrong.
**When to use:** Any test where the "correct" behavior is ambiguous or where CONCERNS.md already flagged fragility (bare except in `reports.py`, manual cascade order in `admin.py`).
**Example:**
```python
# backend/tests/api/test_auth.py
def test_account_lockout_after_five_failed_attempts(client, registered_user):
    for _ in range(5):
        r = client.post("/api/v1/auth/login", data={
            "username": registered_user.email, "password": "WrongPass1234!",
        })
        assert r.status_code == 401

    # 6th attempt: current behavior locks the account for 15 minutes
    r = client.post("/api/v1/auth/login", data={
        "username": registered_user.email, "password": "WrongPass1234!",
    })
    assert r.status_code == 423
    assert "locked" in r.json()["detail"].lower()

def test_forgot_password_always_returns_202_even_for_unknown_email(client):
    # Characterizes current anti-enumeration behavior (auth.py forgot_password) —
    # this is intended, not a bug: response must never reveal whether the
    # email is registered.
    r = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 202
```

### Pattern 3: Mocking WeasyPrint + Resend without hitting real services

**What:** Patch at the point of use (`app.api.v1.reports.WeasyHTML`, `app.api.v1.reports.resend.Emails.send`), not at the point of definition.
**When to use:** Every PDF/email test — never let a test suite call the real Resend API or spend seconds rendering a real PDF.
**Example:**
```python
# backend/tests/api/test_reports.py
from unittest.mock import MagicMock

def test_mail_report_generates_pdf_and_sends_email(client, mocker, initiative_with_answers):
    mock_write_pdf = mocker.patch(
        "app.services.report_generator"  # patched via the reports module's local import
    )
    # WeasyPrint is imported lazily inside _send_report_email — patch where it's
    # imported *into*, i.e. patch the weasyprint module's HTML class before the
    # lazy import resolves it:
    mock_html_cls = mocker.patch("weasyprint.HTML")
    mock_html_cls.return_value.write_pdf.return_value = b"%PDF-FAKE-BYTES"

    mock_send = mocker.patch("resend.Emails.send")

    r = client.post(f"/api/v1/initiatives/{initiative_with_answers.id}/report/mail")
    assert r.status_code == 202

    # _send_report_email runs as a FastAPI BackgroundTask — TestClient executes
    # background tasks synchronously before the response context exits, so
    # assertions below are safe without extra waiting/polling.
    mock_html_cls.return_value.write_pdf.assert_called_once()
    mock_send.assert_called_once()
    sent_kwargs = mock_send.call_args[0][0]
    assert sent_kwargs["attachments"][0]["filename"] == "MAMI-Interoperability-Report.pdf"
```
**Note on lazy import:** `reports.py::_send_report_email` does `from weasyprint import HTML as WeasyHTML` *inside* the function body (deferred import, per STATE.md's "[Phase 11]: WeasyPrint import deferred inside `_send_report_email` for lazy loading"). Patch `weasyprint.HTML` directly (the module-level target), not `app.api.v1.reports.WeasyHTML` — the local alias doesn't exist until the function executes, so patching the reports-module attribute will silently no-op.

### Pattern 4: Admin cascade-delete test against real FK ordering

**What:** Seed an initiative with answers + evidence + a report row, delete the user, assert zero orphaned child rows remain in Postgres directly (not just a 200 response).
**When to use:** Success criterion 2 — cascade-delete is exactly the fragile manual-FK-order code CONCERNS.md flags.
**Example:**
```python
# backend/tests/api/test_admin.py
from sqlmodel import select
from app.models.questionnaire import QuestionnaireAnswer
from app.models.evidence import EvidenceURL
from app.models.report import ComplianceReport

def test_delete_user_cascades_all_child_rows(client, session, admin_client, user_with_full_initiative):
    initiative_id = user_with_full_initiative.initiative.id
    user_id = user_with_full_initiative.user.id

    r = admin_client.delete(f"/api/v1/admin/users/{user_id}")
    assert r.status_code == 200

    assert session.exec(
        select(QuestionnaireAnswer).where(QuestionnaireAnswer.initiative_id == initiative_id)
    ).all() == []
    assert session.exec(
        select(EvidenceURL).where(EvidenceURL.initiative_id == initiative_id)
    ).all() == []
    assert session.exec(
        select(ComplianceReport).where(ComplianceReport.initiative_id == initiative_id)
    ).all() == []
```

### Anti-Patterns to Avoid

- **Recreating the schema (`drop_all()` + `create_all()`) between test modules:** Postgres native ENUM types (`answervalue`) are not cleanly dropped/recreated by SQLAlchemy's `drop_all()` in all code paths — repeated drop/create against the *same* long-lived container across a session can raise `type "answervalue" already exists`. Use one `create_all()` per session (Pattern 1) and isolate tests via transaction rollback instead of schema teardown.
- **Testing the admin heatmap or report endpoints via dependency-override alone, without lifespan:** `request.app.state.mami_config` / `request.app.state.zen_engine` are only populated by `app.main.py`'s `lifespan()`. A `TestClient(app)` instantiated *not* as a context manager (`client = TestClient(app)` then calling `.get(...)` directly) will raise `AttributeError` on `app.state.mami_config` the first time `get_admin_heatmap` or any report endpoint runs, because lifespan startup never fired.
- **Mocking `score_all_answers`/ZEN engine in the PDF/email tests:** Per D-04 (characterize current behavior) and because Phase 14 hasn't replaced scoring yet, let the real (current) ZEN/MoSCoW scoring path run in these tests — only the *external* boundaries (WeasyPrint's actual PDF byte-rendering, Resend's HTTP call) should be mocked. Mocking the scoring engine too would make these into pure unit tests of PDF/email plumbing and lose the "does report generation still work end-to-end" characterization value.
- **One `checkpoint:human-verify` per SUS-flagged package:** Given all 13 packages evaluated in this phase's audit are flagged `SUS` purely due to checker-ecosystem limitations (see Package Legitimacy Audit), don't burn a separate checkpoint per package — use one combined verification step for the dependency-install task.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ephemeral real-Postgres instance for tests | A bespoke Docker-Compose-based pytest plugin, or a hand-rolled `subprocess.run(["docker", "run", ...])` fixture | `testcontainers[postgres]`'s `PostgresContainer` | Handles container readiness polling, port mapping, and cleanup-on-exit/interrupt correctly — a hand-rolled version reliably misses at least one of these (e.g., orphaned containers on `Ctrl-C`). |
| Test data generation with realistic-looking values | Hardcoded literal strings repeated across every fixture function | `faker` | D-03 asks for "production-shaped" data (multiple initiatives/answers/evidence rows); `faker` gives varied, realistic-looking emails/org names without maintaining a literal-string library by hand. |
| Mocking an external SDK's HTTP call | Writing a fake HTTP server or stubbing `requests`/`httpx` at the transport layer for Resend | `pytest-mock`'s `mocker.patch("resend.Emails.send")` | Resend's SDK is a thin wrapper the code already calls directly (`resend.Emails.send(params)`); patching the function is simpler and faster than standing up a fake server, and tests exactly what the code path calls. |
| CI Postgres provisioning | Hand-written GitHub Actions Postgres `services:` YAML block *and* a separate local docker-compose invocation kept in sync by hand | `testcontainers-python`, invoked identically by pytest in both environments | One code path (Python, versioned alongside the tests) instead of two YAML/compose configs that can drift. |

**Key insight:** Every "don't hand-roll" item above exists because this codebase is retrofitting tests onto already-shipped, Postgres-native-feature-dependent code (ENUMs, upserts) — the temptation in a zero-test-infrastructure codebase is to reach for the *simplest possible* thing (SQLite, a fake email server, manual Docker commands) precisely where D-01/D-03 already ruled that out for good reason.

## Common Pitfalls

### Pitfall 1: `app.state` lifespan dependency breaks naive TestClient usage

**What goes wrong:** Any test hitting `get_admin_heatmap`, `generate_report`, `download_report_pdf`, or `mail_report` raises an `AttributeError` (`'State' object has no attribute 'mami_config'`) if `TestClient` wasn't used as a context manager.
**Why it happens:** `backend/app/main.py`'s `lifespan()` async context manager populates `app.state.mami_config`, `app.state.questionnaire_config(s)`, and `app.state.zen_engine` — this only runs when Starlette's lifespan protocol is triggered, which `TestClient` only does inside a `with` block.
**How to avoid:** Always instantiate `with TestClient(app) as client:` (see Pattern 1's `client` fixture) — never `client = TestClient(app)` as a bare assignment.
**Warning signs:** Tests pass for `auth.py` endpoints (no `app.state` dependency) but fail with `AttributeError` specifically on admin-heatmap or any report endpoint.

### Pitfall 2: Lazy-imported WeasyPrint can't be patched at its call-site alias

**What goes wrong:** `mocker.patch("app.api.v1.reports.WeasyHTML")` silently does nothing (the mock is never actually called), and `write_pdf()` runs for real, slowing tests and requiring WeasyPrint's system libraries (`libpango`, `libcairo`, etc.) to be installed in CI.
**Why it happens:** `from weasyprint import HTML as WeasyHTML` happens *inside* `_send_report_email` and `download_report_pdf` (deferred/lazy import, per STATE.md), so there is no module-level `app.api.v1.reports.WeasyHTML` attribute to patch until the function body executes — by then the patch target resolution has already failed to intercept it.
**How to avoid:** Patch `weasyprint.HTML` directly (see Pattern 3) — this intercepts the class at its source module, which the lazy `from weasyprint import HTML` import will pick up correctly regardless of when it executes.
**Warning signs:** Mocked PDF tests take multiple seconds to run (WeasyPrint is actually rendering) or CI fails with a missing-system-library error (`libpangocairo`) that only a real `write_pdf()` call would trigger.

### Pitfall 3: FastAPI `BackgroundTasks` exceptions are invisible to the test's HTTP assertion

**What goes wrong:** `mail_report` returns `202` immediately and the actual PDF-generation/email-send happens in a `BackgroundTask` — if a test only asserts `response.status_code == 202`, it will pass even if `_send_report_email` silently swallowed an exception on the bare `except Exception:` (CONCERNS.md's flagged fragility).
**Why it happens:** `TestClient` (Starlette's) does run background tasks synchronously as part of processing the request/response cycle, but any exception a background task raises is caught by `_send_report_email`'s own bare-except (or would otherwise be a "silent" outcome invisible in the response body) — the response body genuinely never reflects it.
**How to avoid:** Don't just assert `202` — assert the mocked `write_pdf`/`Emails.send` calls actually happened (Pattern 3's final assertions) so the test would fail loudly if the background task's internals changed/broke, not just if the endpoint stopped returning 202.
**Warning signs:** A "green" PDF/email test suite that never actually verifies WeasyPrint or Resend were invoked — passes even if the background task body is deleted entirely.

### Pitfall 4: Rate limiter / account lockout interferes with rapid characterization tests

**What goes wrong:** `login`'s `@limiter.limit("10/minute")` (in `auth.py`) can be tripped by a test file running many login attempts in quick succession (e.g., a lockout test doing 6 logins, followed immediately by another test file's own login attempts within the same minute window), producing an intermittent 429 that looks like test flakiness.
**Why it happens:** `slowapi`'s in-memory limiter is keyed by client IP (`get_remote_address`) and is shared process-wide across the whole pytest session unless reset between tests — this is the same root cause flagged in PITFALLS.md's Pitfall 11 for Playwright E2E, but applies here too at the pytest level since `TestClient` requests all originate from the same "IP."
**How to avoid:** Either (a) reset/clear the limiter's storage between tests (`app.state.limiter.reset()` if exposed, or re-instantiate the `Limiter` per test module), or (b) group lockout/rate-limit-sensitive tests together and keep the total login-attempt count per test file comfortably under the configured limits, documenting the assumption in a comment.
**Warning signs:** `test_account_lockout_after_five_failed_attempts` passes in isolation (`pytest tests/api/test_auth.py::test_account_lockout...`) but fails when the full suite runs (`pytest`) due to a 429 instead of the expected 401/423.

### Pitfall 5: `pg_insert().on_conflict_do_update()` in report generation requires a real unique constraint to exist

**What goes wrong:** `generate_report`'s upsert (`ComplianceReport`, `on_conflict_do_update(index_elements=["initiative_id"])`) only works if the `initiative_id` column actually has a unique index/constraint in the test database — which it does via `SQLModel`'s `unique=True` on the field (`ComplianceReport.initiative_id`), but this is easy to silently break if a future schema-evolution test helper builds a partial or custom schema instead of using the full `SQLModel.metadata.create_all(engine)`.
**Why it happens:** SQLite (what TESTING.md originally suggested) is more forgiving of constraint mismatches in some cases; Postgres will raise `there is no unique or exclusion constraint matching the ON CONFLICT specification` immediately and loudly if the constraint is missing — which is actually a *good* thing (D-01's whole point), but only if the test fixture actually builds the complete schema.
**How to avoid:** Always build the schema from the full `SQLModel.metadata` (Pattern 1), never a hand-picked subset of tables, when testing anything that touches `ComplianceReport`'s upsert path.
**Warning signs:** `psycopg2.errors.InvalidColumnReference` or the SQLAlchemy-wrapped equivalent when calling `generate_report` in a test — signals the test schema is incomplete, not that the app code regressed.

## Code Examples

### `pyproject.toml` test configuration
```toml
# Source: pytest-asyncio docs (asyncio_mode) + this codebase's backend/pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[project.optional-dependencies]
dev = [
    "pytest>=9.1.1",
    "pytest-asyncio>=1.4.0",
    "pytest-cov>=7.1.0",
    "pytest-mock>=3.15.1",
    "testcontainers[postgres]>=4.14.2",
    "faker>=40.32.0",
    "httpx>=0.28.1",
]
```

### CSV export characterization test (admin.py `export_dataset`)
```python
# backend/tests/api/test_admin.py
import csv
import io

def test_export_dataset_csv_shape(admin_client, user_with_full_initiative):
    r = admin_client.get("/api/v1/admin/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")

    reader = csv.reader(io.StringIO(r.text))
    header = next(reader)
    # Characterizes the CURRENT column set (per D-04) — Phase 13's schema
    # swap will need to update this test deliberately, not accidentally.
    assert header == [
        "user_email", "initiative_name", "participant_type", "initiative_status",
        "question_id", "mami_code", "answer_value", "followup_selections", "followup_other",
    ]
    rows = list(reader)
    assert len(rows) == len(user_with_full_initiative.answers)
```

### GitHub Actions workflow (`.github/workflows/test.yml`)
```yaml
# Source: GitHub Docs (creating-postgresql-service-containers), astral-sh/setup-uv docs,
# Docker Docs (testcontainers-python-getting-started) — cross-checked 2026-07-22
name: Test Suite

on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend-tests:
    runs-on: ubuntu-latest   # Docker daemon preinstalled — no `services:` Postgres
                             # block needed; testcontainers manages its own container.
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v7

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
          cache-dependency-glob: "backend/uv.lock"

      - name: Install dependencies
        run: uv sync --locked --all-extras

      - name: Run pytest
        run: uv run pytest --cov=app --cov-report=term-missing
        env:
          # testcontainers needs the Docker socket — already present on
          # ubuntu-latest; no extra env var required for the default case.
          TESTCONTAINERS_RYUK_DISABLED: "false"

  frontend-tests:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v7

      - uses: actions/setup-node@v7
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - run: npm ci
      - run: npx vitest run --coverage
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No test framework at all | pytest + pytest-asyncio + testcontainers (backend), Vitest + RTL (frontend) | This phase (2026-07-22) | First automated regression coverage this codebase has ever had |
| No CI | GitHub Actions, `.github/workflows/test.yml` | This phase | Merges to `main`/PRs now get an automated pass/fail signal instead of relying on manual verification |
| SQLite in-memory (as originally suggested in TESTING.md, 2026-07-20) | Real Postgres via `testcontainers-python` (D-01) | Superseded same week, once `admin.py`'s raw-SQL/ENUM dependency was analyzed in CONCERNS.md/PITFALLS.md | Tests now faithfully catch native-ENUM and `ON CONFLICT` regressions that SQLite would silently pass through incorrectly |

**Deprecated/outdated:**
- TESTING.md's SQLite-in-memory recommendation for backend tests: superseded by D-01 for this project specifically (SQLite remains fine advice in general, just not for this codebase's Postgres-native-feature usage).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | GitHub Actions `ubuntu-latest` runners have Docker preinstalled and usable by `testcontainers-python` without extra setup steps | Architecture Patterns, Code Examples (workflow YAML) | If wrong (e.g., a runner policy change or use of a self-hosted/ARM runner without Docker), the backend-tests job would fail immediately at container startup — low risk since this is a long-standing, well-documented GitHub Actions runner behavior [CITED: GitHub Docs — creating-postgresql-service-containers], but flagging since it wasn't re-verified against a live GH Actions run in this research session. |
| A2 | Testcontainers-in-CI (no GH `services:` block) is preferable to a GH Actions `services:` Postgres block for this project | Standard Stack — Alternatives Considered | If the team later finds testcontainers flaky specifically in GH Actions (e.g., nested-virtualization edge cases on certain runner types), falling back to a `services:` Postgres block is a well-trodden, documented alternative — low switching cost, not a one-way door. |
| A3 | `SQLModel.metadata.create_all()` is sufficient test-schema setup and real Alembic migrations are not needed for this phase's tests | Standard Stack — Alternatives Considered, Pitfall 5 | If a future migration introduces a behavior `create_all()` doesn't replicate (e.g., a data-backfill step), tests could pass against a schema that doesn't match what a real `alembic upgrade head` produces. Low risk for Phase 12 (no migrations are being written in this phase), reconsider for Phase 13. |
| A4 | The local development machine (this repo's checkout) does not currently have Docker installed — a real gap for D-01's local-testing requirement, not just a CI concern | Environment Availability | If a developer runs `pytest` locally without Docker Desktop/Colima/Podman installed, `testcontainers-python` will fail immediately with a "Could not find a valid Docker environment" error — this needs an explicit setup step/README note in this phase's plan, not just a CI-side fix. |

**If this table is empty:** N/A — see entries above.

## Open Questions

1. **Should Vitest test *content* be added in Phase 12, or is CI wiring (config + empty/smoke test) sufficient?**
   - What we know: CONTEXT.md's `<domain>` section states "No new user-facing capability is added here. No questionnaire, scoring, or wizard code is touched," and the four ROADMAP.md success criteria (in the phase description) don't mention any frontend behavior — they're all backend (auth/admin/PDF-email) plus "this suite runs quickly." D-02 does require the workflow to "run backend pytest **and** frontend Vitest."
   - What's unclear: Whether "runs frontend Vitest" requires *any* real frontend test file to exist yet, or just a working, green `npm run test` command (even a trivial smoke test) so the CI job has something to execute and doesn't silently no-op.
   - Recommendation: Add `frontend/vitest.config.ts` plus one trivial smoke test (e.g., a render test for a stable, already-correct component like `TopNav`) so the CI job actually runs and reports pass/fail — real frontend behavior-test authoring is Phase 17's job (TEST-02 in REQUIREMENTS.md), not this phase's.

2. **Does `_send_report_email`'s dev-mode fallback (`if not api_key: logger.warning(...); return`) need its own explicit test, or is it out of scope?**
   - What we know: `RESEND_API_KEY` defaults to `""` in `Settings`, meaning in a bare test environment (no `.env`), `mail_report` would take the "skip email" path rather than exercising the mocked-Resend path — a test that doesn't explicitly set `RESEND_API_KEY` in its environment could accidentally pass without ever calling the mocked `Emails.send`.
   - What's unclear: Whether characterizing *both* paths (API key present → real call path exercised with mocks; API key absent → dev-mode skip) is required by success criterion 3, or just the "happy path" with a key present.
   - Recommendation: Test both explicitly — set `RESEND_API_KEY` via `monkeypatch.setenv` (or override `settings.RESEND_API_KEY` directly) in the primary PDF/email test so the mocked path is definitely exercised, and add one smaller test asserting the dev-mode skip logs a warning and does not call `Emails.send` when the key is empty (this is current, intentional behavior per the code, not a bug — good D-04 characterization candidate).

## Environment Availability

| Dependency | Required By | Available (local dev machine, this session) | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker daemon | `testcontainers-python`'s `PostgresContainer` (D-01), local test runs | ✗ Not found on this machine | — | Developer must install Docker Desktop, Colima, or Podman (with Docker-API compatibility) locally before `pytest` can run — **no fallback exists** given D-01 explicitly rules out SQLite. This is a one-time local setup cost, not a per-run blocker once installed. |
| Docker (GitHub Actions `ubuntu-latest` runner) | `testcontainers-python` in CI | ✓ (per GitHub's documented runner image contents) [CITED: GitHub Docs] | Docker Engine, version varies by runner image | — |
| `uv` | Backend dependency management, matches existing `uv.lock`-based workflow | ✓ | 0.11.29 | — |
| Node.js | Frontend test runner (Vitest), CI `actions/setup-node` | ✓ (local: v24.18.0; recommend CI pin to Node 20 to match `frontend/Dockerfile`'s `node:20-alpine` build stage) | v24.18.0 (local) | CI should still pin Node 20 explicitly via `actions/setup-node` regardless of local Node version, for parity with the production Docker build. |
| npm | Frontend package installs | ✓ | 11.16.0 | — |
| Python (system) | Not directly used — `uv` manages its own interpreter per `.python-version` (3.14) / Docker's 3.13 | System `python3` is 3.9.6 (irrelevant — `uv run`/`uv sync` fetches the pinned interpreter itself) | 3.9.6 (system, unused by this project) | None needed — `uv` resolves 3.14 (local pin) or 3.13 (Docker parity) independently of system Python. |
| `zen-engine` native wheels | Report/PDF tests exercising the current (not-yet-replaced) scoring engine | ✓ — confirmed `manylinux` wheels exist for cp313 and cp314 on PyPI | 0.51.0 | If CI ever moves to a Python version without a prebuilt wheel, `zen-engine` would need to compile from source (slow, requires Rust toolchain) — not currently a risk since both 3.13 and 3.14 have wheels. |

**Missing dependencies with no fallback:**
- Docker daemon on the local development machine used for this research session — must be installed by the developer before local `pytest` runs will succeed (testcontainers has no non-Docker mode compatible with D-01's real-Postgres requirement).

**Missing dependencies with fallback:**
- None beyond the Docker item above — Node/npm/uv are all present and current on this machine; GitHub Actions runners are documented to include Docker by default.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (backend), Vitest 4.1.10 (frontend) |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` (new, this phase) / `frontend/vitest.config.ts` (new, this phase) |
| Quick run command | `uv run pytest -x -k auth` (backend, targeted) / `npx vitest run` (frontend) |
| Full suite command | `uv run pytest --cov=app --cov-report=term-missing` / `npx vitest run --coverage` |

### Phase Requirements → Test Map

Since Phase 12 maps no REQ-IDs (see Phase Requirements section), this maps to the phase's own success criteria instead:

| Success Criterion | Behavior | Test Type | Automated Command | File Exists? |
|--------------------|----------|-----------|-------------------|-------------|
| 1. Auth flows regression-covered | register/login/lockout/password-reset | integration (real Postgres, real HTTP via `TestClient`) | `uv run pytest tests/api/test_auth.py -x` | ❌ Wave 0 |
| 2. Admin cascade-delete + CSV export covered | delete_user/delete_initiative cascade, export_dataset CSV shape, list_users/list_initiatives | integration | `uv run pytest tests/api/test_admin.py -x` | ❌ Wave 0 |
| 3. PDF/email delivery covered | generate_report → mail_report with mocked WeasyPrint/Resend | integration | `uv run pytest tests/api/test_reports.py -x` | ❌ Wave 0 |
| 4. Suite runs fast enough to gate merges | full backend + frontend suite completes quickly (target: well under CI's default job timeout; no hard SLA given in CONTEXT.md) | CI smoke | full GH Actions workflow run | ❌ Wave 0 (workflow itself) |

### Sampling Rate
- **Per task commit:** `uv run pytest -x -k <relevant_module>` (backend) / `npx vitest run <relevant_file>` (frontend)
- **Per wave merge:** `uv run pytest --cov=app --cov-report=term-missing` + `npx vitest run --coverage`
- **Phase gate:** Full suite green in GitHub Actions (both jobs) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/conftest.py` — testcontainers Postgres fixture, session/transaction fixtures, lifespan-aware `TestClient` fixture (Pattern 1)
- [ ] `backend/tests/factories.py` — plain fixture factories for `User`, `Initiative`, `QuestionnaireAnswer`, `EvidenceURL` (D-03 production-shaped data)
- [ ] `backend/tests/api/test_auth.py`, `test_admin.py`, `test_reports.py` — the three success-criterion test files
- [ ] `backend/pyproject.toml` — `[tool.pytest.ini_options]` + dev dependency group
- [ ] `frontend/vitest.config.ts` — new, jsdom environment
- [ ] `.github/workflows/test.yml` — new, both jobs (Code Examples section has a full draft)
- [ ] Framework install: `uv add --dev pytest pytest-asyncio pytest-cov pytest-mock "testcontainers[postgres]" faker httpx` (backend); `npm install -D vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event` (frontend)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes — this phase's own subject matter | Existing bcrypt + PyJWT + account-lockout implementation in `auth.py`/`security.py`; this phase adds regression tests asserting this behavior, not new auth code. No new library introduced. |
| V3 Session Management | Yes (partial) | JWT expiry (24h) is characterized implicitly by testing `create_access_token`/`decode_access_token`; full session-management hardening (httpOnly cookie migration) is explicitly Phase 18, out of scope here. |
| V4 Access Control | Yes | `require_admin` dependency (role check) is exercised by every admin test — verify tests include at least one negative case (non-admin user gets 403) to characterize the access-control boundary, not just the happy path. |
| V5 Input Validation | Partial | `UserCreate`/`ResetPasswordRequest` Pydantic validators (password length/common-password checks) are indirectly exercised by registration/reset tests; not the primary focus of this phase. |
| V6 Cryptography | Yes (characterization only) | `bcrypt` (password hashing) and `PyJWT` (token signing) are pre-existing, correctly-chosen libraries per `.planning/codebase/CONVENTIONS.md`/STATE.md — this phase must NOT introduce a new crypto library; tests only characterize existing behavior. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation (already in place, being characterized not built) |
|---------|--------|---------------------------------------------------------------------|
| Login timing attack (username enumeration via response-time difference) | Information Disclosure | `auth.py`'s dummy-hash verify-even-for-nonexistent-user pattern (`_DUMMY_HASH`) — write a test asserting both existing and non-existing emails hit the same code path (both call `verify_password`), not necessarily a timing assertion (timing-based tests are flaky in CI) but a structural one. |
| Brute-force credential stuffing | Elevation of Privilege | Account lockout after 5 failed attempts (`_MAX_FAILED_ATTEMPTS`) + `slowapi` rate limit on `/login` (`10/minute`) — both already covered by Pattern 2's characterization test; be mindful of Pitfall 4 (rate limiter interference across the test session). |
| Privilege escalation via admin endpoints | Elevation of Privilege | `require_admin` dependency (403 for non-admin) — ensure at least one admin test asserts a plain `USER`-role token is rejected from every admin endpoint, not just that admin tokens succeed. |
| Password reset token replay | Tampering | One-time-use token (`user.password_reset_token = None` after use) + 30-minute expiry — write a characterization test asserting a second `reset-password` call with the same token fails (400), and an expired-token call fails (400) — both are existing, correct behaviors per CONVENTIONS.md/auth.py, good D-04 candidates if any edge case (e.g., clock-skew handling) reveals a gap. |

## Sources

### Primary (HIGH confidence)
- PyPI JSON API (`https://pypi.org/pypi/<pkg>/json`, live fetch) — `testcontainers`, `factory-boy`, `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `httpx`, `faker` — versions and repo URLs verified 2026-07-22.
- npm registry (`npm view <pkg> version`, live) — `vitest`, `@vitest/coverage-v8`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event` — versions verified 2026-07-22.
- Direct source inspection (this session): `backend/app/main.py`, `backend/app/api/v1/{auth,admin,reports}.py`, `backend/app/services/report_generator.py`, `backend/app/core/{config,deps,security}.py`, `backend/app/db/session.py`, `backend/app/models/{user,initiative,questionnaire,report,evidence}.py`, `backend/app/schemas/auth.py`, `backend/pyproject.toml`, `backend/Dockerfile`, `backend/alembic.ini`, `docker-compose.yml`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/Dockerfile` — HIGH confidence, primary source (this codebase, this session).
- `.planning/codebase/{TESTING,CONCERNS,CONVENTIONS}.md`, `.planning/research/{STACK,PITFALLS}.md`, `.planning/phases/12-.../12-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — HIGH confidence, primary source (prior project research/audits, this milestone).

### Secondary (MEDIUM confidence)
- WebSearch: Docker Docs — "Getting started with Testcontainers for Python" (docs.docker.com/guides/testcontainers-python-getting-started) — session/module-scoped fixture patterns, cross-checked against testcontainers.com's own getting-started guide.
- WebSearch: GitHub Docs — "Creating PostgreSQL service containers" (docs.github.com/actions/guides/creating-postgresql-service-containers) — health-check/port-mapping config, cross-checked against Simon Willison's TIL and til.simonwillison.net.
- WebSearch: GitHub — `fastapi/fastapi` Discussion #10800 ("Testing lifespan along with state in FastAPI") + FastAPI's own docs (fastapi.tiangolo.com/advanced/testing-events) — `TestClient` context-manager lifespan behavior.
- WebSearch: `github.com/Kozea/WeasyPrint` issues (#448, #655) + general pytest-mock patching guides — WeasyPrint mocking pattern and lazy-import patch-target gotcha.
- WebSearch: `factoryboy.readthedocs.io`, `github.com/fastapi/sqlmodel` Discussion #615 — factory_boy + SQLModel integration pattern (used to inform the Alternatives Considered table, not adopted as the primary recommendation).
- WebSearch: `docs.astral.sh/uv/guides/integration/github`, `github.com/astral-sh/setup-uv` — uv caching in GitHub Actions.
- WebSearch: "actions/checkout actions/setup-node latest major version 2026" — confirmed `actions/checkout@v7` / `actions/setup-node@v7` current as of July 2026 (Node 24 runtime migration context).
- WebSearch: SQLAlchemy/Alembic GitHub issues (#67, #1612, #1254, #886, #1347, #278) — native ENUM drop/recreate gotchas informing Pitfall/Anti-Pattern on schema teardown.

### Tertiary (LOW confidence)
- None — every finding above was either verified against a registry/tool, cross-checked across 2+ independent sources, or derived directly from this codebase's own source.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every package version verified live against PyPI/npm registries this session; no version claims rely solely on training data.
- Architecture (testcontainers + lifespan patterns): HIGH — cross-checked across Docker's own docs, GitHub's own docs, and FastAPI's own discussion/docs threads; lifespan/app.state finding verified directly against this codebase's `main.py`/`admin.py`/`reports.py` source, not assumed.
- Pitfalls: HIGH — every pitfall in this file is derived from direct inspection of this specific codebase's source (deferred WeasyPrint import, `app.state` lifespan wiring, rate-limiter sharing, ENUM/upsert constraints), not generic industry advice.

**Research date:** 2026-07-22
**Valid until:** 30 days (2026-08-21) for the architecture/pitfall findings (grounded in this codebase's source, changes slowly); ~14 days for the exact package version pins (fast-moving ecosystem — re-verify `pip`/`npm` versions at planning/execution time if this research is consumed after early August 2026).
