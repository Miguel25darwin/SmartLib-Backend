
"""
Entite `dewey_classifications` — referentiel hierarchique et bilingue du
Systeme Decimal de Melvil Dewey (MDS).

IMPORTANT (contrainte legale) : "Dewey Decimal Classification" et "DDC" sont
des marques deposees d'OCLC, et les editions recentes du referentiel complet
sont protegees par droit d'auteur. Cette table ne contient QUE les donnees
fournies par l'etablissement lui-meme (les 10 classes principales transmises
via le document "Consignes de Gestion du catalogue"), jamais une reproduction
du referentiel proprietaire complet d'OCLC. Toute sous-classe additionnelle
doit etre formulee par l'etablissement dans ses propres termes, jamais copiee
d'un referentiel sous licence.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.book import Book


class DeweyClassification(Base, TimestampMixin):
    __tablename__ = "dewey_classifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    label_fr: Mapped[str] = mapped_column(String(255), nullable=False)
    label_en: Mapped[str] = mapped_column(String(255), nullable=False)

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("dewey_classifications.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    # ON DELETE RESTRICT : on refuse de supprimer une categorie parente tant
    # que des sous-categories en dependent, pour ne jamais casser la hierarchie
    # silencieusement (mieux vaut un 409 explicite qu'une suppression en cascade
    # qui efface accidentellement toute une branche du referentiel).

    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 0 = classe principale (ex: "500"), 1 = division (ex: "510"), 2 = section (ex: "512")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Permet de retirer une categorie de l'usage courant sans casser les livres
    # qui y sont deja rattaches (soft-disable plutot que suppression).

    parent: Mapped["DeweyClassification | None"] = relationship(
        remote_side=[id], back_populates="children"
    )
    children: Mapped[list["DeweyClassification"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    books: Mapped[list["Book"]] = relationship(back_populates="dewey")

    def __repr__(self) -> str:
        return f"<DeweyClassification {self.code} - {self.label_fr}>"
