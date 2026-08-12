"""Schemas Pydantic pour les resultats d'import/export en masse du catalogue."""

from pydantic import BaseModel


class ImportRowError(BaseModel):
    """Erreur rencontree sur une ligne specifique du CSV importe."""
    row_number: int
    error: str
    raw_data: dict


class ImportResult(BaseModel):
    """Resultat d'un import CSV — bilan complet, jamais un simple succes/echec binaire."""
    total_rows: int
    created_count: int
    skipped_count: int
    errors: list[ImportRowError]
