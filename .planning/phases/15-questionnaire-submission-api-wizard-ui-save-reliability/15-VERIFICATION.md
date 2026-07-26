---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
verified: 2026-07-26T00:00:00Z
status: gaps_found
score: 4/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Retaking the questionnaire creates a new, dated assessment version rather than overwriting the previous one"
    status: failed
    reason: "Nothing in the codebase ever resets Initiative.status from 'submitted' back to 'draft'. The dashboard's 'Retake Questionnaire'/'Start new assessment' flow navigates straight to /questionnaire after confirmation, but the very first answer-save (PUT /questionnaire/initiatives/{id}/answers/{question_id}) and the last-viewed-category write (PATCH .../last-viewed-category) both explicitly 403 with 'Submitted assessments cannot be edited' whenever initiative.status == submitted. The version-increment machinery in _get_or_create_draft_assessment (the actual point of migration j1a2b3c4d5e6) is therefore unreachable through the UI for any initiative that has ever submitted once. Verified independently: grep -rn 'InitiativeStatus.draft|status = InitiativeStatus' across backend/app/ shows the only assignment is the one-way flip to submitted in submit_initiative (initiatives.py:99); dashboard.tsx's handleStartOrRetake (lines 101-121) performs no API call before navigating; and no test anywhere in backend/tests calls the real POST /submit endpoint before attempting a retake answer-save — test_version_increment_on_retake_after_prior_submission explicitly flips Assessment.status directly via the DB session with an inline comment acknowledging this is 'without flipping the Initiative itself ... initiative-level submission-lock is a separate concern from this plan's scope.'"
    artifacts:
      - path: "backend/app/api/v1/initiatives.py"
        issue: "submit_initiative (line 99) sets initiative.status = InitiativeStatus.submitted with no corresponding reset path anywhere else in the codebase"
      - path: "frontend/src/routes/_app/dashboard.tsx"
        issue: "handleStartOrRetake (lines 101-121) navigates to /questionnaire on confirm with no API call to unlock the initiative for editing"
      - path: "backend/app/api/v1/questionnaire.py"
        issue: "upsert_answer (line 158) and update_last_viewed_category (line 323) both 403 on initiative.status == submitted, which fires on the very first save attempt of a retake"
    missing:
      - "An explicit reset of Initiative.status back to draft as part of starting a retake — e.g. inside _get_or_create_draft_assessment when a genuinely new draft (version > 1) is being created, or via a dedicated POST /initiatives/{id}/retake endpoint the dashboard confirm-dialog calls before navigating to /questionnaire"
      - "A real end-to-end test that calls POST /initiatives/{id}/submit, then attempts a subsequent answer PUT, and asserts the retake succeeds (200, not 403) with the new draft at version = 2"
  - truth: "Retaking the questionnaire ... creates a new, dated assessment version ... the user can view and compare maturity scores across their past versions"
    status: failed
    reason: "Submitted assessment history is not actually frozen/immutable. compute_dimension_scores(session, assessment_id, config) (dimension_scoring.py:114-145) derives category names, per-category question counts, and score divisors entirely from the config dict injected via Depends(get_dssc_questionnaire_config) at REQUEST time — i.e. whatever config/dssc-questionnaire.json currently contains — not from the config as it existed when that assessment was submitted. list_assessment_history / _to_summary (initiatives.py:120-158) call this same live-config path for every submitted version. The module's own docstring (dimension_scoring.py:12-13) flags the config as 'an explicit placeholder pending real content (QSTN-05)' — i.e. it is expected to change soon. Once the real 52-question config replaces the current one (or any future edit adds/removes/renames questions or categories), every previously-submitted assessment's dimension_scores/overall_average returned by GET /initiatives/{id}/assessments will silently change to reflect the NEW config, not what the user actually answered against — directly contradicting the phase goal's 'permanently preserved assessment version' guarantee. Verified independently: no snapshot/frozen-scores column exists on the Assessment model (backend/app/models/assessment.py has only id/initiative_id/version/status/created_at/submitted_at/last_viewed_category_id — no dimension_scores or config_version field), and no caller of compute_dimension_scores passes anything but the current live config."
    artifacts:
      - path: "backend/app/services/dimension_scoring.py"
        issue: "compute_dimension_scores has no concept of 'the config as of submission time' — always uses the live config argument"
      - path: "backend/app/models/assessment.py"
        issue: "Assessment has no column to snapshot computed scores or the config version/hash used at submission"
      - path: "backend/app/api/v1/initiatives.py"
        issue: "_to_summary (lines 148-158) recomputes scores live for every historical/submitted row on every history-list request"
    missing:
      - "A snapshot mechanism: persist the computed dimension_scores (and overall_average) as a JSON column on Assessment at the moment submit_initiative flips it to submitted, and have list_assessment_history/_to_summary prefer that frozen snapshot over a live recompute when present — or at minimum persist a config version/hash and reject/flag recomputation against a different version"
