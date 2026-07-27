---
phase: 16-report-data-contract-dual-visualization-admin-aggregation
plan: 04
subsystem: frontend-report-admin-consumption
tags: [report-contract, radar-svg, priority-list, admin-aggregation, dangerously-set-inner-html, tanstack-search-params]

dependency_graph:
  requires:
    - phase: 16-02
      provides: "GET /initiatives/{id}/report/data (ReportContract: assessment_id, version, initiative, dimension_scores, priority_list, radar_chart_svg, maturity_bands), optional ?assessment_id= query param, admin bypass"
    - phase: 16-03
      provides: "GET /admin/heatmap (AdminAggregateResponse: org_average_scores, org_radar_chart_svg, initiatives[] with has_data/report_assessment_id)"
  provides:
    - "fetchReportData + ReportContract/PriorityListItem/MaturityBand/DimensionScore types (frontend/src/lib/reports.ts)"
    - "rebuilt /report route rendering the server radar SVG + 6-row priority list, with per-version viewing via search params"
    - "rebuilt /admin/heatmap route rendering the org radar + paginated per-initiative table"
  affects: []

tech-stack:
  added: []
  patterns:
    - "Server-rendered SVG injected verbatim via dangerouslySetInnerHTML — no client-side polygon math or band re-derivation, matches the D-02 backend contract"
    - "Loosely-typed TanStack search params (useSearch cast to Record<string, string|undefined>), mirroring the existing /_auth/login precedent — no validateSearch schema added"
    - "setState-in-effect-clean data fetching: loading/error reset moved to the retry handler (not the effect body) to satisfy eslint-plugin-react-hooks' set-state-in-effect rule"

key-files:
  created: []
  modified:
    - frontend/src/lib/reports.ts
    - frontend/src/routes/_app/report.tsx
    - frontend/src/routes/_app/admin.heatmap.tsx

decisions:
  - "No validateSearch registered on /_app/report — search params read via a loose Record cast (same pattern as the pre-existing /_auth/login route), keeping the route's search type open rather than introducing a new TanStack search-schema convention for this one route"
  - "Admin per-initiative table renders one column per dimension name (derived from org_average_scores) plus an Overall average column, rather than a single collapsed score — matches assessments.tsx's existing comparison-table precedent for showing per-dimension breakdowns in a Table"
  - "Zero-submission org-wide state (org_radar_chart_svg === null) replaces the entire radar+table section with the empty-state Card, rather than rendering an empty table alongside a suppressed chart — matches the UI-SPEC's 'not rendered as a zeroed/degenerate hexagon' requirement"
  - "Task 3 (openapi regeneration) was a stability check, not a new export — 16-02/16-03 already regenerated docs/api/openapi.json for their own backend response-model changes; this plan's changes are frontend-only, so both `export_openapi.py` runs produced zero diff and there is nothing new to commit for this task"

metrics:
  duration: ~45min
  completed: 2026-07-27
status: complete
---

# Phase 16 Plan 04: Report Data Contract Frontend Consumption Summary

**Rebuilt the two consuming surfaces of the Phase 16 report contract — the in-app report page (server-rendered radar SVG + 6-row priority list, with per-version viewing via search params) and the admin aggregation page (org radar + paginated per-initiative table with no-data handling) — retiring all remaining MAMI-era frontend code (HeatmapMatrix, StatusChip, MAMI_CODE_TO_REC_ID/RECOMMENDATIONS, the DSI/SP Tabs split, HeatmapGrid/CountPill).**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-07-27
- **Tasks:** 3 (Task 1 report.tsx/reports.ts, Task 2 admin.heatmap.tsx, Task 3 openapi stability check)
- **Files modified:** 3 (frontend `reports.ts`, `report.tsx`, `admin.heatmap.tsx`) — `docs/api/openapi.json` unchanged (see Decisions)

## Accomplishments

