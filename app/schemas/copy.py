
"""Schemas Pydantic pour l'entite Copy (exemplaires physiques)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CopyStatus


class CopyBase(BaseModel):
    location: str | None = Field(default=None, max_length=100)
    call_number: str | None = Field(default=None, max_length=50)


class CopyCreate(CopyBase):
    """
    Payload de creation d'un exemplaire. Le qr_code est genere par le serveur.
    call_number est optionnel a la creation : si absent, le bibliothecaire peut
    le renseigner plus tard via une mise a jour (CopyUpdate), une fois la cote
    definie selon la convention de catalogage de l'etablissement.
    """
    book_id: int


class CopyUpdate(BaseModel):
    """Mise a jour de statut, localisation ou cote (bibliothecaire)."""
    status: CopyStatus | None = None
    location: str | None = Field(default=None, max_length=100)
    call_number: str | None = Field(default=None, max_length=50)


class CopyRead(CopyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    status: CopyStatus
    qr_code: str
    created_at: datetime


class CopyScanResult(BaseModel):
    """Resultat d'un scan de QR Code (GET /copies/scan/{qr_code})."""
    model_config = ConfigDict(from_attributes=True)

    copy_id: int
    qr_code: str
    status: CopyStatus
    location: str | None
    call_number: str | None
    book_id: int
    book_title: str
    book_author: str
