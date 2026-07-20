---
phase: 01-bugfix-retake-questionnaire-save-csv-missing-follow-up-selections-separate-dsi-sp-aggregated-heatmaps
plan: "02"
subsystem: admin
tags: [bugfix, csv-export, heatmap, dsi, sp, tabs, antd]
dependency_graph:
  requires: []
  provides:
    - followup_selections column in CSV export
    - type-filtered admin heatmap endpoint
    - tabbed DSI/SP heatmap frontend
  affects:
    - backend/app/api/v1/admin.py
    - frontend/src/routes/_app/admin.heatmap.tsx
tech_stack:
  added: []
  patterns:
    - antd v6 Tabs with lazy fetch on tab activation
    - LOWER() SQL filter for case-insensitive participant_type matching
    - Semicolon-joined array serialisation for CSV multi-select columns
key_files:
  created: []
  modified:
    - backend/app/api/v1/admin.py
    - frontend/src/routes/_app/admin.heatmap.tsx
decisions:
  - "Used LOWER(participant_type) = :ptype comparison so DB casing (DSI/SP uppercase) doesn't break the filter"
  - "SP tab fetches lazily to avoid an unnecessary API call on page load"
  - "Replaced deprecated antd v6 bodyStyle with styles={{ body }} on Card component"
metrics:
  duration_seconds: 116
  completed_date: "2026-03-15"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 01 Plan 02: CSV followup_selections fix and DSI/SP split admin heatmap Summary

**One-liner:** Added followup_selections column to CSV export (semicolon-joined) and split the admin heatmap into DSI/SP tabs with lazy SP fetch using antd Tabs and a parameterised backend endpoint.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Fix admin.py — add followup_selections to CSV export and type param to heatmap | 2cfe5ea | backend/app/api/v1/admin.py |
| 2 | Restructure admin.heatmap.tsx into tabbed DSI/SP view | ab68c15 | frontend/src/routes/_app/admin.heatmap.tsx |

## What Was Built

### Bug Fix: CSV Missing followup_selections (Bug #2)

The `export_dataset` function in admin.py was missing `qa.followup_selections` from the SQL SELECT, CSV header, and data writerow. Three targeted changes were made:

1. Added `qa.followup_selections` to SQL SELECT clause (between `answer_value` and `followup_other`)
2. Added `"followup_selections"` to the header writerow in the same column position
3. Serialised `followup_selections` (a list stored in the DB) as a semicolon-joined string in the data writerow, with empty string fallback when null/empty

### Feature: Parameterised Heatmap Endpoint

Added an optional `type: Optional[str] = None` query parameter to `get_admin_heatmap`. When provided:
- Builds `AND LOWER(i.participant_type) = :ptype` filter
- Applies the filter to both the COUNT query and the aggregate query
- Uses `LOWER()` on the DB column so "DSI" and "dsi" both match `?type=dsi`

### Feature: Tabbed DSI/SP Admin Heatmap Frontend

Restructured `admin.heatmap.tsx` into two components:

- `HeatmapGrid` — presentational component accepting `data`, `loading`, `error`, and `typeLabel` props; renders the full grid (CountPill, CATEGORY_LABELS, DIMENSION_LABELS) plus the typed footer text
- `AdminHeatmapPage` — tabbed page with two independent fetch states; DSI tab fetches `/admin/heatmap?type=dsi` on mount; SP tab fetches `/admin/heatmap?type=sp` lazily on first activation via `handleTabChange`

Also replaced deprecated `bodyStyle` prop with antd v6 `styles={{ body }}` pattern on the Card component.

## Decisions Made

- `LOWER(participant_type)` comparison ensures DB values like "DSI" (uppercase) match `?type=dsi` (lowercase) without requiring a DB migration
- SP tab uses lazy fetch (`spFetched` guard) to avoid an unnecessary network call when user only needs the DSI view
- `HeatmapGrid` is a plain function component (not exported) since it is only used within this file

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- Python import check: `from app.api.v1.admin import router` — PASSED
- TypeScript check: `npx tsc --noEmit` — PASSED (zero errors)

## Self-Check: PASSED

- `backend/app/api/v1/admin.py` — FOUND, contains `followup_selections`, `type_filter`, `LOWER(i.participant_type)`
- `frontend/src/routes/_app/admin.heatmap.tsx` — FOUND, contains `HeatmapGrid`, `Tabs`, `handleTabChange`, `?type=dsi`, `?type=sp`
- Commit 2cfe5ea — FOUND
- Commit ab68c15 — FOUND
