---
phase: 14-scoring-engine-replacement
plan: 03
subsystem: api
tags: [fastapi, sqlmodel, postgres, jinja2, reports, dimension-scoring]

requires:
  - phase: 14-scoring-engine-replacement
    provides: "compute_dimension_scores/assert_assessment_complete (Plan 14-01), the scoring.py adaptation pattern for the same completion gate (Plan 14-02)"
provides:
  - "GET/POST /report/data now returns dimension_scores (list of {category_id, name, score}) instead of the old matrix/topic_structure/answers shape"
  - "All four report endpoints (/report, /report/data GET+POST, /report/pdf, /report/mail) enforce the SCOR-04 completion gate ownership-first"
  - "report_generator.py trimmed to initiative-info-only + literal-empty Jinja2 context (all MAMI-matrix/heatmap/recommendation builders deleted, D-01a)"
  - "/admin/heatmap reduced to a fixed trivial degraded response {degraded: true, cells: []} (D-01b)"
affects: [14-04, 16-report-rendering]

tech-stack:
  added: []
  patterns:
    - "Ownership check (404) -> assert_assessment_complete (422) -> report-existence check (404), in that exact order, across all four report routes (T-14-01)"
    - "generate_html_report(initiative, generated_at) renders the unchanged report.html with literal heatmap_rows={}/not_yet_recommendations=[] rather than any builder function"

key-files:
  created: []
  modified:
    - backend/app/services/report_generator.py
    - backend/app/api/v1/reports.py
    - backend/app/api/v1/admin.py
    - backend/tests/api/test_reports.py
    - backend/tests/services/test_report_generator.py
    - backend/tests/api/test_admin.py

key-decisions:
  - "Dropped async/await from all four report route functions (mirrors Plan 14-02's scoring.py precedent) — no awaited calls remain once score_all_answers is removed"
  - "generate_html_report/generate_report_data lost their answers/findings/mami_config parameters entirely rather than accepting them as unused/ignored args"
  - "Renamed test_download_report_pdf_no_answers_returns_422 -> test_download_report_pdf_incomplete_assessment_returns_422 (and the equivalent mail_report test) to match the new 422 semantics (assessment completeness, not answer presence)"
  - "test_reports.py's fixtures now fully answer the real config/dssc-questionnaire.json (52 questions) via _answer_all_questions, mirroring test_scoring.py's Plan 14-02 pattern, since the old n=5 partial-answers fixture now fails the SCOR-04 gate with 422"

requirements-completed: [SCOR-04]

coverage:
  - id: D1
    description: "GET/POST /report/data returns dimension_scores (6 entries, category_id/name/score, scores in 1.0-5.0) for a fully-answered assessment, with matrix/topic_structure/answers entirely absent"
    requirement: "SCOR-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_post_report_data_returns_dimension_scores"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_get_report_data_returns_dimension_scores"
        status: pass
    human_judgment: false
  - id: D2
    description: "All four report endpoints (/report, /report/data GET+POST, /report/pdf, /report/mail) return 422 'Questionnaire not fully answered' for an incomplete assessment"
    requirement: "SCOR-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_generate_report_incomplete_assessment_returns_422"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_post_report_data_incomplete_assessment_returns_422"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_get_report_data_incomplete_assessment_returns_422"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_mail_report_incomplete_assessment_returns_422"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_download_report_pdf_incomplete_assessment_returns_422"
        status: unknown
    human_judgment: false
  - id: D3
    description: "Ownership check (404) always fires before the completion-gate 422, so a non-owner never learns whether an initiative's assessment is complete"
    requirement: "SCOR-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_report_data_ownership_before_completion_gate"
        status: pass
    human_judgment: false
  - id: D4
    description: "report_generator.py's MAMI-matrix/heatmap/recommendation builders (_build_matrix, _build_topic_structure, _build_heatmap_rows, _build_not_yet_recommendations, _build_findings_detail, _aggregate_cell, _suggest_next_steps, _RECOMMENDATIONS, _ANSWER_LABEL_MAP) are deleted outright; generate_html_report still renders the unchanged report.html without raising"
    requirement: "SCOR-04"
    verification:
      - kind: unit
        ref: "backend/tests/services/test_report_generator.py#test_generate_report_data_returns_initiative_only_shape"
        status: pass
      - kind: unit
        ref: "backend/tests/services/test_report_generator.py#test_generate_html_report_renders_non_empty_html_with_initiative_name"
        status: pass
    human_judgment: false
  - id: D5
    description: "/admin/heatmap returns a fixed trivial degraded response ({degraded: true, cells: []}) with no topic-structure-building logic"
    requirement: "SCOR-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_admin.py#test_admin_heatmap_reflects_submitted_initiatives"
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-07-24
status: complete
---

