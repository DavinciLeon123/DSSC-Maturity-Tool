# Phase 1: Foundation - Research

**Researched:** 2026-02-14
**Domain:** FastAPI + SQLModel + PostgreSQL + React/Vite + Docker Compose — authentication, RBAC, initiative CRUD, OpenAPI
**Confidence:** HIGH (core stack verified via official docs and Context7-equivalent sources)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Auth behavior
- Rate limit after 5 failed login attempts (temporary lockout)
- JWT session duration: 24 hours
- No email verification for MVP (added to backlog for future version)
- Password rules: Claude's discretion

#### Admin account creation
- Claude's discretion on approach (seed script vs first-user-is-admin)

#### Initiative registration
- Fields: name, description, sector/domain, contact person (name + email), organization
- Sector field: predefined dropdown with "Other" free-text option
- Status workflow: Draft → Active → Submitted
- All fields editable anytime (until submitted)
- One initiative per user for MVP

#### UI shell & branding
- Sidebar navigation layout (dashboard-style)
- Landing page with MAMI framework intro + call-to-action (register/login)
- Extract actual colors from coe-dsc.nl website
- CoE-DSC / TNO branding on landing page

### Claude's Discretion
- Admin account creation method
- Password complexity rules
- Exact sidebar navigation items
- Loading states and error pages
- Responsive behavior

### Deferred Ideas (OUT OF SCOPE)
- Email verification — future version (noted by user)
- Password reset flow — not discussed, likely v2
</user_constraints>

---

## Summary

This phase builds the full skeleton: Python FastAPI backend with JWT auth and USER/ADMIN RBAC, PostgreSQL via SQLModel + Alembic, a DSI initiative CRUD endpoint, OpenAPI docs at `/docs`, a React/Vite frontend shell with coe-dsc.nl branding, and Docker Compose orchestrating all services.

