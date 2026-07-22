---
phase: 12-test-retrofit-stabilize-existing-flows
plan: 02
subsystem: testing
tags: [pytest, auth, characterization-tests, anti-enumeration, lockout, password-reset]

# Dependency graph
requires: ["12-01"]
provides:
  - "backend/tests/api/test_auth.py — 15 characterization tests: register (201/409), login (200/401 equal-path anti-enumeration), lockout (423 after 5x401, reset-on-success), forgot-password (202 known/unknown, 429 cooldown, dev-mode-skip vs mocked-Resend), reset-password (200 first-use, 400 reuse/expired/unknown-token)"
affects: [13, 14, 15, 16, 17, 18]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Characterization tests assert CURRENT auth.py behavior (D-04) — anti-enumeration, lockout, and one-time-use token behavior pinned as regression baseline, not new code"
    - "monkeypatch.setattr(auth_module.settings, \"RESEND_API_KEY\", ...) + mocker.patch(\"resend.Emails.send\") to exercise both the dev-mode-skip and mocked-Resend email paths without a lazy-import indirection (auth.py imports resend directly at module level, unlike reports.py's WeasyPrint)"
    - "Real token driven through forgot-password then read back via session.refresh(user).password_reset_token — no fabricated tokens"

key-files:
  created:
    - backend/tests/api/test_auth.py
  modified: []

key-decisions:
  - "Split the file into two atomic commits matching the plan's Task 1 (register/login) and Task 2 (lockout, forgot/reset password) boundaries, discarding an untracked, uncommitted partial draft left by a prior interrupted executor attempt and rewriting it in full (the draft's Task 1 content was correct and reused verbatim; Task 2 content did not exist yet and was authored fresh per the plan)"
  - "Added one extra test (test_reset_password_unknown_token_returns_400) beyond the plan's explicit acceptance criteria — read_first flagged this branch (auth.py's 'no matching user for token' 400 path) and it was zero-cost to characterize alongside reuse/expiry"

patterns-established:
  - "Anti-enumeration structural-equivalence assertions (same status + same detail string, never a wall-clock timing assertion) for both login and forgot-password"

requirements-completed: []

coverage:
  - id: T1
    description: "Registration (201 + UserRead shape, 409 duplicate email) and login (200 + bearer token, 401 wrong password, 401 non-existent email with identical detail string to wrong-password) characterized"
    verification:
      - kind: unit
        ref: "uv run pytest --collect-only tests/api/test_auth.py — 5 Task-1 tests collected, zero import errors"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/api/test_auth.py -x -q -k 'register or login'"
        status: fail
    human_judgment: true
    rationale: "The live run fails at testcontainer startup (docker.errors.DockerException — no Docker daemon on this machine), not inside any test body or assertion. This is the pre-flagged, pre-documented RESEARCH.md Environment Availability gap A4 / Plan 01's Known Gap, reconfirmed identically here. Collection succeeded cleanly (correct imports, correct fixture wiring, correct assertions by inspection) — a human with Docker (or the first CI run) must confirm the actual green run."
  - id: T2
    description: "Account lockout (423 after 5x401, 'locked' in detail; partial-streak success resets failed_login_attempts/lockout_until) and forgot/reset-password (202 known+unknown email, 429 cooldown, dev-mode-skip vs mocked-Resend both exercised, reset-password 200 first-use/400 reuse/400 expired/400 unknown-token) characterized"
    verification:
      - kind: unit
        ref: "uv run pytest --collect-only tests/api/test_auth.py — 15 total tests collected (5 Task-1 + 10 Task-2), zero import errors"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/api/test_auth.py -x -q"
        status: fail
    human_judgment: true
    rationale: "Same Docker-daemon-absent gap as T1 — the run fails at PostgresContainer startup before any test body executes, identical failure signature to Plan 01's test_smoke.py finding. No test logic was exercised against a live Postgres on this machine; confidence here rests on --collect-only (all 15 tests import- and collection-clean) plus manual review against auth.py's exact line-level behavior (lockout threshold, cooldown math, token-clearing order) rather than a green pytest run. CI (Wave 3 of this phase) will provide the first real execution."

duration: ~15min
completed: 2026-07-22
status: complete
---

# Phase 12 Plan 02: Auth Regression Test Characterization Summary

