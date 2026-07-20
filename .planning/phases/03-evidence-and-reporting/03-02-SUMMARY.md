---
phase: 03-evidence-and-reporting
plan: 02
subsystem: api
tags: [fastapi, sqlmodel, jinja2, postgresql, react, upsert, html-report]

# Dependency graph
requires:
  - phase: 03-01
    provides: EvidenceURL model and evidence API — evidence URLs loaded into report
  - phase: 02-questionnaire
    provides: QuestionnaireAnswer model and scoring_engine.score_all_answers()
  - phase: 01-foundation
    provides: Initiative model, user auth, get_current_user, get_zen_engine, get_mami_config deps

provides:
  - ComplianceReport SQLModel with Text html_content and unique initiative_id
  - POST /api/v1/initiatives/{id}/report — generates and upserts HTML report
  - GET /api/v1/initiatives/{id}/report — retrieves stored HTML
  - Jinja2 report_generator.py with matrix builder and per-code findings
  - Branded HTML template with executive summary, 4x3 matrix, findings cards, evidence links
  - Frontend "Generate Report" button (blob URL approach, opens in new tab)

affects: [04-context-frontend, 05-admin-crawling-pdf]

# Tech tracking
tech-stack:
  added: [jinja2 (already installed), sqlalchemy.dialects.postgresql.insert (already used)]
  patterns:
    - Jinja2 FileSystemLoader from Path(__file__).parent.parent / "templates"
    - autoescape=select_autoescape(["html"]) for XSS protection
    - pg_insert on_conflict_do_update on unique initiative_id for report regeneration
    - Blob URL pattern for authenticated HTML report in new browser tab

key-files:
  created:
    - backend/app/models/report.py
    - backend/app/schemas/report.py
    - backend/app/services/report_generator.py
    - backend/app/templates/report.html
    - backend/app/api/v1/reports.py
    - backend/alembic/versions/e5f3a2b4c6d7_add_compliance_report_table.py
    - frontend/src/lib/reports.ts
  modified:
    - backend/app/main.py (reports router added)
    - backend/app/db/base.py (ComplianceReport import for Alembic)
    - backend/app/schemas/questionnaire.py (datetime bug fix)
    - frontend/src/routes/_app/questionnaire.tsx (Generate Report button)

key-decisions:
  - "Jinja2 FileSystemLoader from templates/ dir at Path(__file__).parent.parent — works in Docker"
  - "pg_insert on_conflict_do_update on initiative_id unique index — one report per initiative, regeneration replaces"
  - "Blob URL approach for report viewing — POST returns HTML text, frontend creates Blob, opens in new tab — no auth header issues"
  - "sa_column=Column(Text) for html_content — SQLModel str maps to VARCHAR (too small for full HTML)"
  - "Report regeneration always reflects latest answers and evidence (pulls fresh data on every POST)"

patterns-established:
  - "Jinja2 template context pattern: initiative dict + matrix dict + findings_detail list + count scalars"
  - "Matrix builder: {category: {dimension: {code_id: status}}} — maps FINDING severity or COMPLIANT/NOT_APPLICABLE/UNANSWERED"
  - "FindingsDetail builder: only FINDING-status entries, enriched with code metadata, answers, evidence URLs, next steps"
  - "Blob URL pattern: api.post(responseType: text) -> new Blob([html]) -> URL.createObjectURL() -> window.open()"

# Metrics
duration: 5min
completed: 2026-02-18
---

# Phase 3 Plan 2: Compliance Report Generator Summary

**Jinja2 HTML compliance report with 4x3 MAMI matrix, per-code findings with evidence links, pg_insert upsert storage, and blob URL frontend viewer**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-18T08:18:04Z
- **Completed:** 2026-02-18T08:23:00Z
- **Tasks:** 2 (all complete)
- **Files modified:** 11

## Accomplishments