The confirmed stack from prior research (FastAPI + SQLModel + PostgreSQL + React/Vite) is mature and well-supported as of early 2026. The key version constraints are: SQLModel 0.0.33 requires SQLAlchemy `>=2.0.14,<2.1.0` (confirmed from SQLModel's own pyproject.toml) and Pydantic v2 only (v1 support dropped in SQLModel 0.0.31). The prior decision to use `bcrypt` directly instead of `passlib` is valid — but research reveals the official FastAPI docs now recommend `pwdlib` as the modern replacement. Since the prior decision explicitly says "bcrypt direct", this research documents both and flags it as a point worth confirming.

The coe-dsc.nl brand colors have been extracted directly from the live site. Rate limiting for login lockout uses `slowapi`. The RBAC pattern uses FastAPI's dependency injection system with reusable `Depends()` callables — not middleware — which is the idiomatic FastAPI pattern.

**Primary recommendation:** Use the pattern from the FastAPI full-stack template as the reference architecture: SQLModel models, Alembic autogenerate, JWT via PyJWT, bcrypt direct for password hashing, slowapi for rate limiting, TanStack Router for the React SPA layout.

---

## Standard Stack

### Core (Backend)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi[standard] | >=0.115.0 | REST API framework, OpenAPI auto-gen | Official choice; includes uvicorn, pydantic |
| sqlmodel | 0.0.33 | ORM bridging SQLAlchemy + Pydantic | Same author as FastAPI; type-safe models |
| sqlalchemy | >=2.0.14,<2.1.0 | DB engine (required by SQLModel) | **Must pin <2.1.0** per SQLModel's pyproject.toml |
| alembic | >=1.13.0 | DB migrations | Industry standard for SQLAlchemy |
| psycopg2-binary | >=2.9.0 | PostgreSQL sync driver | Simple setup for non-async apps |
| PyJWT | >=2.8.0 | JWT creation and verification | Official FastAPI recommendation (replaces python-jose) |
| bcrypt | >=4.2.0 | Password hashing | Direct usage, actively maintained (v5.0.0 released Sep 2025) |
| slowapi | >=0.1.9 | Rate limiting (login lockout) | De facto standard rate limiter for FastAPI/Starlette |
| pydantic-settings | >=2.0.0 | Settings from env vars | Standard config management for FastAPI |
| python-multipart | >=0.0.9 | OAuth2 form data (login endpoint) | Required for OAuth2PasswordRequestForm |

### Core (Frontend)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | ^19.0.0 | UI framework | Confirmed stack choice |
| vite | ^6.0.0 | Build tool | Confirmed stack choice |
| @tanstack/react-router | ^1.x | File-based routing + layouts | Best-in-class type-safe routing for Vite/React |
| @tanstack/react-query | ^5.x | Server state / API caching | Pairs with TanStack Router; official template uses it |
| axios | ^1.7.0 | HTTP client | Simple, widely used; easy interceptors for auth headers |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncpg | >=0.30.0 | Async PostgreSQL driver | If async SQLAlchemy is added later; not needed for sync MVP |
| uvicorn | included in fastapi[standard] | ASGI server | Auto-included |
| python-dotenv | via pydantic-settings | .env file loading | Dev environment |
| alembic | >=1.13.0 | Migrations | Run via `alembic upgrade head` in Docker entrypoint |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| bcrypt (direct) | pwdlib[argon2] | FastAPI official docs NOW recommend pwdlib with Argon2 — see note below |
| PyJWT | python-jose | python-jose is abandoned (no release in ~3 years); PyJWT is the current recommendation |
| slowapi (rate limiting) | Custom in-memory dict | slowapi uses same Redis/in-memory backend, handles edge cases; don't hand-roll |
| TanStack Router | React Router v7 | TanStack is more type-safe; React Router v7 is also fine if team prefers |

**IMPORTANT NOTE on bcrypt vs pwdlib:** The prior decision says "bcrypt direct (not passlib) — passlib unmaintained since 2020." This is correct. However, the current official FastAPI docs (verified Feb 2026) now recommend `pwdlib[argon2]` over direct bcrypt, because Argon2 is more resistant to GPU cracking. The PR to switch the official FastAPI full-stack template to direct bcrypt (#1539) was closed in favor of pwdlib (#2104). **Recommendation: use `bcrypt` directly as decided (it is valid and actively maintained at v5.0.0), but document the pwdlib option for a future upgrade.**

### Backend Installation
```bash
uv add "fastapi[standard]>=0.115.0" "sqlmodel==0.0.33" "sqlalchemy>=2.0.14,<2.1.0" \
       "alembic>=1.13.0" "psycopg2-binary>=2.9.0" "PyJWT>=2.8.0" \
       "bcrypt>=4.2.0" "slowapi>=0.1.9" "pydantic-settings>=2.0.0" \
       "python-multipart>=0.0.9"
```

### Frontend Installation
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install @tanstack/react-router @tanstack/react-query axios
npm install -D @tanstack/router-devtools
```

---

## Architecture Patterns

### Recommended Project Structure
```
mami-checker/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, router registration, lifespan
│   │   ├── core/
│   │   │   ├── config.py        # pydantic-settings: DATABASE_URL, SECRET_KEY, etc.
│   │   │   ├── security.py      # JWT creation/verification, bcrypt hash/verify
│   │   │   └── deps.py          # Shared FastAPI dependencies (get_session, get_current_user, require_admin)
│   │   ├── models/
│   │   │   ├── user.py          # User SQLModel table model
│   │   │   └── initiative.py    # Initiative SQLModel table model
│   │   ├── schemas/
│   │   │   ├── auth.py          # Token, TokenData, UserCreate, UserRead Pydantic schemas
│   │   │   └── initiative.py    # InitiativeCreate, InitiativeRead, InitiativeUpdate schemas
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py      # /register, /login, /logout endpoints
│   │   │   │   └── initiatives.py # CRUD endpoints for initiatives
│   │   │   └── deps.py          # (re-export or place here)
│   │   └── db/
│   │       ├── base.py          # SQLModel metadata import (for Alembic)
│   │       └── session.py       # get_session dependency, engine creation
│   ├── alembic/
│   │   ├── env.py               # target_metadata = SQLModel.metadata
│   │   └── versions/            # Migration files
│   ├── scripts/
│   │   └── create_admin.py      # Seed script: creates admin user if not exists
│   ├── alembic.ini
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── __root.tsx       # Root layout (auth check)
│   │   │   ├── _auth/           # Unauthenticated layout (landing, login, register)
│   │   │   │   ├── index.tsx    # Landing page
│   │   │   │   ├── login.tsx
│   │   │   │   └── register.tsx
│   │   │   └── _app/            # Authenticated layout (sidebar shell)
│   │   │       ├── _layout.tsx  # Sidebar navigation wrapper
│   │   │       └── dashboard.tsx
│   │   ├── components/
│   │   │   ├── ui/              # Reusable UI primitives (Button, Input, etc.)
│   │   │   └── layout/          # Sidebar, Header components
│   │   ├── lib/
│   │   │   ├── api.ts           # Axios instance with auth interceptor
│   │   │   └── auth.ts          # Token storage, login/logout helpers
│   │   └── main.tsx
│   ├── public/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── docker-compose.override.yml  # Dev overrides (volume mounts, hot reload)
└── .env
```

### Pattern 1: JWT Authentication with FastAPI Dependency Injection

**What:** JWT issued on login; verified on each protected request via a reusable `Depends()` callable. Role enforcement via separate role-check dependencies.
**When to use:** All protected endpoints.

```python
# Source: FastAPI official docs https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
# app/core/security.py

import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings

ALGORITHM = "HS256"

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> str | None:
    from jwt.exceptions import InvalidTokenError
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except InvalidTokenError:
        return None
```

```python
# app/core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.user import User
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    sub = decode_token(token)
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    user = session.exec(select(User).where(User.email == sub)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="User not found")
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Admin access required")
    return current_user
```

### Pattern 2: SQLModel Model Definition

**What:** SQLModel combines SQLAlchemy ORM table definition with Pydantic schema in one class.
**When to use:** Every database table.

```python
# Source: SQLModel docs https://sqlmodel.tiangolo.com/
# app/models/user.py

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    role: str = Field(default="USER")  # "USER" or "ADMIN"
    failed_login_attempts: int = Field(default=0)
    lockout_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

```python
# app/models/initiative.py

from enum import Enum
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class InitiativeStatus(str, Enum):
    draft = "draft"
    active = "active"
    submitted = "submitted"

class Initiative(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str
    description: str
    sector: str                         # From predefined list or "Other"
    sector_other: Optional[str] = None  # Free text if sector == "Other"
    contact_name: str
    contact_email: str
    organization: str
    status: InitiativeStatus = Field(default=InitiativeStatus.draft)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### Pattern 3: Alembic env.py with SQLModel

**What:** Configure Alembic to see all SQLModel models for autogenerate.
**Critical detail:** Must import all models before `target_metadata` is set.

```python
# alembic/env.py (critical section)
# Source: https://arunanshub.hashnode.dev/using-sqlmodel-with-alembic

import sqlmodel.sql.sqltypes  # REQUIRED — prevents type mapping errors
from sqlmodel import SQLModel

# Import ALL models so Alembic can detect them
from app.models.user import User       # noqa: F401
from app.models.initiative import Initiative  # noqa: F401

target_metadata = SQLModel.metadata

# In context.configure() calls, add:
# render_as_batch=True,
# user_module_prefix="sqlmodel.sql.sqltypes.",
```

```ini
# alembic/script.py.mako — add this import at the top
import sqlmodel.sql.sqltypes
```

### Pattern 4: Login Rate Limiting with SlowAPI

**What:** Limit login attempts to prevent brute force; track failures in DB for per-account lockout.
**When to use:** On the `/login` endpoint.

```python
# Source: https://github.com/laurentS/slowapi
# app/main.py

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(...)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

```python
# app/api/v1/auth.py
from slowapi import Limiter
from slowapi.util import get_remote_address

@router.post("/login")
@limiter.limit("10/minute")        # IP-level: 10 per minute
async def login(request: Request, ...):
    # Additionally: track per-account failures in User.failed_login_attempts
    # Lock for 15 minutes after 5 consecutive failures
    pass
```

**Note:** The 5-attempts lockout is per-account (stored in DB), not just IP-based. Implement both:
1. Per-IP rate limit via slowapi (handles distributed attacks)
2. Per-account lockout counter in `User.failed_login_attempts` + `User.lockout_until`

### Pattern 5: Admin Seed Script

**Recommendation:** Use a seed script (not first-user-is-admin). Reasons:
- Deterministic; admin email/password set via environment variables
- Idempotent: checks if admin exists before creating
- Invoked in Docker entrypoint before starting uvicorn

```python
# scripts/create_admin.py
from sqlmodel import Session, select, create_engine
from app.models.user import User
from app.core.security import hash_password
from app.core.config import settings

def create_admin():
    engine = create_engine(settings.DATABASE_URL)
    with Session(engine) as session:
        existing = session.exec(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        ).first()
        if not existing:
            admin = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role="ADMIN"
            )
            session.add(admin)
            session.commit()
            print(f"Admin user created: {settings.ADMIN_EMAIL}")
        else:
            print("Admin user already exists — skipping")

if __name__ == "__main__":
    create_admin()
```

### Pattern 6: Docker Compose Setup

```yaml
# docker-compose.yml
# Source: https://fastapi.tiangolo.com/deployment/docker/ + official template pattern

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: mami_db
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d mami_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/mami_db
      SECRET_KEY: ${SECRET_KEY}
      ADMIN_EMAIL: ${ADMIN_EMAIL}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
    ports:
      - "8000:8000"
    command: >
      sh -c "alembic upgrade head &&
             python scripts/create_admin.py &&
             fastapi run app/main.py --port 8000"

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

### Pattern 7: TanStack Router Layout Split (Authenticated vs Public)

**What:** Separate route trees for public pages (landing/login/register) and authenticated pages (sidebar shell).
**When to use:** Any app with a fundamentally different layout for logged-in vs logged-out users.

```tsx
// Source: https://tanstack.com/router/v1/docs
// src/routes/__root.tsx
import { Outlet, createRootRoute } from '@tanstack/react-router'
import { useAuthStore } from '@/lib/auth'

export const Route = createRootRoute({
  component: () => <Outlet />,
})

// src/routes/_app/_layout.tsx  — authenticated shell with sidebar
export const Route = createFileRoute('/_app')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: '/login' })
  },
  component: AppLayout,  // Renders sidebar + <Outlet />
})

