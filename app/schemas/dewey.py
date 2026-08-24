"""Schemas Pydantic pour le referentiel Dewey."""

from pydantic import BaseModel, ConfigDict, Field


class DeweyClassificationBase(BaseModel):
    code: str = Field(min_length=1, max_length=10)
    label_fr: str = Field(min_length=1, max_length=255)
    label_en: str = Field(min_length=1, max_length=255)
    parent_id: int | None = None


class DeweyClassificationCreate(DeweyClassificationBase):
    pass


class DeweyClassificationRead(DeweyClassificationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: int
    is_active: bool


class DeweyClassificationTree(DeweyClassificationRead):
    """Version avec enfants imbriques, pour un affichage hierarchique cote Flutter."""
    children: list["DeweyClassificationTree"] = []


DeweyClassificationTree.model_rebuild()
