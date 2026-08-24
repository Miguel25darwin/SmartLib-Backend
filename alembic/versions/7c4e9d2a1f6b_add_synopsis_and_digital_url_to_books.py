"""add synopsis and digital_url to books

Revision ID: 7c4e9d2a1f6b
Revises: a6cb34e62c3e
Create Date: 2026-08-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c4e9d2a1f6b"
down_revision: Union[str, None] = "a6cb34e62c3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("books", sa.Column("synopsis", sa.String(length=2000), nullable=True))
    op.add_column("books", sa.Column("digital_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("books", "digital_url")
    op.drop_column("books", "synopsis")
