# Phase 16: Report Data Contract, Dual Visualization & Admin Aggregation - Pattern Map

**Mapped:** 2026-07-26
**Files analyzed:** 11
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `backend/app/services/report_generator.py` (rewrite) | service | transform | itself (existing `generate_report_data`/`generate_html_report`) + `backend/app/services/dimension_scoring.py` (`compute_dimension_scores`) | exact (extend in place) |
| `backend/app/services/dimension_scoring.py` (add resolver helper) | service | CRUD | `list_submitted_assessments`/`get_current_assessment` in same file | exact |
| `backend/app/services/admin_aggregation.py` (NEW) | service | batch/CRUD | `backend/app/api/v1/admin.py`'s `list_initiatives` raw-SQL join pattern | role-match |
| `backend/app/schemas/report.py` (NEW) | model (pydantic schema) | transform | `backend/app/schemas/assessment.py` (`AssessmentSummary`) | exact |
| `backend/app/api/v1/reports.py` (rewrite) | controller/route | request-response | itself (existing 4 endpoints) | exact (rewrite in place) |
| `backend/app/api/v1/admin.py` (`/heatmap` rewrite) | controller/route | request-response | `GET /admin/initiatives` in same file (raw-SQL join + response model) | exact |
| `backend/app/templates/report.html` (rewrite) | template | transform | itself (existing Jinja2 template) + `generate_html_report`'s render context | exact |
| `config/dssc-questionnaire.json` (add `maturity_bands` key) | config | transform | existing `categories` top-level key in same file | exact |
| `frontend/src/routes/_app/report.tsx` (rewrite) | route/component | request-response | itself (existing `ReportPage`/`HeatmapMatrix`) | exact (rewrite in place) |
| `frontend/src/routes/_app/admin.heatmap.tsx` (rewrite) | route/component | request-response | itself (existing `AdminHeatmapPage`/`HeatmapGrid`) + `frontend/src/routes/_app/assessments.tsx` (antd `Table` + pagination precedent) | exact / role-match |
| `frontend/src/lib/reports.ts` (extend) | utility (API client) | request-response | `frontend/src/lib/assessments.ts` (`fetchAssessmentHistory` typed-fetch pattern) | role-match |

## Pattern Assignments

### `backend/app/services/dimension_scoring.py` (add: submitted-assessment-by-id resolver)

**Analog:** same file, `list_submitted_assessments` (L62-82) and `get_current_assessment` (L43-59)

**Core pattern to copy** (L62-82):
```python
def list_submitted_assessments(session: Session, initiative_id: int) -> list[Assessment]:
    """All SUBMITTED Assessments for this initiative, ordered by version
    (HIST-02)."""
    return list(
        session.exec(
            select(Assessment)
            .where(
                Assessment.initiative_id == initiative_id,
                Assessment.status == AssessmentStatus.submitted,
            )
            .order_by(Assessment.version)
        ).all()
    )
```

**New helper to add (D-04, RESEARCH Pitfall 1):** `resolve_report_assessment(session, initiative_id, assessment_id, config) -> Assessment` — mirrors this exact `select(Assessment).where(...)` shape but adds `Assessment.id == assessment_id` when given, else picks `order_by(Assessment.version.desc()).first()`; always filters `status == AssessmentStatus.submitted` (never `assert_assessment_complete`/`get_current_assessment`, which are draft-scoped — RESEARCH Pitfall 1 names this explicitly). Raise `HTTPException(404, "Assessment not found")` on no match, matching the file's existing `HTTPException` import and style (L16, L98-99).

**Error handling pattern** (L98-99, `assert_assessment_complete`):
```python
if assessment is None:
    raise HTTPException(status_code=422, detail="Questionnaire not fully answered")
```
Reuse this "generic detail, no enumeration" idiom but with `404` for report-not-found, matching V4 access-control guidance (never leak existence via 403).

---