// src/routes/_auth/index.tsx  — public landing page
export const Route = createFileRoute('/_auth/')({
  component: LandingPage,
})
```

### Anti-Patterns to Avoid

- **Storing JWT in localStorage without httpOnly cookies:** Fine for MVP SPA, but document the XSS risk. Use `Authorization: Bearer` header pattern with in-memory token + refresh-token-in-httpOnly cookie for production hardening.
- **Doing role checks in UI only:** Role MUST be enforced by the `require_admin` dependency on backend routes. UI gating is UX-only.
- **Not importing models in Alembic env.py:** Alembic cannot detect tables it doesn't know about. Missing import = silent migration failure.
- **Using `SQLModel.metadata` without importing `sqlmodel.sql.sqltypes`:** Causes type mapping errors in generated migrations.
- **Setting `SQLAlchemy >= 2.1.0`:** SQLModel 0.0.33 pins `<2.1.0` in its own pyproject.toml — letting SQLAlchemy 2.1+ install will cause import errors.
- **python-jose for JWT:** It is abandoned. Use PyJWT.
- **passlib for password hashing:** It is unmaintained since ~2020. Use bcrypt directly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rate limiting | Custom IP counter dict | `slowapi` | Thread safety, Redis support, decorator syntax |
| JWT creation/verification | Custom HMAC | `PyJWT` | Handles expiration, algorithm selection, timing-safe comparison |
| Password hashing | Custom bcrypt wrapper | `bcrypt` directly | Salt generation, work factor, timing-safe compare built in |
| DB migrations | Manual ALTER TABLE | `alembic` autogenerate | Schema drift detection, rollback, version history |
| Settings from env | `os.environ.get()` scattered | `pydantic-settings` | Type coercion, `.env` loading, validation at startup |
| OpenAPI docs | Manual doc endpoint | FastAPI built-in | Auto-generated from route definitions; zero extra work |
| CORS config | Manual middleware | `fastapi.middleware.cors.CORSMiddleware` | Handles preflight, credentials, origins correctly |

**Key insight:** FastAPI's dependency injection system handles auth guard composition without custom middleware — use `Depends()` chains, not raw middleware, for RBAC.

---

## Common Pitfalls

### Pitfall 1: SQLAlchemy Version Mismatch
**What goes wrong:** `ImportError` or unexpected behavior when SQLAlchemy 2.1.0+ is installed.
**Why it happens:** SQLModel 0.0.33 pins `sqlalchemy>=2.0.14,<2.1.0` in its own pyproject.toml. If uv resolves a newer version, imports fail.
**How to avoid:** Explicitly add `"sqlalchemy>=2.0.14,<2.1.0"` to pyproject.toml dependencies. Don't rely on SQLModel's transitive constraint.
**Warning signs:** `ImportError: cannot import name 'X' from 'sqlalchemy'` on startup.

### Pitfall 2: Alembic Cannot Detect Tables
**What goes wrong:** `alembic revision --autogenerate` produces empty migrations even though models exist.
**Why it happens:** Models not imported in `alembic/env.py` before `target_metadata = SQLModel.metadata` is set.
**How to avoid:** Explicitly import every model module in `env.py`. Add a comment: `# DO NOT REMOVE — Alembic needs these imports`.
**Warning signs:** Migration file contains only `pass` in `upgrade()`.

