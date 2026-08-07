---
phase: 12-test-retrofit-stabilize-existing-flows
plan: 01
subsystem: testing
tags: [pytest, testcontainers, postgres, fastapi, sqlmodel, faker]

# Dependency graph
requires: []
provides:
  - "backend/tests/conftest.py — session-scoped real-Postgres testcontainer fixture, transaction-rollback session fixture, lifespan-aware client/admin_client/user_client fixtures, autouse rate-limiter-disable fixture"
  - "backend/tests/factories.py — plain fixture-factory functions (User, Initiative, QuestionnaireAnswer, EvidenceURL, ComplianceReport)"
  - "backend/tests/test_smoke.py — infra chain proof (not yet green locally — see Known Gaps)"
  - "backend/pyproject.toml [tool.pytest.ini_options] + dev dependency group"
  - "backend/tests/README.md — Docker/Colima/Podman local-setup documentation"
affects: [12-02, 12-03, 12-04, 12-05, 17]

# Tech tracking
tech-stack:
  added: ["pytest 9.1.1", "pytest-asyncio 1.4.0", "pytest-cov 7.1.0", "pytest-mock 3.15.1", "httpx 0.28.1", "faker 40.32.0", "testcontainers[postgres] 4.14.2"]
  patterns:
    - "Session-scoped real-Postgres testcontainer + one create_all() per session (no drop/recreate) to avoid Postgres ENUM 'type already exists' errors"
    - "Function-scoped transaction-rollback session fixture for per-test isolation"
    - "Lifespan-aware TestClient (with TestClient(app) as c:) — required for app.state.mami_config/zen_engine to populate"
    - "Independent admin_client/user_client fixtures (each builds its own TestClient) so a test can hold an anonymous and an authenticated client simultaneously without header-mutation collisions"
    - "Autouse fixture disables the auth router's process-wide slowapi rate limiter for the whole test session"

key-files:
  created:
    - backend/tests/conftest.py
    - backend/tests/factories.py
    - backend/tests/test_smoke.py
    - backend/tests/README.md
    - backend/tests/__init__.py
    - backend/tests/api/__init__.py
    - backend/tests/services/__init__.py
  modified:
    - backend/pyproject.toml
    - backend/uv.lock

key-decisions:
  - "Human approved the RESEARCH.md Package Legitimacy Audit as-is — all 7 backend packages installed exactly at their audited pinned versions, no substitutions"
  - "admin_client/user_client each build an independent TestClient instance (rather than mutating the shared `client` fixture's headers) so a single test can use both an anonymous and an authenticated client at once"
  - "Docker daemon confirmed absent on this execution machine — matches RESEARCH.md Environment Availability A4 exactly; test_smoke.py cannot run locally until Docker Desktop/Colima/Podman is installed, per tests/README.md"

patterns-established:
  - "Pattern 1 (RESEARCH.md): session-scoped postgres_container -> engine (create_all once) -> function-scoped rollback session -> lifespan-aware client"
  - "One create_all() per pytest session, never drop_all()/create_all() between modules"

requirements-completed: []

coverage:
  - id: D1
    description: "Backend dev test dependencies installed at exact audited versions (pytest, pytest-asyncio, pytest-cov, pytest-mock, httpx, faker, testcontainers[postgres])"
    verification:
      - kind: unit
        ref: "uv run python -c \"import pytest, testcontainers.postgres, faker, pytest_asyncio, pytest_mock\" — printed deps-ok"
        status: pass
    human_judgment: false
  - id: D2
    description: "pytest config ([tool.pytest.ini_options] testpaths + asyncio_mode=auto) added to backend/pyproject.toml without touching runtime dependencies"
    verification:
      - kind: unit
        ref: "grep -n 'asyncio_mode' backend/pyproject.toml / grep -n 'testpaths' backend/pyproject.toml"
        status: pass
    human_judgment: false
  - id: D3
    description: "Docker local-setup gap (RESEARCH.md A4) documented in backend/tests/README.md"
    verification:
      - kind: other
        ref: "backend/tests/README.md exists, names Docker Desktop/Colima/Podman"
        status: pass
    human_judgment: false
  - id: D4
    description: "conftest.py fixtures implement Pattern 1 (real-Postgres testcontainer, transaction-rollback session, lifespan-aware client) and Pitfall 4 mitigation (rate limiter disabled)"
    verification:
      - kind: unit
        ref: "uv run pytest --collect-only — 1 test collected, no import errors"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/test_smoke.py -x -q"
        status: fail
    human_judgment: true
    rationale: "The collect-only run and static grep checks prove the fixture code is structurally correct (no import errors, correct context-manager usage, single create_all call). The actual smoke test cannot execute on this machine because no Docker daemon is installed — this is the pre-flagged RESEARCH.md Environment Availability gap (A4), not a code defect. A human with Docker (or CI) must confirm the smoke test passes before this deliverable is fully proven end-to-end."

