"""add_initiatives_table

Revision ID: c3f2a891e5b7
Revises: 9a6864dd3f14
Create Date: 2026-02-15 09:22:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
import sqlmodel.sql.sqltypes

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f2a891e5b7"
down_revision: str | None = "9a6864dd3f14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "initiative",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("sector", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("sector_other", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("contact_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("contact_email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("organization", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_initiative_user_id"), "initiative", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_initiative_user_id"), table_name="initiative")
    op.drop_table("initiative")
