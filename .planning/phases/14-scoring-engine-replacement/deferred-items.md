# Deferred Items — Phase 14

Out-of-scope discoveries logged per the executor's scope-boundary rule
(pre-existing issues unrelated to the current task's changes are not
auto-fixed).

## Plan 14-03

### WeasyPrint native library missing on local dev machine (pre-existing, unrelated — recurs from Phase 13)

**Found during:** Task 3 full-suite verification (`uv run pytest tests/ -n auto -m "not perf and not benchmark" -q`).

**Symptom:** The same 4 tests in `backend/tests/api/test_reports.py`
(`test_mail_report_generates_pdf_and_sends_email`,
`test_mail_report_dev_mode_skips_resend_send`,
`test_download_report_pdf_returns_pdf_content_type`,
`test_download_report_pdf_incomplete_assessment_returns_422` — renamed this
plan from `test_download_report_pdf_no_answers_returns_422`, same
underlying test) fail locally with `OSError: cannot load library
'libgobject-2.0-0'` (WeasyPrint/Pango native dependency). The unconditional
`from weasyprint import HTML as WeasyHTML` import at the top of
`download_report_pdf` runs before the ownership/completion-gate checks,
so even the 422 test hits the import failure first — this import position
is unchanged from the pre-Phase-14 code (see Phase 13's
`deferred-items.md`, Plans 13-01 through 13-04, where this exact gap was
first logged and recurred four times).

**Scope check:** Not caused by this plan's changes — the failure traceback
errors inside `weasyprint`'s cffi import, before any of this plan's
reworked `reports.py`/`report_generator.py`/`admin.py` code paths run.

**Action taken:** Not fixed (out of scope — same local-machine environment
gap already tracked in Phase 13's `deferred-items.md`, now recurring a
fifth consecutive plan touching `reports.py`). CI has the native library
installed (per CLAUDE.md's 4 pytest-running workflow fixes) and remains the
authoritative signal; 87/91 quick-suite tests pass locally.

## Plan 14-04

### Perf/benchmark scoring coverage intentionally quiet until Phase 17 (D-08)

**Found during:** Task 2 (deleting the legacy scoring perf/benchmark tests
and their `conftest.py` fixtures).

**Context:** `backend/tests/perf/test_scoring_perf.py`
(`test_score_all_answers_p95`) and
`backend/tests/benchmark/test_scoring_regression.py`
(`test_score_all_answers_output_distribution`) were deleted outright in this
plan (SCOR-03) — both exercised the now-removed `scoring_engine.py`/ZEN
engine via the `make_answers` synthetic-answer fixture, which was deleted
alongside them since they were its only consumers. This means there is
currently **no** `perf`- or `benchmark`-marked test covering the new
equal-weight `compute_dimension_scores` scoring path (`dimension_scoring.py`,
Plan 14-01) — CI's `perf-gate` job and the `staging.yml`/`main.yml`
`benchmark`-marked test selection will simply collect zero tests for this
area until new ones exist.

**Action taken:** Not written this plan — out of scope per this plan's
`<action>` spec, which only calls for deletion + a deferral note here. Phase
17 (TEST-01) owns authoring the equal-weight-scoring perf (p95 latency) and
benchmark (deterministic output-distribution regression) replacements against
`compute_dimension_scores`, mirroring the deleted tests' shape but driven by
`config/dssc-questionnaire.json` instead of the deleted MAMI config. This gap
is intentional, not an oversight.
