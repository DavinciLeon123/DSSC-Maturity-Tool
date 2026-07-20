---
phase: 10-survey-completion-text-fix-scroll-to-top-on-wizard-navigation-remove-my-initiative-tab-100-user-scalability-equal-width-heatmap-pills-admin-aggregated-heatmap
plan: "01"
subsystem: frontend
tags: [ux, wizard, navigation, heatmap, polish]
dependency_graph:
  requires: []
  provides:
    - WizardPage completion heading text fix
    - Scroll-to-top on wizard Next/Previous navigation
    - My Initiative tab removed from TopNav
    - Dashboard button renamed to "Generate Heatmap"
    - Equal-width (90px min) StatusChip pills in report heatmap
  affects:
    - frontend/src/components/questionnaire/WizardPage.tsx
    - frontend/src/components/layout/TopNav.tsx
    - frontend/src/routes/_app/dashboard.tsx
    - frontend/src/routes/_app/report.tsx
tech_stack:
  added: []
  patterns:
    - "window.scrollTo before async save — immediate UX feedback before network round-trip"
    - "minWidth on inline-flex pill for consistent grid alignment"
key_files:
  created: []
  modified:
    - frontend/src/components/questionnaire/WizardPage.tsx
    - frontend/src/components/layout/TopNav.tsx
    - frontend/src/routes/_app/dashboard.tsx
    - frontend/src/routes/_app/report.tsx
decisions:
  - "scrollTo placed before setIsSaving(true) so scroll fires immediately on click, not after save completes"
  - "minWidth: 90px applied universally to StatusChip (not only heatmap context) — legend visually unaffected"
  - "'/initiative' removed from TypeScript union type in navItems to keep type safety consistent with removed array entry"
metrics:
  duration_seconds: 98
  completed_date: "2026-03-10"
  tasks_completed: 2
  files_modified: 4
requirements:
  - UX-10-01
  - UX-10-02
  - UX-10-03
  - UX-10-04
  - UX-10-05
---

# Phase 10 Plan 01: Frontend Polish — Wizard Text, Scroll, Nav, Heatmap Pills Summary

**One-liner:** Five targeted UX fixes — wizard completion heading, immediate scroll-to-top on wizard navigation, My Initiative tab removed, "Generate Heatmap" button label, and 90px equal-width StatusChip pills in the report matrix.

## What Was Built

Four files modified with zero new dependencies, preparing the app for the 100-user breakout session:

1. **WizardPage.tsx** — Completion screen heading changed from "Your submission is complete" to "Thanks for completing the survey." Scroll-to-top (`window.scrollTo({ top: 0, behavior: 'smooth' })`) added at the top of `handleNext` and `handleBack`, immediately after guard check and before any async save logic — ensures scroll fires on click, not after the 1-2 second save round-trip.

2. **TopNav.tsx** — Removed the `{ label: 'My Initiative', to: '/initiative' }` entry from `navItems` array. Also removed `'/initiative' |` from the TypeScript union type annotation to keep the type system consistent.

3. **dashboard.tsx** — Button label changed from "Generate Compliance Report" to "Generate Heatmap". No other props changed (onClick, loading, size, style preserved).

4. **report.tsx** — Added `minWidth: '90px'` and `justifyContent: 'center'` to the `StatusChip` span's inline style. All existing style properties preserved. Applied universally — heatmap cells and legend pills both get consistent width.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | WizardPage — completion heading + scroll-to-top | 2055e5a | WizardPage.tsx |
| 2 | Nav cleanup + dashboard button rename + StatusChip equal-width | 9d92236 | TopNav.tsx, dashboard.tsx, report.tsx |

## Verification Results

All checks passed after execution:

- `npx tsc --noEmit` — clean, no errors
- `grep "Thanks for completing" WizardPage.tsx` — line 349 found
- `grep "scrollTo" WizardPage.tsx` — 2 lines found (lines 232, 253 — handleNext and handleBack)
- `grep "My Initiative" TopNav.tsx` — nothing found (correct)
- `grep "Generate Heatmap" dashboard.tsx` — line 333 found
- `grep "minWidth" report.tsx` — line 95 found in StatusChip style

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `frontend/src/components/questionnaire/WizardPage.tsx` — modified (commit 2055e5a)
- [x] `frontend/src/components/layout/TopNav.tsx` — modified (commit 9d92236)
- [x] `frontend/src/routes/_app/dashboard.tsx` — modified (commit 9d92236)
- [x] `frontend/src/routes/_app/report.tsx` — modified (commit 9d92236)
- [x] Commits verified: 2055e5a, 9d92236

## Self-Check: PASSED
