---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
plan: 03
subsystem: ui
tags: [react, typescript, debounce, retry-backoff, fetch-keepalive, antd, radio-scale]

requires:
  - phase: 13-new-questionnaire-config-schema-data-model-migration
    provides: "question_id/category_id/score(1-5) backend shape, config/dssc-questionnaire.json (categories[{id,name,questions}], default_options)"
provides:
  - "Rewritten frontend/src/lib/questionnaire.ts matching the live Phase-13 backend (AnswerOption/Question/Category/QuestionnaireConfig, AnswerCreate/AnswerRead, saveAnswer/fetchAnswers/fetchQuestionnaireConfig)"
  - "flushAnswerBeacon (D-07/SAVE-04): fetch+keepalive+Authorization-header beforeunload-safe save, bypassing axios"
  - "frontend/src/hooks/useDebouncedSave.ts: per-question debounce (schedule/flush/flushAll) + 3-attempt [1000,2000,4000] retry-with-backoff state machine with a distinct non-escalating 429 path"
  - "Rebuilt horizontal RadioScale (AnswerButtonGroup.tsx) — 5 config-driven circles, 44px hit target, 2-line-wrap labels"
  - "Rebuilt QuestionCard.tsx (text + RadioScale only, no followup branch)"
  - "Extended StepPills.tsx with a config-derived 'N of {total} answered' counter (D-04)"
  - "Deleted ContextCallout.tsx and FollowupPanel.tsx (orphaned by the new config schema)"
affects: [15-04-wizard-page-rebuild, 15-05-history-page]

tech-stack:
  added: []
  patterns:
    - "Per-question useRef-keyed debounce timer map (schedule/flush/flushAll) — no shared global timer"
    - "Capped exponential backoff retry ladder (1s/2s/4s) with a distinct non-escalating 429 branch, reusable for any future per-answer save call site"
    - "fetch(..., {keepalive:true}) bypassing the shared axios instance for beforeunload-safe requests requiring custom headers/PUT"

key-files:
  created:
    - frontend/src/hooks/useDebouncedSave.ts
  modified:
    - frontend/src/lib/questionnaire.ts
    - frontend/src/components/questionnaire/AnswerButtonGroup.tsx
    - frontend/src/components/questionnaire/QuestionCard.tsx
    - frontend/src/components/questionnaire/StepPills.tsx
    - frontend/src/components/questionnaire/WizardPage.tsx
  deleted:
    - frontend/src/components/questionnaire/ContextCallout.tsx
    - frontend/src/components/questionnaire/FollowupPanel.tsx

key-decisions:
  - "QuestionCard takes a defaultOptions prop (config.default_options) rather than the full QuestionnaireConfig, keeping its prop surface minimal; the caller (WizardPage, rebuilt in 15-04) resolves question.options ?? defaultOptions before rendering"
  - "StepPills.tsx dropped the topic-level accordion entirely (new Category type has no topics substructure — categories now hold questions directly) rather than inventing a synthetic single-topic wrapper"
  - "Rule 3 auto-fix: removed the dead ContextCallout import + 2 JSX call sites from WizardPage.tsx (not in this plan's file list) so Task 3's own grep-based 'no reference anywhere in src' verify gate passes; left WizardPage.tsx's deeper type breakage (topics/currentTopic/AnswerRecord/etc., all pre-existing to this plan's Task-1 type rewrite) untouched — full rebuild is 15-04's job per this plan's explicit objective note"

requirements-completed: [QSTN-02, SAVE-01, SAVE-02]

