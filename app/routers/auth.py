"""Routes d'authentification : inscription et connexion."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import EmailAlreadyExistsError, authenticate_user, create_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    """Crée un nouveau compte SmartLib (étudiant, enseignant, personnel...)."""
    try:
        user = create_user(db, user_in)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """
    Connexion — retourne un JWT.
    Le champ 'username' du formulaire OAuth2 standard porte l'email.

    NOTE (à affiner en phase 2) : la durée de vie du jeton utilise par défaut
    l'expiration "campus" (8h). La distinction campus/distant nécessitera
    la détection du réseau d'origine (IP university) côté infrastructure.
    """
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES_CAMPUS,
    )
    return Token(access_token=access_token)
