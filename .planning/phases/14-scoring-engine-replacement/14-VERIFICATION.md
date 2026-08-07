---
phase: 14-scoring-engine-replacement
verified: 2026-07-24T09:20:39Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "GoRules ZEN Engine, its rule configs, and MoSCoW-based findings no longer exist anywhere in the codebase (frontend dead code still references the old MoSCoW response shape)"
    addressed_in: "Phase 15 / Phase 16"
    evidence: "14-CONTEXT.md explicitly lists frontend/src/lib/scoring.ts, frontend/src/components/questionnaire/WizardPage.tsx, frontend/src/routes/_app/report.tsx, frontend/src/routes/_app/dashboard.tsx as untouched-this-phase, deliberately deferred to the Phase 15 wizard rebuild and Phase 16 report/admin rebuild (roadmap Phase 16 goal: 'radar chart and a sorted priority list identically in-app and in the mailed PDF' / 'admin view aggregates this same 6-dimension data'). Recorded as a discussed, user-approved scope decision in 14-DISCUSSION-LOG.md ('User's choice: Leave it untouched — confirmed as-is')."
---

# Phase 14: Scoring Engine Replacement Verification Report

**Phase Goal:** Maturity scores are computed via simple equal-weight averaging per dimension, with GoRules ZEN Engine and MoSCoW findings completely removed.
**Verified:** 2026-07-24T09:20:39Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each dimension's score = sum(answers)/question_count, shown as 1.0–5.0 | ✓ VERIFIED | `backend/app/services/dimension_scoring.py::compute_dimension_scores` computes `round(sums.get(cat_id, 0)/n_questions, 2)` per category, derived from config. Confirmed by running `tests/services/test_dimension_scoring.py` live (7/7 pass), including boundary (all-1s=1.0, all-5s=5.0) and precision (3.333…→3.33) tests. |
| 2 | No question/category carries more weight than another | ✓ VERIFIED | No weight multiplier anywhere in `compute_dimension_scores`; each category divides by its own config-derived count. `test_equal_weight_across_different_question_counts` (9-question cat-1 vs 8-question cat-5, same per-answer value) passes live, proving no cross-category weighting. |
| 3 | GoRules ZEN Engine, rule configs, MoSCoW findings no longer exist anywhere in the codebase or dependency manifest | ✓ VERIFIED (backend) / deferred (frontend dead code) | Backend: `grep -r zen backend/app backend/config` → 0 hits (excl. `.venv`); `scoring_engine.py`, `config/scoring/mami-scoring.json`, `config/mami-framework.json` all deleted (confirmed absent on disk); `zen-engine` absent from `pyproject.toml`/`uv.lock` (grep -c = 0 both); `backend/tests/test_zen_removed.py` (AST-walk + substring scan across `backend/app`+`config/`) passes live (4/4 tests). Frontend: `frontend/src/lib/scoring.ts` and `frontend/src/components/questionnaire/FindingsPanel.tsx` still define/render the old MoSCoW `Finding`/`severity`/`critical_count` shape — but both are orphaned dead code (not imported by any route/page; `grep -rn FindingsPanel/triggerScoring` across frontend/src finds only self-references). This is a documented, user-approved scope decision (see Deferred Items) — not an oversight. |
| 4 | Scores/report only shown after 100% completion — no partial/live scoring | ✓ VERIFIED | `assert_assessment_complete` raises `HTTPException(422, "Questionnaire not fully answered")` server-side (never client-trusted) when any config question_id is unanswered or no draft assessment exists; called first in `/score`, and in all four report endpoints (`/report`, `/report/data` GET+POST, `/report/pdf`, `/report/mail`) immediately after the ownership check. Verified live via `test_score_422_when_incomplete`, `test_score_422_when_no_assessment_exists`, and the equivalent `test_reports.py` 422 tests — all pass. |

