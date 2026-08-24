"""Entite `books` — titres du catalogue (bilingue FR/EN), physiques ou numeriques."""

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import BookType, LanguagePref

if TYPE_CHECKING:
    from app.models.copy import Copy
    from app.models.dewey_classification import DeweyClassification
    from app.models.digital_resource import DigitalResource


class Book(Base, TimestampMixin):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    title_fr: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    isbn: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)

    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synopsis: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    digital_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    dewey_id: Mapped[int | None] = mapped_column(
        ForeignKey("dewey_classifications.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    dewey_classification: Mapped[str | None] = mapped_column(String(10), nullable=True)

    type: Mapped[BookType] = mapped_column(SAEnum(BookType, name="book_type"), nullable=False)
    language: Mapped[LanguagePref] = mapped_column(
        SAEnum(LanguagePref, name="book_language"), nullable=False, default=LanguagePref.FR
    )
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    copies: Mapped[list["Copy"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    digital_resources: Mapped[list["DigitalResource"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    dewey: Mapped["DeweyClassification | None"] = relationship(back_populates="books")

    def __repr__(self) -> str:
        return f"<Book {self.title_fr or self.title_en!r}>"