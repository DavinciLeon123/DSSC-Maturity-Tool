# Phase 16: Report Data Contract, Dual Visualization & Admin Aggregation - Context

**Gathered:** 2026-07-26
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase builds the actual report *presentation* layer on top of Phase 14's scoring math and Phase 15's Assessment/history schema:

1. **RPRT-01/02** — a radar/spider chart (all 6 dimensions at a glance) and a sorted priority list (lowest→highest maturity, with color indicator), both driven by one report data contract.
2. **RPRT-03** — the red/orange/green color-band thresholds (1.0-2.0 / 2.0-3.5 / 3.5-5.0) are defined exactly once in config and used identically by both the chart and the list.
3. **RPRT-04** — the in-app report view and the mailed PDF render from one shared JSON data contract, not two independently-computed views.
4. **ADMN-01** — the admin `/heatmap` endpoint (currently a fixed `{degraded: true, cells: []}` stub left by Phase 14) is rebuilt into a real cross-initiative aggregation using the new 6-category model, replacing the old 4×3 topic heatmap entirely.

**Out of scope for this phase:** the underlying scoring math (Phase 14, done — `compute_dimension_scores` sum/n formula is not revisited here), the questionnaire wizard/save/retake mechanics (Phase 15, done), automated test coverage for this phase's new code (Phase 17), and auth/security hardening (Phase 18).

</domain>

<decisions>
## Implementation Decisions

### Chart rendering strategy
- **D-01:** No JS charting library is added. The radar chart is produced by **one server-side SVG generator function** (Python), used identically for both surfaces — this guarantees pixel-identical charts in-app and in the mailed PDF, avoids a new frontend dependency, and follows the existing hand-rolled-SVG/CSS-grid precedent already in this codebase (`HeatmapMatrix`/`HeatmapGrid` in `report.tsx`/`admin.heatmap.tsx`).
- **D-02:** The generated SVG **markup itself is embedded as a string field in the report JSON contract** (e.g. `radar_chart_svg`), computed once server-side. The frontend renders that exact markup as-is; the Jinja `report.html` template embeds the same string (e.g. `{{ radar_chart_svg | safe }}`) for the PDF. There is no separate client-side polygon-math reimplementation — one computation, reused verbatim on every surface. This is the strictest reading of "one shared JSON contract" (RPRT-04): the contract carries the rendered visualization itself, not just raw numbers each surface redraws independently.
- No in-app chart interactivity (hover/tooltips/animation) is in scope — this was a deliberate tradeoff for guaranteed visual parity and zero new dependencies.

