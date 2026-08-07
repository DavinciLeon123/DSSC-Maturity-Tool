---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
reviewed: 2026-07-26T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - backend/app/api/v1/initiatives.py
  - backend/tests/api/test_submit_completeness.py
  - backend/tests/api/test_retake_flow.py
  - docs/api/openapi.json
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: issues_found
---

# Phase 15: Code Review Report — Gap-Closure Round 3 (Plan 15-08)

**Reviewed:** 2026-07-26
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found (Info only — no Critical or Warning findings)

## Summary

Reviewed the 15-08 diff (merge `20f83b6`, commits `f47000d..0de6f2a`) that adds the `assert_assessment_complete` completeness gate to `submit_initiative` and the accompanying test changes. This closes the single blocking gap from `15-VERIFICATION.md`: an incomplete draft (e.g. 1 of 52 questions answered) could previously be submitted (200) and permanently freeze a garbage `dimension_scores` snapshot.

**Core correctness verified independently, not just accepted on the executor's word:**

- **Gate placement is correct.** `assert_assessment_complete(session, initiative_id, config)` is the first statement inside the `if assessment:` branch (`initiatives.py:138-139`), strictly before `assessment.status = AssessmentStatus.submitted` (line 140) and before `compute_dimension_scores` (line 143). An incomplete draft raises 422 before any mutation in this function occurs.
- **Idempotent resubmit path verified correct.** When no draft assessment exists (`assessment is None`), the `if assessment:` block is skipped entirely and execution falls through to the unconditional `initiative.status = InitiativeStatus.submitted` / `session.add(initiative)` / `session.commit()` at lines 146-150 — the gate is genuinely skipped, not silently bypassed by a broken conditional. Confirmed by `test_submit_idempotent_resubmit_stays_200` passing.
- **The self-reported "Rule 1" reorder bug fix is real and correctly fixed.** I traced this independently rather than taking the SUMMARY's word for it:
  - Confirmed via `backend/app/db/session.py:15-17` that production `get_session()` opens a **fresh** `Session(engine)` per request (`with Session(engine) as session: yield session`), so the old ordering's transient in-memory mutation could never leak across separate production requests — consistent with the SUMMARY's claim.
  - Confirmed via `backend/tests/conftest.py:49-105` that the test harness's `get_session` dependency override returns the **same** `db_session` object for every HTTP call within one test (function-scoped fixture, no per-request session), so SQLAlchemy's identity map genuinely would have carried a dangling, uncommitted `initiative.status = submitted` mutation into the next request within the same test — exactly the scenario the SUMMARY describes, and exactly what `test_submit_422_when_incomplete`'s "subsequent PUT still returns 200, not 403" assertion (`upsert_answer` reads `initiative.status` off the identity-mapped object via `session.get`) would have caught.
  - Confirmed the reorder introduces no regression: `initiative.status = InitiativeStatus.submitted` still runs unconditionally after the `if assessment:` block regardless of whether that block ran, so the no-draft/idempotent-resubmit path still sets status as before.
  - This was a legitimate, correctly-scoped, low-risk fix — not scope creep, and the claim in the SUMMARY holds up under independent verification.
- **Ownership checks unchanged and correctly ordered** — 404/403 ownership derivation still precedes the gate, matching every other route in the file; no authorization bypass introduced.
- **Tests are genuinely HTTP-driven**, not internal-function calls or mocks: all three new tests in `test_submit_completeness.py` and the updated tests in `test_retake_flow.py` exercise real `PUT /questionnaire/.../answers/{id}` and `POST /initiatives/{id}/submit` calls through the FastAPI `TestClient`.
- **No hardcoded question count.** Both `test_submit_completeness.py::_answer_all_questions_via_http` and `test_retake_flow.py::_answer_all_questions_via_http` iterate `config["categories"] -> questions` via `load_dssc_questionnaire_config()` at test run time — verified the live config currently has 6 categories / 52 questions, and neither test file hardcodes that number anywhere, so the tests will not silently under-answer (and pass incorrectly) if the config's question set grows or shrinks.
- Ran the actual gates myself rather than trusting the SUMMARY's reported results: `ruff check`/`ruff format --check` clean, `mypy app --ignore-missing-imports` clean, and `pytest tests/api/test_submit_completeness.py tests/api/test_retake_flow.py tests/api/test_frozen_scores.py tests/api/test_scoring.py tests/api/test_assessment_history.py -q` → 17 passed.
- `docs/api/openapi.json`'s only diff hunk is the `submit_initiative` route's `description` field gaining the new SCOR-04 docstring paragraph verbatim — no unrelated schema drift.

