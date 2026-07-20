---
phase: 02-questionnaire-and-scoring
plan: 01
subsystem: api
tags: [zen-engine, gorules, jdm, fastapi, lifespan, json-config, mami]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: FastAPI app skeleton, pyproject.toml, backend/app/core/deps.py with auth deps

provides:
  - MAMI framework JSON config (20 codes, 4 categories x 3 dimensions, MoSCoW levels, critical_override flags)
  - Versioned questionnaire JSON config (v1.0, 20 questions grouped by category/dimension, 3 answer types)
  - JDM scoring decision file (hitPolicy first, 8 rules, single-answer evaluation pattern)
  - Config loader service (load_mami_config, load_questionnaire_config, get_scoring_dir)
  - FastAPI lifespan startup loading all three configs + ZEN Engine singleton into app.state
  - Three FastAPI deps: get_zen_engine, get_mami_config, get_questionnaire_config

affects:
  - 02-02 (questionnaire engine + answer storage uses questionnaire config from app.state)
  - 02-03 (scoring engine uses ZEN engine singleton and JDM file from app.state)

# Tech tracking
tech-stack:
  added:
    - zen-engine==0.51.0 (GoRules ZEN Engine — Rust-based JDM evaluation)
  patterns:
    - FastAPI lifespan context manager for startup singletons (not deprecated @app.on_event)
    - Path(__file__).parent resolution for config files independent of working directory
    - Single-answer ZEN evaluation pattern (one engine.evaluate() call per answer, not array iteration)
    - JDM hitPolicy first for mutually exclusive MoSCoW scoring rules

key-files:
  created:
    - config/mami-framework.json
    - config/questionnaire-v1.json
    - config/scoring/mami-scoring.json
    - backend/app/services/mami_config.py
    - backend/app/services/__init__.py
  modified:
    - backend/app/main.py
    - backend/app/core/deps.py
    - backend/pyproject.toml
    - backend/uv.lock

key-decisions:
  - "JDM hitPolicy first (not collect) — rules are mutually exclusive for single-answer evaluation"
  - "Single-answer ZEN evaluation pattern — engine.evaluate() called once per answer (not array iteration) per research Pitfall 1"
  - "Config file path resolved via Path(__file__).parent chain — works in both local dev and Docker regardless of working directory"
  - "20 MAMI codes authored (not just 12 minimum) — covers all 4 categories x 3 dimensions with representative SHOULD codes per category"
  - "critical_override: false on 3 codes (S-HRA-1.3, PP-MRA-2.1, D-TA-3.1) to demonstrate SCOR-02 override capability"

patterns-established:
  - "FastAPI lifespan pattern: all expensive startup resources (config loads, ZEN engine) initialised once in lifespan and stored in app.state"
  - "Config-driven MAMI: all MAMI code references come from mami-framework.json; no codes hardcoded in Python"
  - "Questionnaire versioning: version field in questionnaire-v1.json; answer rows will carry the version string for QUES-07"

# Metrics
duration: 3min
completed: 2026-02-15
---

# Phase 2 Plan 01: MAMI Config Foundation Summary

**JSON config files for MAMI framework (20 codes), questionnaire (20 questions v1.0), and JDM scoring (8 MoSCoW rules) wired into FastAPI via lifespan singleton with zen-engine==0.51.0**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-15T18:51:49Z
- **Completed:** 2026-02-15T18:54:33Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Authored 20 MAMI codes across 4 categories (scheme, participants, data, services) x 3 dimensions (human_readable, machine_readable, trust_anchors) with MoSCoW levels and critical_override flags — 3 codes have `critical_override: false` to demonstrate SCOR-02 per-recommendation override
- Created versioned questionnaire-v1.json with one question per MAMI code, using answer_type values: yes_no_explain, yes_no, and not_applicable_allowed (3 questions have not_applicable_allowed satisfying QUES-04)
- Authored mami-scoring.json JDM file with hitPolicy "first", 3 nodes, and 8 scoring rules implementing the single-answer evaluation pattern per research Pitfall 1
- Installed zen-engine==0.51.0 and created config loader service with Path(__file__) resolution for Docker compatibility
- Updated FastAPI main.py to use lifespan context manager (replacing bare FastAPI) that loads all three configs and ZEN Engine singleton at startup
- Added get_zen_engine, get_mami_config, get_questionnaire_config dependencies to deps.py alongside existing auth dependencies

## Task Commits

Each task was committed atomically:

1. **Task 1: Author MAMI config files (framework, questionnaire, JDM scoring)** - `6f9a6ac` (feat)
2. **Task 2: Python config loader, lifespan startup, deps, and zen-engine install** - `77bacca` (feat)

## Files Created/Modified

- `config/mami-framework.json` - 20 MAMI codes with id, category, dimension, moscow_level, critical_override, description
- `config/questionnaire-v1.json` - Versioned questionnaire v1.0 with 20 questions grouped by category/dimension, three answer types
- `config/scoring/mami-scoring.json` - JDM file: inputNode + decisionTableNode (hitPolicy first, 8 rules) + outputNode
- `backend/app/services/mami_config.py` - load_mami_config(), load_questionnaire_config(), get_scoring_dir() with __file__-relative path resolution
- `backend/app/services/__init__.py` - Empty package init
- `backend/app/main.py` - Added lifespan context manager loading configs + ZEN Engine; passed lifespan=lifespan to FastAPI constructor
- `backend/app/core/deps.py` - Added get_zen_engine, get_mami_config, get_questionnaire_config dependencies
- `backend/pyproject.toml` - Added zen-engine==0.51.0
- `backend/uv.lock` - Updated lockfile

## Decisions Made

- **hitPolicy "first" for JDM**: Rules are mutually exclusive for single-answer evaluation; "first" is cleaner than "collect" and avoids duplicate outputs
- **Single-answer evaluation pattern**: Per research Pitfall 1, ZEN Engine array iteration in Python SDK is not well-documented; plan specifies evaluating one answer per engine.evaluate() call — implemented in JDM accordingly
- **Path(__file__) resolution**: Used `Path(__file__).parent.parent.parent.parent / "config"` (services/ -> app/ -> backend/ -> repo root -> config/) — works regardless of working directory, including Docker
- **20 codes instead of 12 minimum**: Authored representative codes for all 12 matrix cells (4 categories x 3 dimensions) plus additional SHOULD codes per category for completeness

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Config foundation complete — Plans 02-02 (questionnaire engine) and 02-03 (scoring engine) can now build on `app.state.mami_config`, `app.state.questionnaire_config`, and `app.state.zen_engine`
- ZEN Engine singleton available via `get_zen_engine` dependency — Plan 02-03 can call `engine.evaluate("mami-scoring.json", {"answer": ...})` directly
- No blockers

---
*Phase: 02-questionnaire-and-scoring*
*Completed: 2026-02-15*
