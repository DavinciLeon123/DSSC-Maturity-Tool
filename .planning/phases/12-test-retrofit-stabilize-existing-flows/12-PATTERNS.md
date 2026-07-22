# Phase 12: Test Retrofit — Stabilize Existing Flows - Pattern Map

**Mapped:** 2026-07-22
**Files analyzed:** 11 (new files — no zero-coverage codebase has existing analogs, so this phase mostly maps files-under-test → their test files, plus infra configs to their closest existing config sibling)
**Analogs found:** 11 / 11 (all as "system-under-test" analogs — this repo has zero prior test infrastructure, so there are no prior *test* files to copy structure from; instead each new test file's structure is dictated by the module it characterizes, and RESEARCH.md's Pattern 1-4 code blocks are the primary template)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `backend/tests/conftest.py` | config/fixture | request-response (test infra) | `backend/app/db/session.py` (engine/session pattern) + `backend/app/main.py` (lifespan/app.state) | role-match (no prior test conftest exists; analog is the app's own DB/lifespan wiring it must replicate for tests) |
| `backend/tests/factories.py` | utility (fixture factory) | CRUD (data-shape) | `backend/app/models/{user,initiative,questionnaire,evidence,report}.py` | role-match (factories directly mirror these SQLModel schemas) |
| `backend/tests/api/test_auth.py` | test | request-response | `backend/app/api/v1/auth.py` | exact (file under test) |
| `backend/tests/api/test_admin.py` | test | CRUD + streaming (CSV) | `backend/app/api/v1/admin.py` | exact (file under test) |
| `backend/tests/api/test_reports.py` | test | event-driven (BackgroundTasks) + file-I/O (PDF) | `backend/app/api/v1/reports.py` | exact (file under test) |
| `backend/tests/services/test_report_generator.py` | test | transform | `backend/app/services/report_generator.py` | exact (file under test) |
| `backend/pyproject.toml` (modified) | config | — | existing `backend/pyproject.toml` `[project]`/`[build-system]` blocks | exact (same file, additive section) |
| `frontend/vitest.config.ts` | config | — | `frontend/vite.config.ts` | exact (sibling Vite config, same plugin ecosystem) |
| `frontend/src/components/layout/TopNav.test.tsx` | test (smoke) | request-response (renders + queries `/auth/me`) | `frontend/src/components/layout/TopNav.tsx` | exact (file under test) |
| `.github/workflows/test.yml` | config (CI) | batch | none — first CI config in repo; use `docker-compose.yml`'s Postgres image pin (`postgres:16-alpine`) as the version-of-record | no analog (net-new infra) |
| `backend/tests/api/test_admin_access_control.py` (or folded into `test_admin.py`) | test | request-response | `backend/app/core/deps.py` (`require_admin`) | exact (dependency under test) |

## Pattern Assignments

### `backend/tests/conftest.py` (config/fixture, request-response test infra)

**Analog:** `backend/app/db/session.py` (lines 1-11) + `backend/app/main.py` (lines 1-38, lifespan block)

**DB engine pattern to mirror** (`backend/app/db/session.py` full file):
```python
from sqlmodel import Session, create_engine
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=15,
    max_overflow=25,
    pool_pre_ping=True,
    pool_recycle=1800,
)

def get_session():
    with Session(engine) as session:
        yield session
```
Test engine fixture must build its own `create_engine(...)` pointed at the testcontainer URL (not import the app's real `engine`, which is bound to `settings.DATABASE_URL` at import time) — see RESEARCH.md Pattern 1 for the concrete fixture code.

**Lifespan/app.state pattern that MUST be replicated by the test client fixture** (`backend/app/main.py` lines 20-33):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mami_config = load_mami_config()
    app.state.questionnaire_config = load_questionnaire_config()
    app.state.questionnaire_configs = load_questionnaire_configs()
    scoring_dir = get_scoring_dir()
    def loader(key: str) -> str:
        return (scoring_dir / key).read_text()
    app.state.zen_engine = zen.ZenEngine({"loader": loader})
    yield
```
Consequence for the `client` fixture: **must** use `with TestClient(app) as c: yield c` (never bare `TestClient(app)`), per RESEARCH.md Pattern 1 / Pitfall 1 — otherwise `admin.py::get_admin_heatmap` and every `reports.py` endpoint raise `AttributeError` on `request.app.state.mami_config`.

**Dependency override target** — `get_session` is imported from `app.db.session` in every router (`auth.py` line 15, `admin.py` line 10, `reports.py` line 12); override exactly this symbol via `app.dependency_overrides[get_session] = get_session_override`.

---

### `backend/tests/factories.py` (utility/fixture factory, CRUD data-shape)

**Analog:** the four SQLModel model files directly — factories are literal instantiations of these classes, so field names/defaults must match exactly.

**User factory fields** (`backend/app/models/user.py`, full file, 14 lines): `email`, `hashed_password` (must be produced via `hash_password()` from `app.core.security`, not a raw string, if any factory-built user needs to actually log in), `role` (`"USER"`/`"ADMIN"`), `participant_type` (`"DSI"`/`"SP"`), `failed_login_attempts` (default 0), `lockout_until` (Optional).

**Initiative factory fields** (`backend/app/models/initiative.py` lines 22-33): `user_id` (FK, **unique** — one initiative per user, factory must not create two initiatives for the same user), `name`, `sector` (must be one of `SECTOR_OPTIONS`, lines 15-18), `participant_type` (`ParticipantType` enum), `status` (`InitiativeStatus` enum: `draft`/`active`/`submitted` — admin CSV/heatmap tests need `submitted` fixtures specifically per RESEARCH.md's heatmap-filter behavior).

**QuestionnaireAnswer factory fields** (`backend/app/models/questionnaire.py` lines 13-31): `initiative_id` (FK), `question_id`, `mami_code`, `questionnaire_version` (e.g. `"2.0"`), `answer_value` (`AnswerValue` enum: `YES`/`NOT_THERE_YET`/`NOT_APPLICABLE` — **this exact enum is what Phase 13 will change**, per D-01's rationale, so factory should use the enum member, not a raw string, to fail loudly if the enum shape changes), unique constraint `(initiative_id, question_id)` — factory must not produce duplicate question_ids per initiative.

**EvidenceURL / ComplianceReport factory fields** (`backend/app/models/evidence.py` full file, `backend/app/models/report.py` full file) — straightforward FK + string fields; `ComplianceReport.initiative_id` is `unique=True`, matching the `pg_insert().on_conflict_do_update(index_elements=["initiative_id"])` upsert in `reports.py` (Pitfall 5) — factory-created report rows exercise the same unique constraint the real upsert relies on.

---

### `backend/tests/api/test_auth.py` (test, request-response)

**Analog:** `backend/app/api/v1/auth.py` (full file, 172 lines) — already read in full above.

**Imports pattern to mirror in the test file:**
```python
from datetime import datetime, timedelta, timezone
from app.models.user import User
from app.core.security import hash_password, verify_password
```

**Registration — endpoint at lines 27-42:** POST `/auth/register`, 409 on duplicate email (line 30-33), 201 + `UserRead` shape on success.

**Login/lockout — endpoint at lines 45-84:**
- `_DUMMY_HASH`/timing-equalization branch (lines 56-61) — non-existent user still calls `verify_password` before raising 401. Test should assert **both** existing-wrong-password and non-existent-email hit 401 with the same message (STRIDE table's "Login timing attack" row), not a timing measurement.
- Lockout: `_MAX_FAILED_ATTEMPTS = 5` (line 22), 6th attempt after 5 failures → `423 LOCKED` (lines 63-69, 71-79). See RESEARCH.md Pattern 2 code block for the exact test shape (`test_account_lockout_after_five_failed_attempts`).
- Successful login resets `failed_login_attempts`/`lockout_until` (lines 82-85).
- **Rate limiter caveat (Pitfall 4):** `@limiter.limit("10/minute")` on line 47 is process-wide/IP-keyed (`slowapi`, `get_remote_address`) — group lockout tests to stay under 10 requests per test-file run or reset `app.state.limiter` between tests.

**Forgot/reset password — lines 106-172:**
- `forgot_password` (lines 130-152): always returns 202 regardless of whether email exists (line 152) — anti-enumeration, intentional per D-04's characterization note (RESEARCH.md Pattern 2's second example `test_forgot_password_always_returns_202_even_for_unknown_email`). 60-second cooldown returns 429 (lines 140-144).
- `_send_reset_email` (lines 106-125): dev-mode fallback prints to console when `api_key` is falsy (line 111) instead of calling `resend.Emails.send` — mirrors Open Question 2 in RESEARCH.md; test both the dev-mode-skip path (empty `RESEND_API_KEY`) and the mocked-Resend-call path (patched key), same technique as Pattern 3 below but patching `resend.Emails.send` directly (no lazy import here, unlike WeasyPrint).
- `reset_password` (lines 154-172): 400 on invalid/unknown token, 400 on expired token, one-time-use (`password_reset_token = None` after use, line 168) — test a second call with the same (now-cleared) token fails 400.

---

### `backend/tests/api/test_admin.py` (test, CRUD + streaming)

**Analog:** `backend/app/api/v1/admin.py` (full file, 306 lines) — already read in full above.

**Access-control pattern to test first** (`backend/app/core/deps.py` lines 32-36, `require_admin`):
```python
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
```
Every admin endpoint depends on this (`admin.py` lines 96, 138, 154, 178, 214, 262, 300) — per STRIDE table, at least one test per endpoint (or one parametrized test) must assert a plain `USER`-role token gets 403, not just that ADMIN tokens succeed.

**Cascade-delete under test** (`admin.py` lines 66-91, `_delete_initiative_children`/`_delete_user_cascade`) — use RESEARCH.md's Pattern 4 exactly (`test_delete_user_cascades_all_child_rows`), asserting zero orphaned rows in `QuestionnaireAnswer`/`EvidenceURL`/`ComplianceReport` directly via `session.exec(select(...))`, not just a 200 response. Note `delete_user` (lines 137-149) additionally 403s if `user.role == "ADMIN"` (line 144-145) and 404s if user doesn't exist (line 142-143) — both need coverage.

**Raw-SQL / native-ENUM endpoints** (`list_users` lines 95-125, `list_initiatives` lines 152-176, `export_dataset` lines 195-259, `get_admin_heatmap` lines 262-306) — these all execute raw `text(...)` SQL against Postgres-native columns (`answer_value` enum column, `initiative.status`), directly justifying D-01; SQLite would silently pass a query shape that Postgres's real ENUM type would reject. `get_admin_heatmap` (line 269 `request.app.state.mami_config`) additionally requires the lifespan-context-manager `TestClient` (Pitfall 1) since it isn't behind `Depends()`.

**CSV export shape** — use RESEARCH.md's ready-made code example verbatim (`test_export_dataset_csv_shape`), which asserts the *current* header column list (lines 217-220 in `admin.py`) per D-04 — this is a deliberate characterization lock, flagged for Phase 13 to update intentionally when `answer_value`'s ENUM changes.

---

### `backend/tests/api/test_reports.py` (test, event-driven + file-I/O)

**Analog:** `backend/app/api/v1/reports.py` (full file, ~340 lines) — already read in full above.

**Lazy-import mock target** (`_send_report_email`, lines 27-59; `download_report_pdf`, lines ~275-330) — `from weasyprint import HTML as WeasyHTML` happens **inside** the function body (lines 34, ~277), not at module level. Per RESEARCH.md Pattern 3 / Pitfall 2: patch `weasyprint.HTML` directly, never `app.api.v1.reports.WeasyHTML` (that attribute doesn't exist until the function runs — patching it silently no-ops and lets the real WeasyPrint render, which is slow and requires system libs in CI).

**Background-task assertion gap** (`mail_report`, lines ~330-370; bare `except Exception` at `_send_report_email` line 58) — per RESEARCH.md Pitfall 3, don't just assert `202`; assert the mocked `write_pdf`/`Emails.send` were actually called (`mock_html_cls.return_value.write_pdf.assert_called_once()`, `mock_send.assert_called_once()`), otherwise a test suite could stay green even if `_send_report_email`'s body were deleted, because `TestClient` runs `BackgroundTasks` synchronously but swallows the exception via the bare except.

**Upsert path** (`generate_report`, `pg_insert(ComplianceReport).values(...).on_conflict_do_update(index_elements=["initiative_id"])`, lines ~152-172) — per Pitfall 5, this only works if the full `SQLModel.metadata.create_all(engine)` builds the `unique=True` constraint on `ComplianceReport.initiative_id` (`backend/app/models/report.py` line 11) — never build a hand-picked subset schema for this test file.

**Dev-mode / real-scoring-path note** — `score_all_answers` (imported from `app.services.scoring_engine`, called at multiple report endpoints, e.g. line ~112) must run **unmocked** (real ZEN engine, since Phase 14 hasn't replaced it) per D-04 and Pitfall/Anti-Pattern list — only WeasyPrint and Resend are external boundaries to mock.

---

### `backend/tests/services/test_report_generator.py` (test, transform)

**Analog:** `backend/app/services/report_generator.py` (used via `generate_html_report`, `generate_report_data`, `_build_topic_structure` — imported in `reports.py` line 18 and `admin.py` line 20). Not fully read in this pass (module not required for D-01/D-02/D-03 decisions directly) — planner should Read this file directly during plan-writing since it's a pure-function transform module (no HTTP/DB), making it the easiest of the three to unit-test without `TestClient`/Postgres at all.

---

### `frontend/vitest.config.ts` (config, CI wiring only)

**Analog:** `frontend/vite.config.ts` (full file, 17 lines) — reuse the same `@vitejs/plugin-react` plugin and proxy conventions; add `test: { environment: 'jsdom', globals: true }` block per RESEARCH.md's Standard Stack (jsdom + `@testing-library/react`).

```typescript
// frontend/vite.config.ts (existing, to extend — not duplicate)
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'

export default defineConfig({
  plugins: [
    TanStackRouterVite({ routesDirectory: './src/routes', generatedRouteTree: './src/routeTree.gen.ts' }),
    react(),
  ],
  server: { proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } } },
})
```
Either extend this same `defineConfig` with a `test:` key (single-config approach) or create a separate `vitest.config.ts` re-using the same `plugins` array — planner's discretion, but must NOT duplicate the TanStackRouterVite/proxy config into two diverging files.

---

### `frontend/src/components/layout/TopNav.test.tsx` (test, smoke — CI wiring only per Open Question 1)

**Analog:** `frontend/src/components/layout/TopNav.tsx` (lines 1-40+, read above) — a stable, already-correct component using `@tanstack/react-query`'s `useQuery` to call `/auth/me` (lines 13-20) and `@tanstack/react-router`'s `Link`/`useNavigate`.

**Imports the test needs to mirror/wrap:**
```typescript
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
```
Test must wrap the component in a `QueryClientProvider` and a router test harness (or mock `@tanstack/react-router`'s hooks) since `TopNav` calls `useNavigate()`/`Link` unconditionally at module top-level render — a bare `render(<TopNav />)` without these providers will throw. Per RESEARCH.md Open Question 1's recommendation, this can be a trivial render-and-assert-nav-items-present smoke test; deep interaction testing is Phase 17 scope (TEST-02).

---

### `.github/workflows/test.yml` (CI config, batch)

**No analog** — first CI workflow in this repo. Use RESEARCH.md's full draft YAML (Code Examples section) verbatim as the starting point; cross-reference `docker-compose.yml`'s pinned `postgres:16-alpine` image (line 3) so the testcontainers-managed image version matches production/dev-compose parity rather than drifting to a different tag.

## Shared Patterns

### Lifespan-aware TestClient (applies to ALL backend API test files)
**Source:** `backend/app/main.py` lines 20-33 (`lifespan`) + RESEARCH.md Pattern 1
**Apply to:** `test_auth.py`, `test_admin.py`, `test_reports.py` — every file hitting a FastAPI route
```python
with TestClient(app) as c:
    yield c
