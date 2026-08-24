"""
Module Import/Export en masse du catalogue + endpoint Dewey categories.
Conforme aux "Consignes de Gestion du catalogue".
Reserve bibliothecaire/admin (operation sensible sur le catalogue).
"""

import io

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.dewey_classification import DeweyClassification
from app.models.enums import BookType, LanguagePref, UserRole
from app.schemas.book import BookRead
from app.schemas.dewey import DeweyClassificationRead
from app.schemas.import_export import ImportResult
from app.services.catalogue_import_export import export_books_to_csv, import_books_from_csv
from app.services.book_service import (
    DeweyRootNotFoundError,
    search_books,
)

router = APIRouter(prefix="/catalogue", tags=["catalogue", "import-export"])

LIBRARIAN_OR_ADMIN = require_roles(UserRole.LIBRARIAN, UserRole.ADMIN)


@router.get("/search", response_model=list[BookRead])
def search_catalogue(
    dewey_root: str,
    search: str | None = None,
    type: BookType | None = None,
    language: LanguagePref | None = None,
    available: bool = False,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[BookRead]:
    """Recherche les livres rattaches a une racine Dewey et ses descendants."""
    try:
        return search_books(
            db,
            search=search,
            book_type=type,
            language=language,
            dewey_root=dewey_root,
            available_only=available,
            skip=skip,
            limit=limit,
        )
    except DeweyRootNotFoundError as exc:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DEWEY_ROOT_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.get(
    "/dewey-categories",
    response_model=list[DeweyClassificationRead],
    tags=["dewey"],
)
def list_dewey_categories(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> list[DeweyClassificationRead]:
    """
    Liste les categories Dewey actives triees par code.
    Consommé par le dropdown Flutter sur les formulaires de creation/edition de livre.
    """
    return (
        db.query(DeweyClassification)
        .filter(DeweyClassification.is_active.is_(True))
        .order_by(DeweyClassification.code)
        .all()
    )


@router.get("/export", dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def export_catalogue(db: Session = Depends(get_db)) -> StreamingResponse:
    """
    Exporte l'integralite du catalogue au format CSV, telechargeable directement
    (ouvrable dans Excel/LibreOffice). Inclut les champs Dewey resolus et la cote.
    """
    csv_content = export_books_to_csv(db)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=smartlib_catalogue_export.csv"},
    )


@router.post("/import", response_model=ImportResult, status_code=status.HTTP_200_OK,
             dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
async def import_catalogue(
    file: UploadFile,
    db: Session = Depends(get_db),
) -> ImportResult:
    """
    Importe des livres en masse depuis un fichier CSV.
    Colonnes attendues (header) : title_fr, title_en, author, isbn, publisher,
    publication_year, dewey_id, dewey_code, type, language, cover_url, call_number
    (seuls 'author' et 'type' sont obligatoires).
    dewey_id (entier) ou dewey_code (code texte ex: '500') peuvent etre utilises
    pour rattacher le livre au referentiel Dewey.
    call_number : si fourni pour un livre physique, cree automatiquement un exemplaire.
    """
    raw_bytes = await file.read()
    csv_content = raw_bytes.decode("utf-8-sig")  # utf-8-sig gere le BOM d'Excel Windows
    return import_books_from_csv(db, csv_content)
