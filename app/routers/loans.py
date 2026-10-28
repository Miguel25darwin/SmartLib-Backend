
"""
Module Emprunts.
Reflète les endpoints du Cahier d'Architecture §6.3.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import LOAN_LIMITS_BY_ROLE, LoanStatus, UserRole
from app.models.user import User
from app.schemas.loan import LoanCreate, LoanRead
from app.schemas.loan import LoanBorrowByScan, LoanReturnByScan
from app.schemas.loan import LoanCreateAdmin, LoanDecision
from app.services.loan_service import create_loan_for_user
from app.services.user_service import UserNotFoundError as _UserNotFoundErrorAdmin
from app.services.loan_service import borrow_by_scan, return_by_scan
from app.services.user_service import UserNotFoundError

from app.services.loan_service import (
    CopyNotAvailableError,
    CopyNotFoundError,
    DigitalResourceNotFoundError,
    LoanAlreadyReturnedError,
    LoanNotFoundError,
    LoanNotPendingError,
    LoanQuotaExceededError,
    NotLoanOwnerError,
    approve_loan,
    create_loan,
    list_all_loans,
    list_loans_for_user,
    list_pending_loans,
    reject_loan,
    return_loan,
)

router = APIRouter(prefix="/loans", tags=["emprunts"])

LIBRARIAN_OR_ADMIN = require_roles(UserRole.LIBRARIAN, UserRole.ADMIN)


@router.get("/config", dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def loan_config() -> dict:
    """
    Regles metier d'emprunt exposees a l'interface de gestion.

    Source de verite unique : les quotas et la duree ne sont plus dupliques
    en dur cote Flutter.
    """
    return {
        "duration_days": settings.LOAN_DURATION_DAYS,
        "limits_by_role": {
            role.value: limit for role, limit in LOAN_LIMITS_BY_ROLE.items()
        },
    }


@router.post("", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
def borrow(
    loan_in: LoanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LoanRead:
    """Créer une demande d'emprunt (copy_id ou digital_resource_id) pour l'utilisateur connecté.

    La demande est créée au statut PENDING : un bibliothécaire/admin doit
    l'autoriser avant que le membre n'obtienne le document.
    """
    try:
        return create_loan(db, current_user, loan_in)
    except LoanQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (CopyNotFoundError, DigitalResourceNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CopyNotAvailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "/pending",
    response_model=list[LoanRead],
    dependencies=[Depends(LIBRARIAN_OR_ADMIN)],
)
def pending_loans(db: Session = Depends(get_db)) -> list[LoanRead]:
    """Demandes d'emprunt en attente d'autorisation (bibliothécaire/admin)."""
    return list_pending_loans(db)


@router.get(
    "/pending/count",
    dependencies=[Depends(LIBRARIAN_OR_ADMIN)],
)
def pending_loans_count(db: Session = Depends(get_db)) -> dict:
    """Nombre de demandes en attente — utilisé par la cloche de notifications."""
    return {"count": len(list_pending_loans(db))}


@router.put(
    "/{loan_id}/approve",
    response_model=LoanRead,
    dependencies=[Depends(LIBRARIAN_OR_ADMIN)],
)
def approve_pending_loan(
    loan_id: uuid.UUID,
    payload: LoanDecision | None = None,
    db: Session = Depends(get_db),
) -> LoanRead:
    """Autoriser une demande d'emprunt après vérification de l'exemplaire."""
    try:
        return approve_loan(db, loan_id, note=payload.note if payload else None)
    except LoanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (LoanNotPendingError, CopyNotAvailableError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LoanQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.put(
    "/{loan_id}/reject",
    response_model=LoanRead,
    dependencies=[Depends(LIBRARIAN_OR_ADMIN)],
)
def reject_pending_loan(
    loan_id: uuid.UUID,
    payload: LoanDecision | None = None,
    db: Session = Depends(get_db),
) -> LoanRead:
    """Refuser une demande d'emprunt (l'exemplaire reste disponible)."""
    try:
        return reject_loan(db, loan_id, note=payload.note if payload else None)
    except LoanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LoanNotPendingError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/admin",
    response_model=LoanRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(LIBRARIAN_OR_ADMIN)],
)
def borrow_for_user(payload: LoanCreateAdmin, db: Session = Depends(get_db)) -> LoanRead:
    """
    Emprunt manuel cree par un bibliothecaire/admin pour un utilisateur donne
    (pret assiste au guichet). Applique les memes regles metier que l'emprunt
    en libre-service (quota par role, disponibilite de l'exemplaire).
    """
    from app.models.user import User as _UserModel

    target_user = db.get(_UserModel, payload.user_id)
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utilisateur id={payload.user_id} introuvable.",
        )

    try:
        return create_loan_for_user(
            db,
            target_user,
            copy_id=payload.copy_id,
            digital_resource_id=payload.digital_resource_id,
            due_date_override=payload.due_date,
        )
    except LoanQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (CopyNotFoundError, DigitalResourceNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CopyNotAvailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
@router.get("/me", response_model=list[LoanRead])
def my_loans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LoanRead]:
    """Mes emprunts en cours + historique."""
    return list_loans_for_user(db, current_user.id)
@router.post(
    "/scan/borrow",
    response_model=LoanRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(LIBRARIAN_OR_ADMIN)],
    tags=["emprunts", "qr-code"],
)
def borrow_via_scan(
    payload: LoanBorrowByScan,
    db: Session = Depends(get_db),
) -> LoanRead:
    """
    Emprunt assisté par double scan (carte lecteur + QR livre) — poste de prêt.
    Reflète le workflow §3 du document "Consignes de Gestion du catalogue".
    """
    try:
        return borrow_by_scan(db, payload.card_number, payload.qr_code)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LoanQuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except CopyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CopyNotAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.put(
    "/scan/return",
    response_model=LoanRead,
    dependencies=[Depends(LIBRARIAN_OR_ADMIN)],
    tags=["emprunts", "qr-code"],
)
def return_via_scan(
    payload: LoanReturnByScan,
    db: Session = Depends(get_db),
) -> LoanRead:
    """
    Retour par scan du QR Code de l'exemplaire — poste de prêt.
    Reflète le workflow §4.
    """
    try:
        return return_by_scan(db, payload.qr_code)
    except CopyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LoanNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

@router.put("/{loan_id}/return", response_model=LoanRead)
def return_document(
    loan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LoanRead:
    """Retourner un document (par son propriétaire, ou un bibliothécaire/admin au guichet)."""
    try:
        return return_loan(db, loan_id, current_user)
    except LoanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NotLoanOwnerError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LoanAlreadyReturnedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[LoanRead], dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def all_loans(
    status_filter: LoanStatus | None = None,
    db: Session = Depends(get_db),
) -> list[LoanRead]:
    """Tous les emprunts de la bibliothèque (bibliothécaire / admin)."""
    return list_all_loans(db, status_filter)
    
