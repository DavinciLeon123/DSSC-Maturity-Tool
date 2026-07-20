---
phase: 01-foundation
plan: 02
subsystem: auth
tags: [fastapi, sqlmodel, jwt, bcrypt, slowapi, rbac, alembic, postgresql]

# Dependency graph
requires:
  - 01-01 (FastAPI scaffold, SQLModel engine, Alembic infrastructure, Docker Compose stack)
provides:
  - User SQLModel table with lockout fields (id, email, hashed_password, role, failed_login_attempts, lockout_until, created_at)
  - bcrypt password hashing and verification (direct, not passlib)
  - PyJWT access token issuance and decoding (24-hour expiry)
  - POST /api/v1/auth/register (201, UserCreate validation, 409 on duplicate)
  - POST /api/v1/auth/login (JWT, slowapi 10/min rate limit, 5-attempt lockout -> 423, timing-attack prevention)
  - GET /api/v1/auth/me (Bearer token, 401 on invalid/expired)
  - get_current_user and require_admin FastAPI dependency injection
  - Alembic migration 9a6864dd3f14 creating users table
  - Idempotent admin seed script (scripts/create_admin.py)
affects: [01-03, all subsequent plans that use protected endpoints]

# Tech tracking
tech-stack:
  added:
    - bcrypt>=4.2.0 (direct, passlib excluded — unmaintained)
    - PyJWT>=2.8.0
    - slowapi>=0.1.9 (rate limiting)
    - python-multipart>=0.0.9 (OAuth2PasswordRequestForm)
    - email-validator (pydantic[email] for EmailStr)
  patterns:
    - Timing-attack prevention: always call verify_password even when user not found (dummy hash)
    - Per-account lockout: stored in User.failed_login_attempts + User.lockout_until columns
    - RBAC via FastAPI Depends: get_current_user -> require_admin chaining
    - UserRead response schema explicitly excludes hashed_password
    - slowapi Limiter registered on app.state for middleware integration
    - Migration written manually (no live DB) — structurally identical to autogenerate output

key-files:
  created:
    - backend/app/models/user.py
    - backend/app/schemas/__init__.py
    - backend/app/schemas/auth.py
    - backend/app/core/security.py
    - backend/app/core/deps.py
    - backend/app/api/v1/auth.py
    - backend/scripts/create_admin.py
    - backend/alembic/versions/9a6864dd3f14_add_users_table.py
  modified:
    - backend/app/db/base.py (added User import for Alembic detection)
    - backend/app/main.py (mounted auth router, registered slowapi)

key-decisions:
  - "Migration written manually (no live DB) — autogenerate requires live connection, Docker Desktop not installed; migration content verified by inspection"
  - "Per-account lockout stored in users table (failed_login_attempts + lockout_until) — no Redis dependency for Phase 1"
  - "Timing attack prevention via dummy hash on unknown-user login path — equalizes response time regardless of email existence"
  - "JWT sub = user email (not user ID) — simpler for Phase 1; can be migrated to ID in later phases if needed"
  - "slowapi per-IP rate limit (10/min) complements per-account lockout (5 attempts) — layered defense"

# Metrics
duration: 4min
completed: 2026-02-15
---

# Phase 1 Plan 02: Authentication System Summary

**JWT authentication with bcrypt hashing, PyJWT token issuance, slowapi rate limiting, 5-attempt per-account lockout, USER/ADMIN RBAC via FastAPI dependency injection, and idempotent admin seed script**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-15T09:15:23Z
- **Completed:** 2026-02-15T09:19:14Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- User SQLModel table with all required lockout fields (7 columns including role, failed_login_attempts, lockout_until)
- Security utilities: bcrypt direct hash/verify and PyJWT create/decode with 24-hour expiry (verified: 86400s)
- Three auth endpoints registered at /api/v1/auth: register (201), login (JWT + lockout), /me (Bearer)
- Login security: slowapi 10/min rate limit + 5-attempt lockout triggering 423 Locked + timing-attack prevention via dummy hash
- RBAC: get_current_user (401 on invalid token) + require_admin (403 on non-ADMIN role) via FastAPI Depends
- UserRead response schema explicitly excludes hashed_password — no credential leak
- Admin seed script idempotent: creates admin@... user with ADMIN role, skips if already exists
- Alembic migration 9a6864dd3f14_add_users_table with create_table + ix_user_email unique index

## Task Commits

