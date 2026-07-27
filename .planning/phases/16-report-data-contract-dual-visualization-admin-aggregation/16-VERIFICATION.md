---
phase: 16-report-data-contract-dual-visualization-admin-aggregation
verified: 2026-07-27T00:00:00Z
status: human_needed
score: 4/5 truths verified
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "The in-app radar chart and the mailed PDF radar chart render identically and legibly (labels not clipped, correct font/size) when the shared contract is fed through WeasyPrint"
    test: "Trigger POST /initiatives/{id}/report/mail (or GET /initiatives/{id}/report/pdf) against a real submitted assessment in CI/Docker or the deployed Integration environment, open the resulting PDF, and visually compare the radar chart + priority list against the same assessment's in-app /report page."
    expected: "The radar polygon, axis spokes, and all 6 axis text labels (including the longest category name, 'Control over Data & Trust') render inside the page bounds with the same Rubik/#06004f styling as the in-app view — no clipped/overlapping text, no missing polygon fill."
    why_human: "WeasyPrint's native libraries (Pango/GObject) are unavailable on this local machine and this phase's 51 commits are still unpushed to any branch that has run CI (git log origin/feature/dssc-real-questionnaire-content..HEAD shows 51 unpushed commits) — no automated or CI evidence exists yet that the shared radar_chart_svg string actually renders correctly once it passes through WeasyPrint's PDF rasterizer, only that the same string is passed to both surfaces."
human_verification:
  - test: "Trigger POST /initiatives/{id}/report/mail (or GET /initiatives/{id}/report/pdf) against a real submitted assessment in CI/Docker or the deployed Integration environment, open the resulting PDF, and visually compare against the in-app /report page for the same assessment."
    expected: "Radar chart and priority list render identically (same scores, same band colors, same 6 axis labels) in both the in-app view and the PDF; labels are not clipped and text uses the specified Rubik/#06004f styling."
    why_human: "WeasyPrint native libs unavailable locally; branch not yet run through CI. This is the plan's own explicitly-flagged 'verification: backstop' item (16-02 must_haves D8), still open per both 16-02-SUMMARY.md and 16-04-SUMMARY.md's 'Next Phase Readiness' notes."
  - test: "Open the in-app /report page for an assessment scored against the category 'Control over Data & Trust' (the longest current config category name) at a normal desktop viewport width and confirm the priority-list row wraps the name onto a second line rather than truncating or overflowing the card."
    expected: "The dimension name wraps cleanly within the priority-list row; the row layout does not break or overflow horizontally."
    why_human: "This phase's must_haves (16-04) explicitly flag this as a held-out visual check (verification: backstop) — `white-space: normal` is confirmed present in both report.tsx and report.html's CSS, but actual wrap rendering at real viewport widths was not visually inspected as part of this verification."
---

# Phase 16: Report Data Contract, Dual Visualization & Admin Aggregation Verification Report

**Phase Goal:** Completed assessments produce one frozen report data contract that powers a radar chart and a sorted priority list identically in-app and in the mailed PDF, and the admin view aggregates this same 6-dimension data across initiatives.
**Verified:** 2026-07-27
**Status:** human_needed
**Re-verification:** No — initial verification

## Context: Code Review + Fix Cycle Already Ran

