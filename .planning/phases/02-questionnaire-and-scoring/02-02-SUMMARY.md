---
phase: 02-questionnaire-and-scoring
plan: 02
subsystem: api
tags: [rjsf, questionnaire, react, fastapi, sqlmodel, postgres, tanstack-query, antd, auto-save]

# Dependency graph
requires:
  - phase: 02-questionnaire-and-scoring
    plan: 01
    provides: questionnaire-v1.json config in app.state, get_questionnaire_config dep, ZEN engine singleton
  - phase: 01-foundation
    provides: FastAPI app, Initiative model, auth deps, frontend router setup

provides:
  - QuestionnaireAnswer SQLModel table with row-per-question storage and UniqueConstraint
  - Alembic migration b3f7c9a1d2e8 creating questionnaire_answer table
  - AnswerCreate Pydantic schema with model_validator (COMPLY_EXPLAIN requires rationale)
  - GET /api/v1/questionnaire/config endpoint returning questionnaire structure from app.state
  - PUT /api/v1/questionnaire/initiatives/{id}/answers/{qid} with PostgreSQL on_conflict_do_update
  - GET /api/v1/questionnaire/initiatives/{id}/answers for resume-from-session
  - RJSF-based questionnaire page at /_app/questionnaire with category tabs and auto-save
  - NotApplicableWidget and ComplyExplainWidget RJSF custom widgets
  - Questionnaire nav item in Sidebar

affects:
  - 02-03 (scoring engine will query questionnaire_answer table for all answers per initiative)
  - 03-evidence (evidence upload links to questionnaire answers)

# Tech tracking
tech-stack:
  added:
    - "@rjsf/core@^6.3.1 (React JSON Schema Form — questionnaire rendering)"
    - "@rjsf/utils@^6.3.1 (RJSF utilities and types)"
    - "@rjsf/validator-ajv8@^6.3.1 (AJV8 schema validator for RJSF)"
    - "antd@^6.3.0 (Ant Design — installed as RJSF peer dep, used in Phase 3+)"
  patterns:
    - "PostgreSQL on_conflict_do_update via pg_insert for upsert — row-per-question answer storage"
    - "RJSF custom widgets (notApplicableWidget, complyExplainWidget) per question answer_type"
    - "TanStack Query useMutation for auto-save on each answer change (no explicit save button)"
    - "React.StrictMode replaced with QueryClientProvider fragment — RJSF React 19 compatibility workaround"
    - "routeTree.gen.ts committed and updated manually for tsc pre-flight (Vite plugin runs after tsc)"

key-files:
  created:
    - backend/app/models/questionnaire.py
    - backend/app/schemas/questionnaire.py
    - backend/app/api/v1/questionnaire.py
    - backend/alembic/versions/b3f7c9a1d2e8_add_questionnaire_answers_table.py
    - frontend/src/lib/questionnaire.ts
    - frontend/src/components/questionnaire/NotApplicableWidget.tsx
    - frontend/src/components/questionnaire/ComplyExplainWidget.tsx
    - frontend/src/components/questionnaire/QuestionnaireForm.tsx
    - frontend/src/routes/_app/questionnaire.tsx
  modified:
    - backend/app/db/base.py
    - backend/app/main.py
    - frontend/package.json
    - frontend/src/components/layout/Sidebar.tsx
    - frontend/src/main.tsx
    - frontend/src/routeTree.gen.ts

key-decisions:
  - "pg_insert on_conflict_do_update targeting uq_answer_per_question constraint — PostgreSQL-native upsert, avoids SELECT+UPSERT race condition"
  - "Row-per-question storage with UniqueConstraint(initiative_id, question_id) — enables partial saves and resume"
  - "COMPLY_EXPLAIN answers use composite {value, rationale} object in RJSF formData — passed as-is through widget and unwrapped before API call"
  - "QueryClientProvider added to main.tsx alongside StrictMode removal — prerequisite for useQuery/useMutation in questionnaire page"
  - "routeTree.gen.ts manually updated before build — TanStack Router Vite plugin regenerates on next dev/build run"

patterns-established:
  - "RJSF custom widget pattern: WidgetProps (type import), composite object for COMPLY_EXPLAIN {value, rationale}"
  - "Auto-save pattern: useMutation fires on each RJSF onChange, no explicit save button, isPending indicator"
  - "Answer resume pattern: savedAnswers loaded on mount, useMemo builds formData map passed to RJSF formData prop"

