---
phase: 04-context-frontend
plan: 01
subsystem: questionnaire-wizard
tags: [wizard, rjsf-removal, dsi-sp-registration, participant-type, react, fastapi]
dependency_graph:
  requires: [03-02]
  provides: [questionnaire-wizard, dsi-sp-registration, participant-type-on-user]
  affects: [frontend/questionnaire, backend/auth, backend/initiatives]
tech_stack:
  added: []
  removed: ["@rjsf/core", "@rjsf/utils", "@rjsf/validator-ajv8"]
  patterns:
    - "useState wizard navigation (categoryIndex + topicIndex)"
    - "save-on-navigate with Promise.all + useMutation"
    - "forward-blocking based on required question completion"
    - "Pitfall 4 pattern: compute derived values directly on answer change"
    - "React.StrictMode re-enabled after RJSF removal"
key_files:
  created:
    - backend/alembic/versions/add_user_participant_type.py
    - frontend/src/components/questionnaire/AnswerButtonGroup.tsx
    - frontend/src/components/questionnaire/FollowupPanel.tsx
    - frontend/src/components/questionnaire/QuestionCard.tsx
    - frontend/src/components/questionnaire/StepPills.tsx
    - frontend/src/components/questionnaire/WizardPage.tsx
  modified:
    - backend/app/models/user.py
    - backend/app/schemas/auth.py
    - backend/app/api/v1/auth.py
    - backend/app/schemas/initiative.py
    - backend/app/api/v1/initiatives.py
    - frontend/src/lib/questionnaire.ts
    - frontend/src/routes/_auth/register.tsx
    - frontend/src/routes/_app/questionnaire.tsx
    - frontend/src/main.tsx
  deleted:
    - frontend/src/components/questionnaire/QuestionnaireForm.tsx
    - frontend/src/components/questionnaire/NotApplicableWidget.tsx
    - frontend/src/components/questionnaire/ComplyExplainWidget.tsx
decisions:
  - "participant_type stored on User model (not Initiative) — set at registration, read by initiative creation"
  - "Save-on-navigate: answers saved via Promise.all on Next/Back click, not on every change"
  - "Forward blocking: disabled Next button when any required question in current topic has no answer"
  - "NOT_APPLICABLE answer clears followup_selections and followup_other immediately (Pitfall 4 pattern)"
  - "React.StrictMode re-enabled now that RJSF removed"
metrics:
  duration: "~5 minutes"
  completed_date: "2026-02-20"
  tasks_completed: 3
  files_changed: 18
---

# Phase 4 Plan 01: Questionnaire Wizard + DSI/SP Registration Summary

**One-liner:** Custom per-category wizard with Yes/Not-there-yet/N/A + inline follow-up replacing RJSF, DSI/SP selection at registration stored on User model.

## What Was Built

### Backend (Task 1)
- Added `participant_type: str = Field(default="DSI")` to the `User` model
- Updated `UserCreate` schema with `participant_type: Literal["DSI", "SP"] = "DSI"`
- Updated `UserRead` schema to expose `participant_type`
- Updated `/auth/register` and `/auth/me` endpoints to handle participant_type
- Removed `participant_type` from `InitiativeCreate` — initiative creation now reads `current_user.participant_type`
- Created Alembic migration `e5f6a7b8c9d0` adding `user.participant_type` column with server_default='DSI'

### Frontend Types (Task 2)
- Rewrote `questionnaire.ts` with v2 types: `AnswerValue`, `Followup`, `Question`, `Topic`, `Category`, `QuestionnaireConfig`, `LocalAnswer`, `AnswerPayload`, `AnswerRecord`
- `Topic` and `Category` now use `topics` (not `dimensions`) matching v2 config
- `context_text` and `context_image` fields on both `Category` and `Topic` (for Phase 04-03)