duration: 25min
completed: 2026-07-22
status: complete
---

# Phase 12 Plan 01: Backend Test Infrastructure Summary

**pytest + testcontainers-Postgres backend test infrastructure (conftest fixtures, factories, smoke test) installed and wired, blocked from local green-run only by a pre-flagged missing local Docker daemon**

## Performance

- **Duration:** ~25 min (Tasks 2-3, post-checkpoint-approval)
- **Started:** 2026-07-22T08:45:14Z (approx, per STATE.md pre-checkpoint activity)
- **Completed:** 2026-07-22T08:54:29Z
- **Tasks:** 3 (Task 1: checkpoint, Task 2: install/config, Task 3: fixtures/factories/smoke test)
- **Files modified:** 9 (2 modified, 7 created)

## Accomplishments
- Installed the full backend dev-test stack (`pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `httpx`, `faker`, `testcontainers[postgres]`) at exactly the versions the human approved in the Task 1 legitimacy checkpoint — confirmed via install output and `uv.lock` (no unexpected substitute package names)
- Added `[tool.pytest.ini_options]` (`testpaths`, `asyncio_mode = "auto"`) to `backend/pyproject.toml` without touching any runtime dependency
- Created `backend/tests/conftest.py` implementing RESEARCH.md Pattern 1: session-scoped `postgres_container`/`engine` fixtures (one `create_all()` per session), a function-scoped transaction-rollback `session` fixture, a lifespan-aware `client` fixture, and independent `admin_client`/`user_client` fixtures for role-based access-control testing
- Added an autouse fixture disabling the auth router's process-wide `slowapi` rate limiter for the whole test session, mitigating RESEARCH.md Pitfall 4
- Created `backend/tests/factories.py` with plain fixture-factory functions (not `factory_boy`, per D-03) for `User`, `Initiative`, `QuestionnaireAnswer`, `EvidenceURL`, `ComplianceReport` — all mirroring exact model field names/enums, using `faker` for realistic data
- Created `backend/tests/test_smoke.py` proving (structurally — see Known Gaps) the container → schema → lifespan → HTTP chain
- Documented the mandatory local Docker/Colima/Podman prerequisite in `backend/tests/README.md`, including the exact failure symptom testcontainers emits when Docker is absent

## Task Commits

Each task was committed atomically:

1. **Task 1: Package legitimacy verification before first install** — checkpoint only, no commit (human approved "approved")
2. **Task 2: Install backend test deps, add pytest config, document the Docker local-setup gap** - `4dee948` (feat)
3. **Task 3: Create conftest.py fixtures and factories.py** - `5ec951d` (feat)

_No plan-metadata commit shown yet — created after this SUMMARY per the workflow's final_commit step._

## Files Created/Modified
- `backend/pyproject.toml` - added `[tool.pytest.ini_options]` + `[dependency-groups] dev` (additive; runtime `dependencies` unchanged)
- `backend/uv.lock` - resolved dev dependency tree
- `backend/tests/__init__.py`, `backend/tests/api/__init__.py`, `backend/tests/services/__init__.py` - empty package markers (created here to avoid Wave 2 create-races)
- `backend/tests/README.md` - Docker Desktop/Colima/Podman local-setup documentation, testcontainers failure symptom, CI-already-has-Docker note
- `backend/tests/conftest.py` - `postgres_container`, `engine`, `session`, `client`, `admin_client`, `user_client` fixtures + autouse rate-limiter-disable fixture
- `backend/tests/factories.py` - `make_user`, `make_initiative`, `make_submitted_initiative`, `make_answer`, `make_evidence`, `make_report`
- `backend/tests/test_smoke.py` - `test_app_boots_with_lifespan`

## Decisions Made
- Human approved the RESEARCH.md Package Legitimacy Audit exactly as presented at Task 1's checkpoint — no package name/version changes were requested or made.
- Spot-checked resolved `uv.lock` entries and install output after `uv add`: `pytest==9.1.1`, `pytest-asyncio==1.4.0`, `pytest-cov==7.1.0`, `pytest-mock==3.15.1`, `httpx==0.28.1`, `faker==40.32.0`, `testcontainers==4.14.2` — all match the audited table exactly; no unexpected substitute package was pulled in.
- Designed `admin_client`/`user_client` to each build an independent `TestClient` (rather than mutating the shared `client` fixture's auth header) so a single downstream test (e.g. an access-control negative test) can safely use both an anonymous and an authenticated client at once without state collisions. This is a deliberate implementation choice within the plan's "or helper" latitude, not a deviation from the plan's intent.

## Deviations from Plan

None — plan executed exactly as written. The Docker-unavailable outcome for the smoke test is not a deviation: it is the exact, pre-flagged RESEARCH.md Environment Availability gap (A4) the plan explicitly anticipated and required to be documented (not silently assumed away) in `backend/tests/README.md`, which this plan does.

## Issues Encountered
- **`create_all` acceptance-criteria grep collision:** The plan's acceptance criteria requires `grep -n 'create_all' backend/tests/conftest.py` to match exactly once. My first draft's docstring comment also contained the literal substring "create_all", producing two matches. Fixed by rewording the docstring to avoid the substring while preserving the same warning about not repeating the schema-build step. Verified via re-grep before committing — now matches exactly once (the real `SQLModel.metadata.create_all(eng)` call).
- **Local Docker daemon absent:** Confirmed via `docker info` (command not found) that this execution machine has no Docker installed at all (not just a stopped daemon) — an even more complete absence than RESEARCH.md's own research-session finding. `uv run pytest tests/test_smoke.py -x -q` fails at container-startup with `docker.errors.DockerException: Error while fetching server API version: ... FileNotFoundError`. This is the expected, pre-documented failure mode (`tests/README.md` names this exact symptom class). No fabricated pass is claimed — `--collect-only` (1 test collected, zero import errors) and static greps are the actual evidence for this plan's completion; the live smoke-test run itself remains unverified on this machine.

## User Setup Required

**External tooling requires manual local installation.** Install Docker Desktop, Colima, or Podman (Docker-API compatible) on this development machine before `uv run pytest` (any backend test) can execute locally — see `backend/tests/README.md` for exact instructions and the failure symptom to expect if this step is skipped. CI (GitHub Actions `ubuntu-latest`, Phase 12's later Wave 2/3 plans) already has Docker preinstalled and does not need this step.

## Next Phase Readiness
- `backend/tests/conftest.py` and `backend/tests/factories.py` are structurally complete and import-clean (`pytest --collect-only` succeeds with zero errors) — Plans 02/03/04 (test_auth.py, test_admin.py, test_reports.py) can be authored against these fixtures immediately.
- **Blocker for local verification only:** `uv run pytest tests/test_smoke.py -x -q` has not been confirmed green on this machine due to the missing local Docker daemon (see Known Stubs/Gaps below). This does not block downstream plan authoring (fixtures are correct by inspection + collection), but it does mean the "real Postgres container actually boots and the schema builds successfully" claim is currently unverified end-to-end outside of a Docker-equipped environment (CI or a developer machine with Docker installed).

## Known Stubs / Gaps

None are stubs in the code sense (no hardcoded empty/placeholder values reach any UI or API response) — the one open item is an **environment gap, not a code stub**: `backend/tests/test_smoke.py` cannot be executed to completion on this machine because Docker is not installed. This is the exact, pre-documented RESEARCH.md Environment Availability item A4 ("The local development machine ... does not currently have Docker installed"), already surfaced in `backend/tests/README.md` per the plan's Task 2 requirement. Whoever next has Docker access (a developer machine with Docker Desktop/Colima/Podman, or the first CI run once `.github/workflows/test.yml` lands) should run `uv run pytest tests/test_smoke.py -x -q` and confirm it passes — this is the single remaining unverified claim from this plan.

## Self-Check: PASSED

- FOUND: backend/pyproject.toml (asyncio_mode, testpaths present)
- FOUND: backend/tests/README.md
- FOUND: backend/tests/conftest.py
- FOUND: backend/tests/factories.py
- FOUND: backend/tests/test_smoke.py
- FOUND: backend/tests/__init__.py, backend/tests/api/__init__.py, backend/tests/services/__init__.py
- FOUND commit 4dee948 (Task 2)
- FOUND commit 5ec951d (Task 3)

---
*Phase: 12-test-retrofit-stabilize-existing-flows*
*Completed: 2026-07-22*
