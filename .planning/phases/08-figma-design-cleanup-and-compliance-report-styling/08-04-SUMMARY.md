---
phase: 08-figma-design-cleanup-and-compliance-report-styling
plan: "04"
subsystem: ui
tags: [react, tanstack-router, antd, figma, homepage, localization]

# Dependency graph
requires:
  - phase: 07-add-mcp-server
    provides: Footer component and landing page route structure at frontend/src/routes/index.tsx
provides:
  - Fully English homepage matching Figma node 154-3458 with CoE DSC logo in nav
affects: [08-figma-design-cleanup-and-compliance-report-styling]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Logo in nav as <img src={logoSrc}> with width 76px, imported from ../assets/logo-coe-dsc.svg"
    - "All public-facing homepage content in English per CONTEXT.md locked decisions"

key-files:
  created: []
  modified:
    - frontend/src/routes/index.tsx

key-decisions:
  - "Nav logo: <img src={logoSrc}> replacing CoE DSC text span — 76px wide, auto height"
  - "Nav buttons: 'Log In' (text link /login) + 'Register' (green button /register)"
  - "Hero headline: 'MAMI - Minimal Agreements for Maximum Interoperability'"
  - "Hero CTAs: 'Start the check' (green /login) + 'Create an account' (outline /register)"
  - "How does it work section: 3 English step cards — Register, Complete questionnaire, Receive report"
  - "MAMI section CTA: 'Get started' linking to /login (green button)"
  - "Footer component preserved from Phase 07-03"

patterns-established:
  - "Homepage nav uses logo <img> not text — consistent with auth screens"

requirements-completed: [UI-FIX-07, UI-FIX-08]

# Metrics
duration: 5min
completed: 2026-03-07
---

# Phase 08 Plan 04: Homepage English Content + CoE DSC Logo Summary

**Homepage fully rewritten in English with CoE DSC logo in nav, Figma-aligned step cards, and MAMI domain description per node 154-3458**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-07T17:21:11Z
- **Completed:** 2026-03-07T17:26:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Replaced all Dutch text with English equivalents per CONTEXT.md locked decisions
- Added CoE DSC SVG logo (76px) to nav replacing plain text
- Updated nav actions: "Log In" + "Register" (was "Inloggen" / "Registreren")
- Updated hero headline, subtitle, and CTA buttons to English
- Updated "How does it work?" section with 3 English step cards
- Updated MAMI section with English heading, body, and "Get started" CTA linking to /login
- TypeScript compiles clean, no Dutch strings remain, logo import confirmed

## Task Commits

Each task was committed atomically:

1. **Task 1: Fetch Figma specs and rewrite homepage with English content + logo** - `e63e511` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/src/routes/index.tsx` - Full rewrite: English content, CoE DSC logo in nav, Figma-aligned layout

## Decisions Made
- Used `<img src={logoSrc}>` at 76px wide in nav (consistent with auth screens approach in Plan 08-03)
- "Get started" CTA in MAMI section links to `/login` (not `/register`) — matches "Start the check" intent
- Removed the "In three steps" subtitle that was Dutch; heading alone is cleaner per Figma node 154-3458

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Homepage is fully English and Figma-aligned
- Ready for Phase 08-05 (compliance report restyle) or other plan tasks
- No blockers

---
*Phase: 08-figma-design-cleanup-and-compliance-report-styling*
*Completed: 2026-03-07*
