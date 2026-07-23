---
phase: 13-new-questionnaire-config-schema-data-model-migration
reviewed: 2026-07-23T00:00:00Z
depth: standard
files_reviewed: 32
files_reviewed_list:
  - backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py
  - backend/app/api/v1/admin.py
  - backend/app/api/v1/initiatives.py
  - backend/app/api/v1/questionnaire.py
  - backend/app/api/v1/reports.py
  - backend/app/api/v1/scoring.py
  - backend/app/core/deps.py
  - backend/app/db/base.py
  - backend/app/main.py
  - backend/app/models/assessment.py
  - backend/app/models/initiative.py
  - backend/app/models/questionnaire.py
  - backend/app/models/questionnaire_answer_archive.py
  - backend/app/models/user.py
  - backend/app/schemas/auth.py
  - backend/app/schemas/initiative.py
  - backend/app/schemas/questionnaire.py
  - backend/app/services/mami_config.py
  - backend/app/services/report_generator.py
  - backend/tests/README.md
  - backend/tests/api/test_admin.py
  - backend/tests/api/test_evidence_removed.py
  - backend/tests/api/test_questionnaire.py
  - backend/tests/api/test_questionnaire_answers.py
  - backend/tests/api/test_reports.py
  - backend/tests/factories.py
  - backend/tests/migrations/__init__.py
  - backend/tests/migrations/test_v1_archive_migration.py
  - backend/tests/schemas/test_questionnaire_schemas.py
  - backend/tests/services/test_dssc_config.py
  - backend/tests/services/test_report_generator.py
  - config/dssc-questionnaire.json
  - docs/api/openapi.json
findings:
  critical: 2
  warning: 6
  info: 3
  total: 11
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-07-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 32
**Status:** issues_found

## Summary

This phase introduces the Assessment entity, the archive-table-split migration
(`i9d7e6f5a4b3`), and the reshaped `questionnaire_answer` (assessment_id/
category_id/score) across models, schemas, and API routes. The Alembic
migration itself is careful and well-tested: upgrade/downgrade symmetry,
verbatim archival of legacy rows, the zero-answers "stays v2" edge case, and
the DB-level CHECK constraint are all covered by real-Postgres migration
tests (`tests/migrations/test_v1_archive_migration.py`), and I did not find a
correctness defect in the migration's SQL itself.

The problems are concentrated at the boundary the phase explicitly touches:
the new Assessment draft/submitted lifecycle is modeled but never actually
enforced by the API (submitted initiatives can still have their answers
edited, and Assessment.status/submitted_at are dead fields in practice), and
a lazy-create race can silently split a user's answers across two orphaned
Assessment rows. Both are genuine data-integrity risks, not style
nitpicks. Several further inconsistencies exist between the migration's
stated intent ("participant_type ... never populated going forward") and
what the schemas/endpoints actually still do, plus a couple of instances of
new input accepted without validation against the loaded questionnaire
config.

## Critical Issues

### CR-01: Submitted initiatives can still have their questionnaire answers edited — the Assessment draft/submitted lifecycle this phase introduces is never enforced

**File:** `backend/app/api/v1/questionnaire.py:40-120`, `backend/app/api/v1/initiatives.py:78-94`, `backend/app/models/assessment.py:1-10`

**Issue:** `Assessment` is explicitly designed (per its own module docstring) to
carry a `draft`/`submitted` lifecycle with `submitted_at`, described as
satisfying "Phase 15's dated version need." But nothing in this phase ever
transitions an Assessment out of `draft`:

- `submit_initiative` (`initiatives.py:78-94`) only flips `Initiative.status`
  to `submitted`. It never touches the `Assessment` table at all — no
  `Assessment.status = submitted`, no `submitted_at` set.
- `_get_or_create_draft_assessment` (`questionnaire.py:40-60`) always looks
  up `Assessment.status == AssessmentStatus.draft` and returns it if found —
  so after "submission" this query still finds the very same (never-flipped)
  draft assessment.
- `upsert_answer` (`questionnaire.py:67-120`) checks only that the initiative
  belongs to the current user (`initiative.user_id != current_user.id`). It
  never checks `initiative.status` or the assessment's status. Contrast this
  with `update_initiative` (`initiatives.py:63-67`), which explicitly blocks
  edits once `initiative.status == InitiativeStatus.submitted` — that
  immutability guarantee is deliberately implemented for initiative metadata
  but is completely absent for the questionnaire answers themselves, which is
  the actual compliance-relevant content.

