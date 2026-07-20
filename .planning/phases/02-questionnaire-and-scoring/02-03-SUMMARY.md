---
phase: 02-questionnaire-and-scoring
plan: 03
subsystem: api
tags: [zen-engine, gorules, jdm, fastapi, scoring, findings, react, typescript]

# Dependency graph
requires:
  - phase: 02-questionnaire-and-scoring
    plan: 01
    provides: mami-scoring.json JDM, ZEN Engine singleton, get_zen_engine dep, get_mami_config dep
  - phase: 02-questionnaire-and-scoring
    plan: 02
    provides: QuestionnaireAnswer table with mami_code and answer_value per answer

provides:
  - score_all_answers() async function using per-answer ZEN engine.async_evaluate()
  - create_scoring_engine() factory function (optional alternative to inline lifespan code)
  - POST /api/v1/initiatives/{id}/score endpoint returning ScoreResponse with findings[], critical_count, non_critical_count
  - FindingRead and ScoreResponse Pydantic models
  - Frontend triggerScoring() API call function in scoring.ts
  - FindingsPanel React component: CRITICAL count, NON_CRITICAL count, per-finding list
  - "Get Compliance Score" button on questionnaire page

affects:
  - 03-evidence (scoring results can be linked to evidence uploads)
  - 04-admin (admin reporting will build on ScoreResponse structure)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.gather() for concurrent per-answer ZEN evaluation — evaluates all answers in parallel via async_evaluate"
    - "JDM hitPolicy first with single-answer evaluation pattern — one engine.async_evaluate() call per answer, null critical_override falls through to MoSCoW rules"
    - "ScoreResponse Pydantic model with findings[], critical_count, non_critical_count — structured findings output"
    - "React useState + async handler pattern for scoring trigger — no TanStack Query mutation needed for one-shot scoring"

key-files:
  created:
    - backend/app/services/scoring_engine.py
    - backend/app/api/v1/scoring.py
    - frontend/src/lib/scoring.ts
    - frontend/src/components/questionnaire/FindingsPanel.tsx
  modified:
    - backend/app/main.py
    - frontend/src/routes/_app/questionnaire.tsx

key-decisions:
  - "asyncio.gather() for concurrent ZEN evaluation — all answers evaluated in parallel, not sequentially, using async_evaluate"
  - "Ownership check via initiative.user_id != current_user.id — 403 Forbidden if initiative belongs to different user"
  - "Named import { api } for scoring.ts — consistent with questionnaire.ts pattern (api.ts does not have a default export)"
  - "handleGetScore uses useState + try/finally — simpler than useMutation for one-shot scoring requests"

patterns-established:
  - "ZEN Engine MAMI code lookup: code_lookup dict built from mami_config['codes'] keyed by code['id'] — avoids N queries"
  - "Findings filter: score_all_answers() only returns FINDING-status items; COMPLIANT and NOT_APPLICABLE excluded"

# Metrics
duration: 3min
completed: 2026-02-15
---

# Phase 2 Plan 03: ZEN Engine Scoring Service and Findings Panel Summary

