---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
verified: 2026-07-26T11:24:00Z
status: gaps_found
score: 5/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "Gap 1 (CR-01/HIST-01): Initiative.status never reset after submit, permanently locking retakes with a 403 — CLOSED by 15-06's POST /initiatives/{id}/retake endpoint + dashboard wiring. Independently re-verified: real end-to-end test (submit -> 403 -> retake -> 200) passes; grep confirms initiative.status = InitiativeStatus.draft now exists in retake_initiative; dashboard.tsx awaits the retake call before navigating."
    - "Gap 2 (CR-02/HIST-02): assessment history recomputed scores live against the current config instead of freezing at submission — CLOSED by 15-07's Assessment.dimension_scores JSONB snapshot column + submit-time freeze + snapshot-preferred history read. Independently re-verified: migration k2b3c4d5e6f7 chains cleanly from j1a2b3c4d5e6 (single head); test_frozen_scores.py proves history survives a live-config mutation (renamed category) served via dependency override; legacy-fallback (dimension_scores=None) path still passes test_assessment_history.py unchanged."
  gaps_remaining: []
  regressions:
    - "NEW (not a regression of the original 2 gaps, but a newly-introduced defect surfaced by 15-07's own diff, confirmed independently per this re-verification's mandate): submit_initiative never calls assert_assessment_complete before computing and permanently freezing dimension_scores, unlike every other scoring/reporting endpoint (scoring.py:50, reports.py:117/171/194/217/246/277). Any authenticated user can submit and permanently lock a wildly incomplete questionnaire. See gaps below."
