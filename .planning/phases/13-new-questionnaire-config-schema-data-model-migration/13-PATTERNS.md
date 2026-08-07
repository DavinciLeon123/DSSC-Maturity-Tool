# Phase 13: New Questionnaire Config Schema & Data Model Migration - Pattern Map

**Mapped:** 2026-07-22
**Files analyzed:** 21 (new + modified + deleted)
**Analogs found:** 19 / 21 (2 are genuinely new-pattern, flagged under "No Analog Found")

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `config/dssc-questionnaire.json` (new) | config | file-I/O | `config/dsi-questionnaire-v2.json` / `config/questionnaire-v1.json` | role-match (shape differs: single file, not split) |
| `backend/app/models/assessment.py` (new) | model | CRUD | `backend/app/models/initiative.py` (status enum + lifecycle) | partial (new entity, precedent is the status-enum pattern only) |
| `backend/app/models/questionnaire_answer_archive.py` (new) | model | CRUD (read-only) | `backend/app/models/questionnaire.py` (current `QuestionnaireAnswer`, pre-reshape shape) | exact (archive mirrors current shape verbatim) |
| `backend/app/models/questionnaire.py` (modified — reshaped) | model | CRUD | itself (pre-migration version) + `backend/app/models/initiative.py` (enum-field pattern) | exact (self-analog, reshaped in place) |
| `backend/app/models/initiative.py` (modified — `schema_version` col) | model | CRUD | `backend/alembic/versions/f6a4b3c2d1e9_...py` (added `participant_type` column, same table) | exact |
| `backend/app/models/user.py` (modified — nullable `participant_type`) | model | CRUD | `backend/alembic/versions/h8c6d5e4f3a2_make_contact_fields_nullable.py` | exact |
| `backend/app/models/evidence.py` (deleted) | model | CRUD | n/a (deletion) | n/a |
| `backend/app/schemas/questionnaire.py` (modified — `AnswerCreate`/`AnswerRead` reshaped) | schema (Pydantic) | request-response | itself (pre-reshape) | exact |
| `backend/app/schemas/initiative.py` (modified — `participant_type: str \| None`) | schema (Pydantic) | request-response | itself (pre-change) | exact |
| `backend/app/schemas/evidence.py` (deleted) | schema | request-response | n/a (deletion) | n/a |
| `backend/app/services/mami_config.py` (modified — single-file loader added) | service | file-I/O | itself (`load_questionnaire_configs()` DSI/SP pattern) | exact |
| `backend/app/core/deps.py` (modified — collapse to single config dep) | middleware/utility (FastAPI dependency) | request-response | itself (`get_questionnaire_configs`) | exact |
| `backend/app/main.py` (modified — lifespan config load, evidence router removal) | config (app bootstrap) | request-response | itself (existing `lifespan()`) | exact |
| `backend/app/api/v1/questionnaire.py` (modified — drop participant_type branch, key off `assessment_id`) | controller/route | request-response | itself (existing `upsert_answer`/`get_questionnaire_config_endpoint`) | exact |
| `backend/app/api/v1/evidence.py` (deleted) | controller/route | request-response (CRUD) | n/a (deletion) | n/a |
| `backend/app/api/v1/admin.py` (modified — strip evidence cascade-delete) | controller/route | request-response | itself, lines ~18, 78, 146, 198, 216 | exact |
| `backend/app/api/v1/reports.py` (modified — strip `evidence_by_code` plumbing) | controller/route | request-response | itself (5 near-identical call sites) | exact |
| `backend/app/services/report_generator.py` (modified — strip `evidence_by_code` params) | service | transform | itself (`generate_html_report`, `generate_report_data`, `_build_findings_detail`) | exact |
| `backend/app/db/base.py` (modified — swap model imports) | config (Alembic registry) | n/a | itself | exact |
| `backend/alembic/versions/<new>_questionnaire_v2_schema_migration.py` (new) | migration | batch (one-time data copy) | `backend/alembic/versions/f6a4b3c2d1e9_dsi_sp_questionnaire_foundation.py` (data-preserving, in-place) + `backend/alembic/versions/e5f3a2b4c6d7_add_compliance_report_table.py` (create_table precedent, not read but named in research) | partial — this migration is a *new* pattern (archive-table-split + drop/recreate), no exact same-shape precedent exists |
| `backend/tests/factories.py` (modified — drop `make_evidence`) | test (fixtures) | CRUD | itself | exact |
| `backend/tests/api/test_admin.py` (modified — drop evidence assertions) | test | request-response | itself | exact |
| `backend/tests/migrations/test_v1_archive_migration.py` (new) | test (migration verification) | batch | `backend/tests/conftest.py` (`postgres_container`/`engine` fixtures — session-scoped, must NOT reuse for this test; needs its own isolated fixture) | partial — new test category, no direct precedent in this repo |
| `frontend/src/lib/evidence.ts` (deleted) | utility | request-response | n/a (deletion) | n/a |
| `frontend/src/components/questionnaire/EvidenceInput.tsx` (deleted) | component | request-response | n/a (deletion) | n/a |