### Pitfall 3: Alembic Type Mapping Errors with SQLModel
**What goes wrong:** Generated migration has `sa.Column('field', sa.AutoString())` or similar unknown types.
**Why it happens:** SQLModel uses custom SQLAlchemy types; Alembic doesn't know how to render them without the import.
**How to avoid:** Add `import sqlmodel.sql.sqltypes` to both `env.py` and `script.py.mako`. Add `user_module_prefix="sqlmodel.sql.sqltypes."` to `context.configure()`.
**Warning signs:** Alembic warning messages about unrenderable types during `--autogenerate`.

### Pitfall 4: JWT Token Stored Insecurely in Frontend
**What goes wrong:** XSS attack reads token from localStorage, impersonates user.
**Why it happens:** Convenience — localStorage is simple and persists across sessions.
**How to avoid:** For MVP, use in-memory storage (React state / context) and accept that tokens are lost on refresh. Or store in sessionStorage with documented trade-off. Do NOT store in localStorage without understanding XSS risk.
**Warning signs:** Token readable via `localStorage.getItem('token')` in browser console.

### Pitfall 5: CORS Blocking Frontend-to-Backend Calls
**What goes wrong:** Browser blocks requests from `localhost:3000` to `localhost:8000` in development.
**Why it happens:** FastAPI default has no CORS headers.
**How to avoid:** Add CORSMiddleware in development with `allow_origins=["http://localhost:3000"]`. In production, origin should be the actual domain.
**Warning signs:** Browser console shows `CORS policy: No 'Access-Control-Allow-Origin' header`.

