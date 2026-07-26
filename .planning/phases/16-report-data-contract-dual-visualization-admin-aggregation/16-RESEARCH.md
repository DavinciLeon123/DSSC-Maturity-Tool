# Phase 16: Report Data Contract, Dual Visualization & Admin Aggregation - Research

**Researched:** 2026-07-26
**Domain:** Server-side SVG generation, WeasyPrint HTML→PDF rendering, frozen-snapshot report contracts, Postgres "latest row per group" aggregation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Chart rendering strategy**
- **D-01:** No JS charting library is added. The radar chart is produced by **one server-side SVG generator function** (Python), used identically for both surfaces — this guarantees pixel-identical charts in-app and in the mailed PDF, avoids a new frontend dependency, and follows the existing hand-rolled-SVG/CSS-grid precedent already in this codebase (`HeatmapMatrix`/`HeatmapGrid` in `report.tsx`/`admin.heatmap.tsx`).
- **D-02:** The generated SVG **markup itself is embedded as a string field in the report JSON contract** (e.g. `radar_chart_svg`), computed once server-side. The frontend renders that exact markup as-is; the Jinja `report.html` template embeds the same string (e.g. `{{ radar_chart_svg | safe }}`) for the PDF. There is no separate client-side polygon-math reimplementation — one computation, reused verbatim on every surface.
- No in-app chart interactivity (hover/tooltips/animation) is in scope — this was a deliberate tradeoff for guaranteed visual parity and zero new dependencies.

**Report data source & versioning**
- **D-03:** The report (chart + priority list, both surfaces) always renders from the **frozen `Assessment.dimension_scores` snapshot** (written at submission time) — never a live recompute of `compute_dimension_scores` for a submitted assessment.
- **D-04:** The report is **viewable per specific assessment version**, not just "the latest." The report endpoint/route takes an assessment identifier so a user can open the full radar+priority-list report for any past submitted version from their history page, not only the most recent one. Both the in-app route and the PDF-generation path need to resolve a specific `Assessment.id`, not just "the initiative's current assessment."

**Color bands & priority list scope**
- **D-05:** The maturity color-band thresholds (1.0-2.0 red / 2.0-3.5 orange / 3.5-5.0 green) are defined as a **new top-level key inside the existing `config/dssc-questionnaire.json`** (e.g. `maturity_bands`), not a separate new config file.
- **D-06:** The sorted priority list **always shows all 6 dimensions**, lowest-to-highest maturity, regardless of color band — not filtered down to only red/orange "needs attention" dimensions.

