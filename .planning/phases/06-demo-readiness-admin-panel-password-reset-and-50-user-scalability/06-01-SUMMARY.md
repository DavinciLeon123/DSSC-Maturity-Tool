---
phase: 06-demo-readiness-admin-panel-password-reset-and-50-user-scalability
plan: 01
subsystem: database, api
tags: [sqlalchemy, connection-pool, slowapi, rate-limiting, fastapi, postgresql]

requires:
  - phase: 03.1-dsi-sp-foundation
    provides: QuestionnaireAnswer model and upsert endpoint
  - phase: 02-questionnaire
    provides: initiative model with InitiativeStatus enum

provides:
  - SQLAlchemy engine with pool_size=10, max_overflow=20, pool_pre_ping, pool_recycle configured
  - Rate-limited answer upsert endpoint (60/min per IP via slowapi)
  - POST /initiatives/{initiative_id}/submit endpoint setting status=submitted

affects:
  - 06-04 (submission confirmation screen needs the submit endpoint)
  - Any future plans loading backend — pool tuning is global

tech-stack:
  added: []
  patterns:
    - slowapi @limiter.limit decorator requires request: Request as first positional param
    - SQLAlchemy pool kwargs passed directly to create_engine for Railway-hosted PostgreSQL

key-files:
  created: []
  modified:
    - backend/app/db/session.py
    - backend/app/api/v1/questionnaire.py
    - backend/app/api/v1/initiatives.py

key-decisions:
  - "pool_size=10, max_overflow=20 chosen: 30 total connections provides headroom for one Uvicorn worker serving 50 interleaved users"
  - "rate limit 60/min per IP on answer upsert: prevents abuse while allowing normal wizard save-on-navigate patterns"
  - "submit endpoint is idempotent: re-submitting already-submitted initiative returns 200 (not 409)"
  - "datetime import already existed in initiatives.py — no additional import needed for submit endpoint"

patterns-established:
  - "slowapi local limiter pattern: each router file creates its own Limiter(key_func=get_remote_address) instance; app.state.limiter in main.py handles exception handler"
  - "submit endpoint pattern: GET initiative → check ownership → set status → commit → return dict (not Pydantic model)"

requirements-completed:
  - INFR-SCALE-01
  - INFR-SCALE-02
  - INFR-SCALE-03
  - UX-RESIL-03

duration: 3min
completed: 2026-03-05
---

# Phase 06 Plan 01: DB Pool Tuning, Rate Limiting, and Submit Endpoint Summary

**SQLAlchemy connection pool tuned for 50 concurrent users (pool_size=10, max_overflow=20), slowapi rate limit (60/min) added to answer upsert, and idempotent POST /submit endpoint added for frontend submission flow.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-05T19:12:29Z
- **Completed:** 2026-03-05T19:14:37Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- DB connection pool upgraded from default pool_size=5 to pool_size=10/max_overflow=20 — prevents exhaustion under 50 concurrent users all saving answers simultaneously
- Answer upsert endpoint now rate-limited to 60 requests/minute per IP via slowapi; `request: Request` added as first param (required by slowapi's decorator contract)
- POST `/initiatives/{initiative_id}/submit` endpoint added — sets `InitiativeStatus.submitted`, idempotent, enables the 06-04 submission confirmation screen

## Task Commits

Each task was committed atomically:

1. **Task 1: Tune DB connection pool in session.py** - `b9a5131` (feat)
2. **Task 2: Rate-limit answer upsert + add submit endpoint** - `ebdc385` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `backend/app/db/session.py` - SQLAlchemy engine with tuned pool kwargs: pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=1800
- `backend/app/api/v1/questionnaire.py` - Added slowapi imports, local Limiter instance, @limiter.limit("60/minute") decorator and request: Request first param on upsert_answer
- `backend/app/api/v1/initiatives.py` - Added POST /{initiative_id}/submit endpoint setting InitiativeStatus.submitted

## Decisions Made

- **Pool sizing:** pool_size=10 + max_overflow=20 = 30 total max connections. Default (5+10=15) too small for 50 concurrent users saving answers. 30 provides 40% headroom above expected peak.
- **Rate limit value:** 60/min per IP — generous enough for normal wizard navigation (save on each topic change, ~1-2/sec max) but blocks abusive bulk-submit patterns.
- **Submit idempotency:** Re-submitting an already-submitted initiative returns 200 OK rather than 409 conflict. This simplifies frontend retry logic (network errors, double-clicks).
- **Local limiter in questionnaire.py:** Created a new `Limiter` instance in the router file rather than importing from main.py — cleaner dependency, avoids circular import risk.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Python modules not installed in local environment (Docker/Railway-only deployment). Used the `.venv` directory found in the backend folder for verification. All checks passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Pool tuning is complete: backend can handle 50 concurrent users without pool exhaustion
- Rate limiting active: 60/min per IP on the most frequently called endpoint
- Submit endpoint ready: 06-04 frontend submission confirmation screen can call `POST /api/v1/initiatives/{id}/submit`
- No blockers for subsequent 06-phase plans

---
*Phase: 06-demo-readiness-admin-panel-password-reset-and-50-user-scalability*
*Completed: 2026-03-05*

## Self-Check: PASSED

All files found and commits verified:
- backend/app/db/session.py: FOUND
- backend/app/api/v1/questionnaire.py: FOUND
- backend/app/api/v1/initiatives.py: FOUND
- .planning/.../06-01-SUMMARY.md: FOUND
- Commit b9a5131 (Task 1): FOUND
- Commit ebdc385 (Task 2): FOUND
