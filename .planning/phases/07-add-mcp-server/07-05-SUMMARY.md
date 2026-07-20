---
phase: 07-add-mcp-server
plan: "07-05"
subsystem: ui
tags: [react, figma, questionnaire, wizard, inline-styles, rubik]

# Dependency graph
requires:
  - phase: 07-01
    provides: antd ConfigProvider with DSC brand tokens, Rubik font loaded in index.html
  - phase: 07-02
    provides: top navbar layout, _app.tsx shell updated
provides:
  - Questionnaire wizard restyled to match Figma "Vragen flow" screens
  - Two-column layout: sticky progress panel left + white question card right
  - Vertical stacked choice cards with green-border selection state
  - "Not yet, but planning to" label for NOT_THERE_YET answer option
affects:
  - 07-06-PLAN (dashboard/initiative/about/admin — same design token patterns)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Two-column wizard layout (StepPills sticky left panel + question card flex:1 right)
    - Inline style objects with design tokens (#06004f, #399e5a, rgba(61,82,213,0.16))
    - Choice card pattern (radio-indicator + label, green border on selected)

key-files:
  created: []
  modified:
    - frontend/src/components/questionnaire/AnswerButtonGroup.tsx
    - frontend/src/components/questionnaire/StepPills.tsx
    - frontend/src/components/questionnaire/WizardPage.tsx

key-decisions:
  - "Questionnaire wizard two-column layout: StepPills sticky left (260px) + question card flex:1 right (max 1100px)"
  - "Question X of Y chip shows range (Questions N-M of T) when topic has multiple questions"
  - "Next button: navy fill when active, outlined/muted when isNextDisabled — clear affordance"
  - "Previous button labeled 'Vorige' (Dutch), Next labeled 'Volgende' per Figma — matches product language"
  - "MCP unavailable fallback used: design values taken from CONTEXT.md Specific Ideas section"

patterns-established:
  - "Choice card: white bg, 1px solid rgba(6,0,79,0.15) default, 1px solid #399e5a selected, radio circle indicator left"
  - "Progress panel: sticky, 260px, white, 16px radius, done=green circle+checkmark, current=navy circle, pending=outline circle"
  - "Question chip: rgba(61,82,213,0.16) bg, #3d52d5 text, 100px border-radius (pill), 0.8125rem font"

requirements-completed:
  - FRNT-WIZARD-01
  - FRNT-INIT-01

# Metrics
duration: 20min
completed: 2026-03-07
---

# Phase 07 Plan 05: Questionnaire Wizard Summary

**Questionnaire wizard restyled to match Figma "Vragen flow": two-column layout with sticky progress panel, vertical choice cards with green-border selection, "Question X of Y" chip, and outlined navy Previous/Next buttons**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-07T09:00:00Z
- **Completed:** 2026-03-07T09:20:00Z
- **Tasks:** 4 implementation tasks complete (T5 awaits human verify)
- **Files modified:** 3

## Accomplishments

- Restyled `AnswerButtonGroup.tsx`: horizontal button row replaced with vertical stacked choice cards — white bg, green border on selection, radio-style circle indicator, "Not yet, but planning to" label
- Restyled `StepPills.tsx`: horizontal pills replaced with sticky left panel (260px, white, 16px radius), "Your progress" heading, three circle states (done=green+checkmark, current=navy, pending=outline)
- Restyled `WizardPage.tsx`: two-column layout (StepPills left + question card right), white question card (16px radius, 2.5rem padding), "Question X of Y" chip with purple tint, outlined navy Previous/Next buttons — all state logic preserved

## Task Commits

Each task was committed atomically:

1. **Task T2: Update AnswerButtonGroup** - `7ea4e22` (feat)
2. **Task T3: Restyle StepPills** - `79f251d` (feat)
3. **Task T4: Restyle WizardPage** - `a1d4245` (feat)

**Plan metadata:** (final docs commit — pending T5 human-verify)

## Files Created/Modified

- `frontend/src/components/questionnaire/AnswerButtonGroup.tsx` — Vertical choice cards, updated NOT_THERE_YET label to "Not yet, but planning to", radio circle indicator
- `frontend/src/components/questionnaire/StepPills.tsx` — Vertical progress panel with circle state indicators and connector lines
- `frontend/src/components/questionnaire/WizardPage.tsx` — Two-column layout, question card with chip, outlined nav buttons, all state logic preserved

## Decisions Made

- Two-column layout uses `maxWidth: 1100px` to accommodate both panels comfortably
- "Question X of Y" chip shows a range (`Questions N–M of T`) when a topic contains multiple questions, single format for single-question topics
- Next button: navy fill (#06004f) when active, muted outlined when disabled — provides clear affordance beyond just cursor change
- Dutch button labels: "Vorige" / "Volgende" per Figma language — consistent with product language
- MCP tool unavailable in this environment — fell back to CONTEXT.md "Specific Ideas" values (all token values were explicitly documented there)

## Deviations from Plan

None — plan executed exactly as written. All design values from CONTEXT.md matched the Figma specs listed in the plan tasks.

## Issues Encountered

None. TypeScript (`tsc --noEmit`) passed with zero errors after all changes.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Questionnaire wizard fully restyled to Figma spec
- All state logic (badgeState, isNextDisabled, save-on-navigate, Promise.all) preserved and verified by TypeScript
- Ready for 07-06 (dashboard/initiative/about/admin restyling) — same design token patterns apply

---
*Phase: 07-add-mcp-server*
*Completed: 2026-03-07*
