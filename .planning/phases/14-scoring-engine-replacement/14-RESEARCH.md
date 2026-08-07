# Phase 14: Scoring Engine Replacement - Research

**Researched:** 2026-07-24
**Domain:** Python/FastAPI + SQLModel backend — dependency removal, endpoint response-shape adaptation, config-driven aggregate scoring
**Confidence:** HIGH (all findings below are grep/read-verified against this exact codebase, not general framework knowledge)

## Summary

This phase is entirely mechanical: delete a well-isolated ZEN/MoSCoW subsystem, add a small pure-computation service, and adapt five existing endpoints (`/score`, `/report`, `/report/data` GET+POST, `/report/pdf`, `/report/mail`) plus one admin endpoint (`/heatmap`) to stop depending on it. Every touch point is traced below with exact current code. Two non-obvious landmines were found that are NOT in CONTEXT.md's canonical_refs and must be in the plan or the phase will ship broken: (1) `report.html`'s Jinja2 template calls `heatmap_rows.get(...)` and iterates `not_yet_recommendations` — deleting `_build_heatmap_rows`/`_build_not_yet_recommendations` (D-01a) without still passing `heatmap_rows={}`/`not_yet_recommendations=[]` literals into the template context will crash `/report`, `/report/pdf`, `/report/mail` with a Jinja2 `UndefinedError` on every call; (2) the actual PyPI package name is `zen-engine`, not `zen` — `uv remove zen` will fail; the pyproject.toml dependency line is `"zen-engine==0.51.0"`.

Also found: `/initiatives/{id}/score` currently returns HTTP 200 with an all-zero `ScoreResponse` when there are no answers (no 422 at all today) — D-07's "422 when incomplete" is a *new* behavior for this endpoint, not a fix to an existing 422. `backend/tests/api/test_admin.py`'s existing heatmap test (`test_admin_heatmap_reflects_submitted_initiatives`) asserts `"matrix" in body` / `"topic_structure" in body`, which will fail once D-01b's trivial degraded shape ships — this test is a **required edit** the CONTEXT.md canonical_refs list does not mention. The `mami_codes`/`make_answers` fixtures in `conftest.py` (which import `load_mami_config`) have **no consumers other than** the two files D-08 deletes — confirmed by repo-wide grep — so they should be deleted, not adapted.

