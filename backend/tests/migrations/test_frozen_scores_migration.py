"""Migration-verification tests for k2b3c4d5e6f7 (HIST-02, gap-closure plan
15-07) — the `dimension_scores` JSONB snapshot column on `assessment`.

Mirrors test_assessment_version_migration.py's isolated-per-test
PostgresContainer pattern (RESEARCH Pitfall 2) — each test gets its own
fresh Postgres via the `alembic_env` fixture, not the shared session-scoped
`postgres_container`/`engine` fixtures in tests/conftest.py, so the real
`alembic upgrade head` path (not `SQLModel.metadata.create_all()`) is what's
actually exercised.

Not marked `perf`/`benchmark` — belongs in the default fast gate.
"""

import os
from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from alembic.config import Config
from testcontainers.postgres import PostgresContainer

from alembic import command

# The revision this migration chains from (current head before k2b3c4d5e6f7).
PREVIOUS_HEAD = "j1a2b3c4d5e6"


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


def test_upgrade_head_from_empty_db_adds_dimension_scores_column(alembic_env):
    """Fresh empty DB: alembic upgrade head succeeds; `assessment` gains a
    nullable `dimension_scores` JSONB column."""
    config, engine = alembic_env

    command.upgrade(config, "head")

    inspector = sa.inspect(engine)
    columns = {c["name"]: c for c in inspector.get_columns("assessment")}
    assert "dimension_scores" in columns
    assert columns["dimension_scores"]["nullable"] is True


def test_upgrade_downgrade_upgrade_round_trip_succeeds(alembic_env):
    """Round-trip: upgrade -> downgrade -> upgrade succeeds without error;
    the column is absent after downgrade to the previous head, present
    again after re-upgrading to head."""
    config, engine = alembic_env
    command.upgrade(config, PREVIOUS_HEAD)

    inspector = sa.inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("assessment")}
    assert "dimension_scores" not in columns

    command.upgrade(config, "head")

    inspector = sa.inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("assessment")}
    assert "dimension_scores" in columns

    command.downgrade(config, PREVIOUS_HEAD)

    inspector = sa.inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("assessment")}
    assert "dimension_scores" not in columns

    command.upgrade(config, "head")

    inspector = sa.inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("assessment")}
    assert "dimension_scores" in columns
