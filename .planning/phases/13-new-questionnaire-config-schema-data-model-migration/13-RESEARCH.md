# Phase 13: New Questionnaire Config Schema & Data Model Migration - Research

**Researched:** 2026-07-22
**Domain:** SQLModel/Alembic schema evolution, data-preserving Postgres migration, config-driven questionnaire schema
**Confidence:** HIGH (codebase mechanics) / MEDIUM (SQLModel-Alembic enum gotcha, cross-checked externally) / LOW (none — no unverifiable claims required for this phase)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**V1.0 Data Preservation Strategy**
- **D-01:** Old MAMI answers (3-way enum: YES/NOT_THERE_YET/NOT_APPLICABLE) are migrated into a new **separate archive table** (`questionnaire_answer_v1_archive` or equivalent), not kept in the same table as new answers. This is a new pattern for this repo — the existing precedent (`f6a4b3c2d1e9_dsi_sp_questionnaire_foundation.py`) used same-table-plus-version-discriminator for a same-shape change (enum remap), but here the answer *shape* itself changes (3-way categorical → 1-5 numeric), which the user judged too different to overload into one table/column.
- **D-02:** `questionnaire_answer` (going forward) becomes purely the new 1-5-score shape. It does not need to carry legacy enum columns.
- **D-03:** `Initiative` gets its own version/schema tag (e.g. `schema_version` or `is_legacy` — exact naming left to planning) so "is this an old MAMI initiative" is a cheap filter without joining to answers. This also sets up cheap filtering once Phase 15 adds multiple `Assessment` rows per `Initiative`.
- **D-04:** MIGR-01's "queryable read-only" requirement is satisfied by **DB-level access only** in this phase — no new admin endpoint or UI to browse old MAMI submissions. If that's ever needed, it's a future ask, not part of Phase 13.
- **D-05 (compliance_report table):** Not explicitly discussed as its own question — the old `compliance_report` table is not named in MIGR-01, but per "never delete" as the operating principle throughout this discussion, it should be left as-is (no drop, no forced migration) unless it directly blocks the new schema. Flagged as an assumption for the researcher/planner rather than a fully settled decision — see Pitfall 4 for the research verdict.

**Assessment/Versioning Foundation**
- **D-06:** Phase 13 introduces the `Assessment` entity now, not deferred to Phase 15. New table: `initiative_id` FK, version/date field, `status` (draft/submitted, mirroring `Initiative`'s existing draft/active/submitted lifecycle). New `questionnaire_answer` rows key off `assessment_id`, not `initiative_id` directly. Rationale (user-confirmed): avoids a second migration/refactor of the answer table when Phase 15 lands.
- **D-07:** An `Assessment` row is created at the **first answer** (draft state), not only at submission. `status=draft` on first answer, flips to `status=submitted` on full completion.
- **Note for Phase 14/15/16 planners:** this Assessment-first schema is a load-bearing decision for those phases.

**New Config Schema Shape & Placeholder Depth**
- **D-08:** Placeholder content stubs **all 52 questions across all 6 categories** (not a smaller sample) — full structural skeleton at real size, using generic placeholder text (e.g. "Category 3 – Question 5").
- **D-09:** Answer-option labels use a **shared default 5-label set** (mapped 1-5) reused across all placeholder questions, while the schema itself supports per-question custom label overrides (required by QSTN-03).
- **D-10:** The new config lives in a **single JSON file** (e.g. `config/dssc-questionnaire.json`) containing all 6 categories and 52 questions nested inside — not split one-file-per-category.

**Evidence & Participant_type Removal Scope**
- **D-11:** Evidence data is **dropped outright**, not archived. `evidence_url` table, model, endpoints (`backend/app/api/v1/evidence.py`), and frontend (`frontend/src/lib/evidence.ts`, `EvidenceInput.tsx`) are deleted entirely with no archive step.
- **D-12:** `participant_type` columns on `Initiative` and `User` are **kept, made nullable, and simply stop being populated/enforced** going forward — not dropped from the schema.

### Claude's Discretion
- Exact naming of the new `schema_version`/`is_legacy`-style column on `Initiative` (D-03).
- Exact naming and shape of the archive table (`questionnaire_answer_v1_archive` vs. alternative naming) (D-01).
- Whether `compliance_report` needs any touch at all, beyond "don't delete it" (D-05) — flagged as an assumption for the researcher to confirm against the actual migration mechanics, not a fully closed decision. **Research verdict: no schema-level touch needed — see Pitfall 4.**
- Exact `Assessment.status` enum values and version/date field naming (D-06/D-07) — see Open Question 1 for a concrete recommendation.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope (schema + migration). No scope-creep topics came up during discuss-phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| QSTN-01 | User answers a 52-question assessment organized into 6 categories (dimensions) | Pattern 3 (single-file config loader) + Recommended Project Structure (`config/dssc-questionnaire.json`) define exactly how 52 questions/6 categories are represented and loaded; Validation Architecture maps this to a new `test_dssc_config.py` |
| QSTN-03 | Question and answer-option text (including per-question custom option labels) is fully config-driven — no code deploy required | Pattern 3 + D-09/D-10 constraints confirm the config shape supports per-question label overrides while defaulting to a shared 5-label set for placeholder content |
| QSTN-04 | Questionnaire is universal — no DSI/Service-Provider participant-type split | Pattern 3's `GET /questionnaire/config` example removes the participant_type branch entirely; Pitfall 5 covers the Pydantic/admin-schema fallout of making `participant_type` nullable rather than removing it |
| QSTN-05 | Real v2.0 content pending — placeholder sufficient now, no schema/engine change needed later | D-08/D-09 (locked decisions) plus Pattern 3's plain-JSON structure confirm swapping placeholder text for real content requires zero code changes |
| MIGR-01 | Existing v1.0 MAMI initiative/answer data preserved read-only | Pattern 2 (archive-table-split migration) is the concrete mechanism; Pitfall 1 (enum-type gotcha) and Pitfall 2 (untested migrations) are the two biggest risks to getting this right; Validation Architecture specifies the new `tests/migrations/test_v1_archive_migration.py` needed to actually verify it |
| MIGR-02 | Evidence/URL-per-question subsystem removed entirely | Pitfall 3 gives the exact file-by-file removal list (models, schemas, API, service call sites, frontend, tests) and the degenerate-but-safe behavior of downstream ZEN-based reporting once evidence is gone |
</phase_requirements>

## Summary

This phase is a backend-data-model phase with no new external dependencies — every finding below comes from direct inspection of this repo's own code plus targeted verification of two SQLModel/Alembic mechanics claims. The core technical risk is not "which library to use" (SQLModel/Alembic/Postgres are already fixed) but **getting the migration mechanics right against this repo's specific, somewhat inconsistent existing patterns**, and **not leaving `reports.py`/`admin.py`/`report_generator.py`/three test files in a state that fails CI** when `EvidenceURL` is deleted and `QuestionnaireAnswer.answer_value` changes shape.

Three load-bearing discoveries change how this phase must be planned:

1. **Migrations in this repo are never tested.** `backend/tests/conftest.py` builds test schema via `SQLModel.metadata.create_all(engine)`, bypassing Alembic entirely. `alembic upgrade head` only ever runs at Docker container startup (`backend/Dockerfile` CMD, `docker-compose.override.yml`) — never in CI, never in pytest. This phase's migration is the riskiest one to date (archive-table split + data copy, not just an ALTER) and currently has **zero automated verification path**. The plan must add one (Wave 0 gap).
2. **SQLModel's `(str, Enum)` fields map to a native PostgreSQL `ENUM` type by default** (confirmed via SQLModel GitHub discussion #717 + reproduced in this repo's own `conftest.py` comment about `answer_value` / "type already exists" errors), but **this repo's hand-written migrations for `answer_value` explicitly used `sa.String()`** to sidestep that — meaning the column's *real* production type (VARCHAR) already silently diverges from what bare `SQLModel.metadata.create_all()` would produce (native ENUM). The new archive table must deliberately repeat the `sa.String()` choice, not let autogenerate "fix" it into a native enum.
3. **`reports.py`/`admin.py`/`report_generator.py` all import `EvidenceURL` directly and read `answer.mami_code`** for scoring/heatmap/CSV logic tied to the old GoRules ZEN engine (which Phase 14 removes, not Phase 13). Deleting `EvidenceURL` breaks these modules' imports immediately; the new answer shape has no `mami_code` at all. Phase 13 must surgically strip evidence plumbing from these files (empty/removed `evidence_by_code`) so the app **imports and boots**, while explicitly leaving the ZEN-engine-based report/heatmap logic operating in a **degenerate-but-non-crashing** state for new-schema initiatives (verified: the ZEN JDM rules match on exact string literals like `"NOT_THERE_YET"`; a new integer `answer_value` matches no rule under `hitPolicy: "first"`, producing zero findings rather than an exception) — full replacement of that logic is explicitly Phase 14/16's job.

