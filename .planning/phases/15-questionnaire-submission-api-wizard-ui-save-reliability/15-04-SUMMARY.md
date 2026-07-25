---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
plan: 04
subsystem: ui
tags: [react, typescript, tanstack-query, debounce, retry-backoff, fetch-keepalive, fastapi]

requires:
  - phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
    provides: "15-01's PATCH .../last-viewed-category write endpoint, per-user rate-limit key, version-increment logic"
  - phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
    provides: "15-03's rewritten questionnaire.ts type contract, useDebouncedSave hook, rebuilt AnswerButtonGroup/QuestionCard/StepPills"
provides:
  - "Fully rebuilt WizardPage.tsx: category-per-page navigation (D-01/D-02/D-03), per-answer debounced autosave wired to useDebouncedSave (SAVE-01/D-05), flushAll() on Next/Back (D-06), two-tier transient/terminal AutosaveBadge with a Retry save button and blocking banner (SAVE-02/D-09/D-10/D-11/D-12), beforeunload keepalive flush (SAVE-04/D-07), resume-at-last-viewed-category (D-08), 'Submit assessment →' rename (D-12)"
  - "Updated questionnaire.tsx route: single full-panel loading gate across config+answers+last-viewed-category, shared Retry error banner"
  - "New questionnaire.ts wrappers: fetchLastViewedCategory, saveLastViewedCategory"
  - "New backend GET /questionnaire/initiatives/{id}/last-viewed-category (Rule 3 auto-fix — read-side counterpart to 15-01's PATCH, previously missing)"
affects: [15-05-history-page, phase-17-e2e-test-coverage]

tech-stack:
  added: []
  patterns:
    - "Per-question saveStates map (Record<questionId, SaveState>) aggregated to a single page-level badge via worst-state-wins, rather than one global mutation-level badge"
    - "pendingFlushRef (useRef, not state) as the single source of truth for 'what still needs a beforeunload-safe flush' — populated on every local answer edit, cleared only on confirmed save"
    - "Symmetric GET/PATCH pair for a single resume-position column, mirroring the existing ownership-check pattern in the same route file"

key-files:
  created: []
  modified:
    - frontend/src/components/questionnaire/WizardPage.tsx
    - frontend/src/routes/_app/questionnaire.tsx
    - frontend/src/lib/questionnaire.ts
    - backend/app/api/v1/questionnaire.py
    - backend/tests/api/test_questionnaire_answers.py
    - docs/api/openapi.json

key-decisions:
  - "[Rule 3 auto-fix, backend] Added GET /questionnaire/initiatives/{id}/last-viewed-category — plan 15-01 shipped only the PATCH write side of D-08; no existing route exposed last_viewed_category_id for the wizard to read on mount (GET .../answers returns only answer rows, InitiativeRead has no assessment fields). Minimal, additive, no migration — mirrors the PATCH route's own ownership/lock checks."
  - "Manual 'Retry save' re-enters schedule()+flush() on useDebouncedSave's existing public API rather than adding a new method to the hook, since useDebouncedSave.ts is outside this plan's declared files_modified."
  - "pendingFlushRef (not the hook's internal pending map, which isn't exposed) is WizardPage's own bookkeeping of 'answers edited but not yet confirmed saved' — used identically by both the beforeunload flush and the Retry save button, so a failed save always retains the correct category_id even after the user has navigated to a different category page (D-03 free back-navigation)."
  - "saveLastViewedCategory fires via a useEffect keyed on categoryIndex (not inlined into handleNext/handleBack), so it fires uniformly on mount and on every subsequent index change without special-casing the resumed starting position."
  - "Flagged-edge sign-off (must_haves.flagged_edge_assumptions, SAVE-04 OS-killed-tab beforeunload edge): CARRIED FORWARD AS A KNOWN OPEN ITEM, not verified acceptable. beforeunload/fetch-keepalive is best-effort per RESEARCH D-07 — it does not fire reliably for a backgrounded mobile tab killed by the OS before the ~1.5s debounce elapses. No code change can close this gap within the locked D-07 beforeunload approach (RESEARCH explicitly notes pagehide/visibilitychange as a possible defense-in-depth addition beyond D-07's literal text, not adopted here to stay within this plan's declared scope). This is an open item for Phase 17's Playwright/real-browser E2E coverage per the plan's own verification section, not a silently-dropped gap."

requirements-completed: [SAVE-01, SAVE-02, SAVE-04, HIST-01]

