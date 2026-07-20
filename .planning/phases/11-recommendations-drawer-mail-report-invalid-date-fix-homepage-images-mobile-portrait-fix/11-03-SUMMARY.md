---
phase: 11-recommendations-drawer-mail-report-invalid-date-fix-homepage-images-mobile-portrait-fix
plan: "03"
subsystem: frontend/report
tags: [report, recommendations, mail, mobile, collapse, antd]
dependency_graph:
  requires: [11-02]
  provides: [recommendations-drawer, mail-report-button, mobile-portrait-overflow-fix]
  affects: [frontend/src/routes/_app/report.tsx]
tech_stack:
  added: []
  patterns: [antd-collapse-items-v6, fetch-with-bearer-token, derived-list-from-answers]
key_files:
  created: []
  modified:
    - frontend/src/routes/_app/report.tsx
decisions:
  - "antd Collapse uses items prop (not Collapse.Panel subcomponent) — v6 API"
  - "recommendations derived list filters NOT_THERE_YET and unanswered codes only"
  - "handleMail uses native fetch (not api lib) to match existing pattern in file"
  - "overflow on heatmap card changed to visible; overflowX:auto on inner wrapper for mobile scroll"
metrics:
  duration: "~3 min"
  completed_date: "2026-03-13"
  tasks_completed: 2
  files_modified: 1
---

# Phase 11 Plan 03: Recommendations Drawer + Mail Report + Mobile Portrait Fix Summary

**One-liner:** Mobile-scrollable heatmap, mail-me-the-results button with API call, and collapsible recommendations drawer built from 27-entry static lookup maps.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Fix mobile overflow + update NextStepsPanel with mail button | c5b7b5d | frontend/src/routes/_app/report.tsx |
| 2 | Add recommendations Collapse drawer below the heatmap section | 2fc52bf | frontend/src/routes/_app/report.tsx |

## What Was Built

### Task 1: Mobile overflow fix + Mail button
- Changed heatmap card `overflow: "hidden"` to `overflow: "visible"` so border-radius renders correctly
- Wrapped `<HeatmapMatrix>` in `<div style={{ overflowX: "auto" }}>` so wide table scrolls horizontally on portrait phone screens (390px viewport)
- Added `Collapse` to antd import
- Updated `NextStepsPanel` signature to accept `{ onMail: () => void; isSending: boolean }` props
- Replaced "Schedule an appointment" href Button with "Mail me the results" onClick Button with loading and disabled states
- Added helper text "Our experts will help you translate your results into concrete actions" below button
- Added `isSending` and `mailError` state to `ReportPage`
- Added `handleMail` async function calling `POST /api/v1/initiatives/{id}/report/mail` with Bearer token from localStorage
- Wired `<NextStepsPanel onMail={handleMail} isSending={isSending} />` and error Alert below the Next Steps card

### Task 2: Recommendations Collapse drawer
- Added three module-level constant maps: `MAMI_CODE_TO_REC_ID`, `MAMI_CODE_TO_LABELS`, `RECOMMENDATIONS` (27 entries each)
- Added `recommendations` derived list inside `ReportPage` filtering codes where answers are `NOT_THERE_YET` or absent
- Added antd `<Collapse>` with `items` prop (v6 API, not `<Collapse.Panel>`) collapsed by default (`defaultActiveKey={[]}`)
- Drawer header: "Recommendations for improving your interoperability"
- Each item renders: `<strong>{dimension_label} — {topic_label}</strong> - {recommendation text}`
- Drawer only rendered when `recommendations.length > 0`
- Styled with 16px border-radius, white background, matching card shadow

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `grep -n "overflow.*hidden" report.tsx` returns 0 results (heatmap card no longer clips)
- `grep -n "overflowX.*auto" report.tsx` returns 1 result (HeatmapMatrix wrapper)
- `grep -n "Mail me the results" report.tsx` returns 1 result
- `grep -c "HRA-1.1|MRA-1.1|TA-1.1" report.tsx` returns 19 (entries in static maps matching pattern)
- `grep -n "defaultActiveKey" report.tsx` returns 1 result
- `npx tsc --noEmit` exits 0 — no TypeScript errors

## Self-Check: PASSED

Files verified present:
- frontend/src/routes/_app/report.tsx — FOUND (modified)

Commits verified present:
- c5b7b5d — FOUND (feat(11-03): fix mobile overflow + mail button in NextStepsPanel)
- 2fc52bf — FOUND (feat(11-03): add recommendations Collapse drawer to report page)