## Pattern Assignments

### `backend/app/services/mami_config.py` (service, file-I/O) — add single-file loader

**Analog:** itself, `load_questionnaire_configs()` (lines 23-29)

**Existing pattern to extend** (`backend/app/services/mami_config.py:1-29`):
```python
CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"

def load_questionnaire_configs() -> dict:
    """Load both DSI and SP questionnaire configs (v2).
    Returns dict keyed by participant_type: {"DSI": {...}, "SP": {...}}
    """
    dsi = json.loads((CONFIG_DIR / "dsi-questionnaire-v2.json").read_text())
    sp = json.loads((CONFIG_DIR / "sp-questionnaire-v2.json").read_text())
    return {"DSI": dsi, "SP": sp}
```

**New function to add** (same file, same `CONFIG_DIR` resolution, single dict return — no participant_type key):
```python
def load_dssc_questionnaire_config() -> dict:
    """Load config/dssc-questionnaire.json. Single universal config, no participant_type key."""
    path = CONFIG_DIR / "dssc-questionnaire.json"
    return json.loads(path.read_text())
```
Do not remove `load_questionnaire_configs`/`load_questionnaire_config` yet — `app.state.questionnaire_config`/`questionnaire_configs` may still be referenced elsewhere this phase does not touch (verify at `main.py` before deleting). Adding alongside is the safe move; removal is optional cleanup only if nothing else in the codebase imports the old ones after this phase's edits.

---

### `backend/app/core/deps.py` (FastAPI dependency, request-response) — collapse config dependency

**Analog:** itself, `get_questionnaire_configs` (lines 57-59)

**Existing pattern**:
```python
def get_questionnaire_configs(request: Request) -> dict:
    """FastAPI dependency: returns both v2 questionnaire configs as {"DSI": {...}, "SP": {...}}."""
    return request.app.state.questionnaire_configs
```

**New dependency, identical shape**:
```python
def get_dssc_questionnaire_config(request: Request) -> dict:
    return request.app.state.dssc_questionnaire_config
```

---

### `backend/app/main.py` (app bootstrap) — lifespan config caching + evidence router removal

**Analog:** itself, `lifespan()` (lines 26-43) and router registration (lines 67-73)

**Existing lifespan pattern to extend**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mami_config = load_mami_config()
    app.state.questionnaire_config = load_questionnaire_config()
    app.state.questionnaire_configs = load_questionnaire_configs()
    scoring_dir = get_scoring_dir()
    def loader(key: str) -> str:
        return (scoring_dir / key).read_text()
    app.state.zen_engine = zen.ZenEngine({"loader": loader})
    yield