Net effect: a user can call `POST /initiatives/{id}/submit` and then continue
to `PUT /questionnaire/initiatives/{id}/answers/{question_id}` indefinitely,
silently mutating the "submitted" assessment's answers with no record that
anything changed after submission. For a compliance/audit tool this defeats
the entire point of having a submission lock, and it makes the new
`Assessment.status`/`submitted_at` fields dead weight — they are set once at
creation and never read/written again anywhere in the reviewed code.

**Fix:**
```python
# initiatives.py — submit_initiative: also flip the current draft Assessment
@router.post("/{initiative_id}/submit", status_code=200)
def submit_initiative(...):
    ...
    initiative.status = InitiativeStatus.submitted
    initiative.updated_at = datetime.utcnow()
    assessment = session.exec(
        select(Assessment)
        .where(Assessment.initiative_id == initiative_id, Assessment.status == AssessmentStatus.draft)
        .order_by(Assessment.created_at.desc())
    ).first()
    if assessment:
        assessment.status = AssessmentStatus.submitted
        assessment.submitted_at = datetime.utcnow()
        session.add(assessment)
    session.add(initiative)
    session.commit()
    ...

# questionnaire.py — upsert_answer: reject writes once submitted
if initiative.status == InitiativeStatus.submitted:
    raise HTTPException(status_code=403, detail="Submitted assessments cannot be edited")
```

### CR-02: Race condition in lazy Assessment creation can silently orphan answers (data loss)

**File:** `backend/app/api/v1/questionnaire.py:40-60`, `backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py:65-78`

**Issue:** `_get_or_create_draft_assessment` does a plain
select-then-insert with no locking and no DB-level uniqueness guard:

```python
assessment = session.exec(
    select(Assessment).where(Assessment.initiative_id == initiative_id, Assessment.status == AssessmentStatus.draft)
    .order_by(Assessment.created_at.desc())
).first()
if assessment:
    return assessment
assessment = Assessment(initiative_id=initiative_id)
session.add(assessment)
session.commit()
```

The `assessment` table (created in the migration, lines 67-78) has only a
plain (non-unique) index on `initiative_id` — there is no
`UNIQUE(initiative_id) WHERE status = 'draft'` constraint or equivalent. Two
concurrent first-answer requests for the same initiative (e.g. a
double-submit from autosave, or two open tabs) can both see "no draft exists"
and each insert their own `Assessment` row. From then on:
- `get_answers` and `_get_or_create_draft_assessment` both pick only the
  *latest* draft (`order_by(created_at.desc()).first()`), so any answers
  already written against the *older* draft become permanently invisible to
  the user and to reporting/scoring — a silent, unrecoverable data-loss bug,
  not just a UX glitch.

**Fix:** Add a partial unique index in the migration and/or use
`INSERT ... ON CONFLICT` semantics equivalent to it:
```python
op.create_index(
    "uq_assessment_one_draft_per_initiative",
    "assessment",
    ["initiative_id"],
    unique=True,
    postgresql_where=sa.text("status = 'draft'"),
)
```
and handle the resulting `IntegrityError` in `_get_or_create_draft_assessment`
by re-querying (retry-on-conflict pattern), rather than relying on an
unguarded check-then-insert.

## Warnings

### WR-01: Report/score endpoints return a fabricated "fully compliant" result for real answers under the new schema, with no indication to the caller that scoring is degraded

**File:** `backend/app/api/v1/reports.py:44-57,112-181`, `backend/app/api/v1/scoring.py:63-83`

**Issue:** `_degraded_scoring_inputs()` always returns `([], [])`, so
`findings_raw` is always empty for every initiative using the new answer
shape. `generate_report` then computes `compliant_count = len(answers) - 0 =
len(answers)` and persists/returns an HTML/PDF report claiming zero critical
and zero non-critical findings and 100% compliance for every real user who
filled in the questionnaire. This is clearly flagged internally as an
accepted Phase 13→14 interim gap (excellent in-code documentation), but the
HTTP responses themselves carry no signal of degraded/incomplete scoring —
an end user hitting `POST /initiatives/{id}/report` today gets a
production-looking, misleadingly "compliant" PDF emailed to them
(`mail_report`) with no disclaimer.

**Fix:** Until Phase 14 lands, gate these endpoints behind
`initiative.schema_version` (or equivalent) and return a clear "scoring not
yet available for this questionnaire version" response (e.g. 501/409)
instead of a fabricated 200 compliant report, or inject a visible banner into
the rendered HTML/PDF stating results are provisional/incomplete.

### WR-02: `upsert_answer` accepts arbitrary `question_id`/`category_id` with no validation against the loaded questionnaire config

