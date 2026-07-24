# Phase 14: Scoring Engine Replacement - Pattern Map

**Mapped:** 2026-07-24
**Files analyzed:** 12 (new/modified)
**Analogs found:** 12 / 12 (all matches are same-repo, pre-existing code — this phase edits/deletes existing files plus adds one new service and one new test file; there is no external codebase to borrow from)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/services/dimension_scoring.py` (NEW) | service | CRUD (aggregation read) | `backend/app/api/v1/questionnaire.py` (`valid_categories_by_question` config-comprehension idiom, lines 138-142) + `backend/app/api/v1/admin.py` heatmap raw-SQL GROUP BY | role-match (idiom-match, not a literal service analog since none existed) |
| `backend/app/api/v1/scoring.py` (MODIFIED) | controller/route | request-response | itself, pre-edit (same file) | exact (in-place edit) |
| `backend/app/api/v1/reports.py` (MODIFIED, 4 endpoints) | controller/route | request-response | itself, pre-edit (same file) | exact (in-place edit) |
| `backend/app/services/report_generator.py` (MODIFIED) | service | transform | itself, pre-edit (same file) | exact (in-place edit) |
| `backend/app/api/v1/admin.py` (`/heatmap`, MODIFIED) | controller/route | request-response | itself, pre-edit (same file) | exact (in-place edit) |
| `backend/app/services/mami_config.py` (MODIFIED — 2 functions removed) | utility/config-loader | file-I/O | itself, pre-edit; surviving `load_dssc_questionnaire_config` (lines 32-36) is the pattern to preserve | exact |
| `backend/app/core/deps.py` (MODIFIED — 2 deps removed) | middleware/DI | request-response | surviving `get_dssc_questionnaire_config` (line 62-67) | exact |
| `backend/app/main.py` (MODIFIED — lifespan wiring removed) | config | event-driven (startup) | surviving `app.state.dssc_questionnaire_config` wiring (line 37) | exact |
| `backend/pyproject.toml` / `uv.lock` (MODIFIED) | config | — | N/A (dependency manifest edit, not a code pattern) | n/a |
| `backend/tests/services/test_dimension_scoring.py` (NEW) | test | CRUD (unit) | `backend/tests/services/test_report_generator.py` (fixture/session style) | role-match |
| `backend/tests/api/test_scoring.py` (NEW) | test | request-response (integration) | `backend/tests/api/test_reports.py` (client/session fixtures, ownership + 422 assertions) | exact |
| `backend/tests/api/test_admin.py` (MODIFIED — heatmap test) | test | request-response (integration) | itself, pre-edit (same file) | exact |

## Pattern Assignments

### `backend/app/services/dimension_scoring.py` (NEW service, CRUD)

**Analog:** `backend/app/api/v1/questionnaire.py` lines 138-145 (config-comprehension idiom) + `backend/app/api/v1/admin.py` lines ~365-380 (raw aggregation over `questionnaire_answer` joined through `assessment`)

**Config-as-source-of-truth idiom to copy** (`questionnaire.py:138-142`):
```python
valid_categories_by_question = {
    q["id"]: q["category_id"]
    for cat in config.get("categories", [])
    for q in cat.get("questions", [])
}
```
Use the same double-comprehension shape to derive `_full_question_ids(config)` and `_category_question_counts(config)` — never hardcode 52 or 9/9/9/9/8/8 (RESEARCH "Don't Hand-Roll").

**Aggregation-over-assessment-join idiom to copy** (`admin.py`'s heatmap SQL, ~lines 365-380):
```python
agg_result = session.execute(
    text(f"""
    SELECT qa.category_id, qa.score, COUNT(*) as cnt
    FROM questionnaire_answer qa
    JOIN assessment a ON a.id = qa.assessment_id
    JOIN initiative i ON i.id = a.initiative_id
    WHERE i.status = 'submitted' {type_filter}
    GROUP BY qa.category_id, qa.score
"""),
    params,
)
```
Prefer the SQLModel/ORM equivalent (`select(QuestionnaireAnswer.category_id, func.sum(...)).group_by(...)`) shown fully in RESEARCH.md's "Pattern 1: Dimension Score Computation" — that exact function body (`compute_dimension_scores`, `_full_question_ids`, `_category_question_counts`, `_category_names`, `get_current_assessment`) and "Pattern 2: Completion Gate" (`assert_assessment_complete`) are pre-written, verified-against-this-repo code in RESEARCH.md lines 162-260 — copy them near-verbatim rather than re-deriving.

**Current-assessment lookup idiom to copy** (mirrors `questionnaire.py`'s `get_answers()`/draft-assessment lookup — same file, not separately excerpted since RESEARCH.md's `get_current_assessment` already matches it):
```python
def get_current_assessment(session: Session, initiative_id: int) -> Assessment | None:
    return session.exec(
        select(Assessment)
        .where(
            Assessment.initiative_id == initiative_id,
            Assessment.status == AssessmentStatus.draft,
        )
        .order_by(Assessment.created_at.desc())
    ).first()