- `frontend/src/lib/reports.ts` gained `ReportContract`/`PriorityListItem`/`MaturityBand`/`DimensionScore`/`ReportInitiative` TypeScript types mirroring `backend/app/schemas/report.py` verbatim, and `fetchReportData(initiativeId, assessmentId?)` — a typed GET wrapper over `/initiatives/{id}/report/data` with an optional `?assessment_id=` query param (D-04). `generateReport`/`getReportUrl` (the existing blob-URL PDF flow) were left untouched.
- `report.tsx` fully rewritten: reads optional `initiative_id`/`assessment_id` from the route's search params (falling back to `/initiatives/me` when `initiative_id` is absent, supporting both the owner's own report and admin/history deep-links), fetches the shared report contract, and renders:
  - the server-generated `radar_chart_svg` injected verbatim via `dangerouslySetInnerHTML` (RPRT-01/D-02 — no client-side polygon math, no client-side band re-derivation) as the primary visual anchor
  - a 6-row priority list, each row pairing a `band_color` dot with the `band_label` text and the 2-decimal score (RPRT-02, color never the sole signal), with `white-space: normal` so long dimension names wrap rather than truncate (the UI-SPEC backstop item)
  - a centered `Spin` loading state and an `Alert` + Retry error state using the exact UI-SPEC copy ("We couldn't load this report. Make sure the assessment has been fully submitted, then try again.")
  - the primary CTA relabeled "Download PDF Report", still using the existing blob-URL fetch approach (now also forwarding `assessment_id` when present)
  - retired dead code removed outright: `HeatmapMatrix`, `StatusChip`, `MAMI_CODE_TO_REC_ID`, `MAMI_CODE_TO_LABELS`, `RECOMMENDATIONS`, `NextStepsPanel`, and the MAMI matrix/topic-structure types
