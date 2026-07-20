---
phase: 06-demo-readiness-admin-panel-password-reset-and-50-user-scalability
plan: 05
subsystem: frontend-auth
tags: [react, tanstack-router, password-reset, auth-flow, file-based-routing]
dependency_graph:
  requires: [06-02, 06-04]
  provides: [forgot-password-ui, reset-password-ui, login-reset-success-banner]
  affects: [frontend/src/routes/_auth/login.tsx, frontend/src/routeTree.gen.ts]
tech_stack:
  added: []
  patterns:
    - useSearch from @tanstack/react-router reads URL search params (token, session, reset)
    - Inline fetch calls for auth routes (matching login.tsx pattern, no api client needed)
    - routeTree.gen.ts manually updated with new _auth routes following existing pattern
key_files:
  created:
    - frontend/src/routes/_auth/forgot-password.tsx
    - frontend/src/routes/_auth/reset-password.tsx
  modified:
    - frontend/src/routes/_auth/login.tsx
    - frontend/src/routeTree.gen.ts
decisions:
  - Manually updated routeTree.gen.ts to include new _auth routes (dev server regenerates on start per existing project decision)
  - Added resetSuccess banner in same location as sessionExpired banner (both use inline style pattern, no Ant Design)
  - Token missing guard in reset-password.tsx renders immediately — no loading state before the conditional check
metrics:
  duration_minutes: 4
  tasks_completed: 2
  files_changed: 4
  completed_date: "2026-03-06"
requirements_satisfied:
  - AUTH-RESET-01
  - AUTH-RESET-02
  - AUTH-RESET-03
  - AUTH-RESET-04
---

# Phase 06 Plan 05: Password Reset Frontend Summary

**One-liner:** Two new TanStack Router auth routes for password reset (forgot-password email form + reset-password token form), with Forgot your password? link and reset-success banner added to login page.

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-06T15:59:51Z
- **Completed:** 2026-03-06T16:03:01Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `forgot-password.tsx`: Email form calling `POST /auth/forgot-password` with inline styles matching login.tsx pattern. Always shows success confirmation state after 202 (no email enumeration). "Back to Sign In" link after submission.
- `reset-password.tsx`: New password form reading `?token=` from URL via `useSearch`. Validates passwords match and are minimum 12 characters. Calls `POST /auth/reset-password`, redirects to `/login?reset=success` on success. Shows 400 error detail from backend (invalid/expired token). Renders token-missing guard immediately if no token in URL.
- `login.tsx`: Added `resetSuccess` state from `?reset=success` URL param. Green success banner renders below the existing session-expired amber banner. "Forgot your password?" link added below the "No account? Register" paragraph. Session-expired banner from 06-04 fully preserved.
- `routeTree.gen.ts`: All sections updated — imports, route object declarations, `FileRoutesByFullPath`, `FileRoutesByTo`, `FileRoutesById`, `FileRouteTypes` unions, `declare module` path declarations, `AuthRouteChildren` interface and const.

## Task Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Create forgot-password and reset-password route files | e47d145 |
| 2 | Add Forgot password? link + reset-success banner to login, update routeTree.gen.ts | c992d87 |

## Files Created/Modified

### Created
- `frontend/src/routes/_auth/forgot-password.tsx` — Email form with sent/unsent states, POST /auth/forgot-password, success confirmation, Back to Sign In link
- `frontend/src/routes/_auth/reset-password.tsx` — Token-based new password form, POST /auth/reset-password, redirects to /login?reset=success, missing-token guard

### Modified
- `frontend/src/routes/_auth/login.tsx` — `resetSuccess` const + green success banner + Forgot your password? link (session-expired banner preserved)
- `frontend/src/routeTree.gen.ts` — Full update for /_auth/forgot-password and /_auth/reset-password routes

## Decisions Made

- **routeTree.gen.ts manual update:** Per existing project decision (routeTree.gen.ts committed to repo, Vite plugin regenerates on dev server start), manually updated all sections to match new route files.
- **resetSuccess banner position:** Added after sessionExpired banner, before the heading — consistent with 06-04 pattern and visible without scrolling.

## Deviations from Plan

None - plan executed exactly as written.

## User Setup Required

None for this plan. Password reset end-to-end requires the backend env vars from 06-02 (RESEND_API_KEY, FRONTEND_URL) for email sending in production. In dev, reset links are logged to console.

## Self-Check: PASSED

All files verified and commits confirmed:
- FOUND: frontend/src/routes/_auth/forgot-password.tsx
- FOUND: frontend/src/routes/_auth/reset-password.tsx
- FOUND: frontend/src/routes/_auth/login.tsx (modified)
- FOUND: frontend/src/routeTree.gen.ts (modified)
- FOUND commit: e47d145
- FOUND commit: c992d87
