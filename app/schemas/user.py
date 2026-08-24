
"""Schemas Pydantic pour l'entite User (comptes utilisateurs)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import LanguagePref, UserRole


class UserBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    language_pref: LanguagePref = LanguagePref.FR


class UserCreate(UserBase):
    """Payload de creation de compte (POST /auth/register)."""
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.STUDENT


class UserUpdate(BaseModel):
    """Payload de mise a jour du profil (PUT /users/me) — tous les champs optionnels."""
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    language_pref: LanguagePref | None = None


class UserUpdateAdmin(BaseModel):
    """Payload de modification d'un compte par admin ou bibliothécaire."""
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    role: UserRole | None = None
    language_pref: LanguagePref | None = None
    is_active: bool | None = None


class UserAdminUpdate(BaseModel):
    """Payload de modification d'un compte par un admin/bibliothecaire."""
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    role: UserRole | None = None
    language_pref: LanguagePref | None = None
    is_active: bool | None = None


class UserChangePassword(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordChange(BaseModel):
    """Payload de changement de mot de passe par l'utilisateur lui-meme."""
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class UserRead(UserBase):
    """Representation renvoyee par l'API (jamais le password_hash)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: UserRole
    is_active: bool
    card_number: str
    created_at: datetime


class UserCardScanResult(BaseModel):
    """
    Resultat du scan d'une carte membre (GET /users/scan/{card_number}).
    Volontairement minimal : pas d'email ni d'historique, juste de quoi
    identifier le lecteur au poste de pret.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    card_number: str
    full_name: str
    role: UserRole
    is_active: bool


