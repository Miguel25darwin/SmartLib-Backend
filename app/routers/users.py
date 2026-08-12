"""Routes de gestion du profil utilisateur et scan de carte membre."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserCardScanResult, UserRead, UserUpdate
from app.services.user_service import UserNotFoundError, get_user_by_card_number

router = APIRouter(prefix="/users", tags=["users"])

LIBRARIAN_OR_ADMIN = require_roles(UserRole.LIBRARIAN, UserRole.ADMIN)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserRead:
    """Profil de l'utilisateur actuellement connecte (inclut son numero de carte)."""
    return current_user


@router.put("/me", response_model=UserRead)
def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    """Modifier son propre profil (nom complet, preference de langue)."""
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get(
    "/scan/{card_number}",
    response_model=UserCardScanResult,
    dependencies=[Depends(LIBRARIAN_OR_ADMIN)],
    tags=["users", "qr-code"],
)
def scan_user_card(card_number: str, db: Session = Depends(get_db)) -> UserCardScanResult:
    """
    Scan de la carte membre d'un lecteur — reserve bibliothecaire/admin.
    Utilise au poste de pret pour identifier rapidement le lecteur (§3 du document
    "Consignes de Gestion du catalogue").
    """
    try:
        return get_user_by_card_number(db, card_number)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

