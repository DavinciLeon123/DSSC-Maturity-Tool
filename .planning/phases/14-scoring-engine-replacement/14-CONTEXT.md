# Phase 14: Scoring Engine Replacement - Context

**Gathered:** 2026-07-23
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase replaces the entire scoring layer: GoRules ZEN Engine + MoSCoW-findings scoring is deleted, root and branch, and replaced with simple equal-weight dimension averaging (SCOR-01/02/03). It also enforces that scores/reports are never computed or shown for a partially-answered assessment (SCOR-04).

This phase does **not** build the wizard, submission API, retake history (Phase 15), or the frozen report data contract / radar chart / priority list / admin aggregation (Phase 16). It has no UI hint — the frontend is untouched. Where this phase's removal work would otherwise leave existing backend endpoints broken (because they currently depend on the deleted ZEN engine), those endpoints are adapted just enough to compile and return real per-category scores instead of MoSCoW findings — not rebuilt into the real Phase 15/16 contract.

</domain>

<decisions>
## Implementation Decisions

### Removal boundary (SCOR-03) — cleanup-first: delete what won't be reused, don't just degrade it
- **D-01:** Full removal now, not partial. Delete: the `zen` Python package (dependency in `pyproject.toml`/`uv.lock`), `backend/app/services/scoring_engine.py`, `config/scoring/` (the ZEN JDM rule directory, i.e. `mami-scoring.json`), **and** `config/mami-framework.json` (the MAMI 4×3 category/dimension/topic/`moscow_level` structural config) — even though the latter is structural metadata rather than a literal "rule config," it exists solely to drive MoSCoW-priority-tagged findings and the old 4×3 heatmap, both of which are being replaced wholesale by Phase 16. Nothing of value survives leaving it half-wired.
- Also remove: `app.state.zen_engine` / `app.state.mami_config` wiring in `main.py` lifespan, `get_zen_engine`/`get_mami_config` in `core/deps.py`, and `load_mami_config()`/`get_scoring_dir()` in `mami_config.py`.
- **D-01a (revised — supersedes an earlier "degrade to empty" draft):** `report_generator.py`'s MAMI-matrix-building functions (`_build_matrix`, `_build_topic_structure`, `_build_heatmap_rows`, `_build_not_yet_recommendations`, `_build_findings_detail`) and the 27-entry `_RECOMMENDATIONS` dict are **deleted outright**, not kept as empty/degraded stubs. None of this code is reused — Phase 16 rebuilds the report contract from scratch. `generate_report_data`/`generate_html_report` are simplified to only what still works (initiative info) plus the new `dimension_scores` field (D-05) — no dead matrix-building code left behind for Phase 16 to delete later.
- **D-01b (revised):** `admin.py`'s `/heatmap` endpoint is simplified to a trivial fixed degraded response (e.g. `{"degraded": true, "cells": []}` or equivalent minimal shape) — the topic-structure-building logic that currently reads `mami_config` is stripped out entirely, not preserved and fed an empty config. Phase 16 replaces this endpoint's whole model anyway (ADMN-01), so there's no value in keeping the old structure-building code path around.

### New scoring logic (SCOR-01/02)
- **D-02 (locked formula, client-confirmed verbatim):** `dimension_score = sum(answers in that dimension) / number of questions in that dimension`. Range 1.0–5.0. Every question is equally weighted; no question or category carries more weight than another. Dimensions (categories) have varying question counts (9/9/9/9/8/8 in the current placeholder config) — the formula must divide by each dimension's own question count, not a fixed constant, so dimensions remain comparable regardless of size.
- **D-03:** New scoring logic lives as an internal service (e.g. `backend/app/services/dimension_scoring.py` or similar naming — exact module name is Claude's discretion), computing per-category scores from `QuestionnaireAnswer` rows joined through `Assessment`, against the 6 categories defined in `config/dssc-questionnaire.json`. No dedicated new API endpoint is added purely for this — it's surfaced by adapting existing endpoints (see below), not by inventing a new route.

### Legacy endpoint adaptation
- **D-04:** `POST /initiatives/{id}/score` (`backend/app/api/v1/scoring.py`) has its response shape changed: drop `FindingRead`/`severity`/MoSCoW-findings entirely, return the new per-category shape instead (e.g. `{category_id, name, score}` list) computed via the new dimension-scoring service. The endpoint itself is kept, just repurposed.
- **D-05:** `/report/data`, `/report` (HTML), `/report/pdf`, `/report/mail` (`backend/app/api/v1/reports.py`) get a **new field** added to the JSON returned by `/report/data` (e.g. `"dimension_scores": [...]`) using the new scoring service. Per D-01a, the old matrix/heatmap/topic_structure fields are **removed from the response entirely** (not present-but-empty) since their builder functions are deleted, not degraded. **JSON only** — the Jinja2 `report.html` template and the PDF it renders from are NOT touched this phase; Phase 16 owns real HTML/PDF rendering of dimension scores (Report Data Contract, Dual Visualization).
- **D-05a (revised — supersedes an earlier "reconsider wording" draft):** The `_DEGRADED_SCORING_BANNER_HTML` / `_inject_degraded_banner` mechanism in `reports.py` is **removed entirely**, not reworded. Its premise ("scoring not yet implemented") is false once real dimension scores exist — the HTML/PDF report simply won't show them yet (JSON-only, per D-05), which needs no banner to explain; Phase 16 builds the real report view.

### Completion gate (SCOR-04)
- **D-06:** "Fully answered" is determined by comparing the distinct `question_id`s answered for the assessment's current `Assessment` row against the **full set of question IDs in `config/dssc-questionnaire.json`** (all 52) — not by `Assessment.status`. No auto-transition of `Assessment.status` from `draft` to `submitted` is added in this phase; that remains Phase 15's explicit-submission job.
- **D-07:** When an assessment is incomplete, `/score`, `/report`, `/report/data`, `/report/pdf`, and `/report/mail` all return **HTTP 422** with a clear message (e.g. "Questionnaire not fully answered") — matching the existing 422 pattern already used in `reports.py` for "no answers found." No partial/live scores are ever returned, per SCOR-04's literal wording.

### Legacy test fate
- **D-08:** `backend/tests/benchmark/test_scoring_regression.py` and `backend/tests/perf/test_scoring_perf.py` (both import `create_scoring_engine`/`score_all_answers` from the soon-deleted `scoring_engine.py`) are **deleted outright** in this phase, not replaced with new-engine equivalents. Full test coverage for the new scoring logic is explicitly Phase 17's job ("Test Coverage — New Scoring, Questionnaire & Visualization Logic"). Leave a note (deferred-items or CONTEXT-equivalent) that Phase 17 owns writing their equal-weight-scoring replacements, so the perf/benchmark CI jobs going quiet on scoring coverage between Phase 14 and Phase 17 isn't mistaken for an oversight.
- `backend/tests/test_health.py`'s `client.app.state.mami_config is not None` / `zen_engine is not None` assertions must be updated/removed to match D-01's removal of both from `app.state`.
- `backend/tests/api/test_reports.py` and `backend/tests/services/test_report_generator.py` (which reference the ZEN/MoSCoW-shaped functions) will need adaptation to keep passing against the adapted `report_generator.py`/`reports.py` — exact test changes are Claude's discretion during planning, consistent with D-01/D-04/D-05.

### Claude's Discretion
- Exact module/file naming for the new dimension-scoring service (D-03).
- Exact response field names for the new `/score` and `/report/data` shapes (D-04/D-05) — category id/name/score is the agreed shape, exact JSON key naming is planning's call.
- Exact fixed shape of the simplified `/heatmap` degraded response (D-01b).
- Exact adaptation of `test_reports.py`/`test_report_generator.py` to match the new adapted endpoints (now testing deletion + simplification, not degradation).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project/Milestone Context
- `.planning/PROJECT.md` — v2.0 milestone goals, equal-weight scoring target feature description
- `.planning/REQUIREMENTS.md` — SCOR-01/02/03/04 full requirement text and Traceability table
- `.planning/ROADMAP.md` §Phase 14 — phase goal and success criteria this CONTEXT.md elaborates on; also see §Phase 16 for how this phase's dimension scores get consumed into the real report contract
- `.planning/phases/13-new-questionnaire-config-schema-data-model-migration/13-CONTEXT.md` — prior phase; Assessment-first schema (D-06/D-07 there) this phase's scoring reads from
- `.planning/phases/13-new-questionnaire-config-schema-data-model-migration/13-VERIFICATION.md` — confirms Phase 13's schema/migration is fully verified and stable to build on

### Codebase State (no `.planning/codebase/*.md` maps exist in this repo — same gap noted in Phase 13's CONTEXT; not re-created speculatively here)
- `backend/app/services/scoring_engine.py` — ZEN-based scoring, full-file deletion target (D-01)
- `backend/app/services/mami_config.py` — `load_mami_config()`/`get_scoring_dir()` deletion targets (D-01); `load_dssc_questionnaire_config()` (the new-config loader, from Phase 13) is the one this phase's scoring service reads categories/questions from
- `config/dssc-questionnaire.json` — new universal config; 6 categories (`cat-1`..`cat-6`), currently 9/9/9/9/8/8 questions each, each question has `default_options`-inherited or per-question `options` array mapping label→1-5 score
- `backend/app/models/assessment.py` — `Assessment`/`AssessmentStatus` (draft/submitted); scoring reads answers scoped to a specific `Assessment.id`, not `Initiative.id` directly
- `backend/app/models/questionnaire.py` — `QuestionnaireAnswer` (assessment_id, question_id, category_id, score 1-5) — the exact rows the new scoring service sums/averages
- `backend/app/main.py` — lifespan wiring for `app.state.mami_config`/`app.state.zen_engine`, deletion targets (D-01)
- `backend/app/core/deps.py` — `get_zen_engine`/`get_mami_config` dependency functions, deletion targets (D-01)
- `backend/app/api/v1/scoring.py` — `/initiatives/{id}/score` endpoint, response-shape replacement target (D-04)
- `backend/app/api/v1/reports.py` — `/report`, `/report/data`, `/report/pdf`, `/report/mail`; `_degraded_scoring_inputs`, `_DEGRADED_SCORING_BANNER_HTML`, `_inject_degraded_banner` — `_DEGRADED_SCORING_BANNER_HTML`/`_inject_degraded_banner` are deletion targets (D-05a), the rest is adaptation target (D-05)
- `backend/app/services/report_generator.py` — `_build_matrix`/`_build_topic_structure`/`_build_heatmap_rows`/`_build_not_yet_recommendations`/`_build_findings_detail`/`_RECOMMENDATIONS` are **deletion targets** (D-01a); `generate_report_data`/`generate_html_report` are simplified accordingly and `generate_report_data` gets the new `dimension_scores` field (D-05)
- `backend/app/api/v1/admin.py` (`/heatmap`, ~lines 334-410) — aggregated heatmap reading `mami_config`; topic-structure-building logic is a **deletion target**, replaced with a trivial fixed degraded response (D-01b); full replacement with the new 6-category model is Phase 16's ADMN-01 job, not this phase's
- `backend/pyproject.toml` / `uv.lock` — `zen` package removal target (D-01)
- `backend/tests/benchmark/test_scoring_regression.py`, `backend/tests/perf/test_scoring_perf.py` — deletion targets (D-08)
- `backend/tests/test_health.py` — `app.state.mami_config`/`app.state.zen_engine` assertions need updating (D-08)
- `backend/tests/conftest.py` — imports `load_mami_config` for a fixture (line ~22-28); needs adaptation once that loader is deleted
- `backend/tests/api/test_reports.py`, `backend/tests/services/test_report_generator.py` — adaptation needed to match D-01/D-04/D-05 changes

### Frontend (explicitly NOT touched this phase — informational only)
- `frontend/src/lib/scoring.ts`, `frontend/src/lib/reports.ts`, `frontend/src/components/questionnaire/WizardPage.tsx`, `frontend/src/routes/_app/report.tsx`, `frontend/src/routes/_app/dashboard.tsx` — all call the endpoints this phase adapts (`/score`, `/report/data`, `/report/pdf`). **Note (revised from an earlier draft):** because the old matrix/heatmap/topic_structure fields are now deleted from the response (D-01a), not merely empty, these fields will be `undefined` rather than present-with-empty-value — the old frontend may render more visibly broken (missing data) than a softer "empty state" would have looked. This was confirmed acceptable: no frontend code changes are in scope here regardless — Phase 15/16 replace this UI wholesale, and an explicitly-broken page during that gap is preferable to keeping dead builder code alive just to produce a softer empty state.
- Same applies to `frontend/src/routes/_app/admin` (or equivalent) heatmap page, which calls `/heatmap` — now a trivial fixed degraded shape (D-01b) instead of the old topic/dimension cell structure.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Assessment`/`QuestionnaireAnswer` schema from Phase 13 (assessment_id → category_id/score) is already exactly shaped for this phase's per-category sum/n computation — no schema change needed.
- FastAPI lifespan pattern (`app.state`) — same pattern used for `zen_engine`/`mami_config`, now being torn down; no new singleton needed for the new scoring service since it's pure computation over DB rows + the already-cached `dssc_questionnaire_config`.
- Existing 422 error pattern in `reports.py` ("No answers found. Please complete the questionnaire first.") — direct precedent for the new completion-gate 422 (D-07).

### Established Patterns
- Phase 13 established a "degrade to zero/empty rather than crash" precedent for MAMI-matrix code hitting the new schema (`_degraded_scoring_inputs`, `AdminHeatmapResponse.degraded` flag, `_DEGRADED_SCORING_BANNER_HTML`). Phase 14 deliberately **breaks with that precedent** for code that will never be reused: rather than keep MAMI-matrix builder functions alive returning empty structures, this phase deletes them outright (D-01a/D-01b/D-05a) since Phase 13's degrade-in-place approach made sense for schema-in-transition code with a near-term real replacement, but code Phase 16 rebuilds from scratch has no such need. The `AdminHeatmapResponse.degraded` flag itself is kept (simplified endpoint still reports degraded status), just no longer backed by dead structure-building logic.
- `docs/api/openapi.json` regeneration is a hard CI gate (docs-freshness) — any response-model change to `/score` or `/report/data` requires regenerating this file before commit, per CLAUDE.md.

### Integration Points
- `backend/app/api/v1/scoring.py` and `reports.py` both currently `Depends(get_zen_engine)`/`Depends(get_mami_config)` — both dependencies are removed (D-01), so both files' route signatures change regardless of the response-shape decisions above.
- `docs/security/` SBOM generation (per CLAUDE.md) will reflect the `zen` package removal automatically next time `staging.yml`/`main.yml`/`release.yml` run — no manual action needed this phase.

</code_context>

<specifics>
## Specific Ideas

The user provided the client's exact scoring specification verbatim (in Dutch), which is captured as D-02 and matches SCOR-01/02 precisely:

> Alle vragen kunnen gescoord worden van 1 punt (zeer laag) tot 5 punten (zeer hoge) volwassenheid. Alle vragen hebben eenzelfde weging... Dimensies hebben een variërende hoeveelheid vragen. Dimensiescore = Som van alle antwoorden / aantal vragen binnen de dimensie. Resultaat: Minimum score van 1.0, maximum score van 5.0.

No other specific UI/content examples were given — this phase is backend scoring-logic only, no user-facing surface (no UI hint).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope (scoring logic + ZEN/MoSCoW removal + completion gating). No scope-creep topics came up.

### Reviewed Todos (not folded)
None — no pending todos existed to review (`.planning/todos/pending/` is empty).

</deferred>

---

*Phase: 14-scoring-engine-replacement*
*Context gathered: 2026-07-23*
