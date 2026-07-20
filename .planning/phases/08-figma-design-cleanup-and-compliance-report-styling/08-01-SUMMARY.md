---
phase: 08-figma-design-cleanup-and-compliance-report-styling
plan: "01"
subsystem: frontend-questionnaire-wizard
tags: [figma-alignment, i18n, ui-fix, wizard]
dependency_graph:
  requires: []
  provides: [wizard-english-nav, wizard-question-pill-header]
  affects: [frontend/src/components/questionnaire/WizardPage.tsx]
tech_stack:
  added: []
  patterns: [flex-layout-three-element-header]
key_files:
  created: []
  modified:
    - frontend/src/components/questionnaire/WizardPage.tsx
decisions:
  - Three-element flex header row (category title + question pill + autosave badge) chosen over two-row layout — keeps all elements visible without crowding and aligns with Figma top-right pill position
key_decisions:
  - Three-element flex row for card header — pill center-right, badge far right, category title flex:1 left
metrics:
  duration: ~1 min
  completed: 2026-03-07
  tasks_completed: 2
  files_modified: 1
requirements_satisfied:
  - UI-FIX-01
  - UI-FIX-03
---

# Phase 08 Plan 01: Wizard UI Figma Alignment — Question Pill Reposition + English Nav Labels Summary

**One-liner:** Moved "Question X of Y" pill to card header top-right via three-element flex row and replaced Dutch nav labels ("Vorige"/"Volgende"/"Voltooien") with English ("Previous"/"Next"/"Finish").

## What Was Built

Two targeted fixes to `WizardPage.tsx` to align the questionnaire wizard with the approved Figma design and the English language requirement.

### Task 1: Reposition "Question X of Y" Pill to Card Header Top-Right

The pill was previously a sibling of the `<h4>` topic label in a flex row below the card header. It is now part of the card header row itself:

- Card header is a three-element flex row: `<h3>` category title (flex:1, left) | question pill (center-right, `marginLeft/Right: 1rem`) | `<AutosaveBadge>` (far right)
- The `<h4>` topic label row is retained but is now a simple `<div>` with no pill sibling
- Pill styling preserved: `rgba(61,82,213,0.16)` background, `#3d52d5` text, `100px` border radius, Rubik 500

### Task 2: Replace Dutch Navigation Labels with English

All three Dutch string literals in the nav button row replaced:

| Before | After |
|--------|-------|
| `← Vorige` | `← Previous` |
| `Volgende →` | `Next →` |
| `Voltooien →` | `Finish →` |

`Saving...` (English) left untouched.

## Verification

- `npx tsc --noEmit` — zero errors after both tasks
- `grep "Vorige\|Volgende\|Voltooien"` — zero matches (PASS)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 0b995da | feat(08-01): move Question X of Y pill to card header top-right |
| Task 2 | 7fb89aa | feat(08-01): replace Dutch nav labels with English equivalents |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `frontend/src/components/questionnaire/WizardPage.tsx` modified and committed
- Commits 0b995da and 7fb89aa confirmed in git log
- Zero Dutch strings in WizardPage.tsx
- TypeScript compiles clean
