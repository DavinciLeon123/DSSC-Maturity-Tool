---
phase: 01-bugfix-retake-questionnaire-save-csv-missing-follow-up-selections-separate-dsi-sp-aggregated-heatmaps
plan: 01
subsystem: ui
tags: [react, tanstack-router, useEffect, useRef, questionnaire, report, heatmap]

# Dependency graph
requires: []
provides:
  - report.tsx refetches data on every mount via merged single useEffect
  - WizardPage.tsx saves current topic answers on unmount (nav-away) via ref cleanup
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Merged single useEffect with cancelled flag for sequential async fetches that must re-fire on every mount"
    - "useRef + sync effect pattern for stable cleanup callbacks in React (avoids stale closures in unmount effects)"

key-files:
  created: []
  modified:
    - frontend/src/routes/_app/report.tsx
    - frontend/src/components/questionnaire/WizardPage.tsx

key-decisions:
  - "Keep initiativeId in state (not local variable) so handleMail can still access it after the merged effect resolves"
  - "Use useRef pattern for unmount save — avoids adding saveCurrentTopic to [] dep array which would break unmount-only semantics"
  - "fire-and-forget (void) on unmount save — component is going away, errors cannot be surfaced to user"

patterns-established:
  - "Single merged useEffect with [] deps and cancelled flag: correct pattern for sequential fetches that must re-fire on every TanStack Router navigation (no loader/loaderDeps)"
  - "saveCurrentTopicRef pattern: keep a mutable ref in sync each render, use it in cleanup-only effect — safe stale-closure-free unmount save"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 01 Plan 01: Fix Retake Questionnaire Stale Heatmap Summary

**Merged report.tsx fetch into single cancelled-guard useEffect and added WizardPage.tsx save-on-unmount via useRef cleanup to fix stale heatmap data on nav-away retake.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T19:36:23Z
- **Completed:** 2026-03-15T19:37:47Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Fixed Root cause A: report.tsx two-chained-effect pattern replaced with single merged effect that fires on every component mount, guaranteeing fresh data on every navigation to /report
- Fixed Root cause B: WizardPage.tsx now saves current topic answers on unmount using the ref pattern, so nav-away via the nav bar persists unsaved answers before /report fetches them
- TypeScript compiles with zero errors across the full frontend after both changes

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix report.tsx — merge chained useEffects into single mount effect** - `e8d13aa` (fix)
2. **Task 2: Fix WizardPage.tsx — save-on-unmount via ref cleanup** - `98b784b` (fix)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `frontend/src/routes/_app/report.tsx` - Replaced two chained useEffects with one merged effect using cancelled flag; fetches /initiatives/me then chains into /report/data POST sequentially on every mount
- `frontend/src/components/questionnaire/WizardPage.tsx` - Added useRef import; added saveCurrentTopicRef + sync effect + unmount cleanup effect to save current topic on nav-away

## Decisions Made
- Keep `initiativeId` in state rather than a local variable — `handleMail` uses it outside the effect and must read it after the async fetch resolves
- Use `useRef` + sync-effect pattern (not `useCallback` with dep array) for the unmount save — this is the established React pattern to avoid stale closures in cleanup-only effects without adding deps that would break unmount-only semantics
- `void saveCurrentTopicRef.current()` — fire-and-forget: component is unmounting, errors cannot be shown to the user and awaiting would be unsafe

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

One ordering concern resolved: the initial placement of `saveCurrentTopicRef` was above `saveMutation` (before `saveCurrentTopic` was defined in the function body). Moved ref initialization and effects to immediately after `saveCurrentTopic` function declaration — correct placement, no functional change needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Both root causes of the stale heatmap bug are fixed
- Manual verification recommended: navigate away from /questionnaire mid-edit via nav bar, then check /report shows updated answers
- Ready for next plan in phase 01 (CSV missing follow-up selections fix)

---
*Phase: 01-bugfix-retake-questionnaire-save-csv-missing-follow-up-selections-separate-dsi-sp-aggregated-heatmaps*
*Completed: 2026-03-15*
