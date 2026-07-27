---
phase: 16-report-data-contract-dual-visualization-admin-aggregation
plan: 03
subsystem: backend-admin-aggregation
tags: [admin-aggregation, radar-svg, latest-submitted-query, org-average]
dependency_graph:
  requires:
    - get_maturity_band (16-01)
    - generate_radar_svg (16-01)
    - build_priority_list (16-01)
    - config/dssc-questionnaire.json maturity_bands key (16-01)
  provides:
    - build_admin_aggregate
    - AdminAggregateResponse
    - AdminInitiativeAggregateRow
    - GET /admin/heatmap (rebuilt)
  affects:
    - backend/app/services/admin_aggregation.py
    - backend/app/api/v1/admin.py
    - backend/tests/api/test_admin.py
    - backend/tests/services/test_admin_aggregation.py
    - docs/api/openapi.json
tech_stack:
  added: []
  patterns:
    - "LEFT JOIN LATERAL raw-SQL query (session.execute(text(...)) + .mappings()) adapting admin.py's existing list_initiatives idiom — one row per initiative, one query, no N+1"
    - "Zero-coercion aggregate guard: filter to has_data rows before averaging, empty-set short-circuits to org_radar_chart_svg=None/org_average_scores=[] (RESEARCH Pitfall 5)"
key_files:
  created:
    - backend/app/services/admin_aggregation.py
    - backend/tests/services/test_admin_aggregation.py
  modified:
    - backend/app/api/v1/admin.py
    - backend/tests/api/test_admin.py
    - docs/api/openapi.json
decisions:
  - "Sort per-initiative rows by (has_data, overall_average, name) — has_data rows first, ascending average, name as tiebreaker; Python's stable sort preserves the SQL's ORDER BY i.created_at DESC relative order for genuine ties (ADMN-01 ordering requirement)"
  - "Dropped the unused type/request params from get_admin_heatmap (leftover from the deleted DSI/SP heatmap split) — this phase's aggregation is not type-scoped"
metrics:
  duration: ~30min
  completed: 2026-07-27
status: complete
---

# Phase 16 Plan 03: Admin Aggregation Rebuild Summary

Rebuilt the admin `/heatmap` endpoint (a fixed degraded stub since Phase 14) into a real cross-initiative aggregation over the new 6-category model — one org-wide averaged radar chart plus a per-initiative breakdown table, each initiative contributing only its latest submitted assessment, with initiatives that have no submitted data excluded from the average but still listed as "no data."

## What Was Built