A code review (`16-REVIEW.md`) found 2 Critical + 6 Warning issues; a fix pass (`16-REVIEW-FIX.md`) claims all 8 were resolved. This verification independently re-read every touched file and re-ran the relevant tests rather than trusting either report's claims. All 8 fixes were confirmed present and correctly wired in the current code (see "Anti-Patterns / Review-Fix Cross-Check" below) — none were claimed-but-missing.

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | On completing the questionnaire, the user sees a radar/spider chart showing all 6 dimension scores at a glance | ✓ VERIFIED | `generate_radar_svg` (backend/app/services/report_generator.py:112-186) produces one `<svg viewBox=...>` with 6 axis labels + 1 polygon; `report.tsx:263-268` injects `data.radar_chart_svg` verbatim via `dangerouslySetInnerHTML`; confirmed via `test_radar_svg_structure` and `test_get_report_data_returns_report_contract` (pytest, passing) |
| 2 | The same report shows a sorted priority list (lowest→highest maturity) with dimension name, average score, and red/orange/green color indicator | ✓ VERIFIED | `build_priority_list` (report_generator.py:87-109) always returns 6 rows, stable-sorted ascending; `report.tsx` `PriorityRow` renders `band_color` dot + `band_label` + `score.toFixed(2)` (never color-only); `report.html:157-166` mirrors the same fields; `test_priority_list_six_rows_sorted`/`test_priority_list_tie_stable` pass |
| 3 | Color-band thresholds (1.0-2.0 / 2.0-3.5 / 3.5-5.0) are defined in exactly one place in config and produce identical banding in both the chart and the priority list | ✓ VERIFIED | `config/dssc-questionnaire.json`'s `maturity_bands` key (verified via direct JSON read: red/orange/green with exact hex `#d64545`/`#e08e2b`/`#399e5a`); `get_maturity_band` is the sole classification function, called by both `build_priority_list` and `generate_radar_svg` (confirmed via grep — no second inequality chain anywhere in `backend/app` or `frontend/src`); `admin_aggregation.py` reuses `generate_radar_svg` rather than reimplementing; `test_maturity_band_same_for_both_callers` passes |
| 4 | The user can view this report in-app and receive the same report as a mailed PDF, both rendered from one shared JSON data contract rather than two independently computed views | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `build_report_contract` is called once per request and its 4 shared keys (`dimension_scores`/`priority_list`/`radar_chart_svg`/`maturity_bands`) feed both `/report/data`'s JSON response and `generate_html_report`'s Jinja context (`reports.py:88-103`, confirmed by reading `_render_html_for`); `test_report_data_and_html_share_identical_contract_values` passes, proving the **contract-sharing code path** is correct. However, the plan's own must_haves flag "the embedded radar chart renders legibly in the actual WeasyPrint PDF output" as an explicit `verification: backstop` item that neither this phase's executor nor this verification could exercise — WeasyPrint's native libraries are unavailable locally, and the branch has 51 unpushed commits with no CI run yet (confirmed via `git log origin/...HEAD` and `gh run list`, which shows no workflow run touching this phase's commits). The data-sharing mechanism is proven; the rendered-PDF visual outcome is not |
| 5 | An admin can view an aggregated radar/priority view across initiatives using the new 6-category model, replacing the old 4x3 topic heatmap | ✓ VERIFIED | `build_admin_aggregate` (admin_aggregation.py) returns `org_average_scores`/`org_radar_chart_svg`/`initiatives`; `GET /admin/heatmap` returns `AdminAggregateResponse`; `admin.heatmap.tsx` renders the org radar + paginated per-initiative `Table`; `grep -c "degraded=True" app/api/v1/admin.py` → 0 (old stub fully removed); 17/17 `test_admin.py` + 7/7 `test_admin_aggregation.py` pass |

