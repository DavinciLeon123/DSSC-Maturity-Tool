---
phase: 06-demo-readiness-admin-panel-password-reset-and-50-user-scalability
plan: 04
subsystem: frontend
tags: [react, tanstack-query, autosave, ux-resilience, axios-interceptor, session-expiry]

requires:
  - phase: 06-01
    provides: POST /initiatives/{initiative_id}/submit endpoint

provides:
  - AutosaveBadge component with 4 states (saving/saved/failed/rate-limited)
  - 429 rate-limit badge with 3-second auto-reset
  - Next button disabled while saveMutation is in-flight
  - Submission confirmation screen with Generate Report CTA
  - 401 interceptor redirecting to /login?session=expired
  - Session-expired amber banner on login page

affects:
  - 06-05 (login.tsx updated — password reset banner will be added by 06-05 reading fresh)
  - Any future wizard work — autosave badge pattern established

tech-stack:
  added: []
  patterns:
    - Local badgeState useState preferred over saveMutation.isPending for stable badge UI (avoids TanStack Query cache-time reset pitfall)
    - AutosaveBadge early-return component pattern for clean state-driven rendering
    - submitMutation.mutateAsync() called inside handleNext isFinish branch; setSubmitted(true) via onSuccess
    - useSearch from @tanstack/react-router reads URL search params in login page

key-files:
  created: []
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/routes/_auth/login.tsx
    - frontend/src/components/questionnaire/WizardPage.tsx

key-decisions:
  - "WizardPage lives at components/questionnaire/WizardPage.tsx (not in the route file) — plan referred to route file but actual wizard logic is in component"
  - "badgeState local state used instead of saveMutation.isPending — avoids TanStack Query v5 mutation cache-time reset resetting badge prematurely"
  - "429 auto-retry resets badge to idle after 3 seconds; does not replay last payload (user triggers next save normally)"
  - "isNextDisabled extended to include badgeState === saving — prevents navigation mid-save"

patterns-established:
  - "Autosave badge pattern: local SaveBadgeState enum + AutosaveBadge component + setBadgeState in mutationFn/onSuccess/onError"
  - "Submit flow: handleNext calls submitMutation.mutateAsync() when isFinish; onSuccess sets submitted=true; early return renders confirmation"

requirements-completed:
  - UX-RESIL-01
  - UX-RESIL-02
  - UX-RESIL-03
  - UX-RESIL-04

duration: 2min
completed: 2026-03-05
---

# Phase 06 Plan 04: Frontend UX Resilience (Autosave Badge, Session Expiry, Submit Confirmation) Summary

**Four frontend resilience features implemented: autosave 4-state badge with 429 rate-limit handling, Next button disabled during in-flight saves, 401 session-expiry redirect with amber login banner, and submission confirmation screen with Generate Report CTA.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-05T19:18:17Z
- **Completed:** 2026-03-05T19:20:26Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `api.ts`: 401 interceptor now redirects to `/login?session=expired` — demo users get a clear "session expired" message instead of a silent redirect to the login page
- `login.tsx`: `useSearch` reads `?session=expired` URL param; amber banner ("Your session expired. Please log in again.") renders inline above the Sign In heading using the page's existing inline style pattern (no Ant Design)
- `WizardPage.tsx`: `AutosaveBadge` component with 5 render states (`idle` returns null, `saving` shows grey "Saving...", `saved` shows green "Saved", `failed` shows amber "Save failed — retrying", `rate-limited` shows amber "Too many saves — slow down")
- `WizardPage.tsx`: `saveMutation` extended with `onSuccess`/`onError` callbacks that drive `badgeState`; 429 response triggers rate-limited badge + 3-second auto-reset to idle
- `WizardPage.tsx`: `isNextDisabled` now includes `badgeState === "saving"` — Next/Finish button is disabled while any save is in-flight
- `WizardPage.tsx`: `submitMutation` calls `POST /initiatives/{id}/submit`; `handleNext` in `isFinish` branch awaits `submitMutation.mutateAsync()` instead of navigating directly to dashboard
- `WizardPage.tsx`: Confirmation screen rendered as early return when `submitted === true` — checkmark, "Your submission is complete" heading, and "Generate Report" button navigating to `/dashboard`
- `WizardPage.tsx`: `submitError` shown as red error div if submit API call fails

## Task Commits

1. **Task 1: Enhance api.ts 401 interceptor and add session-expired banner to login page** - `eb44590` (feat)
2. **Task 2: Add 4-state autosave badge, Next button safety, and submission confirmation to WizardPage** - `c1916e7` (feat)

## Files Created/Modified

- `frontend/src/lib/api.ts` — 401 interceptor updated: `/login` → `/login?session=expired`
- `frontend/src/routes/_auth/login.tsx` — `useSearch` import added; `sessionExpired` derived from URL param; amber banner rendered conditionally
- `frontend/src/components/questionnaire/WizardPage.tsx` — `AutosaveBadge` component + `SaveBadgeState` type added before `WizardPage`; `badgeState`/`submitted`/`submitError` state + `submitMutation` added; `saveMutation` extended with badge callbacks; `isNextDisabled` extended; confirmation screen early return added; autosave badge div added above category heading; `submitError` error div added before question cards

## Decisions Made

- **WizardPage actual location:** Plan specified `frontend/src/routes/_app/questionnaire.tsx` as the file to edit, but the questionnaire route file is a thin wrapper — the actual WizardPage component lives at `frontend/src/components/questionnaire/WizardPage.tsx`. Edited the component file directly.
- **Local badgeState vs saveMutation.isPending:** Used local `useState<SaveBadgeState>` instead of reading `saveMutation.isPending` — this gives stable UI behavior across TanStack Query v5's cache-time resets and enables the custom "rate-limited" state that has no direct mutation-state equivalent.
- **429 retry behavior:** Badge resets to idle after 3 seconds; no automatic payload replay (user triggers next save normally after cooldown).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Structural] WizardPage is a component, not in the route file**
- **Found during:** Task 2 setup (reading questionnaire.tsx)
- **Issue:** The plan listed `frontend/src/routes/_app/questionnaire.tsx` as the file to edit for the WizardPage, but that file is only a data-fetching wrapper that renders `<WizardPage>` imported from `frontend/src/components/questionnaire/WizardPage.tsx`
- **Fix:** Edited `WizardPage.tsx` at its actual component path instead
- **Files modified:** `frontend/src/components/questionnaire/WizardPage.tsx`
- **Impact:** None — all plan requirements implemented at the correct location

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- UX resilience complete: autosave feedback, session expiry handling, submission confirmation all implemented
- login.tsx is ready for 06-05 to add `?reset=success` banner and "Forgot password?" link (06-05 reads the file fresh before editing)
- TypeScript compiles cleanly with zero new errors

---
*Phase: 06-demo-readiness-admin-panel-password-reset-and-50-user-scalability*
*Completed: 2026-03-05*

## Self-Check: PASSED

All files found and commits verified:
- frontend/src/lib/api.ts: FOUND
- frontend/src/routes/_auth/login.tsx: FOUND
- frontend/src/components/questionnaire/WizardPage.tsx: FOUND
- .planning/.../06-04-SUMMARY.md: FOUND
- Commit eb44590 (Task 1): FOUND
- Commit c1916e7 (Task 2): FOUND