```

**Error handling / 422 pattern to copy** (existing precedent, `reports.py` lines 326-329, `download_report_pdf`):
```python
if not answers:
    raise HTTPException(
        status_code=422, detail="No answers found. Please complete the questionnaire first."
    )
```
Reuse this exact status code and message style for `assert_assessment_complete()`'s new 422 (D-07 — use one identical message across all five endpoints per RESEARCH's Open Question 2 recommendation).

---

### `backend/app/api/v1/scoring.py` (controller, request-response) — MODIFIED IN PLACE

**Analog:** itself, current version (full file read above, 84 lines)

**Imports to remove:**
```python
import zen
from app.core.deps import get_current_user, get_mami_config, get_zen_engine
from app.services.scoring_engine import score_all_answers
```
**Imports to add:**
```python
from app.core.deps import get_current_user, get_dssc_questionnaire_config
from app.services.dimension_scoring import assert_assessment_complete, compute_dimension_scores
```

**Ownership-check pattern to preserve exactly** (lines 41-45 — keep as the FIRST gate, per RESEARCH's security section, before the new 422 gate):
```python
initiative = session.get(Initiative, initiative_id)
if not initiative:
    raise HTTPException(status_code=404, detail="Initiative not found")
if initiative.user_id != current_user.id:
    raise HTTPException(status_code=403, detail="Not your initiative")
```

**Response model to replace** (drop `FindingRead`, `severity`, `critical_count`/`non_critical_count`; new shape per D-04):
```python
class DimensionScore(BaseModel):
    category_id: str
    name: str
    score: float


class ScoreResponse(BaseModel):
    initiative_id: int
    dimension_scores: list[DimensionScore]
```

**Core pattern (route body)** — replace lines 47-83 (answer-loading + `score_all_answers` call + findings aggregation) with:
```python
assessment = assert_assessment_complete(session, initiative_id, config)
scores = compute_dimension_scores(session, assessment.id, config)
return ScoreResponse(
    initiative_id=initiative_id,
    dimension_scores=[DimensionScore(**s) for s in scores],
)
```
Route signature drops `engine`/`mami_config` params, adds `config: dict = Depends(get_dssc_questionnaire_config)` (mirrors `questionnaire.py`'s existing `config: dict = Depends(get_dssc_questionnaire_config)` param usage).

---

### `backend/app/api/v1/reports.py` (controller, request-response) — MODIFIED IN PLACE, 4 route functions + module-level helpers

**Analog:** itself, current version (full file read above, 395 lines)

**Delete outright** (D-05a): `_DEGRADED_SCORING_BANNER_HTML` (lines 65-73), `_inject_degraded_banner` (lines 76-83), `_degraded_scoring_inputs` (lines 44-57), the `import zen` (line 8), `score_all_answers` import (line 23), `get_mami_config`/`get_zen_engine` import (line 15).

**Keep unchanged:** `_get_answers_for_initiative` (lines 31-41), `_initiative_dict` (lines 86-95), `_send_report_email` (lines 98-135) — none of these touch ZEN/mami_config.

**Ownership-check + 404 pattern to preserve exactly in every route** (e.g. lines 152-154):
```python
initiative = session.get(Initiative, initiative_id)
if not initiative or initiative.user_id != current_user.id:
    raise HTTPException(status_code=404, detail="Initiative not found")