coverage:
  - id: D1
    description: "Category-per-page navigation (D-01/D-02/D-03): categoryIndex-only state, Next disabled until every question on the page is answered, Back is free (only disabled on category 0)"
    requirement: "SAVE-01"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b --noEmit"
        status: pass
      - kind: unit
        ref: "cd frontend && npx eslint src/components/questionnaire/WizardPage.tsx"
        status: pass
    human_judgment: true
    rationale: "tsc/eslint confirm type/lint correctness only; actual per-page navigation/disabled-state behavior needs a rendered/interactive check, deferred to manual UAT per 15-VALIDATION.md."
  - id: D2
    description: "Per-answer debounced autosave wired to useDebouncedSave.schedule on every answer change; Next/Back call flushAll() before navigating (SAVE-01/D-05/D-06)"
    requirement: "SAVE-01"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b --noEmit"
        status: pass
    human_judgment: true
    rationale: "Debounce timing (~1.5s) and flush-before-navigate ordering require a real browser/interactive check (network tab timing) — deferred to manual UAT."
  - id: D3
    description: "Two-tier AutosaveBadge: transient amber (retrying/rate-limited, self-clearing) vs terminal red (failed, with Retry save button); terminal failure blocks Next and Submit via isNextDisabled, with an inline blocking banner; transient states do not block"
    requirement: "SAVE-02"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b --noEmit"
        status: pass
      - kind: unit
        ref: "cd frontend && npx eslint src/components/questionnaire/WizardPage.tsx"
        status: pass
    human_judgment: true
    rationale: "The retry-ladder timing and actual terminal-vs-transient visual distinction need a real save-failure to observe end-to-end — deferred to manual UAT per 15-VALIDATION.md."
  - id: D4
    description: "beforeunload listener fires flushAnswerBeacon (fetch keepalive) synchronously per still-pending answer, never awaited, never batched; old useRef unmount fire-and-forget save removed"
    requirement: "SAVE-04"
    verification:
      - kind: unit
        ref: "cd frontend && npx eslint src/components/questionnaire/WizardPage.tsx"
        status: pass
      - kind: other
        ref: "cd frontend && grep -c 'addEventListener(\"beforeunload\"' src/components/questionnaire/WizardPage.tsx"
        status: pass
    human_judgment: true
    rationale: "beforeunload/keepalive survival cannot be exercised in jsdom/vitest — requires a real browser tab-close, explicitly deferred to Phase 17 Playwright E2E per the plan's verification section and RESEARCH.md's coverage table."
  - id: D5
    description: "WizardPage resumes at lastViewedCategoryId (mapped to its index, default 0 if null/not found); saveLastViewedCategory fires unconditionally on every categoryIndex change via a dedicated useEffect, independent of any answer save"
    requirement: "HIST-01"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b --noEmit"
        status: pass
      - kind: other
        ref: "cd frontend && grep -n 'saveLastViewedCategory' src/components/questionnaire/WizardPage.tsx"
        status: pass
    human_judgment: true
    rationale: "The specific 'navigate to category 4 without answering, hard-refresh, resume on category 4' case is the plan's own named manual UAT check (15-VALIDATION.md) — code-level grep confirms the write path is unconditional, but end-to-end resume behavior needs a real refresh."
  - id: D6
    description: "questionnaire.tsx fetches config + saved answers + last-viewed-category in parallel; single full-panel loading state until all three resolve; shared #991B1B-on-#FEE2E2 Retry error banner on any fetch failure"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b --noEmit"
        status: pass
      - kind: unit
        ref: "cd frontend && npx eslint src/routes/_app/questionnaire.tsx"
        status: pass
    human_judgment: false
  - id: D7
    description: "[Rule 3 auto-fix] New GET /questionnaire/initiatives/{id}/last-viewed-category backend endpoint, the read-side counterpart to 15-01's PATCH, needed for D-08's resume behavior to be readable at all"
    requirement: "HIST-01"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_questionnaire_answers.py#test_get_last_viewed_category_returns_none_when_no_assessment_exists"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_questionnaire_answers.py#test_get_last_viewed_category_returns_previously_written_value"
        status: pass
      - kind: integration
        ref: "backend/tests/api/test_questionnaire_answers.py#test_get_last_viewed_category_rejects_non_owner"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-25
status: complete
---

# Phase 15 Plan 04: Wizard Page Rebuild — Debounce, Retry-Terminal-Block, Resume Summary

**Fully rebuilt WizardPage.tsx with per-answer debounced autosave, two-tier transient/terminal retry-blocking on Next/Submit, a beforeunload keepalive flush, and resume-at-last-viewed-category — plus a Rule 3 backend GET endpoint that 15-01 never shipped, without which resume was unreadable.**

## Performance

