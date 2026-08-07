---
phase: 16-report-data-contract-dual-visualization-admin-aggregation
fixed_at: 2026-07-27T18:30:00Z
review_path: .planning/phases/16-report-data-contract-dual-visualization-admin-aggregation/16-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 16: Code Review Fix Report

**Fixed at:** 2026-07-27T18:30:00Z
**Source review:** .planning/phases/16-report-data-contract-dual-visualization-admin-aggregation/16-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (fix_scope: critical_warning — 2 Critical + 6 Warning; the 2 Info findings were out of scope)
- Fixed: 8
- Skipped: 0

## Fixed Issues

### CR-01: Admin aggregate org-average computation crashes (500) when a frozen assessment snapshot doesn't cover every current config category

**Files modified:** `backend/app/services/admin_aggregation.py`, `backend/tests/services/test_admin_aggregation.py`
**Commit:** `6e6eac6`
**Applied fix:** Replaced the unguarded `next(...)` (raises `StopIteration` on a
missing `category_id`) with a `next(..., None)` default, per-category. Any
initiative whose frozen snapshot lacks the current category is excluded from
that category's average rather than crashing the whole `/admin/heatmap`
endpoint; `org_average_scores`/`org_radar_chart_svg` degrade to `[]`/`None`
only if literally no initiative covers any category. Added a regression test
(`test_org_average_excludes_stale_snapshot_category_mismatch_no_crash`) that
submits an assessment with a stale `category_id` absent from the current
config and asserts `build_admin_aggregate` returns 200 with a correct average
computed only from initiatives that do have current-config coverage. Verified
against a real Postgres testcontainer: 7/7 tests in
`test_admin_aggregation.py` pass.

### CR-02: CSV export is vulnerable to formula/CSV injection via free-text initiative name

**Files modified:** `backend/app/api/v1/admin.py`, `backend/tests/api/test_admin.py`
**Commit:** `75bc027`
**Applied fix:** Added a `_csv_safe()` helper that prefixes a leading `'`
(single quote) onto any cell value starting with `=`, `+`, `-`, `@`, tab, or
CR, and applied it to `row["initiative_name"]` in `export_dataset`'s
per-row `writer.writerow(...)` call (CWE-1236 mitigation). Added a regression
test (`test_export_dataset_csv_sanitizes_formula_injection_in_initiative_name`)
that sets an initiative name to a formula-injection payload
(`=cmd|"/c calc.exe"!A1`) and asserts the exported CSV cell is neutralized
with a leading quote. 3/3 export-related tests pass.

### WR-01: Per-initiative dimension score lookup keys off display `name`, not the stable `category_id`

**Files modified:** `frontend/src/routes/_app/admin.heatmap.tsx`
**Commit:** `a072cc7`
**Applied fix:** Replaced the `dimensionNames: string[]` derivation with a
`dimensionColumns: { category_id, name }[]` array, and changed the per-cell
lookup from `record.dimension_scores?.find((d) => d.name === name)` to
`.find((d) => d.category_id === category_id)`. Column headers still display
`name` as the title text; only the matching key changed. Verified with
`npx tsc -b --noEmit` (clean, no new errors).

### WR-02: Per-initiative breakdown table is completely hidden when the org has zero submitted assessments

**Files modified:** `frontend/src/routes/_app/admin.heatmap.tsx`
**Commit:** `1f93bb5`
**Applied fix:** Restructured the conditional rendering so the outer
`{!loading && !error && data && (...)}` block always renders; inside it, an
`isOrgEmpty ? <EmptyStateCard /> : <RadarCard />` ternary scopes the "No
submitted assessments yet" messaging to the radar card only, while the
per-initiative `<Table>` card now renders unconditionally regardless of
`isOrgEmpty` (it already handles `has_data=False` rows via the "No data yet"
tag). Verified with `npx tsc -b --noEmit` (clean).

### WR-03: `ReportContract`/`PriorityListItem`/`MaturityBand` schemas are dead code

