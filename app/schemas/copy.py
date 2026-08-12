"""Schemas Pydantic pour l'entite Copy (exemplaires physiques)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CopyStatus


class CopyBase(BaseModel):
    location: str | None = Field(default=None, max_length=100)


class CopyCreate(CopyBase):
    """Payload de creation d'un exemplaire pour un livre donne. Le qr_code est genere par le serveur."""
    book_id: int


class CopyUpdate(BaseModel):
    """Mise a jour de statut ou de localisation (bibliothecaire)."""
    status: CopyStatus | None = None
    location: str | None = Field(default=None, max_length=100)


class CopyRead(CopyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    status: CopyStatus
    qr_code: str
    created_at: datetime


class CopyScanResult(BaseModel):
    """
    Resultat d'un scan de QR Code (GET /copies/scan/{qr_code}).
    Contient les infos utiles affichees a l'ecran du bibliothecaire/etudiant
    juste apres le scan : identite de l'exemplaire + titre + statut.
    """
    model_config = ConfigDict(from_attributes=True)

    copy_id: int
    qr_code: str
    status: CopyStatus
    location: str | None
    book_id: int
    book_title: str
    book_author: str
