"""Backend test fixtures.

One fixture family lives here:
- `postgres_container` / `engine` / `session` / `client` / `admin_client` /
  `user_client` — real-Postgres-backed fixtures added for the auth/admin/reports
  characterization suite (test-retrofit milestone). Per that plan's D-01,
  tests run against a real Postgres via testcontainers-python, never SQLite —
  `admin.py` relies on raw SQL against Postgres-native features (native ENUM
  type, `pg_insert().on_conflict_do_update()`) that SQLite cannot faithfully
  reproduce. Requires a local Docker-API-compatible daemon (Docker Desktop /
  Colima / Podman) — see tests/README.md. No fallback exists; this is
  intentional.

(The former synthetic scoring-engine input fixtures were removed in Phase 14
Plan 04 alongside the ZEN engine they fed — SCOR-03.)
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from testcontainers.postgres import PostgresContainer

from app.core.security import create_access_token, hash_password


@pytest.fixture(scope="session")
def postgres_container():
    """One real Postgres container for the whole test session — matches
    docker-compose.yml's pinned postgres:16-alpine image."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def engine(postgres_container):
    """A SQLAlchemy engine built independently of the app's own `engine`
    (app/db/session.py binds to settings.DATABASE_URL at import time, which
    is NOT this container's URL) — schema is built exactly ONCE per session.

    Never repeat this schema-build step after this — Postgres native ENUM
    types (answervalue) raise "type already exists" on repeated
    drop/recreate against the same long-lived container."""
    url = postgres_container.get_connection_url().replace("postgresql+psycopg2", "postgresql")
    eng = create_engine(url)
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    """Function-scoped: each test runs inside its own connection + outer
    transaction, rolled back at teardown. Keeps tests isolated without ever
    recreating tables/ENUM types between tests."""
    connection = engine.connect()
    transaction = connection.begin()
    db_session = Session(bind=connection)
    yield db_session
    db_session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _disable_auth_rate_limiter():
    """Autouse: the auth router's slowapi Limiter is process-wide and
    IP-keyed (get_remote_address) — shared across every TestClient request
    in the whole pytest session. Without disabling it, a lockout test doing
    6 rapid login attempts followed by another test file's own logins within
    the same minute window produces an intermittent 429 that looks like test
    flakiness. Lockout tests must be able to assert 401/423 deterministically,
    never an incidental 429."""
    from app.api.v1 import auth

    auth.limiter.enabled = False
    yield
    auth.limiter.enabled = True


def _make_client(session):
    """Build one lifespan-aware TestClient bound to the rollback-scoped test
    session. Each call yields an independent client — used directly by the
    `client` fixture and again (separately) by `admin_client`/`user_client`
    so a single test can safely hold an anonymous client AND an
    authenticated one at the same time without mutating shared headers.

    MUST use `with TestClient(app) as c:` (context-manager form) — a bare
    `TestClient(app)` never fires app.main.py's lifespan(), so
    app.state.mami_config / app.state.zen_engine stay unset and
    admin.py::get_admin_heatmap and every reports.py endpoint raise
    AttributeError on first use."""
    from app.db.session import get_session
    from app.main import app

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client(session):
    yield from _make_client(session)


def _create_authed_user(session, *, role: str, participant_type: str = "DSI"):
    """Create a user with the given role directly in the DB (bypassing
    /register, which always creates role="USER") and return a bearer token
    for it."""
    import uuid

    from app.models.user import User

    email = f"{role.lower()}-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        hashed_password=hash_password("Str0ngPassw0rd!123"),
        role=role,
        participant_type=participant_type,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user, create_access_token(user.email)


@pytest.fixture
def admin_client(session):
    """A separate, independently authenticated TestClient (ADMIN role) — for
    admin endpoint happy-path tests and cascade-delete tests. Independent of
    `client` so a test can use both an anonymous and an admin client at once."""
    _, token = _create_authed_user(session, role="ADMIN")
    gen = _make_client(session)
    c = next(gen)
    c.headers.update({"Authorization": f"Bearer {token}"})
    yield c
    next(gen, None)  # drain generator to run teardown (dependency_overrides.clear())


@pytest.fixture
def user_client(session):
    """A separate, independently authenticated TestClient (plain USER role)
    — for negative access-control tests (assert 403 from admin endpoints)."""
    _, token = _create_authed_user(session, role="USER")
    gen = _make_client(session)
    c = next(gen)
    c.headers.update({"Authorization": f"Bearer {token}"})
    yield c
    next(gen, None)