**Files modified:** `backend/app/api/v1/reports.py`, `docs/api/openapi.json`
**Commit:** `84d2480`
**Applied fix:** Added `response_model=ReportContract` to both
`generate_report_data_endpoint` (`POST /report/data`) and
`get_report_data_endpoint` (`GET /report/data`), and imported `ReportContract`
from `app.schemas.report`. Confirmed `build_report_contract`'s returned dict
shape matches `ReportContract`'s fields exactly (`assessment_id`, `version`,
`initiative`, `dimension_scores`, `priority_list`, `radar_chart_svg`,
`maturity_bands`). Regenerated `docs/api/openapi.json` via
`scripts/export_openapi.py` (the repo's own docs-freshness CI gate) — the two
`/report/data` routes' 200 response schemas now reflect the real contract
instead of `{}`. Verified: 14/18 `test_reports.py` tests pass (4 pre-existing
failures are unrelated local-environment WeasyPrint/`libgobject` issues,
confirmed present before this change too); `mypy` clean on both touched
files.

### WR-04: Zero-question config category produces a score (`0.0`) outside every maturity band's range

**Files modified:** `backend/app/services/mami_config.py`, `backend/tests/services/test_dssc_config.py`
**Commit:** `1dfa6d2`
**Applied fix:** Chose the review's first suggested option — fail fast at
config-load time rather than at request time. `load_dssc_questionnaire_config()`
now validates every category has at least one question immediately after
parsing the JSON, raising a clear `ValueError` naming the offending
category id(s) if not. Since this loader runs once at FastAPI lifespan
startup (`app/main.py`), a future config edit that empties a category now
fails the app's startup instead of 500ing every report/heatmap request at
runtime. Added a regression test
(`test_load_raises_fast_on_zero_question_category`) using a monkeypatched
`CONFIG_DIR` and a synthetic bad config to assert the `ValueError` fires.
4/4 tests in `test_dssc_config.py` pass; `mypy` clean.

### WR-05: `generate_radar_svg` interpolates category names into SVG `<text>` content with no XML escaping

**Files modified:** `backend/app/services/report_generator.py`, `backend/tests/services/test_report_generator.py`, `backend/tests/api/test_reports.py`
**Commit:** `4051b4d`
**Applied fix:** Escaped `s["name"]` via `xml.sax.saxutils.escape` before
interpolating into the SVG `<text>` element in `generate_radar_svg`, as
defense in depth against the documented "server-controlled only" invariant
ever being violated. This surfaced two **pre-existing, latent** test issues
that this fix made visible rather than introduced: (1)
`test_radar_svg_structure` asserted the raw (unescaped) category name
appeared in the SVG — updated to assert the escaped form, since the real
`dssc-questionnaire.json` config already has a category named "Control over
Data & Trust"; (2)
`test_report_data_and_html_share_identical_contract_values` asserted
`row["name"] in html` for every priority-list row — this assertion was only
ever passing because the *unescaped* radar SVG label for the same category
name happened to appear elsewhere in the same HTML page (a coincidental
match, not a real proof that the priority-list text itself was unescaped);
now that the radar SVG is properly escaped too, the assertion needed to
compare against the Jinja-autoescaped form (`markupsafe.escape`), which is
what `report.html`'s `{{ row.name }}` already produces and always did.
Added a dedicated escaping regression test
(`test_radar_svg_escapes_special_characters_in_category_name`). Full
before/after diff confirmed via `git stash`: both fixed tests pass identically
whether or not the `report.tsx`/`admin.heatmap.tsx` changes are present,
isolating the cause to the WR-05 SVG-escaping change alone. 7/7
`test_report_generator.py` tests and 14/18 `test_reports.py` tests pass
(same 4 pre-existing unrelated WeasyPrint failures as WR-03); `mypy` clean.

### WR-06: `report.tsx`'s PDF download hardcodes a duplicate fallback API base URL

**Files modified:** `frontend/src/routes/_app/report.tsx`
**Commit:** `4d154ea`
**Applied fix:** Replaced the duplicated
`` `${import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1"}` ``
expression with `api.defaults.baseURL` (the shared client, already imported
in this file). Verified with `npx tsc -b --noEmit` (clean); no existing test
file covers this download path, so verification relied on Tier 1 (re-read)
+ Tier 2 (tsc) only, per the fallback rule for untested files.

## Skipped Issues

None — all 8 in-scope findings (CR-01, CR-02, WR-01 through WR-06) were
fixed and committed. The 2 Info findings (IN-01: stale docstring in
`reports.ts`; IN-02: deprecated `datetime.utcnow()`) were intentionally
excluded — `fix_scope` for this run was `critical_warning`.

---

_Fixed: 2026-07-27T18:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