```

**Existing 422 precedent to extend to all 5 endpoints** (currently only on `download_report_pdf`/`mail_report`, lines 326-329):
```python
if not answers:
    raise HTTPException(
        status_code=422, detail="No answers found. Please complete the questionnaire first."
    )
```
Replace with a call to the new shared gate: `assessment = assert_assessment_complete(session, initiative_id, config)` placed immediately after the ownership check, before any `ComplianceReport` lookup logic (per RESEARCH's ordering guidance — 422 completion gate must not fire before the 403/404 ownership check, but should fire before endpoint-specific report-existence 404s like `get_report_data_endpoint`'s "No report generated yet").

**Core pattern for `/report/data` (both GET+POST) — new `dimension_scores` field (D-05):**
```python
data = generate_report_data(initiative=initiative)
data["dimension_scores"] = compute_dimension_scores(session, assessment.id, config)
return data
```
(No more `data["degraded"] = True` — that was the Phase 13→14 interim flag being removed along with `_degraded_scoring_inputs`.)

**Jinja2 context literal-empty pattern (Pitfall 1 — required, non-obvious):** `generate_html_report()`'s simplified context dict (called from `generate_report`/`download_report_pdf`/`mail_report`) MUST still pass:
```python
context = {
    "initiative": initiative,
    "generated_at": generated_at,
    "heatmap_rows": {},
    "not_yet_recommendations": [],
}
```
so `report.html`'s unchanged `heatmap_rows.get(...)` / `{% for rec in not_yet_recommendations %}` calls don't raise Jinja2 `UndefinedError`.

---

### `backend/app/services/report_generator.py` (service, transform) — MODIFIED IN PLACE

**Analog:** itself, current version (313 lines)

**Delete outright** (D-01a): `_RECOMMENDATIONS` dict (lines 9-37), `_build_matrix` (92-123), `_build_findings_detail` (126-164), `_build_topic_structure` (167-192), `_aggregate_cell` (195-207), `_build_heatmap_rows` (210-226), `_build_not_yet_recommendations` (229-249), `_suggest_next_steps` (301-313), `_ANSWER_LABEL_MAP` (39-43, only consumed by `generate_report_data`'s deleted matrix-building).

**Keep and simplify** — `generate_html_report` (lines 55-89): drop the `answers`/`findings`/`mami_config` params (no longer needed once matrix-building is gone), keep the Jinja2 env/template-load lines 72-73, replace lines 78-88 with the literal-empty context shown above.

**Keep and simplify** — `generate_report_data` (lines 252-298): drop `answers`/`findings`/`mami_config` params, keep the `initiative_id`/`initiative_name` dual-type resolution (lines 271-277 — ORM-object-or-dict pattern, still useful), drop the `matrix`/`topic_structure`/`answers` list keys entirely (not present-but-empty per D-01a), return only `{"initiative": {...}}` — the caller (`reports.py`) adds `dimension_scores` on top.

**Reusable dual-type resolution pattern to keep verbatim** (lines 271-277):
```python
if hasattr(initiative, "id"):
    initiative_id = str(initiative.id)
    initiative_name = initiative.name
else:
    initiative_id = str(initiative.get("id", ""))
    initiative_name = initiative.get("name", "")
