---
phase: 16-report-data-contract-dual-visualization-admin-aggregation
plan: 01
subsystem: backend-report-contract
tags: [report-contract, maturity-bands, radar-svg, priority-list, config-driven]
dependency_graph:
  requires: []
  provides:
    - get_maturity_band
    - build_priority_list
    - generate_radar_svg
    - build_report_contract
    - config/dssc-questionnaire.json maturity_bands key
    - schemas/report.py (MaturityBand, PriorityListItem, ReportContract)
  affects:
    - backend/app/services/report_generator.py
    - backend/app/schemas/report.py
    - config/dssc-questionnaire.json
tech_stack:
  added: []
  patterns:
    - "Single band-classification function (get_maturity_band) called by both build_priority_list and generate_radar_svg — no duplicated inequality chain (RPRT-03)"
    - "viewBox-based hand-rolled SVG string templating (Python stdlib math only, no new dependency, D-01)"
    - "Config-driven structure derivation (never hardcode band lists or category counts), mirroring dimension_scoring.py's existing idiom"
key_files:
  created:
    - backend/app/schemas/report.py (rewritten — replaces the unused legacy ReportRead schema)
  modified:
    - config/dssc-questionnaire.json
    - backend/app/services/report_generator.py
    - backend/tests/services/test_report_generator.py
decisions:
  - "Replaced the pre-existing but zero-call-site legacy ReportRead schema in schemas/report.py entirely, rather than adding the new models alongside it — confirmed via repo-wide grep that ReportRead had no importers anywhere in app/ or tests/"
  - "generate_radar_svg colors the whole polygon fill/stroke from get_maturity_band(overall_average, bands) — one color for the whole shape, not per-axis segment coloring (RESEARCH Assumption A2, Open Question 3, already resolved before this plan executed)"
metrics:
  duration: ~35min
  completed: 2026-07-27
status: complete
---

# Phase 16 Plan 01: Report Data Contract Core Summary

Built the pure, config-driven report-contract core — the single color-band lookup (`get_maturity_band`), the priority-list builder (`build_priority_list`), the server-side radar-chart SVG generator (`generate_radar_svg`), and the contract-assembly function (`build_report_contract`) — plus their Pydantic schema shapes (`schemas/report.py`) and unit test coverage, all driven from a new `maturity_bands` key added to `config/dssc-questionnaire.json`.

## What Was Built