- `admin.heatmap.tsx` fully rewritten: fetches `GET /admin/heatmap` in a single effect (no DSI/SP `type=` split — this aggregation is not type-scoped), typed to `AdminAggregateResponse`. Renders, in order: the page title "Aggregated Maturity Overview"; the org radar via `dangerouslySetInnerHTML` (primary visual anchor) plus a correctly-pluralized summary caption ("1 submitted initiative" / "N submitted initiatives"); and an antd `Table` (`pageSize: 10`, `showSizeChanger: false`) with one column per dimension (derived from `org_average_scores`' names), an Overall average column, an ellipsis+native-title-tooltip name column, and a Report column showing a "View report" link (`/report?initiative_id=&assessment_id=`) for `has_data` rows or a "No data yet" `Tag` otherwise (D-08). The zero-submission org-wide state (`org_radar_chart_svg === null`) renders the "No submitted assessments yet" / "Once an initiative fully completes and submits the questionnaire, its scores will appear here." empty-state Card instead of a degenerate chart+table. Retired the DSI/SP `Tabs` split and `HeatmapGrid`/`CountPill` code outright.
- Task 3 confirmed the docs-freshness gate is already green: `uv run python scripts/export_openapi.py` (run twice) produced zero diff against `docs/api/openapi.json` — expected, since Plans 16-02/16-03 already regenerated the schema for their own backend response-model changes and this plan introduces no backend changes.

## Task Commits

1. **Task 1: Extend reports.ts + rebuild report.tsx** - `b362332` (feat)
2. **Task 2: Rebuild admin.heatmap.tsx** - `50ab97e` (feat)
3. **Task 3: Regenerate/verify docs/api/openapi.json** - no commit (zero diff both runs — nothing to commit, see Decisions)

**Plan metadata:** (this SUMMARY's own commit, made immediately after this file)

## Files Created/Modified

- `frontend/src/lib/reports.ts` - Added `ReportContract`/`PriorityListItem`/`MaturityBand`/`DimensionScore`/`ReportInitiative` types + `fetchReportData`; kept `generateReport`/`getReportUrl` untouched
- `frontend/src/routes/_app/report.tsx` - Full rewrite: server radar SVG render, 6-row priority list, search-param-driven per-version viewing, retired MAMI dead code
- `frontend/src/routes/_app/admin.heatmap.tsx` - Full rewrite: org radar + paginated per-initiative table with no-data handling and empty state, retired DSI/SP tab split

## Verification

- `cd frontend && npx tsc -b --noEmit` — clean (0 errors)
- `cd frontend && npx eslint src/routes/_app/report.tsx src/routes/_app/admin.heatmap.tsx src/lib/reports.ts` — clean (0 errors, 0 warnings)
- `grep -q "dangerouslySetInnerHTML" report.tsx && grep -c HeatmapMatrix report.tsx` → 0 (matrix removed, radar renders)
- `grep -c HeatmapGrid admin.heatmap.tsx` → 0 (grid removed)
- `grep` for client-side band-derivation logic (`score >=`, `getBand`, etc.) in both rewritten routes → none found (RPRT-03 prohibition upheld)
- `cd backend && uv run python scripts/export_openapi.py && git diff --exit-code -- docs/api/openapi.json` (run twice) → exit 0 both times, zero diff (docs-freshness gate green)

## Decisions Made

- No `validateSearch` registered on `/_app/report` — search params (`initiative_id`, `assessment_id`) are read via a loosely-typed `Record<string, string | undefined>` cast, the same pattern already used by `/_auth/login`'s `session`/`reset` query params in this codebase. This avoids introducing a new TanStack search-schema convention for a single route.
- The admin per-initiative table shows one column per dimension (names derived from `org_average_scores`) plus an "Overall average" column, following `assessments.tsx`'s existing per-dimension comparison-table precedent rather than collapsing to a single score column.
- The zero-submission org-wide empty state fully replaces the radar+table section (rather than showing an empty/degenerate chart alongside a no-data table) — matches the UI-SPEC's explicit "not rendered as a zeroed/degenerate hexagon" requirement.
- Task 3 produced no commit: both `export_openapi.py` runs were diff-clean against the already-committed `docs/api/openapi.json` from Plans 16-02/16-03. This is the expected, documented outcome for a frontend-only plan and is not a skipped step — it is the plan's designed verification that no backend contract drift occurred.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Moved `setLoading(true)`/`setError(null)` reset calls out of the fetch `useEffect` body into `handleRetry`**
- **Found during:** Task 1 verification (`npx eslint`)
- **Issue:** The initial `report.tsx` draft called `setLoading(true)`/`setError(null)` synchronously at the top of the data-fetching `useEffect` (needed so a retry click could reset stale error/loading state before refetching). `eslint-plugin-react-hooks`'s `set-state-in-effect` rule (part of this repo's already-bumped `eslint-plugin-react-hooks`, see CLAUDE.md's 2026-07-26 dependency note) flags any direct synchronous `setState` call in an effect body as a potential cascading-render bug.
- **Fix:** Removed the two calls from the effect body (relying on `useState`'s initial `true`/`null` defaults for the mount case, matching the pre-existing `dashboard.tsx`/`admin.heatmap.tsx` effect pattern in this codebase) and moved the reset into `handleRetry`, which now explicitly sets `loading`/`error` before bumping the `retryToken` dependency that re-triggers the effect.
- **Files modified:** `frontend/src/routes/_app/report.tsx`
- **Verification:** `npx eslint src/routes/_app/report.tsx` — 0 errors, 0 warnings (previously 1 error + 1 warning).
- **Committed in:** `b362332` (Task 1 commit — fixed before the commit was made, not a follow-up)

No other deviations — both tasks otherwise executed as written.

### Authentication Gates

None encountered — both routes reuse existing JWT bearer-token auth (`api` client, `/auth/me` admin guard already in place on `admin.heatmap.tsx`'s `beforeLoad`).

## Known Stubs

None. Both routes are fully wired to their respective live backend endpoints (`/initiatives/{id}/report/data`, `/admin/heatmap`) with no hardcoded/placeholder data paths.

## Threat Flags

None beyond what the plan's own `<threat_model>` already covers. `radar_chart_svg`/`org_radar_chart_svg` are injected via `dangerouslySetInnerHTML` exactly as scoped by T-16-02 (server-generated, config category names + numeric scores only, no end-user free text) — the frontend does not construct or modify this SVG string in any way, only passes it through verbatim. The `/report` deep-link (`initiative_id`+`assessment_id` in the URL) carries no authorization weight itself (T-16-06) — every request still re-resolves ownership/admin status server-side via `resolve_report_assessment`/`_get_authorized_initiative` (Plan 16-02).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RPRT-01, RPRT-02, RPRT-04, and ADMN-01 are now fully observable end-to-end: the in-app report renders the server radar + priority list, the admin page renders the org radar + per-initiative table, and both surfaces consume the identical backend contract shapes from Plans 16-02/16-03 with zero client-side score/band re-derivation.
- The WeasyPrint PDF-rendering backstop (radar chart legibility in an actual rendered PDF, flagged in 16-02's SUMMARY as `D8`) remains unverified locally (WeasyPrint native libraries unavailable on this Mac) — still must be checked via CI or Docker before Phase 16's overall `/gsd-verify-work` gate is considered fully closed. This plan's frontend rendering of the identical `radar_chart_svg` string is one input to that same backstop, not a separate risk.
- No further backend contract changes are expected from this phase for the report/admin endpoint groups — Phase 17 (TEST-01, per `deferred-items.md`/CLAUDE.md's perf-gate tolerance note) owns adding dimension-scoring perf coverage and any Playwright E2E coverage for these two rebuilt surfaces.

---
*Phase: 16-report-data-contract-dual-visualization-admin-aggregation*
*Completed: 2026-07-27*
