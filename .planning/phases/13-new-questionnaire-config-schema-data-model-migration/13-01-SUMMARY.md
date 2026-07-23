---
phase: 13-new-questionnaire-config-schema-data-model-migration
plan: 01
subsystem: api
tags: [fastapi, sqlmodel, questionnaire-config, json-config, pytest]

requires: []
provides:
  - "config/dssc-questionnaire.json — universal 52-question / 6-category placeholder config, single file, no participant_type split"
  - "backend/app/services/mami_config.py::load_dssc_questionnaire_config() — single-file loader"
  - "backend/app/core/deps.py::get_dssc_questionnaire_config() — FastAPI dependency"
  - "app.state.dssc_questionnaire_config — lifespan-cached config, additive alongside existing MAMI/ZEN state"
  - "GET /api/v1/questionnaire/config — now universal, no participant_type branch, no Initiative-existence gate"
affects: [14-scoring-engine-replacement, 15-wizard-autosave-history, 16-report-visualization]

tech-stack:
  added: []
  patterns:
    - "Single-file JSON config loaded once at FastAPI lifespan startup, served via app.state + Depends() — extends the existing Path(__file__).parent CONFIG_DIR pattern, no new tooling"

key-files:
  created:
    - config/dssc-questionnaire.json
    - backend/tests/services/test_dssc_config.py
    - backend/tests/api/test_questionnaire.py
    - .planning/phases/13-new-questionnaire-config-schema-data-model-migration/deferred-items.md
  modified:
    - backend/app/services/mami_config.py
    - backend/app/core/deps.py
    - backend/app/main.py
    - backend/app/api/v1/questionnaire.py
    - docs/api/openapi.json

key-decisions:
  - "Dropped the participant_type-driven 404-if-no-Initiative gate on GET /questionnaire/config per plan frontmatter assumption A1 — incidental coupling to the removed DSI/SP split, not load-bearing UX; no replacement guard added (future ask if ever needed)"
  - "Old MAMI/ZEN config loaders (load_questionnaire_config/load_questionnaire_configs) kept alive unmodified — purely additive change per the Phase 14 boundary"
  - "Regenerated docs/api/openapi.json to keep the docs-freshness CI gate green (endpoint docstring changed the schema)"

patterns-established:
  - "Universal (non-participant-type-branching) config endpoint pattern: Depends(get_dssc_questionnaire_config) returns app.state dict directly, no DB lookup"

requirements-completed: [QSTN-01, QSTN-03, QSTN-04, QSTN-05]

coverage:
  - id: D1
    description: "config/dssc-questionnaire.json defines exactly 52 questions across exactly 6 categories, with a shared 5-label default_options set (scores 1-5) and one question demonstrating a per-question options override"
    requirement: "QSTN-01, QSTN-03, QSTN-05"
    verification:
      - kind: unit
        ref: "backend/tests/services/test_dssc_config.py#test_all_52_questions_present"
        status: pass
      - kind: unit
        ref: "backend/tests/services/test_dssc_config.py#test_config_is_pure_data_no_hardcoded_labels"
        status: pass
      - kind: unit
        ref: "backend/tests/services/test_dssc_config.py#test_served_content_is_byte_for_parsed_equal_to_raw_json_file"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /questionnaire/config serves the identical universal config to every authenticated caller regardless of participant_type, returning 200 even with no owned Initiative"
    requirement: "QSTN-04"
    verification:
      - kind: integration
        ref: "backend/tests/api/test_questionnaire.py#test_config_endpoint_universal"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-23
status: complete
---

# Phase 13 Plan 01: New Universal Questionnaire Config Schema Summary

**Single-file 52-question/6-category DSSC config with a shared default 5-label answer set (plus one per-question override), served universally via a new FastAPI dependency that replaces the old DSI/SP dual-config selection on GET /questionnaire/config.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-23T06:49:00Z
- **Completed:** 2026-07-23T06:55:15Z
- **Tasks:** 3 completed
- **Files modified:** 5 modified/regenerated, 4 created

