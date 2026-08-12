"""Schemas Pydantic pour l'auto-remplissage par ISBN (Open Library / Google Books)."""

from pydantic import BaseModel


class IsbnLookupResult(BaseModel):
    """
    Resultat d'une recherche par ISBN, pre-rempli pour alimenter le formulaire
    de creation de livre cote bibliothecaire (il reste libre de corriger avant de valider).
    """
    isbn: str
    title: str | None = None
    author: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    cover_url: str | None = None
    source: str  # "open_library" ou "google_books"