**Score:** 4/5 truths verified (1 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `config/dssc-questionnaire.json` (`maturity_bands` key) | 3 bands, exact hex colors | ✓ VERIFIED | Confirmed via direct JSON parse: red/orange/green, `#d64545`/`#e08e2b`/`#399e5a`, thresholds 1.0/2.0/3.5/5.0 |
| `backend/app/services/report_generator.py` (`get_maturity_band`, `build_priority_list`, `generate_radar_svg`, `build_report_contract`) | Pure contract-core functions | ✓ VERIFIED | All 4 present, read, and unit-tested; boundary rule (2.0→orange, 3.5→green) matches plan spec exactly |
| `backend/app/schemas/report.py` (`MaturityBand`, `PriorityListItem`, `ReportContract`) | Pydantic contract types | ✓ VERIFIED | Present; now wired as `response_model=ReportContract` on both `/report/data` routes (WR-03 fix confirmed in `reports.py:180,197`) — no longer dead code |
| `backend/app/services/dimension_scoring.py` (`resolve_report_assessment`) | Submitted-scoped resolver | ✓ VERIFIED | Present at dimension_scoring.py:87-121; filters `status == submitted`; raises 404 (not 403/422) on any miss; does not call `get_current_assessment`/`assert_assessment_complete` |
| `backend/app/api/v1/reports.py` (4 endpoint groups, `assessment_id`, admin bypass, `ComplianceReport` removed) | Rebuilt endpoints | ✓ VERIFIED | `grep -c "ComplianceReport" reports.py` → 0; all 6 route functions accept `assessment_id: int | None` and call `resolve_report_assessment`; admin bypass via `current_user.role != "ADMIN"` inside the 404 branch |
| `backend/app/templates/report.html` | 6-dim radar + priority list, no MAMI matrix | ✓ VERIFIED | Embeds `{{ radar_chart_svg | safe }}`; renders 6-row priority list with band dot + label; no `human_readable`/`trust_anchors` tokens present |
| `backend/app/services/admin_aggregation.py` (`build_admin_aggregate`) | Cross-initiative aggregation | ✓ VERIFIED | Present; `generate_radar_svg` imported and called (not reimplemented); CR-01's `StopIteration` crash bug confirmed fixed (`next(..., None)` + skip) |
| `backend/app/api/v1/admin.py` (`AdminAggregateResponse`, `AdminInitiativeAggregateRow`, rebuilt `/heatmap`) | Real response models | ✓ VERIFIED | `degraded=True` stub gone (grep confirms 0 hits); real Pydantic models present and used |
| `frontend/src/lib/reports.ts` (`fetchReportData`, `ReportContract` types) | Typed fetch client | ✓ VERIFIED | Present; types mirror backend schema field-for-field |
| `frontend/src/routes/_app/report.tsx` | Radar + priority list render, search params | ✓ VERIFIED | Renders `dangerouslySetInnerHTML` for radar; reads `initiative_id`/`assessment_id` from search params; falls back to `/initiatives/me`; no client-side band derivation (grep confirms) |
| `frontend/src/routes/_app/admin.heatmap.tsx` | Org radar + paginated table | ✓ VERIFIED | Renders org radar, `Table` with `pageSize: 10`; empty state scoped correctly after WR-02 fix; dimension columns matched on stable `category_id` after WR-01 fix |
| `docs/api/openapi.json` | Regenerated, diff-clean | ✓ VERIFIED | Re-ran `scripts/export_openapi.py` independently — `git diff --exit-code` returns 0 (confirmed clean at verification time) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `get_maturity_band` | `build_priority_list` + `generate_radar_svg` | direct function call, both call sites | ✓ WIRED | Confirmed by reading both call sites; no duplicated inequality logic found anywhere else in `backend/app` or `frontend/src` |
| `resolve_report_assessment` | all 6 report route functions in `reports.py` | direct call at top of each handler | ✓ WIRED | Confirmed — every one of `generate_report`, `get_report`, `generate_report_data_endpoint`, `get_report_data_endpoint`, `download_report_pdf`, `mail_report` calls it |
| `build_report_contract` | JSON response (`/report/data`) AND `generate_html_report`'s Jinja context | shared dict, single computation | ✓ WIRED | `_render_html_for` builds the contract once and passes its keys straight into `generate_html_report`; `/report/data` returns the same dict shape directly; `test_report_data_and_html_share_identical_contract_values` passes |
| `admin_aggregation.build_admin_aggregate` | `generate_radar_svg` (report_generator.py) | import + direct call | ✓ WIRED | `grep -c "generate_radar_svg" admin_aggregation.py` → 3 (import, docstring, call site) |
| `report.tsx` / `admin.heatmap.tsx` | backend `radar_chart_svg` / `org_radar_chart_svg` | `dangerouslySetInnerHTML` | ✓ WIRED | No client-side SVG construction or band re-derivation found in either file |
| admin "View report" link | `/report?initiative_id=&assessment_id=` | `<Link>` with `search` prop, re-checked server-side | ✓ WIRED | `admin.heatmap.tsx:128-133`; ownership/admin bypass re-verified server-side by `resolve_report_assessment`/`_get_authorized_initiative` regardless of the link's params (no client-trust shortcut) |

### Behavioral Spot-Checks / Test Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend lint | `uv run ruff check .` | All checks passed | ✓ PASS |
| Backend format | `uv run ruff format --check .` | 70 files already formatted | ✓ PASS |
| Backend types | `uv run mypy app --ignore-missing-imports` | 0 issues, 35 files | ✓ PASS |
| Report/admin/scoring unit tests | `pytest tests/services/test_report_generator.py tests/services/test_admin_aggregation.py tests/services/test_dimension_scoring.py -q` | 27 passed | ✓ PASS |
| Report API tests | `pytest tests/api/test_reports.py -q` | 31 passed, 4 failed (WeasyPrint `libgobject-2.0-0` OSError — pre-existing local-only environment gap, confirmed unrelated to this phase's logic; same 4 tests documented as failing in 16-02-SUMMARY.md before this verification ran) | ⚠️ Known local gap (not a phase regression) |
| Admin API tests | `pytest tests/api/test_admin.py -q` | 17 passed | ✓ PASS |
| Full quick suite | `pytest tests/ -n auto -m "not perf and not benchmark" -q` | 146 passed, 4 failed (same WeasyPrint gap) | ✓ PASS (modulo known gap) |
| Frontend types | `npx tsc -b --noEmit` | 0 errors | ✓ PASS |
| Frontend lint | `npx eslint src/routes/_app/report.tsx src/routes/_app/admin.heatmap.tsx src/lib/reports.ts` | 0 errors/warnings | ✓ PASS |
| Docs freshness | `uv run python scripts/export_openapi.py && git diff --exit-code -- docs/api/openapi.json` | Exit 0, zero diff | ✓ PASS |

The 4 failing `test_reports.py` cases (`test_mail_report_generates_pdf_and_sends_email`, `test_mail_report_dev_mode_skips_resend_send`, `test_download_report_pdf_returns_pdf_content_type`, `test_download_report_pdf_no_submitted_assessment_returns_404`) all fail identically with `OSError: cannot load library 'libgobject-2.0-0'` — WeasyPrint's native rendering dependency is genuinely absent on this Mac, a documented, pre-existing gap recurring since Phase 12 (per CLAUDE.md's SBOM/test history and prior phases' SUMMARYs), not something introduced or left broken by Phase 16.

### Anti-Patterns / Review-Fix Cross-Check

All 8 findings from `16-REVIEW.md` were independently re-verified in the current codebase (not just trusted from `16-REVIEW-FIX.md`'s claims):

| Finding | Fix Claimed | Independently Confirmed |
|---------|-------------|--------------------------|
| CR-01 (admin org-average `StopIteration` crash on config-drift) | `next(..., None)` + skip | ✓ Confirmed at `admin_aggregation.py:107-121`; regression test `test_org_average_excludes_stale_snapshot_category_mismatch_no_crash` present and passing |
| CR-02 (CSV formula injection) | `_csv_safe()` helper | ✓ Confirmed at `admin.py:28-37`, applied to `initiative_name` at the `writer.writerow` call; regression test present and passing |
| WR-01 (admin table matched on mutable `name`) | Match on `category_id` | ✓ Confirmed at `admin.heatmap.tsx:111` |
| WR-02 (per-initiative table hidden on empty org) | Table renders unconditionally | ✓ Confirmed — `admin.heatmap.tsx:195-244` scopes the empty state to the radar card only; table at line 249 is outside the `isOrgEmpty` ternary |
| WR-03 (`ReportContract` dead code, `{}` in OpenAPI) | `response_model=ReportContract` added | ✓ Confirmed at `reports.py:180,197`; re-ran `export_openapi.py` independently, diff-clean |
| WR-04 (zero-question category → out-of-range score → `ValueError`) | Fail-fast at config-load | ✓ Confirmed in `mami_config.py` — raises `ValueError` naming offending category if any category has zero questions |
| WR-05 (unescaped category name in SVG `<text>`) | `xml_escape()` added | ✓ Confirmed at `report_generator.py:173` (`xml_escape(s["name"])`); dedicated regression test present and passing |
| WR-06 (duplicate hardcoded API base URL) | Reuse `api.defaults.baseURL` | ✓ Confirmed at `report.tsx:156` |

No new anti-patterns (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers, empty stub returns, hardcoded empty data) were found in any of the 17 files this phase touched.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RPRT-01 | 16-01, 16-04 | Radar/spider chart visualizing all 6 dimension scores | ✓ SATISFIED | Code-verified above; REQUIREMENTS.md marked `[x]` Complete |
| RPRT-02 | 16-01, 16-04 | Sorted priority list w/ name, score, color indicator | ✓ SATISFIED | Code-verified above; REQUIREMENTS.md marked `[x]` Complete |
| RPRT-03 | 16-01 | Color-band thresholds defined once, shared by chart + list | ✓ SATISFIED (code) — ⚠️ NOT reflected in REQUIREMENTS.md | `get_maturity_band` confirmed as sole classification function via grep + code read; **but** `.planning/REQUIREMENTS.md` still shows `RPRT-03` as `[ ]` unchecked / "Pending" in both the checklist and the Traceability table — unlike RPRT-01/02/04 and ADMN-01, which each got a dedicated `docs(16-0N): mark ... complete` commit, no commit in this phase's history ever flipped RPRT-03's checkbox (confirmed via `git log -p -- .planning/REQUIREMENTS.md`). This is a bookkeeping gap, not a functional one — the code satisfies the requirement — but it means the project's own source-of-truth traceability document currently under-reports this phase's completion. Recommend a follow-up commit updating `.planning/REQUIREMENTS.md` to mark RPRT-03 complete. |
| RPRT-04 | 16-02, 16-04 | In-app + PDF share one JSON contract | ⚠️ SATISFIED (contract-sharing code) — PDF-legibility backstop unverified | See Truth #4 above; REQUIREMENTS.md marked `[x]` Complete, which is defensible for the contract-sharing mechanism but the plan's own PDF-rendering backstop item remains open |
| ADMN-01 | 16-03, 16-04 | Admin aggregated 6-category view | ✓ SATISFIED | Code-verified above; REQUIREMENTS.md marked `[x]` Complete |

No orphaned requirements: all 5 requirement IDs declared across the phase's 4 plans (`RPRT-01`, `RPRT-02`, `RPRT-03`, `RPRT-04`, `ADMN-01`) match exactly the 5 IDs the task specified and the 5 IDs `.planning/REQUIREMENTS.md`'s Traceability table maps to Phase 16.

### Human Verification Required

1. **WeasyPrint PDF radar/priority-list legibility (RPRT-04 backstop)**
   **Test:** Trigger `POST /initiatives/{id}/report/mail` or `GET /initiatives/{id}/report/pdf` against a real submitted assessment via CI or Docker (where WeasyPrint's native libs are available), open the resulting PDF, and compare it against the same assessment's in-app `/report` page.
   **Expected:** The radar chart (polygon + 6 axis labels, including "Control over Data & Trust") and the priority list render identically to the in-app view — correct band colors, no clipped/overlapping text, no missing polygon fill.
   **Why human:** WeasyPrint's native libraries (`libgobject-2.0-0`) are unavailable on this local machine, and this phase's commits have not yet been pushed through any CI run (51 commits ahead of `origin/feature/dssc-real-questionnaire-content`, confirmed via `git log` and `gh run list`). This is the plan's own explicitly-flagged backstop item (16-02 must_haves), still open per both SUMMARYs' "Next Phase Readiness" sections.

2. **Long dimension-name wrapping in the priority list (RPRT-02/UI-SPEC backstop)**
   **Test:** Open the in-app `/report` page for an assessment and visually confirm the "Control over Data & Trust" priority-list row wraps its name onto a second line at normal viewport widths, rather than truncating or breaking the card layout.
   **Expected:** The dimension name wraps cleanly; the row layout does not overflow or break.
   **Why human:** Explicitly flagged in 16-04's must_haves as `verification: backstop` — `white-space: normal` is confirmed present in the CSS (both `report.tsx` and `report.html`), but the actual rendered wrap behavior was not visually inspected.

### Gaps Summary

No functional gaps were found. All 8 code-review findings (2 Critical, 6 Warning) were independently confirmed fixed and correctly wired in the current codebase — this is not merely trusting `16-REVIEW-FIX.md`'s claims. All plan-level must-haves for the 4 plans in this phase are satisfied in code and covered by passing automated tests (146/150 backend tests pass; the 4 failures are a pre-existing, documented, environment-only WeasyPrint gap unrelated to this phase's logic).

Two items route to human verification rather than blocking the phase: (1) the plan's own explicitly-flagged WeasyPrint PDF-legibility backstop, which cannot be exercised without CI/Docker or a pushed branch, and (2) a visual long-name-wrap check, also explicitly flagged as a backstop in the plan's own must_haves. Neither reflects a code defect found during this verification — both are pre-declared "cannot verify locally" items the plan authors themselves called out.

One documentation-only issue was found: `.planning/REQUIREMENTS.md` still shows `RPRT-03` as Pending/unchecked despite the requirement being functionally satisfied in code (confirmed via the same evidence used for the RPRT-03 truth above) — recommend a follow-up commit to correct this so the traceability document accurately reflects the phase's actual completion state.

---

_Verified: 2026-07-27_
_Verifier: Claude (gsd-verifier)_