# Phase 14 Plan 03: Report Endpoints and Admin Heatmap Adaptation Summary

**All four report endpoints now enforce the SCOR-04 completion gate ownership-first and `/report/data` emits a new `dimension_scores` field, while `report_generator.py`'s entire MAMI-matrix/heatmap/recommendation subsystem and the degraded-banner mechanism are deleted outright, and `/admin/heatmap` is reduced to a fixed trivial degraded response.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-07-24T09:05Z (approx)
- **Completed:** 2026-07-24T09:27Z
- **Tasks:** 3 completed
- **Files modified:** 6

## Accomplishments
- Deleted `report_generator.py`'s `_RECOMMENDATIONS`, `_ANSWER_LABEL_MAP`, `_build_matrix`, `_build_findings_detail`, `_build_topic_structure`, `_aggregate_cell`, `_build_heatmap_rows`, `_build_not_yet_recommendations`, `_suggest_next_steps` outright (D-01a) — the module is now 22 lines of initiative-info logic plus a literal-empty Jinja2 context, down from 313 lines.
- Rewrote `reports.py`: removed `import zen`, `score_all_answers`, `get_mami_config`/`get_zen_engine`, and the entire degraded-banner mechanism (`_DEGRADED_SCORING_BANNER_HTML`, `_inject_degraded_banner`, `_degraded_scoring_inputs`, D-05a). All four routes now call `assert_assessment_complete` immediately after the ownership check (T-14-01 ordering) instead of the old ad-hoc `if not answers` 422/`degraded` flag; both `/report/data` handlers add `dimension_scores` via `compute_dimension_scores` on top of the simplified `generate_report_data` output.
- Rewrote `admin.py`'s `/heatmap`: removed the orphaned `_build_topic_structure` import and the entire matrix-aggregation body, replacing `AdminHeatmapResponse` (`total_submitted`/`matrix`/`topic_structure`/`degraded`) with a 2-field model (`degraded: bool = True`, `cells: list[dict] = []`) per D-01b.
- Rewrote all three affected test files against the new shapes: `test_report_generator.py` (trimmed contract), `test_reports.py` (dimension_scores present + matrix/topic_structure/answers absent, 422-for-incomplete on all four endpoints, ownership-before-gate ordering — required rebuilding the answer fixtures to fully answer the real 52-question config since the old partial fixture now fails SCOR-04), `test_admin.py` (fixed degraded shape).
- App imports cleanly; ruff/mypy/ruff-format all clean across the backend; 87/91 quick-suite tests pass locally (same 4 pre-existing local-only WeasyPrint/libgobject failures recurring from Phase 13, unrelated — logged in this phase's new `deferred-items.md`).
- Did not regenerate `docs/api/openapi.json` per this plan's explicit prohibition (Plan 14-04 owns it once, after all Wave 2/3 response-model changes land).

## Task Commits

Each task was committed atomically:

1. **Task 1: Trim report_generator.py to initiative info only (delete MAMI-matrix builders)** - `eec2c29` (feat)
2. **Task 2: Adapt the four report endpoints (dimension_scores field, 422 gate, banner removal) and admin /heatmap** - `6b962ea` (feat)
3. **Task 3: Adapt report/admin tests to the new shapes and 422 gate** - `f2dfe52` (test)

**Plan metadata:** (this commit) `docs(14-03): complete report-endpoints-and-admin-heatmap-adaptation plan`

## Files Created/Modified
- `backend/app/services/report_generator.py` - Trimmed to `generate_report_data(initiative)` and `generate_html_report(initiative, generated_at)`; all MAMI-matrix/heatmap/recommendation builders deleted
- `backend/app/api/v1/reports.py` - Removed ZEN/MoSCoW imports and the degraded-banner mechanism; all four routes gate on `assert_assessment_complete` ownership-first; `/report/data` (GET+POST) add `dimension_scores`
- `backend/app/api/v1/admin.py` - Removed orphaned `_build_topic_structure` import; `AdminHeatmapResponse`/`get_admin_heatmap` reduced to a fixed `{degraded: true, cells: []}` response
- `backend/tests/api/test_reports.py` - Rewritten around a fully-answered-config fixture; new dimension_scores/422/ordering assertions
- `backend/tests/services/test_report_generator.py` - Rewritten for the trimmed function signatures/contract
- `backend/tests/api/test_admin.py` - Heatmap test asserts the fixed degraded shape
- `.planning/phases/14-scoring-engine-replacement/deferred-items.md` - New file logging the recurring pre-existing local WeasyPrint gap

## Decisions Made
- Dropped `async`/`await` from all four report routes (`generate_report`, `get_report`, `generate_report_data_endpoint`, `get_report_data_endpoint`, `download_report_pdf`, `mail_report`) — mirrors Plan 14-02's `scoring.py` precedent; nothing awaits once `score_all_answers` is gone.
- `generate_html_report` and `generate_report_data` had their `answers`/`findings`/`mami_config` parameters removed entirely rather than kept-but-unused, matching the plan's explicit signature guidance.
- Renamed the "no answers" 422 tests to "incomplete assessment" (`test_download_report_pdf_incomplete_assessment_returns_422`, `test_mail_report_incomplete_assessment_returns_422`) to reflect the new SCOR-04 completeness semantics rather than the old "answers exist at all" check.
- Rebuilt `test_reports.py`'s fixtures to fully answer the real `config/dssc-questionnaire.json` (52 questions across 6 categories) via a `_answer_all_questions` helper mirroring `test_scoring.py`'s Plan 14-02 pattern — the prior `_initiative_with_answers(n=5)` fixture now fails the completion gate with 422 instead of reaching the endpoint body.
- Added `test_get_report_data_no_report_yet_returns_404_when_complete` to pin the ordering guidance explicitly: a fully-answered assessment with no report ever generated still 404s (report-existence check runs after the completion gate, not instead of it).

## Deviations from Plan

None - plan executed exactly as written. Test rewrites went beyond the plan's literal task-3 description in volume (new ordering test, new "report not yet generated but complete" test) but stay within Task 3's stated behavior/acceptance criteria — no new endpoint or production-code behavior was added beyond what Task 2 specified.

## Issues Encountered
- The pre-existing local-only WeasyPrint/`libgobject-2.0-0` native-library gap (first logged in Phase 13's `deferred-items.md`, recurring across all 4 of that phase's plans) recurred again for the same 4 tests in `test_reports.py`. Confirmed via traceback that the failure is inside `weasyprint`'s cffi import, unrelated to this plan's changes (the unconditional `from weasyprint import HTML as WeasyHTML` import position is unchanged from before). Logged in a new `deferred-items.md` for Phase 14 rather than fixed — CI has the native library installed and is the authoritative signal.

## User Setup Required

None - no external service configuration required. This plan adds no new dependency, no new environment variable, and no new endpoint (only modifies existing ones).

## Next Phase Readiness

- `/report/data`'s new `dimension_scores` field and the SCOR-04 gate are live across all four report endpoints and `/score` (Plan 14-02) — Plan 14-04 can now safely delete the ZEN/MoSCoW dependency (`zen-engine`), `deps.py`'s now-unused `get_zen_engine`/`get_mami_config`, and `main.py`'s ZEN lifespan wiring, since no remaining call site references them.
- `docs/api/openapi.json` was deliberately NOT regenerated this plan (per the plan's explicit prohibition) — Plan 14-04 must regenerate it once, after Wave 2/3's full set of response-model changes (this plan's `AdminHeatmapResponse`, this plan's implicit `/report/data` shape change, Plan 14-02's `ScoreResponse`) have all landed.
- `/admin/heatmap`'s fixed degraded response and `report.html`'s unchanged literal-empty rendering are explicitly interim — Phase 16 (ADMN-01 / report rendering) owns rebuilding both against the new 6-category dimension-score model.
- Full quick suite: 87/91 passing locally (same 4 pre-existing local-only WeasyPrint failures as every prior Phase 13/14 plan touching `reports.py`, unrelated — CI is green on these per CLAUDE.md's documented workflow fix).

---
*Phase: 14-scoring-engine-replacement*
*Completed: 2026-07-24*

## Self-Check: PASSED

- FOUND: backend/app/services/report_generator.py
- FOUND: backend/app/api/v1/reports.py
- FOUND: backend/app/api/v1/admin.py
- FOUND: backend/tests/api/test_reports.py
- FOUND: backend/tests/services/test_report_generator.py
- FOUND: backend/tests/api/test_admin.py
- FOUND: commit eec2c29
- FOUND: commit 6b962ea
- FOUND: commit f2dfe52
