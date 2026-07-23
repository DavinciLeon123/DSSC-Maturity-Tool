# Deferred Items — Phase 13

Out-of-scope discoveries logged per the executor's scope-boundary rule
(pre-existing issues unrelated to the current task's changes are not
auto-fixed).

## Plan 13-01

### WeasyPrint native library missing on local dev machine (pre-existing, unrelated)

**Found during:** Task 3 full-suite verification (`uv run pytest tests/ -n auto -m "not perf and not benchmark" -q`).

**Symptom:** 4 tests in `backend/tests/api/test_reports.py` fail locally with
`OSError: cannot load library 'libgobject-2.0-0'` (WeasyPrint/Pango native
dependency, imported lazily inside `_send_report_email`/PDF endpoints per
the Phase 11 decision in CLAUDE.md).

**Scope check:** None of the 4 files this plan modifies
(`config/dssc-questionnaire.json`, `backend/app/services/mami_config.py`,
`backend/app/core/deps.py`, `backend/app/main.py`,
`backend/app/api/v1/questionnaire.py`) are imported by
`backend/app/api/v1/reports.py` or `backend/app/services/report_generator.py`
— confirmed via import grep. This is a local-machine environment gap (the
native library is installed in CI's Docker/Linux images per CLAUDE.md's
4 pytest-running workflow fixes, but not present on this macOS dev machine),
not a regression introduced by this plan.

**Action taken:** Not fixed (out of scope — pre-existing, unrelated file).
Logged here per the scope-boundary rule rather than auto-fixed or silently
ignored. CI (which has the native library installed) is the authoritative
signal for these 4 tests; `test_dssc_config.py` and `test_questionnaire.py`
(this plan's own tests) both pass locally and are unaffected.

## Plan 13-02

### Same WeasyPrint native-library gap recurs (still pre-existing, still unrelated)

**Found during:** Task 2 full-suite verification (`uv run pytest tests/ -n auto -m "not perf and not benchmark" -q`).

**Symptom:** The same 4 tests in `backend/tests/api/test_reports.py` fail
locally with `OSError: cannot load library 'libgobject-2.0-0'`. This plan's
Task 2 does modify `reports.py`/`report_generator.py` directly (stripping
`evidence_by_code` plumbing), but the failure is the WeasyPrint/Pango native
import inside `download_report_pdf`/`mail_report`, not anything touched by
this plan's edits — confirmed by reading the failure traceback (it errors
inside `weasyprint`'s cffi import, before any of this plan's changed code
paths run).

**Action taken:** Not fixed (out of scope — same local-machine environment
gap as Plan 13-01, already tracked above). CI has the native library
installed and remains the authoritative signal; 41/45 quick-suite tests pass
locally, including this plan's own new `test_evidence_removed.py`.

## Plan 13-03

### Same WeasyPrint native-library gap recurs a third time (still pre-existing, still unrelated)

**Found during:** Task 3 full-suite verification (`uv run pytest tests/ -n auto -m "not perf and not benchmark" -q`).

**Symptom:** The same 4 tests in `backend/tests/api/test_reports.py`
(`test_mail_report_generates_pdf_and_sends_email`,
`test_mail_report_dev_mode_skips_resend_send`,
`test_download_report_pdf_returns_pdf_content_type`,
`test_download_report_pdf_no_answers_returns_422`) fail locally with
`OSError: cannot load library 'libgobject-2.0-0'`. This plan's Task 3
rewrites `reports.py` extensively (assessment-first answer fetching,
degraded scoring), but the failure traceback confirms it errors inside
`weasyprint`'s cffi import (triggered by the unconditional
`from weasyprint import HTML as WeasyHTML` at the top of
`download_report_pdf`, and by `mocker.patch("weasyprint.HTML")` needing to
import the real module before it can patch it) — before any of this plan's
changed code paths run. This import statement's position (unconditional,
before the ownership/answers checks) is unchanged from the pre-Phase-13
code; not introduced or altered by this plan.

**Action taken:** Not fixed (out of scope — same local-machine environment
gap as Plans 13-01/13-02, already tracked above). CI has the native library
installed and remains the authoritative signal; 60/64 quick-suite tests pass
locally, including this plan's own new `tests/schemas/test_questionnaire_schemas.py`
(16 tests).

## Plan 13-04

### Same WeasyPrint native-library gap recurs a fourth time (still pre-existing, still unrelated)

**Found during:** Task 3 full-suite verification (`uv run pytest tests/ -n auto -m "not perf and not benchmark" -q`).

**Symptom:** The same 4 tests in `backend/tests/api/test_reports.py`
(`test_download_report_pdf_returns_pdf_content_type`,
`test_mail_report_generates_pdf_and_sends_email`,
`test_mail_report_dev_mode_skips_resend_send`,
`test_download_report_pdf_no_answers_returns_422`) fail locally with
`OSError: cannot load library 'libgobject-2.0-0'`. This plan (13-04) touches
only `backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py`
and `backend/tests/migrations/`, neither of which is imported by
`reports.py`/`report_generator.py` — confirmed by reading the same
WeasyPrint/cffi import failure trace as Plans 13-01/13-02/13-03.

**Action taken:** Not fixed (out of scope — same local-machine environment
gap, already tracked above, now recurring a fourth consecutive plan). CI has
the native library installed and remains the authoritative signal; 68/72
quick-suite tests pass locally, including this plan's own 3 new
`tests/migrations/test_v1_archive_migration.py` tests (the BLOCKING
migration-verification gate, all green).
