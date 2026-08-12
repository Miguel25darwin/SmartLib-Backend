
"""Entité `digital_resources` — fichiers numériques (pdf, epub, audio, video) liés à un livre."""

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import DigitalFormat

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.loan import Loan


class DigitalResource(Base, TimestampMixin):
    __tablename__ = "digital_resources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )

    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    format: Mapped[DigitalFormat] = mapped_column(
        SAEnum(DigitalFormat, name="digital_format"), nullable=False
    )

    book: Mapped["Book"] = relationship(back_populates="digital_resources")
    loans: Mapped[list["Loan"]] = relationship(back_populates="digital_resource")

    def __repr__(self) -> str:
        return f"<DigitalResource id={self.id} format={self.format.value}>"