## Accomplishments
- Authored `config/dssc-questionnaire.json`: 6 categories, 52 questions total (9+9+9+9+8+8), a shared `default_options` array (5 labels scored 1-5), and one question (`q-1-1`) demonstrating the per-question `options` override path — full structural skeleton at real size per D-08, placeholder content only.
- Added `load_dssc_questionnaire_config()` alongside the existing MAMI/ZEN loaders in `mami_config.py` (no removal — Phase 14 boundary preserved), a matching `get_dssc_questionnaire_config()` FastAPI dependency, and a new `app.state.dssc_questionnaire_config` lifespan cache.
- Rewired `GET /api/v1/questionnaire/config` to depend only on the new universal dependency — removed the Initiative lookup, `participant_type` resolution, and the 404-if-no-Initiative branch entirely (assumption A1 decision, documented inline in the endpoint's docstring).
- Wrote `backend/tests/services/test_dssc_config.py` (3 tests) and `backend/tests/api/test_questionnaire.py` (1 test) covering QSTN-01/03/04: question/category counts, default-vs-override option resolution, byte-for-parsed equality against the raw JSON file (proving zero hardcoded content in Python), and cross-user identical-response + no-Initiative-200 behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Author config/dssc-questionnaire.json** - `5ed4947` (feat)
2. **Task 2: Add single-file loader, dependency, lifespan cache, and universal config endpoint** - `266f250` (feat)
   - Docs-freshness fix (regenerated openapi.json) - `ad6e6df` (docs)
3. **Task 3: Config + universal-endpoint tests (QSTN-01/03/04/05)** - `5077856` (test)

**Plan metadata:** committed separately per final_commit step.

## Files Created/Modified
- `config/dssc-questionnaire.json` - universal placeholder questionnaire config (52q/6cat, default + one override options set)
- `backend/app/services/mami_config.py` - added `load_dssc_questionnaire_config()`
- `backend/app/core/deps.py` - added `get_dssc_questionnaire_config()` dependency
- `backend/app/main.py` - lifespan now also caches `app.state.dssc_questionnaire_config`
- `backend/app/api/v1/questionnaire.py` - `GET /questionnaire/config` now universal, no participant_type/Initiative branch
- `docs/api/openapi.json` - regenerated to reflect the endpoint's new docstring (docs-freshness CI gate)
- `backend/tests/services/test_dssc_config.py` - new loader unit tests
- `backend/tests/api/test_questionnaire.py` - new endpoint characterization test
- `.planning/phases/13-new-questionnaire-config-schema-data-model-migration/deferred-items.md` - logs one pre-existing, unrelated local-env test gap found during full-suite verification

## Decisions Made
- Dropped the participant_type-driven 404-if-no-Initiative gate per frontmatter assumption A1 (RESEARCH.md confirmed this was incidental coupling, not load-bearing UX) — no replacement initiative-existence guard added; that is explicitly deferred to a future ask, not silently designed away.
- Kept `load_questionnaire_configs`/`load_questionnaire_config` (old MAMI/ZEN loaders) untouched — this plan is purely additive at the service layer per the Phase 14 boundary; nothing else in the codebase besides the changed endpoint referenced the old DSI/SP config dependency, so no further cleanup was needed or attempted.
- Regenerated `docs/api/openapi.json` (Rule 3 auto-fix — blocking CI issue): the endpoint's docstring change altered the FastAPI-generated schema, and `docs-freshness` (pr.yml) hard-fails on any diff against a freshly regenerated file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking CI issue] Regenerated docs/api/openapi.json**
- **Found during:** Task 2 (endpoint docstring change)
- **Issue:** The rewritten `GET /questionnaire/config` docstring changed the FastAPI-generated OpenAPI schema; `docs/api/openapi.json` (committed, regenerated by the `docs-freshness` CI job) would otherwise drift and fail that gate on the next PR.
- **Fix:** Ran `uv run python scripts/export_openapi.py` and committed the resulting one-line diff.
- **Files modified:** `docs/api/openapi.json`
- **Commit:** `ad6e6df`

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking CI issue).
**Impact on plan:** Necessary for CI correctness (docs-freshness gate). No scope creep — no application behavior changed beyond what the plan specified.

## Issues Encountered

One pre-existing, unrelated local-environment gap surfaced during the full-suite verification run (`uv run pytest tests/ -n auto -m "not perf and not benchmark" -q`): 4 tests in `backend/tests/api/test_reports.py` fail locally with `OSError: cannot load library 'libgobject-2.0-0'` (WeasyPrint/Pango native dependency, present in CI's Docker images per CLAUDE.md's documented fix but absent on this macOS dev machine). Confirmed via import grep that none of this plan's 5 changed files are imported by `reports.py`/`report_generator.py` — out of scope per the scope-boundary rule, not fixed, logged in `deferred-items.md`. This plan's own 4 new tests (`test_dssc_config.py` x3, `test_questionnaire.py` x1) all pass, and the app imports cleanly (`python -c "import app.main"` succeeds).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The universal 52-question/6-category config shape is now stable and servable — Phase 14 (scoring) and Phase 15 (wizard) can build against `config/dssc-questionnaire.json`'s `categories[].questions[].{id, category_id, text, options?}` shape and the shared `default_options` fallback. No blockers. Note for downstream planners: this plan does not touch `Assessment`, `questionnaire_answer` reshape, or evidence removal — those land in 13-02/13-03/13-04 per the phase's strictly sequential wave plan.

---
*Phase: 13-new-questionnaire-config-schema-data-model-migration*
*Completed: 2026-07-23*