deferred: []
human_verification: []
---

# Phase 15: Questionnaire Submission API + Wizard UI + Save Reliability Verification Report

**Phase Goal:** A user can take the full 52-question questionnaire through a rebuilt wizard whose answers save reliably in the background, and every full completion creates a new, permanently preserved assessment version the user can return to.
**Verified:** 2026-07-26
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each question presents its 5 answer options as a horizontal line of radio circles (config-driven labels), each mapped to a 1-5 score | ✓ VERIFIED | `AnswerButtonGroup.tsx` renders `options.map(...)` in a `flexDirection: "row"` container, one circle+label per option, `value === opt.score` drives selection; `config/dssc-questionnaire.json` confirmed via inspection to have exactly 5 `default_options` mapped to scores 1-5, 6 categories, 52 total questions |
| 2 | Answers auto-save in the background within a few seconds of being selected (debounced), without requiring Next/Back, and rate limiting is keyed per authenticated user | ✓ VERIFIED | `useDebouncedSave.ts` schedules a save 1500ms after each `handleAnswerChange` call (no Next/Back needed) with a per-question `useRef` timer map; `questionnaire.py`'s `get_user_or_ip_key` decodes the Bearer token via `decode_access_token` and returns `user:<sub>`, applied via `@limiter.limit("120/minute")` on `upsert_answer` and `update_last_viewed_category`; 5 dedicated unit tests (`test_rate_limit_key_*`) pass, confirming determinism/idempotency/no-collision |
| 3 | If an autosave fails, the user sees a clear, visible error with a retry action — never a silent lost save | ✓ VERIFIED | `useDebouncedSave`'s `saveWithRetry` performs 3 auto-retries (1s/2s/4s) then sets state `"failed"`; `WizardPage`'s `AutosaveBadge` renders a red "Save failed" message + a "Retry save" button wired to `handleRetryAllFailed`/`handleRetrySave`; `hasTerminalFailure` blocks Next/Submit (no dismiss/continue-anyway path) |
| 4 | Closing the tab or hard-refreshing mid-questionnaire does not lose previously-saved answers when the user returns to resume | ✓ VERIFIED | `beforeunload` handler fires `flushAnswerBeacon` (native `fetch` + `keepalive:true` + Authorization header) for every still-pending answer; on mount, `questionnaire.tsx` fetches `fetchAnswers` + `fetchLastViewedCategory` + config before rendering the wizard; `WizardPage` initializes `categoryIndex` from `lastViewedCategoryId` and `localAnswers` from `savedAnswers`; the dedicated `PATCH .../last-viewed-category` endpoint persists the viewed category unconditionally on every `categoryIndex` change (not piggybacked on answer saves), confirmed server-side in `questionnaire.py` |
| 5 | Retaking the questionnaire creates a new, dated assessment version rather than overwriting the previous one, and the user can view and compare maturity scores across their past versions | ✗ FAILED | **CR-01 (confirmed independently):** `Initiative.status` is set to `submitted` exactly once (`initiatives.py:99`) and never reset to `draft` anywhere in the codebase (`grep -rn "InitiativeStatus.draft\|status = InitiativeStatus" backend/app/` shows only the one-way flip). Dashboard's `handleStartOrRetake` (`dashboard.tsx:101-121`) navigates straight to `/questionnaire` with no API call to unlock editing. The very first answer-save on a retake 403s (`questionnaire.py:158`/`:323`, "Submitted assessments cannot be edited"), so the version-increment code this phase's migration exists for is unreachable through the real UI. No test anywhere calls the real `POST /submit` before a retake save — `test_version_increment_on_retake_after_prior_submission` explicitly bypasses it, flipping `Assessment.status` directly in the DB session with an inline comment acknowledging the initiative-level lock is untested here. **CR-02 (confirmed independently):** historical/submitted scores are not frozen — `compute_dimension_scores` (`dimension_scoring.py:114-145`) always derives category structure and score divisors from the live config injected at request time; no snapshot column exists on `Assessment` (`assessment.py`); once the placeholder config (explicitly flagged as pending real QSTN-05 content) is replaced, every past version's displayed scores will silently drift, undermining "permanently preserved." |

