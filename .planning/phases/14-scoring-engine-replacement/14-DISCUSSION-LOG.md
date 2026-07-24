# Phase 14: Scoring Engine Replacement - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-23
**Phase:** 14-scoring-engine-replacement
**Areas discussed:** Removal boundary, Scoring surface / API exposure, Completion gate mechanics, Legacy endpoint fate, Incomplete-assessment gating, Legacy test fate

---

## Removal boundary (ZEN Engine / MoSCoW / MAMI framework config)

| Option | Description | Selected |
|--------|-------------|----------|
| Full removal now | Delete zen engine, scoring_engine.py, config/scoring/*, AND config/mami-framework.json. Strip/adapt report_generator.py's MAMI-matrix functions and admin.py's heatmap so they compile without it. | ✓ |
| Minimal removal — leave mami-framework.json in place | Only remove the literal ZEN engine/package and mami-scoring.json. Keep mami-framework.json wired via app.state until Phase 16. | |

**User's choice:** Full removal now.
**Notes:** Rationale: nothing of value survives leaving MAMI-framework structure half-wired since Phase 16 replaces the heatmap/matrix model wholesale anyway.

---

## Scoring surface / formula

**Question asked:** Internal service only (no new endpoint) vs. adding a minimal interim endpoint for the new equal-weight scoring logic.

**User's response:** Did not pick either option directly — instead pasted the client's exact (Dutch) scoring specification to confirm the formula:

> Alle vragen kunnen gescoord worden van 1 punt (zeer laag) tot 5 punten (zeer hoge) volwassenheid. Alle vragen hebben eenzelfde weging, i.e., geen vraag wordt gezien als "belangrijker" dan andere vragen. Dimensies hebben een variërende hoeveelheid vragen. Dimensiescore = Som van alle antwoorden / aantal vragen binnen de dimensie. Resultaat: Minimum score van 1.0, maximum score van 5.0. Hierdoor kunnen de dimensies vergeleken worden ongeacht het aantal vragen.

This matches SCOR-01/02 exactly and is captured as D-02. The API-surface question itself was resolved in the follow-up round below (wired into existing endpoints, no new dedicated route).

---

## /score endpoint fate

| Option | Description | Selected |
|--------|-------------|----------|
| Replace response shape | Change /initiatives/{id}/score to return per-category {category_id, name, score}, dropping FindingRead/severity entirely. | ✓ |
| Remove the endpoint entirely | Delete /initiatives/{id}/score outright; dimension scores only surface via /report/data. | |

**User's choice:** Replace response shape.

---

## Report wiring depth (/report/data, /report, /report/pdf)

| Option | Description | Selected |
|--------|-------------|----------|
| JSON only | Add dimension_scores to /report/data JSON only; leave report.html/PDF template untouched (still shows degraded banner + empty heatmap). | ✓ |
| JSON + a simple line in the HTML/PDF too | Also add a plain list of dimension scores into the Jinja2 template so the PDF shows real numbers now. | |

**User's choice:** JSON only.
**Notes:** Avoids doing template/HTML rendering work that Phase 16 (Report Data Contract, Dual Visualization) explicitly owns.

---

## Completion gate mechanics (SCOR-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Compare against config's full question-id set | Count distinct answered question_ids for the assessment vs. every question_id in dssc-questionnaire.json (52). | ✓ |
| Compare against Assessment.status == submitted | Only compute scores when Assessment.status is 'submitted'; would require Phase 14 to also add the draft→submitted auto-transition. | |

**User's choice:** Compare against config's full question-id set.

---

## Incomplete-assessment gate (endpoint behavior)

| Option | Description | Selected |
|--------|-------------|----------|
| 422 with a clear error | Return HTTP 422 ("Questionnaire not fully answered") from all score/report-producing endpoints when incomplete. | ✓ |
| 200 with a partial/null score marker | Return 200 with dimension_scores omitted/null and an incomplete flag. | |

**User's choice:** 422 with a clear error.
**Notes:** Matches the existing 422 pattern already used in reports.py for "no answers found."

---

## Legacy test fate (ZEN-based benchmark/perf tests)

| Option | Description | Selected |
|--------|-------------|----------|
| Delete both, leave a note | Remove test_scoring_regression.py and test_scoring_perf.py outright; note that Phase 17 owns writing equal-weight-scoring replacements. | ✓ |
| Replace with minimal equivalents now | Write bare-minimum benchmark/perf tests against the new compute function in Phase 14 itself. | |

**User's choice:** Delete both, leave a note.
**Notes:** Full new-logic test coverage is explicitly Phase 17's job per ROADMAP.md.

---

## Claude's Discretion

- Exact module/file naming for the new dimension-scoring service.
- Exact response field names for the new `/score` and `/report/data` shapes (category id/name/score agreed; JSON key naming is planning's call).
- Exact fixed shape of the simplified `/heatmap` degraded response.
- Exact adaptation of `test_reports.py`/`test_report_generator.py` to match the new adapted endpoints.

## Deferred Ideas

None — discussion stayed within phase scope. No scope-creep topics came up.

---

## Follow-up round: cleanup pass ("delete what we won't reuse" review)

**Date:** 2026-07-24
**Trigger:** User asked whether the initial decisions matched a "clean up everything we don't use or aren't going to re-use" philosophy. Re-review found 4 places where the original decisions kept dead code alive in a degraded state rather than deleting it.

### Matrix code (report_generator.py)

| Option | Description | Selected |
|--------|-------------|----------|
| Delete outright | Remove _build_matrix/_build_topic_structure/_build_heatmap_rows/_build_not_yet_recommendations/_build_findings_detail and _RECOMMENDATIONS entirely; simplify generate_report_data/generate_html_report to what still works + dimension_scores. | ✓ |
| Keep degraded-to-empty | Leave functions in place returning empty structures, as originally decided. | |

**User's choice:** Delete outright. Supersedes D-01/D-05 as originally written; now D-01a.

### Degraded-scoring banner (reports.py)

| Option | Description | Selected |
|--------|-------------|----------|
| Remove it | Its premise ("scoring not yet implemented") is false once real scores exist; JSON-only reporting needs no banner. | ✓ |
| Keep it, reworded | Keep a banner with updated wording flagging the HTML/PDF report as incomplete pending Phase 16. | |

**User's choice:** Remove it. Supersedes the original D-05 banner note; now D-05a.

### Admin /heatmap endpoint

| Option | Description | Selected |
|--------|-------------|----------|
| Simplify to trivial response | Strip topic-structure-building logic entirely; return a minimal fixed degraded shape. | ✓ |
| Keep structure-building code, feed it nothing | Keep the existing code path, adapted to run against an empty/stub config, as originally decided. | |

**User's choice:** Simplify to trivial response. Supersedes the original D-01 admin.py note; now D-01b.

### Old MAMI wizard/report/admin-heatmap frontend

| Option | Description | Selected |
|--------|-------------|----------|
| Leave it untouched | Keep Phase 14 backend-only as scoped; old frontend renders against now-empty/undefined data until Phase 15/16 replace it. | ✓ |
| Delete the now-dead frontend pieces too | Pull frontend cleanup into Phase 14, accepting no working questionnaire/report/admin-heatmap UI until Phase 15/16 land. | |

**User's choice:** Leave it untouched — confirmed as-is, no change from the original decision. (Frontend fields will now be `undefined` rather than empty-but-present, since the backend fields are deleted rather than degraded — noted as an accepted consequence, not a new decision.)