```
Never instantiate `TestClient(app)` as a bare variable — `app.state.mami_config`/`app.state.zen_engine` (used directly, not via `Depends()`, in `admin.py::get_admin_heatmap` and every `reports.py` endpoint) are populated only when the lifespan context manager fires.

### DB session override via `get_session`
**Source:** `backend/app/db/session.py` (the `get_session` symbol imported identically in `auth.py` line 15, `admin.py` line 10, `reports.py` line 12)
**Apply to:** `conftest.py`'s `client` fixture — `app.dependency_overrides[get_session] = get_session_override`, cleared after each test.

### Real-Postgres-only, never SQLite (D-01)
**Source:** `backend/app/models/questionnaire.py` (native `AnswerValue` enum, line 8-11) + `backend/app/api/v1/reports.py` (`pg_insert().on_conflict_do_update`, lines ~152-172) + `backend/app/api/v1/admin.py` (raw `text()` SQL against enum columns, lines 95-125, 262-306)
**Apply to:** every backend test file — `testcontainers.postgres.PostgresContainer("postgres:16-alpine")`, matching `docker-compose.yml`'s pinned image.

### Error-response convention
**Source:** `backend/app/api/v1/auth.py`/`admin.py`/`reports.py` — consistently `HTTPException(status_code=..., detail="...")`; no custom error-wrapper class exists in this codebase (unlike some FastAPI projects). Tests should assert `response.json()["detail"]` for error cases, not a different envelope shape.
**Apply to:** all three API test files.

### Mock-at-point-of-use for external SDKs
**Source:** RESEARCH.md Pattern 3 / Pitfall 2 — `weasyprint.HTML`, `resend.Emails.send`
**Apply to:** `test_auth.py` (forgot-password email path), `test_reports.py` (PDF+email path)

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.github/workflows/test.yml` | config (CI) | batch | No `.github/` directory exists anywhere in this repo today (D-02) — RESEARCH.md's Code Examples section is the only template; use it directly rather than searching the codebase further. |
| `backend/tests/conftest.py` (testcontainers plumbing itself) | config/fixture | request-response | No prior test infra of any kind exists (TESTING.md confirms zero coverage); RESEARCH.md Pattern 1 is the authoritative template, cross-checked against this codebase's own `session.py`/`main.py` (documented above) rather than a codebase analog. |

## Metadata

**Analog search scope:** `backend/app/api/v1/`, `backend/app/core/`, `backend/app/db/`, `backend/app/models/`, `backend/app/services/`, `backend/app/main.py`, `backend/pyproject.toml`, `docker-compose.yml`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/src/components/layout/TopNav.tsx`
**Files scanned:** 16 (all files under test/config plus their direct schema/dependency neighbors — sufficient given this is a zero-test-infrastructure codebase where the "analog" for each new test file is definitionally the module it characterizes, not a pre-existing sibling test)
**Pattern extraction date:** 2026-07-22
