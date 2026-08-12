"""
Classe de base déclarative SQLAlchemy 2.0.
Tous les modèles (User, Book, Copy, ...) héritent de `Base`.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base déclarative partagée par tous les modèles ORM."""
    pass


class TimestampMixin:
    """Mixin ajoutant created_at / updated_at, gérés automatiquement par la base de données."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )