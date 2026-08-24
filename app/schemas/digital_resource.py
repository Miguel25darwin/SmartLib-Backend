"""Schémas Pydantic pour l'entité DigitalResource (ressources numériques)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DigitalFormat


class DigitalResourceBase(BaseModel):
    file_url: str = Field(min_length=1, max_length=500)
    format: DigitalFormat


class DigitalResourceCreate(DigitalResourceBase):
    book_id: int


class DigitalResourceUpdate(BaseModel):
    file_url: str | None = Field(default=None, min_length=1, max_length=500)
    format: DigitalFormat | None = None


class DigitalResourceRead(DigitalResourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    created_at: datetime