### `backend/app/services/report_generator.py` (rewrite: `build_report_contract`, `generate_radar_svg`, `build_priority_list`, `get_maturity_band`)

**Analog:** existing `generate_report_data` (L52-76) for the "assemble a dict from an ORM object, support both ORM and plain-dict input" idiom; `compute_dimension_scores` in `dimension_scoring.py` (L114-149) for the "derive structure from config, never hardcode" idiom this phase's `build_priority_list`/`generate_radar_svg` must follow.

**Imports pattern** (existing file, L13-16):
```python
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
```
Add `import math` for radar trigonometry (RESEARCH Pattern 2) — stdlib only, no new dependency (D-01).

**Core pattern — config-driven, never hardcoded** (from `dimension_scoring.py` L32-40):
```python
def _category_question_counts(config: dict) -> dict[str, int]:
    return {cat["id"]: len(cat["questions"]) for cat in config["categories"]}

def _category_names(config: dict) -> dict[str, str]:
    return {cat["id"]: cat["name"] for cat in config["categories"]}
```
The new `get_maturity_band(score, bands)` must read `config["maturity_bands"]` the same way — never a hardcoded inequality chain (RPRT-03's literal deliverable, per RESEARCH Pattern 1).

**Existing render-context shape to extend** (L43-49, `generate_html_report`):
```python
context = {
    "initiative": initiative,
    "generated_at": generated_at,
    "heatmap_rows": {},
    "not_yet_recommendations": [],
}
return template.render(**context)
```
Rewrite to drop the two stale stub keys and add `dimension_scores`, `priority_list`, `radar_chart_svg`, `maturity_bands` — the same keys returned by the new `build_report_contract()` dict, so `report.html`'s context and `/report/data`'s JSON response are populated from one shared dict (D-02/RPRT-04), not two separately-built payloads.

**ORM-or-dict flexibility idiom to reuse** (L63-68, `generate_report_data`):
```python
if hasattr(initiative, "id"):
    initiative_id = str(initiative.id)
    initiative_name = initiative.name
else:
    initiative_id = str(initiative.get("id", ""))
    initiative_name = initiative.get("name", "")
```

---

### `backend/app/schemas/report.py` (NEW — `ReportContract`/`PriorityListItem`/`MaturityBand`)

**Analog:** `backend/app/schemas/assessment.py` (full file, 17 lines)

**Full pattern to copy** (this file establishes the exact convention: plain `BaseModel`, no ORM config, hand-assembled in the route not returned directly from an ORM instance):
```python
from pydantic import BaseModel


class AssessmentSummary(BaseModel):
    id: int
    version: int
    submitted_at: str
    overall_average: float
    dimension_scores: list[dict]
```
New schemas follow this identical shape/docstring convention: `class MaturityBand(BaseModel): id: str; label: str; min: float; max: float; color: str`, `class PriorityListItem(BaseModel): category_id: str; name: str; score: float; band_id: str; band_label: str; band_color: str`, `class ReportContract(BaseModel): assessment_id: int; version: int; initiative: dict; dimension_scores: list[dict]; priority_list: list[PriorityListItem]; radar_chart_svg: str; maturity_bands: list[MaturityBand]`.

---

### `backend/app/api/v1/reports.py` (rewrite all 4 endpoints + drop `ComplianceReport` upsert)

**Analog:** itself — existing endpoints already establish the ownership-check + `Depends` idiom; only the assessment-resolution and persistence pieces change.

**Imports pattern** (L1-22, keep this shape, drop `pg_insert`/`ComplianceReport` per RESEARCH Pitfall 2):
```python
import logging
from collections.abc import Sequence
from datetime import datetime

import resend
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.core.config import settings
from app.core.deps import get_current_user, get_dssc_questionnaire_config
from app.db.session import get_session
from app.models.initiative import Initiative
from app.models.user import User
from app.services.dimension_scoring import resolve_report_assessment  # NEW helper
from app.services.report_generator import build_report_contract  # NEW function
```

**Ownership pattern to keep verbatim** (repeated 5x, e.g. L113-115):
```python
initiative = session.get(Initiative, initiative_id)
if not initiative or initiative.user_id != current_user.id:
    raise HTTPException(status_code=404, detail="Initiative not found")
```
Extend per RESEARCH's V4/admin-bypass guidance: `if not initiative or (initiative.user_id != current_user.id and current_user.role != "ADMIN"): raise HTTPException(404, ...)` for the D-07 admin per-initiative report links, mirroring how `admin.py` re-derives its own authorization rather than reusing a second route.

**Assessment-resolution replacement (D-03/D-04, RESEARCH Pitfall 1):** every `assert_assessment_complete(session, initiative_id, config)` call (L117, L171, L194, L217, L246, L277) must be replaced with `resolve_report_assessment(session, initiative_id, assessment_id, config)`, accepting a new `assessment_id: int | None = None` query param on each endpoint.

**PDF pattern to keep verbatim** (L231-257, `download_report_pdf`):
```python
from weasyprint import HTML as WeasyHTML
...
pdf_bytes: bytes = WeasyHTML(string=html_content).write_pdf()
return Response(
    content=pdf_bytes,
    media_type="application/pdf",
    headers={"Content-Disposition": "attachment; filename=MAMI-Interoperability-Report.pdf"},
)
```

**Mail pattern to keep verbatim** (L60-97, `_send_report_email` + `background_tasks.add_task` at L284-289) — no change needed beyond passing the new contract-derived `html_content`.

**Deleted pattern (do not carry forward):** the `pg_insert(ComplianceReport)...on_conflict_do_update(index_elements=["initiative_id"])` upsert (L128-154) — RESEARCH Pitfall 2 confirms this is structurally incompatible with per-version reports; stop writing to `ComplianceReport` for this contract path.

---

### `backend/app/api/v1/admin.py` (`/heatmap` full rebuild, ADMN-01)

**Analog:** `list_initiatives` in the same file (L174-209) — raw-SQL join + `response_model` pattern to adapt for "latest submitted per initiative."

**Imports pattern already present** (L1-22): `from sqlalchemy import text`, `from sqlmodel import Session, select`, `from app.core.deps import require_admin` — reuse as-is.

**Core raw-SQL join pattern to adapt** (L183-195, `list_initiatives`):
```python
result = session.execute(
    text("""
    SELECT i.id, i.name, i.participant_type, i.status, i.created_at,
           u.email AS user_email,
           COUNT(qa.id) AS answer_count
    FROM initiative i
    LEFT JOIN "user" u ON u.id = i.user_id
    LEFT JOIN assessment a ON a.initiative_id = i.id
    LEFT JOIN questionnaire_answer qa ON qa.assessment_id = a.id
    GROUP BY i.id, i.name, i.participant_type, i.status, i.created_at, u.email
    ORDER BY i.created_at DESC
""")
)
for row in result.mappings():
    ...
```
Adapt this exact `session.execute(text("..."))` + `.mappings()` idiom for the new query, per RESEARCH Pattern 3 (`LEFT JOIN LATERAL` to get one row per initiative including those with zero submitted assessments, per D-08).

**Response model pattern to follow** (L30-37, `AdminHeatmapResponse` stub — replace entirely):
```python
class AdminHeatmapResponse(BaseModel):
    degraded: bool = True
    cells: list[dict] = []
```
Replace with a real Pydantic model, e.g. `AdminAggregateResponse(BaseModel): org_radar_chart_svg: str | None; org_average_scores: list[dict]; initiatives: list[AdminInitiativeAggregateRow]` where `AdminInitiativeAggregateRow` mirrors `AdminInitiativeRow`'s shape (L54-61) plus `dimension_scores`/`overall_average`/`has_data`/`report_assessment_id`.

**Endpoint pattern to keep** (L324-338, decorator/dependency shape only):
```python
@router.get("/heatmap", response_model=AdminHeatmapResponse)
def get_admin_heatmap(
    request: Request,
    type: str | None = None,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
```
Keep `Depends(require_admin)` and the route path; drop the unused `type`/`request` params (leftover from the deleted DSI/SP heatmap split — this phase's org-wide aggregation is not type-scoped per CONTEXT.md/UI-SPEC).

**Zero-division / empty-aggregate guard (RESEARCH Pitfall 5) — no direct analog exists in this codebase (confirmed via grep, "No existing `band`/`threshold` constant" per CONTEXT.md L76); write as new code**:
```python
included = [row for row in rows if row["dimension_scores"] is not None]
if not included:
    org_radar_chart_svg = None
    org_average_scores = []
else:
    org_average_scores = [
        {"category_id": cat_id, "score": mean(...)}
        for cat_id in ...
    ]
    org_radar_chart_svg = generate_radar_svg(org_average_scores, bands)
```

---

### `config/dssc-questionnaire.json` (add `maturity_bands` top-level key, D-05)

**Analog:** existing `categories` top-level key in the same file (already read by `get_dssc_questionnaire_config()` — no new loader).

**Exact shape to add** (from RESEARCH Code Examples, hex values copied verbatim from `16-UI-SPEC.md` — do not re-derive):
```json
{
  "maturity_bands": [
    { "id": "red",    "label": "Needs attention", "min": 1.0, "max": 2.0, "color": "#d64545" },
    { "id": "orange", "label": "Developing",       "min": 2.0, "max": 3.5, "color": "#e08e2b" },
    { "id": "green",  "label": "Mature",            "min": 3.5, "max": 5.0, "color": "#399e5a" }
  ]
}
```

---

### `frontend/src/routes/_app/report.tsx` (rewrite for radar SVG + priority list)

**Analog:** itself — existing `ReportPage`/fetch-on-mount pattern; card-layout/typography/loading/error precedent to keep, matrix-rendering internals (`HeatmapMatrix`, `MAMI_CODE_TO_REC_ID`, `RECOMMENDATIONS`) to delete outright per RESEARCH ("dead code to delete, not adapt").

**Fetch pattern to keep, retarget to new contract shape + `assessment_id` param** (L432-454):
```typescript
useEffect(() => {
  let cancelled = false;
  api.get<{ id: number; name: string; status: string }>("/initiatives/me")
    .then((res) => {
      if (cancelled) return;
      const id = res.data.id;
      setInitiativeId(id);
      return api.post<ReportData>(`/initiatives/${id}/report/data`, {});
    })
    .then((res) => {
      if (cancelled || !res) return;
      setData(res.data);
    })
    .catch(() => {
      if (!cancelled) setError("Failed to generate report. Make sure you have answered the questionnaire.");
    })
    .finally(() => {
      if (!cancelled) setLoading(false);
    });
  return () => { cancelled = true; };
}, []);
```
Retarget to `GET /initiatives/{id}/report/data?assessment_id=` (reads `assessment_id` from the route's search params per D-04's discretion — Claude's Discretion item) instead of the current `POST`.

**Loading/error/card chrome to keep verbatim** (L521-534, L554-636) — `<Spin size="large" />` centered, `<Alert type="error" showIcon>`, `borderRadius: "16px"`, `boxShadow: "0 2px 12px rgba(6,0,79,0.08)"` card styling, `#06004f`/Rubik typography tokens — all match `16-UI-SPEC.md`'s declared tokens exactly (dominant white card, navy secondary, borderRadiusLG 16px).

**New radar rendering (D-02) — no existing analog, verbatim-render idiom to establish:**
```tsx
<div dangerouslySetInnerHTML={{ __html: data.radar_chart_svg }} />
```
(React 19 equivalent of "render the exact markup as-is" — server-controlled string only, per RESEARCH's XSS note: dimension names/scores are server-config-controlled, never end-user input, so this is safe by construction.)

**Priority list — new plain-list/table analog:** follow `HeatmapMatrix`'s row-rendering CSS-grid idiom (L126-233) simplified to a single-column 6-row list, each row showing `name`, `score.toFixed(2)`, and a colored dot using `band_color`+`band_label` (never re-deriving color from score client-side, per RESEARCH anti-pattern).

**CTA copy to update per UI-SPEC Copywriting Contract** (was L384, "Download results as PDF" → "Download PDF Report").

---

### `frontend/src/routes/_app/admin.heatmap.tsx` (rebuild for org radar + per-initiative table, ADMN-01)

**Analog:** itself for page chrome/auth `beforeLoad` guard (L10-23) — keep verbatim; `frontend/src/routes/_app/assessments.tsx` for the antd `Table` + pagination pattern (D-07's per-initiative table).

**Auth guard pattern to keep verbatim** (L10-23):
```typescript
beforeLoad: async () => {
  try {
    const res = await api.get<{ role: string }>("/auth/me");
    if (res.data.role !== "ADMIN") {
      throw redirect({ to: "/dashboard" });
    }
  } catch (err: unknown) {
    if (err && typeof err === "object" && "to" in err) throw err;
    throw redirect({ to: "/dashboard" });
  }
},
```

**Table + pagination pattern to copy** (`assessments.tsx` L61-89, 213):
```tsx
const versionColumns: ColumnsType<AssessmentSummary> = [
  { title: "Submitted", dataIndex: "submitted_at", key: "submitted_at", render: (v) => v ? new Date(v).toLocaleDateString() : "—" },
  { title: "Version", dataIndex: "version", key: "version", render: (v) => `v${v}` },
  { title: "Overall average", dataIndex: "overall_average", key: "overall_average", render: (v) => v.toFixed(2) },
  { title: "Report", key: "report", render: () => <Link to="/report">View report</Link> },
];
...
<Table columns={versionColumns} dataSource={history} pagination={{ pageSize: 10, showSizeChanger: false }} />
```
Adapt columns to: initiative name (with `ellipsis: true` + `title` tooltip per UI-SPEC long-text row), per-dimension scores, overall average, "No data yet" badge (D-08, conditionally rendered per row), "View report" link to `/report?assessment_id=<row's latest submitted id>`.

**Fetch pattern to simplify** (was DSI/SP dual-tab lazy-fetch, L236-268 — delete the tab split, this phase's aggregation is not type-scoped): keep the single `useEffect` + `api.get(...)` + loading/error state shape from the DSI branch only (L249-255).

**Page chrome to keep verbatim** (L297-322): back-link `<Button>`, `<Title level={1}>` styling — matches UI-SPEC's Display typography token (28px/600, standardized weight, not the legacy 700).

---

### `frontend/src/lib/reports.ts` (extend for the new JSON contract fetch)

**Analog:** `frontend/src/lib/assessments.ts`'s `fetchAssessmentHistory` (referenced by `assessments.tsx` L6, L47 — typed async wrapper around `api.get<T>(...)`)

**Existing pattern in this file to keep** (L8-18, `generateReport`/`getReportUrl`) — keep both untouched (still used by other flows); add a new typed function alongside:
```typescript
export async function generateReport(initiativeId: number): Promise<string> {
  const res = await api.post(`/initiatives/${initiativeId}/report`, null, {
    responseType: "text",
    headers: { Accept: "text/html" },
  });
  return res.data as string;
}
```

**New function to add, following the `fetchAssessmentHistory` typed-fetch shape** (inferred from its usage at `assessments.tsx` L47: `fetchAssessmentHistory(initiative!.id) => Promise<AssessmentSummary[]>`):
```typescript
export interface ReportContract {
  dimension_scores: { category_id: string; name: string; score: number }[];
  priority_list: { category_id: string; name: string; score: number; band_id: string; band_label: string; band_color: string }[];
  radar_chart_svg: string;
  maturity_bands: { id: string; label: string; min: number; max: number; color: string }[];
}

export async function fetchReportData(initiativeId: number, assessmentId?: number): Promise<ReportContract> {
  const res = await api.get<ReportContract>(
    `/initiatives/${initiativeId}/report/data${assessmentId ? `?assessment_id=${assessmentId}` : ""}`
  );
  return res.data;
}
```

## Shared Patterns

### Ownership + 404 (never 403 on existence) — access control
**Source:** `backend/app/api/v1/reports.py`, repeated at L113-115, L167-169, L190-192, L213-215, L242-244, L273-275
**Apply to:** every rewritten `reports.py` endpoint, plus the new `resolve_report_assessment` helper's own 404 on assessment-id mismatch (RESEARCH V4 — never leak existence via 403)
```python
initiative = session.get(Initiative, initiative_id)
if not initiative or initiative.user_id != current_user.id:
    raise HTTPException(status_code=404, detail="Initiative not found")
```

### Config-driven structure, never hardcoded
**Source:** `backend/app/services/dimension_scoring.py` L24-40 (`_full_question_ids`, `_category_question_counts`, `_category_names`)
**Apply to:** `get_maturity_band(score, config["maturity_bands"])`, `build_priority_list`, `generate_radar_svg` — all must derive from `config` dict passed via `Depends(get_dssc_questionnaire_config)`, never a hardcoded band list or category count.

### Raw-SQL admin join with `.mappings()`
**Source:** `backend/app/api/v1/admin.py` L110-154 (`list_users`), L174-209 (`list_initiatives`)
**Apply to:** the new admin aggregation query in `admin_aggregation.py`/`admin.py`'s rewritten `/heatmap` — same `session.execute(text("..."))` + `for row in result.mappings():` idiom, extended to a `LEFT JOIN LATERAL` per RESEARCH Pattern 3.

### Loading/error/card chrome (antd)
**Source:** `frontend/src/routes/_app/report.tsx` L521-534 (loading/error), `frontend/src/routes/_app/admin.heatmap.tsx` L95-107 (`HeatmapGrid`'s loading/error branches)
**Apply to:** both rewritten frontend routes — centered `<Spin size="large" />`, `<Alert type="error" showIcon>` with UI-SPEC's exact copy strings ("We couldn't load this report...", "Couldn't load the aggregated maturity data.") paired with a Retry button per the Copywriting Contract.

### WeasyPrint PDF generation (unchanged call site)
**Source:** `backend/app/api/v1/reports.py` L60-97 (`_send_report_email`), L231-257 (`download_report_pdf`)
**Apply to:** both PDF-producing endpoints — same `WeasyHTML(string=html_content).write_pdf()` call, now fed by the rewritten `generate_html_report`'s new context keys (`radar_chart_svg`, etc.) rather than a second PDF pipeline (RESEARCH "Don't Hand-Roll").

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `backend/app/services/admin_aggregation.py` (NEW module) | service | batch | No existing standalone aggregation-service module exists — closest precedent is `admin.py`'s inline raw-SQL query functions, which this new module extracts/extends per RESEARCH's recommended project structure; genuinely new file, not a rewrite. |
| `get_maturity_band` / `generate_radar_svg` (new pure functions) | utility | transform | RESEARCH itself confirms "No existing `band`/`threshold` constant anywhere in the backend" — these are net-new pure functions with no prior in-repo pattern; built from RESEARCH's own Pattern 1/Pattern 2 code examples instead of a codebase analog. |

## Metadata

**Analog search scope:** `backend/app/api/v1/`, `backend/app/services/`, `backend/app/schemas/`, `backend/app/templates/`, `config/`, `frontend/src/routes/_app/`, `frontend/src/lib/` — all read directly this session (per RESEARCH.md's own "Primary (HIGH confidence)" source list, cross-checked here).
**Files scanned:** 11 target files + 4 additional analog-only reads (`initiatives.py` L190-235, `assessments.py` schema, `assessments.tsx` L1-100, `dimension_scoring.py` full)
**Pattern extraction date:** 2026-07-26