**Primary recommendation:** Treat this phase as three sequenced legs — (A) new config schema + loader, (B) new `Assessment`/`QuestionnaireAnswer`/archive-table models + one hand-written Alembic migration verified against a seeded testcontainer Postgres, (C) surgical evidence-removal + participant_type-nullability edits across models/schemas/API/tests, done in an order where each leg leaves `main.py` importable and the existing (soon-to-be-updated) test suite runnable.

## Project Constraints (from CLAUDE.md)

- **`docs-freshness` CI gate (`pr.yml`) hard-fails on any diff** between the committed `docs/api/openapi.json` and a freshly regenerated one (`uv run python scripts/export_openapi.py`) — since this phase changes multiple Pydantic schemas (`AnswerCreate`/`AnswerRead`, `InitiativeRead`, evidence schemas deleted entirely), **regenerating and committing `docs/api/openapi.json` is a required task in this phase's plan**, not optional cleanup.
- **Local quality gate before any PR** (from CLAUDE.md): `uv run ruff check --fix . ; uv run ruff format .` then `uv run ruff check . && uv run ruff format --check . && uv run mypy app --ignore-missing-imports && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` — must pass before this phase's PR into `staging`.
- **`-n auto` (xdist), never `-x`** — any new migration-verification test (Pitfall 2) must be safe to run under parallel workers; a testcontainer-per-session fixture (as `tests/conftest.py` already does) is compatible with this, but a fresh from-scratch `alembic upgrade head` test should use its own isolated container/session scope rather than sharing the existing session-scoped `postgres_container`/`engine` fixtures (which have already had `SQLModel.metadata.create_all()` run against them and are not a clean slate for testing an actual upgrade path).
- **`perf`/`benchmark` pytest markers** — the new migration test does not belong under either marker; it must run in the default `pytest -m "not perf and not benchmark"` gate so it's part of every PR's fast feedback, given its importance per Pitfall 2.
- **No `--no-verify`/skipped hooks, no force-push, no `-i` git flags** — standard repo-wide constraints, applicable to this phase's commits like any other.
- **SQLModel requires SQLAlchemy <2.1.0 — pinned explicitly** (STATE.md) — do not introduce any new dependency or upgrade that violates this pin as part of schema work.
- **Never delete compliance-relevant data** — the overarching philosophy behind D-01/D-04/D-05/D-11's asymmetric treatment (initiative/answer data preserved, evidence data dropped) — the planner should hold this same bar for any additional data-shape decisions that come up during implementation that CONTEXT.md didn't explicitly anticipate.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Questionnaire content (52 questions/6 categories/labels) | Config (JSON, filesystem) | API/Backend (loader + endpoint) | QSTN-03 requires zero-deploy content edits — must live outside code, loaded once at FastAPI lifespan startup like `mami_config.py` today |
| Assessment lifecycle (draft/submitted, versioning) | API/Backend (DB model + service) | Database/Storage | New `Assessment` table is the join point Phase 14 (scoring), 15 (autosave/retake), 16 (report contract) all key off — must be correct now |
| Answer storage (1-5 score) | Database/Storage | API/Backend (upsert endpoint) | `questionnaire_answer` keyed by `assessment_id`, not `initiative_id`, per D-06 |
| V1.0 legacy data preservation | Database/Storage (archive table) | — | DB-level only per D-04 — no new admin UI/endpoint this phase |
| Evidence subsystem | — (deleted) | — | MIGR-02 — no replacement tier; capability is removed, not relocated |
| participant_type (legacy tag) | Database/Storage (nullable column) | API/Backend (stop-writing, keep-reading) | D-12 — column stays for historical filtering, no new tier owns "assigning" it going forward |
| Config loading / caching | API/Backend (FastAPI `app.state` at lifespan startup) | — | Direct precedent: `mami_config.py` + `deps.py` pattern, reused for the new single-file loader |

## Package Legitimacy Audit

