"""
Module Catalogue et Recherche.
Reflète exactement les endpoints du Cahier d'Architecture §6.2.
Écriture (POST/PUT/DELETE) réservée aux rôles librarian/admin (RBAC).
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import BookType, LanguagePref, UserRole
from app.models.book import Book
from app.schemas.book import BookCreate, BookRead, BookUpdate
from app.schemas.copy import CopyCreate, CopyRead, CopyUpdate, CopyScanResult
from app.schemas.digital_resource import DigitalResourceCreate, DigitalResourceRead, DigitalResourceUpdate
from app.services.book_service import (
    BookInUseError,
    BookHasLoanHistoryError,
    BookNotFoundError,
    IsbnAlreadyExistsError,
    create_book,
    delete_book,
    get_book,
    search_books,
    update_book,
    DeweyIdInvalidError,
)
from app.services.copy_service import BookNotFoundForCopyError, QrCodeNotFoundError, scan_qr_code, update_copy
from app.services.copy_service import create_copy, list_copies_for_book
from app.services.digital_resource_service import create_digital_resource, delete_digital_resource, list_digital_resources_for_book, update_digital_resource, BookNotFoundError as DigitalBookNotFoundError, DigitalResourceNotFoundError

router = APIRouter(prefix="/books", tags=["catalogue"])

LIBRARIAN_OR_ADMIN = require_roles(UserRole.LIBRARIAN, UserRole.ADMIN)
ADMIN_ONLY = require_roles(UserRole.ADMIN)

from app.services.copy_service import (
    CopyNotRepairableError,
    mark_copy_as_lost,
    mark_copy_as_repaired,
)
from app.services.upload_service import InvalidImageError, ImageTooLargeError, save_cover_image



@router.get("", response_model=list[BookRead])
def list_books(
    search: str | None = None,
    type: BookType | None = None,
    language: LanguagePref | None = None,
    dewey_category_id: int | None = None,
    available: bool = False,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[BookRead]:
    """Liste des livres avec pagination et filtres (recherche libre, type, langue, catégorie Dewey, disponibilité)."""
    return search_books(
        db, search=search, book_type=type, language=language,
        dewey_category_id=dewey_category_id,
        available_only=available, skip=skip, limit=limit,
    )
@router.get("/copies/scan/{qr_code}", response_model=CopyScanResult, tags=["catalogue", "qr-code"])
def scan_copy_qr_code(
    qr_code: str,
    _current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CopyScanResult:
    """Scan d'un QR Code d'exemplaire — réservé aux utilisateurs authentifiés."""
    try:
        return scan_qr_code(db, qr_code)
    except QrCodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/copies/{copy_id}", response_model=CopyRead, dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def edit_copy(copy_id: int, copy_update: CopyUpdate, db: Session = Depends(get_db)) -> CopyRead:
    """Modifier un exemplaire (statut, localisation, cote)."""
    from app.services.copy_service import CopyNotFoundError as _CopyNotFoundError
    try:
        return update_copy(db, copy_id, copy_update)
    except _CopyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{book_id}", response_model=BookRead)
def get_book_detail(book_id: int, db: Session = Depends(get_db)) -> BookRead:
    """Détail d'un livre, avec compteur d'exemplaires disponibles/total."""
    try:
        return get_book(db, book_id)
    except BookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOOK_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def add_book(book_in: BookCreate, db: Session = Depends(get_db)) -> BookRead:
    """Ajouter un livre au catalogue (bibliothécaire / admin)."""
    try:
        return create_book(db, book_in)
    except IsbnAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DeweyIdInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.put("/{book_id}", response_model=BookRead, dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def edit_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)) -> BookRead:
    """Modifier un livre existant (bibliothécaire / admin)."""
    try:
        return update_book(db, book_id, book_update)
    except BookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOOK_NOT_FOUND", "message": str(exc)},
        ) from exc
    except DeweyIdInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(ADMIN_ONLY)])
def remove_book(book_id: int, db: Session = Depends(get_db)) -> None:
    """Supprimer un livre du catalogue (admin uniquement)."""
    try:
        delete_book(db, book_id)
    except BookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOOK_NOT_FOUND", "message": str(exc)},
        ) from exc
    except BookInUseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except BookHasLoanHistoryError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{book_id}/copies", response_model=CopyRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def add_copy(book_id: int, copy_in: CopyCreate, db: Session = Depends(get_db)) -> CopyRead:
    """Ajouter un exemplaire physique à un livre (bibliothécaire / admin)."""
    if copy_in.book_id != book_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="book_id du corps de la requête incohérent avec l'URL.",
        )
    try:
        return create_copy(db, copy_in)
    except BookNotFoundForCopyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Livre id={book_id} introuvable.") from exc


@router.get("/{book_id}/copies", response_model=list[CopyRead])
def get_book_copies(book_id: int, db: Session = Depends(get_db)) -> list[CopyRead]:
    """Liste des exemplaires d'un livre donné, avec leur statut."""
    return list_copies_for_book(db, book_id)


@router.post("/{book_id}/cover", response_model=BookRead, dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
async def upload_book_cover(
    book_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> BookRead:
    """Uploader une image de couverture pour un livre."""
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Livre id={book_id} introuvable.")
    try:
        book.cover_url = await save_cover_image(file)
    except InvalidImageError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except ImageTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc

    db.commit()
    db.refresh(book)
    from app.services.book_service import _with_copy_counts
    return _with_copy_counts(db, book)


@router.put("/copies/{copy_id}/damaged", response_model=CopyRead, dependencies=[Depends(LIBRARIAN_OR_ADMIN)], tags=["catalogue"])
def mark_copy_damaged(copy_id: int, db: Session = Depends(get_db)) -> CopyRead:
    """Met un exemplaire en statut endommagé."""
    try:
        damage_payload = CopyUpdate(status="damaged")
        return update_copy(db, copy_id, damage_payload)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Exemplaire id={copy_id} introuvable.") from exc


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


@router.get("/{book_id}/digital-resources", response_model=list[DigitalResourceRead])
def list_resources(book_id: int, db: Session = Depends(get_db)) -> list[DigitalResourceRead]:
    """Retourne les ressources numériques liées à un livre."""
    try:
        return list_digital_resources_for_book(db, book_id)
    except DigitalBookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{book_id}/digital-resources", response_model=DigitalResourceRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def create_resource(book_id: int, payload: DigitalResourceCreate, db: Session = Depends(get_db)) -> DigitalResourceRead:
    """Crée une ressource numérique pour un livre."""
    if payload.book_id != book_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="book_id du corps de la requête incohérent avec l'URL.")
    try:
        return create_digital_resource(db, payload)
    except DigitalBookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/digital-resources/{resource_id}", response_model=DigitalResourceRead, dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def update_resource(resource_id: int, payload: DigitalResourceUpdate, db: Session = Depends(get_db)) -> DigitalResourceRead:
    """Met à jour une ressource numérique."""
    try:
        return update_digital_resource(db, resource_id, payload)
    except DigitalResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/digital-resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def delete_resource(resource_id: int, db: Session = Depends(get_db)) -> None:
    """Supprime une ressource numérique."""
    try:
        delete_digital_resource(db, resource_id)
    except DigitalResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