```

---

### `backend/app/api/v1/admin.py` (`/heatmap`, controller) — MODIFIED IN PLACE

**Analog:** itself, current version (`get_admin_heatmap`, full body read above)

**Delete:** `from app.services.report_generator import _build_topic_structure` (module-level import, line 23 — orphaned import once that function is deleted, per RESEARCH Pitfall 3), the entire aggregation/matrix-building body of `get_admin_heatmap` (the `type_filter`/`agg_result`/`counts`/`code_lookup`/`dimensions`/`matrix` construction), `AdminHeatmapResponse.matrix`/`.topic_structure` fields.

**Simplified response model (D-01b):**
```python
class AdminHeatmapResponse(BaseModel):
    degraded: bool = True
    cells: list[dict] = []
```

**Simplified route body:**
```python
@router.get("/heatmap", response_model=AdminHeatmapResponse)
def get_admin_heatmap(
    request: Request,
    type: str | None = None,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """Phase 16 (ADMN-01) rebuilds this endpoint against the new 6-category
    dimension-score model. This is a fixed, deliberately trivial degraded
    response until then (D-01b) — no topic-structure-building logic survives."""
    return AdminHeatmapResponse(degraded=True, cells=[])
```
Note: keep the existing `degraded: bool = True` field name/semantics — RESEARCH explicitly says "The `AdminHeatmapResponse.degraded` flag itself is kept... just no longer backed by dead structure-building logic."

---

### `backend/app/services/mami_config.py` (utility, file-I/O) — MODIFIED IN PLACE

**Analog:** itself; surviving function `load_dssc_questionnaire_config` (lines 32-36) is the pattern for what remains:
```python
def load_dssc_questionnaire_config() -> dict:
    """Load config/dssc-questionnaire.json. Single universal 52-question /
    6-category config, no participant_type key (D-10, QSTN-04)."""
    path = CONFIG_DIR / "dssc-questionnaire.json"
    return json.loads(path.read_text())
```
**Delete:** `load_mami_config` (lines 11-14), `get_scoring_dir` (lines 39-41). Keep `load_questionnaire_config`/`load_questionnaire_configs` (legacy loaders, explicitly out of this phase's boundary per CONTEXT.md).

---

### `backend/app/core/deps.py` (middleware/DI) — MODIFIED IN PLACE

**Analog:** itself; surviving pattern `get_dssc_questionnaire_config` (line 62-67, exact body not re-quoted here — already the template every other `get_*_config` dependency in this file follows):
```python
def get_dssc_questionnaire_config(request: Request) -> dict:
    return request.app.state.dssc_questionnaire_config
```
**Delete:** `import zen` (line 1), `get_zen_engine` (lines 42-45), `get_mami_config` (lines 47-49).

---

### `backend/app/main.py` (config, startup event-driven) — MODIFIED IN PLACE

**Analog:** itself; surviving pattern (line 37):
```python
app.state.dssc_questionnaire_config = load_dssc_questionnaire_config()
```
**Delete:** `import zen` (line 3), `app.state.mami_config = load_mami_config()` (line ~28), the `scoring_dir`/`loader`/`app.state.zen_engine = zen.ZenEngine(...)` block (lines ~38-44), `load_mami_config`/`get_scoring_dir` from the `mami_config` import block (keep `load_dssc_questionnaire_config` and other legacy loaders).

---

### `backend/tests/services/test_dimension_scoring.py` (NEW test, unit)

**Analog:** `backend/tests/services/test_report_generator.py` — same fixture style (session/factories, no HTTP client needed for a pure-service unit test).

**Pattern:** construct `Assessment` + `QuestionnaireAnswer` rows via existing `factories.py` helpers (`make_assessment`/`make_answer` — confirmed pre-existing per RESEARCH's Wave 0 Gaps section), call `compute_dimension_scores`/`assert_assessment_complete` directly against the `session` fixture, assert:
- SCOR-01: `score == sum/count`, range 1.0-5.0
- SCOR-02: two categories with equal per-answer values but different question counts still average correctly per-category (proves no cross-category weighting)
- `assert_assessment_complete` raises `HTTPException(422)` when answers are missing, returns the `Assessment` when complete

---

### `backend/tests/api/test_scoring.py` (NEW test, integration)

**Analog:** `backend/tests/api/test_reports.py` — copy its `client`/`admin_client`/`user_client` fixture usage and ownership/422 assertion style.

**Pattern to copy** (mirrors `test_reports.py`'s existing structure — same fixtures, same assertion idiom):
```python
def test_score_initiative_requires_ownership(client, ...):
    ...
    resp = client.post(f"/api/v1/initiatives/{other_users_initiative_id}/score")
    assert resp.status_code == 403

def test_score_initiative_422_when_incomplete(client, ...):
    resp = client.post(f"/api/v1/initiatives/{initiative_id}/score")
    assert resp.status_code == 422

def test_score_initiative_returns_dimension_scores(client, ...):
    # answer all 52 questions first via PUT /questionnaire/.../answers/{qid}
    resp = client.post(f"/api/v1/initiatives/{initiative_id}/score")
    assert resp.status_code == 200
    body = resp.json()
    assert "dimension_scores" in body
    assert all(1.0 <= d["score"] <= 5.0 for d in body["dimension_scores"])
```

---

### `backend/tests/api/test_admin.py` (MODIFIED — heatmap test)

**Analog:** itself, current version — `test_admin_heatmap_reflects_submitted_initiatives` (line ~209-221) currently asserts `assert "matrix" in body` / `assert "topic_structure" in body`.

**Change to:**
```python
assert body["degraded"] is True
assert body["cells"] == []
```
(or whatever exact key names D-01b's plan settles on — keep in sync with the `AdminHeatmapResponse` model change in `admin.py`).

## Shared Patterns

### Ownership check (V4 access control) — apply to `scoring.py` and all 4 `reports.py` routes
**Source:** `reports.py` lines 152-154 / `scoring.py` lines 41-45 (two equivalent forms already in the codebase)
```python
initiative = session.get(Initiative, initiative_id)
if not initiative or initiative.user_id != current_user.id:
    raise HTTPException(status_code=404, detail="Initiative not found")
```
**Rule:** this check must run before `assert_assessment_complete()`'s new 422 gate in every route (RESEARCH security section — don't let ordering leak "not yours" vs "not complete" to an attacker).

### Completion gate (SCOR-04) — apply to `scoring.py` + all 4 `reports.py` routes
**Source:** new `assert_assessment_complete()` in `dimension_scoring.py` (RESEARCH.md Pattern 2, lines 239-259) — single shared function, one identical 422 message across all five endpoints (RESEARCH Open Question 2 recommendation):
```python
raise HTTPException(status_code=422, detail="Questionnaire not fully answered")
```

### Config-as-source-of-truth idiom — apply to `dimension_scoring.py`
**Source:** `questionnaire.py` lines 138-142 (`valid_categories_by_question` comprehension) — never hardcode category/question counts; always derive from `config["categories"]`/`config["categories"][*]["questions"]`.

### Dependency injection via `app.state` — apply to `main.py`/`deps.py` (no new pattern needed)
**Source:** `get_dssc_questionnaire_config` (`deps.py` line 62-67) is the template every remaining config dependency follows; the new scoring service needs no new singleton (pure computation over DB rows + this already-cached config).

## No Analog Found

None — every touched file is an in-place edit or deletion of existing code, and the one new service (`dimension_scoring.py`) has strong idiom-level analogs (`questionnaire.py`'s config-comprehension pattern, `admin.py`'s aggregation-over-join pattern) plus a fully pre-written reference implementation already verified against this repo in RESEARCH.md.

## Metadata

**Analog search scope:** `backend/app/api/v1/`, `backend/app/services/`, `backend/app/core/`, `backend/app/main.py`, `backend/tests/`
**Files scanned:** 12 target files + `questionnaire.py` (config idiom source) + `admin.py` (aggregation idiom source), all read directly this session
**Pattern extraction date:** 2026-07-24