**Not applicable — this phase adds zero new external packages.** All work uses dependencies already pinned in `backend/pyproject.toml` (`sqlmodel==0.0.33`, `sqlalchemy>=2.0.14,<2.1.0`, `alembic>=1.13.0`, `psycopg2-binary`). No `npm install`/`pip install` of anything new is required for QSTN-01/03/04/05 or MIGR-01/02.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────┐
                    │ config/dssc-questionnaire.json │  (D-10: single file,
                    │  6 categories × 52 questions   │   52 Qs stubbed w/
                    │  5 labeled options -> 1-5 score│   placeholder text)
                    └──────────────┬──────────────┘
                                   │ read once at startup
                                   ▼
                    ┌─────────────────────────────┐
                    │ app.state.questionnaire_config │ (new loader replaces
                    │  (FastAPI lifespan, cached)     │  load_questionnaire_configs())
                    └──────────────┬──────────────┘
                                   │ Depends(get_questionnaire_config)
                                   ▼
   Client ──GET /questionnaire/config──▶ questionnaire.py (no participant_type branch)
                                   │
                                   │ PUT /questionnaire/initiatives/{id}/answers/{qid}
                                   ▼
                    ┌─────────────────────────────┐
                    │ Assessment (draft on 1st answer)│──FK──▶ Initiative (+schema_version)
                    │  questionnaire_answer(1-5)      │        (existing v1 rows tagged legacy)
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    │  questionnaire_answer_v1_archive │  (D-01: separate table,
                    │  (read-only, DB-level access)    │   old 3-way enum shape,
                    └───────────────────────────────┘   populated once by migration)

  Migration path (one-time, at deploy):
  old questionnaire_answer rows ──COPY──▶ questionnaire_answer_v1_archive
  old questionnaire_answer table ──TRUNCATE/redefine──▶ new 1-5-shaped questionnaire_answer
  initiative ──ADD COLUMN schema_version/is_legacy──▶ tag existing rows 'legacy'
  evidence_url table ──DROP──▶ (gone, no archive, per D-11)
```

### Recommended Project Structure (files touched, not new folders)
```
backend/
├── config/dssc-questionnaire.json          # NEW — single-file universal config (D-10)
├── app/models/
│   ├── initiative.py                       # + schema_version/is_legacy col, participant_type -> nullable
│   ├── questionnaire.py                    # QuestionnaireAnswer reshaped to 1-5 score, keyed by assessment_id
│   ├── assessment.py                       # NEW — Assessment entity (D-06/D-07)
│   ├── questionnaire_answer_archive.py     # NEW — v1 archive table model (D-01)
│   ├── evidence.py                         # DELETED (D-11)
│   └── user.py                             # participant_type -> nullable
├── app/schemas/
│   ├── questionnaire.py                    # AnswerCreate/Read reshaped
│   ├── evidence.py                         # DELETED
│   └── initiative.py                       # InitiativeRead.participant_type -> str | None
├── app/services/mami_config.py             # replaced/extended with single-config loader
├── app/core/deps.py                        # get_questionnaire_config(s) collapsed to one
├── app/api/v1/
│   ├── questionnaire.py                    # drop participant_type selection logic
│   ├── evidence.py                         # DELETED, router removed from main.py
│   ├── admin.py                            # drop evidence cascade-delete + CSV evidence column
│   └── reports.py                          # strip EvidenceURL usage (see Pitfall 3)
├── app/services/report_generator.py        # strip evidence_by_code plumbing
├── app/db/base.py                          # remove EvidenceURL import, add Assessment + archive model imports
└── alembic/versions/
    └── <new>_questionnaire_v2_schema_migration.py   # the phase's core migration

backend/tests/
├── factories.py                            # drop make_evidence/EvidenceURL import
├── api/test_admin.py                       # drop evidence-cascade assertions
├── api/test_reports.py                     # drop/adjust evidence-dependent assertions
├── services/test_report_generator.py       # drop evidence_by_code fixture usage
└── (new) test migration verification       # Wave 0 gap — see Validation Architecture

frontend/src/
├── lib/evidence.ts                         # DELETED (D-11, orphaned already — no wiring to unpick)
└── components/questionnaire/EvidenceInput.tsx  # DELETED (confirmed: not imported anywhere else)
```

### Pattern 1: Assessment-first answer keying (D-06)
**What:** `questionnaire_answer` rows get a new `assessment_id` FK instead of (or in addition to, during transition) `initiative_id`. An `Assessment` row is created eagerly at the first answer write (`status="draft"`), not deferred to submission.
**When to use:** Every new-schema answer write, from this phase forward — this is the schema Phase 15's autosave/retake and Phase 14's per-assessment scoring both build on directly.
**Example (schema shape, not existing code — new this phase):**
```python
# Source: pattern derived from existing Initiative.status precedent (app/models/initiative.py)
class AssessmentStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"

class Assessment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    initiative_id: int = Field(foreign_key="initiative.id", index=True)
    version: int = Field(default=1)          # or a date field — exact naming is Claude's discretion (D-07)
    status: AssessmentStatus = Field(default=AssessmentStatus.draft)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: datetime | None = None
```
The upsert-on-first-answer flow (`PUT /questionnaire/initiatives/{id}/answers/{qid}`) must be extended: look up (or create) the current draft `Assessment` for the initiative before upserting the answer row, mirroring the existing `pg_insert(...).on_conflict_do_update(...)` pattern already used in `questionnaire.py:60-81` and `reports.py`'s `ComplianceReport` upsert.

### Pattern 2: Archive-table-split migration (D-01) — new pattern for this repo
**What:** Unlike the one existing precedent (`f6a4b3c2d1e9_dsi_sp_questionnaire_foundation.py`, which remapped enum *values* in place within the same column/table because the shape didn't change), this migration must (a) create a new `questionnaire_answer_v1_archive` table with the OLD 3-way-enum shape, (b) `INSERT INTO ... SELECT` copy every existing `questionnaire_answer` row into it, (c) then either `TRUNCATE`+redefine `questionnaire_answer` columns or `DROP`+`CREATE` it fresh with the new 1-5-score shape.
**When to use:** This exact migration, once, chained from `h8c6d5e4f3a2` (current head).
**Example:**
```python
# Source: pattern synthesized from this repo's own e5f3a2b4c6d7 (create_table) +
# f6a4b3c2d1e9 (data-preserving op.execute UPDATE) conventions
def upgrade() -> None:
    # 1. Create archive table with the OLD shape (mirrors current questionnaire_answer columns)
    op.create_table(
        "questionnaire_answer_v1_archive",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiative_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(), nullable=False),
        sa.Column("mami_code", sa.String(), nullable=False),
        sa.Column("questionnaire_version", sa.String(), nullable=False),
        sa.Column("answer_value", sa.String(), nullable=False),  # sa.String — NOT sa.Enum, see Pitfall 1
        sa.Column("followup_selections", JSONB, nullable=True),
        sa.Column("followup_other", sa.Text(), nullable=True),
        sa.Column("rationale", sa.String(), nullable=True),
        sa.Column("answered_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        # NOTE: deliberately NO FK to initiative.id here if initiative rows could ever be
        # hard-deleted by admin.py's existing _delete_initiative_children — decide per D-04
        # whether archive rows survive an admin initiative-delete (recommend: yes, they should
        # NOT cascade-delete, since MIGR-01 says preserve; add archive cleanup to
        # _delete_initiative_children only if the team decides old data should die with the initiative)
    )
    # 2. Copy existing data verbatim
    op.execute("""
        INSERT INTO questionnaire_answer_v1_archive
            (id, initiative_id, question_id, mami_code, questionnaire_version,
             answer_value, followup_selections, followup_other, rationale,
             answered_at, updated_at)
        SELECT id, initiative_id, question_id, mami_code, questionnaire_version,
               answer_value, followup_selections, followup_other, rationale,
               answered_at, updated_at
        FROM questionnaire_answer
    """)
    # 3. Tag initiatives that have archived answers as legacy BEFORE dropping the old table
    op.add_column("initiative", sa.Column("schema_version", sa.String(), nullable=False,
                                            server_default="v2"))
    op.execute("""
        UPDATE initiative SET schema_version = 'v1_legacy'
        WHERE id IN (SELECT DISTINCT initiative_id FROM questionnaire_answer_v1_archive)
    """)
    # 4. Drop and recreate questionnaire_answer with the new shape (assessment_id FK, integer score)
    op.drop_table("questionnaire_answer")
    op.create_table(
        "questionnaire_answer",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(), nullable=False),   # new-config question identifier
        sa.Column("category_id", sa.String(), nullable=False),   # new-config category identifier
        sa.Column("score", sa.Integer(), nullable=False),         # 1-5
        sa.Column("answered_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessment.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id", "question_id", name="uq_answer_per_question_v2"),
    )

