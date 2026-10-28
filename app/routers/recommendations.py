"""Router Recommandations d'ouvrages.

- Lecture : tout utilisateur authentifie (les etudiants consultent les ouvrages
  recommandes pour leurs cours).
- Ecriture : personnel enseignant, personnel administratif, bibliothecaire, admin.
- Modification / suppression : auteur de la recommandation ou gestionnaire
  (bibliothecaire / admin).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationCreate,
    RecommendationRead,
    RecommendationUpdate,
)
from app.services.recommendation_service import (
    DuplicateRecommendationError,
    RecommendationBookNotFoundError,
    RecommendationForbiddenError,
    RecommendationNotFoundError,
    create_recommendation,
    delete_recommendation,
    get_recommendation,
    list_recommendations,
    update_recommendation,
)

router = APIRouter(prefix="/recommendations", tags=["recommandations"])

CONTRIBUTOR_ROLES = (
    UserRole.LECTURER,
    UserRole.STAFF,
    UserRole.LIBRARIAN,
    UserRole.ADMIN,
)


@router.get("", response_model=list[RecommendationRead])
def list_all(
    mine: bool = Query(default=False, description="Limiter a mes recommandations"),
    course_code: str | None = Query(default=None, max_length=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RecommendationRead]:
    """Liste des recommandations, avec couverture du stock calculee en direct."""
    return list_recommendations(db, current_user, mine=mine, course_code=course_code)


@router.get("/{recommendation_id}", response_model=RecommendationRead)
def get_one(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationRead:
    try:
        return get_recommendation(db, recommendation_id, current_user)
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "",
    response_model=RecommendationRead,
    status_code=status.HTTP_201_CREATED,
)
def create(
    payload: RecommendationCreate,
    current_user: User = Depends(require_roles(*CONTRIBUTOR_ROLES)),
    db: Session = Depends(get_db),
) -> RecommendationRead:
    """Recommander un ouvrage pour un cours (personnel / enseignants)."""
    try:
        return create_recommendation(db, payload, current_user)
    except RecommendationBookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateRecommendationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.put("/{recommendation_id}", response_model=RecommendationRead)
def update(
    recommendation_id: int,
    payload: RecommendationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationRead:
    try:
        return update_recommendation(db, recommendation_id, payload, current_user)
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RecommendationForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RecommendationBookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateRecommendationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{recommendation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        delete_recommendation(db, recommendation_id, current_user)
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RecommendationForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