### Pitfall 6: OAuth2PasswordRequestForm Requires `python-multipart`
**What goes wrong:** `422 Unprocessable Entity` on POST to `/login` even with correct body.
**Why it happens:** OAuth2 login uses `application/x-www-form-urlencoded`, not JSON. FastAPI requires `python-multipart` to parse this.
**How to avoid:** Add `python-multipart` to dependencies. Note: `fastapi[standard]` includes it, but a bare `fastapi` install does not.
**Warning signs:** 422 error with message about `username` field missing even when you send it.

### Pitfall 7: Initiative Status Bypass
**What goes wrong:** User edits a submitted initiative via direct API call, bypassing the UI lock.
**Why it happens:** Status enforcement is only in the UI, not the API layer.
**How to avoid:** In the initiative UPDATE endpoint, check `if initiative.status == "submitted": raise 403`. The UI "locks" are a visual convenience only.
**Warning signs:** No status check in the API endpoint handler.

### Pitfall 8: Timing Attack on Login (Username Enumeration)
**What goes wrong:** Attacker can determine valid email addresses by measuring response time — hash check takes longer for existing users.
**Why it happens:** Code returns early if user is not found (fast), but runs bcrypt verify if user exists (slow).
**How to avoid:** Always run `bcrypt.checkpw()` even when user is not found, using a dummy hash. This is the pattern from official FastAPI docs.
**Warning signs:** Login returns immediately for non-existent users vs. ~200ms for existing users.

---

## Code Examples

### bcrypt Direct Usage (verified from PyPI)
```python
# Source: https://pypi.org/project/bcrypt/ — bcrypt 5.0.0
import bcrypt

def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
```

