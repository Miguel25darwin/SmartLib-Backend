"""Schemas Pydantic pour l'entite Book (catalogue)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import BookType, LanguagePref


class BookBase(BaseModel):
    title_fr: str | None = Field(default=None, max_length=500)
    title_en: str | None = Field(default=None, max_length=500)
    author: str = Field(min_length=1, max_length=255)
    isbn: str | None = Field(default=None, max_length=20)
    publisher: str | None = Field(default=None, max_length=255)
    publication_year: int | None = Field(default=None, ge=1400, le=2100)
    dewey_classification: str | None = Field(default=None, max_length=10)
    type: BookType
    language: LanguagePref = LanguagePref.FR
    cover_url: str | None = Field(default=None, max_length=500)

    @field_validator("dewey_classification")
    @classmethod
    def validate_dewey(cls, v: str | None) -> str | None:
        """Verifie que la classification suit le format Dewey (ex: 005, 005.8, 621.39)."""
        if v is None:
            return v
        stripped = v.strip()
        prefix = stripped.split(".")[0]
        if not prefix.isdigit() or not (0 <= int(prefix) <= 999):
            raise ValueError(
                "Classification Dewey invalide : doit commencer par un code entre 000 et 999 "
                "(ex: '005.8' pour securite informatique)."
            )
        return stripped


class BookCreate(BookBase):
    """Payload de creation (POST /books, reserve bibliothecaire/admin)."""
    pass


class BookUpdate(BaseModel):
    """Payload de mise a jour partielle (PUT /books/{id})."""
    title_fr: str | None = Field(default=None, max_length=500)
    title_en: str | None = Field(default=None, max_length=500)
    author: str | None = Field(default=None, max_length=255)
    isbn: str | None = Field(default=None, max_length=20)
    publisher: str | None = Field(default=None, max_length=255)
    publication_year: int | None = Field(default=None, ge=1400, le=2100)
    dewey_classification: str | None = Field(default=None, max_length=10)
    language: LanguagePref | None = None
    cover_url: str | None = Field(default=None, max_length=500)


class BookRead(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    copies_total: int = 0
    copies_available: int = 0
