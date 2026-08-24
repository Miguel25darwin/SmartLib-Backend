"""
Module Referentiel Dewey.
Lecture publique (tout utilisateur authentifie peut consulter le referentiel
pour le formulaire de creation de livre) ; ecriture reservee admin (le
referentiel est une donnee structurante, pas un usage courant bibliothecaire).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.schemas.dewey import DeweyClassificationCreate, DeweyClassificationRead
from app.services.dewey_service import (
    DeweyCodeAlreadyExistsError,
    DeweyNotFoundError,
    DeweyParentNotFoundError,
    create_classification,
    get_classification,
    list_all_classifications,
)

router = APIRouter(prefix="/dewey", tags=["dewey"])

ADMIN_ONLY = require_roles(UserRole.ADMIN)


@router.get("", response_model=list[DeweyClassificationRead])
def list_dewey(db: Session = Depends(get_db), _current_user=Depends(get_current_user)) -> list[DeweyClassificationRead]:
    """Liste plate de toutes les categories Dewey actives (pour peupler un dropdown Flutter)."""
    return list_all_classifications(db)


@router.get("/{classification_id}", response_model=DeweyClassificationRead)
def get_dewey(
    classification_id: int, db: Session = Depends(get_db), _current_user=Depends(get_current_user)
) -> DeweyClassificationRead:
    """Detail d'une categorie Dewey."""
    try:
        return get_classification(db, classification_id)
    except DeweyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("", response_model=DeweyClassificationRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(ADMIN_ONLY)])
def add_dewey(data: DeweyClassificationCreate, db: Session = Depends(get_db)) -> DeweyClassificationRead:
    """Ajoute une categorie Dewey au referentiel (admin uniquement)."""
    try:
        return create_classification(db, data)
    except DeweyCodeAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DeweyParentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