- ComplianceReport model with `sa_column=Column(Text)` for full HTML storage and `unique=True` on initiative_id for upsert semantics
- Jinja2 report generator service (`report_generator.py`) with `FileSystemLoader` + `autoescape`, matrix builder (4 categories x 3 dimensions), and findings detail enrichment with evidence URLs and next steps
- Branded HTML template (`report.html`) with executive summary with counts/status message, color-coded 4x3 MAMI matrix, per-code finding cards with severity badge + MoSCoW level + answer + rationale + evidence + next steps
- POST endpoint scores all answers via `score_all_answers()`, loads evidence, renders template, upserts via `pg_insert on_conflict_do_update` — regeneration always reflects latest data
- GET endpoint returns stored HTML as `HTMLResponse`
- Alembic migration `e5f3a2b4c6d7` applied in running Docker container
- Frontend: `reports.ts` API lib + "Generate Report" button on questionnaire page using blob URL approach to open report in new tab without auth header issues

## Task Commits

Both tasks executed in a single atomic commit:

1. **Task 1: Backend model, service, template, API, migration** - `46ccfe2` (feat)
2. **Task 2: Frontend reports.ts + questionnaire button** - `46ccfe2` (feat, same commit)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/app/models/report.py` - ComplianceReport SQLModel with Text html_content, unique initiative_id
- `backend/app/schemas/report.py` - ReportRead schema
- `backend/app/services/report_generator.py` - Jinja2 generator with matrix builder, findings detail, next steps
- `backend/app/templates/report.html` - Full branded HTML template (coe-dsc.nl colors, executive summary, 4x3 matrix, per-code cards)
- `backend/app/api/v1/reports.py` - POST (generate+upsert) and GET (retrieve) endpoints with auth
- `backend/alembic/versions/e5f3a2b4c6d7_add_compliance_report_table.py` - compliance_report table migration
- `backend/app/main.py` - Added reports_router import and include_router
- `backend/app/db/base.py` - Added ComplianceReport import for Alembic autogenerate
- `backend/app/schemas/questionnaire.py` - Fixed datetime type bug (answered_at/updated_at)
- `frontend/src/lib/reports.ts` - generateReport() and getReportUrl() API functions
- `frontend/src/routes/_app/questionnaire.tsx` - isGenerating state, handleGenerateReport(), Generate Report button

## Decisions Made

- **Blob URL approach for report viewing:** The GET endpoint requires Bearer auth, so a new tab can't send the token automatically. POST returns the HTML as text; frontend creates a `Blob` and opens `URL.createObjectURL(blob)` — works immediately with no backend changes.
- **sa_column=Column(Text) for html_content:** SQLModel maps plain `str` to VARCHAR which would be too small for a full HTML document.
- **pg_insert on_conflict_do_update on initiative_id:** Guarantees exactly one stored report per initiative; regeneration (another POST) always replaces with fresh content.
- **Jinja2 autoescape enabled:** `select_autoescape(["html"])` escapes all template variables — prevents XSS if user input (names, rationale text) contains HTML.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed AnswerRead schema datetime type mismatch**
- **Found during:** Task 1 verification (checking Docker logs after restart)
- **Issue:** `AnswerRead.answered_at` and `answered_at.updated_at` were typed as `str` but `QuestionnaireAnswer` model returns `datetime` objects — FastAPI raised `ResponseValidationError` 500 on every answer upsert
- **Fix:** Changed both fields to `datetime` in `backend/app/schemas/questionnaire.py`
- **Files modified:** `backend/app/schemas/questionnaire.py`
- **Verification:** Server auto-reloaded, `uv run python -c "from app.schemas.questionnaire import AnswerRead; print('OK')"` passed, no more 500s in logs
- **Committed in:** `46ccfe2` (included in task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Pre-existing bug found incidentally during log inspection. Fix necessary for questionnaire answers to work, which is required for report generation to have data to score.

## Issues Encountered

None beyond the pre-existing questionnaire schema bug. Template rendering, upsert, and frontend blob approach all worked as designed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 is now complete: EvidenceURL subsystem (03-01) + ComplianceReport generator (03-02) both done
- Phase 4 (context frontend) can begin: question context text/images and production frontend from design team
- Phase 5 (admin, crawling, PDF): URL crawling with SSRF prevention, SHA-256 snapshots, WeasyPrint PDF export, admin panel — all deferred intentionally

## Self-Check: PASSED

All created files confirmed present. Migration `e5f3a2b4c6d7` confirmed applied in Docker logs. TypeScript compilation clean. Backend imports clean. Report routes registered and verified in `app.routes`.

---
*Phase: 03-evidence-and-reporting*
*Completed: 2026-02-18*
