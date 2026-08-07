---
phase: 13-new-questionnaire-config-schema-data-model-migration
fixed_at: 2026-07-23T09:10:27Z
review_path: .planning/phases/13-new-questionnaire-config-schema-data-model-migration/13-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 13: Code Review Fix Report

**Fixed at:** 2026-07-23T09:10:27Z
**Source review:** .planning/phases/13-new-questionnaire-config-schema-data-model-migration/13-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (2 critical, 6 warning; fix_scope = critical_warning, Info findings excluded)
- Fixed: 8
- Skipped: 0

## Fixed Issues

### CR-01: Submitted initiatives can still have their questionnaire answers edited

**Files modified:** `backend/app/api/v1/initiatives.py`, `backend/app/api/v1/questionnaire.py`
**Commit:** 7597f42
**Applied fix:** `submit_initiative` now looks up the initiative's current draft
`Assessment` and flips it to `submitted` (stamping `submitted_at`) in addition to
setting `Initiative.status`. `upsert_answer` now rejects (403) any answer write
once `initiative.status == InitiativeStatus.submitted`, mirroring the
immutability guarantee `update_initiative` already enforces for initiative
metadata. Verified against `tests/api/test_questionnaire_answers.py` (all pass)
and `tests/api/test_reports.py`'s draft-status fixtures (unaffected — factory
initiatives default to draft).

### CR-02: Race condition in lazy Assessment creation can silently orphan answers

**Files modified:** `backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py`, `backend/app/api/v1/questionnaire.py`
**Commit:** 97df312
**Applied fix:** Added a partial unique index
(`uq_assessment_one_draft_per_initiative` on `assessment.initiative_id WHERE
status = 'draft'`) to this phase's own `i9d7e6f5a4b3` migration (not a new
migration — this schema has not shipped yet). `_get_or_create_draft_assessment`
now catches the `IntegrityError` a losing concurrent insert raises, rolls back,
and re-queries for the winning draft row instead of silently creating a second,
orphaned `Assessment`. Re-ran the full migration test suite
(`tests/migrations/test_v1_archive_migration.py`) — upgrade/downgrade round-trip
still passes (3/3).

### WR-01: Report/score endpoints return a fabricated "fully compliant" result with no degraded signal

**Files modified:** `backend/app/api/v1/reports.py`
**Commit:** 683eee1
**Applied fix:** Took the "banner" alternative from the review's fix suggestion
(rather than gating with 501/409) to avoid a breaking API-shape change on an
already-shipped-in-this-phase set of endpoints with existing 200-expecting
tests. Added `_inject_degraded_banner()`, which inserts a visible
"Provisional result" banner into the rendered HTML immediately after `<body>`,
wired into all four HTML/PDF-producing code paths (`generate_report`,
`download_report_pdf`, `mail_report`). Added a `"degraded": true` field to the
two JSON report-data endpoints' responses. `tests/api/test_reports.py`'s one
unmocked HTML-path test (`test_generate_report_returns_html_and_upserts_compliance_report`)
still passes; the 4 WeasyPrint-mocked tests fail for a pre-existing,
unrelated reason (see Quality Gate section below).

### WR-02: `upsert_answer` accepts arbitrary question_id/category_id with no config validation

**Files modified:** `backend/app/api/v1/questionnaire.py`
**Commit:** 300d72d (+ 7bbdf5f lint fixup)
**Applied fix:** Injected `get_dssc_questionnaire_config` into `upsert_answer`,
built a `{question_id: category_id}` lookup from the config, and now 422s on an
unknown `question_id` or a `category_id` that doesn't match the question's real
category. Verified against `tests/api/test_questionnaire_answers.py` and
`tests/api/test_questionnaire.py` (all pass — existing tests use real
`q-1-1`/`cat-1` pairs from `config/dssc-questionnaire.json`).

### WR-03: `AnswerCreate.question_id` silently ignored, no path/body consistency check

