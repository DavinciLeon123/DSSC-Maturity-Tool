---
phase: 15-questionnaire-submission-api-wizard-ui-save-reliability
reviewed: 2026-07-26T11:18:11Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - backend/alembic/versions/k2b3c4d5e6f7_assessment_frozen_dimension_scores.py
  - backend/app/api/v1/initiatives.py
  - backend/app/models/assessment.py
  - backend/app/services/dimension_scoring.py
  - backend/tests/api/test_frozen_scores.py
  - backend/tests/api/test_retake_flow.py
  - backend/tests/migrations/test_frozen_scores_migration.py
  - docs/api/openapi.json
  - frontend/src/routes/_app/dashboard.tsx
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 15: Code Review Report (gap-closure: plans 15-06, 15-07)

**Reviewed:** 2026-07-26T11:18:11Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the two gap-closure fixes at standard depth: `POST /initiatives/{id}/retake`
(15-06, fixing the retake-status-never-reset bug) and the frozen
`Assessment.dimension_scores` snapshot column (15-07, fixing live-config score drift
in history).

The retake endpoint itself is well-built: ownership is re-derived before any state
change, the 409 guard against retaking a still-in-progress draft is correct, and the
"reuse `_get_or_create_draft_assessment`'s existing IntegrityError-catch-and-requery
race path" design genuinely does make the `initiative.status` reset and the new draft
insert atomic for whichever transaction wins a concurrent double-retake — I traced
both the winning and losing branches of that race and both converge to a consistent
end state. The `dimension_scores` migration chains cleanly off the single current head
(`j1a2b3c4d5e6`, verified no branch/fork), and the frozen-snapshot-preferred /
live-recompute-only-for-legacy-NULL fallback in `_to_summary` is implemented exactly
as documented — I could not find a path where a row carrying a snapshot ever
re-touches the live config.

However, I found one critical, directly provable defect: **`submit_initiative` never
calls `assert_assessment_complete` before freezing the dimension-score snapshot.**
Every other scoring/reporting endpoint in this codebase (`scoring.py`, `reports.py`)
enforces this gate; `submit_initiative` — the one endpoint 15-07 modified to call
`compute_dimension_scores` directly — does not, even though `compute_dimension_scores`'s
own docstring states completeness verification is "the caller's" obligation. This means
any authenticated user can submit (and permanently lock) a wildly incomplete
questionnaire, freezing a nonsensical score snapshot forever (a retake is the only way
out, and it wipes all prior answers). This is not a hypothetical: the submitted test
suite itself proves it — `test_submit_then_retake_unlocks_editing_and_creates_v2_draft`
in `test_retake_flow.py` answers exactly 1 of 52 real config questions and asserts
`submit_response.status_code == 200`.

Also flagging: a narrow but real race window in the (out-of-diff-scope, but directly
implicated) `upsert_answer` endpoint that can let an answer write land *after* a
concurrent submit has already frozen the snapshot, plus a couple of maintainability
issues (an overstated "not lossy" downgrade claim in the migration docstring, and a
hardcoded question count in the frontend that duplicates a value the rest of the
codebase deliberately always derives from config).

## Critical Issues

### CR-01: `submit_initiative` freezes a dimension-score snapshot without ever verifying the questionnaire is complete

**File:** `backend/app/api/v1/initiatives.py:82-128`
**Issue:** Every other scorer/reporter in this codebase (`backend/app/api/v1/scoring.py:50`,
`backend/app/api/v1/reports.py:117,171,194,217,246,277`) calls
`assert_assessment_complete(session, initiative_id, config)` before computing scores.
`submit_initiative` — which 15-07 changed to call `compute_dimension_scores` directly at
line 124 — skips this entirely:

```python
assessment = session.exec(
    select(Assessment)
    .where(
        Assessment.initiative_id == initiative_id,
        Assessment.status == AssessmentStatus.draft,
    )
    .order_by(Assessment.created_at.desc())
).first()
if assessment:
    assessment.status = AssessmentStatus.submitted
    assessment.submitted_at = datetime.utcnow()
    assert assessment.id is not None
    assessment.dimension_scores = compute_dimension_scores(session, assessment.id, config)
    session.add(assessment)
```