**Primary recommendation:** Delete ZEN/MoSCoW code first (it's fully inert already — see Pitfall 4), then build `dimension_scoring.py` as a pure function over `(session, assessment_id, config)`, then adapt the five score/report endpoints to call a shared `_require_complete_assessment()` gate before touching scoring, then fix the two call sites that will otherwise crash (`generate_html_report`'s Jinja context, `test_admin.py`'s heatmap assertions).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Dimension score computation (SCOR-01/02) | API/Backend (service layer) | Database (aggregation query) | Pure computation over `QuestionnaireAnswer` rows scoped to one `Assessment`; no client-side logic, no new persisted column |
| Completion gate (SCOR-04) | API/Backend (route dependency/helper) | Database (existence/count query) | Must run server-side before any scoring computation — a client-trusted "is complete" flag would violate SCOR-04's "no partial/live scoring is ever returned" guarantee |
| ZEN/MoSCoW removal (SCOR-03) | API/Backend + Database/Storage (config files) + Dependency manifest | — | Removal spans app code, `app.state`, JSON config files, and `pyproject.toml`/`uv.lock` — all backend-tier, no frontend/CDN involvement this phase |
| `/score`, `/report/data` response shape | API/Backend | — | Pydantic response models + plain dict returns; no template/HTML involved for `/report/data` (JSON only, D-05) |
| `/report`, `/report/pdf`, `/report/mail` HTML rendering | API/Backend (Jinja2 template render) | — | Template itself (`report.html`) is explicitly NOT touched this phase (D-05) — only the Python context-building around it changes |

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions

**Removal boundary (SCOR-03):**
- D-01: Full removal of `zen` package (`zen-engine` in `pyproject.toml`/`uv.lock`), `scoring_engine.py`, `config/scoring/` (`mami-scoring.json`), and `config/mami-framework.json`. Also remove `app.state.zen_engine`/`app.state.mami_config` wiring in `main.py`, `get_zen_engine`/`get_mami_config` in `deps.py`, and `load_mami_config()`/`get_scoring_dir()` in `mami_config.py`.
- D-01a (revised): `report_generator.py`'s `_build_matrix`, `_build_topic_structure`, `_build_heatmap_rows`, `_build_not_yet_recommendations`, `_build_findings_detail`, and `_RECOMMENDATIONS` are **deleted outright**, not degraded to empty stubs. `generate_report_data`/`generate_html_report` are simplified to only what still works (initiative info) plus the new `dimension_scores` field.
- D-01b (revised): `admin.py`'s `/heatmap` endpoint becomes a trivial fixed degraded response (e.g. `{"degraded": true, "cells": []}`) — topic-structure-building logic stripped entirely, not fed an empty config.

**New scoring logic (SCOR-01/02):**
- D-02 (locked formula): `dimension_score = sum(answers in that dimension) / number of questions in that dimension`. Range 1.0–5.0. Dimensions have varying question counts (9/9/9/9/8/8 currently) — divide by each dimension's own question count, not a fixed constant.
- D-03: New scoring logic lives as an internal service (e.g. `backend/app/services/dimension_scoring.py`, exact name Claude's discretion), computing per-category scores from `QuestionnaireAnswer` rows joined through `Assessment`, against the 6 categories in `config/dssc-questionnaire.json`. No new dedicated endpoint — surfaced via adapting existing endpoints.

**Legacy endpoint adaptation:**
- D-04: `POST /initiatives/{id}/score` response shape changes: drop `FindingRead`/`severity`/MoSCoW-findings, return per-category shape instead (e.g. `{category_id, name, score}` list) via the new dimension-scoring service. Endpoint kept, repurposed.
- D-05: `/report/data`, `/report`, `/report/pdf`, `/report/mail` get a new field on `/report/data`'s JSON (e.g. `"dimension_scores": [...]`). Old matrix/heatmap/topic_structure fields are removed entirely from the response (not present-but-empty). **JSON only** — `report.html` template and PDF rendering are NOT touched this phase; Phase 16 owns real HTML/PDF rendering of dimension scores.
- D-05a (revised): `_DEGRADED_SCORING_BANNER_HTML`/`_inject_degraded_banner` in `reports.py` are removed entirely, not reworded.

**Completion gate (SCOR-04):**
- D-06: "Fully answered" = distinct `question_id`s answered for the assessment's current `Assessment` row compared against the full set of question IDs in `config/dssc-questionnaire.json` (all 52) — NOT `Assessment.status`. No auto-transition of `Assessment.status` from draft to submitted (that's Phase 15's job).
- D-07: When incomplete, `/score`, `/report`, `/report/data`, `/report/pdf`, `/report/mail` all return HTTP 422 with a clear message (e.g. "Questionnaire not fully answered") — matching the existing 422 pattern already used in `reports.py` for "no answers found." No partial/live scores ever returned.

**Legacy test fate:**
- D-08: `backend/tests/benchmark/test_scoring_regression.py` and `backend/tests/perf/test_scoring_perf.py` are deleted outright, not replaced. Full test coverage for new scoring logic is Phase 17's job. Leave a note that Phase 17 owns writing their equal-weight-scoring replacements.
- `test_health.py`'s `app.state.mami_config is not None`/`zen_engine is not None` assertions must be updated/removed.
- `test_reports.py` and `test_report_generator.py` need adaptation to keep passing against the adapted `report_generator.py`/`reports.py` — exact changes are Claude's discretion.

### Claude's Discretion
- Exact module/file naming for the new dimension-scoring service (D-03).
- Exact response field names for the new `/score` and `/report/data` shapes (D-04/D-05) — category id/name/score is the agreed shape, exact JSON key naming is planning's call.
- Exact fixed shape of the simplified `/heatmap` degraded response (D-01b).
- Exact adaptation of `test_reports.py`/`test_report_generator.py` to match the new adapted endpoints.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. No scope-creep topics came up.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCOR-01 | Dimension score = sum of answers / number of questions in dimension, range 1.0–5.0 | See "New Dimension Scoring Service" pattern below — exact SQLModel aggregation query and config-driven denominator |
| SCOR-02 | All questions equally weighted — no question/category weighting | Formula has no weighting term by construction; config's `default_options`/`options` only map label→score, never a weight multiplier — confirmed by reading `dssc-questionnaire.json` structure |
| SCOR-03 | GoRules ZEN Engine and MoSCoW scoring fully removed | Full call-graph traced below (every `import zen`, every `Depends(get_zen_engine)`/`Depends(get_mami_config)`, every config file, the `zen-engine` PyPI package, and every SBOM/test reference) |
| SCOR-04 | Report/scores only computed once questionnaire is 100% answered | Exact completion-gate mechanics, existing 422 precedent, and the "currently NOT gated at all" finding for `/score` documented below |

</phase_requirements>

## Standard Stack

No new libraries are introduced this phase — it is a pure removal + internal-service phase. Nothing to install.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain Python `sum()`/`len()` over ORM-loaded rows | SQL-side `func.sum()`/`func.count()` GROUP BY `category_id` | SQL aggregation avoids loading full row objects into Python for large answer sets; at 52 rows max per assessment this is a non-issue either way — recommend SQL aggregation only for idiom-consistency with `admin.py`'s existing raw-SQL `COUNT`/`GROUP BY` patterns, not for performance |

**Installation:** N/A — no packages added. One package removed (see Package Legitimacy Audit).

## Package Legitimacy Audit

No new packages are installed this phase. One existing package is **removed**: `zen-engine` (PyPI name; imported in code as `import zen`).

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| zen-engine | PyPI | Pre-existing dependency, already vetted at original install time | N/A (removal, not install) | github.com/gorules/zen | N/A | **REMOVED** — no legitimacy check needed for a removal |

**Packages removed due to [SLOP] verdict:** none — this is a planned architectural removal, not a security disposition.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
PUT /questionnaire/initiatives/{id}/answers/{qid}   (unchanged this phase, Phase 13)
        │
        ▼
QuestionnaireAnswer rows (assessment_id, question_id, category_id, score 1-5)
        │
        │  read by (NEW, this phase)
        ▼
┌─────────────────────────────────────────────────────────────┐
│  dimension_scoring.py (new internal service, D-03)           │
│  1. Load current draft Assessment for initiative              │
│  2. Load answered question_ids for that assessment            │
│  3. Compare against full question_id set from                 │
│     dssc_questionnaire_config (cached at startup)              │
│     → incomplete? raise/signal 422 (SCOR-04, D-06/D-07)        │
│  4. GROUP BY category_id: sum(score) / count(*) per category   │
│     → [{category_id, name, score}], range 1.0-5.0 (SCOR-01/02) │
└─────────────────────────────────────────────────────────────┘
        │
        ├──▶ POST /initiatives/{id}/score  (scoring.py, D-04)
        │        → {category_id, name, score}[] replacing FindingRead[]
        │
        └──▶ /report, /report/data (GET+POST), /report/pdf, /report/mail
                 (reports.py, D-05)
                 → /report/data JSON gains "dimension_scores": [...]
                 → /report, /report/pdf, /report/mail still render
                   report.html via generate_html_report(), now WITHOUT
                   real heatmap/recommendation data (D-01a) — must pass
                   safe empty literals into the template context or the
                   Jinja2 render crashes (see Pitfall 1)

DELETED entirely (D-01):
  backend/app/services/scoring_engine.py
  backend/app/services/mami_config.py::load_mami_config, ::get_scoring_dir
  config/scoring/mami-scoring.json (+ config/scoring/ dir if now empty)
  config/mami-framework.json
  app.state.zen_engine / app.state.mami_config (main.py lifespan)
  get_zen_engine / get_mami_config (core/deps.py)
  zen-engine dependency (pyproject.toml / uv.lock)
```

### Recommended Project Structure
```
backend/app/services/
├── dimension_scoring.py   # NEW — SCOR-01/02/04 computation + completion check
├── mami_config.py         # SURVIVES, trimmed — load_dssc_questionnaire_config()
│                           #   stays; load_mami_config()/get_scoring_dir() deleted
├── report_generator.py    # SURVIVES, trimmed — matrix/heatmap/recommendation
│                           #   builders deleted; generate_report_data/
│                           #   generate_html_report simplified
└── scoring_engine.py       # DELETED entirely
```

### Pattern 1: Dimension Score Computation (SCOR-01/02)

The literal client formula (D-02, verbatim): `Dimensiescore = Som van alle antwoorden / aantal vragen binnen de dimensie`.

Because the completion gate (D-06/D-07) already guarantees every question is answered before scoring ever runs, `count(answered rows in category)` and `count(config questions in category)` are provably equal at the point scoring executes — but deriving the denominator from config (not from the DB row count) is the literal, defensive reading of D-02 and matches how `upsert_answer` in `questionnaire.py` already derives per-question validity from config (`valid_categories_by_question`), not from the DB. Recommend deriving both numerator/denominator inputs this way for consistency with the codebase's existing "config is the source of truth for structure, DB is the source of truth for answers" idiom:

```python
# Source: pattern mirrors app/api/v1/questionnaire.py's existing
# `valid_categories_by_question` config-comprehension idiom (line ~138-142)
from collections import defaultdict

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.assessment import Assessment, AssessmentStatus
from app.models.questionnaire import QuestionnaireAnswer


def _full_question_ids(config: dict) -> set[str]:
    return {q["id"] for cat in config["categories"] for q in cat["questions"]}


def _category_question_counts(config: dict) -> dict[str, int]:
    return {cat["id"]: len(cat["questions"]) for cat in config["categories"]}


def _category_names(config: dict) -> dict[str, str]:
    return {cat["id"]: cat["name"] for cat in config["categories"]}


def get_current_assessment(session: Session, initiative_id: int) -> Assessment | None:
    """Mirrors the exact lookup already used in questionnaire.py's
    get_answers()/_get_or_create_draft_assessment() — the most recent
    draft Assessment for this initiative. D-06 explicitly anchors
    completion on "the assessment's current Assessment row", not on
    Assessment.status, and no submitted-assessment history exists yet
    (Phase 15's job) — so "current" == "most recent draft" today."""
    return session.exec(
        select(Assessment)
        .where(
            Assessment.initiative_id == initiative_id,
            Assessment.status == AssessmentStatus.draft,
        )
        .order_by(Assessment.created_at.desc())
    ).first()


def compute_dimension_scores(
    session: Session, assessment_id: int, config: dict
) -> list[dict]:
    """SCOR-01/02: equal-weight per-category average, 1.0-5.0.
    Caller MUST have already verified completeness (SCOR-04) — this
    function does not re-check and will silently divide by each
    category's config-derived question count regardless of how many
    rows actually exist."""
    rows = session.exec(
        select(
            QuestionnaireAnswer.category_id,
            func.sum(QuestionnaireAnswer.score),
        )
        .where(QuestionnaireAnswer.assessment_id == assessment_id)
        .group_by(QuestionnaireAnswer.category_id)
    ).all()
    sums = dict(rows)
    counts = _category_question_counts(config)
    names = _category_names(config)

    return [
        {
            "category_id": cat_id,
            "name": names[cat_id],
            "score": round(sums.get(cat_id, 0) / n_questions, 2),
        }
        for cat_id, n_questions in counts.items()
    ]
```

### Pattern 2: Completion Gate (SCOR-04, D-06/D-07)

```python
# Source: mirrors the existing 422 precedent already in reports.py
# (download_report_pdf/mail_report: "No answers found. Please complete
# the questionnaire first.")
def assert_assessment_complete(
    session: Session, initiative_id: int, config: dict
) -> Assessment:
    """Raises HTTPException(422) if the initiative's current assessment
    has not answered every question_id in the config. Returns the
    Assessment on success so callers don't have to re-query it."""
    assessment = get_current_assessment(session, initiative_id)
    if assessment is None:
        raise HTTPException(status_code=422, detail="Questionnaire not fully answered")

    answered_ids = set(
        session.exec(
            select(QuestionnaireAnswer.question_id).where(
                QuestionnaireAnswer.assessment_id == assessment.id
            )
        ).all()
    )
    missing = _full_question_ids(config) - answered_ids
    if missing:
        raise HTTPException(status_code=422, detail="Questionnaire not fully answered")
    return assessment
```

Call this as the very first scoring-related step in `scoring.py::score_initiative` and in all four `reports.py` endpoints that currently do scoring (`generate_report`, both `report/data` handlers, `download_report_pdf`, `mail_report`) — **before** any endpoint-specific 404 logic (e.g. `get_report_data_endpoint`'s existing "no report generated yet" 404 check), so an incomplete assessment always surfaces 422 regardless of whatever ComplianceReport row state exists.

### Anti-Patterns to Avoid
- **Reusing `_get_answers_for_initiative`'s multi-assessment join for the completion check:** `reports.py`'s current `_get_answers_for_initiative` joins `QuestionnaireAnswer` to `Assessment` filtered only by `Assessment.initiative_id`, with **no filter on `Assessment.status` or a single assessment id** — it sums answers across every `Assessment` row an initiative has ever had. This is harmless today only because exactly one `Assessment` row exists per initiative in practice (no submission/versioning flow ships until Phase 15). Do not carry this join pattern into the new completion-gate/scoring code; use the single-current-assessment lookup (`get_current_assessment` above, matching `questionnaire.py`'s `get_answers` pattern) so this phase doesn't quietly assume multi-assessment semantics it can't yet support.
- **Degrading `report_generator.py`'s builders to return empty dicts/lists instead of deleting them:** D-01a explicitly rejects this — the functions are deleted outright. Passing hardcoded empty literals (`heatmap_rows={}`, `not_yet_recommendations=[]`) directly at the two call sites is correct; keeping the builder functions alive "just to be safe" is exactly what D-01a forbids.
- **Trusting a client-supplied "is complete" flag:** SCOR-04 requires the gate be enforced server-side from the DB's actual answered-row state on every request, not cached/memoized across requests (per the phase's "no partial/live scoring" requirement).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-category sum/count aggregation | A Python loop that manually buckets rows by category | SQLAlchemy `select(...).group_by(...)` (Pattern 1 above) or an ORM-level Python `sum()`/`len()` over a pre-fetched list (either is fine at this data volume — 52 rows max) | GROUP BY is the existing idiom this codebase already uses for aggregate counts (`admin.py`'s `/heatmap`, `/initiatives` raw SQL) — matching it keeps the new service's style consistent, not because raw Python summation would be wrong at this scale |
| Full-question-id-set comparison | A hardcoded `52` or a hardcoded 6-category/9-9-9-9-8-8 list | Derive both the full ID set and per-category counts from the already-cached `dssc_questionnaire_config` dict at request time | The config is explicitly a placeholder (`"_schema_note"` in the JSON says real content is pending, QSTN-05) — hardcoding today's placeholder shape (52, 9/9/9/9/8/8) breaks the instant real content lands, with no test to catch it |

**Key insight:** Every "don't hand-roll" concern in this phase reduces to "read structure from `dssc_questionnaire_config`, never from a memorized constant" — the config is deliberately a placeholder that will be replaced wholesale later in the milestone (QSTN-05).

## Common Pitfalls

### Pitfall 1: Deleting the matrix/heatmap builders without updating what feeds `report.html`'s Jinja2 context WILL crash `/report`, `/report/pdf`, `/report/mail`
**What goes wrong:** `report.html` (264 lines, confirmed by direct read) references `heatmap_rows.get(cat_id, [])` and `{% if not_yet_recommendations %} ... {% for rec in not_yet_recommendations %}`. `generate_html_report()`'s current context dict passes exactly four keys: `initiative`, `generated_at`, `heatmap_rows`, `not_yet_recommendations` — nothing else. If `_build_heatmap_rows`/`_build_not_yet_recommendations` are deleted (D-01a, correct) and the calls to them are simply removed without substituting literal empty values, Jinja2's default `Undefined` type raises `UndefinedError: 'heatmap_rows' is undefined` the moment the template calls `.get()` on it (Undefined has no `.get` method) — every call to `/report`, `/report/pdf`, `/report/mail` will 500.
**Why it happens:** D-05 explicitly keeps `report.html` untouched this phase (Phase 16 owns real rendering) — but the simplified `generate_html_report()` still must render *some* valid context for that same unchanged template.
**How to avoid:** In the simplified `generate_html_report()`, pass `heatmap_rows={}` and `not_yet_recommendations=[]` as literal empty values directly in the context dict (no builder function call at all) — this satisfies the template's structural needs (empty categories, no recommendations shown) without resurrecting any deleted matrix-building logic.
**Warning signs:** Any test hitting `/report`, `/report/pdf`, or `/report/mail` returning 500 instead of the expected status code; a Jinja2 `UndefinedError` traceback mentioning `heatmap_rows` or `not_yet_recommendations`.

### Pitfall 2: `/initiatives/{id}/score` has NO 422 gate today — D-07 is new behavior, not a fix
**What goes wrong:** Reading `scoring.py::score_initiative` as it exists now: `if not answers: return ScoreResponse(initiative_id=..., total_answers=0, findings=[], critical_count=0, non_critical_count=0)` — this returns **HTTP 200** with an all-zero body when there are no saved answers. There is no 422 anywhere in this file today. A plan that treats D-07 as "keep the existing 422 behavior, just change the body shape" will silently under-implement SCOR-04 for this specific endpoint (the other four `reports.py` endpoints already have a 422 precedent to extend; `/score` has none).
**Why it happens:** `scoring.py` predates the assessment-first schema (Phase 13) and was never wired to any completion concept — it only ever checked "are there zero rows."
**How to avoid:** Explicitly add the `assert_assessment_complete()` call (Pattern 2) to `score_initiative` as new logic, not a modification of existing 422 logic — there is nothing to modify, only something to add.
**Warning signs:** A test asserting `/score` returns 422 for an incomplete/empty assessment failing with a 200 instead.

### Pitfall 3: `test_admin.py`'s existing heatmap test will fail once D-01b ships, and it's not in CONTEXT.md's list
**What goes wrong:** `backend/tests/api/test_admin.py::test_admin_heatmap_reflects_submitted_initiatives` (line ~209-221) currently asserts `assert "matrix" in body` and `assert "topic_structure" in body` against `GET /api/v1/admin/heatmap`'s response. D-01b's simplified degraded response (e.g. `{"degraded": true, "cells": []}`) has neither key — this test will fail the moment `admin.py`'s `/heatmap` handler is simplified, even though CONTEXT.md's canonical_refs section never names `test_admin.py` as a file needing adaptation (it only names `test_health.py`, `test_reports.py`, `test_report_generator.py`, `test_scoring_regression.py`, `test_scoring_perf.py`, `conftest.py`).
**Why it happens:** CONTEXT.md's test-fate list was written before a full repo-wide grep for every response-shape-dependent assertion; `admin.py`'s `_build_topic_structure` import (from `report_generator.py`) and this test's shape assertions are a second-order consequence of D-01a/D-01b that wasn't enumerated.
**How to avoid:** Plan a task to update this specific test's assertions to match whatever fixed degraded shape is chosen for D-01b (e.g. assert `body["degraded"] is True` and the actual chosen key names), alongside `AdminHeatmapResponse`'s model change in `admin.py` itself. Also note `admin.py` currently does `from app.services.report_generator import _build_topic_structure` at module level (line 23) — this import must be removed too, or it will raise `ImportError` once that function is deleted.
**Warning signs:** `ruff`/`mypy`/`pytest` all failing on `admin.py` or `test_admin.py` after `report_generator.py`'s builders are deleted — an orphaned import (`_build_topic_structure`) is the first thing to check.

### Pitfall 4: The ZEN scoring path is already fully inert — deletion order is low-risk, but don't assume it's "live" code
**What goes wrong:** None, if understood correctly — but a planner who assumes `scoring.py`/`reports.py` currently do "real" ZEN scoring might over-engineer a careful migration path. In fact, every one of these four endpoints already calls `_degraded_scoring_inputs()` (reports.py) or hardcodes `answers_for_scoring: list[dict] = []` (scoring.py) — a Phase 13 interim workaround (Assumption A3) that means `score_all_answers(engine, [])` is called with an **empty list** today, every time, in production. `asyncio.gather()` over zero tasks returns `[]` instantly; the ZEN engine's `.async_evaluate()` is never actually invoked with real data anywhere in the current codebase.
**Why it happens:** Phase 13 intentionally degraded these call sites to avoid crashing on the reshaped `QuestionnaireAnswer` schema, without removing the ZEN plumbing itself (that was explicitly deferred to this phase).
**How to avoid:** Treat this as good news for planning risk — deleting `scoring_engine.py`, `config/scoring/mami-scoring.json`, and the `zen-engine` package cannot regress any currently-exercised runtime behavior (the "real" ZEN evaluation path is already dead code in production). The only regression risk is compile-time (orphaned imports) and test-time (fixtures/assertions), both enumerated in this document.
**Warning signs:** N/A — this pitfall is about not over-scoping the plan, not about a runtime failure mode.

### Pitfall 5: The Dockerfile has a stale comment that will become misleading, but the version pin itself is out of scope
**What goes wrong:** `backend/Dockerfile` line 10: `# Use the container's system Python (3.13) — zen-engine has cp313 wheels` and `ENV UV_PYTHON_PREFERENCE=only-system`. Once `zen-engine` is removed, this comment's stated reason is gone, but the Python 3.13 pin itself may still be load-bearing for other reasons (WeasyPrint native bindings, `psycopg2-binary` wheel availability, etc.) that were never verified independently of `zen-engine`'s constraint.
**Why it happens:** `zen-engine==0.51.0`'s wheel matrix (confirmed via `uv.lock`) covers cp312/cp313/cp314 — so it was never actually the sole reason 3.13 was chosen over the local dev machine's 3.14; the comment is just imprecise, not necessarily wrong about the pin's necessity.
**How to avoid:** Low-risk fix: update the comment to stop citing `zen-engine` specifically (e.g. "pinned for wheel-compatibility consistency with other native-extension dependencies," or simply remove the now-inaccurate justification clause), but do NOT change `FROM python:3.13-slim` or `UV_PYTHON_PREFERENCE=only-system` as part of this phase — that's an unrelated infra change with its own blast radius (Docker build/CI), and CONTEXT.md's boundary doesn't ask for it.
**Warning signs:** None functional — this is a documentation-accuracy nit, not a build breaker. Flag as low-priority cleanup, optional for the plan to include.

### Pitfall 6: `config/scoring/` directory becomes empty after deleting `mami-scoring.json`
**What goes wrong:** `config/scoring/` currently contains only `mami-scoring.json` (confirmed via `ls`). Deleting the file leaves an empty directory that git won't track (git has no empty-directory concept) — so `git rm config/scoring/mami-scoring.json` naturally removes the directory from version control once it's empty, but a local working tree might retain the empty folder. Not a functional bug, just worth being deliberate about (`get_scoring_dir()` in `mami_config.py` is also deleted per D-01, so nothing resolves this path anymore regardless).
**How to avoid:** Use `git rm config/scoring/mami-scoring.json` (not a manual `rm`) so git records the deletion cleanly; no further action needed since no code references the directory path after `get_scoring_dir()` is removed.
**Warning signs:** None — purely cosmetic.

## Code Examples

### Removing the dependency correctly
```bash
# Source: uv 0.11.29 (confirmed installed this repo) `uv remove` behavior —
# updates pyproject.toml's [project.dependencies] AND uv.lock AND the
# active .venv in one step. Run from backend/ (where pyproject.toml lives).
cd backend
uv remove zen-engine   # NOT `uv remove zen` — that is the import name,
                       # not the PyPI/pyproject.toml package name.
```
Verified: `backend/pyproject.toml` line 18 reads `"zen-engine==0.51.0",` (not `"zen"`); `backend/uv.lock` line 1116 confirms `{ name = "zen-engine", specifier = "==0.51.0" }`. `import zen` in Python code is just the module's internal name — this is normal for zen-engine (PyPI package `zen-engine` ships an importable module named `zen`), but it means grepping for `zen` to find "the dependency" and then running `uv remove zen` is a natural but incorrect mistake.

### Exact current `main.py` lifespan lines to remove (D-01)
```python
# Source: backend/app/main.py lines 28-29, 38-44 (current, to be deleted)
app.state.mami_config = load_mami_config()
...
scoring_dir = get_scoring_dir()

def loader(key: str) -> str:
    return (scoring_dir / key).read_text()

app.state.zen_engine = zen.ZenEngine({"loader": loader})
```
Also remove `import zen` (line 3) and `load_mami_config`, `get_scoring_dir` from the `mami_config` import block (lines 17-23) — but KEEP `load_dssc_questionnaire_config`, `load_questionnaire_config`, `load_questionnaire_configs` (unrelated legacy loaders, out of this phase's boundary per CONTEXT.md).

### Exact current `core/deps.py` functions to remove (D-01)
```python
# Source: backend/app/core/deps.py lines 1, 42-49 (current, to be deleted)
import zen  # line 1 — remove

def get_zen_engine(request: Request) -> zen.ZenEngine:
    """FastAPI dependency: returns the ZEN Engine singleton from app.state."""
    return request.app.state.zen_engine


def get_mami_config(request: Request) -> dict:
    """FastAPI dependency: returns the loaded mami-framework.json dict."""
    return request.app.state.mami_config
```
Every route currently doing `Depends(get_zen_engine)` / `Depends(get_mami_config)` (all four `reports.py` endpoints, `scoring.py`'s one endpoint) needs both the import and the parameter removed from its signature.

### `dssc-questionnaire.json`'s actual verified shape (for config-reading code)
```json
{
  "version": "dssc-v2-placeholder",
  "default_options": [ /* 5 {label, score} objects, score 1-5 */ ],
  "categories": [
    {
      "id": "cat-1",
      "name": "Category 1",
      "questions": [
        { "id": "q-1-1", "category_id": "cat-1", "text": "...", "options": [...] },
        { "id": "q-1-2", "category_id": "cat-1", "text": "..." }
        /* questions without "options" inherit default_options (5 labels -> scores 1-5) */
      ]
    }
    /* ... 6 categories total: cat-1..cat-6, question counts 9/9/9/9/8/8 = 52 total,
       verified by direct parse this research session */
  ]
}
```
No weight field exists anywhere in this structure (SCOR-02 — nothing to strip, the config was never capable of expressing per-question/category weight).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| GoRules ZEN JDM decision table (`mami-scoring.json`) evaluated per-answer via `async_evaluate`, MoSCoW severity (CRITICAL/NON_CRITICAL) findings | Equal-weight arithmetic mean per category, computed in pure Python/SQL, no external rules engine | This phase (14) | Removes an entire native-extension dependency (`zen-engine`, Rust-backed wheels) and its filesystem-loader indirection; scoring becomes a single aggregation query, testable without any decision-table fixtures |
| 4×3 MAMI category/dimension/topic heatmap structure (`mami-framework.json`) | 6-category flat dimension list (`dssc-questionnaire.json`) | Phase 13 (config), Phase 14 (removal of the old structure's last consumers) | The old structural config is now fully unused after this phase — nothing reads `mami-framework.json` once `load_mami_config()`/`admin.py`'s topic-structure code are gone |

**Deprecated/outdated:**
- `zen-engine` / GoRules ZEN Engine: fully removed this phase, not deprecated-in-place.
- `config/mami-framework.json`, `config/scoring/mami-scoring.json`: deleted, no replacement (their successor, `dssc-questionnaire.json`, already existed since Phase 13).
- `_DEGRADED_SCORING_BANNER_HTML` / `_inject_degraded_banner`: removed; its premise ("scoring not implemented yet") becomes false once real dimension scores exist server-side, even though the HTML template doesn't render them yet this phase (D-05a).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `uv remove zen-engine` (rather than editing `pyproject.toml` by hand and running `uv lock`) is the correct, minimal command for this repo's uv 0.11.29 — verified by reading the installed `uv --version` and the existing `pyproject.toml`/`uv.lock` entries, but the actual removal has not been executed in this research session | Code Examples | Low — if `uv remove` behaves unexpectedly (e.g. leaves a stale lock entry), `uv lock` as a follow-up command is a safe, well-known fallback the planner can add as a verification step |
| A2 | The Docker image's Python 3.13 pin is unrelated to `zen-engine` specifically and safe to leave untouched (Pitfall 5) | Common Pitfalls | Low — worst case, an unverified assumption that another dependency also needs cp313; this phase deliberately recommends NOT touching the pin, so the risk is inert unless a future phase changes it without re-verifying |

**If this table is empty:** N/A — two low-risk assumptions logged above; both are about follow-up/fallback safety nets, not about the core removal-and-replace mechanics, which are all directly verified via `Read`/`grep` against this repository this session.

## Open Questions

1. **Should `assert_assessment_complete()` live in `dimension_scoring.py` or a separate module?**
   - What we know: D-03 only names the scoring computation itself as the new service; the completion gate is a related but logically separate concern (SCOR-04 vs SCOR-01/02).
   - What's unclear: Whether the planner should colocate both in one file (simpler, one new file total) or split them (cleaner separation, matches D-03's narrower "computing per-category scores" framing).
   - Recommendation: Colocate in the same new service module — both operate on the same `(session, initiative_id/assessment_id, config)` inputs, and D-03 already grants naming discretion; a single file keeps the five call sites' imports simple (one `from app.services.dimension_scoring import assert_assessment_complete, compute_dimension_scores` line).

2. **Exact field name for the completion-gate 422 detail message.**
   - What we know: D-07 gives an example ("Questionnaire not fully answered") but doesn't lock exact wording; the existing precedent in `reports.py` uses "No answers found. Please complete the questionnaire first." for the zero-answers case.
   - What's unclear: Whether the plan should reuse identical wording across all five endpoints (simplest, matches D-07's literal example) or differentiate "no assessment exists yet" vs "assessment exists but incomplete."
   - Recommendation: Use one identical message across all five endpoints for both sub-cases (no assessment / incomplete assessment) — SCOR-04 doesn't require the caller to distinguish these, and a single message keeps `assert_assessment_complete()`'s contract simple (see Pattern 2's example, which already does this).

## Environment Availability

No new external dependencies, services, or tools are introduced this phase. Existing environment prerequisites (Docker for Postgres-testcontainer tests, WeasyPrint native libraries for the report-generation tests) are unchanged — see `backend/tests/README.md` and the recurring pre-existing WeasyPrint gap already logged in `.planning/phases/13-.../deferred-items.md` (macOS-local-only, CI unaffected). This phase's own test changes (deleting `test_scoring_regression.py`/`test_scoring_perf.py`, editing `test_reports.py`/`test_report_generator.py`/`test_admin.py`/`test_health.py`/`conftest.py`) do not add any new environment requirement.

## Validation Architecture

`.planning/config.json` has no `workflow.nyquist_validation` key — treated as enabled per the default rule.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-xdist (parallel) + pytest-asyncio (auto mode) |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd backend && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` |
| Full suite command | `cd backend && uv run pytest tests/ -n auto -m "not perf" -q` (staging-onward gate per CLAUDE.md) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCOR-01 | `dimension_score = sum/count` per category, 1.0-5.0 range | unit | `pytest tests/services/test_dimension_scoring.py -x` | ❌ Wave 0 (new service, no test file yet) |
| SCOR-02 | No question/category weighting anywhere | unit | Same file — assert two categories with equal answer patterns but different question counts still each average correctly per-category (proves no cross-category weighting) | ❌ Wave 0 |
| SCOR-03 | ZEN/MoSCoW fully removed | static/negative | `grep -rL "zen\|scoring_engine\|mami_config\b" backend/app` (adapt `test_evidence_removed.py`'s AST-walk/substring-scan pattern from Phase 13, per RESEARCH precedent) | ❌ Wave 0 — recommend a `test_zen_removed.py` mirroring `test_evidence_removed.py`'s structure |
| SCOR-04 | 422 on incomplete assessment for all 5 endpoints | integration | `pytest tests/api/test_reports.py tests/api/test_scoring.py -x` | ❌ Wave 0 — `test_scoring.py` does not exist at all today (confirmed by directory listing); `test_reports.py` exists but needs new 422 assertions added |

### Sampling Rate
- **Per task commit:** quick run command above
- **Per wave merge:** full suite command above
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/services/test_dimension_scoring.py` — covers SCOR-01/02, unit tests for `compute_dimension_scores`/`assert_assessment_complete` against the `session` fixture + `make_answer`/`make_assessment` factories (already exist, no factory changes needed)
- [ ] `tests/api/test_scoring.py` — does not exist yet; this phase's D-04 response-shape change to `/score` has zero existing test coverage to adapt (unlike `/report/*`, which `test_reports.py` already covers) — recommend at minimum a happy-path + 422 test here, even though full TEST-01 coverage is explicitly Phase 17's job (D-08's note) — a phase that changes an endpoint's entire response contract with zero test touching that endpoint at all is a real Nyquist gap, not just deferred polish
- [ ] Optional: `tests/test_zen_removed.py` mirroring Phase 13's `test_evidence_removed.py` AST-walk pattern, to lock in SCOR-03 as a regression-proof static check rather than relying on "ruff/mypy happen to catch orphaned imports"

*(Note: full new-scoring-logic test coverage is explicitly out of scope per D-08 — Phase 17 owns it. The two gaps flagged above as non-optional are the minimum needed so this phase's own response-shape changes aren't shipped completely unverified by an automated test, which is a lower bar than full TEST-01 coverage.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no (unchanged) | Existing JWT bearer auth via `get_current_user`, untouched this phase |
| V3 Session Management | no (unchanged) | N/A |
| V4 Access Control | yes (unchanged pattern, re-verify) | All five endpoints already re-derive ownership via `initiative.user_id != current_user.id` before touching scoring — this phase must preserve that check exactly as-is while removing the `zen`/`mami_config` `Depends()` params; do not accidentally reorder checks so a 422 (completion gate) fires before the 403/404 ownership check |
| V5 Input Validation | yes | `score` is already DB-CHECK-constrained 1-5 (Phase 13 migration) and Pydantic-`Field(ge=1, le=5)`-validated (`AnswerCreate`); the new dimension-scoring service reads already-validated data, introduces no new user input surface |
| V6 Cryptography | no | N/A — no crypto involved |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Ownership-check bypass via endpoint reordering | Elevation of Privilege | Keep the existing `if initiative.user_id != current_user.id: raise 403` check as the FIRST gate in every adapted endpoint, before the new `assert_assessment_complete()` 422 gate — an attacker probing for initiative existence/completeness state must not be able to distinguish "not yours" from "not complete" ordering-wise in a way that leaks whether an initiative_id exists for another user (both currently correctly 403/404 before any scoring logic runs; preserve that order) |
| Information disclosure via error message specificity | Information Disclosure | Keep the 422 detail message generic ("Questionnaire not fully answered") — do not leak which specific `question_id`s are missing in the HTTP response body, since that's unnecessary detail for a same-owner caller and irrelevant/noisy for anyone else (though ownership is already checked first) |

## Sources

### Primary (HIGH confidence — direct Read/grep of this repository, this session)
- `backend/app/main.py`, `backend/app/core/deps.py`, `backend/app/services/scoring_engine.py`, `backend/app/services/mami_config.py` — full lifespan/dependency/service call graph
- `backend/app/api/v1/scoring.py`, `backend/app/api/v1/reports.py`, `backend/app/api/v1/admin.py`, `backend/app/services/report_generator.py` — every endpoint and builder function this phase touches
- `backend/app/models/assessment.py`, `backend/app/models/questionnaire.py`, `backend/app/api/v1/questionnaire.py` — exact schema and existing query idioms the new service should match
- `backend/app/templates/report.html` — confirmed exact Jinja2 context-variable dependencies (Pitfall 1)
- `config/dssc-questionnaire.json` — parsed directly: 6 categories, 9/9/9/9/8/8 questions, 52 total, no weight field
- `backend/pyproject.toml`, `backend/uv.lock` — confirmed exact package name `zen-engine==0.51.0`, confirmed `uv --version` 0.11.29 installed
- `backend/Dockerfile` — confirmed the stale zen-engine comment (Pitfall 5)
- `backend/tests/conftest.py`, `backend/tests/test_health.py`, `backend/tests/api/test_reports.py`, `backend/tests/api/test_admin.py`, `backend/tests/services/test_report_generator.py`, `backend/tests/benchmark/test_scoring_regression.py`, `backend/tests/perf/test_scoring_perf.py`, `backend/tests/factories.py` — full grep + read of every test file referencing `zen`/`scoring_engine`/`mami_config`/`FindingRead`/matrix/topic_structure, confirming CONTEXT.md's list plus the two additions (`test_admin.py`, the `_build_topic_structure` import in `admin.py`) not in that list
- `docs/api/openapi.json` — confirmed `FindingRead`/`ScoreResponse`/`AdminHeatmapCell`/`AdminHeatmapResponse` schema components exist and will need regeneration; confirmed `/report/data` endpoints currently have no declared response schema (plain dict return)
- `docs/security/*.json` — confirmed these SBOM files currently reference `zen`; regeneration happens automatically in CI per CLAUDE.md, no manual action needed this phase
- `.planning/phases/14-scoring-engine-replacement/14-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — user decisions, requirement text, project history

### Secondary (MEDIUM confidence)
None — no external documentation lookups were needed this phase; every finding is repository-internal.

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — no new stack introduced
- Architecture: HIGH — every file/line cited above was read directly this session
- Pitfalls: HIGH — all six pitfalls are grep/read-verified against actual current code (report.html's template vars, scoring.py's missing 422, test_admin.py's assertions, zen-engine's real package name, the Dockerfile comment, the empty-directory git behavior), not inferred from general FastAPI/Python knowledge

**Research date:** 2026-07-24
**Valid until:** Until this phase executes (no time-decay risk — findings are internal-repo facts, not external ecosystem state)
