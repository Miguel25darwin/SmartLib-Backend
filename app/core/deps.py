
"""
Dépendances FastAPI transversales : authentification (get_current_user)
et contrôle d'accès basé sur les rôles (require_roles).

Ce module ne contient AUCUNE route — uniquement des dépendances réutilisables
par les routers (étapes 7 à 10).
"""

import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import InvalidTokenError, safe_decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Identifiants invalides ou session expirée.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Décode le jeton JWT, récupère l'utilisateur correspondant en base et
    vérifie qu'il est toujours actif. Utilisé dans toutes les routes protégées.
    """
    try:
        payload = safe_decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise CREDENTIALS_EXCEPTION
    except InvalidTokenError:
        raise CREDENTIALS_EXCEPTION

    user = db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise CREDENTIALS_EXCEPTION
    return user


def require_roles(*allowed_roles: UserRole) -> Callable:
    """
    Fabrique de dépendance RBAC.

    Usage dans un router :
        @router.post("/books", dependencies=[Depends(require_roles(UserRole.LIBRARIAN, UserRole.ADMIN))])

    Renvoie 403 si le rôle de l'utilisateur courant n'est pas dans la liste autorisée.
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé : rôle '{current_user.role.value}' non autorisé pour cette action.",
            )
        return current_user

    return role_checker
