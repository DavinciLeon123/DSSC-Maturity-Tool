---
phase: 12
slug: test-retrofit-stabilize-existing-flows
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-22
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (backend), Vitest 4.1.10 (frontend) |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]` (new, this phase) / `frontend/vitest.config.ts` (new, this phase) |
| **Quick run command** | `uv run pytest -x -k auth` (backend, targeted) / `npx vitest run` (frontend) |
| **Full suite command** | `uv run pytest --cov=app --cov-report=term-missing` / `npx vitest run --coverage` |
| **Estimated runtime** | Not yet measured — Wave 0 installs the suite from scratch; no prior baseline exists |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -x -k <relevant_module>` (backend) / `npx vitest run <relevant_file>` (frontend)
- **After every plan wave:** Run `uv run pytest --cov=app --cov-report=term-missing` + `npx vitest run --coverage`
- **Before `/gsd-verify-work`:** Full suite must be green in GitHub Actions (both jobs)
- **Max feedback latency:** Target well under CI's default job timeout (no hard SLA given in CONTEXT.md — success criterion #4 only requires the suite be fast enough to gate merges)

---

## Per-Task Verification Map

Phase 12 maps no REQ-IDs (foundational safety-net phase — see ROADMAP.md/REQUIREMENTS.md). Verification maps to the phase's own success criteria instead. Task-level rows are filled in by the planner/executor as PLAN.md tasks are created.

| Success Criterion | Behavior | Test Type | Automated Command | File Exists? | Status |
|--------------------|----------|-----------|-------------------|-------------|--------|
| 1. Auth flows regression-covered | register/login/lockout/password-reset | integration (real Postgres, real HTTP via `TestClient`) | `uv run pytest tests/api/test_auth.py -x` | ❌ Wave 0 | ⬜ pending |
| 2. Admin cascade-delete + CSV export covered | delete_user/delete_initiative cascade, export_dataset CSV shape, list_users/list_initiatives | integration | `uv run pytest tests/api/test_admin.py -x` | ❌ Wave 0 | ⬜ pending |
| 3. PDF/email delivery covered | generate_report → mail_report with mocked WeasyPrint/Resend | integration | `uv run pytest tests/api/test_reports.py -x` | ❌ Wave 0 | ⬜ pending |
| 4. Suite runs fast enough to gate merges | full backend + frontend suite completes quickly | CI smoke | full GH Actions workflow run | ❌ Wave 0 (workflow itself) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/conftest.py` — testcontainers Postgres fixture, session/transaction fixtures, lifespan-aware `TestClient` fixture (tests MUST use `with TestClient(app) as client:` — `app.state.mami_config`/`app.state.zen_engine` are only populated via the lifespan context manager)
- [ ] `backend/tests/factories.py` — plain fixture factories for `User`, `Initiative`, `QuestionnaireAnswer`, `EvidenceURL` (D-03 production-shaped synthetic data)
- [ ] `backend/tests/api/test_auth.py`, `test_admin.py`, `test_reports.py` — the three success-criterion test files
- [ ] `backend/pyproject.toml` — `[tool.pytest.ini_options]` + dev dependency group
- [ ] `frontend/vitest.config.ts` — new, jsdom environment
- [ ] `.github/workflows/test.yml` — new, both jobs (backend pytest + frontend Vitest, Postgres service/testcontainers)
- [ ] Framework install: `uv add --dev pytest pytest-asyncio pytest-cov pytest-mock "testcontainers[postgres]" faker httpx` (backend); `npm install -D vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event` (frontend)
- [ ] Developer setup note: local dev machine has no Docker daemon installed — testcontainers' `PostgresContainer` has no non-Docker fallback compatible with D-01's real-Postgres requirement; a one-time local Docker install (Docker Desktop/Colima/Podman) is required before `pytest` runs locally. Document this in the plan/README, do not silently assume Docker is present.

*Wave 0 must land before any success-criterion test file can execute — nothing in this phase has "existing infrastructure" to lean on (zero test coverage today).*

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification. This phase's entire scope is adding automated regression coverage; nothing here relies on manual testing.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < CI's default job timeout
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
