---
phase: 16-report-data-contract-dual-visualization-admin-aggregation
plan: 02
subsystem: backend-report-endpoints
tags: [report-contract, weasyprint, jinja2, idor, admin-bypass, frozen-snapshot]

requires:
  - phase: 16-01
    provides: get_maturity_band, build_priority_list, generate_radar_svg, build_report_contract, config maturity_bands, schemas/report.py (MaturityBand/PriorityListItem/ReportContract)
provides:
  - resolve_report_assessment (submitted-scoped assessment resolver, dimension_scoring.py)
  - rewritten reports.py — all 4 endpoint groups (GET/POST /report, GET/POST /report/data, GET /report/pdf, POST /report/mail) resolve via resolve_report_assessment, accept assessment_id, admin bypass
  - rebuilt report.html — 6-dimension radar + priority list, no MAMI matrix
  - submit-first test_reports.py fixtures proving the post-submission 422 bug is fixed
affects: [16-03, 16-04, 18-secure-phase]

tech-stack:
  added: []
  patterns:
    - "Single submitted-scoped assessment resolver (resolve_report_assessment) — every report/PDF/mail endpoint goes through it, never the draft-scoped assert_assessment_complete/get_current_assessment"
    - "Compute-on-read report contract — no persisted report storage; every read recomputes from the frozen Assessment.dimension_scores snapshot"
    - "Ownership check extended (not weakened) for admin bypass via current_user.role == \"ADMIN\" inside the same 404 branch"

key-files:
  created: []
  modified:
    - backend/app/services/dimension_scoring.py (resolve_report_assessment added)
    - backend/app/api/v1/reports.py (full rewrite — all endpoint groups)
    - backend/app/services/report_generator.py (generate_html_report signature change, generate_report_data removed)
    - backend/app/templates/report.html (full rewrite — 6-dimension radar + priority list)
    - backend/tests/services/test_dimension_scoring.py (resolve_report_assessment tests)
    - backend/tests/services/test_report_generator.py (updated for new generate_html_report signature, removed generate_report_data tests)
    - backend/tests/api/test_reports.py (full rewrite — submit-first fixtures, IDOR/admin/contract-parity tests)
    - docs/api/openapi.json (regenerated — new assessment_id query params)

key-decisions:
  - "resolve_report_assessment raises HTTPException(404, \"Report not found\") on any miss — no submitted assessment, a draft-status id, or a foreign-initiative id all resolve identically (V4, no enumeration leak)"
  - "ComplianceReport upsert deleted outright from reports.py (RESEARCH Pitfall 2, decision A1) — the compliance_report table itself is left unused with no migration this phase; drop deferred to a future cleanup phase"
  - "generate_report_data (report_generator.py) removed outright as dead code — fully superseded by build_report_contract, which reports.py now calls directly"
  - "GET /report no longer requires a prior POST /report — both render fresh from the resolved assessment's contract identically, since there is no stored report to look up anymore"

requirements-completed: [RPRT-04, RPRT-01, RPRT-02]

