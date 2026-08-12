
"""Schémas Pydantic liés à l'authentification par jeton."""

from pydantic import BaseModel


class Token(BaseModel):
    """Réponse de POST /auth/login."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Contenu décodé d'un jeton JWT SmartLib."""
    sub: str
    role: str
    exp: int
