"""drop legacy dewey_classification text column from books

Revision ID: 4d1e8c9a7b62
Revises: 7c4e9d2a1f6b
Create Date: 2026-10-18 00:00:00.000000

La classification Dewey est desormais portee par la seule FK `books.dewey_id`
-> `dewey_classifications.id` (voir migration b03ff011b21a). L'ancienne colonne
texte libre `dewey_classification` n'est plus lue ni ecrite par l'application :
la conserver entretenait une source de divergence (un livre renseigne cote
legacy mais non lie a `dewey_id` apparaissait comme non classe).

Les donnees existantes ont ete alignees au prealable via
`python scripts/classify_books.py` (association par ISBN au referentiel).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d1e8c9a7b62"
down_revision: Union[str, None] = "7c4e9d2a1f6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tout index attache a la colonne est supprime automatiquement avec elle.
    op.drop_column("books", "dewey_classification")


def downgrade() -> None:
    op.add_column(
        "books",
        sa.Column("dewey_classification", sa.String(length=10), nullable=True),
    )