coverage:
  - id: D1
    description: "resolve_report_assessment resolves a SUBMITTED assessment (latest, or a specific assessment_id) and never uses the draft-scoped assert_assessment_complete/get_current_assessment"
    requirement: "RPRT-04"
    verification:
      - kind: unit
        ref: "backend/tests/services/test_dimension_scoring.py#test_resolve_report_assessment_no_id_returns_latest_submitted"
        status: pass
      - kind: unit
        ref: "backend/tests/services/test_dimension_scoring.py#test_resolve_report_assessment_specific_id_returns_that_one"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /initiatives/{id}/report/data returns HTTP 200 (not 422) with a real report contract after a genuine submit"
    requirement: "RPRT-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_get_report_data_returns_report_contract"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_get_report_data_no_submitted_assessment_returns_404_not_422"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_get_report_data_draft_only_still_returns_404"
        status: pass
    human_judgment: false
  - id: D3
    description: "A report can be opened for any past submitted version via ?assessment_id=, and a foreign assessment_id 404s (never 403, no existence leak)"
    requirement: "RPRT-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_report_data_specific_assessment_id_returns_that_version"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_report_data_foreign_assessment_id_returns_404_idor"
        status: pass
    human_judgment: false
  - id: D4
    description: "An ADMIN can view any initiative's report; a non-admin non-owner still gets 404 (owner check extended, not weakened)"
    requirement: "RPRT-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_admin_can_view_another_users_report"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_non_admin_non_owner_still_gets_404"
        status: pass
    human_judgment: false
  - id: D5
    description: "report.html renders a 6-dimension radar (embedded radar_chart_svg via | safe) and a sorted 6-row priority list, with band dot + label paired (never color-only)"
    requirement: "RPRT-01"
    verification:
      - kind: other
        ref: "backend/app/templates/report.html static check: radar_chart_svg present, human_readable/trust_anchors absent"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_generate_report_returns_html_with_no_persistence"
        status: pass
    human_judgment: false
  - id: D6
    description: "The same radar_chart_svg string and priority_list values appear in both /report/data's JSON and the rendered report.html (one shared contract, two renderings)"
    requirement: "RPRT-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_reports.py#test_report_data_and_html_share_identical_contract_values"
        status: pass
    human_judgment: false
  - id: D7
    description: "reports.py no longer writes to or reads from ComplianceReport — recomputed on every read from the frozen snapshot"
    requirement: "RPRT-02"
    verification:
      - kind: other
        ref: "grep -c ComplianceReport backend/app/api/v1/reports.py == 0"
        status: pass
    human_judgment: false
  - id: D8
    description: "The embedded radar chart renders legibly (labels not clipped, correct font/size) in the actual WeasyPrint PDF output"
    verification: []
    human_judgment: true
    rationale: "Explicit backstop item in this plan's must_haves (verification: backstop) — WeasyPrint's native libraries (Pango/GObject) are unavailable on this local Mac (RESEARCH Pitfall 4), so the actual rendered PDF cannot be visually inspected here. Must be checked via CI or the project's Docker image before this phase is considered fully verified."

duration: ~30min
completed: 2026-07-27
status: complete
---

# Phase 16 Plan 02: Report Data Contract Endpoints Summary

**Rewrote all four report endpoint groups (`/report`, `/report/data`, `/report/pdf`, `/report/mail`) to resolve a submitted assessment via a new `resolve_report_assessment` helper — fixing the phase's primary blocking bug (every endpoint 422ing post-submission) — wired them through the shared `build_report_contract`, rebuilt `report.html` for the 6-dimension radar + priority list, and deleted the version-incompatible `ComplianceReport` persistence path entirely.**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-07-27
- **Tasks:** 3 (Task 1 TDD, Tasks 2/3 direct implementation)
- **Files modified:** 8 (2 source services, 1 route module, 1 template, 3 test files, 1 generated docs file)

## Accomplishments