`compute_dimension_scores`'s own docstring (`dimension_scoring.py:120-124`) states: "Caller
MUST have already verified completeness via `assert_assessment_complete` (SCOR-04) — this
function does not re-check and will silently divide by each category's config-derived
question count regardless of how many rows actually exist." `submit_initiative` is exactly
the kind of caller that docstring warns about, and it does not do this.

Consequences, all real and reachable by any authenticated user directly hitting the API
(not just a hypothetical): the initiative is flipped to `submitted` (locking every further
`PUT /answers` with a 403 per the CR-01 lock in `questionnaire.py`), and a permanent,
nonsensical `dimension_scores` snapshot is frozen — e.g. a category with 9 questions and
only 1 answered scores `round(4/9, 2) = 0.44`, and every category with zero answers scores
`0.0` (via `sums.get(cat_id, 0)` defaulting to 0) — with no way to correct it short of a
full retake that discards every existing answer.

This is proven directly by this diff's own test suite:
`backend/tests/api/test_retake_flow.py::test_submit_then_retake_unlocks_editing_and_creates_v2_draft`
answers only `q-1-1` (1 question) and then asserts:
```python
submit_response = client.post(f"/api/v1/initiatives/{initiative.id}/submit")
assert submit_response.status_code == 200
```
against the real 6-category/52-question DSSC config — i.e., the test that was written to
prove the retake fix incidentally proves this submit-completeness gap too.

**Fix:**
```python
from app.services.dimension_scoring import assert_assessment_complete, compute_dimension_scores

@router.post("/{initiative_id}/submit", status_code=200)
def submit_initiative(
    initiative_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    config: dict = Depends(get_dssc_questionnaire_config),
):
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")

    # Idempotent re-submit of an already-submitted initiative should stay a
    # no-op 200, not re-run the completeness gate against a draft that no
    # longer exists — only enforce completeness when there is a draft to lock.
    draft = get_current_assessment(session, initiative_id)
    if draft is not None:
        assert_assessment_complete(session, initiative_id, config)
        draft.status = AssessmentStatus.submitted
        draft.submitted_at = datetime.utcnow()
        draft.dimension_scores = compute_dimension_scores(session, draft.id, config)
        session.add(draft)

    initiative.status = InitiativeStatus.submitted
    initiative.updated_at = datetime.utcnow()
    session.add(initiative)
    session.commit()
    return {"message": "Initiative submitted successfully", "status": initiative.status.value}
```
Also add a regression test asserting `POST /submit` returns 422 (not 200) when fewer than
all config questions are answered, mirroring the existing 422 tests for `scoring.py`/
`reports.py`.

## Warnings

### WR-01: Migration downgrade's "not lossy" claim is only true before the feature is ever used

