---
phase: 07-add-mcp-server
plan: "07-02"
subsystem: ui

tags: [react, antd, tanstack-router, topnav, drawer, layout]

# Dependency graph
requires:
  - phase: 07-01
    provides: antd ConfigProvider with DSC design tokens (navy #06004f, green #399e5a, Rubik font)

provides:
  - TopNav.tsx component with sticky header, hamburger button, and antd Drawer navigation
  - App shell updated to flex-col layout with green-tinted content background

affects:
  - 07-03 (public landing page — _app layout now flex-col; TopNav visible on all authenticated routes)
  - 07-04 (login/register redesign — logout target confirmed as /login after redirect fix)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TopNav with antd Drawer: hamburger opens right-side slide-out nav (replaces sidebar)"
    - "Sticky header: position sticky, top 0, zIndex 100 — remains visible on scroll"
    - "Conditional admin link: useQuery(['current-user-role']) drives isAdmin check"

key-files:
  created:
    - frontend/src/components/layout/TopNav.tsx
  modified:
    - frontend/src/routes/_app.tsx
    - frontend/src/components/layout/TopNav.tsx (redirect fix commit 925c038)
    - frontend/src/routes/_auth/index.tsx (redirect fix commit 925c038)

key-decisions:
  - "MCP unavailable — used fallback design tokens from plan spec (white navbar, #06004f text, #399e5a accent)"
  - "Logo placeholder: 'CoE DSC' text rendered until frontend/src/assets/logo-coe-dsc.svg is provided by user"
  - "Logout navigates to /login (not /) — fixed in 925c038 after infinite redirect loop discovered at /"
  - "Sidebar.tsx retained (not deleted) — no longer imported by _app.tsx"

patterns-established:
  - "TopNav pattern: sticky white header 64px with left logo + right hamburger, Drawer for full nav list"

requirements-completed:
  - FRNT-SHELL-01

# Metrics
duration: ~30min
completed: "2026-03-07"
---

# Phase 07 Plan 02: Top Navbar + App Shell Summary

**Sticky white top navbar (64px) with antd Drawer navigation replaces left sidebar; app shell switched to flex-col with green-tinted background**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-03-07T08:22Z (approx)
- **Completed:** 2026-03-07T09:29Z
- **Tasks:** 4 (T1 fallback, T2 create, T3 update, T4 verify approved)
- **Files modified:** 3 (TopNav.tsx created, _app.tsx updated, _auth/index.tsx fixed)

## Accomplishments

- Created `TopNav.tsx` — sticky white header with CoE DSC text placeholder on left, hamburger + "Menu" label on right, all using DSC design tokens from 07-01
- Replaced left sidebar with antd Drawer (right side, 280px) containing all nav links with active state highlighting (green #399e5a) and admin-conditional link
- Updated `_app.tsx` shell to flex-col layout with green-tinted background (`rgba(57,158,90,0.1)`), auth guard unchanged
- Fixed infinite redirect loop at `/` by correcting logout target from `/` to `/login`

## Task Commits

1. **Task 1: Get Figma design context (MCP fallback)** — no commit (context gathering, MCP unavailable, fallback applied)
2. **Task 2+3: Create TopNav.tsx + Update _app.tsx** — `9e1ad7d` (feat)
3. **Task 4: Verify top navbar (auto-fix redirect loop)** — `925c038` (fix)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `frontend/src/components/layout/TopNav.tsx` — New sticky top navbar with hamburger, antd Drawer, nav links, logout
- `frontend/src/routes/_app.tsx` — Sidebar replaced by TopNav; layout changed to flex-col; green-tinted background added
- `frontend/src/routes/_auth/index.tsx` — beforeLoad redirect corrected from `/` to `/login`

## Decisions Made

- MCP tool unavailable at execution time — used fallback design tokens specified in the plan (white navbar, DSC navy `#06004f`, green `#399e5a`)
- Logo: `frontend/src/assets/logo-coe-dsc.svg` not yet provided by user — "CoE DSC" text placeholder rendered with Rubik font
- Logout navigation changed from `/` to `/login` after discovering redirect loop (unauthenticated / redirected to /login, which redirected back to / creating a loop)
- `Sidebar.tsx` retained on disk per plan spec — just no longer imported

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed infinite redirect loop: logout now navigates to /login**
- **Found during:** Task 4 (human-verify checkpoint — user observed redirect loop)
- **Issue:** `TopNav` logout handler navigated to `/` (root). The public landing page at `/` was not yet the auth redirect target; `_auth/index.tsx` redirected unauthenticated users from `/` → `/login`, creating a loop.
- **Fix:** Changed logout `navigate({ to: '/' })` to `navigate({ to: '/login' })` in `TopNav.tsx`; also corrected `_auth/index.tsx` to redirect to `/login` (not `/`)
- **Files modified:** `frontend/src/components/layout/TopNav.tsx`, `frontend/src/routes/_auth/index.tsx`
- **Verification:** Logout now lands on `/login` cleanly with no redirect loop
- **Committed in:** `925c038`

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug)
**Impact on plan:** Essential correctness fix for logout flow. No scope creep.

## Issues Encountered

- Figma MCP tool unavailable — plan included explicit fallback instructions. Design tokens from plan spec used directly. No impact on output quality.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Top navbar and app shell complete — all authenticated routes now render with top nav + drawer
- 07-04 (login/register redesign) can proceed; logout target is confirmed as `/login`
- SVG logo `frontend/src/assets/logo-coe-dsc.svg` still outstanding — when provided, replace the text placeholder in `TopNav.tsx` (import + img tag, commented in code)

---
*Phase: 07-add-mcp-server*
*Completed: 2026-03-07*
