"""Migration-verification tests for i9d7e6f5a4b3 (MIGR-01) — the first
tests in this repo that exercise the real `alembic upgrade head` path
rather than `SQLModel.metadata.create_all()` (RESEARCH Pitfall 2).

Each test gets its OWN fresh, isolated Postgres testcontainer via the
`alembic_env` fixture below — deliberately NOT the shared session-scoped
`postgres_container`/`engine` fixtures in tests/conftest.py, which already
ran `create_all()` and are not a clean slate for verifying an actual
Alembic upgrade path.

Not marked `perf`/`benchmark` — this belongs in the default fast gate
(`pytest -n auto -m "not perf and not benchmark"`) so every PR runs it.
"""

import os
from collections.abc import Iterator
from datetime import datetime

import pytest
import sqlalchemy as sa
from alembic.config import Config
from testcontainers.postgres import PostgresContainer

from alembic import command

# The revision this migration chains from (current head before i9d7e6f5a4b3).
PREVIOUS_HEAD = "h8c6d5e4f3a2"


@pytest.fixture
def alembic_env() -> Iterator[tuple[Config, sa.engine.Engine]]:
    """A fresh Postgres testcontainer + Alembic Config, isolated per test.

    `alembic/env.py` reads `DATABASE_URL` from the process environment at
    run time (`config.set_main_option("sqlalchemy.url",
    os.environ.get("DATABASE_URL", ""))`), so pointing Alembic at this
    container is done by setting that env var before invoking any
    `alembic.command.*` call, restored afterwards.
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


def _seed_v1_shaped_data(engine: sa.engine.Engine) -> dict:
    """Seed pre-migration-shaped rows via raw SQL, matching the OLD schema
    as it existed at `PREVIOUS_HEAD` (the reshaped SQLModel model can no
    longer express this shape, per the plan's key_links note).

    3 initiatives: 2 WITH answers (5 answer rows total, N=5 across M=2),
    1 WITHOUT any answers — the MIGR-01 zero-answers edge, which must stay
    tagged 'v2' rather than 'v1_legacy' after upgrade.
    """
    now = datetime.utcnow()
    with engine.begin() as conn:
        user_ids = []
        for i in range(3):
            result = conn.execute(
                sa.text(
                    """
                    INSERT INTO "user" (email, hashed_password, role, participant_type,
                                          failed_login_attempts, created_at)
                    VALUES (:email, 'hashed', 'USER', 'DSI', 0, :now)
                    RETURNING id
                    """
                ),
                {"email": f"seed-user-{i}@example.com", "now": now},
            )
            user_ids.append(result.scalar_one())

        initiative_ids = []
        for i, user_id in enumerate(user_ids):
            result = conn.execute(
                sa.text(
                    """
                    INSERT INTO initiative (user_id, name, sector, participant_type,
                                              status, created_at, updated_at)
                    VALUES (:user_id, :name, 'Healthcare', 'DSI', 'draft', :now, :now)
                    RETURNING id
                    """
                ),
                {"user_id": user_id, "name": f"Seed Initiative {i}", "now": now},
            )
            initiative_ids.append(result.scalar_one())

        answered_initiative_ids = initiative_ids[:2]
        answerless_initiative_id = initiative_ids[2]

        seeded_answers = []
        answer_values = ["YES", "NOT_THERE_YET", "NOT_APPLICABLE"]
        row_index = 0
        # initiative 0 gets 2 answers, initiative 1 gets 3 answers -> N=5 total
        for initiative_id, answer_count in zip(answered_initiative_ids, (2, 3), strict=True):
            for q in range(answer_count):
                answer_value = answer_values[row_index % len(answer_values)]
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO questionnaire_answer
                            (initiative_id, question_id, mami_code, questionnaire_version,
                             answer_value, answered_at, updated_at)
                        VALUES (:initiative_id, :question_id, :mami_code, '2.0',
                                :answer_value, :now, :now)
                        """
                    ),
                    {
                        "initiative_id": initiative_id,
                        "question_id": f"q-{initiative_id}-{q}",
                        "mami_code": f"M-{row_index}",
                        "answer_value": answer_value,
                        "now": now,
                    },
                )
                seeded_answers.append(
                    {"initiative_id": initiative_id, "answer_value": answer_value}
                )
                row_index += 1

    return {
        "seeded_answers": seeded_answers,
        "answered_initiative_ids": answered_initiative_ids,
        "answerless_initiative_id": answerless_initiative_id,
    }


