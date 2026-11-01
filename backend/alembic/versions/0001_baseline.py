"""Baseline schema (all tables as of the rPPG release).

Built from the SQLAlchemy models themselves (Base.metadata) so that the
same migration yields JSONB columns + native ENUM types on PostgreSQL and
portable JSON/VARCHAR on SQLite. Later schema changes should be added as
normal `alembic revision --autogenerate -m "..."` migrations on top of this.

Revision ID: 0001_baseline
Revises:
"""
from alembic import op

from app.core.database import Base
from app.models import document, kyc_case, results, user  # noqa: F401

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