**Score:** 4/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/assessment.py` | `last_viewed_category_id` + `(initiative_id, version)` unique constraint | ✓ VERIFIED | Both present, model-declared `__table_args__` |
| `backend/alembic/versions/j1a2b3c4d5e6_...py` | migration for above | ✓ VERIFIED | Exists; `tests/migrations/test_assessment_version_migration.py` passes (upgrade/downgrade round-trip, duplicate-pair IntegrityError) |
| `backend/app/api/v1/questionnaire.py` | `get_user_or_ip_key`, version-increment, PATCH last-viewed-category | ✓ VERIFIED | All three present and wired; **but** version-increment path is unreachable for retakes (see Truth 5/CR-01) |
| `backend/app/schemas/questionnaire.py` | `LastViewedCategoryUpdate` schema | ✓ VERIFIED | Present, imported and used |
| `backend/app/schemas/assessment.py` | `AssessmentSummary` schema | ✓ VERIFIED | Present; `dimension_scores: list[dict]` is untyped (WR-02 from code review — minor, not blocking) |
| `backend/app/services/dimension_scoring.py` | `list_submitted_assessments` helper | ✓ VERIFIED | Present, separate query from `get_current_assessment` per plan's Pitfall-5 design |
| `backend/app/api/v1/initiatives.py` | `GET /{id}/assessments` route | ✓ VERIFIED | Present, ownership re-derived, calls `list_submitted_assessments` + `_to_summary` |
| `frontend/src/lib/questionnaire.ts` | rewritten types + API wrappers + `flushAnswerBeacon` | ✓ VERIFIED | Confirmed |
| `frontend/src/hooks/useDebouncedSave.ts` | per-question debounce + retry state machine | ✓ VERIFIED | Confirmed |
| `frontend/src/components/questionnaire/AnswerButtonGroup.tsx` | horizontal 5-circle RadioScale | ✓ VERIFIED | Confirmed |
| `frontend/src/components/questionnaire/QuestionCard.tsx` | text + RadioScale only | ✓ VERIFIED | Confirmed; followup/context branches removed |
| `frontend/src/components/questionnaire/StepPills.tsx` | category stepper + answered-count | ✓ VERIFIED | Confirmed, config-derived total |
| `frontend/src/components/questionnaire/WizardPage.tsx` | rebuilt wizard w/ debounce/retry/beforeunload/resume | ✓ VERIFIED | Confirmed; `tsc -b --noEmit` clean project-wide |
| `frontend/src/lib/assessments.ts` | `fetchAssessmentHistory` wrapper | ✓ VERIFIED | Thin wrapper over `GET /initiatives/{id}/assessments` |
| `frontend/src/routes/_app/assessments.tsx` | history list + comparison table | ✓ VERIFIED | Both tables present, empty/loading/error states implemented |
| `frontend/src/routes/_app/dashboard.tsx` | "View assessment history" + retake confirm dialog | ⚠️ ORPHANED (partial) | UI present and wired to navigation, but the confirm dialog's `onOk` does not perform the state transition needed for the retake to actually work (see CR-01) |
| `ContextCallout.tsx` / `FollowupPanel.tsx` | deleted | ✓ VERIFIED | Confirmed deleted, no remaining references |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `WizardPage.tsx` | `useDebouncedSave` | `schedule`/`flushAll` on answer change and Next/Back | ✓ WIRED | Confirmed |
| `WizardPage.tsx` | `flushAnswerBeacon` | `beforeunload` listener | ✓ WIRED | Confirmed, one request per pending answer (not batched) |
| `WizardPage.tsx` | PATCH last-viewed-category | `saveLastViewedCategory` on every `categoryIndex` change | ✓ WIRED | Confirmed, unconditional (not gated on answer save) |
| `dashboard.tsx` | `/questionnaire` | `handleStartOrRetake` → `Modal.confirm` → `navigate` | ⚠️ PARTIAL | Dialog and navigation wired correctly, but no call resets `Initiative.status`, so the destination route 403s on first save (CR-01) |
| `assessments.tsx` | `GET /initiatives/{id}/assessments` | `fetchAssessmentHistory` | ✓ WIRED | Confirmed, response pivoted client-side into both tables |
| `questionnaire.py upsert_answer` | rate limiter | `@limiter.limit("120/minute")` + `get_user_or_ip_key` | ✓ WIRED | Confirmed |

### Behavioral Spot-Checks / Test Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend answer/history/migration/rate-limit tests | `uv run pytest tests/api/test_questionnaire_answers.py tests/api/test_assessment_history.py tests/migrations/test_assessment_version_migration.py -q` | 25 passed | ✓ PASS |
| Frontend project-wide type check | `npx tsc -b --noEmit` (frontend) | no output / exit 0 | ✓ PASS |
| Real HTTP retake path (`POST /submit` → `PUT answer`) | grep for any test calling `POST /submit` followed by an answer save | no such test exists anywhere in `backend/tests/` | ✗ FAIL (confirms CR-01 gap) |
| Debt-marker scan (TBD/FIXME/XXX) on phase-touched files | `grep -rn -E "TBD|FIXME|XXX"` across all phase 15 files | no matches | ✓ PASS (no unresolved debt markers) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| QSTN-02 | 15-03 | 5-option horizontal radio scale, 1-5 score | ✓ SATISFIED | `AnswerButtonGroup.tsx` + config verified; **note:** `.planning/REQUIREMENTS.md` traceability table still marks this `Pending` — documentation was not updated even though the implementation is complete and correct (process gap, not a code gap) |
| SAVE-01 | 15-03, 15-04 | Debounced auto-save without Next/Back | ✓ SATISFIED | `useDebouncedSave` + `WizardPage.handleAnswerChange` |
| SAVE-02 | 15-03, 15-04 | Save failures surfaced with retry, no silent loss | ✓ SATISFIED | `AutosaveBadge` + terminal-failure blocking |
| SAVE-03 | 15-01 | Rate limiting keyed per authenticated user | ✓ SATISFIED | `get_user_or_ip_key`, 5 passing unit tests; **note:** `.planning/REQUIREMENTS.md` traceability table still marks this `Pending` — same documentation gap as QSTN-02 |
| SAVE-04 | 15-01, 15-04 | Tab close/refresh does not lose answers | ✓ SATISFIED | `flushAnswerBeacon` + resume-at-last-viewed-category |
| HIST-01 | 15-01, 15-04, 15-05 | Retake creates new dated version, not overwrite | ✗ BLOCKED | Version-increment code exists and is unit-tested in isolation, but is unreachable through the real UI/API path — see CR-01. `.planning/REQUIREMENTS.md` marks this `Complete`, which this verification does not confirm. |
| HIST-02 | 15-02, 15-05 | View/compare scores across past versions | ⚠️ PARTIAL | The list/compare UI and endpoint work correctly today, but the underlying scores are not actually frozen at submission time (CR-02), so the "past versions" the user compares are not guaranteed to reflect what they originally submitted once the config changes. `.planning/REQUIREMENTS.md` marks this `Complete`. |

**Orphaned requirements check:** All 7 phase requirement IDs (QSTN-02, SAVE-01, SAVE-02, SAVE-03, SAVE-04, HIST-01, HIST-02) appear in at least one plan's `requirements-completed` list — no orphans found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/alembic/versions/j1a2b3c4d5e6_...py` | 54-58 | Unguarded unique-constraint migration (WR-01 from code review) | ⚠️ Warning | Would fail mid-deployment against any pre-existing DB with duplicate `(initiative_id, version)` rows; not exercised by any test seeding such duplicates |
| `backend/app/api/v1/questionnaire.py` | 292-331 | `update_last_viewed_category` doesn't validate `category_id` against config (WR-02) | ⚠️ Warning | Arbitrary strings can be persisted; frontend defensively falls back to index 0, so not exploitable, but inconsistent with `upsert_answer`'s validation |
| `frontend/src/hooks/useDebouncedSave.ts`, `WizardPage.tsx:129-139` | — | Debounce/retry/auto-clear timers never cleared on unmount (WR-03) | ⚠️ Warning | Leaks timers/state updates on unmounted component if user navigates away via non-flush path |
| `backend/app/services/dimension_scoring.py:137-144`, `initiatives.py:148-158` | — | Division by category/score count with no zero-guard (WR-04) | ⚠️ Warning | `ZeroDivisionError` → unhandled 500 if a config category has 0 questions or 0 categories exist |

