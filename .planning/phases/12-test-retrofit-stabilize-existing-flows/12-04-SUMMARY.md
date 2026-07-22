---
phase: 12-test-retrofit-stabilize-existing-flows
plan: 04
subsystem: testing
tags: [pytest, weasyprint, resend, report-generator, zen-engine, characterization]

# Dependency graph
requires:
  - "12-01: backend/tests/conftest.py (postgres_container/engine/session/client fixtures), backend/tests/factories.py (make_user/make_initiative/make_answer)"
provides:
  - "backend/tests/api/test_reports.py — mail_report (mocked WeasyPrint+Resend, both-called assertion, dev-mode skip, 422), download_report_pdf (mocked WeasyPrint, 422 on no answers), generate_report (real ZEN scoring + pg_insert upsert, verified via direct session query)"
  - "backend/tests/services/test_report_generator.py — pure-function tests for _build_topic_structure, generate_report_data, generate_html_report"
affects: [17]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Login-then-mutate-headers helper (_login) to bind the shared anonymous `client` fixture to a specific factory-created user, needed because report endpoints check initiative.user_id == current_user.id (admin_client/user_client from 12-01 are independent random users, not suitable here)"
    - "weasyprint.HTML patched at module level (never app.api.v1.reports.WeasyHTML) to intercept the lazy in-function `from weasyprint import HTML as WeasyHTML` import"
    - "Both-mocked-boundaries-called assertion (write_pdf + Emails.send) instead of a bare 202 status check, to defeat the bare `except Exception` silent-swallow in _send_report_email"
    - "Pure-function unit tests call report_generator functions directly with hand-authored dict inputs — no TestClient/Postgres session at all"

key-files:
  created:
    - backend/tests/api/test_reports.py
    - backend/tests/services/test_report_generator.py
  modified: []

key-decisions:
  - "Reused real MAMI code IDs (S-HRA-1.1, S-MRA-1.1, S-TA-1.1, S-HRA-2.1, S-MRA-2.1 from config/mami-framework.json) in test_reports.py's fixture answers, rather than the factories' default random S-HRA-N.M codes, so the report's category/dimension/topic aggregation (_build_matrix/_build_topic_structure, which iterate the real mami_config loaded via lifespan) actually finds matches for at least some answers — exercises the real end-to-end path more faithfully, not just a code path that always falls into the 'code not in mami_config' branch."
  - "score_all_answers/ZEN engine left completely unmocked in every test in test_reports.py per D-04 and the plan's explicit instruction — only weasyprint.HTML and resend.Emails.send are mocked."

requirements-completed: []

coverage:
  - id: T1
    description: "mail_report happy path: RESEND_API_KEY set, both weasyprint.HTML(...).write_pdf and resend.Emails.send called, attachment filename correct"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_reports.py::test_mail_report_generates_pdf_and_sends_email"
        status: collection-verified
    human_judgment: true
    rationale: "Collects cleanly (uv run pytest --collect-only, 0 import errors) and was manually reviewed line-by-line against RESEARCH.md Pattern 3/Pitfall 2/Pitfall 3. Cannot execute to a real pass/fail on this machine — no local Docker daemon (testcontainers.postgres.PostgresContainer fails at docker.errors.DockerException immediately, before any test body runs), an outcome pre-flagged in 12-01-SUMMARY.md (RESEARCH.md A4). CI (this phase's later CI-wiring plan) provides the actual green-run verification."
  - id: T2
    description: "mail_report dev-mode: empty RESEND_API_KEY still returns 202, resend.Emails.send NOT called"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_reports.py::test_mail_report_dev_mode_skips_resend_send"
        status: collection-verified
    human_judgment: true
    rationale: "Same Docker-gap caveat as T1."
  - id: T3
    description: "mail_report / download_report_pdf 422 on an initiative with no answers"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_reports.py::test_mail_report_no_answers_returns_422, test_download_report_pdf_no_answers_returns_422"
        status: collection-verified
    human_judgment: true
    rationale: "Same Docker-gap caveat as T1."
  - id: T4
    description: "download_report_pdf happy path returns 200 application/pdf with mocked WeasyPrint"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_reports.py::test_download_report_pdf_returns_pdf_content_type"
        status: collection-verified
    human_judgment: true
    rationale: "Same Docker-gap caveat as T1."
  - id: T5
    description: "generate_report: real ZEN scoring (unmocked) + pg_insert upsert verified via direct ComplianceReport query; regeneration replaces (not duplicates) the row"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_reports.py::test_generate_report_returns_html_and_upserts_compliance_report"
        status: collection-verified
    human_judgment: true
    rationale: "Same Docker-gap caveat as T1 — this test in particular is the one that exercises the real ZEN engine (score_all_answers) and the Postgres-native pg_insert().on_conflict_do_update() path (Pitfall 5), so it is the highest-value test to get a real CI/Docker-equipped green run on."
  - id: T6
    description: "_build_topic_structure / generate_report_data / generate_html_report pure-function contract shape"
    verification:
      - kind: unit
        ref: "uv run pytest tests/services/test_report_generator.py -x -q"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-07-22
