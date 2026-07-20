---
phase: 06-demo-readiness-admin-panel-password-reset-and-50-user-scalability
plan: "06"
subsystem: frontend-admin-panel
tags: [admin, frontend, react, antd, tanstack-router, role-guard]
dependency_graph:
  requires:
    - GET /api/v1/admin/users
    - DELETE /api/v1/admin/users/{user_id}
    - GET /api/v1/admin/initiatives
    - DELETE /api/v1/admin/initiatives/{initiative_id}
    - GET /api/v1/admin/export
    - POST /api/v1/admin/reset-demo
    - GET /api/v1/auth/me
  provides:
    - frontend/src/routes/_app/admin.tsx (AdminPage with 3-tab layout)
    - Sidebar Admin link (conditional on ADMIN role)
    - /_app/admin route registration in routeTree.gen.ts
  affects:
    - frontend/src/components/layout/Sidebar.tsx
    - frontend/src/routeTree.gen.ts
tech_stack:
  added: []
  patterns:
    - TanStack Router flat route pattern (/_app/admin)
    - beforeLoad async role guard redirecting non-ADMIN to /dashboard
    - Ant Design Tabs items API (antd v6)
    - Ant Design Table with expandable rows via expandedRowRender
    - Blob download with axios responseType:blob + createObjectURL (auth-header compatible)
    - Modal.confirm for destructive action confirmation
    - useQuery staleTime:5min for role caching in Sidebar
key_files:
  created:
    - frontend/src/routes/_app/admin.tsx
  modified:
    - frontend/src/components/layout/Sidebar.tsx
    - frontend/src/routeTree.gen.ts
decisions:
  - "routeTree.gen.ts updated manually (Vite dev server not started) — follows exact pattern of existing /_app/* routes"
  - "Sidebar navItems typed with explicit union type to allow /admin alongside other typed routes"
  - "Admin link appended via spread into navItems array (conditional) rather than separate inline conditional"
metrics:
  duration: "2 minutes"
  completed: "2026-03-05"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
requirements_covered:
  - ADMN-DEMO-01
  - ADMN-DEMO-02
  - ADMN-DEMO-03
  - ADMN-DEMO-04
  - ADMN-DEMO-05
---

# Phase 06 Plan 06: Admin Frontend Panel Summary

**One-liner:** Role-protected admin panel at /admin with three tabs (Users expandable rows, Questionnaires, Actions with blob CSV download and demo-reset modal) and a conditional Admin link in the Sidebar for ADMIN-role users.

## What Was Built

### Task 1: Admin panel route (admin.tsx)

Created `frontend/src/routes/_app/admin.tsx` — a TanStack Router flat-layout file route for `/_app/admin`.

**Route guard:** `beforeLoad` calls `GET /auth/me`, redirects non-ADMIN users to `/dashboard`. Redirect errors are rethrown; auth/network errors also redirect to `/dashboard`.

**Three-tab layout using Ant Design `Tabs` items API:**

| Tab | Content |
|-----|---------|
| Users | Table with expandable rows; collapsed row shows email + role tag; expanded row shows participant_type, initiative_name, initiative_status, answer_count, registered date. Delete with Popconfirm (ADMIN rows show "Protected" instead). |
| Questionnaires | Table showing user_email, initiative name, type, status tag, answer count, created date. Delete with Popconfirm. |
| Actions | Download CSV button (blob download via axios, auth-header compatible) + visually distinct red "Reset Demo Data" button (danger+primary) opening Modal.confirm before calling POST /admin/reset-demo. |

**Mutations:** All use `useMutation` with `onSuccess` refetch + `messageApi.success`/`messageApi.error` feedback.

### Task 2: Sidebar + routeTree.gen.ts

**Sidebar.tsx:** Added `useQuery` for `/auth/me` with `staleTime: 5 * 60 * 1000` (5-minute cache). `isAdmin` flag conditionally appends `{ label: "Admin", to: "/admin" }` to the `navItems` array. Non-admin users see no Admin link.

**routeTree.gen.ts:** Manually added `AppAdminRoute` following the exact pattern of existing `/_app/*` routes — import, `.update()` call, all interface entries (`FileRoutesByFullPath`, `FileRoutesByTo`, `FileRoutesById`, `FileRouteTypes`, module augmentation block, `AppRouteChildren`).

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create admin panel route with 3-tab layout | 5fc3613 | frontend/src/routes/_app/admin.tsx |
| 2 | Conditional Admin link in Sidebar + routeTree registration | 7e930df | frontend/src/components/layout/Sidebar.tsx, frontend/src/routeTree.gen.ts |

## Deviations from Plan

None - plan executed exactly as written.

**Routing note:** Dev server was not started to auto-regenerate `routeTree.gen.ts`. Instead the file was updated manually following the same import + registration pattern as `/_app/dashboard` and other existing routes. TypeScript compiled clean with zero errors after manual update.

## Self-Check: PASSED

- FOUND: frontend/src/routes/_app/admin.tsx
- FOUND: frontend/src/components/layout/Sidebar.tsx (modified)
- FOUND: frontend/src/routeTree.gen.ts (modified, includes /_app/admin)
- FOUND: commit 5fc3613 (Task 1 - admin.tsx)
- FOUND: commit 7e930df (Task 2 - Sidebar + routeTree)
- TypeScript: zero new errors
