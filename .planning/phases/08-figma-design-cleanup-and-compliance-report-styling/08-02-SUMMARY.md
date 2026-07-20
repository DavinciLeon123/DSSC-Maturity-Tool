---
phase: 08-figma-design-cleanup-and-compliance-report-styling
plan: "02"
subsystem: frontend-questionnaire
tags: [ui, questionnaire, sidebar, accordion, figma]
dependency_graph:
  requires: []
  provides: [accordion-topic-sidebar]
  affects: [StepPills, WizardPage]
tech_stack:
  added: []
  patterns: [accordion-expand, inline-styles, figma-token-colors]
key_files:
  created: []
  modified:
    - frontend/src/components/questionnaire/StepPills.tsx
    - frontend/src/components/questionnaire/WizardPage.tsx
decisions:
  - "Topic list rendered as static divs (not buttons) — navigation is cursor:default, no onClick"
  - "Accordion shows topics only for active category; non-active categories remain collapsed"
  - "Three topic states: active (navy dot + bold), completed (green dot), future (muted, no dot)"
  - "marginLeft 36px aligns topic sub-list past the category circle indicator"
metrics:
  duration: "5 min"
  completed_date: "2026-03-07"
  tasks_completed: 1
  files_modified: 2
---

# Phase 08 Plan 02: Accordion Topic Sidebar Summary

**One-liner:** Accordion-style topic sub-list in progress sidebar — active category expands to show topic names with navy/green/muted state indicators.

## What Was Built

Updated the questionnaire progress sidebar (StepPills) to display topic (sub-category) names under the currently active category in an accordion pattern. Non-active categories remain collapsed, showing only the category name and state circle.

### Changes

**StepPills.tsx:**
- Added `currentTopicIndex: number` to the Props interface
- After the category row, when `isActive === true`, render a topic sub-list with `marginLeft: 36px`
- Each topic renders a 6px dot + label with three visual states:
  - Active topic (index === currentTopicIndex): navy dot (#06004f) + bold navy text, fontWeight 600
  - Completed topic (index < currentTopicIndex): green dot (#399e5a) + green text
  - Future topic (index > currentTopicIndex): transparent dot + muted text rgba(6,0,79,0.45)
- Topics are `<div>` elements with `cursor: default` — no navigation on click

**WizardPage.tsx:**
- Added `currentTopicIndex={topicIndex}` to the `<StepPills>` call site

## Verification

- TypeScript: `npx tsc --noEmit` — zero errors
- Visual: active category accordion expands to show topic names; non-active categories collapsed; topic state updates as user navigates

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Description | Hash |
|------|-------------|------|
| 1 | Accordion topic list in progress sidebar | 747e7b5 |

## Self-Check

Verified:
- `frontend/src/components/questionnaire/StepPills.tsx` — FOUND
- `frontend/src/components/questionnaire/WizardPage.tsx` — FOUND
- Commit 747e7b5 — FOUND

## Self-Check: PASSED
