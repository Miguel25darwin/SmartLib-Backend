
"""Point d'entrée du package schemas — réexporte les schémas les plus utilisés."""

from app.schemas.book import BookCreate, BookRead, BookUpdate
from app.schemas.copy import CopyCreate, CopyRead, CopyUpdate
from app.schemas.digital_resource import DigitalResourceCreate, DigitalResourceRead
from app.schemas.loan import LoanCreate, LoanRead, LoanReturn
from app.schemas.user import UserCreate, UserRead, UserUpdate

__all__ = [
    "UserCreate", "UserRead", "UserUpdate",
    "BookCreate", "BookRead", "BookUpdate",
    "CopyCreate", "CopyRead", "CopyUpdate",
    "DigitalResourceCreate", "DigitalResourceRead",
    "LoanCreate", "LoanRead", "LoanReturn",
]
