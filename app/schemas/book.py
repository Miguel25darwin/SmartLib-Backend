
"""Schemas Pydantic pour l'entite Book (catalogue)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BookType, LanguagePref


class BookBase(BaseModel):
    title_fr: str | None = Field(default=None, max_length=500)
    title_en: str | None = Field(default=None, max_length=500)
    author: str = Field(min_length=1, max_length=255)
    isbn: str | None = Field(default=None, max_length=20)
    publisher: str | None = Field(default=None, max_length=255)
    publication_year: int | None = Field(default=None, ge=1400, le=2100)
    synopsis: str | None = Field(default=None, max_length=2000)
    digital_url: str | None = Field(default=None, max_length=500)
    dewey_id: int | None = Field(default=None)
    type: BookType
    language: LanguagePref = LanguagePref.FR
    cover_url: str | None = Field(default=None, max_length=500)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title_fr: str | None = Field(default=None, max_length=500)
    title_en: str | None = Field(default=None, max_length=500)
    author: str | None = Field(default=None, max_length=255)
    isbn: str | None = Field(default=None, max_length=20)
    publisher: str | None = Field(default=None, max_length=255)
    publication_year: int | None = Field(default=None, ge=1400, le=2100)
    synopsis: str | None = Field(default=None, max_length=2000)
    digital_url: str | None = Field(default=None, max_length=500)
    dewey_id: int | None = Field(default=None)
    language: LanguagePref | None = None
    cover_url: str | None = Field(default=None, max_length=500)


class BookRead(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    copies_total: int = 0
    copies_available: int = 0
    dewey_code: str | None = None
    dewey_label_fr: str | None = None
    dewey_label_en: str | None = None
    dewey_label: str | None = None       # libelle unifie (label_fr par defaut) pour Flutter
    dewey_classification: str | None = None  # legacy : ancien texte libre
