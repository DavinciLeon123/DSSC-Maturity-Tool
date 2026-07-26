# Phase 16: Report Data Contract, Dual Visualization & Admin Aggregation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-26
**Phase:** 16-report-data-contract-dual-visualization-admin-aggregation
**Areas discussed:** Chart rendering strategy, Report data source & versioning, Color bands & priority list scope, Admin aggregation shape

---

## Chart rendering strategy

| Option | Description | Selected |
|--------|-------------|----------|
| One server-side SVG generator, shared by both | Single Python function builds an SVG radar polygon, embedded in the Jinja PDF template and reused in-app. Pixel-identical, no new dependency, no interactivity. | ✓ |
| JS chart library in-app + separate PDF renderer | Recharts (or similar) in-app for interactivity; separate Python static renderer for PDF. Two implementations reading the same JSON. | |
| You decide | Left to Claude/researcher. | |

**User's choice:** One server-side SVG generator, shared by both.

**Follow-up:** Given the shared generator, should the SVG markup be embedded as a string field in the JSON contract, or should the frontend independently re-derive the same SVG from raw scores?

| Option | Description | Selected |
|--------|-------------|----------|
| SVG string embedded in the JSON contract | Report JSON includes `radar_chart_svg` (or similar) with ready-to-render markup; frontend and PDF template both render it verbatim. | ✓ |
| Raw scores only; each surface draws its own SVG | JSON carries only numeric scores/bands; backend and frontend each independently build an equivalent SVG. | |
| You decide | Left to Claude/researcher. | |

**User's choice:** SVG string embedded in the JSON contract.
**Notes:** No in-app chart interactivity (hover/tooltips) is in scope — deliberate tradeoff for guaranteed visual parity and zero new dependencies.

---

## Report data source & versioning

| Option | Description | Selected |
|--------|-------------|----------|
| Always render from the frozen snapshot | Report reads `Assessment.dimension_scores` (frozen at submission, Phase 15) for whichever assessment is viewed — never recomputes live. | ✓ |
| Keep live recompute, ignore the frozen snapshot | Continue calling `compute_dimension_scores()` fresh on every `/report/data` request, as today. | |
| You decide | Left to Claude/researcher. | |

**User's choice:** Always render from the frozen snapshot.

**Follow-up:** Should the report be viewable per specific past assessment version, or only ever mean "the latest submitted"?

| Option | Description | Selected |
|--------|-------------|----------|
| Report is viewable per specific assessment version | Report route/endpoint takes an assessment id; any past submitted version's full report can be opened from the history page. | ✓ |
| Report always means the latest submitted assessment only | Report page/endpoint stays scoped to "current initiative's latest submitted assessment," no per-version viewing. | |
| You decide | Left to Claude/researcher. | |

**User's choice:** Report is viewable per specific assessment version.
**Notes:** Both the in-app route and the PDF-generation path need to resolve a specific `Assessment.id`, not just "the initiative's current assessment."

---

## Color bands & priority list scope

| Option | Description | Selected |
|--------|-------------|----------|
| New key inside config/dssc-questionnaire.json | Add a top-level `maturity_bands` key to the existing questionnaire config file. | ✓ |
| New small dedicated config/constants file | A new file purely for report-band thresholds, separate from questionnaire content config. | |
| You decide | Left to Claude/researcher. | |

**User's choice:** New key inside config/dssc-questionnaire.json.

**Follow-up:** Should the priority list always show all 6 dimensions, or only the ones needing attention (red/orange)?

| Option | Description | Selected |
|--------|-------------|----------|
| Always show all 6 dimensions | Full sorted list, lowest-to-highest, every dimension included regardless of band. | ✓ |
| Only show dimensions needing attention (red/orange) | Filter list to below-green dimensions; radar chart still shows all 6. | |
| You decide | Left to Claude/researcher. | |

**User's choice:** Always show all 6 dimensions.

---

## Admin aggregation shape

| Option | Description | Selected |
|--------|-------------|----------|
| Both: org-wide average radar + per-initiative list | One blended radar (average per dimension across all initiatives) plus a sortable per-initiative table with a link to each report. | ✓ |
| Org-wide average radar only | Single blended radar, no per-initiative table. | |
| Per-initiative list/table only | Sortable table of every initiative's own scores, no blended radar. | |
| You decide | Left to Claude/researcher. | |

**User's choice:** Both: org-wide average radar + per-initiative list.

**Follow-up:** Which assessment counts per initiative for aggregation?

| Option | Description | Selected |
|--------|-------------|----------|
| Each initiative's latest submitted assessment only | Use only the most recent submitted (not draft) Assessment per initiative; initiatives with zero submitted assessments excluded from the average, shown as "no data yet." | ✓ |
| You decide | Left to Claude/researcher. | |

**User's choice:** Each initiative's latest submitted assessment only.

---

## Claude's Discretion

- Exact SVG generation approach/library or hand-written SVG string-building for the radar polygon.
- Exact route/query-param shape for per-version report viewing (e.g. `?assessment_id=42` vs. path segment vs. new endpoint).
- Exact JSON field names in the report contract (`radar_chart_svg`, `priority_list`, `maturity_bands`, etc.).
- Exact per-initiative table sort order/columns beyond own dimension scores + overall average + report link.
- Visual treatment (badge/empty state) for initiatives with no submitted assessment in the per-initiative admin table.

## Deferred Ideas

None — discussion stayed within phase scope. No scope-creep topics came up.
