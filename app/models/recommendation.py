"""Entite `book_recommendations` — ouvrages recommandes par les enseignants.

Chaque membre du personnel (enseignant, personnel, bibliothecaire, admin)
peut recommander un ouvrage du catalogue pour un cours. Les gestionnaires de
la bibliotheque consultent ces recommandations pour verifier la couverture
du fonds documentaire (exemplaires disponibles vs manquants).
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class BookRecommendation(Base, TimestampMixin):
    __tablename__ = "book_recommendations"
    __table_args__ = (
        UniqueConstraint(
            "course_code",
            "book_id",
            "lecturer_id",
            name="uq_recommendation_course_book_lecturer",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    course_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    course_title: Mapped[str] = mapped_column(String(200), nullable=False)

    # Auteur de la recommandation (enseignant / personnel / bibliothecaire / admin).
    lecturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    lecturer: Mapped["User"] = relationship()
    book: Mapped["Book"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<BookRecommendation course={self.course_code} "
            f"book_id={self.book_id} qty={self.required_quantity}>"
        )
