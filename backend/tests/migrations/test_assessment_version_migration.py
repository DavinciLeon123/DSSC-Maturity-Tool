"""Migration-verification tests for j1a2b3c4d5e6 (D-08, D-15/HIST-01,
Pitfall 4) — the version-uniqueness constraint + last_viewed_category_id
column on `assessment`.

Mirrors test_v1_archive_migration.py's isolated-per-test PostgresContainer
pattern (RESEARCH Pitfall 2) — each test gets its own fresh Postgres via the
`alembic_env` fixture, not the shared session-scoped `postgres_container`/
`engine` fixtures in tests/conftest.py, so the real `alembic upgrade head`
path (not `SQLModel.metadata.create_all()`) is what's actually exercised.

Not marked `perf`/`benchmark` — belongs in the default fast gate.
"""

import os
from collections.abc import Iterator
from datetime import datetime

import pytest
import sqlalchemy as sa
from alembic.config import Config
from testcontainers.postgres import PostgresContainer

from alembic import command

# The revision this migration chains from (current head before j1a2b3c4d5e6).
PREVIOUS_HEAD = "i9d7e6f5a4b3"


@pytest.fixture
def alembic_env() -> Iterator[tuple[Config, sa.engine.Engine]]:
    """A fresh Postgres testcontainer + Alembic Config, isolated per test.

    `alembic/env.py` reads `DATABASE_URL` from the process environment at
    run time, so pointing Alembic at this container is done by setting that
    env var before invoking any `alembic.command.*` call, restored
    afterwards.
    """
    with PostgresContainer("postgres:16-alpine") as postgres:
        url = postgres.get_connection_url().replace("postgresql+psycopg2", "postgresql")
        previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = url
        config = Config("alembic.ini")
        engine = sa.create_engine(url)
        try:
            yield config, engine
        finally:
            engine.dispose()
            if previous_database_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_database_url


def _seed_initiative(engine: sa.engine.Engine) -> int:
    """Seed one user + one initiative via raw SQL against the schema as it
    exists at PREVIOUS_HEAD (the assessment table already exists there, just
    without the new column/constraint)."""
    now = datetime.utcnow()
    with engine.begin() as conn:
        user_id = conn.execute(
            sa.text(
                """
                INSERT INTO "user" (email, hashed_password, role, participant_type,
                                      failed_login_attempts, created_at)
                VALUES ('seed-j1a2b3c4d5e6@example.com', 'hashed', 'USER', 'DSI', 0, :now)
                RETURNING id
                """
            ),
            {"now": now},
        ).scalar_one()
        initiative_id = conn.execute(
            sa.text(
                """
                INSERT INTO initiative (user_id, name, sector, participant_type,
                                          status, created_at, updated_at)
                VALUES (:user_id, 'Seed Initiative', 'Healthcare', 'DSI',
                        'draft', :now, :now)
                RETURNING id
                """
            ),
            {"user_id": user_id, "now": now},
        ).scalar_one()
    return initiative_id


def test_upgrade_head_from_empty_db_creates_column_and_constraint(alembic_env):
    """Fresh empty DB: alembic upgrade head succeeds; `assessment` gains
    last_viewed_category_id (nullable) and the (initiative_id, version)
    unique constraint."""
    config, engine = alembic_env

    command.upgrade(config, "head")

    inspector = sa.inspect(engine)
    columns = {c["name"]: c for c in inspector.get_columns("assessment")}
    assert "last_viewed_category_id" in columns
    assert columns["last_viewed_category_id"]["nullable"] is True

    constraint_names = {uc["name"] for uc in inspector.get_unique_constraints("assessment")}
    assert "uq_assessment_version_per_initiative" in constraint_names


def test_duplicate_initiative_version_pair_raises_integrity_error(alembic_env):
    """The new unique constraint rejects a second assessment row sharing the
    same (initiative_id, version) — this is what makes
    _get_or_create_draft_assessment's IntegrityError-catch-and-requery
    meaningful once version is actually computed (D-15/Pitfall 4)."""
    config, engine = alembic_env
    command.upgrade(config, "head")
    initiative_id = _seed_initiative(engine)

    now = datetime.utcnow()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                INSERT INTO assessment (initiative_id, version, status, created_at)
                VALUES (:initiative_id, 1, 'submitted', :now)
                """
            ),
            {"initiative_id": initiative_id, "now": now},
        )

    with (
        engine.begin() as conn,
        pytest.raises(sa.exc.IntegrityError),
    ):
        conn.execute(
            sa.text(
                """
                INSERT INTO assessment (initiative_id, version, status, created_at)
                VALUES (:initiative_id, 1, 'draft', :now)
                """
            ),
            {"initiative_id": initiative_id, "now": now},
        )

    # A second row with a DIFFERENT version for the same initiative is fine.
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                INSERT INTO assessment (initiative_id, version, status, created_at)
                VALUES (:initiative_id, 2, 'draft', :now)
                """
            ),
            {"initiative_id": initiative_id, "now": now},
        )
        count = conn.execute(
            sa.text("SELECT count(*) FROM assessment WHERE initiative_id = :id"),
            {"id": initiative_id},
        ).scalar_one()
        assert count == 2


def test_upgrade_downgrade_upgrade_round_trip_succeeds(alembic_env):
    """Round-trip: upgrade -> downgrade -> upgrade succeeds without error,
    including against a DB carrying a seeded assessment row."""
    config, engine = alembic_env
    command.upgrade(config, PREVIOUS_HEAD)
    initiative_id = _seed_initiative(engine)
    now = datetime.utcnow()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                INSERT INTO assessment (initiative_id, version, status, created_at)
                VALUES (:initiative_id, 1, 'draft', :now)
                """
            ),
            {"initiative_id": initiative_id, "now": now},
        )

    command.upgrade(config, "head")
    command.downgrade(config, PREVIOUS_HEAD)
    command.upgrade(config, "head")

    inspector = sa.inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("assessment")}
    assert "last_viewed_category_id" in columns
    constraint_names = {uc["name"] for uc in inspector.get_unique_constraints("assessment")}
    assert "uq_assessment_version_per_initiative" in constraint_names

    with engine.begin() as conn:
        count = conn.execute(
            sa.text("SELECT count(*) FROM assessment WHERE initiative_id = :id"),
            {"id": initiative_id},
        ).scalar_one()
        assert count == 1