# Metrics
duration: 20min
completed: 2026-02-15
---

# Phase 2 Plan 02: Questionnaire Answer Storage and RJSF Frontend Summary

**PostgreSQL upsert-backed questionnaire answer storage with RJSF frontend, category tabs, NotApplicableWidget/ComplyExplainWidget custom widgets, and auto-save via TanStack Query mutations**

## Performance

- **Duration:** 20 min
- **Started:** 2026-02-15T18:57:15Z
- **Completed:** 2026-02-15T19:17:00Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments

- QuestionnaireAnswer SQLModel table with UniqueConstraint(initiative_id, question_id, name="uq_answer_per_question") and Alembic migration with 3 indexes
- Three API endpoints: GET /questionnaire/config (from app.state), PUT /questionnaire/initiatives/{id}/answers/{qid} (PostgreSQL on_conflict_do_update), GET /questionnaire/initiatives/{id}/answers (for resume)
- RJSF questionnaire page with 4 category tabs, dimension sections, custom NotApplicableWidget (YES/NO/COMPLY_EXPLAIN/NOT_APPLICABLE) and ComplyExplainWidget (YES/NO/COMPLY_EXPLAIN), auto-save on every answer change
- AnswerCreate model_validator rejects COMPLY_EXPLAIN submissions without rationale (QUES-05 validation)
- Answer resume: saved answers loaded on mount, formData map built from AnswerRecord[] for seamless session restore (QUES-02)

## Task Commits

Each task was committed atomically:

