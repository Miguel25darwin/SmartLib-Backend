"""
Regroupe tous les modèles ORM pour que Base.metadata les connaisse.
Doit être importé avant tout create_all() ou autogénération Alembic.
"""

from app.db.base_class import Base  # noqa: F401
from app.models.book import Book  # noqa: F401
from app.models.copy import Copy  # noqa: F401
from app.models.digital_resource import DigitalResource  # noqa: F401
from app.models.loan import Loan  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = ["Base", "User", "Book", "Copy", "DigitalResource", "Loan"]