status: complete
---

# Phase 12 Plan 04: PDF Generation + Email Delivery Characterization Tests Summary

**Report generate/pdf/mail endpoints characterized with mocked WeasyPrint+Resend boundaries and a live (unmocked) ZEN scoring path; report_generator's pure transform functions unit-tested directly — collection-verified and manually reviewed, execution blocked locally only by the pre-documented missing-Docker-daemon gap.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-22T09:35:07Z (per STATE.md, plan handoff)
- **Completed:** 2026-07-22T09:40:37Z
- **Tasks:** 2
- **Files modified:** 2 (both created)

## Accomplishments

- Created `backend/tests/api/test_reports.py` with 6 tests covering:
  - `mail_report` happy path — asserts both `weasyprint.HTML(...).write_pdf` AND `resend.Emails.send` were called (not just a 202), and the attachment filename is `MAMI-Interoperability-Report.pdf`
  - `mail_report` dev-mode path — empty `RESEND_API_KEY` still returns 202 but `resend.Emails.send` is asserted NOT called (current, intentional behavior)
  - `mail_report` 422 on an initiative with no answers
  - `download_report_pdf` happy path — 200, `application/pdf` content-type, mocked WeasyPrint
  - `download_report_pdf` 422 on an initiative with no answers
  - `generate_report` — real (unmocked) ZEN/MoSCoW scoring path runs end-to-end, HTML returned, and the `ComplianceReport` row is verified directly via a `session.exec(select(...))` query after the call; a second call proves the `pg_insert().on_conflict_do_update()` upsert replaces (not duplicates) the row
- Created `backend/tests/services/test_report_generator.py` with 3 pure-function unit tests (`_build_topic_structure`, `generate_report_data`, `generate_html_report`), calling the functions directly with hand-authored dict inputs — no `TestClient`/Postgres session used at all, confirmed by direct inspection of the test file (no `client`/`session` fixture parameters)
- WeasyPrint patched at `weasyprint.HTML` (module level) in every test that touches PDF rendering, never the reports-module alias — confirmed via `grep -n "weasyprint.HTML\|WeasyHTML" backend/tests/api/test_reports.py`, which shows only the correct module-level target
- `score_all_answers`/the ZEN engine is not mocked anywhere in `test_reports.py` — confirmed via `grep -n "score_all_answers\|zen" backend/tests/api/test_reports.py`, which returns no matches (the real engine, wired via `app.state.zen_engine` at lifespan, is what actually runs)

## Task Commits

Each task was committed atomically:

1. **Task 1: Report endpoint integration tests (mail/pdf/generate) with mocked WeasyPrint + Resend** — `f07a910` (test)
2. **Task 2: report_generator pure-function unit tests** — `e76b423` (test)

## Files Created/Modified

- `backend/tests/api/test_reports.py` — new; 6 tests, real-Postgres integration tests for `generate_report`/`download_report_pdf`/`mail_report`
- `backend/tests/services/test_report_generator.py` — new; 3 tests, pure-function unit tests for `report_generator.py`'s transform functions

## Decisions Made

- Used real MAMI code IDs from `config/mami-framework.json` (`S-HRA-1.1`, `S-MRA-1.1`, `S-TA-1.1`, `S-HRA-2.1`, `S-MRA-2.1`) for `test_reports.py`'s fixture answers instead of the factories' default randomly-generated `S-HRA-{1-4}.{1-2}` codes — this is not a deviation from the plan (factories' defaults already happen to fall in this exact real-code range), it's a deliberate choice to guarantee determinism so the report's category/dimension/topic aggregation (which iterates the *real* `mami_config` loaded at lifespan startup) reliably finds a match rather than relying on `fake.random_int` luck.
- `_login(client, email, password)` helper: logs the shared anonymous `client` fixture in as a specific factory-created user by POSTing to `/api/v1/auth/login` and mutating `client.headers`. This was necessary because `admin_client`/`user_client` (from Plan 01) are each bound to their own randomly-created user — report endpoints require the *same* user to own the initiative (`initiative.user_id == current_user.id`), so neither existing fixture fit; a local login helper was the smallest addition that didn't require touching `conftest.py`.

## Deviations from Plan

None — plan executed exactly as written. No bugs were discovered while writing these tests (no D-04 backlog items to log): the mail/PDF/generate endpoints' current behavior matched what RESEARCH.md/PATTERNS.md predicted (lazy WeasyPrint import, bare-except swallow risk mitigated by the both-called assertion, dev-mode skip, upsert-on-regenerate).

## Backlog items discovered (D-04)

None. Writing these tests did not surface any bug unrelated to the wizard/save issues already scoped for Phase 15 — `reports.py` and `report_generator.py`'s current behavior matched expectations throughout (the bare `except Exception` in `_send_report_email` is a pre-existing, already-tracked concern per CONCERNS.md/T-12-04-SILENT, not a new discovery).

## Issues Encountered — Known Environment Gap (Docker)

Per this plan's `<known_environment_gap>` instruction: this execution machine has no Docker daemon installed (confirmed identically in Plan 01's SUMMARY — `docker.errors.DockerException: Error while fetching server API version: ... FileNotFoundError`, raised immediately at `postgres_container` fixture setup, before any test body runs).

