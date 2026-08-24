"""Schémas Pydantic pour l'entité Loan (emprunts)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import LoanStatus


class LoanCreate(BaseModel):
    """
    Payload de création d'un emprunt (POST /loans).
    Exactement un des deux champs doit être fourni — miroir de la contrainte
    CHECK ck_loan_exactly_one_target en base de données, validé aussi côté API
    pour renvoyer une erreur 422 claire plutôt qu'une erreur 500 de la DB.
    """
    copy_id: int | None = Field(default=None)
    digital_resource_id: int | None = Field(default=None)

    @model_validator(mode="after")
    def check_exactly_one_target(self) -> "LoanCreate":
        has_copy = self.copy_id is not None
        has_digital = self.digital_resource_id is not None
        if has_copy == has_digital:
            raise ValueError(
                "Fournir exactement un des deux champs : copy_id OU digital_resource_id."
            )
        return self


class LoanReturn(BaseModel):
    """Payload optionnel pour le retour d'un document (PUT /loans/{id}/return)."""
    note: str | None = Field(default=None, max_length=500)


class LoanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    copy_id: int | None
    digital_resource_id: int | None
    book_title: str | None = None
    user_name: str | None = None
    borrowed_at: datetime
    due_date: datetime
    returned_at: datetime | None
    status: LoanStatus


class LoanBorrowByScan(BaseModel):
    """
    Payload d'emprunt assiste par double scan (bibliothecaire au poste de pret).
    Reflete le workflow : scanner carte lecteur + scanner QR du livre -> creer emprunt.
    """

    card_number: str = Field(min_length=1, max_length=20)
    qr_code: str = Field(min_length=1, max_length=20)


class LoanReturnByScan(BaseModel):
    """Payload de retour par scan du QR Code de l'exemplaire (sans besoin de connaitre le loan_id)."""

    qr_code: str = Field(min_length=1, max_length=20)


class LoanCreateAdmin(BaseModel):
    """
    Payload d'emprunt manuel cree par un bibliothecaire/admin pour un utilisateur
    donne (pret assiste classique, sans scan QR). Exactement un des deux champs
    copy_id / digital_resource_id doit etre fourni. due_date est optionnelle :
    si absente, la duree standard configuree (settings.LOAN_DURATION_DAYS) s'applique.
    """
    user_id: uuid.UUID
    copy_id: int | None = Field(default=None)
    digital_resource_id: int | None = Field(default=None)
    due_date: datetime | None = Field(default=None)

    @model_validator(mode="after")
    def check_exactly_one_target(self) -> "LoanCreateAdmin":
        has_copy = self.copy_id is not None
        has_digital = self.digital_resource_id is not None
        if has_copy == has_digital:
            raise ValueError(
                "Fournir exactement un des deux champs : copy_id OU digital_resource_id."
            )
        return self
