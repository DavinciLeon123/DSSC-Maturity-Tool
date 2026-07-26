---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
plan: 05
subsystem: ui
tags: [react, tanstack-router, tanstack-query, antd-table, antd-modal, history-view]

# Dependency graph
requires:
  - phase: 15-questionnaire-submission-api-wizard-ui-save-reliability (Plan 02)
    provides: "GET /initiatives/{id}/assessments — owner-scoped, version-ordered submitted-assessment history with per-dimension scores"
  - phase: 15-questionnaire-submission-api-wizard-ui-save-reliability (Plan 03)
    provides: "questionnaire.ts type-contract rewrite establishing the thin api-wrapper convention this plan mirrors"
provides:
  - "frontend/src/lib/assessments.ts: fetchAssessmentHistory(initiativeId), AssessmentSummary/DimensionScore types"
  - "New /assessments route: version-list table + per-dimension comparison table (HIST-02, D-16/D-17)"
  - "Dashboard 'View assessment history' link + confirmed 'Start new assessment' retake dialog (HIST-01, D-13/D-14)"
affects: [phase-16-report-rebuild]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Thin api.get wrapper convention (fetchAssessmentHistory) mirrors questionnaire.ts's saveAnswer/fetchAnswers shape"
    - "Client-side pivot of a flat per-version dimension_scores[] response into a rows=dimensions/columns=versions comparison table, driven off the first version's dimension names rather than a hardcoded list"
    - "Modal.confirm({title,content,onOk}) call shape copied verbatim from admin.index.tsx's handleResetDemo, reused for the retake confirmation"

key-files:
  created:
    - frontend/src/lib/assessments.ts
    - frontend/src/routes/_app/assessments.tsx
  modified:
    - frontend/src/routes/_app/dashboard.tsx
    - frontend/src/routeTree.gen.ts

key-decisions:
  - "The version-list table's 'Report' link points to the existing /report route (current live-assessment view), not a true per-version archived report — no versioned report endpoint/page exists yet (Phase 16 owns the report rebuild); documented as an interim scope boundary, not a defect, since D-16's explicit ask for this phase is the 'boring tabular' list/comparison view, not a rebuilt report"
  - "Comparison table columns/dimension names are derived from the fetched history data itself (history[0].dimension_scores) rather than a second config fetch, since every submitted version's dimension_scores already carries the category names verbatim from the same config"
  - "routeTree.gen.ts's manual edit was superseded by the TanStack Router vite plugin's own auto-regeneration (triggered incidentally by running vitest) — kept the plugin's canonical file-scan ordering rather than my manual insertion order; functionally identical, committed as a small follow-up sync commit"

requirements-completed: [HIST-02, HIST-01]

coverage:
  - id: D1
    description: "New /assessments route renders a version-list table (date, version #, overall average, report link) sourced from fetchAssessmentHistory, with 'Your assessment history (N)' heading"
    requirement: "HIST-02"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b --noEmit (assessments.tsx/assessments.ts clean, no new errors)"
        status: pass
      - kind: unit
        ref: "cd frontend && npx eslint src/lib/assessments.ts src/routes/_app/assessments.tsx"
        status: pass
    human_judgment: true
    rationale: "tsc/eslint confirm type/lint correctness only; the actual rendered table layout, empty/loading/error state visuals, and comparison-table pivot correctness across real multi-version data need a manual UAT pass per 15-VALIDATION.md — no dev server/browser check was run this session"
  - id: D2
    description: "Comparison table pivots dimension_scores across versions: rows = 6 dimension names, columns = each submitted version, cells = that version's score"
    requirement: "HIST-02"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b --noEmit"
        status: pass
    human_judgment: true
    rationale: "Pivot logic type-checks but has no unit test exercising real multi-version data; needs manual UAT with >=2 submitted versions per 15-VALIDATION.md"
  - id: D3
    description: "Dashboard gains a 'View assessment history' link-style button beside Start/Retake, navigating to /assessments (D-17)"
    requirement: "HIST-01"
    verification:
      - kind: unit
        ref: "cd frontend && npx eslint src/routes/_app/dashboard.tsx"
        status: pass
    human_judgment: false
  - id: D4
    description: "Start/Retake on a SUBMITTED initiative opens Modal.confirm with the locked D-13/D-14 title/body/confirm/cancel copy, only navigating to /questionnaire onOk; first-ever-draft case navigates straight through with no dialog"
    requirement: "HIST-01"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b --noEmit && npx eslint src/routes/_app/dashboard.tsx"
        status: pass
    human_judgment: true
    rationale: "Type/lint-clean, but the actual dialog-vs-no-dialog branching (submitted vs first-ever-draft) and exact locked copy rendering needs a manual click-through per 15-VALIDATION.md — no browser check was run this session"