- `resolve_report_assessment(session, initiative_id, assessment_id=None)` in `dimension_scoring.py` — the sole submitted-scoped assessment resolver every report/PDF/mail endpoint now uses; raises `HTTPException(404)` on any miss (no submitted assessment, a draft-status id, or a foreign-initiative id all resolve identically — no enumeration leak, V4).
- All 6 report route functions in `reports.py` (POST/GET `/report`, POST/GET `/report/data`, GET `/report/pdf`, POST `/report/mail`) rewritten to resolve via `resolve_report_assessment`, accept an optional `assessment_id` query param (D-04, per-version viewing), and extend (not weaken) the ownership guard with an admin bypass (`current_user.role == "ADMIN"`, D-07/T-16-03).
- The `pg_insert(ComplianceReport)...on_conflict_do_update` upsert is deleted outright — every read now recomputes the shared report contract fresh from the frozen `Assessment.dimension_scores` snapshot (falling back to a live `compute_dimension_scores` only for legacy submitted rows with a null snapshot, mirroring `initiatives.py`'s `_to_summary` idiom).
- `report.html` rebuilt: drops the stale 4×3 MAMI matrix (`heatmap_rows`/`not_yet_recommendations` loops, `human_readable`/`machine_readable`/`trust_anchors` chips), embeds the server-generated `radar_chart_svg` via Jinja `| safe`, and renders a 6-row priority list where each row pairs a colored band dot with the band label text (never color-only) plus a maturity-band legend. Navy `#06004f` header/Rubik typography chrome kept, retitled "Your DSSC Maturity Report".
- `test_reports.py` fixtures now build a real SUBMITTED assessment (freezing `dimension_scores` exactly as `POST /initiatives/{id}/submit` does) before hitting any report endpoint — replacing the draft-only fixtures that masked RESEARCH Pitfall 1. New coverage: post-submission 200 (not 422), no-submitted-assessment 404, draft-only-still-404, D-04 specific-`assessment_id` per-version resolution, an IDOR test (foreign `assessment_id` → 404), an admin-bypass test, a non-admin-non-owner-still-404 test, and a contract-parity test proving identical `radar_chart_svg`/`priority_list` values between the JSON contract and the rendered HTML.

## Task Commits

Each task was committed atomically (Task 1 followed the TDD RED→GREEN cycle):

1. **Task 1 RED: resolve_report_assessment — failing tests** - `396ca46` (test)
2. **Task 1 GREEN: resolve_report_assessment implementation** - `f1b1749` (feat)
3. **Task 2: Rewrite reports.py + report_generator.py coordination** - `e645efd` (feat)
4. **Task 3: Rebuild report.html + submit-first test_reports.py** - `1517159` (feat)
5. **Docs: regenerate openapi.json** - `950a964` (docs)

**Plan metadata:** (this SUMMARY's own commit, made immediately after this file)

## Files Created/Modified

- `backend/app/services/dimension_scoring.py` - Added `resolve_report_assessment`, the submitted-only assessment resolver
- `backend/app/api/v1/reports.py` - Full rewrite: all endpoints resolve via `resolve_report_assessment`, accept `assessment_id`, admin bypass, `ComplianceReport` removed
- `backend/app/services/report_generator.py` - `generate_html_report` now takes contract keys directly; `generate_report_data` removed (superseded by `build_report_contract`)
- `backend/app/templates/report.html` - Full rewrite: 6-dimension radar (embedded SVG) + sorted priority list, stale MAMI matrix removed
- `backend/tests/services/test_dimension_scoring.py` - 6 new tests for `resolve_report_assessment`
- `backend/tests/services/test_report_generator.py` - Updated `generate_html_report` test for new signature; removed 2 obsolete `generate_report_data` tests
- `backend/tests/api/test_reports.py` - Full rewrite: submit-first fixtures, 18 tests covering the post-submission fix, D-04, IDOR, admin bypass, contract parity
- `docs/api/openapi.json` - Regenerated for the new `assessment_id` query params (docs-freshness CI gate)

## Decisions Made

- `resolve_report_assessment` raises a single generic `HTTPException(404, "Report not found")` for every miss case (no submitted assessment / draft-status id / foreign-initiative id) — indistinguishable by design, matching the plan's V4 no-enumeration requirement.
- `ComplianceReport` upsert deleted outright from `reports.py` rather than migrated to key off `assessment_id` (RESEARCH Open Question 1, recommendation A1) — the `compliance_report` table itself is left unused with no migration this phase; its drop is deferred to a future cleanup phase, not silently forgotten.
- `generate_report_data` (in `report_generator.py`) removed outright as dead code rather than left orphaned — it is fully superseded by `build_report_contract`, which `reports.py` now calls directly; its 2 tests in `test_report_generator.py` were removed alongside it.
- `GET /report` no longer requires a prior `POST /report` to have run — since there is no stored report to look up anymore, both verbs render identically fresh from the resolved assessment's contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated `report_generator.py`'s `generate_html_report` signature (not in this plan's `files_modified`, but required for Task 2/3 to compile and function)**
- **Found during:** Task 2
- **Issue:** This plan's frontmatter `files_modified` lists only `dimension_scoring.py`, `reports.py`, `report.html`, and `test_reports.py` — but Task 3's own `<action>` text explicitly instructs "Update `generate_html_report`'s context to pass `radar_chart_svg`, `priority_list`, `dimension_scores`, and `maturity_bands` (this signature change is coordinated with plan 16-01 Task 2 and this plan's Task 2)." Task 2's rewritten `reports.py` cannot call the old `generate_html_report(initiative, generated_at)` signature and still deliver RPRT-04's "one shared contract, two renderings" — the file omission from the frontmatter list was a bookkeeping gap, not an instruction to skip the change.
- **Fix:** Changed `generate_html_report` to a keyword-only signature accepting `dimension_scores`/`priority_list`/`radar_chart_svg`/`maturity_bands` directly (the same 4 keys `build_report_contract` returns), and removed the now-fully-superseded `generate_report_data` helper along with its 2 tests in `test_report_generator.py` (dead code — Rule 1 cleanup, since nothing calls it anymore).
- **Files modified:** `backend/app/services/report_generator.py`, `backend/tests/services/test_report_generator.py`
- **Verification:** `pytest tests/services/test_report_generator.py` (6/6 pass); `mypy`/`ruff` clean.
- **Committed in:** `e645efd` (Task 2 commit)

**2. [Rule 3 - Blocking] Regenerated `docs/api/openapi.json`**
- **Found during:** post-Task-3 verification
- **Issue:** This repo's CI enforces a `docs-freshness` gate (`pr.yml`/`staging.yml`/`main.yml`) that regenerates the OpenAPI schema and fails the build on any diff. The new `assessment_id` query params on every report endpoint (and updated docstrings) change the schema; leaving it stale would fail CI on the very next push.
- **Fix:** Ran `uv run python scripts/export_openapi.py`, confirmed a second run produced zero further diff (idempotent).
- **Files modified:** `docs/api/openapi.json`
- **Verification:** Diff limited to the new `assessment_id` query parameters and route docstrings; re-run confirmed stable.
- **Committed in:** `950a964`

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking, required for the plan's own coordinated changes and this repo's CI gate to function)
**Impact on plan:** Both fixes are direct, unavoidable consequences of Task 2/3's own explicit design (the coordinated `generate_html_report` signature change) and this repo's existing CI contract (docs-freshness). No scope creep — no functionality was added beyond what Task 2/3 already required.

## Issues Encountered

- Old `test_reports.py`/`test_report_generator.py` fixtures built draft-only assessments and called the old `generate_html_report(initiative, generated_at)` signature — both failed immediately once Task 2 landed, exactly reproducing RESEARCH Pitfall 1 and confirming the bug was real before the fix. Resolved by Task 3's fixture/template rewrite in the same plan (by design — the plan's own Task 3 action text calls out this coordination explicitly).
- 4 of 18 tests in `test_reports.py` fail locally: `test_mail_report_generates_pdf_and_sends_email`, `test_mail_report_dev_mode_skips_resend_send`, `test_download_report_pdf_returns_pdf_content_type`, `test_download_report_pdf_no_submitted_assessment_returns_404`. All 4 fail with `OSError: cannot load library 'libgobject-2.0-0'` — WeasyPrint's native libraries are unavailable on this local Mac, a pre-existing, well-documented gap recurring in every prior phase touching `reports.py` (Phases 12-15, see `STATE.md`/`deferred-items.md` history) and already fixed in this repo's CI workflows (Phase 12). Not a regression — `download_report_pdf` imports `from weasyprint import HTML as WeasyHTML` unconditionally at the top of the function body (matching the pre-existing pattern), so even the 404-before-rendering test path still triggers the import.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `resolve_report_assessment` and `build_report_contract` (from 16-01) are now the stable, tested contract every downstream surface can build on — Plan 16-03 (frontend `report.tsx`/`admin.heatmap.tsx` rebuild) and 16-04 (admin aggregation) can consume `/initiatives/{id}/report/data`'s JSON shape and the `assessment_id` query param directly, no further backend contract changes expected from those plans for this endpoint group.
- The `compliance_report` table itself still exists in the schema (no migration this phase, per RESEARCH decision A1) — flagged for a future cleanup phase to actually drop it; not a blocker for 16-03/16-04.
- The WeasyPrint PDF-rendering backstop (radar chart legibility in an actual rendered PDF, `D8` above) remains unverified locally — must be checked via CI or Docker before this phase's overall `/gsd-verify-work` gate is considered fully closed.

---
*Phase: 16-report-data-contract-dual-visualization-admin-aggregation*
*Completed: 2026-07-27*