1. **Task 1: QuestionnaireAnswer model, schemas, Alembic migration, and API endpoints** - `f8463e3` (feat)
2. **Task 2: Frontend questionnaire page with RJSF, category tabs, custom widgets, and auto-save** - `de96b33` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/app/models/questionnaire.py` - QuestionnaireAnswer SQLModel with UniqueConstraint
- `backend/app/schemas/questionnaire.py` - AnswerCreate (model_validator), AnswerRead
- `backend/app/api/v1/questionnaire.py` - 3 endpoints with pg_insert upsert and ownership checks
- `backend/alembic/versions/b3f7c9a1d2e8_add_questionnaire_answers_table.py` - Migration creating table + 3 indexes
- `backend/app/db/base.py` - Added QuestionnaireAnswer import for Alembic autogenerate
- `backend/app/main.py` - Registered questionnaire_router at /api/v1
- `frontend/src/lib/questionnaire.ts` - fetchQuestionnaireConfig, fetchAnswers, saveAnswer API calls
- `frontend/src/components/questionnaire/NotApplicableWidget.tsx` - RJSF widget for NOT_APPLICABLE toggle
- `frontend/src/components/questionnaire/ComplyExplainWidget.tsx` - RJSF widget for COMPLY_EXPLAIN
- `frontend/src/components/questionnaire/QuestionnaireForm.tsx` - RJSF Form wrapper with custom widgets
- `frontend/src/routes/_app/questionnaire.tsx` - Questionnaire page with category tabs and auto-save
- `frontend/src/components/layout/Sidebar.tsx` - Added Questionnaire nav item
- `frontend/src/main.tsx` - Replaced StrictMode with QueryClientProvider (RJSF compatibility)
- `frontend/package.json` - Added @rjsf/core, @rjsf/utils, @rjsf/validator-ajv8, antd
- `frontend/src/routeTree.gen.ts` - Added /_app/questionnaire route

## Decisions Made

- **pg_insert on_conflict_do_update**: PostgreSQL-native upsert via sqlalchemy.dialects.postgresql.insert targeting the uq_answer_per_question UniqueConstraint — atomically handles first-save and subsequent updates without SELECT+UPDATE race
- **Composite {value, rationale} for COMPLY_EXPLAIN in RJSF**: Widgets receive/emit `{value: "COMPLY_EXPLAIN", rationale: string}` as a single object; questionnaire page unwraps before sending to API
- **QueryClientProvider added to main.tsx**: The questionnaire page uses useQuery/useMutation — QueryClientProvider is required. StrictMode removed simultaneously per RJSF React 19 compatibility (Pitfall 2 from research)
- **routeTree.gen.ts manually synced**: The TanStack Router Vite plugin regenerates this file on `vite build` but `tsc -b` runs first in the build script. Updated manually; Vite plugin will overwrite with identical content on next dev server start

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TypeScript verbatimModuleSyntax requires `import type` for type-only imports**
- **Found during:** Task 2 (frontend build)
- **Issue:** `WidgetProps`, `RJSFSchema`, `UiSchema` imported without `type` keyword; tsconfig has verbatimModuleSyntax enabled
- **Fix:** Changed to `import type { WidgetProps }` and `import type { RJSFSchema, UiSchema }` in widget and form components
- **Files modified:** NotApplicableWidget.tsx, ComplyExplainWidget.tsx, QuestionnaireForm.tsx
- **Verification:** `npm run build` passes with zero TypeScript errors
- **Committed in:** de96b33 (Task 2 commit)

**2. [Rule 1 - Bug] IChangeEvent not exported from @rjsf/utils — lives in @rjsf/core**
- **Found during:** Task 2 (frontend build)
- **Issue:** onChange handler typed against `{ formData: Record<string, unknown> }` — RJSF IChangeEvent has `formData?: Record<string, unknown>` (optional); wrong import path
- **Fix:** Changed to `import type { IChangeEvent } from "@rjsf/core"` and updated handler signature to `IChangeEvent<Record<string, unknown>>`
- **Files modified:** QuestionnaireForm.tsx
- **Verification:** `npm run build` passes with zero TypeScript errors
- **Committed in:** de96b33 (Task 2 commit)

**3. [Rule 2 - Missing Critical] Added QueryClientProvider to main.tsx**
- **Found during:** Task 2 (questionnaire page uses useQuery/useMutation)
- **Issue:** TanStack Query hooks require QueryClientProvider ancestor — not present in original main.tsx
- **Fix:** Added `QueryClient` and `QueryClientProvider` from @tanstack/react-query wrapping RouterProvider
- **Files modified:** frontend/src/main.tsx
- **Verification:** Build passes; hooks will have provider in runtime tree
- **Committed in:** de96b33 (Task 2 commit)

**4. [Rule 1 - Bug] routeTree.gen.ts not updated for questionnaire route — tsc fails before Vite runs**
- **Found during:** Task 2 (frontend build — tsc pre-flight)
- **Issue:** TanStack Router Vite plugin regenerates routeTree.gen.ts during `vite build` but `tsc -b` runs first; TypeScript cannot resolve `/_app/questionnaire` route type or `/questionnaire` in Sidebar Link
- **Fix:** Manually added questionnaire route to routeTree.gen.ts (imports, route object, all interface entries)
- **Files modified:** frontend/src/routeTree.gen.ts
- **Verification:** `npm run build` passes; Vite plugin re-confirms route on next dev server start
- **Committed in:** de96b33 (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (2 type bugs, 1 missing critical, 1 build-order bug)
**Impact on plan:** All auto-fixes required for correctness and TypeScript compilation. No scope creep. The build-order issue with routeTree.gen.ts is a recurring pattern — documented for future plans.

## Issues Encountered

None - all issues resolved via deviation rules.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- QuestionnaireAnswer table and API complete — Plan 02-03 (scoring engine) can read all answers per initiative via GET /questionnaire/initiatives/{id}/answers
- RJSF frontend renders and auto-saves answers; users can fill the questionnaire and resume across sessions
- antd installed as peer dep — ready for @gorules/jdm-editor in Phase 3+
- No blockers

## Self-Check: PASSED

All key files exist on disk. All task commits verified in git log.

- FOUND: backend/app/models/questionnaire.py
- FOUND: backend/app/schemas/questionnaire.py
- FOUND: backend/app/api/v1/questionnaire.py
- FOUND: backend/alembic/versions/b3f7c9a1d2e8_add_questionnaire_answers_table.py
- FOUND: frontend/src/routes/_app/questionnaire.tsx
- FOUND: frontend/src/components/questionnaire/NotApplicableWidget.tsx
- FOUND: frontend/src/components/questionnaire/ComplyExplainWidget.tsx
- FOUND: frontend/src/components/questionnaire/QuestionnaireForm.tsx
- FOUND: frontend/src/lib/questionnaire.ts
- FOUND: f8463e3 (Task 1 commit)
- FOUND: de96b33 (Task 2 commit)

---
*Phase: 02-questionnaire-and-scoring*
*Completed: 2026-02-15*