No Critical or Warning-level defects were found in this diff. The three items below are minor maintainability notes, included for completeness per the adversarial review mandate, not because they represent risk.

## Critical Issues

None found.

## Warnings

None found.

## Info

### IN-01: Redundant duplicate query for the current draft assessment

**File:** `backend/app/api/v1/initiatives.py:130-139`
**Issue:** `submit_initiative` queries for the current draft `Assessment` directly (lines 130-137) to decide whether to enter the `if assessment:` branch, then immediately calls `assert_assessment_complete(session, initiative_id, config)` (line 139), which internally re-runs the *exact same* query via `get_current_assessment` (`dimension_scoring.py:43-59`) and discards its returned `Assessment` in favor of the outer-scope `assessment` variable. This is a second DB round-trip for data already in hand — functionally harmless (SQLAlchemy's identity map guarantees the same object is returned, so there's no risk of the two reads diverging within one transaction), but it's avoidable duplication that a future refactor could easily miss and assume `assert_assessment_complete`'s return value is unused for no reason.

Contrast with `scoring.py:50`, the pattern this gate is explicitly mirroring, which uses the function as intended: `assessment = assert_assessment_complete(session, initiative_id, config)` — one query, no discarded return value. `initiatives.py` can't adopt that exact one-liner because it has an additional requirement `scoring.py` doesn't (skip the gate entirely, not treat "no draft" as an error, on the idempotent resubmit path) — but the redundancy is still worth calling out as a known, intentional trade-off rather than an oversight.

**Fix:** Not required to change now given the correctness trade-off above; if ever revisited, consider a variant like `get_current_assessment(session, initiative_id)` reused directly for the branch check, with the completeness-only logic (`_full_question_ids(config) - answered_ids`) factored out separately so it can be called without re-querying the assessment row. Low priority.

### IN-02: Test helper duplication (`_login` / `_answer_all_questions_via_http`) grows with this change

**File:** `backend/tests/api/test_submit_completeness.py:19-44`, `backend/tests/api/test_retake_flow.py:19-44`
**Issue:** This plan adds a 7th near-identical copy of the `_login`/`_answer_all_questions_via_http` helper pair across `backend/tests/api/` (already duplicated in `test_frozen_scores.py`, `test_reports.py`, `test_questionnaire_answers.py`, `test_scoring.py`, `test_assessment_history.py` prior to this plan). `test_submit_completeness.py` is a wholly new file that copies both helpers verbatim rather than importing a shared version, and `test_retake_flow.py` gains its own second copy of `_answer_all_questions_via_http` (it already had `_login`). This is a pre-existing pattern this plan continues rather than one it introduces from scratch, but every new copy makes a future change to the answer-PUT contract (e.g. a new required field) a multi-file find-and-replace instead of a one-line fix.
**Fix:** Consider hoisting `_login` and `_answer_all_questions_via_http` into a shared `tests/api/conftest.py` fixture or `tests/helpers.py` module in a future cleanup pass — out of scope for this gap-closure plan specifically, but worth tracking so the duplication doesn't keep compounding.

### IN-03: Stale test comment after the full-answer loop overwrites the score it describes

**File:** `backend/tests/api/test_retake_flow.py:55-65`
**Issue:** The test comments "First answer creates a draft Assessment at version 1" for the `q-1-1` PUT with `score: 4` (line 58), then three lines later calls `_answer_all_questions_via_http(client, initiative.id, config)` (line 65) with its default `score=3`, which re-PUTs `q-1-1` as part of iterating every question in `cat-1` — silently overwriting that answer's score from 4 to 3 before submission. No assertion in the test depends on the value 4 surviving, so this isn't a functional bug, but the comment/reader's mental model ("q-1-1 is answered with a 4") no longer matches what's actually frozen into the v1 snapshot by the time `submit` runs.
**Fix:** Either drop the specific `score: 4` from the initial PUT's stated intent (since it's immediately overwritten) or exclude `q-1-1` from the full-answer loop and only answer the remaining questions, so the comment and the final on-disk state agree. Cosmetic — does not affect test correctness or coverage.

---

_Reviewed: 2026-07-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
