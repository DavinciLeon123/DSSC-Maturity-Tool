"""Make initiative contact fields nullable

Revision ID: h8c6d5e4f3a2
Revises: g7b5c4d3e2f1
Create Date: 2026-03-09

Changes:
- Alter initiative.contact_name to allow NULL
- Alter initiative.contact_email to allow NULL
- Alter initiative.organization to allow NULL

Reason: Dashboard inline registration form only collects name + sector.
The three contact fields are now optional to support that flow.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h8c6d5e4f3a2'
down_revision = 'g7b5c4d3e2f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('initiative', 'contact_name', nullable=True)
    op.alter_column('initiative', 'contact_email', nullable=True)
    op.alter_column('initiative', 'organization', nullable=True)


def downgrade() -> None:
    # Set any NULLs to empty string before making NOT NULL again
    op.execute("UPDATE initiative SET contact_name = '' WHERE contact_name IS NULL")
    op.execute("UPDATE initiative SET contact_email = '' WHERE contact_email IS NULL")
    op.execute("UPDATE initiative SET organization = '' WHERE organization IS NULL")
    op.alter_column('initiative', 'contact_name', nullable=False)
    op.alter_column('initiative', 'contact_email', nullable=False)
    op.alter_column('initiative', 'organization', nullable=False)