**ZEN Engine async per-answer scoring with POST /initiatives/{id}/score returning CRITICAL/NON_CRITICAL findings, wired to a React FindingsPanel component triggered by a Get Compliance Score button on the questionnaire page**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-15T19:07:01Z
- **Completed:** 2026-02-15T19:09:52Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Created `backend/app/services/scoring_engine.py` with `create_scoring_engine()` factory and `score_all_answers()` using `asyncio.gather()` to evaluate all answers concurrently via `engine.async_evaluate("mami-scoring.json", ...)`
- Created `backend/app/api/v1/scoring.py` with `POST /initiatives/{id}/score` endpoint: verifies ownership (403 if not owner), loads all QuestionnaireAnswer rows, joins with MAMI code metadata (moscow_level, critical_override), calls score_all_answers(), returns ScoreResponse
- Registered scoring_router in `backend/app/main.py` at `/api/v1`
- All 4 scoring test cases pass: MUST+NO=CRITICAL, MUST+NO+critical_override=False=NON_CRITICAL, SHOULD+NO=NON_CRITICAL, YES=no finding
- Created `frontend/src/lib/scoring.ts` with `triggerScoring()` POSTing to `/initiatives/${initiativeId}/score`
- Created `frontend/src/components/questionnaire/FindingsPanel.tsx` with CRITICAL count, NON_CRITICAL count, per-finding list (CRITICAL first, then NON_CRITICAL), and fully-compliant message
- Updated `frontend/src/routes/_app/questionnaire.tsx` with handleGetScore(), isScoring state, Get Compliance Score button, and FindingsPanel conditional render
- `npm run build` passes with zero TypeScript errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Scoring engine service and POST /initiatives/{id}/score endpoint** - `ccfc22b` (feat)
2. **Task 2: Frontend findings panel and scoring trigger on questionnaire page** - `71819eb` (feat)

## Files Created/Modified

- `backend/app/services/scoring_engine.py` - create_scoring_engine() and score_all_answers() with asyncio.gather() concurrency
- `backend/app/api/v1/scoring.py` - POST /initiatives/{id}/score, FindingRead + ScoreResponse models, ownership check
- `backend/app/main.py` - Added scoring_router import and include_router at /api/v1
- `frontend/src/lib/scoring.ts` - triggerScoring() async function, Finding and ScoreResponse interfaces
- `frontend/src/components/questionnaire/FindingsPanel.tsx` - Findings display component with counts and per-finding list
- `frontend/src/routes/_app/questionnaire.tsx` - Added imports, state, handleGetScore(), button, and FindingsPanel render

## Decisions Made

- **asyncio.gather() for concurrent evaluation**: All answers evaluated in parallel using async_evaluate — more efficient than sequential awaits. ZEN Engine handles concurrent calls safely.
- **Named import { api } for scoring.ts**: api.ts exports `api` as a named export (not default). Used `import { api } from "./api"` consistent with questionnaire.ts — the plan template had `import api from "./api"` (default import) which would be a type error.
- **handleGetScore uses useState + try/finally**: Simpler than useMutation for a one-shot scoring request where we just want isScoring loading state and a result — no retry/cache behavior needed.
- **mami-scoring.json already correct**: The JDM file created in Plan 02-01 already had hitPolicy "first" and single-answer input format — no changes needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used named import { api } instead of default import**
- **Found during:** Task 2 (creating scoring.ts)
- **Issue:** Plan template showed `import api from "./api"` (default import), but `api.ts` uses named export `export const api = axios.create(...)` — default import would be a TypeScript error
- **Fix:** Used `import { api } from "./api"` consistent with the pattern in questionnaire.ts
- **Files modified:** frontend/src/lib/scoring.ts
- **Verification:** npm run build passes with zero TypeScript errors
- **Committed in:** 71819eb (Task 2 commit)

## Issues Encountered

None - one minor auto-fix for import style.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- POST /initiatives/{id}/score endpoint complete — frontend can display CRITICAL and NON_CRITICAL findings per initiative
- Phase 2 (Questionnaire & Scoring) is now fully complete: config foundation (02-01), answer storage (02-02), and scoring engine (02-03) all done
- Phase 3 (Evidence) can begin — evidence upload will link to questionnaire answers and MAMI codes
- No blockers

## Self-Check: PASSED

All key files exist on disk. All task commits verified in git log.

- FOUND: backend/app/services/scoring_engine.py
- FOUND: backend/app/api/v1/scoring.py
- FOUND: frontend/src/lib/scoring.ts
- FOUND: frontend/src/components/questionnaire/FindingsPanel.tsx
- FOUND: ccfc22b (Task 1 commit)
- FOUND: 71819eb (Task 2 commit)

---
*Phase: 02-questionnaire-and-scoring*
*Completed: 2026-02-15*