**15 characterization tests for register/login/lockout/forgot-reset-password in `backend/tests/api/test_auth.py`, collection-verified clean but NOT run-verified green due to the pre-documented local Docker-daemon gap (RESEARCH.md A4 / Plan 01's identical finding)**

## Performance

- **Duration:** ~15 min (building on an untracked, uncommitted partial draft from a prior interrupted attempt)
- **Completed:** 2026-07-22
- **Tasks:** 2 (Task 1: registration + login; Task 2: lockout + forgot/reset password)
- **Files modified:** 1 created (`backend/tests/api/test_auth.py`)

## Accomplishments

- **Task 1 — Registration + login:** 5 tests asserting 201 + `UserRead` shape on register, 409 on duplicate email, 200 + bearer token on successful login, 401 on wrong password, and — the anti-enumeration characterization — 401 with the *identical* detail string for a non-existent email as for a wrong password (structural equivalence only, no wall-clock timing assertion, per RESEARCH.md's Security Domain note).
- **Task 2 — Lockout + forgot/reset password:** 10 tests:
  - Lockout: 5 consecutive wrong-password attempts each return 401, the 6th returns 423 with "locked" in the detail (all 6 attempts kept in one test per the plan's Pitfall-4-aware guidance); a separate test asserts a login success after a partial (<5) failure streak resets `failed_login_attempts` and `lockout_until`.
  - Forgot-password: 202 for both a known and an unknown email (anti-enumeration); 429 on an immediate second request (60s cooldown); both email code paths exercised explicitly per Open Question 2 — dev-mode (empty `RESEND_API_KEY`) asserts `resend.Emails.send` is NOT called, and a mocked non-empty key asserts it IS called exactly once.
  - Reset-password: a real token is driven through `forgot-password` and read back via `session.refresh(user).password_reset_token` (never fabricated); 200 on first valid use; 400 on token reuse (one-time-use); 400 on a manually-expired token (`password_reset_expires` set into the past via the test session); 400 on a syntactically-valid-but-unknown token (extra coverage beyond the plan's explicit acceptance criteria, cheap to add given `read_first` flagged this branch).

## Task Commits

Each task was committed atomically:

1. **Task 1: Registration + login characterization tests** — `66f8ec5` (test)
2. **Task 2: Account lockout + forgot/reset password characterization tests** — `3076f4e` (test)

## Files Created/Modified

- `backend/tests/api/test_auth.py` — new, 15 tests total (269 lines)

## Decisions Made

- **Reused vs. rewrote the prior interrupted attempt's draft:** The untracked, uncommitted partial file at `backend/tests/api/test_auth.py` (92 lines, Task 1 only) was reviewed and found correct against the plan's acceptance criteria — reused verbatim as the Task 1 commit rather than rewritten from scratch. Task 2 content (lockout, forgot/reset password) did not exist in the draft and was authored fresh.
- **Two atomic commits matching the plan's task boundaries** even though the draft was already a single uncommitted file — split so `git log` reflects Task 1 / Task 2 exactly as scoped in `12-02-PLAN.md`, rather than one combined commit.
- **`monkeypatch.setattr(auth_module.settings, "RESEND_API_KEY", ...)`** rather than `monkeypatch.setenv` — `auth.py` imports the already-instantiated `settings` singleton from `app.core.config`, so mutating the attribute directly on that same object (imported into the test file as `auth_module.settings`) is the more precise target than an environment variable that `pydantic-settings` only reads once at process start.

## Deviations from Plan

None — plan executed exactly as written. No bugs were discovered while writing these tests; every characterized behavior (anti-enumeration structural equivalence, 5-attempt lockout, 60s cooldown, one-time-use token, expired-token rejection) matches `auth.py`'s intentional, documented design per D-04 and the plan's own read_first annotations. No D-04 backlog items to log.

### Backlog items discovered (D-04)

None.

## Issues Encountered

- **Docker daemon absent on this execution machine (expected, pre-documented gap):** `uv run pytest tests/api/test_auth.py -x -q` (both the Task 1 `-k "register or login"` subset and the full-file run) fails immediately with `docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))` at `PostgresContainer` startup — before any test body executes. This is the identical, pre-flagged failure mode from RESEARCH.md's Environment Availability item A4 and Plan 01's own `test_smoke.py` finding (Docker not installed at all, not merely stopped). No fabricated pass is claimed here. `uv run pytest --collect-only` succeeded cleanly both times (5/5 then 15/15 tests collected, zero import errors), confirming the fixtures, imports, and test structure are correct by inspection — but the actual "does this pass against a live Postgres" claim remains unverified on this machine. CI (Wave 3 of this phase) is the first environment expected to run this suite to completion.

## User Setup Required

Same as Plan 01: install Docker Desktop, Colima, or Podman locally before `uv run pytest` (any backend test) can execute to completion on this machine — see `backend/tests/README.md`. Not a blocker for this plan's completion (tests are structurally verified via collection + manual review against `auth.py`'s exact behavior), but the first real green/red signal for this file will come from a Docker-equipped developer machine or CI.

## Known Stubs

None — no hardcoded empty/placeholder values in any test; every test asserts a real HTTP status code and, where relevant, a real response body field or mocked-call assertion.

## Threat Flags

None beyond what the plan's own `<threat_model>` already scoped (T-12-02-ENUM, T-12-02-BF, T-12-02-RST, T-12-02-VAL) — this plan added test coverage only, no new endpoints, auth paths, or schema changes.

## Next Phase Readiness

- `backend/tests/api/test_auth.py` is complete per the plan's task breakdown (register/login/lockout/forgot-reset-password, 15 tests) and collection-clean.
- **Unverified claim carried forward:** the full auth test file has not been confirmed to pass against a live Postgres instance on any machine yet (same open item as Plan 01's smoke test) — the first Docker-equipped run (developer machine or CI, once `.github/workflows/test.yml` lands in a later wave of this phase) should run `uv run pytest tests/api/test_auth.py -x -q` and confirm all 15 tests pass.
- Plans 03/04 (admin, reports test files) can proceed independently against the same `conftest.py`/`factories.py` fixtures from Plan 01; nothing in this plan changes those fixtures.

## Self-Check: PASSED

- FOUND: backend/tests/api/test_auth.py
- FOUND commit 66f8ec5 (Task 1)
- FOUND commit 3076f4e (Task 2)

---
*Phase: 12-test-retrofit-stabilize-existing-flows*
*Completed: 2026-07-22*
