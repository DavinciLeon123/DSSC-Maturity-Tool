---
phase: 16-report-data-contract-dual-visualization-admin-aggregation
reviewed: 2026-07-27T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - backend/app/api/v1/admin.py
  - backend/app/api/v1/reports.py
  - backend/app/schemas/report.py
  - backend/app/services/admin_aggregation.py
  - backend/app/services/dimension_scoring.py
  - backend/app/services/report_generator.py
  - backend/app/templates/report.html
  - backend/tests/api/test_admin.py
  - backend/tests/api/test_reports.py
  - backend/tests/services/test_admin_aggregation.py
  - backend/tests/services/test_dimension_scoring.py
  - backend/tests/services/test_report_generator.py
  - config/dssc-questionnaire.json
  - docs/api/openapi.json
  - frontend/src/lib/reports.ts
  - frontend/src/routes/_app/admin.heatmap.tsx
  - frontend/src/routes/_app/report.tsx
findings:
  critical: 2
  warning: 6
  info: 2
  total: 10
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-07-27T00:00:00Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Reviewed the Phase 16 report-data-contract rebuild: the shared `ReportContract`
(`build_report_contract`), the submitted-scoped assessment resolver
(`resolve_report_assessment`), the admin cross-initiative aggregation
(`build_admin_aggregate`), the Jinja/SVG rendering path, and the two React
surfaces (`report.tsx`, `admin.heatmap.tsx`) that consume the contract.