**Score:** 4/4 truths verified (0 present-but-behavior-unverified)

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Frontend dead code (`frontend/src/lib/scoring.ts`, `frontend/src/components/questionnaire/FindingsPanel.tsx`) still references the removed MoSCoW/ZEN response shape | Phase 15 (wizard rebuild) / Phase 16 (report data contract + dual visualization + admin aggregation) | 14-CONTEXT.md § "Frontend (explicitly NOT touched this phase)" names these exact files as deferred; 14-DISCUSSION-LOG.md records the explicit user decision "Leave it untouched — confirmed as-is." Both files are orphaned (not imported by any live route), so no user-facing flow is currently broken by this. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/services/dimension_scoring.py` | New service: `compute_dimension_scores`, `assert_assessment_complete`, `get_current_assessment` | ✓ VERIFIED | Exists, imports cleanly, all 3 public functions present, config-derived (no hardcoded 52/9-9-9-9-8-8), ruff/mypy clean. |
| `backend/tests/services/test_dimension_scoring.py` | Unit coverage SCOR-01/02/04 | ✓ VERIFIED | 7 tests, all pass live. |
| `backend/app/api/v1/scoring.py` | `/score` repurposed to per-dimension shape + 422 gate | ✓ VERIFIED | `ScoreResponse{initiative_id, dimension_scores}`, `DimensionScore{category_id,name,score}`; no `FindingRead`/zen/mami references (grep=0). Ownership check precedes `assert_assessment_complete`. |
| `backend/tests/api/test_scoring.py` | Happy-path/422/ownership tests | ✓ VERIFIED | 4 tests, all pass live; ownership test explicitly asserts non-422. |
| `backend/app/api/v1/reports.py` | 4 endpoints: dimension_scores + 422 gate ownership-first; degraded-banner mechanism removed | ✓ VERIFIED | `_DEGRADED_SCORING_BANNER_HTML`/`_inject_degraded_banner`/`_degraded_scoring_inputs` absent (grep=0); all 4 routes call ownership-check then `assert_assessment_complete` then (for /report/data) `compute_dimension_scores`. |
| `backend/app/services/report_generator.py` | Trimmed to initiative-info + literal-empty Jinja context | ✓ VERIFIED | 77 lines (down from 313); `_build_matrix`/`_build_topic_structure`/`_build_heatmap_rows`/`_build_not_yet_recommendations`/`_build_findings_detail`/`_RECOMMENDATIONS`/`_ANSWER_LABEL_MAP`/`_aggregate_cell`/`_suggest_next_steps` all absent (grep=0); `generate_html_report` passes literal `heatmap_rows={}`/`not_yet_recommendations=[]`. |
| `backend/app/api/v1/admin.py` | `/heatmap` reduced to fixed degraded response | ✓ VERIFIED | `AdminHeatmapResponse{degraded: bool=True, cells: list=[]}`; `_build_topic_structure` import absent (grep=0). |
| `backend/tests/api/test_reports.py`, `test_report_generator.py`, `test_admin.py` | Adapted assertions for new shapes/gate | ✓ VERIFIED | Assertions for `dimension_scores`/absence of `matrix`/`topic_structure`, degraded shape, 422s — all present; 27/31 pass live (4 failures are a pre-existing local-only WeasyPrint native-library gap, not a phase-14 regression — see Anti-Patterns/Spot-Checks below). |
| `backend/tests/test_zen_removed.py` | Static regression test locking SCOR-03 | ✓ VERIFIED | 4 tests, all pass live; scoped to `backend/app`+`config/` (not `backend/tests`), tokens built from parts. |
| `docs/api/openapi.json` | Regenerated, diff-clean | ✓ VERIFIED | Re-ran `scripts/export_openapi.py` live; `git diff --exit-code` on the file exits 0. |
| `config/scoring/mami-scoring.json`, `config/mami-framework.json`, `backend/app/services/scoring_engine.py` | Deleted | ✓ VERIFIED | Confirmed absent via `find` (only matches were `.venv` unrelated files and the removal test itself). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `scoring.py` | `dimension_scoring.py` | `assert_assessment_complete`/`compute_dimension_scores` imports | ✓ WIRED | Confirmed by source read; called in that order after ownership check. |
| `reports.py` | `dimension_scoring.py` | same imports, called in all 4 routes | ✓ WIRED | Confirmed in all 4 route bodies; `/report/data` (GET+POST) additionally sets `data["dimension_scores"]`. |
| `dimension_scoring.py` | `QuestionnaireAnswer`/`Assessment` | single-assessment-scoped SQLModel `select` | ✓ WIRED | `get_current_assessment` filters `Assessment.initiative_id`+`status==draft`, ordered by `created_at desc`, `.first()` — does not reuse the multi-assessment `_get_answers_for_initiative` join. |
| `main.py`/`deps.py` | `mami_config.py` | surviving `get_dssc_questionnaire_config`/`load_dssc_questionnaire_config` | ✓ WIRED | `load_mami_config`/`get_scoring_dir` removed; legacy/DSSC loaders untouched and still wired at lifespan startup (app imports and `test_health.py` passes live). |

### Behavioral Spot-Checks (live-run, not trusted from SUMMARY)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| App imports with zen-engine removed | `cd backend && uv run python -c "import app.main"` | exit 0 | ✓ PASS |
| Dimension-scoring unit tests | `uv run pytest tests/services/test_dimension_scoring.py -q` | 7 passed | ✓ PASS |
| Static ZEN/MoSCoW removal test | `uv run pytest tests/test_zen_removed.py -q` | 4 passed | ✓ PASS |
| /score integration tests | `uv run pytest tests/api/test_scoring.py -q` | 4 passed | ✓ PASS |
| /report* + /admin/heatmap integration tests | `uv run pytest tests/api/test_reports.py tests/services/test_report_generator.py tests/api/test_admin.py -q` | 27 passed, 4 failed | ⚠️ See note below |
| Full quick suite | `uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` | 91 passed, 4 failed | ⚠️ See note below |
| Lint/type checks | `uv run ruff check .` / `uv run mypy app --ignore-missing-imports` | all clean | ✓ PASS |
| OpenAPI freshness | `uv run python scripts/export_openapi.py && git diff --exit-code -- docs/api/openapi.json` | exit 0 | ✓ PASS |

**Note on the 4 failing tests:** `test_mail_report_generates_pdf_and_sends_email`, `test_mail_report_dev_mode_skips_resend_send`, `test_download_report_pdf_returns_pdf_content_type`, `test_download_report_pdf_incomplete_assessment_returns_422` fail locally with `OSError: cannot load library 'libgobject-2.0-0'`. Traced the failure to WeasyPrint's cffi native-library import (`from weasyprint import HTML as WeasyHTML`), which is unconditional at the top of `download_report_pdf`/inside `_send_report_email` — this import position is unchanged from before Phase 14 and is the same pre-existing local-machine gap first logged in Phase 13's `deferred-items.md` (recurring, documented again in this phase's `deferred-items.md`). Confirmed via traceback that the failure occurs before any of Phase 14's reworked code executes. Not a phase-14 regression.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SCOR-01 | 14-01 | Dimension score = sum/count, range 1.0-5.0 | ✓ SATISFIED | `compute_dimension_scores`, live-tested. |
| SCOR-02 | 14-01 | Equal weighting, no question/category weight | ✓ SATISFIED | No weight term in formula; `test_equal_weight_across_different_question_counts` passes. |
| SCOR-03 | 14-04 | ZEN Engine + MoSCoW fully removed, not dual-maintained | ✓ SATISFIED (backend) | Verified via grep, file-existence checks, and live `test_zen_removed.py` run. Frontend dead-code exception logged as a deferred item (see above). |
| SCOR-04 | 14-01, 14-02, 14-03 | Scores/report only computed once 100% answered | ✓ SATISFIED | `assert_assessment_complete` gate live-verified across `/score` and all 4 report endpoints. |

No orphaned requirements — all 4 phase-14 requirement IDs (SCOR-01..04) declared across the 4 plans match REQUIREMENTS.md's Phase 14 mapping exactly (all marked Complete there).

### Anti-Patterns Found

None in the phase's modified backend files. Scanned `dimension_scoring.py`, `scoring.py`, `reports.py`, `report_generator.py`, `admin.py`, `main.py`, `deps.py`, `mami_config.py`, `test_zen_removed.py` for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` — zero hits.

