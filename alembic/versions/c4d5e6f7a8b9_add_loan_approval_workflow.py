"""add loan approval workflow (pending/rejected + decision fields)

Revision ID: c4d5e6f7a8b9
Revises: 9b1f2c3d4e5f
Create Date: 2026-10-28 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "9b1f2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nouvelles valeurs du statut d'emprunt. PostgreSQL 12+ autorise
    # ALTER TYPE ... ADD VALUE dans une transaction.
    op.execute("ALTER TYPE loan_status ADD VALUE IF NOT EXISTS 'PENDING'")
    op.execute("ALTER TYPE loan_status ADD VALUE IF NOT EXISTS 'REJECTED'")

    op.add_column(
        "loans", sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "loans", sa.Column("decision_note", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("loans", "decision_note")
    op.drop_column("loans", "decided_at")
    # PostgreSQL ne permet pas de retirer une valeur d'un type ENUM sans
    # recreer le type : les valeurs 'pending'/'rejected' sont conservees.
