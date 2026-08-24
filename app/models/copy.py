"""Entite `copies` — exemplaires physiques d'un livre, chacun avec son propre statut, cote et QR Code."""

import secrets
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import CopyStatus

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.loan import Loan


def generate_qr_identifier() -> str:
    """Genere un identifiant opaque unique pour le QR Code d'un exemplaire (ex: BK-7F92A31C)."""
    return f"BK-{secrets.token_hex(4).upper()}"


class Copy(Base, TimestampMixin):
    __tablename__ = "copies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[CopyStatus] = mapped_column(
        SAEnum(CopyStatus, name="copy_status"), nullable=False, default=CopyStatus.AVAILABLE
    )

    # --- Trois concepts distincts, jamais a confondre ---
    # location    : ou se trouve physiquement l'exemplaire dans les rayons (ex: "R02-A15")
    # call_number : la cote de rangement, construite generalement a partir du code Dewey
    #               + un code auteur + l'annee (ex: "512 DUP 2024"). C'est la convention
    #               de catalogage qui permet de retrouver un ouvrage dans l'ordre du rayon.
    # qr_code     : identifiant technique opaque unique, colle physiquement sur l'exemplaire,
    #               utilise pour le scan (n'a aucune signification bibliographique).
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    call_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    qr_code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False, default=generate_qr_identifier
    )

    book: Mapped["Book"] = relationship(back_populates="copies")
    loans: Mapped[list["Loan"]] = relationship(back_populates="copy")

    def __repr__(self) -> str:
        return f"<Copy id={self.id} book_id={self.book_id} call_number={self.call_number} qr={self.qr_code}>"