**File:** `backend/app/api/v1/questionnaire.py:63-120`, `backend/app/schemas/questionnaire.py:6-9`

**Issue:** `AnswerCreate` only validates `score` bounds (`ge=1, le=5`).
Neither `question_id` (path param) nor `category_id` (body) is checked
against `dssc_questionnaire_config` (which is loaded and injected elsewhere
via `get_dssc_questionnaire_config`, but not into this endpoint). A client
can PUT any `question_id`/`category_id` string pair — including a
`category_id` that doesn't match the question's real category, or a
`question_id` that doesn't exist in the config at all — and it will be
persisted without error. Since scoring/reporting (Phase 14/16) will presumably
key off these values matching the config, this silently seeds bad data now.

**Fix:**
```python
def upsert_answer(..., config: dict = Depends(get_dssc_questionnaire_config)):
    valid = {
        q["id"]: q["category_id"]
        for cat in config["categories"] for q in cat["questions"]
    }
    if question_id not in valid or valid[question_id] != answer_in.category_id:
        raise HTTPException(status_code=422, detail="Unknown question_id/category_id")
```

### WR-03: `AnswerCreate.question_id` in the request body is accepted but silently ignored — no consistency check against the URL path parameter

**File:** `backend/app/api/v1/questionnaire.py:67-119`, `backend/app/schemas/questionnaire.py:6-9`

**Issue:** The route is `PUT .../answers/{question_id}` and also requires
`question_id` in the JSON body (`AnswerCreate.question_id`). The handler
never reads `answer_in.question_id` — it always uses the path parameter for
both the insert (`question_id=question_id`) and the subsequent re-fetch. If a
caller sends a body `question_id` that differs from the path, the mismatch is
silently swallowed rather than rejected or acknowledged, which is a
misleading API contract (`tests/api/test_questionnaire_answers.py` only ever
exercises the case where both match, so this is untested).

**Fix:** Either drop `question_id` from `AnswerCreate` (rely solely on the
path) or validate `answer_in.question_id == question_id` and 422 on mismatch.

### WR-04: `participant_type` is still unconditionally populated on new users/initiatives, contradicting the migration's stated "never populated going forward" intent (D-12)

**File:** `backend/app/schemas/auth.py:19-22`, `backend/app/api/v1/initiatives.py:27-31`, `backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py:26-27,137-139`

**Issue:** The migration's docstring and multiple inline comments across the
reviewed files (`admin.py`, `initiatives.py`, `reports.py`, `schemas/*`)
state that `participant_type` is nullable now and "kept for historical
reference, never populated/enforced on new registrations going forward."
In practice:
- `UserCreate.participant_type: Literal["DSI", "SP"] = "DSI"`
  (`schemas/auth.py:22`) is still a required-with-default field — every new
  registration still gets a concrete `"DSI"`/`"SP"` value; there is no way to
  register with `participant_type = None` through the public API.
- `create_initiative` (`initiatives.py:29`) copies
  `current_user.participant_type` onto every new `Initiative`, so new
  initiatives are populated too.

So for every user/initiative created *after* this migration ships, the field
is still fully populated exactly as before — only pre-existing legacy rows
end up with `NULL`. This is an inconsistency between the stated design intent
threaded through the comments and the actual write path; a future reader
relying on "new rows have NULL participant_type" (e.g. to distinguish legacy
vs. new records, similar to `schema_version`) will be wrong.

**Fix:** Either update the comments to reflect that `participant_type` is
still being populated (it's just no longer *enforced/required* for existing
records), or actually stop populating it going forward (drop the field from
`UserCreate`/stop copying it in `create_initiative`) to match the documented
intent.

### WR-05: Admin heatmap silently returns an all-zero matrix for the new schema with no indication the data is incomplete

**File:** `backend/app/api/v1/admin.py:336-427`