def test_upgrade_head_from_empty_db_creates_new_tables(alembic_env):
    """Fresh empty DB: alembic upgrade head succeeds and all new tables
    exist with the new answer shape (no mami_code/initiative_id)."""
    config, engine = alembic_env

    command.upgrade(config, "head")

    inspector = sa.inspect(engine)
    tables = set(inspector.get_table_names())
    assert "assessment" in tables
    assert "questionnaire_answer_v1_archive" in tables
    assert "questionnaire_answer" in tables

    answer_columns = {c["name"] for c in inspector.get_columns("questionnaire_answer")}
    assert {"assessment_id", "category_id", "score"} <= answer_columns
    assert "mami_code" not in answer_columns
    assert "initiative_id" not in answer_columns

    archive_columns = {c["name"] for c in inspector.get_columns("questionnaire_answer_v1_archive")}
    assert {"initiative_id", "mami_code", "answer_value"} <= archive_columns


def test_upgrade_preserves_seeded_v1_answers_and_tags_legacy_initiatives(alembic_env):
    """Seeded DB: upgrade copies every pre-migration row into the archive
    verbatim (same count/content/initiative_id linkage) and tags only
    initiatives that had answers as 'v1_legacy' — the answerless initiative
    stays 'v2' (MIGR-01 zero-answers edge, not silently dropped)."""
    config, engine = alembic_env
    command.upgrade(config, PREVIOUS_HEAD)
    seeded = _seed_v1_shaped_data(engine)

    command.upgrade(config, "head")

    with engine.begin() as conn:
        archive_rows = conn.execute(
            sa.text(
                "SELECT initiative_id, answer_value FROM questionnaire_answer_v1_archive "
                "ORDER BY id"
            )
        ).all()
        assert len(archive_rows) == len(seeded["seeded_answers"])
        for archived, expected in zip(archive_rows, seeded["seeded_answers"], strict=True):
            assert archived.initiative_id == expected["initiative_id"]
            assert archived.answer_value == expected["answer_value"]

        for initiative_id in seeded["answered_initiative_ids"]:
            schema_version = conn.execute(
                sa.text("SELECT schema_version FROM initiative WHERE id = :id"),
                {"id": initiative_id},
            ).scalar_one()
            assert schema_version == "v1_legacy"

        answerless_schema_version = conn.execute(
            sa.text("SELECT schema_version FROM initiative WHERE id = :id"),
            {"id": seeded["answerless_initiative_id"]},
        ).scalar_one()
        assert answerless_schema_version == "v2"

        # The live (reshaped) questionnaire_answer table starts empty — only
        # the archive is populated from pre-migration rows.
        live_answer_count = conn.execute(
            sa.text("SELECT count(*) FROM questionnaire_answer")
        ).scalar_one()
        assert live_answer_count == 0

        # Defense-in-depth CHECK constraint exists on the new shape.
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(
                sa.text(
                    """
                    INSERT INTO assessment (initiative_id, version, status, created_at)
                    VALUES (:initiative_id, 1, 'draft', :now)
                    """
                ),
                {"initiative_id": seeded["answerless_initiative_id"], "now": datetime.utcnow()},
            )
            conn.execute(
                sa.text(
                    """
                    INSERT INTO questionnaire_answer
                        (assessment_id, question_id, category_id, score, answered_at, updated_at)
                    VALUES (
                        (SELECT id FROM assessment ORDER BY id DESC LIMIT 1),
                        'q-out-of-range', 'cat-1', 99, :now, :now
                    )
                    """
                ),
                {"now": datetime.utcnow()},
            )


def test_upgrade_downgrade_upgrade_round_trip_succeeds(alembic_env):
    """Round-trip: upgrade -> downgrade -> upgrade succeeds without error
    against a DB carrying seeded pre-migration data."""
    config, engine = alembic_env
    command.upgrade(config, PREVIOUS_HEAD)
    _seed_v1_shaped_data(engine)

    command.upgrade(config, "head")
    command.downgrade(config, PREVIOUS_HEAD)
    command.upgrade(config, "head")

    inspector = sa.inspect(engine)
    tables = set(inspector.get_table_names())
    assert "assessment" in tables
    assert "questionnaire_answer_v1_archive" in tables
    assert "questionnaire_answer" in tables

    with engine.begin() as conn:
        # The seeded rows survived the full round-trip (restored to the old
        # shape on downgrade, then re-archived on the second upgrade).
        archive_count = conn.execute(
            sa.text("SELECT count(*) FROM questionnaire_answer_v1_archive")
        ).scalar_one()
        assert archive_count == 5
