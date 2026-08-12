"""Entite `copies` — exemplaires physiques d'un livre, chacun avec son propre statut et QR Code."""

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
    """
    Genere un identifiant opaque unique pour le QR Code d'un exemplaire.
    Format : BK-XXXXXXXX (8 caracteres hexadecimaux), conforme a l'exemple
    du document "Consignes de Gestion du catalogue" (ex: BK-7F92A31C).
    """
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
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)  # cote / rayon

    # --- Ajout : identifiant QR unique, colle physiquement sur l'exemplaire ---
    qr_code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False, default=generate_qr_identifier
    )

    book: Mapped["Book"] = relationship(back_populates="copies")
    loans: Mapped[list["Loan"]] = relationship(back_populates="copy")

    def __repr__(self) -> str:
        return f"<Copy id={self.id} book_id={self.book_id} qr={self.qr_code} status={self.status.value}>"