### Register Form (Task 2)
- Added DSI/SP button group ("I am a:") to registration form
- Two styled buttons: "DSI — Data Space Initiator" and "SP — Service Provider"
- Selected state uses `var(--color-green)` background, matching existing form button style
- `participant_type` included in POST body as JSON

### RJSF Removal (Task 2)
- Deleted `QuestionnaireForm.tsx`, `NotApplicableWidget.tsx`, `ComplyExplainWidget.tsx`
- Uninstalled `@rjsf/core`, `@rjsf/utils`, `@rjsf/validator-ajv8` (19 packages removed)
- Zero @rjsf imports remain in source code

### Wizard Components (Task 3)

**AnswerButtonGroup.tsx** — 3 horizontal buttons (Yes / Not there yet / Not applicable) with CSS variable styling.

**FollowupPanel.tsx** — Multi-select checkboxes from config options + free-text "Other" input. Rendered whenever answer is YES or NOT_THERE_YET and question has a followup config.

**QuestionCard.tsx** — Question card with answer button group and conditional inline followup panel. Passes NOT_APPLICABLE handling up to WizardPage.

**StepPills.tsx** — Dynamic numbered pills (not hardcoded to 4) showing active category (navy), completed categories (green checkmark), and future categories (gray).

**WizardPage.tsx** — Main wizard component:
- `categoryIndex` + `topicIndex` state (useState, not URL params)
- Local answers initialized from `savedAnswers` prop on mount
- Save-on-navigate: `Promise.all` saves all answered questions in current topic before advancing
- Forward blocking: Next button disabled when any required question in current topic is unanswered
- Answer change handler clears followup_selections/followup_other immediately when switching to NOT_APPLICABLE (Pitfall 4 pattern — uses fresh values, not stale state)
- Context callout box rendered above questions when `topic.context_text` is non-null
- "Finish" label on last topic of last category; navigates to `/dashboard` on click

**questionnaire.tsx (rewritten)** — Uses TanStack Query for initiative, config, and answers. Renders WizardPage once data loaded. Shows friendly message if no initiative exists.

## Verification

- `npx tsc --noEmit` — PASS (zero errors)
- `npm run build` — PASS (379kB bundle, 1.36s)
- No `@rjsf` imports in source (only one comment in main.tsx removed)
- No `antd` imports in source
- All 5 new component files in `frontend/src/components/questionnaire/`
- `questionnaire.tsx` imports `WizardPage` (not `QuestionnaireForm`)
- Alembic migration file exists with `participant_type` column addition

## Deviations from Plan

### Auto-fix: Re-enabled React.StrictMode (Rule 2)
- **Found during:** Task 3 (reviewing main.tsx)
- **Issue:** React.StrictMode was disabled with a comment referencing RJSF React 19 compatibility. Now that RJSF is removed, the workaround is no longer needed.
- **Fix:** Restored `<StrictMode>` wrapper in main.tsx; build still passes.
- **Files modified:** `frontend/src/main.tsx`
- **Commit:** 18ac4fc

### Auto-fix: Removed unused ParticipantType import from initiative schemas (Rule 1)
- **Found during:** Task 1
- **Issue:** After removing `participant_type` from `InitiativeCreate`, the `ParticipantType` import from `app.models.initiative` became unused.
- **Fix:** Removed `ParticipantType` from the import line in `backend/app/schemas/initiative.py`.
- **Files modified:** `backend/app/schemas/initiative.py`
- **Commit:** 2d1adba

## Commits

| Hash | Message |
|------|---------|
| 2d1adba | feat(04-01): backend DSI/SP on User model, Alembic migration, endpoint updates |
| 877c676 | feat(04-01): TypeScript v2 types, register DSI/SP selection, RJSF removal |
| 18ac4fc | feat(04-01): wizard components and questionnaire.tsx rewrite |

## Self-Check: PASSED

All 14 key files verified present on disk. All 3 task commits confirmed in git history (2d1adba, 877c676, 18ac4fc). Build passes with zero errors.