gaps:
  - truth: "Every full completion creates a new, permanently preserved assessment version the user can return to (implicit corollary: an INCOMPLETE questionnaire must not be permanently frozen as a version with no correction path short of destroying real answers)"
    status: failed
    reason: >
      Independently reproduced (not just code-read): submit_initiative (backend/app/api/v1/initiatives.py:82-128)
      never calls assert_assessment_complete before computing and persisting assessment.dimension_scores. Every
      other scoring/reporting endpoint in this codebase (scoring.py:50, reports.py:117,171,194,217,246,277) calls
      assert_assessment_complete(session, initiative_id, config) first; submit_initiative — the exact endpoint
      15-07 modified to call compute_dimension_scores directly — does not, even though compute_dimension_scores's
      own docstring (dimension_scoring.py:120-124) says completeness verification is "the caller's" obligation.
      I wrote and ran a standalone repro test (not part of the committed suite) that: creates a user+initiative,
      answers exactly 1 of 52 real config questions (q-1-1), and calls the real POST /initiatives/{id}/submit.
      Result: HTTP 200 (not 422), and the frozen, permanent GET /initiatives/{id}/assessments snapshot reads
      overall_average: 0.07 with 5 of 6 categories permanently scored 0.0 (only cat-1 scores 0.44 = round(4/9,2)).
      This is also directly provable from the gap-closure plans' own committed test suite: 15-06's
      test_retake_flow.py::test_submit_then_retake_unlocks_editing_and_creates_v2_draft answers only q-1-1 and
      asserts submit_response.status_code == 200 against the real 52-question config — i.e. the test written to
      prove the retake fix incidentally proves this submit-completeness gap is real and already shipped. Once
      frozen, the only way to correct a garbage snapshot is a full retake, which (by design, D-14) wipes every
      real answer — there is no "fix and resubmit" path. This also regresses SCOR-04 ("Report/scores are only
      computed and shown once the full questionnaire is 100% answered") for the new submit-time snapshot code
      path specifically, even though SCOR-04 continues to hold for scoring.py/reports.py.
    artifacts:
      - path: "backend/app/api/v1/initiatives.py"
        issue: "submit_initiative (lines 82-128) computes and freezes compute_dimension_scores(...) with no assert_assessment_complete gate beforehand, unlike scoring.py and reports.py"
    missing:
      - "Call assert_assessment_complete(session, initiative_id, config) before flipping the draft assessment to submitted / computing dimension_scores in submit_initiative, returning 422 'Questionnaire not fully answered' for an incomplete draft (mirroring scoring.py/reports.py's existing pattern) — see 15-REVIEW-gaps.md's CR-01 fix suggestion, which also correctly notes an already-submitted initiative's idempotent re-submit path should stay a no-op 200 and not re-run the gate against a draft that no longer exists"
      - "A regression test asserting POST /submit returns 422 (not 200) when fewer than all config questions are answered, mirroring the existing 422 tests for scoring.py/reports.py"
deferred: []
human_verification: []
---

# Phase 15: Questionnaire Submission API + Wizard UI + Save Reliability Verification Report

**Phase Goal:** A user can take the full 52-question questionnaire through a rebuilt wizard whose answers save reliably in the background, and every full completion creates a new, permanently preserved assessment version the user can return to.
**Verified:** 2026-07-26T11:24:00Z
**Status:** gaps_found
**Re-verification:** Yes — after gap closure (plans 15-06, 15-07), with an additional independently-verified finding from `15-REVIEW-gaps.md` factored in

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each question presents its 5 answer options as a horizontal line of radio circles (config-driven labels), each mapped to a 1-5 score | ✓ VERIFIED | Unchanged since initial verification; regression check: `AnswerButtonGroup.tsx` still present and unmodified by 15-06/15-07 |
| 2 | Answers auto-save in the background within a few seconds of being selected (debounced), without requiring Next/Back, and rate limiting is keyed per authenticated user | ✓ VERIFIED | Unchanged; `useDebouncedSave.ts` untouched by gap-closure plans; regression suite (`test_questionnaire_answers.py`) still 20 passed |
| 3 | If an autosave fails, the user sees a clear, visible error with a retry action — never a silent lost save | ✓ VERIFIED | Unchanged; `WizardPage.tsx` retry/`AutosaveBadge` logic untouched by 15-06/15-07's diff (only `submitMutation`/dashboard-adjacent code was touched) |
| 4 | Closing the tab or hard-refreshing mid-questionnaire does not lose previously-saved answers when the user returns to resume | ✓ VERIFIED | Unchanged; `flushAnswerBeacon`/resume-on-mount logic untouched |
| 5 | Retaking the questionnaire creates a new, dated assessment version rather than overwriting the previous one, and the user can view and compare maturity scores across their past versions | ✓ VERIFIED | **Gap 1 (CR-01/HIST-01) CLOSED:** `POST /initiatives/{id}/retake` (`initiatives.py:131-174`) re-derives ownership, 409-guards a non-submitted initiative, resets `Initiative.status = InitiativeStatus.draft`, and reuses `_get_or_create_draft_assessment` for the race-safe version-increment. `dashboard.tsx`'s `handleStartOrRetake` now `await`s this call before navigating, re-throwing on failure to keep the confirm dialog open. Independently re-ran `backend/tests/api/test_retake_flow.py` (3 tests, real HTTP: submit -> 403 -> retake -> 200, 409 non-submitted guard, 403 non-owner) — all pass. **Gap 2 (CR-02/HIST-02) CLOSED:** `Assessment.dimension_scores` (nullable JSONB, `assessment.py`) is now computed once at submit time (`initiatives.py:120-125`) and `_to_summary` (`initiatives.py:205-225`) prefers the frozen snapshot, falling back to live recompute only when `None` (legacy rows). Independently re-ran `test_frozen_scores.py` (2 tests: freeze-under-config-drift proof via `dependency_overrides`, legacy-fallback control) and `test_assessment_history.py` (fallback-path regression) — all pass. Migration `k2b3c4d5e6f7` confirmed single head chaining from `j1a2b3c4d5e6` via `ruff`/`mypy`/pytest all green. |
| 6 (new, derived from phase goal's "every **full** completion ... **permanently** preserved") | Only a fully-answered questionnaire can be submitted and permanently frozen as a version — no partial/garbage submission is ever permanently preservable | ✗ FAILED | **New finding (CR-01 in `15-REVIEW-gaps.md`), independently reproduced, not merely code-read:** wrote and ran a standalone test that answers 1 of 52 real config questions, then calls the real `POST /initiatives/{id}/submit` — result: HTTP 200, and `GET /initiatives/{id}/assessments` permanently returns `overall_average: 0.07` (5 of 6 categories frozen at `0.0`). `submit_initiative` never calls `assert_assessment_complete`, unlike `scoring.py:50` and `reports.py:117,171,194,217,246,277`. Also directly provable from the committed `test_retake_flow.py::test_submit_then_retake_unlocks_editing_and_creates_v2_draft`, which answers only `q-1-1` and asserts `submit_response.status_code == 200` against the real 52-question config. See Gaps Summary. |

**Score:** 5/6 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/api/v1/initiatives.py :: retake_initiative` (POST /initiatives/{id}/retake) | 15-06 gap-closure endpoint | ✓ VERIFIED | Present at lines 131-174; ownership 404/403, 409 guard, status reset, reuses `_get_or_create_draft_assessment`; ruff/mypy clean |
| `frontend/src/routes/_app/dashboard.tsx :: handleStartOrRetake` | now calls POST /retake before navigating | ✓ VERIFIED | Confirmed at lines 101-127: `await api.post(.../retake)` then `navigate`, catch re-throws to keep dialog open on failure |
| `backend/tests/api/test_retake_flow.py` | real end-to-end retake test | ✓ VERIFIED | 3 tests, all pass; genuinely drives real HTTP `POST /submit` and `POST /retake` (no direct DB status flips) |
| `backend/app/models/assessment.py :: Assessment.dimension_scores` | nullable JSONB snapshot column | ✓ VERIFIED | Present, mirrors `questionnaire_answer_archive.py`'s JSONB idiom |
| `backend/alembic/versions/k2b3c4d5e6f7_...py` | frozen-scores migration, chains from j1a2b3c4d5e6 | ✓ VERIFIED | Confirmed single head; `test_frozen_scores_migration.py` (2 tests) pass |
| `backend/app/api/v1/initiatives.py :: submit_initiative` (snapshot) + `_to_summary` (prefers snapshot) | 15-07 gap-closure | ⚠️ VERIFIED-WITH-DEFECT | Snapshot mechanism itself works exactly as designed (frozen, immune to config drift) — **but** `submit_initiative` computes/freezes the snapshot without first verifying completeness (see Truth 6 / Gaps) |
| `backend/app/services/dimension_scoring.py :: compute_dimension_scores` zero-guard (WR-04) | division-by-zero guard | ✓ VERIFIED | `round(sums.get(cat_id, 0) / n_questions, 2) if n_questions else 0.0` present |
| `backend/tests/api/test_frozen_scores.py` + `backend/tests/migrations/test_frozen_scores_migration.py` | new tests | ✓ VERIFIED | 2 + 2 tests, all pass |
| `.planning/REQUIREMENTS.md` | QSTN-02/SAVE-03 doc drift correction | ✓ VERIFIED | Both now `[x]`/Complete (previously flagged `Pending` in prior verification pass) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `dashboard.tsx` confirm `onOk` | `POST /initiatives/{id}/retake` | `await api.post(...)` before `navigate` | ✓ WIRED | Confirmed; failure path re-throws to keep dialog open |
| `retake_initiative` | `_get_or_create_draft_assessment` | direct cross-module import from `questionnaire.py` | ✓ WIRED | Confirmed, no circular import (`uv run python -c "import app.main"` clean per SUMMARY, and app already imports fine here) |
| `submit_initiative` | `Assessment.dimension_scores` | `compute_dimension_scores(...)` assigned before commit | ✓ WIRED | Confirmed — **but missing the `assert_assessment_complete` precondition every sibling caller has (Truth 6 gap)** |
| `list_assessment_history` / `_to_summary` | `Assessment.dimension_scores` | `a.dimension_scores if not None else compute_dimension_scores(...)` | ✓ WIRED | Confirmed via `test_frozen_scores.py`'s config-drift proof and the legacy-fallback control |

### Behavioral Spot-Checks / Test Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Gap-closure test suites | `uv run pytest tests/api/test_retake_flow.py tests/api/test_frozen_scores.py tests/api/test_assessment_history.py tests/migrations/test_frozen_scores_migration.py -q` | 12 passed | ✓ PASS |
| Regression: original phase-15 test areas | `uv run pytest tests/api/test_questionnaire_answers.py tests/api/test_assessment_history.py tests/migrations/ -q` | 31 passed | ✓ PASS |
| ruff + mypy on touched files | `uv run ruff check app/api/v1/initiatives.py app/services/dimension_scoring.py app/models/assessment.py && uv run mypy app --ignore-missing-imports` | clean | ✓ PASS |
| **Independent repro of CR-01 (new finding)** | Standalone test: answer 1/52 questions, `POST /submit`, assert status | **200 (bug reproduced)**, `overall_average: 0.07` permanently frozen | ✗ FAIL (confirms new gap; test discarded after use, not committed) |
| Debt-marker scan (TBD/FIXME/XXX) on 15-06/15-07-touched files | `grep -rn -E "TBD|FIXME|XXX"` | no matches | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| QSTN-02 | 15-03 | 5-option horizontal radio scale, 1-5 score | ✓ SATISFIED | Unchanged; REQUIREMENTS.md now correctly marks Complete (doc-drift from prior pass fixed by 15-07) |
| SAVE-01 | 15-03, 15-04 | Debounced auto-save without Next/Back | ✓ SATISFIED | Unchanged |
| SAVE-02 | 15-03, 15-04 | Save failures surfaced with retry, no silent loss | ✓ SATISFIED | Unchanged |
| SAVE-03 | 15-01 | Rate limiting keyed per authenticated user | ✓ SATISFIED | Unchanged; REQUIREMENTS.md doc-drift fixed |
| SAVE-04 | 15-01, 15-04 | Tab close/refresh does not lose answers | ✓ SATISFIED | Unchanged |
| HIST-01 | 15-01, 15-04, 15-05, 15-06 | Retake creates new dated version, not overwrite | ✓ SATISFIED | Closed by 15-06; real end-to-end test proves submit -> 403 -> retake -> 200 with v2 draft, v1 untouched |
| HIST-02 | 15-02, 15-05, 15-07 | View/compare scores across past versions | ✓ SATISFIED (mechanism) | Freezing mechanism itself is correct and independently verified — but see the new Truth 6 finding: a version can be frozen from an incomplete questionnaire, which undermines the practical trustworthiness of "past versions" a user compares, even though the strict requirement wording ("view a history... compare maturity scores across versions") is met |

**Orphaned requirements check:** All 7 phase requirement IDs (QSTN-02, SAVE-01, SAVE-02, SAVE-03, SAVE-04, HIST-01, HIST-02) appear in at least one plan's `requirements-completed` list, including the two gap-closure plans (15-06: HIST-01, 15-07: HIST-02). No orphans found.

**Cross-cutting note:** The new Truth 6 finding also touches **SCOR-04** ("Report/scores are only computed and shown once the full questionnaire is 100% answered", owned by Phase 14, already marked Complete in REQUIREMENTS.md). SCOR-04 still holds for `scoring.py`/`reports.py` — this verification found no regression there — but the new submit-time snapshot code path 15-07 added to `initiatives.py` is a second, un-gated place scores are now computed, and it does not honor SCOR-04's completeness precondition. This is flagged here because the defect lives entirely inside phase 15's own diff, not because SCOR-04 itself is reopened.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/app/api/v1/initiatives.py` | 82-128 | `submit_initiative` computes/freezes scores with no `assert_assessment_complete` gate (CR-01, `15-REVIEW-gaps.md`) | 🛑 Blocker | Confirmed via independent repro — see Gaps |
| `backend/app/api/v1/questionnaire.py` (`upsert_answer`) | — | Narrow race: an answer write can land after a concurrent submit has already frozen the snapshot (WR-02, `15-REVIEW-gaps.md`) | ⚠️ Warning | Pre-existing lock check, but 15-07's frozen-snapshot guarantee is the first place this race affects data integrity, not just UX; not independently reproduced under load in this pass (narrow timing window) |
| `backend/alembic/versions/k2b3c4d5e6f7_...py` | 28-31 | Downgrade docstring overstates "not lossy" — only true before the column is ever populated (WR-01) | ⚠️ Warning | Documentation risk for a future operator rollback in production |
| `frontend/src/routes/_app/dashboard.tsx` | 111 | Hardcoded "52 questions" in retake dialog copy, unlike sibling components that always derive the count from config (WR-03) | ⚠️ Warning | Will silently go stale once QSTN-05 replaces the placeholder config |
| `frontend/src/routes/_app/dashboard.tsx` | 118-124 | `reportError` state reused for retake failures (IN-01) | ℹ️ Info | Maintainability only |
| `backend/tests/migrations/test_frozen_scores_migration.py` | — | No test exercises the lossy-downgrade case (IN-02) | ℹ️ Info | Documentation/test-completeness only |

None of the warnings/info items are debt markers (no TBD/FIXME/XXX). The one Blocker (submit-completeness gate) is independently confirmed in this pass via a standalone reproduction, not merely accepted from the code review's narrative.

### Human Verification Required

None. The new finding is confirmed directly and completely via independent code reading, grep, and an executed reproduction test (1-of-52 submit returning 200 with a permanently frozen 0.07 average) — no ambiguity requiring human judgment.

### Gaps Summary

Both original gaps from the prior verification pass are genuinely closed:

1. **Gap 1 (CR-01/HIST-01, retake non-functional) — CLOSED.** `POST /initiatives/{id}/retake` now performs the missing `Initiative.status` reset atomically with a version-incremented blank draft, wired to the dashboard's confirm dialog, proven by a real end-to-end HTTP test.
2. **Gap 2 (CR-02/HIST-02, history not frozen) — CLOSED.** `Assessment.dimension_scores` is now a JSONB snapshot computed once at submit time and preferred over live recomputation, proven immune to live config drift by a test that mutates the config mid-test via dependency override.

However, this re-verification independently confirms a **new blocking defect**, surfaced by the same-run code review (`15-REVIEW-gaps.md` CR-01) and directly reproduced here rather than taken on faith:

3. **NEW — `submit_initiative` never verifies questionnaire completeness before permanently freezing a score snapshot.** Every other scoring/reporting endpoint in this codebase (`scoring.py`, `reports.py`) calls `assert_assessment_complete` first; the exact endpoint 15-07 modified to compute and freeze `dimension_scores` does not. I independently reproduced this: a standalone test answering 1 of 52 real config questions calls the real `POST /submit` and receives `200`, after which `GET /initiatives/{id}/assessments` permanently returns `overall_average: 0.07` (5 of 6 categories frozen at `0.0`) with no correction path short of a full retake that destroys every real answer already given. This is also directly provable from the gap-closure plans' own committed test, `test_retake_flow.py::test_submit_then_retake_unlocks_editing_and_creates_v2_draft`, which answers only `q-1-1` and asserts a 200 submit against the real config.

This directly threatens the phase goal's own wording — "**every full completion** creates a new, **permanently preserved** assessment version" implies incomplete completions should not produce permanently preserved versions at all. A user (or an automated/malicious client bypassing the wizard's own client-side "must complete this category before Next" gating) can today create garbage history entries with no way back except discarding all real progress. The fix is small and well-scoped (add `assert_assessment_complete(session, initiative_id, config)` inside `submit_initiative`'s `if assessment:` branch, mirroring the existing pattern in `scoring.py`/`reports.py`, plus a 422 regression test) — this does not require re-opening 15-06 or 15-07's other work, both of which are independently confirmed sound.

**Recommendation:** This is not a wholesale rejection — 5 of 6 truths are solidly verified, and the two originally-identified gaps are genuinely and cleanly closed. A small, targeted closure plan (15-08) adding the missing completeness gate to `submit_initiative` (plus its regression test) should close this before Phase 15 is considered done.

---

_Verified: 2026-07-26T11:24:00Z_
_Verifier: Claude (gsd-verifier)_
