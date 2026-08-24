"""Routes de gestion du profil utilisateur et scan de carte membre."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.models.enums import UserRole as UserRoleEnum
from app.services.user_service import (
    InvalidCurrentPasswordError,
    change_password as change_password_service,
    deactivate_user,
    list_users,
    update_user_admin,
)
from app.schemas.user import PasswordChange, UserAdminUpdate, UserCardScanResult, UserRead, UserUpdate
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


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Changer son propre mot de passe (necessite l'ancien mot de passe)."""
    try:
        change_password_service(db, current_user, payload.current_password, payload.new_password)
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.put("/{user_id}", response_model=UserRead, dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def update_user(user_id: uuid.UUID, data: UserAdminUpdate, db: Session = Depends(get_db)) -> UserRead:
    """Modifier un compte utilisateur (bibliothecaire / admin)."""
    try:
        return update_user_admin(db, user_id, data)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{user_id}", response_model=UserRead, dependencies=[Depends(require_roles(UserRole.ADMIN))])
def delete_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> UserRead:
    """Desactive un compte utilisateur (admin uniquement)."""
    try:
        return deactivate_user(db, user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("", response_model=list[UserRead], dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def list_all_users(
    role: UserRoleEnum | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[UserRead]:
    """
    Liste tous les utilisateurs du systeme, avec filtre optionnel par role
    et pagination. Reserve bibliothecaire/admin.
    """
    return list_users(db, role_filter=role.value if role else None, skip=skip, limit=limit)