def downgrade() -> None:
    # Reconstruct old questionnaire_answer from the archive (lossy for any NEW-shape answers
    # written after upgrade — document this limitation explicitly in the migration docstring,
    # same as f6a4b3c2d1e9's downgrade already accepts lossiness)
    ...
```
**Why `op.drop_table` + `op.create_table` rather than a chain of `op.alter_column`:** the column set changes entirely (`mami_code`→gone, `initiative_id`→`assessment_id`, enum string→integer) — this is a full reshape, not a type tweak. `render_as_batch=True` is already set in `alembic/env.py` (needed historically for SQLite batch mode; harmless no-op on Postgres) so this doesn't change the approach.

### Pattern 3: Single-file config loader (D-10) replacing DSI/SP dual-load
**What:** Replace `load_questionnaire_configs()` (returns `{"DSI": {...}, "SP": {...}}`) with a single `load_questionnaire_config()` returning one dict; replace `get_questionnaire_configs` dependency with a single `get_questionnaire_config`.
**When to use:** `main.py` lifespan, `deps.py`, `questionnaire.py` endpoint — all three must change together or the app won't boot.
**Example:**
```python
# Source: direct extension of existing app/services/mami_config.py pattern (Path(__file__).parent chain)
def load_dssc_questionnaire_config() -> dict:
    """Load config/dssc-questionnaire.json. Single universal config, no participant_type key."""
    path = CONFIG_DIR / "dssc-questionnaire.json"
    return json.loads(path.read_text())
```
```python
# app/core/deps.py — replaces get_questionnaire_config/get_questionnaire_configs
def get_dssc_questionnaire_config(request: Request) -> dict:
    return request.app.state.dssc_questionnaire_config
```
```python
# app/api/v1/questionnaire.py — GET /questionnaire/config no longer needs an Initiative lookup
# at all (no participant_type to resolve), which also removes the current 404-if-no-initiative
# behavior — confirm with planner whether that 404 was load-bearing UX or accidental coupling.
@router.get("/questionnaire/config")
def get_questionnaire_config_endpoint(
    config: dict = Depends(get_dssc_questionnaire_config),
):
    return config