```
Add `app.state.dssc_questionnaire_config = load_dssc_questionnaire_config()` alongside the existing loads (do not remove the MAMI/ZEN config loads — Phase 14's concern, must keep booting).

**Router removal**: delete `from app.api.v1.evidence import router as evidence_router` (line 12) and `app.include_router(evidence_router, prefix="/api/v1")` (line 71).

---

### `backend/app/api/v1/questionnaire.py` (controller, request-response) — drop participant_type branch

**Analog:** itself (lines 20-35, 38-91)

**Current pattern with participant_type + initiative lookup** (lines 20-35):
```python
@router.get("/questionnaire/config")
def get_questionnaire_config_endpoint(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    configs: dict = Depends(get_questionnaire_configs),
):
    initiative = session.exec(
        select(Initiative).where(Initiative.user_id == current_user.id)
    ).first()
    if not initiative:
        raise HTTPException(status_code=404, detail="Create an initiative first to access the questionnaire")
    participant_type = initiative.participant_type.value
    return configs[participant_type]
```
**New pattern** (per RESEARCH.md Pattern 3, keep the same file/router structure, no initiative lookup needed):
```python
@router.get("/questionnaire/config")
def get_questionnaire_config_endpoint(
    config: dict = Depends(get_dssc_questionnaire_config),
):
    return config
```
Flag A1 from RESEARCH.md: confirm with planner whether the 404-if-no-initiative gate should be preserved as a plain existence check (no participant_type resolution) — do not silently drop user-facing behavior without a decision.

**Existing upsert pattern to extend for `assessment_id` keying** (lines 42-91, `pg_insert(...).on_conflict_do_update(...)`):
```python
stmt = pg_insert(QuestionnaireAnswer).values(
    initiative_id=initiative_id,
    question_id=question_id,
    mami_code=answer_in.mami_code,
    questionnaire_version=answer_in.questionnaire_version,
    answer_value=answer_in.answer_value,
    followup_selections=answer_in.followup_selections,
    followup_other=answer_in.followup_other,
    answered_at=datetime.utcnow(),
    updated_at=datetime.utcnow(),
)
stmt = stmt.on_conflict_do_update(
    constraint="uq_answer_per_question",
    set_={...},
)
session.exec(stmt)
session.commit()
```
Extend this exact upsert shape but (a) look up-or-create the current draft `Assessment` for the initiative first (mirror the `initiative.user_id != current_user.id` ownership check already present, lines 53-57/101-105, re-derived through `Assessment.initiative_id`), (b) swap `initiative_id`/`mami_code` for `assessment_id`/`category_id`/`score`, (c) update the `UniqueConstraint` name to match the new one (`uq_answer_per_question_v2` per RESEARCH.md Pattern 2).

---

### `backend/app/models/questionnaire.py` (model, CRUD) — reshape to 1-5 score

**Analog:** itself, current shape (lines 1-33)

**Current shape**:
```python
class AnswerValue(str, Enum):
    yes = "YES"
    not_there_yet = "NOT_THERE_YET"
    not_applicable = "NOT_APPLICABLE"

class QuestionnaireAnswer(SQLModel, table=True):
    __tablename__ = "questionnaire_answer"
    __table_args__ = (
        UniqueConstraint("initiative_id", "question_id", name="uq_answer_per_question"),
    )
    id: int | None = Field(default=None, primary_key=True)
    initiative_id: int = Field(foreign_key="initiative.id", index=True)
    question_id: str = Field(index=True)
    mami_code: str = Field(index=True)
    questionnaire_version: str
    answer_value: AnswerValue
    followup_selections: list[str] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    followup_other: str | None = None
    rationale: str | None = None
    answered_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```
Reshape per RESEARCH.md Pattern 2's new-table columns: `assessment_id` FK (not `initiative_id`), `category_id`, `score: int` (1-5, `Field(ge=1, le=5)` per Security Domain V5 constraint), keep `answered_at`/`updated_at` timestamp pattern, new `UniqueConstraint("assessment_id", "question_id", name="uq_answer_per_question_v2")`.

**IMPORTANT pitfall carried over from analog** — the model currently declares `answer_value: AnswerValue` (bare `(str, Enum)` field) without an explicit `sa_column=Column(String)`; the archive table (below) must NOT repeat this for its own `answer_value` field if defined as a real ORM class — see Pitfall 1 in RESEARCH.md.

---

### `backend/app/models/questionnaire_answer_archive.py` (new model) — mirror OLD shape verbatim

**Analog:** `backend/app/models/questionnaire.py` pre-reshape shape (exact same columns)

**Copy this shape into the new archive model**, but per RESEARCH.md Pitfall 1, force `sa.String()` explicitly for the enum-shaped column rather than a bare `Enum` annotation:
```python
class QuestionnaireAnswerV1Archive(SQLModel, table=True):
    __tablename__ = "questionnaire_answer_v1_archive"
    id: int | None = Field(default=None, primary_key=True)
    initiative_id: int = Field(index=True)  # deliberately NO FK — see Anti-Patterns (A2: must survive initiative hard-delete)
    question_id: str = Field(index=True)
    mami_code: str = Field(index=True)
    questionnaire_version: str
    answer_value: str = Field(sa_column=Column(String, nullable=False))  # NOT AnswerValue enum type — see Pitfall 1
    followup_selections: list[str] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    followup_other: str | None = None
    rationale: str | None = None
    answered_at: datetime
    updated_at: datetime