None of these four are debt markers (no TBD/FIXME/XXX) and none independently rise to BLOCKER severity, but they are pre-existing findings from the same-run code review (`15-REVIEW.md`) that remain unresolved; recorded here for completeness.

### Human Verification Required

None. Both gaps identified (CR-01, CR-02) are confirmed directly and completely from code/grep/test evidence — no ambiguity requiring a human judgment call.

### Gaps Summary

Two Critical findings from the same-run code review (`15-REVIEW.md`) were independently re-verified against the codebase and both are real, confirmed blockers:

1. **CR-01 — Retake is non-functional end-to-end.** The phase ships a full "Start new assessment" / "Retake Questionnaire" UI and a version-increment backend, but nothing ever transitions `Initiative.status` back from `submitted` to `draft`. Every write endpoint the retake flow depends on (`upsert_answer`, `update_last_viewed_category`) explicitly locks (403) once `initiative.status == submitted`. A real user who retakes today will submit → see the retake button → confirm → land on `/questionnaire` → get a 403 on the very first answer, forever. This directly fails Success Criterion 5 ("Retaking the questionnaire creates a new, dated assessment version").

2. **CR-02 — Assessment history is not actually frozen.** `compute_dimension_scores` always recomputes against the live/current questionnaire config, not the config in effect when a given version was submitted. Since the config is explicitly documented as a placeholder pending real QSTN-05 content (i.e., it will change soon), every previously-submitted version's displayed scores will silently drift once that happens — contradicting the phase goal's explicit "permanently preserved assessment version" language.

Both gaps require a closure plan before this phase's goal can be considered achieved. The remaining 3 of 5 success criteria (QSTN-02 rendering, SAVE-01/02 autosave+retry, SAVE-04 resume-on-refresh) are solidly implemented, well-tested, and verified independently in this pass — this is not a wholesale rejection of the phase's work, but the retake/history versioning half of the goal (which the review correctly flagged) does not hold up.

A documentation-only gap was also found: `.planning/REQUIREMENTS.md`'s traceability table still marks QSTN-02 and SAVE-03 as "Pending" despite both being fully implemented and tested — this should be corrected regardless of the gaps above, and HIST-01/HIST-02 are marked "Complete" there despite this verification finding them blocked/partial.

---

_Verified: 2026-07-26_
_Verifier: Claude (gsd-verifier)_
