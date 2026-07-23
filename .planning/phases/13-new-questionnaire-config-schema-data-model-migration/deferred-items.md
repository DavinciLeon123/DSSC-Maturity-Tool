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