**Admin aggregation shape**
- **D-07:** The admin aggregated view shows **both**: (a) one org-wide averaged radar chart (average score per dimension, blended across all initiatives), and (b) a per-initiative table/list below it, each row showing that initiative's own dimension scores and overall average with a link to its individual report.
- **D-08:** For aggregation, each initiative contributes **only its latest submitted assessment** (never a draft, never averaged across an initiative's own retake history). Initiatives with **zero submitted assessments are excluded** from the org-wide average radar and shown as "no data yet" in the per-initiative table.

### Claude's Discretion
- Exact SVG generation approach/library (or hand-written SVG string-building) for the radar polygon (D-01/D-02) — geometry/library choice is an implementation detail, not a user preference.
- Exact route/query-param shape for per-version report viewing (D-04) — e.g. `/report?assessment_id=42` vs. a path segment vs. a new endpoint entirely.
- Exact JSON field names in the report contract (`radar_chart_svg`, `priority_list`, `maturity_bands`, etc.) — naming is a planning-time decision, not settled here.
- Exact per-initiative table sort order/columns beyond "own dimension scores + overall average + link to report" (D-07) — e.g. default sort by overall average vs. by name.
- Whether/how a small "no data yet" badge or empty state is shown for initiatives with no submitted assessment in the per-initiative table (D-08) — visual treatment is a UI-pass concern, not settled here.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope (report contract, chart/PDF rendering, color bands, admin aggregation). No scope-creep topics came up.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| RPRT-01 | End-of-survey report shows a spider/radar chart visualizing all 6 dimension scores at a glance | Architecture Pattern 2 (`generate_radar_svg`) — hand-rolled viewBox-based SVG polygon generator, confirmed compatible with WeasyPrint 69.0 (see Summary + Pitfall 3) |
| RPRT-02 | End-of-survey report shows a sorted priority list (lowest→highest maturity) with dimension name, average score, and color indicator | Code Examples → `build_priority_list` (pure function, always 6 rows per D-06) + `get_maturity_band` (Pattern 1) |
| RPRT-03 | Color-band thresholds are defined once in config and shared by both the chart and the priority list (no duplicated logic) | Pattern 1 (single `get_maturity_band` function) + Code Examples' `maturity_bands` config shape — both the SVG generator and priority-list builder call the same function |
| RPRT-04 | Report is available both in-app (live view) and as a mailed PDF (WeasyPrint + Resend), each rendering the same score data via one shared JSON contract | System Architecture Diagram (READ TIME section) — one `report_contract` dict feeds both the JSON response and the Jinja2/WeasyPrint template; Pitfall 1 identifies the blocking gap (draft-scoped resolution) that must be fixed for this to work post-submission |
| ADMN-01 | Admin aggregated view is rebuilt for the new 6-category model (cross-initiative radar/priority visualization), replacing the old 4×3 topic heatmap | System Architecture Diagram (ADMIN AGGREGATION section) + Pattern 3 (`DISTINCT ON`/`LATERAL` latest-submitted-per-initiative query) + Pitfall 5 (zero-initiative average handling) |
</phase_requirements>

## Summary

This phase turns two already-frozen numeric inputs (Phase 15's `Assessment.dimension_scores` JSONB snapshot, and a new `maturity_bands` config key) into three rendered surfaces — an in-app React report, a mailed WeasyPrint PDF, and an admin cross-initiative aggregate — all fed by exactly one server-computed JSON contract. The riskiest technical bet in the phase's locked decisions (D-01/D-02: hand-build a radar-chart `<svg>` string in Python and embed the identical string verbatim into both the React page and the Jinja2→WeasyPrint PDF path) is **confirmed safe**: WeasyPrint has supported literal inline `<svg>` elements (not just `<img src="data:...">`) since v53 (2021), and this repo pins WeasyPrint 69.0 — six years of hardening past that baseline. No new dependency is needed; the codebase already has a hand-rolled-visualization precedent (`HeatmapMatrix`/`HeatmapGrid`) that this phase directly extends into Python-side SVG string templating.

The bigger risk this research surfaced is **not** the SVG/WeasyPrint question the discussion flagged — it's that all four existing report endpoints (`/report`, `/report/data` GET+POST, `/report/pdf`, `/report/mail`) currently gate on `assert_assessment_complete`, which only ever resolves the initiative's most-recent **draft** Assessment. Once a user actually submits (Phase 15's `submit_initiative` flips the assessment to `status=submitted`), that draft-scoped lookup returns nothing and every report endpoint 422s — confirmed by reading `test_reports.py`'s fixtures, which never call submit and only ever exercise a still-draft, fully-answered assessment. This is exactly the gap D-03/D-04 already anticipated ("must change... to accept an assessment identifier") but it needs to be named explicitly as **the** primary rebuild task, not a side effect: every report endpoint must be re-pointed at `list_submitted_assessments`/a specific submitted `Assessment.id`, never at the draft-scoped completeness gate, for the report to be reachable at all post-submission.

A second architectural fork needs resolving in planning: the existing `ComplianceReport` table has a **unique constraint on `initiative_id`** (one HTML blob per initiative, upserted on every regenerate) — structurally incompatible with D-04's "viewable per specific assessment version." Recommendation below: stop persisting rendered report HTML/JSON at all. Since the whole point of D-03 is that `dimension_scores` are already frozen and cheap (6 numbers), the priority list + SVG + color-banded rows can be **recomputed on every read** from that frozen snapshot with zero risk of drift — no new storage, no migration, and it matches this codebase's demonstrated "one source of truth, not a cached duplicate" philosophy better than widening a table that structurally can't support multiple versions per initiative.

**Primary recommendation:** Build a small, pure, config-driven contract-assembly function (`build_report_contract(assessment, config) -> dict`) that is called fresh on every report-viewing request (GET `/report/data`, `/report/pdf`, `/report/mail`, and the admin aggregate) from the frozen `Assessment.dimension_scores` — never persisted to a new table, never recomputed via `compute_dimension_scores` for an already-submitted assessment. Retire `ComplianceReport`-based HTML persistence for the new contract path; keep hand-rolled SVG string templating (no new Python dependency); resolve "which assessment" via a new submitted-assessment resolver, not the existing draft-scoped `assert_assessment_complete`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Resolve "which Assessment" (latest submitted vs. specific `assessment_id`) | API/Backend | Database | Ownership + submitted-only filtering must happen server-side (security V4); DB provides the row via SQLModel query |
| Color-band lookup (`get_maturity_band(score, bands)`) | API/Backend | — | Single function, config-driven, called by both the SVG generator and the priority-list builder — must not exist in two places (RPRT-03) |
| Radar-chart SVG generation | API/Backend | — | D-01/D-02: one Python function, output embedded verbatim on both surfaces — the browser and WeasyPrint never compute geometry, only render markup |
| Priority-list assembly (sort, 2dp round, pair with band) | API/Backend | — | Pure function over the frozen `dimension_scores` + `maturity_bands` config |
| Report contract JSON response | API/Backend | — | `GET /report/data`-equivalent — the one shared payload both the in-app page and the PDF template consume |
| In-app report rendering | Browser/Client (React) | — | Renders `radar_chart_svg` string verbatim (no client-side polygon math) + a plain list/table for `priority_list` |
| PDF rendering | API/Backend (WeasyPrint) | — | Jinja2 template embeds the identical `radar_chart_svg` string; WeasyPrint converts HTML (incl. inline SVG) → PDF bytes |
| Admin cross-initiative aggregation query | Database | API/Backend | "Latest submitted per initiative" is a DB-shaped problem (window function / `DISTINCT ON`); the average-across-initiatives math is cheap enough to do in Python once rows are fetched |
| Admin org-wide radar + per-initiative table | API/Backend | Browser/Client | Backend assembles the same contract shape (reusing the SVG generator + band lookup); frontend renders it with an antd `Table` |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| WeasyPrint | 69.0 (pinned via `uv.lock`, unpinned range in `pyproject.toml`) [VERIFIED: uv.lock] | HTML→PDF rendering, incl. inline `<svg>` | Already the project's only PDF engine (`_send_report_email`, `download_report_pdf`); inline SVG support confirmed present since v53, five major versions before this pin |
| Jinja2 | already a transitive dep via `fastapi[standard]`/direct use in `report_generator.py` | HTML templating for the PDF path | Already used by `generate_html_report`; no change needed except passing new context keys |
| antd v6 (`^6.3.0`) | existing | `Table`, `Card`, `Alert`, `Spin` for admin per-initiative table and report page chrome | Already the app's only component library (confirmed no charting lib present, per `frontend/package.json` L14-20) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `math` (sin/cos) | stdlib | Polygon-point trigonometry for the 6-axis radar chart | Always — no dependency needed for regular-hexagon-angle point placement |
| Python stdlib `string`/f-strings | stdlib | SVG markup templating | Always — matches the "hand-rolled, no library" precedent already in this codebase (`HeatmapMatrix`) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled Python SVG string templating | A Python SVG-building library (e.g. `svgwrite`, `drawsvg`) | Adds a new dependency for what is ~40 lines of f-string templating around 6 fixed axis points; D-01 explicitly rules out adding new dependencies for this, and the codebase already favors hand-rolled markup over libraries for visualizations |
| Recompute report contract on every read | Persist the full contract (incl. `radar_chart_svg`) onto `Assessment` at submit time, alongside `dimension_scores` | Persisting would need a second JSONB column and would violate "the SVG generator's output can change if band colors are retuned in config" — recomputing on read means a future palette tweak applies retroactively to old submitted reports' *rendering* without touching the frozen *scores*, which is the correct semantics (frozen data, not frozen pixels) |
| Postgres `DISTINCT ON` for "latest submitted per initiative" | `ROW_NUMBER() OVER (PARTITION BY initiative_id ORDER BY version DESC)` subquery + filter `rn = 1` | Equivalent result; `DISTINCT ON` is simpler SQL for this exact "one row per group, tie-broken by column" case and is idiomatic Postgres (this app is Postgres-only, no portability concern) |

**Installation:** No new packages required for this phase — `weasyprint`, `jinja2`, `antd` are already installed dependencies. Skipping the `## Package Legitimacy Audit` gate below with an explicit "none" since no new package is being added.

**Version verification:** WeasyPrint version confirmed directly from this repo's own lockfile (`grep -A1 'name = "weasyprint"' backend/uv.lock` → `version = "69.0"`), not merely training-data recollection.

## Package Legitimacy Audit

**No new external packages are introduced by this phase.** All libraries used (WeasyPrint, Jinja2, antd, Python stdlib) are already installed dependencies confirmed present in `backend/pyproject.toml`/`backend/uv.lock` and `frontend/package.json`. The Package Legitimacy Gate protocol is not applicable — nothing to check against a registry.

**Packages removed due to [SLOP] verdict:** none (n/a — no new packages).
**Packages flagged as suspicious [SUS]:** none (n/a — no new packages).

## Architecture Patterns

### System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│ SUBMISSION TIME (Phase 15 — unchanged by this phase)                    │
│                                                                          │
│  User answers final Q → POST /initiatives/{id}/submit (initiatives.py) │
│         │                                                               │
│         ▼                                                              │
│  assert_assessment_complete()  →  compute_dimension_scores()            │
│  (dimension_scoring.py, unchanged)   (dimension_scoring.py, unchanged)  │
│         │                                    │                         │
│         ▼                                    ▼                        │
│  Assessment.status = submitted     Assessment.dimension_scores = [ ... ]│
│                                     (frozen JSONB — never touched again)│
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ READ TIME — every report view, in-app or PDF (Phase 16, this phase)     │
│                                                                          │
│  Request: initiative_id + optional assessment_id (query param)         │
│       │                                                                 │
│       ▼                                                                │
│  resolve_report_assessment(session, initiative_id, assessment_id, user)│
│    • 404 if initiative not owned by user (and not admin)               │
│    • resolves to a SUBMITTED Assessment — latest if no id given,       │
│      else that specific id (404 if it doesn't belong to this           │
│      initiative — never leak existence via 403, matches SECU-02)       │
│       │                                                                 │
│       ▼                                                                │
│  frozen Assessment.dimension_scores  (read-only; SCOR-04's completion   │
│  gate already ran at submit time — never re-run here)                  │
│       │                                                                 │
│       ├──► get_maturity_band(score, config["maturity_bands"])          │
│       │      called once per dimension, by BOTH branches below         │
│       │                                                                │
│       ├──► build_priority_list(scores, bands) ─────────────┐           │
│       │      [{category_id,name,score,band_id,band_label}] │           │
│       │      sorted ascending by score                      │           │
│       │                                                     ▼           │
│       └──► generate_radar_svg(scores, bands) ──────►  report_contract = │
│              pure-function <svg> string,               {               │
│              viewBox-based, 6 axes                        assessment,  │
│                                                             initiative, │
│                                                             dimension_  │
│                                                             scores,     │
│                                                             priority_   │
│                                                             list,       │
│                                                             radar_      │
│                                                             chart_svg,  │
│                                                             maturity_   │
│                                                             bands       │
│                                                           }             │
│       │                                                                 │
│       ├──► JSON response → GET /initiatives/{id}/report/data           │
│       │      → React /report page: renders radar_chart_svg verbatim    │
│       │        (raw markup, e.g. dangerouslySetInnerHTML-equivalent    │
│       │        in a React 19 + antd context) + a plain priority table  │
│       │                                                                 │
│       └──► same contract fed into Jinja2 report.html                   │
│              {{ radar_chart_svg | safe }} — same string, same bytes    │
│              → WeasyPrint HTML(string=...).write_pdf()                 │
│              → GET /report/pdf (download) / POST /report/mail (Resend) │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ ADMIN AGGREGATION — GET /admin/heatmap rebuild (ADMN-01)                 │
│                                                                          │
│  latest_submitted = SELECT DISTINCT ON (a.initiative_id) ...            │
│                     FROM assessment a WHERE a.status='submitted'        │
│                     ORDER BY a.initiative_id, a.version DESC            │
│       │                                                                 │
│       ├─ LEFT JOIN initiative → every initiative appears once           │
│       │    • has a latest_submitted row → include in org average + row  │
│       │    • no submitted row at all    → excluded from average,        │
│       │                                    row shows "No data yet"      │
│       ▼                                                                 │
│  org_avg_scores[dim] = mean(dimension_scores[dim] across included      │
│                              initiatives' frozen snapshots)             │
│       │                                                                 │
│       ├──► generate_radar_svg(org_avg_scores, bands) — SAME function   │
│       │      used for individual reports, not a second implementation  │
│       │                                                                 │
│       └──► per-initiative table rows: name, dimension scores, overall  │
│              average, band, link → /report?assessment_id=<that row's   │
│              latest submitted Assessment.id> (admin bypasses the       │
│              ownership check via require_admin, same pattern as every  │
│              other admin.py endpoint)                                  │
└────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

No new top-level directories — this phase modifies/extends existing files:

```
backend/app/
├── services/
│   ├── dimension_scoring.py     # add: resolve-submitted-assessment helper(s)
│   ├── report_generator.py      # rewrite: build_report_contract(), generate_radar_svg(),
│   │                             #   build_priority_list(), get_maturity_band()
│   └── admin_aggregation.py     # NEW — org-wide average + per-initiative "latest submitted" query
├── api/v1/
│   ├── reports.py               # rewrite: resolve by assessment_id, drop ComplianceReport upsert
│   └── admin.py                 # rewrite: /heatmap → real 6-dimension aggregation
├── schemas/
│   └── report.py                # NEW — ReportContract/PriorityListItem/MaturityBand pydantic models
└── templates/
    └── report.html              # rewrite: 6-dimension layout, embed radar_chart_svg, priority list

frontend/src/
├── routes/_app/
│   ├── report.tsx                # rewrite: fetch by ?assessment_id, render radar_chart_svg + priority list
│   └── admin.heatmap.tsx         # rewrite: org radar + per-initiative Table
└── lib/
    └── reports.ts                 # extend: typed fetch for the new JSON contract shape

config/
└── dssc-questionnaire.json       # add: top-level "maturity_bands" key (D-05)
```

### Pattern 1: Single color-band lookup function, reused by both renderers

**What:** One pure function `get_maturity_band(score: float, bands: list[dict]) -> dict` that both `generate_radar_svg` (to pick each axis's segment color) and `build_priority_list` (to pick each row's dot color + label) call — never two separate inequality chains.

**When to use:** Any time a numeric score needs to map to a red/orange/green (or any config-driven band) classification — this is the literal deliverable of RPRT-03 ("no duplicated logic").

**Example:**
```python
# Source: hand-written pattern, no external reference (bands come from
# config/dssc-questionnaire.json's new "maturity_bands" key per D-05)
def get_maturity_band(score: float, bands: list[dict]) -> dict:
    """Bands are checked in ascending `min` order; a score exactly on a
    shared boundary (e.g. 2.0, which is both the red band's max and the
    orange band's min) belongs to the HIGHER band — i.e. `min <= score`
    is the inclusive edge, `max` is exclusive except for the top band.
    This single rule must never be reimplemented elsewhere."""
    for band in bands:
        is_last = band is bands[-1]
        if band["min"] <= score < band["max"] or (is_last and score == band["max"]):
            return band
    raise ValueError(f"score {score} not covered by any maturity_bands entry")
```

### Pattern 2: Hand-rolled SVG radar/spider polygon (viewBox-based, N axes)

**What:** A pure function that places N=6 axis points around a circle (angle offset so axis 0 points straight up), scales each dimension's score into a radius fraction, and emits a `<polygon>` (data shape) plus `<line>`/`<text>` axis spokes and labels — all as one f-string-built `<svg viewBox="0 0 W H">...</svg>` document.

**When to use:** This phase's only chart — reused verbatim for both a single assessment's report and the admin org-wide average (same function, different `scores` input).

**Example:**
```python
# Source: hand-written — standard radar-chart trigonometry (angle = 2*pi*i/n
# - pi/2 so the first axis points up), no external library dependency (D-01)
import math

def generate_radar_svg(
    scores: list[dict],       # [{category_id, name, score}, ...] len == 6
    bands: list[dict],
    *, size: int = 320, max_score: float = 5.0,
) -> str:
    n = len(scores)
    cx = cy = size / 2
    radius = size * 0.38  # leave room for axis labels outside the chart

    def point(i: int, value_fraction: float) -> tuple[float, float]:
        angle = (2 * math.pi * i / n) - (math.pi / 2)
        r = radius * value_fraction
        return (cx + r * math.cos(angle), cy + r * math.sin(angle))

    # Data polygon
    data_points = " ".join(
        f"{x:.1f},{y:.1f}"
        for i, s in enumerate(scores)
        for x, y in [point(i, min(s["score"], max_score) / max_score)]
    )

    # Axis spokes (full-radius lines) + labels
    spokes = []
    labels = []
    for i, s in enumerate(scores):
        x, y = point(i, 1.0)
        spokes.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
                       f'stroke="#d9d9d9" stroke-width="1"/>')
        lx, ly = point(i, 1.18)  # push labels outside the polygon
        labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" '
                       f'text-anchor="middle" fill="#06004f">{s["name"]}</text>')

    band = get_maturity_band(
        sum(s["score"] for s in scores) / n, bands
    )  # overall-average band tints the fill, per-axis dots could use per-axis bands

    return (
        f'<svg viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
        + "".join(spokes)
        + f'<polygon points="{data_points}" fill="{band["color"]}" '
          f'fill-opacity="0.25" stroke="{band["color"]}" stroke-width="2"/>'
        + "".join(labels)
        + "</svg>"
    )
```

### Pattern 3: "Latest submitted assessment per initiative" (Postgres `DISTINCT ON`)

**What:** One query that returns exactly one row per initiative — its highest-`version` **submitted** Assessment — with initiatives that have zero submitted assessments still appearing (via `LEFT JOIN`) so the admin table can render "No data yet" instead of silently omitting them (D-08).

**Example:**
```sql
-- Source: adapts the existing raw-SQL join precedent in admin.py's
-- list_initiatives/list_users (this repo's established pattern for
-- enum-safe, join-heavy admin queries)
SELECT
    i.id            AS initiative_id,
    i.name          AS initiative_name,
    latest.id       AS assessment_id,
    latest.version  AS version,
    latest.dimension_scores AS dimension_scores
FROM initiative i
LEFT JOIN LATERAL (
    SELECT a.id, a.version, a.dimension_scores
    FROM assessment a
    WHERE a.initiative_id = i.id AND a.status = 'submitted'
    ORDER BY a.version DESC
    LIMIT 1
) latest ON true
ORDER BY i.created_at DESC;
```
Equivalently, a plain `DISTINCT ON (a.initiative_id) ... ORDER BY a.initiative_id, a.version DESC` subquery joined back to `initiative` works too — `LATERAL` is shown here because it composes more simply with SQLModel's existing `session.execute(text(...))` raw-SQL style already used in `admin.py`.

### Anti-Patterns to Avoid

- **Recomputing `dimension_scores` from live answers for a submitted assessment:** D-03 explicitly forbids this — always read `Assessment.dimension_scores` (the frozen snapshot). `compute_dimension_scores` remains a submit-time-only function (as it already is for scoring.py's live in-progress endpoint).
- **A second inequality chain for color bands in the frontend:** The frontend must never re-derive red/orange/green from a raw score — it only ever displays `band_label`/`band_color`/`band_id` fields the backend already attached to each `priority_list` row and to the SVG's embedded fill colors.
- **Client-side SVG generation for the admin org-wide radar:** Some teams are tempted to reuse a JS charting lib "just for the admin view since it's different data." D-01 is a project-wide decision, not per-surface — the same Python `generate_radar_svg` function must render both the individual and aggregate charts.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "One row per group, tie-broken by a column" (latest submitted assessment per initiative) | A Python loop that fetches all submitted assessments and picks the max per initiative_id in application code | Postgres `DISTINCT ON` / `LATERAL` subquery | Doing this in Python means fetching every submitted assessment's full JSONB blob for every initiative just to discard all but one — wasteful and racy if graded against updated_at instead of version; `DISTINCT ON` is a single indexed query |
| HTML→PDF rendering | A second, separate PDF-generation path or library "for the new report" | The exact same WeasyPrint call already used by `download_report_pdf`/`_send_report_email` | The PDF must render the SAME `report.html` template with the SAME `radar_chart_svg` string as the in-app view — introducing a second renderer would violate D-04/RPRT-04's "one shared contract" |
| Config loading/caching for `maturity_bands` | A new config loader/cache singleton | `get_dssc_questionnaire_config()` (existing FastAPI lifespan-cached dependency) | D-05 explicitly puts `maturity_bands` inside the same `dssc-questionnaire.json` file this loader already serves — a second loader would be pure duplication |

**Key insight:** Every "don't hand-roll" item here is really the same insight repeated: this phase's entire job is *not* inventing new infrastructure — it's wiring one already-frozen data source through one pure-function pipeline (band lookup → priority list / SVG) that both consumers (React, WeasyPrint) render without modification. Any solution that introduces a second query, a second config path, or a second rendering surface is very likely fighting the phase's own locked decisions.

## Common Pitfalls

### Pitfall 1: All four report endpoints currently 422 for any actually-submitted assessment
**What goes wrong:** `reports.py`'s `/report`, `/report/data` (GET+POST), `/report/pdf`, `/report/mail` all call `assert_assessment_complete(session, initiative_id, config)`, which internally calls `get_current_assessment` — explicitly documented (dimension_scoring.py) as scoped to "the most-recent **draft**" Assessment. Once `submit_initiative` flips that assessment's `status` to `submitted`, `get_current_assessment` returns `None` for that initiative (until a retake creates a new draft), so every report endpoint immediately 422s with "Questionnaire not fully answered" — even though the user has a perfectly good, fully-scored submitted assessment sitting right there.
**Why it happens:** `assert_assessment_complete` was built in Phase 14 purely as the *pre-submission* completeness gate (used correctly by `scoring.py` and `initiatives.py`'s `submit_initiative`). Phase 14/15's stub versions of the report endpoints reused it as a stand-in ownership+existence check without anyone revisiting whether "current draft" was still the right resolution target after Phase 15 introduced real submit/retake semantics. `test_reports.py`'s fixtures mask this: every test builds a fully-answered **draft** assessment and never calls `/submit`, so the tests pass while the real post-submission user flow would break.
**How to avoid:** Every report-related endpoint must resolve its assessment via a **submitted-scoped** lookup — either "the initiative's latest submitted assessment" (default, no query param) or "the submitted assessment matching this specific `assessment_id`" (D-04) — using `list_submitted_assessments` (already exists) or a new `get_assessment_by_id` + ownership/status check, never `assert_assessment_complete`/`get_current_assessment`.
**Warning signs:** Any test that builds a report-endpoint fixture via `make_assessment(...)` + `_answer_all_questions(...)` without also calling the submit endpoint (or setting `status=AssessmentStatus.submitted` directly) is testing the wrong lifecycle state for this phase's rebuild — the plan's own test fixtures need updating to submit first, or they'll silently keep passing against the old (wrong) behavior.

### Pitfall 2: `ComplianceReport`'s `initiative_id` unique constraint can't hold multiple versions
**What goes wrong:** `ComplianceReport` (in `app/models/report.py`) has `initiative_id: int = Field(..., unique=True)` and `POST /initiatives/{id}/report` upserts on that column — meaning the table can only ever hold ONE stored report blob per initiative, permanently overwritten on every regenerate. This is structurally incompatible with D-04 ("viewable per specific assessment version").
**Why it happens:** `ComplianceReport` predates the Assessment/versioning model entirely (it was built when there was one report per initiative, full stop, in the original MAMI app).
**How to avoid:** Recommended: stop writing to `ComplianceReport` for the new contract-based flow entirely — since the contract is cheap to recompute from the frozen `Assessment.dimension_scores` on every read, there is no correctness or performance reason to persist it. If a "generate and store" step is still wanted for the plain HTML view (`POST /report`), it must be re-keyed off `assessment_id` (would need a schema migration + likely dropping the `unique=True` constraint) rather than `initiative_id`. Flag this table's fate as an explicit planning decision — don't silently keep upserting to a column that can't represent what D-04 requires.
**Warning signs:** Any implementation that keeps calling `pg_insert(ComplianceReport)...on_conflict_do_update(index_elements=["initiative_id"])` for the rebuilt endpoints will silently lose older versions' stored HTML the moment a second submitted version exists for the same initiative.

### Pitfall 3: WeasyPrint's inline `<svg>` support has real limitations, even though it exists
**What goes wrong:** WeasyPrint's SVG renderer (its own implementation, "highly inspired by CairoSVG" per the WeasyPrint 53 release notes) is not a full SVG spec implementation — some features are documented as missing (e.g. `clipping`), and separate GitHub issues report CSS `font` shorthand being ignored inside `<text>` elements (falls back to WeasyPrint's default font rather than an inline `style="font: ..."` override) [CITED: courtbouillon.org/blog/00009-weasyprint-53-what-s-new, github.com/Kozea/WeasyPrint/issues/2255].
**Why it happens:** WeasyPrint's PDF engine renders through Pango/Cairo for text layout — "Cairo is known to be just a 'toy' about fonts" per WeasyPrint's own architecture docs — so SVG `<text>` styling that relies on CSS shorthand or web fonts loaded only via the HTML page's `<style>` (not inline `style=` attributes on the SVG elements themselves) may not carry through identically to how a browser renders the same SVG.
**How to avoid:** Set font properties as **explicit SVG presentation attributes** on each `<text>` element (`font-size="11" font-family="Rubik, sans-serif" fill="#06004f"`) rather than relying on an external CSS class/shorthand cascading into the SVG. Since `radar_chart_svg` is generated once server-side and reused verbatim, this only needs to be gotten right in one function (`generate_radar_svg`), and a visual check should compare the same rendered chart in a browser (React page) vs. the actual PDF output (not just eyeballing the raw markup) before considering this pattern "done" — the plan should include a concrete verification step for this, e.g. a manual/checkpoint task to open the generated PDF and confirm the chart labels are legible and correctly positioned, since no automated visual-regression tooling exists in this repo yet (confirmed — Phase 17 scope per the UI-SPEC's own "overflow… backstop" note).
**Warning signs:** Chart text appearing in a different font/size in the downloaded PDF than in the browser, or radar-chart labels overlapping/clipping near the SVG's edges (mitigated by the `viewBox` sizing in Pattern 2 above, but must actually be checked against a real WeasyPrint render, not just the React preview).

### Pitfall 4: Local dev machine cannot exercise WeasyPrint at all
**What goes wrong:** This repo's own `deferred-items.md` history (Phases 12-15) repeatedly notes "4 pre-existing local-only WeasyPrint failures" on this Mac — WeasyPrint's native library dependencies (Pango/GObject) aren't installed locally, confirmed again this session (`uv run python -c "import weasyprint"` fails locally with the WeasyPrint troubleshooting URL as its only output). CI has this fixed (per Phase 12's CLAUDE.md-documented fix to all pytest-running workflows).
**Why it happens:** WeasyPrint depends on system-level Cairo/Pango/GDK-Pixbuf libraries that aren't part of the Python package itself and aren't installed on this particular macOS dev machine.
**How to avoid:** Any task in this phase's plan that needs to visually confirm the actual rendered PDF (not just that Python code imports/runs) must run in CI or inside the project's Docker image, never assume `uv run pytest` on this local machine will exercise real WeasyPrint rendering — tests that mock `weasyprint.HTML` (the existing pattern in `test_reports.py`) will pass locally regardless, but that only proves the endpoint *calls* WeasyPrint correctly, not that the SVG renders correctly inside the PDF.
**Warning signs:** A plan step described as "verify the PDF renders correctly" that doesn't specify running through CI/Docker will silently produce a false-pass locally on this machine.

### Pitfall 5: Zero-initiative / all-drafts admin average must not divide by zero or include phantom zero scores
**What goes wrong:** If an org has zero initiatives with any submitted assessment (or every initiative is still mid-draft), naively computing `sum(scores)/count(initiatives)` either divides by zero or — if a `LEFT JOIN` returns `NULL` `dimension_scores` for un-submitted initiatives and those get coerced to `0` before averaging — silently drags the org average down toward zero even though "no data" is not the same as "score of zero" (D-08 explicitly calls this out).
**How to avoid:** Filter to only initiatives with a non-null `latest_submitted` assessment *before* computing the mean; if that filtered set is empty, the org radar/average must be suppressed entirely (per the UI-SPEC's "empty" state: "org radar is suppressed... not rendered as a zeroed/degenerate hexagon") rather than rendered as a chart of all-zero scores.
**Warning signs:** A radar chart that renders as a single point at the center (all-zero) instead of not rendering at all when there's no submitted data org-wide.

## Code Examples

### Priority list assembly (pure function, reused shape for both surfaces)
```python
# Source: hand-written, config-driven — mirrors compute_dimension_scores'
# existing "derive structure from config, never hardcode" idiom
def build_priority_list(scores: list[dict], bands: list[dict]) -> list[dict]:
    """D-06: always all 6 dimensions, sorted lowest-to-highest maturity."""
    return [
        {
            "category_id": s["category_id"],
            "name": s["name"],
            "score": s["score"],
            "band_id": (band := get_maturity_band(s["score"], bands))["id"],
            "band_label": band["label"],
            "band_color": band["color"],
        }
        for s in sorted(scores, key=lambda s: s["score"])
    ]
```

### `maturity_bands` config shape to add under D-05
```json
{
  "maturity_bands": [
    { "id": "red",    "label": "Needs attention", "min": 1.0, "max": 2.0, "color": "#d64545" },
    { "id": "orange", "label": "Developing",       "min": 2.0, "max": 3.5, "color": "#e08e2b" },
    { "id": "green",  "label": "Mature",            "min": 3.5, "max": 5.0, "color": "#399e5a" }
  ]
}
```
Hex values copied verbatim from the approved `16-UI-SPEC.md` Color section (`#d64545`/`#e08e2b`/`#399e5a`) — do not re-derive or re-guess these in code.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| 4×3 MAMI matrix (scheme/participants/data/services × human/machine/trust) rendered as a hand-rolled CSS grid (`HeatmapMatrix`/`HeatmapGrid`) | 6-dimension radar + priority list, driven by one server-rendered SVG string + a plain data table | Phase 13 (schema migration) → Phase 14 (scoring engine replacement, admin stub) → Phase 16 (this phase, full rebuild) | The old topic-level chip aggregation logic (`aggregateCellStatus`) and MAMI-code-to-recommendation maps in `report.tsx`/`admin.heatmap.tsx` are fully retired, not extended |
| `GET /report/data` regenerated scores live from stored answers on every request (Phase 08 decision, noted in STATE.md) | Reads a frozen `Assessment.dimension_scores` snapshot written once at submit time | Phase 15 (HIST-02, gap-closure 15-07) | Old reports become immune to later config/scoring changes — a real behavior change the plan must not accidentally regress |

**Deprecated/outdated:**
- `ComplianceReport`'s "one HTML blob per initiative" model: superseded by this phase's requirement to view any past submitted version — recommend ceasing writes to it for the new contract path (see Pitfall 2).
- The MAMI-code-keyed `RECOMMENDATIONS`/`MAMI_CODE_TO_REC_ID` maps in `report.tsx`: no longer meaningful once the 4×3 matrix is gone — dead code to delete, not adapt, when rebuilding this route.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Recommending `ComplianceReport` writes be dropped entirely for the new contract flow, rather than migrating the table to key off `assessment_id` | Summary / Pitfall 2 | If the team actually wants persisted/immutable report snapshots (e.g. for audit reasons beyond what `Assessment.dimension_scores` already guarantees), this recommendation under-scopes the work — a migration adding `assessment_id` + dropping the old unique constraint would be needed instead. Flagged as an explicit open question below, not silently decided. |
| A2 | The exact per-axis "overall polygon fill color" (Pattern 2 uses the *overall average's* band to tint the whole polygon, since a radar chart typically has one fill color, not six) | Architecture Patterns Pattern 2 | If the intended visual design wants per-axis segment coloring (e.g. a red wedge next to a green wedge within one polygon), the single-fill-color approach shown needs revisiting — this is a `## Claude's Discretion` item in CONTEXT.md ("Exact SVG generation approach... is an implementation detail"), so some visual judgment call is expected at plan/implementation time regardless. |
| A3 | Recommending the org-wide average be computed in plain Python after fetching each included initiative's frozen `dimension_scores` JSONB blob, rather than via `jsonb_array_elements` SQL aggregation | Don't Hand-Roll / Pattern 3 | Fine at today's likely initiative counts (tens, not millions); if this app scales to a very large number of initiatives, an all-Python aggregation could become a real cost, but that is explicitly out of scope for this phase's requirements. |

## Open Questions

1. **Does `ComplianceReport` need to survive this phase at all, and if so, re-keyed how?**
   - What we know: its current `unique=True` on `initiative_id` cannot represent "one report per submitted version" (D-04).
   - What's unclear: whether the plan should (a) drop writes to it entirely and always compute-on-read (this research's recommendation), (b) migrate it to key off `assessment_id` with a schema change, or (c) leave it as dead/unused code for a future cleanup phase.
   - Recommendation: (a) — simplest, no migration, and consistent with D-03's "frozen scores, not frozen renders" semantics; but this should be an explicit decision recorded in the plan, not an implicit side effect of rewriting `reports.py`.

2. **Exact route/query-param shape for admin's "View report" links into a user's per-version report.**
   - What we know: CONTEXT.md leaves this to Claude's discretion; the admin per-initiative table needs a link that bypasses per-user ownership (admins can view any initiative's report).
   - What's unclear: whether the shared `/report` route/endpoint should accept an `?initiative_id=`/`?assessment_id=` pair when called by an admin (bypassing the `current_user.id == initiative.user_id` check for `require_admin`-authenticated requests), or whether a separate `admin`-prefixed report-viewing route is cleaner.
   - Recommendation: extend the existing report endpoint(s) to accept the requesting principal being either the initiative's owner OR an admin (mirrors how every other `admin.py` endpoint already re-derives its own authorization rather than reusing owner-scoped routes) — avoids building a second report-rendering code path.

3. **Per-axis vs. overall-average band coloring for the radar chart's fill.**
   - See Assumption A2 above — this is a visual-design judgment call appropriately left to plan/implementation, not fully resolved by research.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| WeasyPrint (Python package) | PDF rendering (`/report/pdf`, `/report/mail`) | ✓ (installed, but see below) | 69.0 | — |
| WeasyPrint native libs (Pango/Cairo/GObject) | Actually rendering a PDF from HTML/SVG | ✗ on this local Mac | — | CI (all 4 pytest workflows already fixed per Phase 12) and Docker have this working; any visual-verification task in this phase's plan must target CI/Docker, not local `uv run pytest` |
| Postgres | Admin aggregation query (`DISTINCT ON`/`LATERAL`) | ✓ (existing test/dev DB via testcontainers + Railway) | — | — |
| Node/npm | Frontend build/typecheck for `report.tsx`/`admin.heatmap.tsx` rebuild | ✓ | Node v24.18.0 | — |

**Missing dependencies with no fallback:** none — WeasyPrint's native-library gap has an established fallback (CI/Docker) already in daily use by this project.

**Missing dependencies with fallback:** WeasyPrint native rendering locally on this Mac — verify PDF/SVG output through CI or the project's Docker image instead of local pytest runs.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-xdist (backend); Vitest 4.1.10 + Testing Library (frontend) |
| Config file | `backend/pyproject.toml` (`[tool.pytest]`-equivalent via `dev-dependencies`); `frontend/vitest.config.ts` |
| Quick run command | `cd backend && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` |
| Full suite command | `cd backend && uv run pytest tests/ -n auto -m "not perf" -q` |

### Phase Requirement → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| RPRT-01 | Report response includes a `radar_chart_svg` string containing 6 axis labels | unit/integration | `pytest tests/api/test_reports.py -k radar -x` | ❌ Wave 0 — new test file/cases needed |
| RPRT-02 | `priority_list` always has exactly 6 entries, sorted ascending by score, each with `band_label`/`band_color` | unit | `pytest tests/services/test_report_generator.py -k priority_list -x` | ❌ Wave 0 |
| RPRT-03 | `get_maturity_band` returns identical band for the same score regardless of caller (SVG generator vs. priority list) | unit | `pytest tests/services/test_report_generator.py -k maturity_band -x` | ❌ Wave 0 |
| RPRT-04 | The same `radar_chart_svg`/`priority_list` values appear in both `/report/data`'s JSON and the rendered `report.html` context | integration | `pytest tests/api/test_reports.py -k contract_parity -x` | ❌ Wave 0 |
| ADMN-01 | `/admin/heatmap` excludes initiatives with zero submitted assessments from the average but includes them (as "no data yet") in the per-initiative list | integration | `pytest tests/api/test_admin.py -k heatmap_aggregation -x` | ❌ Wave 0 |

**Note:** per this phase's own explicit boundary ("automated test coverage for this phase's new code (Phase 17)"), full test-writing is deferred to Phase 17 (TEST-01/02). The table above is provided so the planner can decide whether to add a minimal smoke-test safety net now (recommended for at least the Pitfall 1 lifecycle-state bug, since it's a functional regression risk, not just missing coverage) versus leaving all of it to Phase 17 per the milestone's stated sequencing.

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/api/test_reports.py tests/api/test_admin.py -q` (fast, scoped)
- **Per wave merge:** full quick-run command above
- **Phase gate:** full suite green before `/gsd-verify-work`, plus a CI-or-Docker-based manual check of an actual downloaded PDF (Pitfall 3/4 — cannot be automated away locally)

### Wave 0 Gaps
- [ ] No test file yet exercises a report endpoint against a **submitted** (not draft) assessment — every existing `test_reports.py` fixture uses a still-draft assessment (Pitfall 1). This must be added regardless of Phase 17's broader test-coverage mandate, since it directly proves/disproves this phase's core rebuild.
- [ ] `tests/services/test_report_generator.py` currently only covers the old minimal stub — needs new cases for `generate_radar_svg`/`build_priority_list`/`get_maturity_band`.
- [ ] `tests/api/test_admin.py`'s heatmap tests currently only assert the fixed degraded stub — needs a full rewrite for the new aggregation shape.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no (unchanged) | Existing JWT bearer auth (`get_current_user`/`require_admin`) — no change this phase |
| V3 Session Management | no (unchanged) | n/a |
| V4 Access Control | **yes** | Resolving a report by an arbitrary `assessment_id` query param must re-derive ownership server-side (join `Assessment.initiative_id → Initiative.user_id == current_user.id`), returning 404 (not 403) on mismatch to avoid confirming an assessment id's existence — exact pattern already used everywhere else in `reports.py`/`admin.py` (`if not initiative or initiative.user_id != current_user.id: raise HTTPException(404, ...)`). Admin-viewed reports (per D-07's per-initiative links) must bypass this via `require_admin`, not by weakening the owner-scoped check itself. |
| V5 Input Validation | yes | `assessment_id` (if accepted as a query/path param) must be validated as a positive integer by FastAPI's own type coercion (`assessment_id: int | None = None`) — no manual parsing needed |
| V6 Cryptography | no | n/a — no new secrets/crypto surface introduced |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| IDOR via sequential `assessment_id` (enumerate other users' report data by incrementing the query param) | Information Disclosure | Server-side ownership re-check on every request (see V4 above) — never trust the path/query id alone as authorization, matches SECU-02's broader non-enumerable-ID goal even though SECU-02 itself is Phase 18's scope |
| Reflected/stored XSS via the embedded `radar_chart_svg` string if any user-controlled text ever entered SVG `<text>` content | Tampering / Elevation of Privilege | Dimension names come only from server-controlled `config/dssc-questionnaire.json` (not end-user input) — safe by construction as long as no future change starts interpolating free-text user input into the SVG string. If `initiative.name` or similar ever gets embedded into SVG/HTML, it must go through the same Jinja2 `autoescape=select_autoescape(["html"])` already configured in `report_generator.py`, or be manually escaped before insertion into the raw SVG string (the SVG string itself, being pre-rendered server-side and marked `| safe` in Jinja, is NOT auto-escaped a second time — this is exactly why only server-controlled category names/scores may ever flow into it). |

## Sources

### Primary (HIGH confidence)
- This repo's own source files — `backend/app/api/v1/reports.py`, `backend/app/services/report_generator.py`, `backend/app/services/dimension_scoring.py`, `backend/app/api/v1/admin.py`, `backend/app/api/v1/initiatives.py`, `backend/app/models/assessment.py`, `backend/app/models/report.py`, `backend/app/models/initiative.py`, `backend/tests/api/test_reports.py`, `backend/app/templates/report.html`, `frontend/src/routes/_app/report.tsx`, `frontend/src/routes/_app/admin.heatmap.tsx`, `frontend/src/lib/theme.ts`, `config/dssc-questionnaire.json` — all read directly this session.
- `backend/uv.lock` — direct grep confirming WeasyPrint 69.0.
- GitHub API (`api.github.com/repos/Kozea/WeasyPrint/issues/75`) — confirmed `state: closed`, `state_reason: completed`, `closed_at: 2021-08-17`.

### Secondary (MEDIUM confidence)
- [CourtBouillon — WeasyPrint 53: What's New](https://www.courtbouillon.org/blog/00009-weasyprint-53-what-s-new/) — "basic support for inline SVG" landed in v53; "some features are known to be missing (clipping, for example)".
- [WeasyPrint stable docs — Features/API reference](https://doc.courtbouillon.org/weasyprint/stable/features.html) — confirms `<img>`/`<embed>`/`<object>` SVG support pattern and vector (not rasterized) PDF output.
- [GitHub Issue #2255 — 'font' CSS shorthand ignored in SVG 'text' elements](https://github.com/Kozea/WeasyPrint/issues/2255) — informs Pitfall 3's guidance to use explicit presentation attributes.

### Tertiary (LOW confidence)
- General WebSearch summaries of WeasyPrint GitHub issues (#134, #845, #1021, #1761, #1864, #2234) — used only to corroborate "known rough edges exist in SVG text/CSS handling," not relied on for any specific factual claim beyond what the primary/secondary sources above directly confirm.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; existing versions confirmed directly from this repo's own lockfiles/config, not assumed from training data.
- Architecture: HIGH — the frozen-snapshot-driven contract design follows directly from Phase 15's already-shipped `dimension_scores` JSONB column and `list_submitted_assessments` helper; the SVG/WeasyPrint compatibility question (the phase's stated top risk) is independently confirmed via GitHub's own issue-tracker API plus official docs, not training-data recall alone.
- Pitfalls: HIGH for Pitfall 1 (verified by reading the actual test fixtures and endpoint code — this is a real, reproducible finding, not a guess) and Pitfall 2 (verified via the model's own field definition); MEDIUM for Pitfalls 3/4 (based on documented GitHub issues plus this repo's own recorded WeasyPrint troubleshooting history, but the actual PDF has not been rendered and visually inspected this session since local WeasyPrint is unavailable).

**Research date:** 2026-07-26
**Valid until:** 2026-08-25 (30 days — this is stable, in-house architecture research, not fast-moving external API surface; re-verify the WeasyPrint version pin if `uv.lock` changes before this phase executes)
