"""
Sécurité applicative : hash de mot de passe et gestion des jetons JWT.

Conforme au Cahier d'Architecture §3.1 :
- hachage bcrypt
- jetons JWT signés, expiration configurable (8h campus / 2h accès distant)
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
import bcrypt

from app.core.config import settings



def hash_password(plain_password: str) -> str:
    """Hache un mot de passe en clair avec bcrypt."""
    salt = bcrypt.gensalt()
    pwd_bytes = plain_password.encode('utf-8')
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe en clair contre son hash stocké en base."""
    pwd_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str, expires_minutes: int) -> str:
    """
    Crée un jeton JWT signé.

    `subject` = user.id (str), `role` = rôle métier (inclus dans le payload
    pour permettre un contrôle RBAC sans requête DB supplémentaire si besoin).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Décode et valide un jeton JWT.
    Lève jose.JWTError si le jeton est invalide, corrompu ou expiré.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


class InvalidTokenError(Exception):
    """Exception métier levée par les dépendances FastAPI en cas de jeton invalide."""
    pass


def safe_decode_access_token(token: str) -> dict:
    """Wrapper qui convertit toute erreur JWT en InvalidTokenError (plus simple à catcher)."""
    try:
        return decode_access_token(token)
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