### PyJWT Token Creation (verified from FastAPI official docs)
```python
# Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
import jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = "..."  # from env: openssl rand -hex 32
ALGORITHM = "HS256"

def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> str | None:
    from jwt.exceptions import InvalidTokenError
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except InvalidTokenError:
        return None
```

### SlowAPI Login Rate Limiting
```python
# Source: https://github.com/laurentS/slowapi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

# In app setup:
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# On login endpoint:
@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    ...
```

### Alembic env.py Critical Configuration
```python
# Source: https://arunanshub.hashnode.dev/using-sqlmodel-with-alembic
import sqlmodel.sql.sqltypes  # MUST be imported
from sqlmodel import SQLModel
from app.models.user import User       # noqa
from app.models.initiative import Initiative  # noqa

target_metadata = SQLModel.metadata

# In run_migrations_online():
with connectable.connect() as connection:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        user_module_prefix="sqlmodel.sql.sqltypes.",
    )
```

### uv Dockerfile with Layer Caching
```dockerfile
# Source: https://docs.astral.sh/uv/guides/integration/docker/
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies (cached layer — separate from code)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy and install project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:3.12-slim
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app
CMD ["sh", "-c", "alembic upgrade head && python scripts/create_admin.py && fastapi run app/main.py --port 8000"]
```

### OpenAPI Configuration (FastAPI)
```python
# Source: https://fastapi.tiangolo.com/tutorial/metadata/
app = FastAPI(
    title="MAMI Checker API",
    description="API for the MAMI Framework DSI Assessment Tool — CoE-DSC / TNO",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "CoE-DSC",
        "url": "https://coe-dsc.nl",
    },
)
```

### coe-dsc.nl Brand Colors (CSS variables for React)
```css
/* Source: Extracted from https://coe-dsc.nl — verified Feb 2026 */
:root {
  --color-navy:       #020059;  /* Primary — deep navy blue */
  --color-green:      #41A765;  /* Secondary — accent green */
  --color-blue:       #3D52D5;  /* Accent — interactive elements */
  --color-text-gray:  #4A495B;  /* Body text */
  --color-bg-light:   #F5F5F8;  /* Light background (derived from B7B6C321) */
  --font-family:      'Rubik', sans-serif;
  --font-size-body:   16px;
  --line-height-body: 22px;
  --border-radius-sm: 6px;
  --border-radius-lg: 30px;  /* Cards */
}
```

### Password Complexity Recommendation (Claude's Discretion)
Based on NIST SP 800-63B (2025 update):
- **Minimum length: 12 characters** (NIST recommends 8 minimum; 12 is better practice for an assessment tool)
- **No mandatory character classes** (NIST 2025 drops mandatory uppercase/number/special requirements)
- **Blocklist common passwords** (check against a list of top 1000 or "Password1234" type patterns)
- **Implementation:** Simple regex for length check + a small common-password blocklist array