**Files modified:** `backend/app/api/v1/questionnaire.py`
**Commit:** 62b71d8
**Applied fix:** `upsert_answer` now 422s when `answer_in.question_id !=
question_id` (the path parameter), instead of silently using the path value and
ignoring a disagreeing body. Verified against
`tests/api/test_questionnaire_answers.py` (all pass — existing tests always
send matching path/body values).

### WR-04: `participant_type` comments contradict actual (still-populated) behavior

**Files modified:** `backend/app/models/initiative.py`, `backend/app/models/user.py`, `backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py`
**Commit:** 139969a
**Applied fix:** Chose the "update the comments" option from the review's two
alternatives rather than "stop populating it going forward" — removing
population now would be a functional behavior change breaking
`tests/api/test_auth.py`'s registration assertions (`body["participant_type"]
== "DSI"`), which is out of scope for a comment/doc-accuracy finding. Updated
the three comment locations (model field docstrings + migration docstring +
inline migration comment) to accurately state that D-12 only relaxed the NOT
NULL constraint; new rows are still populated exactly as before. Verified
`tests/migrations/test_v1_archive_migration.py` and `tests/api/test_auth.py`
(all pass).

### WR-05: Admin heatmap returns all-zero matrix with no machine-readable degraded signal

**Files modified:** `backend/app/api/v1/admin.py`
**Commit:** 235b180
**Applied fix:** Added `degraded: bool = True` to `AdminHeatmapResponse` (this
endpoint's counts lookup is keyed off the legacy `mami_code`/`answer_value`
shape and never matches new-schema data, nor joins the v1 legacy archive, so it
is unconditionally degraded today per its own docstring). Verified against
`tests/api/test_admin.py` (all 15 pass — the heatmap test only checks
presence of `matrix`/`topic_structure` keys, not an exhaustive response shape).

### WR-06: Migration downgrade's participant_type fabrication is undocumented

**Files modified:** `backend/alembic/versions/i9d7e6f5a4b3_questionnaire_v2_schema_migration.py`
**Commit:** d4f8df0
**Applied fix:** Documentation-only change — added a second "Downgrade
lossiness" paragraph to the module docstring explaining that `downgrade()`
blanket-assigns `participant_type = 'DSI'` to every NULL row (not just the
legacy rows this migration tagged), including brand-new post-upgrade
users/initiatives. Migration behavior itself is unchanged; re-verified via
`tests/migrations/test_v1_archive_migration.py` (3/3 pass).

## Skipped Issues

None — all 8 in-scope findings (CR-01, CR-02, WR-01 through WR-06) were fixed.
Info findings (IN-01, IN-02, IN-03) were excluded per `fix_scope:
critical_warning` and were not attempted.

## Quality Gate

Ran from `backend/` per the project's local quality gate:

```
uv run ruff check . && uv run ruff format --check . && uv run mypy app --ignore-missing-imports && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q
```

- `ruff check .` — all checks passed (one E501 introduced by the WR-02 fix was
  caught and fixed in commit 7bbdf5f).
- `ruff format --check .` — 60 files already formatted.
- `mypy app --ignore-missing-imports` — Success: no issues found in 33 source
  files.
- `pytest tests/ -n auto -m "not perf and not benchmark"` — 68 passed, 4
  failed. The 4 failures (`test_mail_report_generates_pdf_and_sends_email`,
  `test_mail_report_dev_mode_skips_resend_send`,
  `test_download_report_pdf_returns_pdf_content_type`,
  `test_download_report_pdf_no_answers_returns_422`, all in
  `tests/api/test_reports.py`) are the pre-existing, already-documented
  WeasyPrint `libgobject-2.0-0` native-library gap on this machine — confirmed
  by inspecting the failure output ("WeasyPrint could not import some
  external libraries") — not caused by any fix in this pass. Failure count
  (4) matches the previously-known threshold exactly.
- Migration test suite (`tests/migrations/test_v1_archive_migration.py`) was
  additionally re-run standalone after both the CR-02 and WR-06 migration
  edits, per the task's explicit instruction: 3/3 pass both times.

---

_Fixed: 2026-07-23T09:10:27Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