**Issue:** `counts` is keyed by integer `score` (1-5) from the new
`questionnaire_answer` table, but the lookup code reads it with string keys
(`code_counts.get("yes", 0)`, `"not_there_yet"`, `"not_applicable"`) inherited
from the legacy `mami_code`/`answer_value` shape — these never match, so
`yes_total`/`not_yet_total`/`na_total` are always `0` for any new-schema
data. Additionally, legacy (`v1_legacy`) initiatives' answers live only in
`questionnaire_answer_v1_archive`, which this query never joins, so their
data is excluded too. The docstring explicitly and correctly documents this
as an accepted interim gap ("do NOT read an all-zero heatmap as ... fully
compliant"), but the API response itself carries no machine-readable
indicator (e.g. a `degraded: true` field) — an admin consuming this via a
dashboard has no way to distinguish "genuinely zero submissions" from
"scoring pipeline is degraded."

**Fix:** Add an explicit `degraded: bool` (or similar) field to
`AdminHeatmapResponse` so frontend consumers can render a warning banner
instead of an indistinguishable empty heatmap.

### WR-06: Migration downgrade fabricates `participant_type = 'DSI'` for every NULL row, including ones intentionally left NULL post-upgrade — undocumented lossiness

**File:** `backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py:168-174`

**Issue:** The migration's module docstring documents downgrade lossiness
only for the answer-table reconstruction ("Downgrade lossiness:
reconstructing the old-shape questionnaire_answer ... is lossy ..."). It does
not mention that `downgrade()` also does:
```python
op.execute("UPDATE initiative SET participant_type = 'DSI' WHERE participant_type IS NULL")
op.execute('UPDATE "user" SET participant_type = \'DSI\' WHERE participant_type IS NULL')
```
This blanket-assigns `'DSI'` to *every* row with a NULL `participant_type` —
including brand-new users/initiatives created entirely after the v2 upgrade
that were deliberately never given a `participant_type` (per D-12). A
downgrade run against a live-for-a-while v2 database will fabricate incorrect
`DSI` classification for those rows with no record that this happened.

**Fix:** At minimum, document this specific lossiness in the module
docstring alongside the existing answer-table lossiness note, so an operator
running this downgrade in production understands the blast radius.

## Info

### IN-01: Dead legacy config-loader code paths left in place after the DSSC config supersedes them

**File:** `backend/app/core/deps.py:52-59`, `backend/app/main.py:30-33`

**Issue:** `get_questionnaire_config`/`get_questionnaire_configs` in
`deps.py` and the corresponding `app.state.questionnaire_config`/
`questionnaire_configs` loads in `main.py`'s `lifespan` are no longer used by
any route (confirmed via grep — only `get_dssc_questionnaire_config` is
referenced from `questionnaire.py`). They still read `questionnaire-v1.json`,
`dsi-questionnaire-v2.json`, and `sp-questionnaire-v2.json` from disk on
every app startup for no consumer.

**Fix:** Remove the unused dependency functions and the corresponding
`lifespan` loads, or explicitly mark them as intentionally-kept-for-a-later-
phase with a comment (the current comments already say "legacy"/"kept for
reference" but don't explain why the dead code itself is being kept alive in
`main.py`'s hot startup path).

### IN-02: Migration-verification test wraps a non-failing statement inside the same `pytest.raises` block as the one under test

**File:** `backend/tests/migrations/test_v1_archive_migration.py:203-225`

**Issue:** The CHECK-constraint assertion does:
```python
with pytest.raises(sa.exc.IntegrityError):
    conn.execute(...)  # INSERT INTO assessment — expected to succeed
    conn.execute(...)  # INSERT INTO questionnaire_answer with score=99 — expected to fail
```
Both statements share one `pytest.raises` block. This works today because
only the second statement raises, but it's a fragile pattern: if the first
statement (assessment insert) ever failed for an unrelated reason (e.g. a
future FK change), the test would still pass for the wrong reason, masking
a real regression in the setup rather than the constraint under test.

**Fix:** Split into two statements, asserting the first succeeds before
entering a `pytest.raises` block scoped to only the second.

### IN-03: Explicit `id` values are copied verbatim across archive/legacy tables without resetting destination sequences

**File:** `backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py:116-120,214-218`

**Issue:** Both the upgrade's archive-copy (`INSERT INTO
questionnaire_answer_v1_archive (id, ...) SELECT id, ... FROM
questionnaire_answer`) and the downgrade's restore (`INSERT INTO
questionnaire_answer (id, ...) SELECT id, ... FROM
questionnaire_answer_v1_archive`) explicitly carry over the source table's
`id` values into a freshly created table whose `id` column is an
auto-incrementing serial/identity column. Postgres allows explicit values
into a serial column, but the underlying sequence's `nextval()` is not
advanced past the max copied value. This is harmless under the current
design (per `D-04`, the archive is never written to by the app, and after a
downgrade the app's ORM model no longer matches the old-shape table anyway),
but is worth a one-line comment so a future maintainer doesn't assume the
destination table's sequence is in a normal state.

**Fix:** Optional — add `SELECT setval(pg_get_serial_sequence('<table>',
'id'), (SELECT MAX(id) FROM <table>))` after each copy, or a comment
explaining why it's unnecessary given current usage.

---

_Reviewed: 2026-07-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
