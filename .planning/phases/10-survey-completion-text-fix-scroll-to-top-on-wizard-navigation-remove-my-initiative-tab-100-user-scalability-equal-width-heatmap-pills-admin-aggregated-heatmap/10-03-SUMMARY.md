---
phase: 10-survey-completion-text-fix-scroll-to-top-on-wizard-navigation-remove-my-initiative-tab-100-user-scalability-equal-width-heatmap-pills-admin-aggregated-heatmap
plan: "03"
subsystem: frontend
tags: [admin, heatmap, route, tanstack-router, antd]
dependency_graph:
  requires: [10-02]
  provides: [admin-aggregated-heatmap-page, admin-heatmap-nav-link]
  affects: [frontend/src/routes/_app/admin.heatmap.tsx, frontend/src/routes/_app/admin.tsx, frontend/src/routeTree.gen.ts]
tech_stack:
  added: []
  patterns: [tanstack-router-file-route, admin-guard-beforeLoad, count-pill-component, css-grid-matrix]
key_files:
  created:
    - frontend/src/routes/_app/admin.heatmap.tsx
  modified:
    - frontend/src/routes/_app/admin.tsx
    - frontend/src/routeTree.gen.ts
decisions:
  - Admin heatmap route registered as flat /_app child (same pattern as /admin) — not nested under /_app/admin — matching project convention
  - Category header rows use solid navy (#06004f) background with white text rather than the light translucent style used in report.tsx, to distinguish the admin view
  - CountPill legend shown inline in subtitle above the matrix using zero-count pills as colour swatches
metrics:
  duration: "3 min"
  completed_date: "2026-03-10"
  tasks_completed: 1
  files_changed: 3
---

# Phase 10 Plan 03: Admin Aggregated Heatmap Frontend Summary

Admin aggregated heatmap page at /admin/heatmap with 9x3 matrix of CountPills (yes/not_yet/n_a) fetched from GET /admin/heatmap, gated by beforeLoad admin guard, plus "View Aggregated Heatmap" button added to /admin panel header.

## What Was Built

### Task 1: Create admin.heatmap.tsx + update admin.tsx link + update routeTree.gen.ts

**Commit:** bf96377

**Files changed:**
- `frontend/src/routes/_app/admin.heatmap.tsx` (created)
- `frontend/src/routes/_app/admin.tsx` (modified)
- `frontend/src/routeTree.gen.ts` (modified)

**What was done:**

1. Created `admin.heatmap.tsx` with:
   - `createFileRoute("/_app/admin/heatmap")` with `beforeLoad` admin guard (exact copy of admin.tsx pattern: checks `/auth/me`, redirects non-admin to `/dashboard`)
   - Local `AdminHeatmapCell` and `AdminHeatmapResponse` TypeScript interfaces matching the backend shape from 10-02
   - `CATEGORY_LABELS` and `DIMENSION_LABELS` duplicated from `report.tsx` exact keys
   - Inline `CountPill` component with green/blue/grey colour configs
   - `AdminHeatmapPage` component: fetches `GET /admin/heatmap` on mount, renders CSS-grid matrix with category group headers (navy bg, white text) + topic rows, each data cell showing 3 CountPills (yes=green, not_yet=blue, n_a=grey), plus a "Back to Admin" link

2. Updated `admin.tsx`:
   - Added `Link` import from `@tanstack/react-router`
   - Restructured page header into a flex row with `<h1>Admin Panel</h1>` on the left and `<Link to="/admin/heatmap"><Button>View Aggregated Heatmap →</Button></Link>` on the right

3. Updated `routeTree.gen.ts` (all 10 required locations per plan):
   - Import: `AppAdminHeatmapRouteImport`
   - Route const: `AppAdminHeatmapRoute` with id `/_app/admin/heatmap`, path `/admin/heatmap`
   - `FileRoutesByFullPath`: `/admin/heatmap`
   - `FileRoutesByTo`: `/admin/heatmap`
   - `FileRoutesById`: `/_app/admin/heatmap`
   - `FileRouteTypes.fullPaths` union: `| '/admin/heatmap'`
   - `FileRouteTypes.to` union: `| '/admin/heatmap'`
   - `FileRouteTypes.id` union: `| '/_app/admin/heatmap'`
   - `declare module` block: `/_app/admin/heatmap` entry
   - `AppRouteChildren` interface + const: `AppAdminHeatmapRoute`

**Verification:** `npx tsc --noEmit` passes with no errors.

## Deviations from Plan

None — plan executed exactly as written.

## Awaiting Checkpoint Verification

The plan includes a `checkpoint:human-verify` gate requiring browser testing before this plan is considered complete. The human verification covers:
1. /admin shows "View Aggregated Heatmap →" button
2. /admin/heatmap renders matrix with category headers + topic rows + 3 dimension columns + count pills
3. Non-admin redirect to /dashboard
4. All Phase 10 plan 01 UX improvements (scroll-to-top, nav cleanup, etc.)

## Self-Check: PASSED

- FOUND: `frontend/src/routes/_app/admin.heatmap.tsx`
- FOUND: commit `bf96377`