duration: ~20min
completed: 2026-07-25
status: complete
---

# Phase 15 Plan 05: History UI & Explicit Retake Trigger Summary

**New /assessments history page (version-list table + per-dimension comparison table) consuming the 15-02 history endpoint, plus a dashboard "View assessment history" link and a Modal.confirm-gated "Start new assessment" retake dialog that communicates permanence before navigating to /questionnaire.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-25 (session start, this worktree)
- **Completed:** 2026-07-25T14:33:00Z
- **Tasks:** 2
- **Files modified:** 4 (2 new, 2 modified)

## Accomplishments
- New `frontend/src/lib/assessments.ts`: `AssessmentSummary`/`DimensionScore` types and a thin `fetchAssessmentHistory(initiativeId)` wrapper over `GET /initiatives/{id}/assessments`, mirroring `questionnaire.ts`'s wrapper-function convention
- New `frontend/src/routes/_app/assessments.tsx` (`/assessments` route): fetches the current initiative then its submitted-assessment history via chained `useQuery`s; renders a version-list `antd Table` (submitted date, version #, overall average, report link) under a "Your assessment history (N)" heading, plus a second comparison `Table` pivoting `dimension_scores` (rows = 6 dimension names, columns = each version, cells = scores) with a horizontal-scroll container and a sticky left dimension-name column
- Loading (`Skeleton`), empty (`No completed assessments yet` + locked body copy — never a "(0)" heading), and error (`Couldn't load your assessment history.` + inline `Retry` button) states implemented per the UI-SPEC's exact copy
- Registered the new route in `routeTree.gen.ts`
- `frontend/src/routes/_app/dashboard.tsx`: added a `View assessment history` link-style `Button` beside the existing Start/Retake button, navigating to `/assessments` (D-17); wrapped the Start/Retake click-through in a `Modal.confirm` (copying `admin.index.tsx`'s `handleResetDemo` call shape) with the locked D-13/D-14 title/body/confirm/cancel copy when `initiative.status === "submitted"`, only navigating to `/questionnaire` on confirm — the first-ever-draft case (no prior submission) still navigates straight through with no dialog

## Task Commits

Each task was committed atomically:

1. **Task 1: assessments.ts lib + /assessments history page** - `6d369b4` (feat)
2. **Task 2: Dashboard history link + confirmed retake dialog** - `bc02332` (feat)
3. **Follow-up: sync routeTree.gen.ts to auto-generated order** - `664df2f` (chore)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `frontend/src/lib/assessments.ts` - New `AssessmentSummary`/`DimensionScore` types + `fetchAssessmentHistory` thin wrapper
- `frontend/src/routes/_app/assessments.tsx` - New history page: version-list table + per-dimension comparison table, loading/empty/error states
- `frontend/src/routes/_app/dashboard.tsx` - Added "View assessment history" link + `Modal.confirm`-gated retake handler
- `frontend/src/routeTree.gen.ts` - Registered the new `/assessments` route

## Decisions Made
- The version-list table's "Report" link points to the existing `/report` route (always reflects the current live assessment state) rather than a true per-version archived report — no versioned report endpoint/page exists yet, and Phase 16 explicitly owns the report rebuild. This is a documented interim scope boundary consistent with D-16's "boring tabular, not a chart/rebuilt-report" ask for this phase, not a defect.
- Comparison-table dimension names are derived from the fetched history response itself (`history[0].dimension_scores`) rather than a separate config fetch, since every submitted version's `dimension_scores` already carries identical category names from the same config (per RESEARCH's Greenfield History Endpoint note).
- Used chained `useQuery`s (current initiative → history, `enabled: !!initiative?.id`) rather than a single combined fetch, matching the existing `useQuery` convention in `admin.index.tsx`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Resynced routeTree.gen.ts after the TanStack Router plugin auto-regenerated it**
- **Found during:** Post-Task-2 verification (`npx vitest run`)
- **Issue:** Running vitest incidentally triggered the TanStack Router vite plugin, which regenerated `routeTree.gen.ts` and reordered the new `/assessments` route entries to match its own file-scan order, diverging from my manually-inserted ordering committed in Task 1.
- **Fix:** Committed the plugin's regenerated (functionally identical, differently-ordered) version as a small follow-up commit rather than reverting it — this is the canonical output the generator itself produces, matching the project convention that `routeTree.gen.ts` should stay in sync with what the generator would output.
- **Files modified:** `frontend/src/routeTree.gen.ts`
- **Verification:** `npx tsc -b --noEmit` (no new errors) + `npx vitest run` (1/1 passing) after the resync
- **Committed in:** `664df2f`

---

**Total deviations:** 1 auto-fixed (1 bug/build-correctness, Rule 1)
**Impact on plan:** Cosmetic reordering only — no functional change, no scope creep. Both tasks otherwise executed exactly as written.

## Issues Encountered
- `frontend/node_modules` was not yet installed in this worktree; ran `npm install` before tsc/eslint/vitest could execute. Not a plan deviation (tooling setup, no source changes) — `node_modules/` is `.gitignore`d, nothing new staged for it.
- `frontend/src/components/questionnaire/WizardPage.tsx` has ~28 pre-existing `tsc -b --noEmit` errors (topics/`AnswerRecord`/`LocalAnswer`/`AnswerValue`/`mami_code` references) unrelated to this plan's files — these are documented in the 15-03-SUMMARY as expected "not green until 15-04" and are 15-04's job (a separate, concurrently-executing wave-2 plan in this phase, not yet merged into this worktree). Confirmed via `grep -v "WizardPage.tsx"` that no new tsc errors were introduced by this plan's changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- HIST-02's history list + comparison table and HIST-01's confirmed retake dialog are both implemented and type/lint-clean, consuming the 15-02 backend endpoint with zero backend changes needed.
- Manual UAT per `15-VALIDATION.md` is still needed (deferred, no dev server/browser session run this session): the retake confirmation dialog + first-ever-draft skip-dialog behavior, and the history list + comparison table rendering across multiple real submitted versions (the "overflow" backstop — horizontal scroll + sticky dimension column — was implemented but not visually verified).
- The version-list "Report" link's current-live-report-only limitation should be revisited once Phase 16 builds a true per-version report view; flagging this dependency for that phase's planning.
- This plan's files are disjoint from 15-04's (`WizardPage.tsx`/`QuestionCard.tsx`/`AnswerButtonGroup.tsx`/`StepPills.tsx`) — no merge-conflict risk expected between the two wave-2 plans.

---
*Phase: 15-questionnaire-submission-api-wizard-ui-save-reliability*
*Completed: 2026-07-25*

## Self-Check: PASSED

- FOUND: frontend/src/lib/assessments.ts
- FOUND: frontend/src/routes/_app/assessments.tsx
- FOUND: frontend/src/routeTree.gen.ts (modified, /assessments registered)
- FOUND: frontend/src/routes/_app/dashboard.tsx (modified)
- FOUND commit 6d369b4 (Task 1)
- FOUND commit bc02332 (Task 2)
- FOUND commit 664df2f (routeTree sync follow-up)