**Task 1 — `maturity_bands` config + `get_maturity_band` + `build_priority_list`:**
- Added a new top-level `maturity_bands` array to `config/dssc-questionnaire.json` (sibling of `categories`) with the three approved bands: red (1.0-2.0, `#d64545`, "Needs attention"), orange (2.0-3.5, `#e08e2b`, "Developing"), green (3.5-5.0, `#399e5a`, "Mature") — hex values copied verbatim from `16-UI-SPEC.md`, no new loader needed (served by the existing `get_dssc_questionnaire_config()`).
- `get_maturity_band(score, bands)` in `report_generator.py`: the sole band-classification function in the codebase. A score exactly on a shared boundary belongs to the higher band (2.0 → orange, 3.5 → green); the top band is also inclusive of its own max (5.0 → green); raises `ValueError` for an uncovered score.
- `build_priority_list(scores, bands)`: always returns all 6 rows sorted ascending by score (Python's `sorted()` stable sort preserves config category order on ties); each row carries `category_id`, `name`, `score`, `band_id`, `band_label`, `band_color` — band fields sourced only from `get_maturity_band`.

**Task 2 — `generate_radar_svg` + `build_report_contract` + `schemas/report.py`:**
- `generate_radar_svg(scores, bands, *, size=320, max_score=5.0)`: a hand-rolled `<svg viewBox="0 0 {size} {size}">` string with 6 axis points placed via `math.cos`/`math.sin` (angle offset so axis 0 points up), one `<polygon>` data shape colored by the overall-average's band, axis spoke `<line>` elements, and one `<text>` label per axis carrying explicit `font-size="11"`, `font-family="Rubik, sans-serif"`, `fill="#06004f"` presentation attributes (WeasyPrint parity, Pitfall 3 — never relies on external CSS).
- `build_report_contract(dimension_scores, initiative, assessment, config)`: assembles the single shared dict (`assessment_id`, `version`, `initiative`, `dimension_scores`, `priority_list`, `radar_chart_svg`, `maturity_bands`) that every downstream surface (React report, WeasyPrint PDF, admin aggregate) will consume without recomputation — one computation, reused verbatim.
- `backend/app/schemas/report.py`: `MaturityBand`, `PriorityListItem`, `ReportContract` — plain `BaseModel`s mirroring `schemas/assessment.py`'s hand-assembled convention.

**Task 3 — unit tests:**
- Added `test_maturity_band_boundaries`, `test_maturity_band_same_for_both_callers` (RPRT-03 single-source proof), `test_priority_list_six_rows_sorted`, `test_priority_list_tie_stable`, `test_radar_svg_structure` to `backend/tests/services/test_report_generator.py` — all driven from the real `config/dssc-questionnaire.json` via `load_dssc_questionnaire_config()`, no hardcoded question ids or band thresholds beyond the boundary values under test (mirrors `test_dimension_scoring.py`'s config-comprehension style).

## Verification

- `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app --ignore-missing-imports` — all clean (68 files formatted, 0 lint errors, 0 mypy errors across 34 source files).
- `cd backend && uv run pytest tests/services/test_report_generator.py -q` — 8 passed (3 pre-existing + 5 new).
- Config JSON parses; `maturity_bands` has the 3 approved bands with exact hex values (`#d64545`/`#e08e2b`/`#399e5a`).
- `grep -rn "3.5" backend/app/api backend/app/templates frontend/src | grep -iv test` — all hits are coincidental (font sizes, margins, unrelated hex colors like `#3d52d5`), zero band-classification logic outside `report_generator.py`/config.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Dead code cleanup] Replaced the unused legacy `ReportRead` schema in `schemas/report.py`**
- **Found during:** Task 2
- **Issue:** `backend/app/schemas/report.py` already existed with a `ReportRead` model (leftover from the old `ComplianceReport`-backed report flow). A repo-wide grep confirmed zero call sites for `ReportRead` anywhere in `app/` or `tests/`.
- **Fix:** Replaced the file's contents entirely with the new `MaturityBand`/`PriorityListItem`/`ReportContract` models, documenting the removal in the module docstring. `ComplianceReport`-based persistence itself is out of this plan's scope (Plan 16-02's job per RESEARCH Pitfall 2 / Open Question 1) — only the dead, unreferenced Pydantic schema was removed here.
- **Files modified:** `backend/app/schemas/report.py`
- **Commit:** `40187d1`

**2. [Rule 1 - Bug] Fixed an out-of-range test fixture value**
- **Found during:** Task 3, writing `test_priority_list_six_rows_sorted`
- **Issue:** Initial test used `float(5 - i)` across 6 categories, producing a `0.0` score for the 6th category — outside the valid `[1.0, 5.0]` dimension-score range, causing `get_maturity_band` to correctly raise `ValueError` (proving the function's defensive guard works, but the test itself was wrong).
- **Fix:** Changed to `round(5.0 - i * 0.7, 2)`, producing 6 distinct values all within `[1.5, 5.0]`.
- **Files modified:** `backend/tests/services/test_report_generator.py`
- **Commit:** `78a017a`

No other deviations — plan executed as written.

### Authentication Gates

None encountered — this plan touches only pure service functions, a config file, and unit tests; no auth-gated operations.

## Known Stubs

None. All functions built this plan are fully wired (config → `get_maturity_band`/`build_priority_list`/`generate_radar_svg` → `build_report_contract`), with no placeholder values or hardcoded empty returns.

## Threat Flags

None beyond what the plan's own `<threat_model>` already covers (T-16-02, mitigated by construction: only config category names and computed scores flow into `generate_radar_svg`'s output string, never `initiative`/`assessment` free-text — confirmed by reading the implementation, which only reads `s["name"]` from the config-derived `scores` list argument).

## Self-Check: PASSED

- `backend/app/services/report_generator.py` — FOUND, contains `get_maturity_band`, `build_priority_list`, `generate_radar_svg`, `build_report_contract`
- `backend/app/schemas/report.py` — FOUND, contains `MaturityBand`, `PriorityListItem`, `ReportContract`
- `config/dssc-questionnaire.json` — FOUND, contains `maturity_bands` key
- `backend/tests/services/test_report_generator.py` — FOUND, 8 tests passing
- Commit `41b6f02` — FOUND in git log
- Commit `40187d1` — FOUND in git log
- Commit `78a017a` — FOUND in git log