coverage:
  - id: D1
    description: "questionnaire.ts rewritten to Phase-13 backend shape (AnswerOption/Question/Category/QuestionnaireConfig, AnswerCreate/AnswerRead), old AnswerValue/mami_code/Followup/Topic types fully removed"
    requirement: "QSTN-02"
    verification:
      - kind: unit
        ref: "cd frontend && npx eslint src/lib/questionnaire.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "flushAnswerBeacon: native fetch with keepalive:true and an Authorization header (not sendBeacon), for beforeunload-safe answer saves"
    requirement: "SAVE-01"
    verification:
      - kind: unit
        ref: "cd frontend && npx eslint src/lib/questionnaire.ts"
        status: pass
    human_judgment: true
    rationale: "eslint confirms syntax/lint cleanliness only; actual beforeunload survival behavior (tab-close mid-save) requires manual browser verification, which is out of this plan's automated gate and deferred to 15-04's WizardPage wiring + Phase 17 test coverage"
  - id: D3
    description: "useDebouncedSave hook: per-question debounce timer (schedule/flush/flushAll) + 3-attempt [1000,2000,4000] retry ladder with a distinct non-escalating 429 rate-limited path"
    requirement: "SAVE-02"
    verification:
      - kind: unit
        ref: "cd frontend && npx eslint src/hooks/useDebouncedSave.ts"
        status: pass
    human_judgment: true
    rationale: "eslint confirms syntax/lint cleanliness only; the hook has no wiring/caller yet in this plan (WizardPage integration is 15-04's job), so its actual debounce/backoff timing behavior cannot be exercised end-to-end until then"
  - id: D4
    description: "AnswerButtonGroup.tsx rebuilt as a horizontal 5-circle RadioScale, config-driven (question.options ?? config.default_options), 44px hit target, 2-line-wrap labels, literal theme hex (no CSS custom properties)"
    requirement: "QSTN-02"
    verification:
      - kind: unit
        ref: "cd frontend && npx eslint src/components/questionnaire/AnswerButtonGroup.tsx"
        status: pass
    human_judgment: true
    rationale: "eslint does not verify visual layout (horizontal row, spacing, wrap behavior at 1100px card width) — this needs a rendered/visual check, deferred to 15-04's WizardPage integration or a UI review pass"
  - id: D5
    description: "QuestionCard.tsx rebuilt: question text + RadioScale only, followup/ContextCallout branch removed"
    requirement: "QSTN-02"
    verification:
      - kind: unit
        ref: "cd frontend && npx eslint src/components/questionnaire/QuestionCard.tsx"
        status: pass
    human_judgment: false
  - id: D6
    description: "StepPills.tsx extended with a config-derived 'N of {total} answered' counter, never a hardcoded 52"
    requirement: "SAVE-01"
    verification:
      - kind: unit
        ref: "cd frontend && npx eslint src/components/questionnaire/StepPills.tsx"
        status: pass
    human_judgment: false
  - id: D7
    description: "ContextCallout.tsx and FollowupPanel.tsx deleted; no remaining import/JSX reference anywhere in src; FindingsPanel.tsx untouched"
    verification:
      - kind: other
        ref: "cd frontend && ! grep -rn 'ContextCallout\\|FollowupPanel' src --include=*.tsx --include=*.ts | grep -v '^Binary'"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-25
status: complete
---

# Phase 15 Plan 03: Wizard Answer Plumbing Rebuild Summary

**Rewrote questionnaire.ts's type contract to the live Phase-13 backend shape, added a per-question debounced-save + retry-with-backoff hook (useDebouncedSave), rebuilt the RadioScale/QuestionCard/StepPills components for the 5-circle config-driven answer scale, and deleted the two schema-orphaned components (ContextCallout, FollowupPanel).**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-25T10:40:00Z (approx.)
- **Completed:** 2026-07-25T10:54:34Z
- **Tasks:** 3
- **Files modified:** 7 (2 created/rewritten, 3 rebuilt/extended, 2 deleted; plus 1 out-of-list surgical edit to WizardPage.tsx)

## Accomplishments
- `questionnaire.ts` fully rewritten to the Phase-13 backend contract (`AnswerOption`/`Question`/`Category`/`QuestionnaireConfig`, `AnswerCreate`/`AnswerRead`) — the old pre-Phase-13 `YES/NOT_THERE_YET/NOT_APPLICABLE`/`mami_code`/`Followup`/`Topic` types are gone entirely.
- `flushAnswerBeacon` added: native `fetch(..., {keepalive:true})` with a manually-attached `Authorization` header, deliberately bypassing the shared axios instance (D-07/SAVE-04) — `sendBeacon` was ruled out per RESEARCH since it cannot carry auth headers or use `PUT`.
- New `hooks/useDebouncedSave.ts`: per-question `useRef`-keyed debounce timer (`schedule`/`flush`/`flushAll`), wrapping each save in a 3-attempt `[1000,2000,4000]` backoff ladder with a distinct, non-escalating `rate-limited` path for HTTP 429 (SAVE-02).
- `AnswerButtonGroup.tsx` rebuilt as a horizontal RadioScale: 5 config-driven circles (`question.options ?? config.default_options`), 44px hit target around a 30px visible circle, labels wrap up to 2 lines (never ellipsis-truncated), literal theme hex instead of CSS custom properties (stops the pre-existing token-drift per UI-SPEC).
- `QuestionCard.tsx` rebuilt: question text + RadioScale only — the followup/ContextCallout branch is gone.
- `StepPills.tsx` extended: category stepper now reads the new `Category.name`/no-topics shape, plus a new config-derived "N of {total} answered" counter (D-04), never a hardcoded 52.
- `ContextCallout.tsx` and `FollowupPanel.tsx` deleted (`git rm`) — orphaned by the new config schema; `FindingsPanel.tsx` left untouched per the plan's explicit exclusion.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite questionnaire.ts + useDebouncedSave hook** - `494aef2` (feat)
2. **Task 2: Rebuild RadioScale/QuestionCard + extend StepPills** - `dde9673` (feat)
3. **Task 3: Delete orphaned ContextCallout/FollowupPanel** - `2839f88` (chore)

**Plan metadata:** committed together with this SUMMARY (see final commit below)