- **Duration:** ~20 min active execution
- **Completed:** 2026-07-25
- **Tasks:** 2/2 completed
- **Files modified:** 6 (3 frontend as declared in the plan's files_modified; 3 backend as a Rule 3 auto-fix — see Deviations)

## Accomplishments

- `WizardPage.tsx` fully rebuilt against the new flat `config.categories[].questions[]` schema: `categoryIndex`-only state (no topic sub-pagination), `isNextDisabled` requires every question on the page answered (D-02), Back is free and only disabled on the first category (D-03)
- Per-question debounced autosave wired to `useDebouncedSave.schedule` on every `handleAnswerChange` call (SAVE-01/D-05); `handleNext`/`handleBack` both call `flushAll()` before navigating (D-06)
- `AutosaveBadge` extended (not replaced) with a genuine two-tier distinction: transient amber `retrying`/`rate-limited` (self-clearing, never blocking) vs. terminal red `failed` (persists until a manual "Retry save" click succeeds) — per-question save states aggregate to one page-level badge via worst-state-wins
- Terminal failure blocks both Next and Submit (`isNextDisabled` includes `hasTerminalFailure`) with an inline "This answer didn't save. Retry before continuing." banner next to the nav row — no dismiss/continue-anyway path (D-10/D-11/D-12)
- Final-category CTA renamed `Submit assessment →` (from `Finish →`), still composing with the existing `/initiatives/{id}/submit` call and its backend 422 gate (D-12)
- `beforeunload` listener fires `flushAnswerBeacon` (keepalive) synchronously, one small request per still-pending answer, never awaited/batched (SAVE-04/D-07/Pitfall 2/3); the old `useRef` unmount fire-and-forget save is gone
- WizardPage resumes at `lastViewedCategoryId` (mapped to its index, default 0); a dedicated `useEffect` calls the new `saveLastViewedCategory` wrapper unconditionally on every `categoryIndex` change, independent of any answer save (D-08)
- `questionnaire.tsx` fetches config + saved answers + last-viewed-category in parallel, shows one full-panel loading state until all three resolve, and a shared `#991B1B`-on-`#FEE2E2` Retry error banner on any fetch failure
- **[Rule 3 auto-fix]** Added `GET /questionnaire/initiatives/{id}/last-viewed-category` to the backend — 15-01 shipped only the PATCH write side; nothing exposed the value for the wizard to read on mount

## Task Commits

Each task was committed atomically:

1. **Task 1: Rebuild WizardPage — category-per-page nav, debounced save, retry-terminal-block** - `59f5f8c` (feat)
2. **Task 2: beforeunload keepalive flush + resume-at-last-viewed-category + mount loading/error** - `e563463` (feat) — includes the Rule 3 backend GET endpoint, its tests, and the regenerated `openapi.json`

## Files Created/Modified

- `frontend/src/components/questionnaire/WizardPage.tsx` - Full rebuild: category-per-page nav, per-question debounce+retry state, beforeunload flush, resume-at-last-viewed
- `frontend/src/routes/_app/questionnaire.tsx` - Parallel config+answers+last-viewed fetch, single loading gate, shared Retry error banner
- `frontend/src/lib/questionnaire.ts` - New `fetchLastViewedCategory`/`saveLastViewedCategory` thin wrappers
- `backend/app/api/v1/questionnaire.py` - New `GET .../last-viewed-category` endpoint (Rule 3 auto-fix)
- `backend/tests/api/test_questionnaire_answers.py` - 3 new tests for the GET endpoint
- `docs/api/openapi.json` - Regenerated for the new GET route (docs-freshness CI gate)

## Decisions Made

- Manual "Retry save" reuses `useDebouncedSave`'s existing `schedule`+`flush` public API rather than adding a method to the hook, since `useDebouncedSave.ts` is outside this plan's declared `files_modified`.
- `pendingFlushRef` (a `WizardPage`-local ref, not the hook's internal pending map) is the single source of truth for "answers edited but not yet confirmed saved" — used by both the `beforeunload` flush and the Retry button, so a retry always uses the correct `category_id` even if the user has since navigated to a different category page.
- `saveLastViewedCategory` fires from a `useEffect` keyed on `categoryIndex` rather than being inlined into `handleNext`/`handleBack`, so it fires uniformly on initial mount (re-persisting the resumed position, harmless/idempotent) and on every subsequent change.
- **[Rule 3 auto-fix, backend]** Added `GET /questionnaire/initiatives/{id}/last-viewed-category` — see Deviations below.
- **Flagged-edge sign-off (plan `must_haves.flagged_edge_assumptions`, SAVE-04 OS-killed-tab beforeunload edge):** **CARRIED FORWARD AS A KNOWN OPEN ITEM**, not verified acceptable. `beforeunload`/`fetch(keepalive:true)` is best-effort per RESEARCH D-07 — it does not fire reliably for a backgrounded mobile tab the OS kills before the ~1.5s debounce elapses, and no implementation choice within the locked D-07 approach closes this gap (RESEARCH flags `pagehide`/`visibilitychange` as a possible defense-in-depth addition beyond D-07's literal text; not adopted here to stay within this plan's declared scope). This is explicitly deferred to Phase 17's Playwright/real-browser E2E coverage, per both the plan's verification section and RESEARCH.md's own coverage table (`SAVE-04 | beforeunload flush survives tab close | manual-only (UAT) | ... ❌ Phase 17`) — a conscious carry-forward, not a silent drop.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing GET /questionnaire/initiatives/{id}/last-viewed-category endpoint**
- **Found during:** Task 2 (resume-at-last-viewed-category wiring)
- **Issue:** The plan's Task 2 requires `questionnaire.tsx` to "fetch config + saved answers + the initiative's last_viewed_category_id," and `WizardPage` to resume at that value. Plan 15-01 (Wave 1 dependency) shipped only the PATCH write endpoint for `last_viewed_category_id` — no route anywhere exposed the value for reading (`GET .../answers` returns only answer rows; `InitiativeRead` has no assessment fields). Without a read path, D-08's resume feature is literally unimplementable — this blocks the whole task, not a cosmetic gap.
- **Fix:** Added `GET /questionnaire/initiatives/{initiative_id}/last-viewed-category` to `backend/app/api/v1/questionnaire.py`, mirroring the sibling PATCH route's ownership checks (404/403) and returning `{"last_viewed_category_id": null}` when no draft assessment exists yet (a first-ever visit has nothing to resume — not an error). No new column, no migration, no architectural change — purely additive, symmetric read/write pair on an already-existing column.
- **Files modified:** `backend/app/api/v1/questionnaire.py`, `backend/tests/api/test_questionnaire_answers.py`, `docs/api/openapi.json`
- **Verification:** 3 new backend tests (none-exists / previously-written-value / non-owner-403) all pass; full backend quick suite (`uv run pytest tests/ -n auto -m "not perf and not benchmark"`) — 111 passed, 4 pre-existing local-only WeasyPrint failures (documented since Phase 13, unrelated); `ruff check`/`ruff format --check`/`mypy app --ignore-missing-imports` all clean; `docs/api/openapi.json` regenerated via `scripts/export_openapi.py` (docs-freshness gate).
- **Committed in:** `e563463` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking, Rule 3)
**Impact on plan:** Necessary for correctness — without this endpoint, D-08's resume-at-last-viewed-category feature (a core plan deliverable and a HIST-01/SAVE-04-adjacent requirement) could not function at all. Minimal and additive: no new column, no migration, no change to any existing route's behavior. No scope creep beyond what Task 2 already required to be implementable.

## Issues Encountered

`frontend/node_modules` was not installed in this worktree; ran `npm install` before `tsc`/`eslint`/`vitest` could execute (same one-time setup step noted in 15-03's summary). Not a plan deviation — tooling setup only, `node_modules/` is gitignored.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `WizardPage.tsx`/`questionnaire.tsx`/`questionnaire.ts` are fully rebuilt and green: `npx tsc -b --noEmit` (project-wide, the Wave-2 frontend exit gate 15-03 deferred), `npx eslint` on all three files, and `npx vitest run` (existing suite) all pass with zero errors.
- Backend quick suite green except the 4 pre-existing local-only WeasyPrint failures (unrelated, documented since Phase 13); `ruff`/`mypy` clean; `alembic heads` unaffected (no migration in this plan).
- Manual UAT per `15-VALIDATION.md` remains outstanding for: radio-scale render, ~1.5s autosave timing, failed-save block+retry visual sequencing, beforeunload tab-close survival, and specifically the "navigate to category 4 without answering, hard-refresh, resume on category 4" case (code-level grep confirms `saveLastViewedCategory` is unconditional; end-to-end behavior needs a real refresh).
- Plan 15-05 (history page) and Phase 17 (E2E test coverage) can build on this; the SAVE-04 OS-killed-tab edge case is explicitly carried forward to Phase 17's Playwright coverage (see Decisions Made above), not resolved here.
- No blockers for subsequent Phase 15 plans.

---
*Phase: 15-questionnaire-submission-api-wizard-ui-save-reliability*
*Completed: 2026-07-25*

## Self-Check: PASSED

All 6 created/modified files confirmed present on disk (`frontend/src/components/questionnaire/WizardPage.tsx`, `frontend/src/routes/_app/questionnaire.tsx`, `frontend/src/lib/questionnaire.ts`, `backend/app/api/v1/questionnaire.py`, `backend/tests/api/test_questionnaire_answers.py`, `docs/api/openapi.json`). Both commit hashes (`59f5f8c`, `e563463`) confirmed present in `git log --oneline --all`.