```python
# Recommended validation in UserCreate schema
from pydantic import field_validator

COMMON_PASSWORDS = {"password", "123456789", "qwerty123", "admin1234"}

@field_validator("password")
@classmethod
def validate_password(cls, v: str) -> str:
    if len(v) < 12:
        raise ValueError("Password must be at least 12 characters")
    if v.lower() in COMMON_PASSWORDS:
        raise ValueError("Password is too common")
    return v
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| passlib for password hashing | bcrypt direct OR pwdlib[argon2] | 2023-2024 | passlib unmaintained; bcrypt direct is valid; pwdlib is now the official recommendation |
| python-jose for JWT | PyJWT | 2024 | python-jose abandoned; FastAPI docs updated to PyJWT |
| requirements.txt | pyproject.toml + uv | 2024 | uv is now the FastAPI-recommended package manager |
| tiangolo/uvicorn-gunicorn-fastapi Docker image | `fastapi run` command directly | 2024 | Old base image deprecated by FastAPI author |
| SQLModel + Pydantic v1 | SQLModel + Pydantic v2 (required) | SQLModel 0.0.31 | Pydantic v1 support dropped in SQLModel 0.0.31 |

**Deprecated/outdated:**
- `python-jose`: Abandoned, do not use. Use `PyJWT`.
- `passlib`: Unmaintained since ~2020. Use `bcrypt` directly or `pwdlib`.
- `tiangolo/uvicorn-gunicorn-fastapi` Docker base image: Deprecated by FastAPI author. Use slim Python image + `fastapi run`.
- SQLModel with Pydantic v1: Not supported as of SQLModel 0.0.31.

---

## Open Questions

1. **JWT storage strategy in the React frontend**
   - What we know: localStorage has XSS risk; httpOnly cookies require backend to set `Set-Cookie` header and complicate CORS
   - What's unclear: Whether the MVP should use in-memory (loses on refresh) or sessionStorage (acceptable trade-off for MVP)
   - Recommendation: Use sessionStorage for MVP. Token is lost on tab close (acceptable for an assessment tool). Document httpOnly cookie upgrade path.

2. **Initiative sector predefined list**
   - What we know: There should be a predefined dropdown with an "Other" free-text option
   - What's unclear: The actual sector values are not defined in CONTEXT.md
   - Recommendation: Define a seed list in code (e.g., Healthcare, Finance, Government, Energy, Education, Transport, Other) and store as a constant. Can be made configurable later.

3. **Sidebar navigation items (Claude's Discretion)**
   - What we know: Dashboard-style layout, status should be prominent
   - Recommendation: For MVP: Dashboard (home overview after login), My Initiative (create/edit initiative), About (MAMI framework info), and admin-only: Users (user management)

4. **One initiative per user enforcement**
   - What we know: MVP allows one initiative per user
   - What's unclear: Should the POST /initiatives endpoint reject with 409 if user already has one, or should the UI hide the "create" button?
   - Recommendation: Enforce BOTH — API returns 409 Conflict if user already has an initiative, AND UI hides the create button if initiative exists.

5. **"Submitted" initiative editability**
   - What we know: All fields editable "until submitted"
   - What's unclear: Should there be a hard API-level block on editing submitted initiatives?
   - Recommendation: Yes, API returns 403 if status is "submitted". This is a hard business rule, not just a UI convenience.

---

## Sources

### Primary (HIGH confidence)
- https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ — JWT/bcrypt/pwdlib patterns, official Feb 2026
- https://fastapi.tiangolo.com/deployment/docker/ — Docker/uv Dockerfile, deprecation of old base image
- https://fastapi.tiangolo.com/tutorial/metadata/ — OpenAPI metadata configuration
- https://github.com/fastapi/sqlmodel/blob/main/pyproject.toml — SQLAlchemy `>=2.0.14,<2.1.0` pin confirmed
- https://pypi.org/project/bcrypt/ — bcrypt 5.0.0 API (hashpw, checkpw, gensalt)
- https://docs.astral.sh/uv/guides/integration/docker/ — uv multi-stage Dockerfile pattern
- https://coe-dsc.nl — Brand colors extracted directly from live site

### Secondary (MEDIUM confidence)
- https://github.com/laurentS/slowapi — SlowAPI rate limiting, decorator pattern
- https://tanstack.com/router/v1/docs — TanStack Router layout split pattern
- https://github.com/fastapi/full-stack-fastapi-template — Reference architecture for project structure
- https://arunanshub.hashnode.dev/using-sqlmodel-with-alembic — SQLModel + Alembic env.py configuration
- https://pages.nist.gov/800-63-4/sp800-63b.html — NIST password guidelines 2025

### Tertiary (LOW confidence — needs validation)
- Multiple Medium/blog posts on FastAPI + SQLModel project structures — consistent patterns but not official

---

## Metadata

**Confidence breakdown:**
- Standard stack versions: HIGH — confirmed from official pyproject.toml and PyPI
- JWT/auth pattern: HIGH — verified from official FastAPI docs
- SQLModel/Alembic pattern: HIGH — confirmed from official SQLModel repo and Alembic docs
- bcrypt vs pwdlib decision: MEDIUM — prior decision says bcrypt, but official docs now say pwdlib; both valid
- coe-dsc.nl colors: HIGH — extracted directly from live site Feb 2026
- Docker Compose pattern: MEDIUM — based on official template structure, not verbatim copy
- Frontend patterns: MEDIUM — TanStack Router docs verified, component structure is conventional

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (30 days — stable libraries; SQLModel version pin is the main risk)