### Report data source & versioning
- **D-03:** The report (chart + priority list, both surfaces) always renders from the **frozen `Assessment.dimension_scores` snapshot** (written at submission time, per Phase 15's D-15/versioning work) — never a live recompute of `compute_dimension_scores` for a submitted assessment. This matches the phase goal's "one frozen report data contract" framing and keeps old reports immune to later config/scoring drift, consistent with how Phase 15's history comparison table already works.
- **D-04:** The report is **viewable per specific assessment version**, not just "the latest." The report endpoint/route takes an assessment identifier so a user can open the full radar+priority-list report for any past submitted version from their history page (Phase 15's `GET /initiatives/{id}/assessments` list), not only the most recent one. Both the in-app route and the PDF-generation path need to resolve a specific `Assessment.id`, not just "the initiative's current assessment."

### Color bands & priority list scope
- **D-05:** The maturity color-band thresholds (1.0-2.0 red / 2.0-3.5 orange / 3.5-5.0 green) are defined as a **new top-level key inside the existing `config/dssc-questionnaire.json`** (e.g. `maturity_bands`), not a separate new config file. This keeps all questionnaire-and-scoring-related config in one file, reusing the existing `get_dssc_questionnaire_config()` loading/caching path (no new config loader needed).
- **D-06:** The sorted priority list **always shows all 6 dimensions**, lowest-to-highest maturity, regardless of color band — not filtered down to only red/orange "needs attention" dimensions. Matches the literal requirement text and gives a complete picture, not just a to-do list.

### Admin aggregation shape
- **D-07:** The admin aggregated view shows **both**: (a) one org-wide averaged radar chart (average score per dimension, blended across all initiatives), and (b) a per-initiative table/list below it, each row showing that initiative's own dimension scores and overall average with a link to its individual report — closest to what the old 4×3 heatmap gave admins (a summary view plus per-initiative breakdown), just rebuilt for the 6-category model.
- **D-08:** For aggregation, each initiative contributes **only its latest submitted assessment** (never a draft, never averaged across an initiative's own retake history). Initiatives with **zero submitted assessments are excluded** from the org-wide average radar and shown as "no data yet" in the per-initiative table — they don't contribute a zero/blank score that would skew the aggregate.

### Claude's Discretion
- Exact SVG generation approach/library (or hand-written SVG string-building) for the radar polygon (D-01/D-02) — geometry/library choice is an implementation detail, not a user preference.
- Exact route/query-param shape for per-version report viewing (D-04) — e.g. `/report?assessment_id=42` vs. a path segment vs. a new endpoint entirely.
- Exact JSON field names in the report contract (`radar_chart_svg`, `priority_list`, `maturity_bands`, etc.) — naming is a planning-time decision, not settled here.
- Exact per-initiative table sort order/columns beyond "own dimension scores + overall average + link to report" (D-07) — e.g. default sort by overall average vs. by name.
- Whether/how a small "no data yet" badge or empty state is shown for initiatives with no submitted assessment in the per-initiative table (D-08) — visual treatment is a UI-pass concern, not settled here.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project/Milestone Context
- `.planning/PROJECT.md` — v2.0 milestone goals, dual-visualization/color-band target feature description, Key Decisions table through Phase 15
- `.planning/REQUIREMENTS.md` — RPRT-01/02/03/04, ADMN-01 full requirement text and Traceability table
- `.planning/ROADMAP.md` §Phase 16 — phase goal and success criteria this CONTEXT.md elaborates on

### Prior Phase Context (load-bearing decisions this phase builds on)
- `.planning/phases/14-scoring-engine-replacement/14-CONTEXT.md` — D-02/D-03 there: locked `sum(answers)/n` dimension-scoring formula and the `dimension_scoring.py` service this phase's frozen snapshots were computed from; D-01a/D-05a there: `report_generator.py`'s old MAMI-matrix builder functions and `_DEGRADED_SCORING_BANNER_HTML` were already deleted, and `admin.py`'s `/heatmap` was reduced to a fixed degraded stub explicitly pending this phase's rebuild (ADMN-01)
- `.planning/phases/15-questionnaire-submission-api-wizard-ui-save-reliability/15-CONTEXT.md` — D-15 there: `Assessment.version` incrementing on retake; D-16/D-17 there: the history view/endpoint (`GET /initiatives/{id}/assessments`) and frozen `dimension_scores` snapshot this phase's D-03/D-04 directly reuse

### Codebase State (from this session's scouting — no `.planning/codebase/*.md` maps exist in this repo, same gap noted in Phases 13/14's CONTEXT files)
- `backend/app/api/v1/reports.py` (291 lines) — `POST /initiatives/{id}/report` (L100-156, renders `report.html`, upserts `ComplianceReport`), `GET /report` (L159-179, returns stored HTML), `POST`/`GET /report/data` (L182-228, currently calls `generate_report_data` + `compute_dimension_scores` live — must change per D-03 to read the frozen snapshot instead, and per D-04 to accept an assessment identifier), `GET /report/pdf` (L231-257), `POST /report/mail` (L260-290) — all four rendering/delivery endpoints are primary rebuild targets for the shared contract (D-01/D-02/D-03/D-04)
- `backend/app/services/report_generator.py` (76 lines) — `generate_report_data` (L52-76) currently returns only `{"initiative": {...}}`; `generate_html_report` (L28-49) renders `report.html` with empty `heatmap_rows`/`not_yet_recommendations` stubs left over from Phase 14 — both are rebuild targets to add `dimension_scores`, `priority_list`, `radar_chart_svg`, `maturity_bands` per the new contract
- `backend/app/templates/report.html` (264 lines) — still renders the **old 4-category × 3-dimension MAMI matrix** (scheme/participants/data/services × human_readable/machine_readable/trust_anchors, L188-220) — this is stale/disconnected from the new 6-category data and must be rebuilt for the new contract + embedded SVG (D-02)
- `backend/app/services/dimension_scoring.py` — `compute_dimension_scores(session, assessment_id, config) -> list[dict]` (L114-149), one dict per category `{category_id, name, score}` in config order; per D-03 this stays the Phase-14 live-compute path used only to *produce* the frozen snapshot at submission time, not called again for rendering a submitted report
- `backend/app/schemas/assessment.py` (L12-17) — `AssessmentSummary {id, version, submitted_at, overall_average, dimension_scores}` — the frozen-snapshot shape from Phase 15 this phase's report contract reuses per D-03
- `backend/app/api/v1/initiatives.py` (L200-225) — `GET /initiatives/{initiative_id}/assessments`, owner-scoped, submitted-only, already returns the frozen snapshot per version — the natural source for D-04's per-version report links from the history page
- `backend/app/api/v1/admin.py` — `AdminHeatmapResponse` (L30-37, currently `{degraded: bool = True, cells: list[dict] = []}`), `GET /admin/heatmap` (L324-338, always returns the fixed degraded stub) — full rebuild target for D-07/D-08; `GET /admin/initiatives` (L174-209, `AdminInitiativeRow` L54-61) uses a raw-SQL join pattern (initiative→user→assessment→questionnaire_answer) that's a useful precedent to adapt for "each initiative's latest submitted assessment," though it does not currently filter by `AssessmentStatus.submitted` or pick "latest only" — that filtering logic is new
- `frontend/src/routes/_app/report.tsx` — currently fetches `POST /initiatives/{id}/report/data` and expects the stale `ReportData{initiative, matrix, topic_structure, answers}` shape (L58-69); its hand-rolled `HeatmapMatrix`/`StatusChip` grid (navy `#06004f`/green `#399e5a`, Rubik font) is the closest existing visual-styling precedent to match, even though its data shape is being fully replaced
- `frontend/src/routes/_app/admin.heatmap.tsx` — same stale 4×3-matrix shape (`HeatmapGrid`/`CountPill`), full rebuild target for ADMN-01
- `frontend/src/lib/reports.ts` — only wraps the HTML `/report` POST/GET today, not `/report/data` — needs extending for the new JSON contract
- `config/dssc-questionnaire.json` — 6 categories are the radar's 6 axes: `cat-1 Governance` (8q), `cat-2 Business` (9q), `cat-3 Legal` (6q), `cat-4 Interoperability` (9q), `cat-5 Control over Data & Trust` (9q), `cat-6 Value Creation` (11q); this is also where D-05's new `maturity_bands` key gets added
- `frontend/package.json` (L14-20) — confirmed no charting library installed (only `antd ^6.3.0`) — consistent with D-01's no-new-dependency decision
- No existing `band`/`threshold` constant anywhere in the backend (confirmed via repo-wide grep) — D-05's `maturity_bands` config key is genuinely new, not a rename of something existing

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AssessmentSummary` schema + `GET /initiatives/{id}/assessments` (Phase 15) — already returns exactly the frozen per-version `dimension_scores` this phase's report contract needs; no new frozen-snapshot mechanism required, only consumption of what already exists.
- `get_dssc_questionnaire_config()` FastAPI lifespan-cached config loader — direct precedent for how D-05's new `maturity_bands` key gets read (same config, no new loader).
- Hand-rolled SVG/CSS-grid precedent (`HeatmapMatrix` in `report.tsx`, `HeatmapGrid` in `admin.heatmap.tsx`) — establishes that this codebase already favors hand-built visualizations over charting libraries, directly supporting D-01.

### Established Patterns
- Phase 14 deliberately left `report_generator.py`/`report.html`/`admin.py`'s `/heatmap` as deletion-then-stub rather than degrade-in-place, explicitly flagging this phase (ADMN-01, RPRT-*) as the real rebuild — this phase is not fighting legacy MAMI code, it's building on clean stubs.
- `docs/api/openapi.json` regeneration is a hard CI gate (docs-freshness, per `CLAUDE.md`) — any response-model change to `/report/data` or the new admin aggregation endpoint requires regenerating this file before commit.

### Integration Points
- The report contract (dimension_scores, priority_list, radar_chart_svg, maturity_bands) needs to be computable both (a) at submission time to freeze into `Assessment.dimension_scores` (Phase 15's existing write path) and (b) at read time from that frozen data for rendering — planning should confirm whether the frozen snapshot itself should be widened to store the full contract (including the SVG) or whether the SVG/priority-list are cheap enough to regenerate from the frozen numeric scores on every read.
- The new admin aggregation endpoint will need a way to resolve "each initiative's latest submitted Assessment" — likely a new query/join in `admin.py`, adapting the existing `GET /admin/initiatives` raw-SQL pattern rather than inventing a new query style.

</code_context>

<specifics>
## Specific Ideas

No literal visual mockups or copy were provided during this discussion — decisions here are behavioral/structural (chart rendering strategy, data source, config location, aggregation shape), not pixel-level design. `ROADMAP.md` flags this phase with `UI hint: yes`, so a follow-up `/gsd-ui-phase` design pass is expected to cover the actual radar-chart visual styling, priority-list layout, and admin-table presentation — this discussion deliberately stayed at the behavior/data level rather than pre-empting that.

The consistent theme across all four areas: **favor one shared, simple, server-computed source of truth over duplicated or client-recomputed logic** — a single SVG generator embedded verbatim in both surfaces (not two chart implementations), a frozen per-assessment snapshot as the report's only data source (not live recompute), one config location for color bands (not duplicated thresholds), and "latest submitted only" as the one clear rule for what counts toward admin aggregation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope (report contract, chart/PDF rendering, color bands, admin aggregation). No scope-creep topics came up.

### Reviewed Todos (not folded)
None — no pending todos existed to review (`.planning/todos/pending/` is empty).

</deferred>

---

*Phase: 16-report-data-contract-dual-visualization-admin-aggregation*
*Context gathered: 2026-07-26*
