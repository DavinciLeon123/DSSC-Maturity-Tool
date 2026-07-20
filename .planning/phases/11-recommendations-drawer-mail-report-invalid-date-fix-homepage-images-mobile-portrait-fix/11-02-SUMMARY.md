---
phase: 11-recommendations-drawer-mail-report-invalid-date-fix-homepage-images-mobile-portrait-fix
plan: "02"
subsystem: backend
tags: [mail, pdf, weasyprint, resend, background-tasks, docker]
dependency_graph:
  requires: []
  provides: [POST /initiatives/{id}/report/mail]
  affects: [backend/app/api/v1/reports.py, backend/pyproject.toml, backend/Dockerfile]
tech_stack:
  added: [weasyprint, BackgroundTasks]
  patterns: [lazy-import, dev-fallback, non-blocking-202]
key_files:
  created: []
  modified:
    - backend/app/api/v1/reports.py
    - backend/pyproject.toml
    - backend/Dockerfile
decisions:
  - WeasyPrint import deferred inside _send_report_email (lazy) so module loads without system libs in dev
  - PDF attachment uses list(pdf_bytes) per Resend Python SDK spec (not base64 string)
  - RESEND_API_KEY empty string triggers console fallback — endpoint never fails without key
  - apt packages added only to final Dockerfile stage (not builder) — WeasyPrint has pure-Python wheels
metrics:
  duration_minutes: 3
  completed_date: "2026-03-13"
  tasks_completed: 2
  files_modified: 3
---

# Phase 11 Plan 02: Mail Report Summary

**One-liner:** Non-blocking POST /initiatives/{id}/report/mail endpoint using WeasyPrint PDF generation + Resend attachment with dev fallback when API key is absent.

## What Was Built

Added the backend capability for the "Mail me the results" feature:

1. **WeasyPrint dependency** added to `pyproject.toml` — enables HTML-to-PDF conversion.
2. **Dockerfile system packages** — 6 apt packages (libpango, libpangocairo, libcairo2, libgdk-pixbuf2.0-0, libffi-dev, shared-mime-info) added to the final runtime stage so WeasyPrint can load its native rendering libraries on Railway.
3. **`_send_report_email` helper** — generates PDF from stored HTML via WeasyPrint, attaches as `list(pdf_bytes)` per Resend SDK spec, sends via Resend. Dev fallback: logs to console when `RESEND_API_KEY` is empty.
4. **`POST /initiatives/{id}/report/mail` endpoint** — 202 response, non-blocking via `BackgroundTasks`. Guards: 404 if initiative not owned by user, 404 if no report generated yet.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add WeasyPrint dependency and Dockerfile system packages | dfeb07e | backend/pyproject.toml, backend/Dockerfile |
| 2 | Add POST /initiatives/{id}/report/mail endpoint | e2cef11 | backend/app/api/v1/reports.py |

## Verification Results

- `grep "weasyprint" backend/pyproject.toml` — PASS
- `grep "libpango" backend/Dockerfile` — PASS (final stage only)
- `grep -n "report/mail" backend/app/api/v1/reports.py` — PASS (line 325)
- `grep -n "BackgroundTasks" backend/app/api/v1/reports.py` — PASS (import line 6 + usage lines 6, 328)
- `python -c "import ast; ast.parse(...); print('OK')"` — PASS

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `backend/pyproject.toml` — contains `weasyprint`
- `backend/Dockerfile` — contains `libpango-1.0-0` in final stage apt block
- `backend/app/api/v1/reports.py` — contains `_send_report_email`, `report/mail`, `BackgroundTasks`
- Commit `dfeb07e` — exists
- Commit `e2cef11` — exists
