"""add book_recommendations table

Revision ID: 9b1f2c3d4e5f
Revises: 4d1e8c9a7b62
Create Date: 2026-10-28 00:00:00.000000

Table partagee des ouvrages recommandes par les enseignants/personnel pour
leurs cours. Les gestionnaires de la bibliotheque s'appuient dessus pour
verifier la couverture du fonds (exemplaires disponibles vs manquants).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9b1f2c3d4e5f"
down_revision: Union[str, None] = "4d1e8c9a7b62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "book_recommendations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_code", sa.String(length=20), nullable=False),
        sa.Column("course_title", sa.String(length=200), nullable=False),
        sa.Column("lecturer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("required_quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lecturer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "course_code",
            "book_id",
            "lecturer_id",
            name="uq_recommendation_course_book_lecturer",
        ),
    )
    op.create_index(
        "ix_book_recommendations_course_code",
        "book_recommendations",
        ["course_code"],
    )
    op.create_index(
        "ix_book_recommendations_lecturer_id",
        "book_recommendations",
        ["lecturer_id"],
    )
    op.create_index(
        "ix_book_recommendations_book_id",
        "book_recommendations",
        ["book_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_book_recommendations_book_id", table_name="book_recommendations")
    op.drop_index("ix_book_recommendations_lecturer_id", table_name="book_recommendations")
    op.drop_index("ix_book_recommendations_course_code", table_name="book_recommendations")
    op.drop_table("book_recommendations")