### Human Verification Required

None. All must-have truths are backed by live-executed automated tests (unit + integration), not just presence/wiring checks — including the two behavior-dependent truths (the SCOR-04 completion-gate state transition, and the ownership-before-completion-gate ordering invariant), both of which are exercised by passing named tests (`test_score_422_when_incomplete`, `test_score_ownership_before_completion_gate`, and their `test_reports.py` equivalents), confirmed by re-running them in this verification pass rather than trusting SUMMARY.md's claims.

### Gaps Summary

No blocking gaps. One item is tracked as **deferred** rather than a gap: frontend dead code (`frontend/src/lib/scoring.ts`, `frontend/src/components/questionnaire/FindingsPanel.tsx`) still names MoSCoW concepts (`Finding`, `severity`, `critical_count`) and would violate a maximally literal reading of roadmap Success Criterion 3 ("no longer exist anywhere in the codebase"). This is not scope creep or an oversight — it was explicitly identified, discussed, and deferred during phase discussion (`14-CONTEXT.md`, `14-DISCUSSION-LOG.md`, with the user's own recorded choice to leave it untouched), both referenced files are orphaned (imported by nothing else in the app, confirmed via grep), and Phase 15 (wizard rebuild) / Phase 16 (report/admin rebuild) are the roadmap-designated owners of replacing this exact frontend surface. The backend — where the actual GoRules ZEN Engine, its dependency, its rule configs, and the MoSCoW scoring computation lived — is unambiguously and completely removed, locked in by a passing static regression test.

The 4 locally-failing WeasyPrint tests are a pre-existing, previously-documented, environment-only gap (missing native library on this dev machine), not caused by any Phase 14 change, and CI (which has the library installed) is the authoritative signal per CLAUDE.md.

---

_Verified: 2026-07-24T09:20:39Z_
_Verifier: Claude (gsd-verifier)_
