---
phase: 11-recommendations-drawer-mail-report-invalid-date-fix-homepage-images-mobile-portrait-fix
plan: 01
subsystem: api, ui
tags: [python, datetime, isoformat, react, svg, homepage, report]

# Dependency graph
requires:
  - phase: 08-figma-design-cleanup-and-compliance-report-styling
    provides: report_generator.py with generated_at field, index.tsx homepage with hero section
provides:
  - ISO 8601 generated_at strings in report_generator.py (fixes Invalid Date on Railway/Linux)
  - Homepage with OBJECTS.svg hero illustration, lines-top.svg and lines-bottom.svg decorations
affects: [report page, homepage, Railway deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "datetime.utcnow().isoformat() + 'Z' for JSON date strings (not strftime) — safe cross-platform ISO 8601"
    - "SVG assets imported as URL strings via Vite default (no ?url or ?react suffix)"

key-files:
  created: []
  modified:
    - backend/app/services/report_generator.py
    - frontend/src/routes/index.tsx

key-decisions:
  - "isoformat() + 'Z' replaces strftime('%Y-%m-%d %H:%M UTC') — JavaScript new Date() requires ISO 8601 on Linux/Railway"
  - "Hero section uses flex row layout (left: headline/CTA, right: OBJECTS.svg) with flexWrap for mobile stacking"
  - "Line decorations use position: absolute inside position: relative main — zIndex 0 keeps them behind content"

patterns-established:
  - "ISO 8601 date strings: always use isoformat() + 'Z' in Python when the value is consumed by JavaScript new Date()"
  - "SVG decorations: import as plain asset URL, render as <img> with aria-hidden='true'"

requirements-completed:
  - INVALID-DATE-FIX-01
  - HOMEPAGE-IMAGES-01

# Metrics
duration: 8min
completed: 2026-03-13
---

# Phase 11 Plan 01: Invalid Date Fix + Homepage SVG Decorations Summary

**ISO 8601 date fix in report_generator.py eliminates "Invalid Date" on Railway, plus OBJECTS.svg hero illustration and lines-top/bottom decorations added to homepage.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-13T20:20:45Z
- **Completed:** 2026-03-13T20:28:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Both `generated_at` strftime calls in report_generator.py replaced with `isoformat() + "Z"` — report date no longer shows "Invalid Date" on Linux/Railway
- Homepage hero section restructured to flex row: headline/CTA on left, OBJECTS.svg geometric illustration on right (wraps vertically on mobile)
- lines-top.svg and lines-bottom.svg added as absolutely-positioned decorations on left edge of page
- TypeScript compilation passes with zero errors after all changes

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix Invalid Date — ISO 8601 in report_generator.py** - `21fde7f` (fix)
2. **Task 2: Add SVG decorations to homepage** - `596dedd` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/app/services/report_generator.py` - Two `generated_at` strings changed from strftime to isoformat() + "Z"
- `frontend/src/routes/index.tsx` - Three SVG imports added; hero inner layout changed to flex row; lines-top/bottom img elements added

## Decisions Made
- Used `isoformat() + "Z"` (not `strftime`) — JavaScript's `new Date()` only reliably parses ISO 8601 strings, and `strftime("%Y-%m-%d %H:%M UTC")` produces a non-standard format that fails on Linux/Railway
- Hero flex row uses `flexWrap: 'wrap'` so OBJECTS.svg stacks below headline on narrow mobile screens
- Line decoration images use `zIndex: 0` with `position: absolute` inside `position: relative` main — content sections naturally stack above at z-index auto (creates stacking context)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Invalid Date bug is resolved — Railway/Linux deployments will now show correctly formatted dates on the report page
- Homepage visual design is complete with all three SVG decorations per Homepage Design.png
- Ready to proceed to 11-02 (recommendations drawer + mail report features)

---
*Phase: 11-recommendations-drawer-mail-report-invalid-date-fix-homepage-images-mobile-portrait-fix*
*Completed: 2026-03-13*