```

---

### `backend/app/models/initiative.py` (model, CRUD) — add `schema_version` column

**Analog:** `backend/alembic/versions/f6a4b3c2d1e9_dsi_sp_questionnaire_foundation.py` (added `participant_type` column to same table, same "VARCHAR with server_default" style)

**Analog migration excerpt** (lines 27-32):
```python
def upgrade() -> None:
    op.add_column(
        "initiative",
        sa.Column("participant_type", sa.String(), nullable=False, server_default="DSI"),
    )
```
**Model-side precedent to follow** (`backend/app/models/initiative.py:41-42`):
```python
participant_type: ParticipantType = Field(default=ParticipantType.dsi)
status: InitiativeStatus = Field(default=InitiativeStatus.draft)
```
Add `schema_version: str = Field(default="v2")` to the model in the same style, and in the migration use the exact same `op.add_column(... nullable=False, server_default=...)` pattern, then a follow-up `op.execute("UPDATE initiative SET schema_version = 'v1_legacy' WHERE ...")` (see migration section below).

---

### `backend/app/models/user.py` / `backend/app/models/initiative.py` — nullable `participant_type` (D-12)

**Analog:** `backend/alembic/versions/h8c6d5e4f3a2_make_contact_fields_nullable.py` (lines 25-38) — direct precedent for "make column nullable, no data loss"

**Analog excerpt**:
```python
def upgrade() -> None:
    op.alter_column("initiative", "contact_name", nullable=True)
    op.alter_column("initiative", "contact_email", nullable=True)
    op.alter_column("initiative", "organization", nullable=True)

def downgrade() -> None:
    op.execute("UPDATE initiative SET contact_name = '' WHERE contact_name IS NULL")
    ...
    op.alter_column("initiative", "contact_name", nullable=False)
```
Apply the identical `op.alter_column(..., nullable=True)` pattern to `initiative.participant_type` and `user.participant_type`, and update both models (`backend/app/models/initiative.py:41`, `backend/app/models/user.py:11`) from non-optional to `ParticipantType | None = Field(default=None)` / `str | None = Field(default=None)`.

**Downstream Pydantic fallout (Pitfall 5) — same-file pattern to fix together:**
- `backend/app/schemas/initiative.py:54` — `participant_type: str` → `str | None`
- `AdminUserRow.participant_type` / `AdminInitiativeRow.participant_type` in `admin.py` — same change

---

### `backend/app/api/v1/admin.py`, `backend/app/services/report_generator.py`, `backend/app/api/v1/reports.py` — strip evidence plumbing

**Exact call sites found** (all in current codebase, all must be removed together per Pitfall 3):

`admin.py`:
```python
from app.models.evidence import EvidenceURL          # line 18 — remove
session.exec(sql_delete(EvidenceURL).where(EvidenceURL.initiative_id == initiative_id))  # line 78 — remove
```

`reports.py` (5 near-identical blocks, e.g. lines 109-120):
```python
from app.models.evidence import EvidenceURL   # line 16 — remove
evidence_rows = session.exec(
    select(EvidenceURL).where(EvidenceURL.initiative_id == initiative_id)
).all()
evidence_by_code: dict = {}
for ev in evidence_rows:
    evidence_by_code.setdefault(ev.mami_code, []).append(ev)
