"""add call_number to copies, partial unique index one active loan per copy

Revision ID: a6cb34e62c3e
Revises: b03ff011b21a
Create Date: 2026-08-24 15:52:09.915577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6cb34e62c3e'
down_revision: Union[str, None] = 'b03ff011b21a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Cote (call_number) sur les exemplaires physiques
    op.add_column('copies', sa.Column('call_number', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_copies_call_number'), 'copies', ['call_number'], unique=False)

    # 2. Index unique PARTIEL PostgreSQL : 1 Copy => 0..1 emprunt ACTIF
    # Cet index garantit qu'il est impossible d'inserer deux lignes dans `loans`
    # avec le meme copy_id et status='ACTIVE', meme en cas de requetes concurrentes
    # (les transactions concurrentes verront l'index avant le commit). C'est la
    # seule protection fiable contre la double-reservation sous charge.
    op.execute("""
        CREATE UNIQUE INDEX ix_loans_one_active_per_copy
        ON loans (copy_id)
        WHERE copy_id IS NOT NULL AND status = 'ACTIVE'::loan_status
    """)


def downgrade() -> None:
    # 1. Suppression de l'index partiel anti-doublon
    op.execute('DROP INDEX IF EXISTS ix_loans_one_active_per_copy')

    # 2. Suppression de la cote
    op.drop_index(op.f('ix_copies_call_number'), table_name='copies')
    op.drop_column('copies', 'call_number')