---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
reviewed: 2026-07-26T09:50:10Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - backend/alembic/versions/j1a2b3c4d5e6_assessment_version_lastviewed.py
  - backend/app/api/v1/initiatives.py
  - backend/app/api/v1/questionnaire.py
  - backend/app/models/assessment.py
  - backend/app/schemas/assessment.py
  - backend/app/schemas/questionnaire.py
  - backend/app/services/dimension_scoring.py
  - backend/tests/api/test_assessment_history.py
  - backend/tests/api/test_questionnaire_answers.py
  - backend/tests/factories.py
  - backend/tests/migrations/test_assessment_version_migration.py
  - docs/api/openapi.json
  - frontend/src/components/questionnaire/AnswerButtonGroup.tsx
  - frontend/src/components/questionnaire/QuestionCard.tsx
  - frontend/src/components/questionnaire/StepPills.tsx
  - frontend/src/components/questionnaire/WizardPage.tsx
  - frontend/src/hooks/useDebouncedSave.ts
  - frontend/src/lib/assessments.ts
  - frontend/src/lib/questionnaire.ts
  - frontend/src/routeTree.gen.ts
  - frontend/src/routes/_app/assessments.tsx
  - frontend/src/routes/_app/dashboard.tsx
  - frontend/src/routes/_app/questionnaire.tsx
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: issues_found
---

# Phase 15: Code Review Report

**Reviewed:** 2026-07-26T09:50:10Z
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

Reviewed the backend answer-upsert/history/last-viewed-category endpoints, the
`Assessment` model and its new migration, the autosave/debounce frontend
stack (`WizardPage`, `useDebouncedSave`), and the new assessment-history UI.
The individual pieces (per-question debounce/retry state machine, rate-limit
key function, ownership re-derivation on every route, WR-02/WR-03 input
validation on `upsert_answer`, the version-uniqueness migration) are each
well-reasoned and mostly well-tested in isolation.

However, tracing the new **retake** feature end-to-end (dashboard's new
"Start new assessment" confirm dialog → `/questionnaire` → answer saves →
version-increment machinery → assessment history) surfaces a hard blocker:
nothing in the codebase ever resets `Initiative.status` back to `draft`
after submission, so the retake flow this phase ships is provably
non-functional through the UI. A second blocker concerns the "immutable
history" feature: historical/submitted assessment scores are recomputed
live against whatever the *current* questionnaire config is, not frozen at
submission time, undermining the "permanently preserved version" guarantee
the feature is built around. Both are traceable directly from the code and
docstrings in this diff, not hypothetical.

## Critical Issues

### CR-01: Retake flow is shipped but non-functional — Initiative.status is never reset after submission

**File:** `frontend/src/routes/_app/dashboard.tsx:101-121` (new `handleStartOrRetake`), `backend/app/api/v1/initiatives.py:99` (`submit_initiative` sets `initiative.status = InitiativeStatus.submitted`), `backend/app/api/v1/questionnaire.py:158-159` (`upsert_answer`'s submitted-lock) and `:323-324` (`update_last_viewed_category`'s submitted-lock)

