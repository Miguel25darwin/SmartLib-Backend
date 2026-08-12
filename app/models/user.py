"""Entite `users` — comptes utilisateurs (etudiant, enseignant, personnel, bibliothecaire, admin)."""

import secrets
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import LanguagePref, UserRole

if TYPE_CHECKING:
    from app.models.loan import Loan

# Prefixe de carte par role, conforme a l'exemple du document (ETU-2026-00451)
CARD_PREFIX_BY_ROLE = {
    UserRole.STUDENT: "ETU",
    UserRole.LECTURER: "ENS",
    UserRole.STAFF: "PER",
    UserRole.LIBRARIAN: "BIB",
    UserRole.ADMIN: "ADM",
}


def generate_card_number(role: UserRole = UserRole.STUDENT) -> str:
    """
    Genere un numero de carte membre unique, format PREFIX-ANNEE-XXXXX
    (ex: ETU-2026-00451), destine a etre encode dans le QR Code de la carte.
    """
    prefix = CARD_PREFIX_BY_ROLE.get(role, "USR")
    year = datetime.now(timezone.utc).year
    suffix = f"{secrets.randbelow(100000):05d}"
    return f"{prefix}-{year}-{suffix}"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"), nullable=False, default=UserRole.STUDENT
    )
    language_pref: Mapped[LanguagePref] = mapped_column(
        SAEnum(LanguagePref, name="language_pref"), nullable=False, default=LanguagePref.FR
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # --- Ajout : carte membre QR, conforme aux "Consignes de Gestion du catalogue" ---
    card_number: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False, default=generate_card_number
    )

    loans: Mapped[list["Loan"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value}) card={self.card_number}>"

