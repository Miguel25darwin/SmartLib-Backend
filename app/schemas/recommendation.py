"""Schemas Pydantic du module Recommandations d'ouvrages."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecommendationCreate(BaseModel):
    course_code: str = Field(min_length=1, max_length=20)
    course_title: str = Field(min_length=1, max_length=200)
    book_id: int = Field(gt=0)
    required_quantity: int = Field(default=1, ge=1, le=999)

    @field_validator("course_code")
    @classmethod
    def normalize_course_code(cls, value: str) -> str:
        normalized = " ".join(value.strip().upper().split())
        if not normalized:
            raise ValueError("Le code du cours est obligatoire.")
        return normalized

    @field_validator("course_title")
    @classmethod
    def normalize_course_title(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("L'intitule du cours est obligatoire.")
        return normalized


class RecommendationUpdate(BaseModel):
    course_code: str | None = Field(default=None, min_length=1, max_length=20)
    course_title: str | None = Field(default=None, min_length=1, max_length=200)
    book_id: int | None = Field(default=None, gt=0)
    required_quantity: int | None = Field(default=None, ge=1, le=999)

    @field_validator("course_code")
    @classmethod
    def normalize_course_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().upper().split())
        if not normalized:
            raise ValueError("Le code du cours est obligatoire.")
        return normalized

    @field_validator("course_title")
    @classmethod
    def normalize_course_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("L'intitule du cours est obligatoire.")
        return normalized


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_code: str
    course_title: str
    lecturer_id: uuid.UUID
    lecturer_name: str
    book_id: int
    book_title: str
    book_author: str
    book_type: str
    required_quantity: int
    available_copies: int
    total_copies: int
    missing_copies: int
    is_sufficient: bool
    is_owner: bool
    can_delete: bool
    created_at: datetime
