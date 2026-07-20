---
phase: 04-context-frontend
plan: 03
subsystem: ui
tags: [react, typescript, json-config, questionnaire, wizard]

# Dependency graph
requires:
  - phase: 04-01
    provides: WizardPage.tsx, questionnaire.ts with Category/Topic interfaces
provides:
  - context_text/context_image null fields on every category and topic in both questionnaire configs
  - ContextCallout component (renders explanatory text + image when non-null)
  - WizardPage renders category-level and topic-level callouts above question list
affects: 05-admin-crawling-pdf

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Config-driven optional UI: null fields in JSON config = nothing rendered; non-null = callout appears without code deploy"
    - "Null-guard pattern in component: if (!contextText && !contextImage) return null"

key-files:
  created:
    - frontend/src/components/questionnaire/ContextCallout.tsx
  modified:
    - config/dsi-questionnaire-v2.json
    - config/sp-questionnaire-v2.json
    - frontend/src/components/questionnaire/WizardPage.tsx

key-decisions:
  - "ContextCallout renders on every topic page (not just topicIndex===0) — simpler and the plan explicitly chose this approach"
  - "Category callout appears after category heading, before topic label — design team can provide category-wide context without repeating it per-topic"
  - "Inline ad-hoc topic context div in WizardPage removed and replaced by ContextCallout component for consistency"

patterns-established:
  - "Config-driven callout: edit JSON, callout appears — no code deploy needed"

# Metrics
duration: 3min
completed: 2026-02-20
---

# Phase 4 Plan 3: Question Context Callout Summary

**Config-driven ContextCallout component renders admin-provided text/image above each questionnaire topic — null by default, activated by editing JSON without code changes**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-20T13:31:13Z
- **Completed:** 2026-02-20T13:34:14Z
- **Tasks:** 3
- **Files modified:** 4 (2 JSON configs, 1 new component, 1 WizardPage update)

## Accomplishments
- Both questionnaire configs (DSI + SP) now have `context_text: null` and `context_image: null` on all 4 categories and all 12 topics each
- `ContextCallout` component created — returns null when both props are null/undefined, renders styled left-bordered callout box when either is non-null
- `WizardPage` renders two `ContextCallout` instances per topic page: category-level (after category heading) and topic-level (above question cards)
- Build passes cleanly — 232 modules, zero TypeScript errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Add context_text/context_image fields to both configs** - `e68c484` (chore)
2. **Task 2: Create ContextCallout component** - `4cf8067` (feat)
3. **Task 3: Integrate ContextCallout into WizardPage** - `124c843` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/src/components/questionnaire/ContextCallout.tsx` - Callout box component; returns null when both props null; renders pre-wrap text and/or full-width image
- `config/dsi-questionnaire-v2.json` - Added `context_text: null` and `context_image: null` to 4 categories and 12 topics
- `config/sp-questionnaire-v2.json` - Added `context_text: null` and `context_image: null` to 4 categories and 12 topics
- `frontend/src/components/questionnaire/WizardPage.tsx` - Removed inline ad-hoc topic callout div; imported and rendered ContextCallout at both category and topic level

## Decisions Made
- Rendered category callout on every topic page (not only when `topicIndex === 0`) — plan explicitly specified this simpler approach
- Removed the existing inline topic context `div` (lines 231-245 in prior WizardPage) and replaced with the new `ContextCallout` component — eliminates duplicate logic, ensures consistent styling
- Category callout positioned between category heading and topic sub-heading, matching the plan's specified rendering order

## Deviations from Plan

**1. [Rule 1 - Bug] Removed existing inline topic context callout when integrating ContextCallout**
- **Found during:** Task 3 (Integrate ContextCallout into WizardPage)
- **Issue:** WizardPage already had an ad-hoc inline `div` for topic `context_text` (lines 231-245). If left in place alongside the new `ContextCallout`, topic context would render twice.
- **Fix:** Removed the old inline div and replaced it with `<ContextCallout contextText={currentTopic.context_text} contextImage={currentTopic.context_image} />` — single source of truth, proper component usage
- **Files modified:** `frontend/src/components/questionnaire/WizardPage.tsx`
- **Verification:** Build passes, grep shows 2 ContextCallout render usages (not 3)
- **Committed in:** `124c843` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Auto-fix prevented double-rendering of topic context. No scope creep.

## Issues Encountered
None — all verification checks passed on first attempt.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 04-03 complete. Phase 04-context-frontend is now 2/3 plans done (04-02 deferred).
- Design team can activate context by editing `context_text`/`context_image` in either JSON config — no code deploy needed
- Phase 05-admin-crawling-pdf can proceed

---
*Phase: 04-context-frontend*
*Completed: 2026-02-20*
