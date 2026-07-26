---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
verified: 2026-07-26T15:40:00Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "Gap 3 (new finding from round-2 re-verification): submit_initiative never called assert_assessment_complete before freezing dimension_scores, letting a 1-of-52-answered draft be submitted (200) and permanently locked at a garbage score (overall_average 0.07). CLOSED by 15-08's completeness gate. Independently re-verified in this pass (not taken on the executor's or reviewer's word): wrote and ran a fresh standalone repro test (not copied from the committed suite) that creates a user+initiative, answers 1 of 52 real config questions, and calls the real POST /initiatives/{id}/submit — result is now 422 'Questionnaire not fully answered', and GET /initiatives/{id}/assessments returns [] (nothing frozen). A second fresh repro fully answers all 52 questions and confirms submit still returns 200 with a correctly-computed frozen snapshot (overall_average 3.0 across all 6 categories). A third fresh repro confirms the idempotent re-submit (already-submitted initiative, no draft) still returns 200 without the gate misfiring."
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
human_verification: []
---

# Phase 15: Questionnaire Submission API + Wizard UI + Save Reliability Verification Report

**Phase Goal:** A user can take the full 52-question questionnaire through a rebuilt wizard whose answers save reliably in the background, and every full completion creates a new, permanently preserved assessment version the user can return to.
**Verified:** 2026-07-26T15:40:00Z
**Status:** passed
**Re-verification:** Yes — round 4, after gap-closure round 3 (plan 15-08) executed and merged (`20f83b6`)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each question presents its 5 answer options as a horizontal line of radio circles (config-driven labels), each mapped to a 1-5 score | ✓ VERIFIED | Unchanged since round 2/3; regression check: `frontend/src/components/questionnaire/AnswerButtonGroup.tsx` present, untouched by 15-08's diff (`git log 04d81b0..20f83b6 -- frontend/` is empty) |
| 2 | Answers auto-save in the background within a few seconds of being selected (debounced), without requiring Next/Back, and rate limiting is keyed per authenticated user | ✓ VERIFIED | Unchanged; `frontend/src/hooks/useDebouncedSave.ts` present and untouched by 15-08's diff (backend-only plan) |
| 3 | If an autosave fails, the user sees a clear, visible error with a retry action — never a silent lost save | ✓ VERIFIED | Unchanged; `WizardPage.tsx`/`AutosaveBadge` logic untouched — no frontend files appear in the 15-08 commit range |
| 4 | Closing the tab or hard-refreshing mid-questionnaire does not lose previously-saved answers when the user returns to resume | ✓ VERIFIED | Unchanged; `flushAnswerBeacon`/resume-on-mount logic untouched by 15-08 |
| 5 | Retaking the questionnaire creates a new, dated assessment version rather than overwriting the previous one, and the user can view and compare maturity scores across their past versions | ✓ VERIFIED | Unchanged since round 3 (15-06/15-07 mechanisms untouched by 15-08's scope-fenced diff); regression-re-ran `test_retake_flow.py` (3 tests) and `test_frozen_scores.py` (2 tests) fresh in this pass — all pass |
| 6 | Only a fully-answered questionnaire can be submitted and permanently frozen as a version — no partial/garbage submission is ever permanently preservable | ✓ VERIFIED | **CLOSED.** Independently re-read `backend/app/api/v1/initiatives.py:130-148`: `assert_assessment_complete(session, initiative_id, config)` is the first statement inside the `if assessment:` draft branch, strictly before `assessment.status = AssessmentStatus.submitted` and before `compute_dimension_scores(...)`. Independently *reproduced* (not just read) with a fresh, self-written standalone test (discarded after use, not part of the committed suite — see Behavioral Spot-Checks): 1-of-52 answered → `POST /submit` → **422** `"Questionnaire not fully answered"`, and `GET /initiatives/{id}/assessments` → `[]` (nothing frozen, no partial lock — a follow-up `PUT` still succeeds). Full 52/52 answered → `POST /submit` → **200**, `GET /assessments` → one entry, `overall_average: 3.0`, all 6 categories scored 3.0 (correct happy-path freeze, no regression). Already-submitted initiative → second `POST /submit` → still **200** (idempotent path correctly skips the gate, since `assessment` is `None` when no draft remains). |

**Score:** 6/6 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/api/v1/initiatives.py :: submit_initiative` | completeness gate before freeze | ✓ VERIFIED | `assert_assessment_complete(session, initiative_id, config)` present at line 139, textually before `compute_dimension_scores` at line 143 and before `assessment.status` flip at line 140. Import updated (line 14-18) to include `assert_assessment_complete`. |
| `backend/app/services/dimension_scoring.py :: assert_assessment_complete` | pre-existing completeness gate, reused (not reinvented) | ✓ VERIFIED | Unchanged since Phase 14; derives completeness from actual DB answer rows vs config question-id set, generic 422 detail, no question-id enumeration |
| `backend/tests/api/test_submit_completeness.py` | new 422/200/idempotent regression tests | ✓ VERIFIED | 3 tests present (`test_submit_422_when_incomplete`, `test_submit_200_when_complete`, `test_submit_idempotent_resubmit_stays_200`); all HTTP-driven (real `PUT`/`POST`, no direct DB flips); all pass |
| `backend/tests/api/test_retake_flow.py` | updated to fully answer config before submit | ✓ VERIFIED | `_answer_all_questions_via_http` helper added and called before `submit` in both `test_submit_then_retake_unlocks_editing_and_creates_v2_draft` and `test_retake_rejects_non_owner`; all 3 tests in the file pass |
| `docs/api/openapi.json` | docs-freshness regenerated | ✓ VERIFIED | Independently regenerated (`uv run python scripts/export_openapi.py`) and diffed against the committed file — zero diff. The only change vs. pre-15-08 is the `submit_initiative` route's `description` field gaining the SCOR-04 docstring paragraph verbatim; no schema drift. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `submit_initiative` (draft branch) | `assert_assessment_complete` | direct call, before `compute_dimension_scores` | ✓ WIRED | Confirmed by code read + independent repro (422 on incomplete, no freeze) |
| `submit_initiative` (idempotent/no-draft branch) | gate skip | `if assessment:` guard is `None`/falsy when no draft exists | ✓ WIRED | Confirmed by independent repro: already-submitted initiative's second `POST /submit` returns 200, not 422 |
| `submit_initiative` (complete-draft branch) | `Assessment.dimension_scores` freeze | `compute_dimension_scores(...)` assigned only after the gate passes | ✓ WIRED | Confirmed by independent repro: full-answer submit freezes a correct `overall_average: 3.0` snapshot |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Committed 15-08 regression suite | `uv run pytest tests/api/test_submit_completeness.py tests/api/test_retake_flow.py -v` | 6 passed | ✓ PASS |
| **Independent fresh repro (not the committed suite) — 1-of-52 submit** | Self-written standalone test, discarded after use: answer 1 real config question, `POST /submit`, check status + history | `422 {'detail': 'Questionnaire not fully answered'}`; `GET /assessments` → `[]` | ✓ PASS (bug from round 2/3 is genuinely fixed) |
| **Independent fresh repro — full 52/52 submit (happy path, no regression)** | Self-written standalone test: answer all 52 via real `PUT`, `POST /submit`, check history | `200`; `GET /assessments` → `[{version:1, overall_average: 3.0, dimension_scores: [6 categories all 3.0]}]` | ✓ PASS |
| **Independent fresh repro — idempotent re-submit** | Self-written standalone test: full submit (200), then submit again | Second call → `200 {'message': 'Initiative submitted successfully', 'status': 'submitted'}` | ✓ PASS |
| Phase-15-touched regression areas (retake, frozen scores, submit completeness, assessment history, scoring, questionnaire answers, migrations) | `uv run pytest tests/api/test_retake_flow.py tests/api/test_frozen_scores.py tests/api/test_submit_completeness.py tests/api/test_assessment_history.py tests/api/test_scoring.py tests/api/test_questionnaire_answers.py tests/migrations/ -q` | 43 passed | ✓ PASS |
| Full non-perf/non-benchmark suite (once, per CLAUDE.md's local gate) | `uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` | 121 passed, 4 failed | ⚠️ 4 failures independently confirmed pre-existing/environmental — see below |
| ruff + ruff format + mypy on touched files | `uv run ruff check app/api/v1/initiatives.py app/services/dimension_scoring.py && uv run ruff format --check ... && uv run mypy app --ignore-missing-imports` | clean | ✓ PASS |
| Debt-marker scan (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) on 15-08-touched files | `grep -n -E "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER" app/api/v1/initiatives.py tests/api/test_submit_completeness.py tests/api/test_retake_flow.py` | no matches | ✓ PASS |

**On the 4 full-suite failures:** all 4 are in `backend/tests/api/test_reports.py` and independently confirmed (by running one directly and reading the traceback) to fail with `OSError: cannot load library 'libgobject-2.0-0'` — a local-machine WeasyPrint native-library gap (`cffi`/`dlopen` cannot find the GTK/Pango/Cairo shared libraries this dev machine doesn't have installed), not a code defect. This is unrelated to `submit_initiative`, `dimension_scoring.py`, or anything touched by phase 15 — `test_reports.py` exercises PDF generation, a subsystem 15-08 does not touch. SUMMARY.md documents this same 4-failure signature recurring across every prior Phase 12-15 local session on this machine, with CI (which has the native library installed) passing. Independently corroborated here via the traceback itself, not taken on the SUMMARY's word.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| QSTN-02 | 15-03 | 5-option horizontal radio scale, 1-5 score | ✓ SATISFIED | Unchanged; REQUIREMENTS.md marks Complete |
| SAVE-01 | 15-03, 15-04 | Debounced auto-save without Next/Back | ✓ SATISFIED | Unchanged |
| SAVE-02 | 15-03, 15-04 | Save failures surfaced with retry, no silent loss | ✓ SATISFIED | Unchanged |
| SAVE-03 | 15-01 | Rate limiting keyed per authenticated user | ✓ SATISFIED | Unchanged |
| SAVE-04 | 15-01, 15-04 | Tab close/refresh does not lose answers | ✓ SATISFIED | Unchanged |
| HIST-01 | 15-01, 15-04, 15-05, 15-06 | Retake creates new dated version, not overwrite | ✓ SATISFIED | Unchanged since round 3; real end-to-end test proves submit -> 403 -> retake -> 200 with v2 draft, v1 untouched |
| HIST-02 | 15-02, 15-05, 15-07, 15-08 | View/compare scores across past versions, only for genuinely complete submissions | ✓ SATISFIED | Freezing mechanism (15-07) confirmed correct AND now gated on completeness (15-08) — a version can no longer be frozen from an incomplete questionnaire, so "past versions a user compares" are now trustworthy by construction |

**Orphaned requirements check:** All 7 phase requirement IDs (QSTN-02, SAVE-01, SAVE-02, SAVE-03, SAVE-04, HIST-01, HIST-02) appear in at least one plan's `requirements-completed` list, including 15-08 (HIST-02, SCOR-04). No orphans found. REQUIREMENTS.md independently confirmed to mark all 7 `[x]` Complete.

**Cross-cutting note:** SCOR-04 ("Report/scores are only computed and shown once the full questionnaire is 100% answered", owned by Phase 14) previously had an open regression specific to the `initiatives.py` submit-time snapshot path (flagged in the round-3 verification). That regression is now closed: `submit_initiative` honors the same completeness precondition as `scoring.py`/`reports.py`. No other part of SCOR-04 was ever affected.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/app/api/v1/initiatives.py` | 130-139 | Redundant duplicate query: `assert_assessment_complete` internally re-runs the same draft-assessment lookup already performed just above it, discarding its return value (IN-01 in `15-REVIEW-gaps-2.md`, independently confirmed by reading the code) | ℹ️ Info | Harmless — SQLAlchemy identity map guarantees the same row; an avoidable extra round-trip, not a correctness issue |
| `backend/tests/api/test_submit_completeness.py`, `test_retake_flow.py` | — | `_login`/`_answer_all_questions_via_http` helper duplicated across a 7th test file rather than a shared fixture (IN-02) | ℹ️ Info | Maintainability only; pre-existing pattern this plan continues, not introduces |
| `backend/tests/api/test_retake_flow.py` | 55-65 | Stale comment: `q-1-1` is PUT with `score: 4` then silently overwritten to `score: 3` by the subsequent full-answer loop before submit (IN-03) | ℹ️ Info | Cosmetic; no assertion depends on the value 4 surviving |

No Critical or Warning-level findings, independently confirmed by re-reading the diff. No debt markers (TBD/FIXME/XXX) anywhere in the 15-08 diff.

### Human Verification Required

None. All 6 truths are independently verified via direct code reading and fresh, self-written HTTP reproductions (not the committed test suite alone, and not taken on the executor's, reviewer's, or prior verification's word). No behavior-dependent truth was left unexercised.

### Gaps Summary

No gaps remain. Full history across all 4 verification rounds:

1. **Round 1 (`gaps_found`, 4/5):** retake 403-lock (Initiative.status never reset) and live-score drift in history.
2. **Round 2 (plans 15-06, 15-07):** both gaps closed. Re-verification confirmed both closures independently, but surfaced a **new** blocking defect in 15-07's own diff: `submit_initiative` never verified completeness before freezing `dimension_scores`, letting a 1-of-52-answered draft be permanently locked at `overall_average: 0.07`.
3. **Round 3 (plan 15-08):** added the missing `assert_assessment_complete` gate, mirroring the existing `scoring.py`/`reports.py` pattern. A same-run code review (`15-REVIEW-gaps-2.md`) found no Critical/Warning issues (3 Info-level notes only) and independently confirmed a self-reported Rule-1 fix (deferring the `initiative.status` mutation until after the gate) was real and correctly scoped.
4. **Round 4 (this pass, final):** independently re-verified everything from scratch, without trusting the review or SUMMARY: read the actual diff, ran the committed test suite (6/6 pass), wrote and ran three fresh standalone reproductions covering the 422-incomplete case, the 200-complete-happy-path case, and the 200-idempotent-resubmit case — all three behave exactly as required. Ran the full phase-15-touched regression suite (43 tests) and the full non-perf/non-benchmark suite (121 passed; 4 failures independently confirmed as a pre-existing local WeasyPrint native-library environment gap, unrelated to this phase's code). Regenerated `docs/api/openapi.json` and confirmed zero diff (docs-freshness gate genuinely clean, not just claimed). Confirmed no frontend files were touched by 15-08's diff, so truths 1-4 (wizard UI, autosave, retry, resume) carry over from round 3 without regression.

**Phase 15 fully achieves its goal:** a user can take the full 52-question questionnaire through the rebuilt wizard with reliable background autosave, retry-on-failure, and resume-after-refresh; and — as of this final closure — every **full** completion (and only a full completion) creates a new, permanently preserved, correctly-frozen assessment version the user can view and compare in history. Ready to proceed to Phase 16.

---

_Verified: 2026-07-26T15:40:00Z_
_Verifier: Claude (gsd-verifier)_