**What was actually verified on this machine:**
- `uv run pytest tests/api/test_reports.py --collect-only -q` → **6 tests collected, 0 import errors** (proves fixtures/imports/test structure are all correct)
- `uv run pytest --collect-only -q` (whole suite, all of Plans 01-04's tests together) → **40 tests collected, 0 import errors** (proves this plan's new files integrate cleanly alongside `test_auth.py`/`test_admin.py`/`test_smoke.py` with no fixture-naming collisions or import-order issues)
- `uv run pytest tests/services/test_report_generator.py -x -q` → **3 passed** (this file needs no Postgres/Docker at all — genuinely green, not just collected)
- `uv run pytest tests/api/test_reports.py -x -q` → **fails at the `postgres_container` fixture** with the exact pre-documented `docker.errors.DockerException`, identical in shape to Plan 01's own smoke-test failure on this same machine. This is the anticipated, pre-flagged gap (RESEARCH.md Environment Availability A4) — not a code defect in this plan's tests, and not fabricated as a pass.

**No fabricated green run is claimed for `test_reports.py`.** Confidence in this file's correctness rests on: (a) clean collection with zero import errors, (b) careful manual review against RESEARCH.md's Pattern 3 (mock-at-point-of-use), Pitfall 2 (lazy-import patch target), Pitfall 3 (background-task assertion gap), and Pitfall 5 (upsert schema completeness), and (c) the identical fixture chain (`postgres_container` → `engine` → `session` → `client`) already used successfully in Plans 02/03's `test_auth.py`/`test_admin.py`, which this plan's tests reuse unmodified. A human with Docker access (or this phase's later CI wiring) must run `uv run pytest tests/api/test_reports.py -x` to confirm an actual green result — this is the one remaining unverified claim from this plan, consistent with Plan 01/02/03's same caveat.

## User Setup Required

Same as Plans 01-03: install Docker Desktop, Colima, or Podman (Docker-API compatible) on this development machine before `uv run pytest` (any backend test touching Postgres) can execute locally — see `backend/tests/README.md`. CI (this phase's Wave 3 GitHub Actions plan) already has Docker preinstalled and needs no such step.

## Next Phase Readiness

- `backend/tests/api/test_reports.py` and `backend/tests/services/test_report_generator.py` are structurally complete, import-clean, and (for the pure-function file) actually green on this machine.
- **Blocker for local verification only:** `uv run pytest tests/api/test_reports.py -x -q` has not been confirmed green on this machine due to the missing local Docker daemon — identical caveat to Plans 01-03. This does not block Phase 12's remaining plan (05, CI wiring) — once GitHub Actions' Docker-equipped runners execute this suite, the real pass/fail signal will be established.
- ROADMAP.md Phase 12 success criterion #3 (PDF generation and email delivery of a completed report covered by automated regression tests) is met at the code/test-authorship level; full sign-off awaits either a Docker-equipped developer machine or this phase's CI run.

## Known Stubs

None — no hardcoded empty/placeholder values reach any test assertion; all mocks are explicit (`mocker.patch("weasyprint.HTML")`, `mocker.patch("resend.Emails.send")`) and asserted-called, not silently stubbed.

## Threat Flags

None — this plan's threat model (T-12-04-SILENT, T-12-04-INFO, T-12-04-AUTHZ, T-12-04-PDF) was fully anticipated in the plan's own frontmatter; no new security-relevant surface was introduced by these test files (test-only code, no new endpoints/schema/auth paths).

## Self-Check: PASSED

- FOUND: backend/tests/api/test_reports.py
- FOUND: backend/tests/services/test_report_generator.py
- FOUND commit f07a910 (Task 1)
- FOUND commit e76b423 (Task 2)
- CONFIRMED: `uv run pytest tests/services/test_report_generator.py -x -q` → 3 passed
- CONFIRMED: `uv run pytest tests/api/test_reports.py --collect-only -q` → 6 tests collected, 0 errors
- CONFIRMED: `uv run pytest --collect-only -q` (whole suite) → 40 tests collected, 0 errors
- CONFIRMED: `grep -n "weasyprint.HTML\|WeasyHTML" backend/tests/api/test_reports.py` → only module-level `weasyprint.HTML` target used
- CONFIRMED: `grep -n "score_all_answers\|zen\." backend/tests/api/test_reports.py` → no matches (ZEN engine unmocked)

---
*Phase: 12-test-retrofit-stabilize-existing-flows*
*Completed: 2026-07-22*