...
evidence_by_code=evidence_by_code,   # passed into report_generator calls — remove/pass {} at each of 5 call sites
```

`report_generator.py`:
```python
def generate_html_report(..., evidence_by_code: dict, ...):   # drop param, and its usage at line ~144
    evidence = evidence_by_code.get(f["mami_code"], [])
    ...
    "evidence": [{"url": ev.url if hasattr(ev, "url") else ev.get("url", "")} for ev in evidence],
```
Same pattern repeats for `generate_report_data` (~line 263) and `_build_findings_detail` (~line 131). Choose smaller diff: drop the parameter entirely and its call-site references (recommended over passing `{}` inline, since RESEARCH.md flags this as "whichever is a smaller diff").

---

### `backend/tests/factories.py` / `backend/tests/api/test_admin.py` — remove evidence fixtures/assertions

**Exact lines to remove:**
```python
# factories.py
from app.models.evidence import EvidenceURL   # line 17
def make_evidence(...) -> EvidenceURL: ...     # lines 113-130

# test_admin.py
from app.models.evidence import EvidenceURL    # line 18
from ...factories import make_evidence          # line 23
make_evidence(session, initiative=initiative)   # lines 117, 164
session.exec(select(EvidenceURL).where(...)).all()  # lines 133, 179 — and their assertions
```

---

### `backend/alembic/versions/<new>_questionnaire_v2_schema_migration.py` (new migration)

**Analog:** `f6a4b3c2d1e9_dsi_sp_questionnaire_foundation.py` (data-preserving `op.execute` UPDATE pattern) for the "tag legacy initiatives" step; no exact precedent exists for the archive-table-split + drop/recreate — this is a genuinely new pattern for this repo (see "No Analog Found" below). Chain from `h8c6d5e4f3a2` (current head).

Use RESEARCH.md's Pattern 2 code block verbatim as the starting template — it was synthesized directly from this repo's `e5f3a2b4c6d7` (`create_table`) + `f6a4b3c2d1e9` (`op.execute` UPDATE) conventions and is copy-paste ready:
```python
def upgrade() -> None:
    op.create_table(
        "questionnaire_answer_v1_archive",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiative_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(), nullable=False),
        sa.Column("mami_code", sa.String(), nullable=False),
        sa.Column("questionnaire_version", sa.String(), nullable=False),
        sa.Column("answer_value", sa.String(), nullable=False),  # sa.String, NOT sa.Enum — Pitfall 1
        sa.Column("followup_selections", JSONB, nullable=True),
        sa.Column("followup_other", sa.Text(), nullable=True),
        sa.Column("rationale", sa.String(), nullable=True),
        sa.Column("answered_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        # no FK to initiative.id — must survive initiative hard-delete (Anti-Pattern/A2)
    )
    op.execute("""
        INSERT INTO questionnaire_answer_v1_archive (...)
        SELECT ... FROM questionnaire_answer
    """)
    op.add_column("initiative", sa.Column("schema_version", sa.String(), nullable=False, server_default="v2"))
    op.execute("""
        UPDATE initiative SET schema_version = 'v1_legacy'
        WHERE id IN (SELECT DISTINCT initiative_id FROM questionnaire_answer_v1_archive)
    """)
    op.drop_table("questionnaire_answer")
    op.create_table("questionnaire_answer", ...)  # new 1-5-score shape, assessment_id FK
```
Also add `op.create_table("assessment", ...)` before the archive/drop steps (new table, no precedent needed — plain `create_table` matching `e5f3a2b4c6d7`'s style for `compliance_report`).

---

### `backend/tests/migrations/test_v1_archive_migration.py` (new test) — isolated fixture, not shared session fixture

**Analog:** `backend/tests/conftest.py` `postgres_container`/`engine` fixtures (lines 57-76) — reuse the *container-spinning* mechanics but NOT the shared session-scoped fixture itself.

**Existing session-scoped fixture (do not reuse directly)**:
```python
@pytest.fixture(scope="session")
def postgres_container():
    ...