**Issue:** This phase adds `handleStartOrRetake` (new in this diff), which shows a "Start a new assessment?" confirm dialog for a `submitted` initiative and, on confirm, simply navigates to `/questionnaire` — assuming the user can now answer questions again. But `Initiative.status` is set to `submitted` exactly once, in `submit_initiative` (`initiatives.py:99`), and **nothing anywhere in the codebase ever sets it back to `draft`** (verified via `grep -rn "InitiativeStatus.draft\|status = InitiativeStatus"` across `app/` — the only assignment is the one-way flip to `submitted`). Both write endpoints the wizard depends on for a retake — `upsert_answer` and `update_last_viewed_category` — explicitly 403 whenever `initiative.status == InitiativeStatus.submitted` (this is the very "CR-01" lock these routes' own docstrings describe as intentional and load-bearing).

So the sequence a real user takes is: submit → dashboard shows "Retake Questionnaire" → confirm dialog → navigate to `/questionnaire` → answer the first question → **403 "Submitted assessments cannot be edited"** on every single save, forever. The new version-increment machinery in `_get_or_create_draft_assessment` (D-15/HIST-01, the whole point of this phase's migration `j1a2b3c4d5e6`) is unreachable through the UI because the submitted-lock guard fires before a new draft Assessment can ever be created for that initiative again.

This gap is also visible in the test suite: `backend/tests/api/test_questionnaire_answers.py::test_version_increment_on_retake_after_prior_submission` explicitly avoids calling the real `POST /submit` endpoint and instead flips `Assessment.status` directly via the session, with an in-line comment acknowledging *"without flipping the Initiative itself, so a subsequent answer-save PUT is still permitted (initiative-level submission-lock is a separate concern from this plan's scope)"*. No test anywhere exercises the real HTTP path (`POST /submit` → `PUT answer`) for a retake, because doing so would fail with a 403.

**Fix:** Add the missing reset as part of this phase, e.g. in `_get_or_create_draft_assessment` (or a new explicit "start retake" endpoint the dashboard confirm-dialog calls before navigating):
```python
# in _get_or_create_draft_assessment, right after computing next_version
# (i.e. we are genuinely starting a new draft, not reusing an existing one):
initiative = session.get(Initiative, initiative_id)
if initiative and initiative.status == InitiativeStatus.submitted:
    initiative.status = InitiativeStatus.draft
    session.add(initiative)
```
or, preferably, an explicit `POST /initiatives/{id}/retake` endpoint that atomically resets `Initiative.status` in the same transaction the confirm dialog's `onOk` calls, so the "start a new assessment" action is a single well-defined write rather than an implicit side effect of the next answer save.

---

### CR-02: "Immutable" assessment history is recomputed live against the current config, not frozen at submission time

**File:** `backend/app/services/dimension_scoring.py:114-145` (`compute_dimension_scores`), `backend/app/api/v1/initiatives.py:148-158` (`_to_summary`), `frontend/src/routes/_app/assessments.tsx:93-127` (comparison table)

**Issue:** `list_assessment_history` (HIST-02) and its frontend consumer (`assessments.tsx`'s "Compare scores across versions" table) are built around the premise that a submitted assessment version is a permanently preserved, immutable historical record (per this phase's own docstrings: D-14 "prior version immutable", D-15/HIST-01 "a retake ... is a distinguishable, permanently preserved new version"). But `compute_dimension_scores` has no concept of "the config as it was when this assessment was submitted" — it always derives category names, per-category question counts, and score divisors from whatever `config: dict` is injected via `Depends(get_dssc_questionnaire_config)` **at request time**, i.e. the live/current config. `dimension_scoring.py`'s own module docstring flags this directly: *"the config's current question/category shape is an explicit placeholder pending real content (QSTN-05)"* — meaning the config is expected to change.

Once the real 52-question config replaces the placeholder (or is edited at all — added/removed questions, renamed categories, changed per-category counts), every previously-submitted assessment's `dimension_scores`/`overall_average` returned by `GET /initiatives/{id}/assessments` will silently change to reflect the new config, not the config the user actually answered against. This is a data-integrity regression for a feature whose entire value proposition is "look back at exactly what you submitted before."

**Fix:** Snapshot what's needed to reproduce the score at submission time — either persist the computed `dimension_scores` (and `overall_average`) as a JSON column on `Assessment` at the moment `submit_initiative` flips it to `submitted`, or persist the `config` version/hash used and reject recomputation against a different version. Simplest fix compatible with the current schema:
```python
# in submit_initiative, when flipping assessment.status:
assessment.status = AssessmentStatus.submitted
assessment.submitted_at = datetime.utcnow()
assessment.frozen_dimension_scores = compute_dimension_scores(session, assessment.id, config)  # new JSON column
```
and have `list_assessment_history`/`_to_summary` prefer the frozen snapshot over a live recompute when present.

## Warnings

### WR-01: Migration adds a new unique constraint with no guard against pre-existing duplicate (initiative_id, version) rows

**File:** `backend/alembic/versions/j1a2b3c4d5e6_assessment_version_lastviewed.py:54-58`

**Issue:** `upgrade()` calls `op.create_unique_constraint("uq_assessment_version_per_initiative", "assessment", ["initiative_id", "version"])` unconditionally. The migration's own docstring explains that prior to this change `version` "always default[ed] to 1", meaning any pre-existing environment where an initiative accumulated more than one `Assessment` row (e.g. a draft plus an already-submitted row, or any manually seeded/staging data) is very likely to already violate this exact constraint. `alembic upgrade head` will then fail mid-deployment with no automated remediation, and `tests/migrations/test_assessment_version_migration.py` never exercises an upgrade against a DB seeded with such duplicates — every test seeds a clean DB first.

**Fix:** Add a pre-flight dedup/guard step in `upgrade()` before creating the constraint, e.g. detect and reassign conflicting duplicate `(initiative_id, version)` pairs to the next free version number, or at minimum document the required manual remediation query in the migration docstring and add a test that upgrades against a DB seeded with a duplicate pair to prove the failure mode is understood.

### WR-02: `update_last_viewed_category` does not validate `category_id` against the loaded config

**File:** `backend/app/api/v1/questionnaire.py:292-331`

**Issue:** `upsert_answer` validates `question_id`/`category_id` against `config` before persisting (the WR-02 comment at `questionnaire.py:170-186` in this same file). The new sibling endpoint `update_last_viewed_category`, added in this same phase, has no equivalent check — it persists `body.category_id` as an arbitrary string with no relationship to `config.get("categories", [])`. A client can PATCH any string into `last_viewed_category_id`. The frontend defensively falls back to index 0 if the id isn't found (`WizardPage.tsx:87-88`), so this isn't exploitable for privilege escalation, but it's an inconsistent validation posture within the same file and lets garbage values accumulate in the column.

**Fix:**
```python
valid_category_ids = {cat["id"] for cat in config.get("categories", [])}
if body.category_id not in valid_category_ids:
    raise HTTPException(status_code=422, detail="Unknown category_id")
```
(requires adding `config: dict = Depends(get_dssc_questionnaire_config)` to this route's signature).

### WR-03: Auto-clear and debounce/retry timers are never cleared on unmount

**File:** `frontend/src/components/questionnaire/WizardPage.tsx:129-139`, `frontend/src/hooks/useDebouncedSave.ts` (no cleanup effect anywhere in the hook)

**Issue:** `handleSaveStateChange` schedules bare `setTimeout` calls to auto-clear the "saved" (2s) and "rate-limited" (3s) badge states back to "idle", and `useDebouncedSave`'s `schedule()`/`saveWithRetry()` register debounce timers and `await new Promise(setTimeout...)` backoff delays — none of these are tracked/cleared in a `useEffect` cleanup on unmount. If the user navigates away from the questionnaire (e.g. clicking a nav-bar link rather than Next/Back, which do call `flushAll`) while a debounce/backoff/auto-clear timer is still pending, the timer still fires later and calls `setSaveStates`/`onStateChange` against an unmounted component, producing "Can't perform a React state update on an unmounted component" warnings and doing wasted work.

**Fix:** Track all live timeout ids in a ref array/set inside `useDebouncedSave` and add a `useEffect` cleanup in `WizardPage` (or expose a `cancelAll()` from the hook) that clears them on unmount; guard the `setTimeout` callbacks in `WizardPage.tsx:129-139` similarly (e.g. an `isMountedRef`).

### WR-04: `compute_dimension_scores`/`_to_summary` divide by counts that can be zero

**File:** `backend/app/services/dimension_scoring.py:137-144`, `backend/app/api/v1/initiatives.py:148-158`

**Issue:** `compute_dimension_scores` computes `sums.get(cat_id, 0) / n_questions` for every category in `config`, and `_to_summary` computes `sum(...) / len(scores)`. Neither guards against `n_questions == 0` (a category with an empty `questions` list) or `len(scores) == 0` (a config with no categories) — both would raise `ZeroDivisionError`, surfacing as an unhandled 500 rather than a clean error. This function predates this phase, but this phase is the first caller to expose it through a new, directly user-triggered endpoint (`GET /initiatives/{id}/assessments`), so a malformed/edited config now has a new crash surface.

**Fix:** Guard both divisions, e.g. `n_questions and (sums.get(cat_id, 0) / n_questions) or 0.0`, and raise a clear 500/422 with a stable message if `len(scores) == 0` in `_to_summary` rather than letting `ZeroDivisionError` propagate.

## Info

### IN-01: `WizardPage.handleRetrySave` calls `schedule()` immediately before `flush()`, making the `schedule()` call dead code

**File:** `frontend/src/components/questionnaire/WizardPage.tsx:196-210`

**Issue:** `handleRetrySave` calls `schedule(questionId, pending.categoryId, pending.score)` and then immediately `void flush(questionId)`. `schedule()` sets a new debounce timeout; `flush()` (called synchronously right after, since neither is awaited between them) immediately reads the same `pending` entry, clears that very timeout, and fires `saveWithRetry` right away. The `schedule()` call never has any observable effect — its timer is cleared before it can ever run — so it's confusing, misleading dead code that suggests a debounce is happening when it isn't.

**Fix:** Drop the `schedule(...)` call and just call `void flush(questionId)`, or better, call `saveWithRetry` directly if it's exposed, to make the "bypass debounce, retry now" intent explicit in code rather than relying on an implicit clear-before-fire race.

### IN-02: `AssessmentSummary.dimension_scores` is untyped (`list[dict]`)

**File:** `backend/app/schemas/assessment.py:17`

**Issue:** Every other field on `AssessmentSummary` is precisely typed, but `dimension_scores: list[dict]` has no nested schema, so FastAPI/Pydantic cannot validate or document the shape (`category_id`/`name`/`score`) in the OpenAPI spec, and a shape drift in `compute_dimension_scores`'s return value (e.g. a renamed key) would silently pass through with no schema-level signal.

**Fix:**
```python
class DimensionScore(BaseModel):
    category_id: str
    name: str
    score: float

class AssessmentSummary(BaseModel):
    id: int
    version: int
    submitted_at: str
    overall_average: float
    dimension_scores: list[DimensionScore]
```

---

_Reviewed: 2026-07-26T09:50:10Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
