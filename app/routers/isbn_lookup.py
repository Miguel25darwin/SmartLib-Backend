"""Module Auto-remplissage ISBN. Conforme aux "Consignes de Gestion du catalogue"."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import require_roles
from app.models.enums import UserRole
from app.schemas.isbn_lookup import IsbnLookupResult
from app.services.isbn_lookup_service import InvalidIsbnFormatError, lookup_isbn

router = APIRouter(prefix="/isbn-lookup", tags=["catalogue", "isbn-lookup"])

LIBRARIAN_OR_ADMIN = require_roles(UserRole.LIBRARIAN, UserRole.ADMIN)


@router.get("/{isbn}", response_model=IsbnLookupResult, dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def get_isbn_metadata(isbn: str) -> IsbnLookupResult:
    """Recherche les metadonnees d'un livre par ISBN (Open Library, puis Google Books en fallback)."""
    try:
        result = lookup_isbn(isbn)
    except InvalidIsbnFormatError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune information trouvee pour l'ISBN '{isbn}' (Open Library et Google Books consultes).",
        )
    return result