@pytest.fixture(scope="session")
def engine(postgres_container):
    url = postgres_container.get_connection_url().replace("postgresql+psycopg2", "postgresql")
    eng = create_engine(url)
    SQLModel.metadata.create_all(eng)
    return eng
```
Per RESEARCH.md Pitfall 2, this test needs its **own** fixture scope (e.g. function- or module-scoped, a fresh testcontainer) since the shared `engine` fixture has already had `create_all()` run against it — not a clean slate for verifying `alembic upgrade head`. Use `testcontainers.postgres.PostgresContainer` directly in the new test file, run `alembic.command.upgrade(config, "head")` from an empty DB, then a second variant that seeds OLD-shaped rows via raw SQL before upgrading and asserts archive-table row counts.

## Shared Patterns

### Config resolution (`Path(__file__).parent` chain)
**Source:** `backend/app/services/mami_config.py:8`
**Apply to:** New `load_dssc_questionnaire_config()` function — reuse `CONFIG_DIR` exactly as-is, no new path-resolution logic.

### FastAPI lifespan config caching
**Source:** `backend/app/main.py:26-41`
**Apply to:** New `app.state.dssc_questionnaire_config` load — added alongside existing config loads, not replacing them (MAMI/ZEN config stays alive per Phase 14 boundary).

### Ownership check pattern (`initiative.user_id != current_user.id`)
**Source:** `backend/app/api/v1/questionnaire.py:53-57, 101-105`; also `evidence.py:22, 44-45, 62`
**Apply to:** Any new `assessment_id`-keyed endpoint — must re-derive ownership by joining `Assessment.initiative_id` back to `Initiative.user_id`, exactly as today's `initiative_id`-keyed endpoints do. Do not trust `assessment_id` alone (Security Domain V4/Elevation-of-Privilege risk called out in RESEARCH.md).

### Data-preserving migration via `op.execute()` (never bare autogenerate)
**Source:** `backend/alembic/versions/f6a4b3c2d1e9_dsi_sp_questionnaire_foundation.py` (whole file)
**Apply to:** The new migration's legacy-tagging UPDATE and the archive-table INSERT/SELECT copy — hand-written `op.execute()`, matching every prior data-transforming migration in this repo's history.

### `str, Enum` fields require explicit `sa.String()` to avoid native Postgres ENUM drift
**Source:** `backend/app/models/questionnaire.py:26` (`answer_value: AnswerValue`, currently a bare enum annotation — an existing latent inconsistency, not something to imitate) vs. `backend/alembic/versions/f6a4b3c2d1e9_...py:31` (`sa.Column("participant_type", sa.String(), ...)` — the correct explicit pattern)
**Apply to:** Archive-table model's `answer_value` column and the migration's `sa.Column(..., sa.String())` declarations — always explicit, never a bare Python enum type in `op.create_table`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `backend/alembic/versions/<new>_questionnaire_v2_schema_migration.py` (archive-split + drop/recreate portion) | migration | batch | No prior migration in this repo drops+recreates a table or splits data into a new archive table — every existing migration is `ADD COLUMN`/`ALTER COLUMN`/single `CREATE TABLE`. RESEARCH.md's Pattern 2 code block (synthesized, not copied from an existing file) is the closest available template — use it directly rather than searching further. |
| `backend/tests/migrations/test_v1_archive_migration.py` | test (migration verification) | batch | No `tests/migrations/` directory or migration-verification test exists anywhere in this repo today (confirmed via RESEARCH.md Pitfall 2 — `alembic upgrade head` only runs at Docker container startup, never in CI/pytest). Build from `testcontainers.postgres.PostgresContainer` + `alembic.command.upgrade` directly; do not force-fit the existing session-scoped `engine` fixture. |

## Metadata

**Analog search scope:** `backend/app/{models,schemas,services,api/v1,core,db}/`, `backend/alembic/versions/`, `backend/tests/`, `frontend/src/lib/`, `frontend/src/components/questionnaire/`
**Files scanned:** 24 read/grepped directly this session (listed under Pattern Assignments above), plus 10 migration filenames enumerated via `ls`
**Pattern extraction date:** 2026-07-22
