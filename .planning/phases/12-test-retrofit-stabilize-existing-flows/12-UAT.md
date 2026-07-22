---
status: testing
phase: 12-test-retrofit-stabilize-existing-flows
source: [12-VERIFICATION.md]
started: 2026-07-22T12:05:43Z
updated: 2026-07-22T12:40:51Z
---

## Current Test

number: 2
name: Push this phase's commits to origin and confirm the first GitHub Actions "Test Suite" run passes both jobs
expected: |
  Both jobs green; total workflow duration is short enough to comfortably gate a PR merge
  (no hard SLA was set in CONTEXT.md, but a multi-tens-of-minutes runtime would fail the
  intent of success criterion #4).
awaiting: user response

## Tests

### 1. Run the full Postgres-backed backend suite (`cd backend && uv run pytest`) on a Docker-equipped machine, or via the first GitHub Actions run once this branch is pushed/merged
expected: 37/37 pass; the 3 already-green test_report_generator.py tests continue to pass (total 40/40).
result: issue
reported: "Ran `cd backend && uv run pytest --cov=app --cov-report=term-missing` with Docker Desktop installed and running. Result: 36/40 passed, 4 failed. All 4 failures are in tests/api/test_reports.py (test_mail_report_generates_pdf_and_sends_email, test_mail_report_dev_mode_skips_resend_send, test_download_report_pdf_returns_pdf_content_type, test_download_report_pdf_no_answers_returns_422). Root cause: importing `weasyprint` (a runtime dependency declared in backend/pyproject.toml, not test-only) raises `OSError: cannot load library 'libgobject-2.0-0'` — this machine has no Pango/GLib native libraries installed, which WeasyPrint requires to render PDFs. This is a different gap from the earlier Docker/testcontainers issue. More importantly, `.github/workflows/test.yml`'s backend-tests job only installs uv + Python deps (`uv sync --locked --all-extras`) — it has no step installing the system packages (libpango-1.0-0, libpangoft2-1.0-0, libgdk-pixbuf2.0-0, etc.) WeasyPrint needs on Linux either, so these same 4 tests will very likely fail on the first real GitHub Actions run too, not just locally."
severity: blocker

### 2. Push this phase's commits to origin and confirm the first GitHub Actions "Test Suite" run passes both the `backend-tests` and `frontend-tests` jobs, and note its wall-clock duration
expected: Both jobs green; total workflow duration is short enough to comfortably gate a PR merge (no hard SLA was set in CONTEXT.md, but a multi-tens-of-minutes runtime would fail the intent of success criterion #4).
result: [pending]

## Summary

total: 2
passed: 0
issues: 1
pending: 1
skipped: 0
blocked: 0

## Gaps

- gap_id: G-12-1
  truth: "37/37 Postgres-dependent backend tests pass with zero failures (40/40 combined)"
  status: failed
  reason: "User reported: 36/40 passed, 4 failed in tests/api/test_reports.py — weasyprint fails to import (OSError: cannot load library 'libgobject-2.0-0', missing Pango/GLib system libraries). CI workflow also has no step installing these system libraries, so the same failure is expected on first GitHub Actions run."
  severity: blocker
  test: 1
  artifacts: []
  missing: []
  debug_session: ""