Each task was committed atomically:

1. **Task 1: User model, security utils, and Alembic migration** - `1aa7924` (feat)
2. **Task 2: Auth endpoints, RBAC deps, and admin seed script** - `f7e068e` (feat)

## Files Created/Modified

- `backend/app/models/user.py` - User SQLModel table model with lockout fields
- `backend/app/schemas/auth.py` - UserCreate (12-char validation, common password list), UserRead (no hashed_password), Token
- `backend/app/core/security.py` - bcrypt hash/verify, PyJWT create/decode_access_token, 24h ACCESS_TOKEN_EXPIRE_HOURS
- `backend/app/core/deps.py` - get_current_user (decode token, fetch user), require_admin (role=ADMIN gate)
- `backend/app/api/v1/auth.py` - register, login (rate-limited, lockout), /me endpoints
- `backend/app/main.py` - Updated: auth router mounted, slowapi registered
- `backend/app/db/base.py` - Updated: added User import for Alembic model detection
- `backend/scripts/create_admin.py` - Idempotent admin seed script
- `backend/alembic/versions/9a6864dd3f14_add_users_table.py` - Users table migration with email unique index

## Decisions Made

- **Migration written manually**: autogenerate requires a live PostgreSQL connection, which is not available on this machine (Docker Desktop not installed). The migration was written manually — structurally identical to what autogenerate would produce. Will be applied when Docker is running.
- **Per-account lockout in users table**: stored in `failed_login_attempts` and `lockout_until` columns — avoids Redis dependency for Phase 1. Sufficient for expected load.
- **JWT sub = email**: simpler for Phase 1. Can be migrated to user ID if needed without breaking consumers (auth checks sub via database lookup in get_current_user).
- **Timing-attack prevention**: dummy hash computed at module load, used in the no-user-found path — prevents username enumeration via response time differences.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Alembic autogenerate requires live database connection**
- **Found during:** Task 1 (Alembic migration step)
- **Issue:** `alembic revision --autogenerate` failed with `psycopg2.OperationalError: connection refused` — PostgreSQL is not running (Docker Desktop not installed, same constraint as Plan 01-01)
- **Fix:** Wrote migration file manually (`9a6864dd3f14_add_users_table.py`) with correct `create_table` and `create_index` operations, matching what autogenerate would produce
- **Files modified:** `backend/alembic/versions/9a6864dd3f14_add_users_table.py` (manually authored)
- **Verification:** Migration file imports cleanly, `upgrade()` contains `op.create_table('user', ...)` with all 7 columns and unique email index
- **Committed in:** 1aa7924

## Issues Encountered

**Docker not installed**: Same constraint as Plan 01-01. The database curl verifications (register, login, /me, admin seed run) could not be executed. All code was verified by import inspection and unit-level testing:
- All imports resolve
- bcrypt round-trip: True/False correct
- JWT expiry: exactly 86400s (24h)
- Lockout constants: 5 attempts, 15 minutes
- Schema safety: no hashed_password in UserRead
- Migration: create_table present, correct columns

**Action required**: When Docker Desktop is installed, run:
```bash
docker compose up -d
cd backend && uv run python scripts/create_admin.py
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123!"}'
# Expected: 201
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -F "username=test@example.com" -F "password=TestPassword123!" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"
# Expected: 200, role="USER"
```

## User Setup Required

None beyond Docker Desktop installation (tracked in STATE.md blockers).

## Next Phase Readiness

- Auth system is structurally complete: endpoints, RBAC, lockout, JWT, seed script
- Plan 01-03 can use `require_admin` and `get_current_user` as FastAPI dependencies
- Migration will apply cleanly once database is running
- All imports verified; FastAPI app instantiates without errors

---
*Phase: 01-foundation*
*Completed: 2026-02-15*

## Self-Check: PASSED

- backend/app/models/user.py: FOUND
- backend/app/schemas/auth.py: FOUND
- backend/app/core/security.py: FOUND
- backend/app/core/deps.py: FOUND
- backend/app/api/v1/auth.py: FOUND
- backend/scripts/create_admin.py: FOUND
- backend/alembic/versions/9a6864dd3f14_add_users_table.py: FOUND
- .planning/phases/01-foundation/01-02-SUMMARY.md: FOUND
- Commit 1aa7924 (Task 1): FOUND in git log
- Commit f7e068e (Task 2): FOUND in git log