The core submitted-vs-draft resolution logic (`resolve_report_assessment`),
IDOR/ownership handling, and the priority-list/maturity-band logic are sound
and well covered by tests. Two real defects stand out, both centered on the
same root cause: this phase's admin aggregation code assumes every
initiative's **frozen historical** `dimension_scores` snapshot always
matches the **current live** questionnaire config's category set — an
assumption the codebase's own `Assessment.dimension_scores` docstring
explicitly says will NOT hold ("once the config changes ... every
already-submitted version's history must still show what the user actually
answered against, not the new config"), and this exact scenario just
happened one commit prior to this review (`7ede5e2`, replacing the placeholder
config with real content). Additionally, the CSV export writes free-text,
user-controlled initiative names into cells unescaped, a classic CSV/formula
injection vector. Several smaller robustness and dead-code issues are also
listed below.

## Critical Issues

### CR-01: Admin aggregate org-average computation crashes (500) when a frozen assessment snapshot doesn't cover every current config category

**File:** `backend/app/services/admin_aggregation.py:97-115`
**Issue:** `build_admin_aggregate`'s `org_average_scores` computation iterates the
**current, live** `config["categories"]` and, for every included initiative,
does:
```python
next(
    s["score"]
    for s in r["dimension_scores"]
    if s["category_id"] == cat["id"]
)
```
with no default. `r["dimension_scores"]` is the **frozen** JSONB snapshot taken
at submission time (see `Assessment.dimension_scores`'s own docstring in
`backend/app/models/assessment.py:25-35`, which explicitly anticipates config
churn: "once the config changes ... every already-submitted version's
history must still show what the user actually answered against, not the
new config"). If any included initiative's frozen snapshot lacks a
`category_id` that exists in the *current* config (different category id/count
between the config version an old submission was scored against and today's
config), `next()` raises an unhandled `StopIteration`, which is not caught
anywhere in the call chain — the whole `/admin/heatmap` endpoint returns an
unhandled-exception 500 for every admin, not just a degraded row for one
initiative.

This is not a hypothetical: this very branch's most recent commit
(`7ede5e2`, "replace placeholder DSSC config with real 52-question content")
changed the category/question structure that `dssc-questionnaire.json` now
serves, while any previously-submitted assessment's `dimension_scores`
snapshot remains frozen under the old placeholder shape. None of the tests in
`test_admin_aggregation.py`/`test_admin.py` exercise this mismatch — every
test fixture builds its `dimension_scores` fresh from the *same* config
object the assertions later re-read, so the gap is untested.

**Fix:**
```python
score = next(
    (s["score"] for s in r["dimension_scores"] if s["category_id"] == cat["id"]),
    None,
)
if score is None:
    continue  # or: exclude this initiative from this category's average
```
More robustly, exclude a whole initiative from `included` (or from a specific
category's average) when its snapshot doesn't cover the current category set,
rather than crashing the endpoint. Add a regression test that submits an
assessment with a `dimension_scores` snapshot using category ids that don't
exist in the current config, and asserts `/admin/heatmap` still returns 200.

### CR-02: CSV export is vulnerable to formula/CSV injection via free-text initiative name

**File:** `backend/app/api/v1/admin.py:296-306` (also header at `246-316`)
**Issue:** `export_dataset` streams `row["initiative_name"]` directly into a CSV
cell via `csv.writer.writerow(...)` with no sanitization.
`Initiative.name` (`backend/app/models/initiative.py:34`) is free text,
2–200 characters, fully user-controlled (any authenticated user can set it
via `POST /initiatives`). A participant can set their initiative name to a
value starting with `=`, `+`, `-`, or `@` (e.g.
`=cmd|'/c calc.exe'!A1` or `=HYPERLINK("http://evil","click")`), and when an
admin opens the exported `mami-dataset.csv` in Excel/Sheets/LibreOffice, the
cell is interpreted as a formula (CWE-1236, "Improper Neutralization of
Formula Elements in a CSV File") — a classic CSV-injection vector that can
lead to arbitrary command execution or data exfiltration on the admin's
machine, all triggered by an unprivileged user.

**Fix:** Sanitize any cell whose value starts with `=`, `+`, `-`, `@`, tab, or
CR before writing it:
```python
def _csv_safe(value: str) -> str:
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value

writer.writerow([
    row["email"],
    _csv_safe(row["initiative_name"]),
    row["participant_type"],
    row["status"],
    row["question_id"],
    row["category_id"],
    row["score"],
])
```

## Warnings

### WR-01: Per-initiative dimension score lookup keys off display `name`, not the stable `category_id`

**File:** `frontend/src/routes/_app/admin.heatmap.tsx:100-108`
**Issue:** The per-initiative breakdown table's dynamic dimension columns are
built from `data.org_average_scores` (computed fresh from the *current* live
config) and matched against each row's `dimension_scores` (a per-initiative
**frozen** snapshot, per CR-01 above) by `name`:
```ts
const match = record.dimension_scores?.find((d) => d.name === name);
```
Both `AdminInitiativeAggregateRow.dimension_scores` and
`AdminAggregateResponse.org_average_scores` carry a stable `category_id`
field already — matching by mutable display `name` instead is fragile to the
exact same config-drift scenario as CR-01: if a category's display name is
ever renamed, or an older frozen snapshot used a different name for the same
id, a cell that does in fact have data silently renders "—" instead.
**Fix:** Match on `category_id` instead of `name` (the columns can still show
`name` as the header text).

### WR-02: Per-initiative breakdown table is completely hidden when the org has zero submitted assessments, even though the API returns visibility rows for exactly this case

**File:** `frontend/src/routes/_app/admin.heatmap.tsx:181-248`
**Issue:** `AdminAggregateResponse.initiatives` is explicitly designed (per
`build_admin_aggregate`'s docstring and `test_admin_heatmap_empty_org_...`)
to include every initiative — including `has_data=False` draft-only ones —
even when the org-wide radar/average is suppressed. But the frontend renders
the entire `<Card>`+`<Table>` block only inside the `!isOrgEmpty` branch
(line 195), so the moment `org_radar_chart_svg` is `null` (zero submitted
assessments org-wide), admins see only the "No submitted assessments yet"
message and never see the list of initiatives at all — even in a "0 of N
initiatives have submitted" state that would otherwise be useful triage
information the backend already computed and shipped.
**Fix:** Render the per-initiative table unconditionally (it already
handles `has_data=False` rows via the "No data yet" tag); scope the
"no submitted assessments yet" empty-state messaging to the radar-chart card
only.

### WR-03: `ReportContract`/`PriorityListItem`/`MaturityBand` schemas are dead code — never applied as `response_model`, so OpenAPI documents an empty `{}` response

**File:** `backend/app/schemas/report.py` (whole file); `backend/app/api/v1/reports.py:179-211`
**Issue:** `schemas/report.py`'s docstring states these Pydantic models
"document the contract for openapi and for the frontend fetch types," but a
repo-wide grep shows zero import sites outside the module itself. Neither
`generate_report_data_endpoint` nor `get_report_data_endpoint` declares
`response_model=ReportContract` — they return the raw dict from
`build_report_contract` directly. Consequently `docs/api/openapi.json`'s
`/api/v1/initiatives/{initiative_id}/report/data` GET/POST 200 responses
show `"schema": {}` (confirmed by direct inspection), i.e. the documented
contract these types exist to describe never actually reaches the generated
API docs, and there is no FastAPI-side response validation catching a
`build_report_contract` shape regression either.
**Fix:** Add `response_model=ReportContract` to both `/report/data` routes
(and consider whether `Depends`-injected `dict` typing elsewhere should be
tightened too), or remove the unused schema module if it's genuinely not
meant to be wired up yet.

### WR-04: Zero-question config category produces a score (`0.0`) outside every maturity band's range, which `get_maturity_band` will raise `ValueError` on

**File:** `backend/app/services/dimension_scoring.py:174-186`, `backend/app/services/report_generator.py:66-83`
**Issue:** `compute_dimension_scores`'s own comment claims its zero-question
guard ("WR-04" in that file's comment) is now "load-bearing" because it's
"called directly on the submit path (a real, user-triggered crash surface)."
That guard does prevent a `ZeroDivisionError`, returning `0.0` for a
zero-question category — but it does not prevent the *next* crash: every
`maturity_bands` entry in `config/dssc-questionnaire.json` starts at
`min: 1.0`, so `get_maturity_band(0.0, bands)` (called from both
`build_priority_list` and `generate_radar_svg`, both on the report path)
falls through the loop with no match and raises an unhandled
`ValueError("score 0.0 not covered by any maturity_bands entry")`. The
current real config has no zero-question categories, so this is latent, not
currently triggered — but the comment's claim of having closed this crash
surface is only half true, and a future config edit that empties a category
(rather than removing it outright) would 500 report generation for every
user, not just fail gracefully.
**Fix:** Either forbid zero-question categories at config-load time (fail
fast at startup, not at request time), or extend `maturity_bands` coverage
down to include an explicit "no data" band, or have
`compute_dimension_scores` omit zero-question categories from the returned
list entirely instead of emitting a synthetic out-of-range `0.0`.

### WR-05: `generate_radar_svg` interpolates category names into SVG `<text>` content with no XML escaping

**File:** `backend/app/services/report_generator.py:160-165`
**Issue:**
```python
labels.append(
    f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" '
    f'font-family="Rubik, sans-serif" fill="#06004f" '
    f'text-anchor="middle">{s["name"]}</text>'
)
```
`s["name"]` is interpolated raw. Today this is benign because
`dssc-questionnaire.json` category names are static and developer-controlled,
and the function's own docstring documents this as an invariant ("Only
server-controlled config category names and computed numeric scores flow
into this string — never end-user free-text"). But the resulting string is
subsequently marked `| safe` in `report.html` (bypassing Jinja's
autoescaping) and rendered via `dangerouslySetInnerHTML` on both React pages
(`report.tsx:267`, `admin.heatmap.tsx:213`) — three independent layers all
trust this one unescaped string. A category name containing `&`, `<`, or `"`
would silently break the generated SVG's XML validity today; the moment this
invariant is violated by any future feature (e.g. an admin-editable
questionnaire builder), it becomes a stored-XSS vector with no defense in
depth anywhere in the chain.
**Fix:** `xml.sax.saxutils.escape(s["name"])` (or equivalent) before
interpolating into SVG text nodes, regardless of the current trust
assumption — cheap insurance against the documented invariant ever changing.

### WR-06: `report.tsx`'s PDF download hardcodes a duplicate fallback API base URL instead of reusing the shared `api` client's `baseURL`

**File:** `frontend/src/routes/_app/report.tsx:156`
**Issue:**
```ts
const url = new URL(
  `${import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1"}/initiatives/${resolvedInitiativeId}/report/pdf`,
);
```
This duplicates the exact same `import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1"`
fallback expression already defined once in `frontend/src/lib/api.ts:5` as
`api.defaults.baseURL`, and already used correctly elsewhere in this same
module family (`reports.ts`'s `getReportUrl`). Two independent copies of the
same magic default will silently drift if one is ever changed without the
other.
**Fix:**
```ts
const url = new URL(`${api.defaults.baseURL}/initiatives/${resolvedInitiativeId}/report/pdf`);
```

## Info

### IN-01: `generateReport()`'s docstring is stale — claims persistence that Phase 16 explicitly removed

**File:** `frontend/src/lib/reports.ts:65-69`
**Issue:** The comment reads: "The POST endpoint scores all answers, renders
the HTML report, stores it, and returns the rendered HTML as text." Per this
phase's own decision (RESEARCH Pitfall 2 / decision A1, documented at length
in `reports.py`'s module docstring and `report_generator.py`), the POST
endpoint no longer stores anything — `ComplianceReport` persistence was
removed and every read recomputes fresh. This stale comment will mislead a
future maintainer about the actual behavior.
**Fix:** Update the comment to state the report is rendered fresh on every
call with no server-side persistence.

### IN-02: `_generated_at_str()` uses the deprecated `datetime.utcnow()`

**File:** `backend/app/api/v1/reports.py:82-84`
**Issue:** `datetime.utcnow()` is deprecated as of Python 3.12 in favor of
timezone-aware `datetime.now(timezone.utc)`; it returns a naive datetime that
silently claims UTC without actually carrying that information, which is
error-prone if this value is ever consumed programmatically rather than just
formatted to a string.
**Fix:** `datetime.now(UTC)` (or `datetime.now(timezone.utc)`), adjusting the
`.strftime` call accordingly.

---

_Reviewed: 2026-07-27T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
