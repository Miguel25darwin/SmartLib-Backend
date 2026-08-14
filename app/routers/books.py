"""
Module Catalogue et Recherche.
Reflète exactement les endpoints du Cahier d'Architecture §6.2.
Écriture (POST/PUT/DELETE) réservée aux rôles librarian/admin (RBAC).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.enums import BookType, LanguagePref, UserRole
from app.schemas.book import BookCreate, BookRead, BookUpdate
from app.schemas.copy import CopyCreate, CopyRead
from app.services.book_service import (
    BookNotFoundError,
    IsbnAlreadyExistsError,
    create_book,
    delete_book,
    get_book,
    search_books,
    update_book,
)
from app.schemas.copy import CopyScanResult
from app.services.copy_service import QrCodeNotFoundError, scan_qr_code
from app.services.copy_service import create_copy, list_copies_for_book

router = APIRouter(prefix="/books", tags=["catalogue"])

LIBRARIAN_OR_ADMIN = require_roles(UserRole.LIBRARIAN, UserRole.ADMIN)
ADMIN_ONLY = require_roles(UserRole.ADMIN)

from app.services.copy_service import (
    CopyNotRepairableError,
    mark_copy_as_lost,
    mark_copy_as_repaired,
)



@router.get("", response_model=list[BookRead])
def list_books(
    search: str | None = None,
    type: BookType | None = None,
    language: LanguagePref | None = None,
    available: bool = False,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[BookRead]:
    """Liste des livres avec pagination et filtres (recherche libre, type, langue, disponibilité)."""
    return search_books(
        db, search=search, book_type=type, language=language,
        available_only=available, skip=skip, limit=limit,
    )
@router.get("/copies/scan/{qr_code}", response_model=CopyScanResult, tags=["catalogue", "qr-code"])
def scan_copy_qr_code(qr_code: str, db: Session = Depends(get_db)) -> CopyScanResult:
    """
    Scan d'un QR Code d'exemplaire — endpoint public de lookup.
    Utilise par l'application mobile lors du scan (emprunt, retour, inventaire).
    """
    try:
        return scan_qr_code(db, qr_code)
    except QrCodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{book_id}", response_model=BookRead)
def get_book_detail(book_id: int, db: Session = Depends(get_db)) -> BookRead:
    """Détail d'un livre, avec compteur d'exemplaires disponibles/total."""
    try:
        return get_book(db, book_id)
    except BookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def add_book(book_in: BookCreate, db: Session = Depends(get_db)) -> BookRead:
    """Ajouter un livre au catalogue (bibliothécaire / admin)."""
    try:
        return create_book(db, book_in)
    except IsbnAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.put("/{book_id}", response_model=BookRead, dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def edit_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)) -> BookRead:
    """Modifier un livre existant (bibliothécaire / admin)."""
    try:
        return update_book(db, book_id, book_update)
    except BookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(ADMIN_ONLY)])
def remove_book(book_id: int, db: Session = Depends(get_db)) -> None:
    """Supprimer un livre du catalogue (admin uniquement)."""
    try:
        delete_book(db, book_id)
    except BookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{book_id}/copies", response_model=CopyRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def add_copy(book_id: int, copy_in: CopyCreate, db: Session = Depends(get_db)) -> CopyRead:
    """Ajouter un exemplaire physique à un livre (bibliothécaire / admin)."""
    if copy_in.book_id != book_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="book_id du corps de la requête incohérent avec l'URL.",
        )
    return create_copy(db, copy_in)


@router.get("/{book_id}/copies", response_model=list[CopyRead])
def get_book_copies(book_id: int, db: Session = Depends(get_db)) -> list[CopyRead]:
    """Liste des exemplaires d'un livre donné, avec leur statut."""
    return list_copies_for_book(db, book_id)

@router.put("/copies/{copy_id}/lost", response_model=CopyRead,
            dependencies=[Depends(LIBRARIAN_OR_ADMIN)], tags=["catalogue"])
def report_copy_lost(copy_id: int, db: Session = Depends(get_db)) -> CopyRead:
    """Marque un exemplaire comme perdu (bibliothecaire / admin)."""
    from app.services.copy_service import CopyNotFoundError as _CopyNotFoundError
    try:
        return mark_copy_as_lost(db, copy_id)
    except _CopyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/copies/{copy_id}/repair", response_model=CopyRead,
            dependencies=[Depends(LIBRARIAN_OR_ADMIN)], tags=["catalogue"])
def report_copy_repaired(copy_id: int, db: Session = Depends(get_db)) -> CopyRead:
    """Remet un exemplaire endommage en circulation (bibliothecaire / admin)."""
    from app.services.copy_service import CopyNotFoundError as _CopyNotFoundError
    try:
        return mark_copy_as_repaired(db, copy_id)
    except _CopyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CopyNotRepairableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc 
