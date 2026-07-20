---
phase: 08-figma-design-cleanup-and-compliance-report-styling
plan: "05"
subsystem: api

tags: [fastapi, python, report, json, compliance]

# Dependency graph
requires:
  - phase: 03-evidence
    provides: EvidenceURL model and evidence_by_code loading pattern
  - phase: 06-demo-readiness
    provides: ComplianceReport model with upsert pattern, generate_html_report()
provides:
  - generate_report_data() in report_generator.py returning structured JSON dict
  - POST /initiatives/{id}/report/data endpoint returning JSON report
  - GET /initiatives/{id}/report/data endpoint returning JSON report
  - _build_matrix() updated to use yes/not_yet/n_a/unanswered status values
affects:
  - 08-06 (React /report page — consumes POST /initiatives/{id}/report/data)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "generate_report_data() pattern: same signature as generate_html_report() but returns dict"
    - "GET /data endpoint re-runs scoring on the fly (no JSON storage) to avoid schema changes"

key-files:
  created: []
  modified:
    - backend/app/services/report_generator.py
    - backend/app/api/v1/reports.py

key-decisions:
  - "GET /report/data regenerates from stored answers on-the-fly (no new DB column for JSON)"
  - "_build_matrix() updated in-place: same function used by both HTML and JSON generators"
  - "generate_html_report() and all existing endpoints unchanged for backward compatibility"

patterns-established:
  - "_ANSWER_LABEL_MAP module-level constant for YES/NOT_THERE_YET/NOT_APPLICABLE -> human labels"

requirements-completed: [UI-FIX-09]

# Metrics
duration: 8min
completed: 2026-03-07
---

# Phase 08 Plan 05: Compliance Report Backend JSON API Summary

**Replaced CRITICAL/NON_CRITICAL matrix status with yes/not_yet/n_a and added POST+GET /initiatives/{id}/report/data JSON endpoints for the React /report page**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-07T16:01:07Z
- **Completed:** 2026-03-07T16:09:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Updated `_build_matrix()` to use yes/not_yet/n_a/unanswered status values (replacing CRITICAL/NON_CRITICAL/COMPLIANT/NOT_APPLICABLE/UNANSWERED)
- Added `generate_report_data()` function returning structured JSON dict with initiative metadata, matrix, and annotated answers list
- Added POST `/initiatives/{id}/report/data` endpoint (scores answers, returns JSON)
- Added GET `/initiatives/{id}/report/data` endpoint (checks stored report exists, re-runs scoring, returns JSON)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update report_generator.py matrix status mapping** - `939ded2` (feat)
2. **Task 2: Add JSON report endpoint to reports.py** - `c05738e` (feat)

## Files Created/Modified
- `backend/app/services/report_generator.py` - Added _ANSWER_LABEL_MAP, updated _build_matrix() status values, added generate_report_data()
- `backend/app/api/v1/reports.py` - Added two new /report/data endpoints, imported generate_report_data

## Decisions Made
- GET /report/data regenerates scoring on-the-fly from stored answers rather than adding a JSON storage column — avoids schema/migration changes while keeping the endpoint simple
- _build_matrix() updated in-place so both the HTML template and new JSON generator use the same updated status values

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Local Python env missing jinja2/fastapi/zen deps — used Docker exec for final route verification. No code changes required.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend JSON API ready for 08-06 (React /report page)
- POST `/initiatives/{id}/report/data` returns the full JSON shape documented in the plan interfaces
- Existing HTML report endpoints still work — dashboard "open in new tab" flow unaffected until 08-06 changes it

---
*Phase: 08-figma-design-cleanup-and-compliance-report-styling*
*Completed: 2026-03-07*