**File:** `backend/alembic/versions/k2b3c4d5e6f7_assessment_frozen_dimension_scores.py:28-31`
**Issue:** The docstring states: "Downgrade: drops the column. Not lossy in any meaningful
sense — this column has no prior values to lose (it is new)." That's only true in the
narrow window between deploying this migration and the first real submission. The instant
any assessment is submitted in production, `dimension_scores` holds the one and only
permanently-preserved snapshot this entire phase (HIST-02) exists to guarantee — running
`alembic downgrade` after that point (e.g. an operator rolling back a bad release) silently
`DROP COLUMN`s and destroys every frozen historical score, which is precisely the
"permanently preserved assessment version" guarantee this feature was built to protect.
The round-trip test (`test_frozen_scores_migration.py`) only ever exercises this against an
empty table, so nothing catches or documents the real-world lossy case.
**Fix:** Correct the docstring to state the downgrade is lossy for any row with a non-NULL
`dimension_scores` once the feature has been used (don't claim blanket safety), and consider
guarding the real operational runbook (not necessarily the migration itself) with an
explicit check/backup step before downgrading past this revision in production.

### WR-02: Race window lets an answer write land after the frozen snapshot is taken, silently breaking the immutability guarantee

**File:** `backend/app/api/v1/questionnaire.py` (`upsert_answer`, referenced by
`initiatives.py`'s CR-01 lock comment; not itself in this diff's file list, but directly
implicated by the correctness question this review was asked to check)
**Issue:** `upsert_answer` reads `initiative.status` and rejects with 403 only if it is
already `submitted` at the time that read happens. There is no row lock/serialization
between that read and `POST /submit`'s own read-then-flip of the same `Initiative` row. A
request that begins (and passes the not-yet-submitted check) a moment before a concurrent
`POST /submit` commits can still complete its `session.commit()` afterward — the pg upsert
has no application-level guard tying it to `Assessment.status`, only `QuestionnaireAnswer`'s
own unique constraint. The result: an answer is written to (or updates one already in) an
assessment whose `dimension_scores` snapshot was already computed and frozen one line
earlier in `submit_initiative`, so the newly-written answer is now permanently invisible to
history — a real, if narrow-window, way for the "immutable submitted snapshot" invariant
this phase relies on to be violated. This is pre-existing (the `initiative.status ==
InitiativeStatus.submitted` check predates 15-06/15-07), but 15-07's frozen-snapshot
guarantee is the first place this race actually matters for data integrity rather than just
a UX inconvenience.
**Fix:** Re-check `Assessment.status == AssessmentStatus.draft` (not just
`Initiative.status`) transactionally at the point of the answer upsert — e.g. `SELECT ...
FOR UPDATE` on the assessment row, or a `WHERE assessment.status = 'draft'` guard on the
upsert itself that raises if zero rows matched — so a submit-in-flight cannot be raced.

### WR-03: Hardcoded "52 questions" in the retake confirmation dialog duplicates a value this codebase otherwise always derives from config

**File:** `frontend/src/routes/_app/dashboard.tsx:111`
**Issue:**
```tsx
content:
  "This creates a new, permanent version in your history. Your previous submitted assessment stays unchanged, and you'll answer all 52 questions again from scratch — nothing carries over.",
```
The rest of this codebase treats the total question count as strictly config-derived and
never hardcoded — `WizardPage.tsx`'s `totalQuestions` and `StepPills.tsx`'s own
`totalQuestions` are both explicitly commented "D-04: ... always derived from config
(never a hardcoded 52)". This file hardcodes the same number the sibling components
deliberately avoid hardcoding, in the one place (`dashboard.tsx`) that doesn't have the
questionnaire config loaded. Since the config is explicitly called out elsewhere in this
codebase as a placeholder pending real content (QSTN-05), this text will silently go stale
the moment the question count changes, and nothing will catch it.
**Fix:** Either fetch the question count (e.g. via a lightweight `/questionnaire/config`
call or by including a `total_questions` field on `GET /initiatives/me`) and interpolate it,
or drop the specific number from the copy ("you'll answer every question again from
scratch") so it can't drift from the real config.

## Info

### IN-01: `reportError` state is overloaded to also carry retake failures

**File:** `frontend/src/routes/_app/dashboard.tsx:118-124`
**Issue:** `handleStartOrRetake`'s `onOk` catch block calls `setReportError(...)` on a
failed retake, reusing the same state variable (and rendered `<Alert>`) that
`handleGenerateReport` uses for report-generation failures. A future maintainer debugging
"why did the report error banner appear" has no way to tell from the state name that it
might actually be a failed retake.
**Fix:** Add a small dedicated state (e.g. `actionError`) or rename `reportError` to
something generic like `initiativeActionError` shared intentionally, with a comment
explaining the reuse is deliberate.

### IN-02: No migration test exercises the lossy-downgrade case described in WR-01

**File:** `backend/tests/migrations/test_frozen_scores_migration.py`
**Issue:** Both tests in this file operate against an empty `assessment` table — neither
inserts a row with a non-NULL `dimension_scores` before downgrading, so there is no
executable evidence (positive or negative) of what actually happens to real frozen
snapshots on a downgrade. Given WR-01, this would have been informative either way.
**Fix:** Add a test that inserts an `assessment` row with `dimension_scores` populated,
downgrades, and documents (via a comment, since the assertion is the same "column is
gone") that any data in that column is now lost — turning the current implicit assumption
into an explicit, intentional one.

---

_Reviewed: 2026-07-26T11:18:11Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