## Files Created/Modified
- `frontend/src/lib/questionnaire.ts` - Rewritten types + API wrappers + `flushAnswerBeacon`
- `frontend/src/hooks/useDebouncedSave.ts` - New per-question debounce + retry/backoff hook
- `frontend/src/components/questionnaire/AnswerButtonGroup.tsx` - Rebuilt as horizontal RadioScale
- `frontend/src/components/questionnaire/QuestionCard.tsx` - Rebuilt: text + RadioScale only
- `frontend/src/components/questionnaire/StepPills.tsx` - Extended with answered-count counter, topics accordion removed (schema no longer has topics)
- `frontend/src/components/questionnaire/WizardPage.tsx` - Surgical Rule-3 fix: removed dead ContextCallout import/JSX only (not otherwise touched — full rebuild is 15-04)
- `frontend/src/components/questionnaire/ContextCallout.tsx` - Deleted
- `frontend/src/components/questionnaire/FollowupPanel.tsx` - Deleted

## Decisions Made
- `QuestionCard` takes a `defaultOptions: AnswerOption[]` prop rather than the full `QuestionnaireConfig`, keeping its prop surface minimal and letting the caller (WizardPage, 15-04) own config-resolution.
- `StepPills.tsx` dropped the topic-level accordion entirely rather than inventing a synthetic single-topic wrapper, since the new `Category` type has no `topics` substructure at all (categories now hold `questions` directly).
- Kept the `AnswerButtonGroup.tsx` filename/export name (rather than renaming the file to `RadioScale.tsx`) so `QuestionCard.tsx`'s import stays stable and the plan's declared `files_modified` list is honored exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed dead ContextCallout import/JSX from WizardPage.tsx**
- **Found during:** Task 3 (delete orphaned ContextCallout/FollowupPanel)
- **Issue:** Task 3's own automated verify (`! grep -rn "ContextCallout\|FollowupPanel" src ...`) and acceptance criteria ("No remaining import or JSX reference ... anywhere in src") would fail as soon as the two components were deleted, since `WizardPage.tsx` (not in this plan's `files_modified` list, rebuilt in 15-04) still imported `ContextCallout` and rendered it twice with `context_text`/`context_image` props that no longer exist on the new `Category`/Question types.
- **Fix:** Removed only the `import { ContextCallout } from "./ContextCallout"` line and the two JSX `<ContextCallout .../>` call sites from `WizardPage.tsx`, replacing the import with an explanatory comment. Did NOT touch any of `WizardPage.tsx`'s other, larger type breakage (its `topics`/`currentTopic`/`AnswerRecord`/`LocalAnswer`/`AnswerValue` references, which are pre-existing consequences of Task 1's `questionnaire.ts` rewrite and are explicitly this plan's documented "not green until 15-04" scope boundary).
- **Files modified:** `frontend/src/components/questionnaire/WizardPage.tsx`
- **Verification:** `cd frontend && ! grep -rn "ContextCallout\|FollowupPanel" src --include=*.tsx --include=*.ts | grep -v '^Binary'` → exit 0 (pass)
- **Committed in:** `2839f88` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking, Rule 3)
**Impact on plan:** Necessary and minimal — unblocks Task 3's own literal verify gate without doing any of 15-04's WizardPage rebuild work. No scope creep: `WizardPage.tsx`'s remaining ~28 tsc errors (topics/AnswerRecord/etc.) are untouched and confirmed via `npx tsc -b --noEmit` to be exactly the pre-existing, plan-documented gap this plan's objective note calls out.

## Issues Encountered
- `frontend/node_modules` was not yet installed in this worktree; ran `npm install` before the eslint/vitest/tsc verification commands could execute. Not a plan deviation (tooling setup, no source changes), and `node_modules/` is `.gitignore`d so nothing new was staged for it.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `questionnaire.ts`'s new type contract (`AnswerOption`/`Question`/`Category`/`QuestionnaireConfig`, `AnswerCreate`/`AnswerRead`) and `useDebouncedSave` are ready for 15-04 to wire into a rebuilt `WizardPage.tsx`.
- `AnswerButtonGroup`/`QuestionCard`/`StepPills` are rebuilt and ready to be composed by 15-04's `WizardPage.tsx`; `StepPills` now expects an `answeredCount` prop (computed from local answer state) instead of `currentTopicIndex`.
- Confirmed via `npx tsc -b --noEmit`: the only project-wide type errors are in `WizardPage.tsx` (topics/`AnswerRecord`/`LocalAnswer`/`AnswerValue`/`mami_code` references), exactly matching this plan's documented "not green until 15-04" boundary — no new/unexpected type errors were introduced by this plan's files.
- `npx vitest run`: existing TopNav suite still green (1/1 passed) — no regressions.
- `flushAnswerBeacon` and `useDebouncedSave` have no caller yet; wiring them into the wizard's save flow (beforeunload listener, Next/Back flush-first, retry-badge UI) is explicitly 15-04's job per this plan's objective note.

---
*Phase: 15-questionnaire-submission-api-wizard-ui-save-reliability*
*Completed: 2026-07-25*