```

### Anti-Patterns to Avoid
- **Relying on `alembic revision --autogenerate` for this migration:** `alembic/env.py` does not set `compare_type=True` in either `run_migrations_offline`/`run_migrations_online` [VERIFIED: read `backend/alembic/env.py`] — autogenerate here will not reliably detect the column-type reshape (string enum → integer) even if it detects the table exists. Every migration in this repo's history that does a real data transformation (`f6a4b3c2d1e9`, `h8c6d5e4f3a2`) was hand-written with explicit `op.execute()` calls, not raw autogenerate output. Follow that precedent — hand-write this migration.
- **Letting the archive table's `answer_value` column default to SQLAlchemy's native `Enum` type:** see Pitfall 1 below — always pass an explicit `sa.String()` (or `sa.Column(String)` on the model side, not a bare Python `Enum`) to keep migration-created schema and any `SQLModel.metadata.create_all()`-based test schema consistent.
- **Cascading the archive-table delete into `admin.py`'s `_delete_initiative_children`:** MIGR-01 requires preservation; if an admin later hard-deletes a legacy initiative via the existing `/admin/initiatives/{id}` endpoint, decide explicitly whether `questionnaire_answer_v1_archive` rows for that initiative should survive (recommended: yes — the whole point of the archive is durability independent of the live initiative's lifecycle; do not add a cascade-delete for the archive table unless there's a compliance reason to allow deletion).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Config-driven questionnaire content | A custom DSL/templating layer for question text | Plain nested JSON (as today) loaded once at FastAPI lifespan startup | QSTN-03 only requires "no code deploy to edit content" — a flat JSON file already satisfies this; anything more elaborate is scope creep for a schema phase |
| Data-preserving schema reshape | Application-level "soft migration" (e.g. a background job that lazily migrates rows on read) | A single up-front Alembic migration run at deploy time (existing `alembic upgrade head` on container start) | This repo already runs `alembic upgrade head` at every container boot (`Dockerfile` CMD) — a lazy/background migration would be a new, riskier pattern with no precedent and no monitoring in place |
| Legacy-vs-new initiative filtering | A join against `questionnaire_answer_v1_archive` to infer "is this legacy" | The new `Initiative.schema_version`/`is_legacy` column (D-03) | Explicitly called out in CONTEXT.md as the reason for D-03 — avoids a join for a cheap, frequently-needed filter |
| ORM enum handling across Postgres/SQLite-shaped test doubles | Hand-rolled `CHECK` constraints or triggers to keep string values in sync | Plain `sa.String()` column + Python-side `str, Enum` validation (existing pattern for every enum in this repo) | Matches CLAUDE.md's own documented reasoning for the `UP042` ruff-ignore (deliberately not migrating to native `StrEnum`/native Postgres enum "since it touches SQLAlchemy column serialization") |

**Key insight:** Every "don't hand-roll" item above resolves to "extend the existing, already-battle-tested pattern in this exact repo" rather than reaching for a new library or architecture — this phase's entire job is disciplined reshaping of what's already there, not introducing new tooling.

## Runtime State Inventory

> Rename/refactor/migration phase — all 5 categories addressed explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `questionnaire_answer` table: all pre-migration rows (3-way enum `YES`/`NOT_THERE_YET`/`NOT_APPLICABLE`, keyed by `initiative_id`+`question_id`, carrying `mami_code`). `evidence_url` table: all rows (URL evidence per question). `compliance_report` table: one row per initiative (`html_content`, counts) — **not named in MIGR-01**, left untouched per D-05 (see Pitfall 4 for why this is safe but not risk-free). | `questionnaire_answer` rows: **data migration** (copy to archive table, D-01). `evidence_url` rows: **no migration** — dropped outright per D-11 (explicit user decision, not an oversight). `compliance_report` rows: **no migration** — left as-is; will contain stale HTML referencing the old MAMI framework/evidence until Phase 16 rebuilds report generation, which is expected and out of scope here. |
| Live service config | None found. This app has no external SaaS config (no n8n, no Datadog, no Tailscale) that embeds questionnaire/evidence identifiers — verified by grepping for the removed model names outside `backend/` and `frontend/src`; only `.planning/` docs and this research reference them. | None. |
| OS-registered state | None found. No pm2/systemd/launchd/Windows Task Scheduler registrations exist in this repo (Railway/Docker-only deployment per CLAUDE.md branch model) — verified: no `.github/workflows`, `Dockerfile`, or `docker-compose*.yml` reference task-scheduler-style registrations tied to evidence/questionnaire naming. | None. |
| Secrets/env vars | None found. No `.env`/CI secret name embeds "evidence", "mami_code", "participant_type", or "questionnaire_answer" — confirmed via `.github/workflows/*.yml` env/secrets blocks (`STAGING_URL`, `RESEND_API_KEY`, `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD` — none reference the renamed/removed structures). | None. |
| Build artifacts / installed packages | `zen-engine==0.51.0` and `resend`/`weasyprint` dependencies remain pinned in `backend/pyproject.toml` — these are **not** removed by this phase (ZEN engine removal is explicitly SCOR-03/Phase 14's job). No egg-info/compiled-binary artifacts reference the evidence subsystem by name (it's a plain SQLModel table + FastAPI router, no codegen). `docs/api/openapi.json` **will drift** once `evidence`/`questionnaire`/`initiative` schemas change — the `docs-freshness` CI job (`pr.yml`) regenerates this file via `scripts/export_openapi.py` and hard-fails on any `git diff`. | Regenerate `docs/api/openapi.json` via `uv run python scripts/export_openapi.py` and commit it as part of this phase's changes, or `docs-freshness` will fail on the PR. This is a required task, not optional cleanup. |

## Common Pitfalls

### Pitfall 1: SQLModel `(str, Enum)` fields silently produce a native Postgres ENUM type unless explicitly forced to `sa.String()`
**What goes wrong:** If the new archive-table model (or any new model this phase) declares `answer_value: AnswerValue` (a `str, Enum` field) without an explicit `sa_column=Column(String)`, SQLModel/SQLAlchemy will map it to a native Postgres `ENUM` type by default in *any path that uses `SQLModel.metadata.create_all()`* — which is exactly how this repo's own test suite builds schema (`backend/tests/conftest.py`, `engine` fixture). Meanwhile, this repo's actual Alembic migrations for the *existing* `answer_value` column use plain `sa.String()`. If the new archive migration doesn't repeat that explicit choice, tests (native ENUM) and production (VARCHAR, if hand-written differently) will diverge, and a later `alembic revision --autogenerate` run could propose an unwanted `ALTER TYPE` diff.
**Why it happens:** SQLModel changed this behavior at some point — `(str, Enum)` fields are "no longer (automatically) treated as strings in SQL" [CITED: github.com/fastapi/sqlmodel/discussions/717] — and this repo's own `conftest.py` comment independently documents hitting this exact issue ("Postgres native ENUM types (answervalue) raise 'type already exists' on repeated drop/recreate").
**How to avoid:** For the archive table's `answer_value` column (and any other enum-shaped column, old or new), either (a) write the migration's `op.create_table()` with an explicit `sa.String()` (matching existing precedent in `b3f7c9a1d2e8`), and (b) on the model side, use `sa_column=Column(String)` rather than a bare enum type annotation if the model needs to declare `answer_value: AnswerValue` for typing purposes.
**Warning signs:** A test failure like `psycopg2.errors.DuplicateObject: type "answervalue" already exists` when running the test suite a second time against a long-lived container, or an autogenerate diff proposing `sa.Enum(...)` for a column that's `sa.String()` in production.

### Pitfall 2: Migrations in this repo have zero automated verification today
**What goes wrong:** `backend/tests/conftest.py` builds schema via `SQLModel.metadata.create_all(engine)` — this bypasses Alembic entirely and would succeed even if the actual migration file (`alembic/versions/<new>.py`) has a bug that would fail against a real upgrade path. `alembic upgrade head` only executes at Docker container startup (`backend/Dockerfile` line 46, `docker-compose.override.yml` line 6) — there is no CI job and no pytest fixture that runs it. This phase's migration is a full reshape (drop+recreate a table, copy data into a new archive table) — categorically riskier than any prior migration in this repo (all of which were `ALTER COLUMN`/`ADD COLUMN`, never `DROP TABLE`).
**Why it happens:** The test infra added in Phase 12 (testcontainers-python) was built to characterize existing *application behavior* (auth/admin/reports), not to verify *migration scripts* — verifying migrations wasn't in scope for that phase.
**How to avoid:** Add a Wave 0 test that: (1) spins up a fresh Postgres testcontainer, (2) runs `alembic upgrade head` programmatically (via `alembic.command.upgrade(config, "head")`) against it starting from an empty DB, and separately (3) a second test that seeds a Postgres testcontainer with pre-migration-shaped data (via a raw-SQL fixture matching the OLD `questionnaire_answer` schema, since the model will already be redefined by the time this test runs) and asserts row counts/content in `questionnaire_answer_v1_archive` match after upgrade. This is new test infrastructure this phase must add, not reuse.
**Warning signs:** A migration that "works" in a fresh empty DB (matches the current model's `create_all()` shape) but fails against a Postgres instance carrying real Phase-1-through-12 production data — this is precisely the failure mode automated verification is missing today.

### Pitfall 3: Deleting `EvidenceURL` breaks four modules' imports and several tests immediately, and the old ZEN-engine report/heatmap logic has no valid input shape for new-schema answers
**What goes wrong:** `backend/app/api/v1/admin.py`, `backend/app/api/v1/evidence.py`, `backend/app/api/v1/reports.py`, `backend/app/services/report_generator.py` [VERIFIED: read all four files], plus `backend/tests/factories.py` and `backend/tests/api/test_admin.py` [VERIFIED: grep confirmed both import `EvidenceURL`/`make_evidence`], all reference `EvidenceURL` directly. Deleting the model per D-11 without touching these breaks `import app.main` at collection time — every pytest test fails, not just evidence-specific ones. Separately, `reports.py`/`admin.py` build `answers_for_scoring` dicts keyed on `a.mami_code` for the ZEN engine (`scoring_engine.score_all_answers`) — new-schema answers have no `mami_code` at all (the new 52-question config uses new question/category IDs), so any code path that still calls these endpoints against a new-schema `Assessment` would either KeyError or (if using `.get()` defensively) silently score against wildcard "unknown code" metadata.
**Why it happens:** These four modules are Phase 14 (scoring)/Phase 16 (report contract)'s primary *rebuild* targets — CONTEXT.md is explicit that Phase 13 must not implement their replacement logic, only avoid leaving them broken in the interim.
**How to avoid:** Strip (not rebuild) evidence usage: remove `EvidenceURL` imports, the `evidence_by_code` parameter and its query/loop wherever it appears in `reports.py` (4 near-identical call sites) and `report_generator.py` (`generate_html_report`, `generate_report_data`, `_build_findings_detail` all take `evidence_by_code` — either drop the parameter and its usages, or pass `{}` inline at each call site and leave the parameter as dead/optional for now, whichever is a smaller diff for the planner to choose). Remove `evidence_url` cascade-delete lines from `admin.py::_delete_initiative_children` and the CSV export's evidence-adjacent comment. Delete `app/api/v1/evidence.py` and its router registration in `main.py`, and `app/schemas/evidence.py`. Update `factories.py` (drop `make_evidence`/`EvidenceURL` import) and `tests/api/test_admin.py` (drop the two `make_evidence(...)` call sites and their assertions). **Do not** attempt to make `score_all_answers`/ZEN-based reports produce *correct* output for new-schema `Assessment` rows — verified via `config/scoring/mami-scoring.json`'s JDM rules (string-literal match on `col_answer: "\"NOT_THERE_YET\""`, `hitPolicy: "first"`, no visible catch-all rule) that an integer `answer_value` simply fails to match any rule, yielding `outcome.get("status")` as `None` — excluded from `findings` — i.e., these endpoints degrade to "zero findings" for new-schema initiatives rather than crashing. This is acceptable, temporary, and explicitly Phase 14/16's problem to fix, not Phase 13's.
**Warning signs:** `ImportError: cannot import name 'EvidenceURL'` at pytest collection; `docs-freshness` CI diff showing `/initiatives/{id}/evidence` routes still present after evidence removal claims to be complete; a report generated against a new-schema `Assessment` silently claiming "0 findings / fully compliant" — acceptable for now, but must be documented as a known interim limitation, not mistaken for a real "all good" signal by whoever reviews Phase 13.

### Pitfall 4: `compliance_report` (D-05) references `initiative_id` only — it will silently continue to "work" (in the sense of not erroring) but produce meaningless upserts for new-schema initiatives unless the report endpoints are updated per Pitfall 3
**What goes wrong:** `ComplianceReport.initiative_id` [VERIFIED: `backend/app/models/report.py`] has no dependency on `QuestionnaireAnswer`'s shape or on `EvidenceURL` at the schema level — it's just `html_content` + counts. So D-05's "leave it untouched, no drop, no forced migration" is schema-safe: the table itself doesn't reference either changed structure via FK, and won't block the migration. The risk is entirely at the *application* layer (Pitfall 3), not the schema layer.
**Why it happens:** `compliance_report` was designed as a denormalized cache of rendered HTML — it has no structural coupling to the tables this phase changes, which is exactly why the user's instinct ("don't touch it") is correct at the DB level.
**How to avoid:** Confirm (as this research does) that no `ALTER TABLE compliance_report` or FK change is needed in the migration. The only work needed is the application-layer fix in Pitfall 3 (evidence stripping) so that new calls to `POST /initiatives/{id}/report` don't 500 due to the now-deleted `EvidenceURL` import.
**Warning signs:** None expected at the schema level — this is a confirmation, not a risk, once Pitfall 3 is handled.

### Pitfall 5: `participant_type` nullability (D-12) has more call sites than the two models — Pydantic schemas and raw-SQL admin queries also assume it's always present
**What goes wrong:** `backend/app/schemas/initiative.py::InitiativeRead.participant_type: str` [VERIFIED, read] is currently a required `str`, not `str | None` — leaving it as-is after the model column becomes nullable will produce a Pydantic validation error (`none is not an allowed value`) the first time a new (participant_type-less) initiative is serialized through this response model. Similarly, `admin.py`'s raw-SQL queries (`list_users`, `list_initiatives`, `get_admin_heatmap`, CSV export) select `participant_type` directly into `AdminUserRow.participant_type: str`/`AdminInitiativeRow.participant_type: str` [VERIFIED, both non-Optional in `admin.py`] — these will hit the same issue for new users/initiatives.
**Why it happens:** D-12 was scoped at the model/migration level in CONTEXT.md; the Pydantic response schemas and admin raw-SQL row models are a downstream consequence not explicitly enumerated there.
**How to avoid:** When making `Initiative.participant_type`/`User.participant_type` nullable, also update `InitiativeRead.participant_type`, `AdminUserRow.participant_type`, and `AdminInitiativeRow.participant_type` to `str | None` in the same pass. `get_admin_heatmap`'s `LOWER(i.participant_type) = :ptype` filter (existing Phase 01-02 decision, per STATE.md) already handles `NULL` safely (a `NULL` never matches a non-null `:ptype` filter, and the `type=None` no-filter case is unaffected) — no change needed there beyond the response model typing.
**Warning signs:** `pydantic_core.ValidationError` on `GET /admin/users` or `GET /admin/initiatives` the first time a new-schema user/initiative exists in the DB (participant_type NULL).

## Code Examples

### Existing upsert pattern to extend for Assessment-first writes
```python
# Source: backend/app/api/v1/questionnaire.py:59-81 (existing, verified) — this exact
# on_conflict_do_update pattern is the one to extend with an Assessment lookup/create step
stmt = pg_insert(QuestionnaireAnswer).values(...)
stmt = stmt.on_conflict_do_update(
    constraint="uq_answer_per_question",
    set_={...},
)
session.exec(stmt)
session.commit()
```

### Existing FastAPI lifespan config-caching pattern to replicate for the new single config
```python
# Source: backend/app/main.py:26-38 (existing, verified)
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mami_config = load_mami_config()
    app.state.questionnaire_config = load_questionnaire_config()      # legacy, kept until Phase 14 removes MAMI framework entirely
    app.state.questionnaire_configs = load_questionnaire_configs()    # REPLACE with single dssc_questionnaire_config load
    ...
    yield
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| DSI/SP dual questionnaire config (`dsi-questionnaire-v2.json`/`sp-questionnaire-v2.json`), selected by `Initiative.participant_type` | Single universal `config/dssc-questionnaire.json`, no participant_type branching | This phase (Phase 13) | `GET /questionnaire/config` no longer needs an `Initiative` lookup at all — simplifies the endpoint but changes its current "404 if no initiative yet" behavior; flag for planner to decide if that 404 was intentional gating or incidental |
| `questionnaire_answer.answer_value`: 3-way enum (`YES`/`NOT_THERE_YET`/`NOT_APPLICABLE`), keyed by `initiative_id` | 1-5 integer score, keyed by `assessment_id` (new `Assessment` FK) | This phase (Phase 13) | Old rows preserved in `questionnaire_answer_v1_archive`; scoring math itself (SCOR-01..04) is explicitly Phase 14, not this phase |
| Evidence-per-question (`evidence_url` table + endpoints + `EvidenceInput.tsx`) | Removed entirely, no replacement | This phase (Phase 13) | MIGR-02 — no schema home for this concept in the new model |

**Deprecated/outdated:**
- `ParticipantType` enum (`app/models/initiative.py`) — kept for historical/legacy rows only (D-12), never assigned to new records going forward.
- `load_questionnaire_configs()` / `get_questionnaire_configs` dependency — superseded by a single-config loader this phase.
- GoRules ZEN Engine / `config/mami-framework.json` / `config/scoring/mami-scoring.json` — **not** removed this phase (that's SCOR-03/Phase 14); Phase 13 must keep these alive and importable, only adjusting the evidence-plumbing around their call sites per Pitfall 3.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `GET /questionnaire/config`'s current "404 if no Initiative exists yet" behavior is incidental coupling (a side effect of needing to resolve `participant_type`) rather than intentional UX gating, and can be safely dropped once the config becomes universal | Pattern 3 | If it was intentional (e.g., preventing questionnaire access before initiative registration), dropping the check changes user-facing behavior outside this phase's stated "no user-facing surface" boundary — low risk (easy to re-add the check as a plain initiative-exists guard without any participant_type lookup) |
| A2 | Archive-table rows for a hard-deleted (via `admin.py`) legacy initiative should NOT cascade-delete — i.e., `questionnaire_answer_v1_archive` should survive even if its parent `initiative` row is deleted | Pattern 2, Anti-Patterns | If the team actually wants "delete initiative = delete everything including archived history," the migration needs an FK+cascade (or the admin delete path needs an explicit archive-delete step) — currently no FK is proposed at all for the archive table, so nothing cascades by default; safest direction if wrong is adding a cascade later, not the reverse |
| A3 | It's acceptable for `/report`, `/report/data`, `/report/pdf`, `/report/mail`, `/admin/heatmap` to silently degrade to "zero findings" for new-schema (post-migration) initiatives during the Phase 13→14 gap, rather than being explicitly blocked/disabled for such initiatives | Pitfall 3 | If a demo or stakeholder hits these endpoints against a real new-schema initiative before Phase 14 ships, they'll see a misleadingly "fully compliant" report instead of an error — consider recommending the planner add a lightweight `if initiative.schema_version != "v1_legacy": raise HTTPException(422, "Reporting not yet available for new-schema assessments")` guard as cheap insurance, discretionary but not currently required by any locked decision |

**If empty:** N/A — see table above; all three assumptions are low/medium risk and each has a stated safe-direction-if-wrong.

## Open Questions

1. **Exact naming for `Assessment.status` enum values, version/date field, and `Initiative.schema_version`/`is_legacy` column**
   - What we know: CONTEXT.md D-03/D-06/D-07 explicitly leave these as "Claude's Discretion."
   - What's unclear: Whether "version" should be an integer counter or a date/timestamp (both support Phase 15's HIST-01/02 "dated assessment version" requirement, but a bare integer alone wouldn't satisfy "dated" without also keeping `created_at`).
   - Recommendation: Use `version: int` (sequential, human-readable, e.g. "Assessment #3") *plus* the existing `created_at`/`submitted_at` timestamp fields already planned — satisfies both "version" and "dated" without a redundant field. Name the initiative column `schema_version: str` (`"v1_legacy"` / `"v2"`) rather than a boolean `is_legacy`, since a string leaves room for a future v3 without another migration.

2. **Whether `questionnaire_answer_v1_archive` needs its own Pydantic schema for the "DB-level queryable" requirement (MIGR-01/D-04)**
   - What we know: D-04 explicitly says DB-level access only, no admin endpoint/UI this phase.
   - What's unclear: Whether "queryable" implies the planner should still define a lightweight read-only SQLModel class (for direct `session.exec(select(...))` debugging/future use) or truly nothing beyond the raw table.
   - Recommendation: Define the archive table as a real (if unused-by-any-endpoint) SQLModel `table=True` class in `app/models/` — costs nothing, keeps it importable via `db/base.py` for Alembic autogenerate consistency in future phases, and satisfies "queryable" more robustly than a table Alembic created with no corresponding ORM class.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL (via testcontainers) | Migration verification (Pitfall 2), existing test suite | ✓ (per Phase 12 setup — requires local Docker-API-compatible daemon per `tests/conftest.py` docstring) | postgres:16-alpine (pinned, matches `docker-compose.yml`) | None — testcontainers-postgres is a hard dependency for this repo's test strategy per Phase 12's D-01, no SQLite fallback exists or should be introduced |
| Alembic | The core migration this phase delivers | ✓ | `>=1.13.0` (pinned in `backend/pyproject.toml`) | — |
| SQLModel / SQLAlchemy | Model reshaping | ✓ | `sqlmodel==0.0.33`, `sqlalchemy>=2.0.14,<2.1.0` (pinned) | — |
| zen-engine (ZEN) | Kept alive, not removed this phase | ✓ | `zen-engine==0.51.0` (pinned) — untouched this phase | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1+, pytest-xdist (`-n auto`), testcontainers[postgres] 4.14.2+ |
| Config file | `backend/pyproject.toml` (`[tool.pytest]`-style config not separately shown but markers `perf`/`benchmark` registered there); `backend/tests/conftest.py` for fixtures |
| Quick run command | `uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` (per CLAUDE.md local quality gate) |
| Full suite command | `uv run pytest tests/ -n auto -m "not perf"` (staging.yml — includes benchmark) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QSTN-01 | Config exposes 52 questions across 6 categories | unit | `pytest tests/services/test_dssc_config.py -x` | ❌ Wave 0 |
| QSTN-03 | Config-driven labels — editing JSON changes served content, no code path branches on content | unit | `pytest tests/services/test_dssc_config.py::test_config_is_pure_data_no_hardcoded_labels -x` | ❌ Wave 0 |
| QSTN-04 | `GET /questionnaire/config` returns identical config regardless of user/initiative participant_type | integration | `pytest tests/api/test_questionnaire.py::test_config_endpoint_universal -x` | ❌ Wave 0 (no `test_questionnaire.py` exists yet — confirmed via file listing) |
| QSTN-05 | Placeholder content stubs all 52 questions (structural, not real-content, check) | unit | `pytest tests/services/test_dssc_config.py::test_all_52_questions_present -x` | ❌ Wave 0 |
| MIGR-01 | Pre-migration v1.0 data intact, queryable, read-only in archive table after upgrade | integration (migration) | `pytest tests/migrations/test_v1_archive_migration.py -x` | ❌ Wave 0 — new test category, no `tests/migrations/` dir exists |
| MIGR-02 | Evidence subsystem fully absent (no table, no route, no frontend file) | integration + static check | `pytest tests/api/test_evidence_removed.py -x` (assert 404/no route) + `grep -r EvidenceURL backend/app` returns nothing | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` (existing CLAUDE.md gate)
- **Per wave merge:** full suite including the new migration-verification test (which is NOT `perf`/`benchmark`-marked, so it runs in the default quick suite too — keep it fast, e.g. under a few seconds, since it's schema-only, no large data volumes)
- **Phase gate:** Full suite green before `/gsd-verify-work`, plus a manual/scripted check that `alembic upgrade head` followed by `alembic downgrade -1` both succeed against a testcontainer seeded with realistic pre-migration row counts

### Wave 0 Gaps
- [ ] `tests/services/test_dssc_config.py` — covers QSTN-01/03/05 (config shape, 52 questions, 6 categories, label overrides supported)
- [ ] `tests/api/test_questionnaire.py` — covers QSTN-04 (universal config endpoint, no participant_type branching) — **does not currently exist**, confirmed via directory listing
- [ ] `tests/migrations/test_v1_archive_migration.py` — covers MIGR-01 (seed pre-migration-shaped rows via raw SQL against a fresh testcontainer, run `alembic.command.upgrade`, assert archive table row count/content matches, assert `initiative.schema_version` tagged correctly) — **new test category and directory**, no `tests/migrations/` exists today; this is the single most important net-new test this phase needs given Pitfall 2
- [ ] `tests/api/test_evidence_removed.py` — covers MIGR-02 (assert `/initiatives/{id}/evidence` routes return 404, not 405/500; assert no `EvidenceURL` import anywhere via a simple `grep`/`ast`-based static check, or just rely on the fact that a leftover import would fail collection entirely)
- [ ] Update (not create) `tests/factories.py`, `tests/api/test_admin.py`, `tests/api/test_reports.py`, `tests/services/test_report_generator.py` — remove `make_evidence`/`EvidenceURL` usage per Pitfall 3; these are modifications to existing Phase-12 files, tracked here because they'll fail collection otherwise

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Unchanged this phase — no auth logic touched |
| V3 Session Management | No | Unchanged this phase |
| V4 Access Control | Yes (indirectly) | Existing `get_current_user`/ownership checks (`initiative.user_id != current_user.id`) in `questionnaire.py` must continue to gate the new `assessment`/answer endpoints exactly as they do today for `initiative_id`-scoped routes — no new access-control code needed, just verify the pattern is preserved when routes are re-keyed to `assessment_id` |
| V5 Input Validation | Yes | New answer `score: int` field must be validated to the 1-5 range at the Pydantic schema layer (`AnswerCreate`), not left to the DB `CHECK`-less integer column alone — add a `field_validator`/`Field(ge=1, le=5)` constraint |
| V6 Cryptography | No | Not applicable — no new secrets/crypto this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Answer-score out-of-range injection (e.g., posting `score: 999` or `score: -1`) | Tampering | Pydantic `Field(ge=1, le=5)` on `AnswerCreate.score`, mirrored by a DB-level `CHECK (score BETWEEN 1 AND 5)` constraint in the migration for defense-in-depth (cheap to add in `op.create_table`) |
| Cross-initiative `assessment_id` enumeration (a user guessing another user's `assessment_id` to read/write answers) | Elevation of Privilege | Same ownership-check pattern already used for `initiative_id` (`initiative.user_id != current_user.id`) must be re-derived through the `Assessment.initiative_id` FK for any endpoint keyed by `assessment_id` — do not trust `assessment_id` alone without joining back to verify `initiative.user_id == current_user.id` |

## Sources

### Primary (HIGH confidence)
- `backend/alembic/env.py`, `backend/alembic/versions/*.py` (all 9 files) — direct code read, migration mechanics and precedent patterns
- `backend/app/models/{initiative,questionnaire,evidence,user,report}.py`, `backend/app/db/base.py` — direct code read, current schema shapes
- `backend/app/services/{mami_config,scoring_engine,report_generator}.py`, `backend/app/api/v1/{questionnaire,admin,evidence,reports}.py`, `backend/app/core/deps.py`, `backend/app/main.py` — direct code read, integration points and break surfaces
- `backend/tests/conftest.py`, `backend/tests/factories.py`, `backend/tests/api/test_admin.py` — direct code read, test infrastructure gaps
- `config/scoring/mami-scoring.json` — direct code read, JDM rule-matching behavior (confirms degenerate-not-crashing claim in Pitfall 3)
- `.planning/phases/13-.../13-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/config.json` — project/requirement context

### Secondary (MEDIUM confidence)
- [SQLModel GitHub Discussion #717](https://github.com/fastapi/sqlmodel/discussions/717) — confirms `(str, Enum)` fields no longer auto-treated as strings in SQL, cross-checked against this repo's own `conftest.py` comment describing the same symptom
- [Alembic autogenerate documentation](https://alembic.sqlalchemy.org/en/latest/autogenerate.html) — confirms `compare_type` defaults to off unless explicitly enabled, cross-checked against `backend/alembic/env.py` (no `compare_type` param present)

### Tertiary (LOW confidence)
- None used for load-bearing claims in this research.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, everything pinned and already in use
- Architecture: HIGH — every pattern is a direct extension of code read in this repo this session
- Pitfalls: HIGH for repo-specific findings (imports, test coupling, JDM rule matching all directly verified); MEDIUM for the SQLModel-enum-default claim (cross-checked externally, not independently reproduced by running code in this session)

**Research date:** 2026-07-22
**Valid until:** 30 days (stable domain — no fast-moving external dependencies; re-verify only if `sqlmodel`/`alembic` pins change in `pyproject.toml` before Phase 13 executes)