**Task 1 — `admin_aggregation.py`:**
- `build_admin_aggregate(session, config) -> dict` — a single `LEFT JOIN LATERAL` raw-SQL query (adapting `admin.py`'s existing `list_initiatives` `session.execute(text(...))` + `.mappings()` idiom) returns exactly one row per initiative: its highest-`version` **submitted** assessment, or a null `dimension_scores`/`assessment_id` for initiatives with zero submitted assessments (D-08).
- Per-initiative rows carry `id`, `name`, `report_assessment_id`, `dimension_scores`, `overall_average` (rounded 2dp), and `has_data`.
- The org average is computed **only** over `has_data=True` rows (RESEARCH Pitfall 5) — a no-data initiative's scores are never coerced to zero. If the included set is empty, `org_radar_chart_svg` is `None` and `org_average_scores` is `[]` (no degenerate all-zero hexagon, no division-by-zero).
- `org_radar_chart_svg` is generated via `generate_radar_svg` — the exact same function used by individual reports (D-01), imported and called directly, not reimplemented.
- Rows sort by `(has_data, overall_average, name)` so equal averages sort stably.

**Task 2 — `/admin/heatmap` rebuild + test_admin.py:**
- Replaced `AdminHeatmapResponse` (`degraded: bool = True; cells: list[dict] = []`) with real Pydantic models: `AdminInitiativeAggregateRow {id, name, report_assessment_id, dimension_scores, overall_average, has_data}` and `AdminAggregateResponse {org_average_scores, org_radar_chart_svg, initiatives}`.
- `get_admin_heatmap` now depends on `get_dssc_questionnaire_config` (in addition to the unchanged `require_admin`), calls `build_admin_aggregate`, and maps the result into `AdminAggregateResponse`. Dropped the unused `type`/`request` params (leftover from the deleted DSI/SP split).
- Rewrote the heatmap tests in `test_admin.py`: one test builds 2 submitted initiatives (all-2 / all-4 dimension scores) plus a draft-only initiative, asserting the org average is 3.0 per dimension, `org_radar_chart_svg` contains real `<svg` markup, and the draft-only initiative appears with `has_data=False`/null scores/null `report_assessment_id`. A second test asserts the empty-org case (`org_radar_chart_svg=None`, `org_average_scores=[]`). The existing parametrized `require_admin` 403 test (`ADMIN_ENDPOINTS`) already covers `/admin/heatmap`'s access control — not duplicated.
- Regenerated `docs/api/openapi.json` for the docs-freshness CI gate (confirmed zero diff on a second export run).

## Verification

- `cd backend && uv run pytest tests/services/test_admin_aggregation.py tests/api/test_admin.py -q` — 21 passed (6 new service-level unit tests + 16 admin API tests, 2 new heatmap-shape tests replacing the retired degraded-stub test).
- `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app --ignore-missing-imports` — all clean (70 files formatted, 0 lint errors, 0 mypy errors across 35 source files).
- `grep -c "degraded=True" app/api/v1/admin.py` → 0 (stub fully removed).
- `grep -n "def build_admin_aggregate" app/services/admin_aggregation.py` found; `grep -c "generate_radar_svg" app/services/admin_aggregation.py` → 3 (import + doc reference + call site — confirms reuse, not reimplementation).
- Full quick suite: `cd backend && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` — 133 passed, 4 failed. The 4 failures (`test_reports.py`'s PDF/mail tests) are the same pre-existing local-only WeasyPrint native-library gap (`libgobject-2.0-0` missing on this Mac) documented recurring across every prior phase's `deferred-items.md`/STATE.md session log since Phase 12 — confirmed via the actual `OSError` traceback, unrelated to this plan's changes (this plan touches only `admin.py`/`admin_aggregation.py`, never `reports.py`).
- `docs/api/openapi.json` regenerated; re-running the export script a second time produces zero further diff.

## Deviations from Plan

### Auto-fixed Issues

No bug/blocking-issue deviations. One TDD-process correction, not a plan deviation:

**1. [TDD process correction] Wrote Task 1's implementation before its test, then corrected the ordering**
- **Found during:** Task 1
- **Issue:** The full `build_admin_aggregate` implementation was written first (a self-caught process error, not a plan deviation — the plan's `tdd="true"` frontmatter requires RED before GREEN).
- **Fix:** Stashed the full implementation aside, replaced `admin_aggregation.py` with a stub that raises `NotImplementedError`, wrote `backend/tests/services/test_admin_aggregation.py` (6 tests covering the plan's `<behavior>` bullets), confirmed all 6 failed (RED), committed the test file, then restored the full implementation, confirmed all 6 passed (GREEN), and committed the implementation separately.
- **Files affected:** `backend/app/services/admin_aggregation.py`, `backend/tests/services/test_admin_aggregation.py`
- **Commits:** `83da98b` (test, RED), `cb350e8` (feat, GREEN)

**2. [Rule 3 - necessary test infrastructure] Added `backend/tests/services/test_admin_aggregation.py` — not explicitly listed in the plan's `<files>` for Task 1**
- **Found during:** Task 1
- **Issue:** Task 1's `<files>` lists only `backend/app/services/admin_aggregation.py`; the plan's dedicated test coverage for the aggregation function lives in `test_admin.py` (Task 2, HTTP-level). Since Task 1 itself is `tdd="true"` and has its own `<behavior>` bullets independent of the HTTP layer, a direct service-level test file was needed to honor the TDD RED/GREEN gate for Task 1's own commit.
- **Fix:** Added `backend/tests/services/test_admin_aggregation.py` with 6 tests directly exercising `build_admin_aggregate` against the real Postgres `session` fixture (config-driven, no hardcoded category ids/counts) — covering the latest-submitted query shape, org average, zero-coercion guard, and the `generate_radar_svg` reuse check.
- **Files modified:** `backend/tests/services/test_admin_aggregation.py` (new)
- **Commit:** `83da98b` / `cb350e8`

No other deviations — plan executed as written, both tasks' acceptance criteria fully met.

### Authentication Gates

None encountered — this plan touches only an already-`require_admin`-gated endpoint and a new internal service module; no new auth-gated operations were introduced.

## Known Stubs

None. `build_admin_aggregate` is fully wired end-to-end (raw-SQL query → org-average computation → `generate_radar_svg` → `/admin/heatmap` response), with no placeholder values, hardcoded empty returns, or unwired data paths.

## Threat Flags

None beyond what the plan's own `<threat_model>` already covers. `org_radar_chart_svg` is generated by the same `generate_radar_svg` function audited in Plan 16-01 (T-16-02) — only config category names and computed numeric averages flow into it, confirmed by reading `build_admin_aggregate`'s implementation (no `initiative.name` or other free-text is ever passed into `generate_radar_svg`'s `scores` argument).

## Self-Check: PASSED

- `backend/app/services/admin_aggregation.py` — FOUND, contains `build_admin_aggregate`
- `backend/app/api/v1/admin.py` — FOUND, contains `AdminAggregateResponse`, `AdminInitiativeAggregateRow`, rebuilt `get_admin_heatmap`
- `backend/tests/api/test_admin.py` — FOUND, contains `test_admin_heatmap_returns_org_aggregate_and_per_initiative_rows`, `test_admin_heatmap_empty_org_suppresses_radar_and_average`
- `backend/tests/services/test_admin_aggregation.py` — FOUND, 6 tests passing
- `docs/api/openapi.json` — FOUND, regenerated, zero diff on re-export
- Commit `83da98b` — FOUND in git log
- Commit `cb350e8` — FOUND in git log
- Commit `f62836a` — FOUND in git log
- Commit `411fc19` — FOUND in git log
- Commit `e38fdfa` — FOUND in git log

## TDD Gate Compliance

Both tasks (`tdd="true"`) followed the RED → GREEN gate sequence, verified in git log:

- Task 1: `test(16-03)` at `83da98b` (RED, confirmed 6/6 failing) → `feat(16-03)` at `cb350e8` (GREEN, confirmed 6/6 passing).
- Task 2: `test(16-03)` at `f62836a` (RED, confirmed 2/2 new tests failing against the old stub) → `feat(16-03)` at `411fc19` (GREEN, confirmed all 16 `test_admin.py` tests passing).

No REFACTOR-phase commit was needed for either task — no post-GREEN cleanup was required beyond what was already written during GREEN.
