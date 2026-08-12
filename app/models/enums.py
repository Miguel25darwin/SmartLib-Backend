"""
Enums métier partagés par plusieurs modèles.
Alignés sur le Cahier d'Architecture SmartLib v1.0 (§3 et §5).
"""

import enum


class UserRole(str, enum.Enum):
    STUDENT = "student"
    LECTURER = "lecturer"
    STAFF = "staff"
    LIBRARIAN = "librarian"
    ADMIN = "admin"


class LanguagePref(str, enum.Enum):
    FR = "fr"
    EN = "en"


class BookType(str, enum.Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"


class CopyStatus(str, enum.Enum):
    AVAILABLE = "available"
    BORROWED = "borrowed"
    RESERVED = "reserved"
    DAMAGED = "damaged"
    LOST = "lost"


class DigitalFormat(str, enum.Enum):
    PDF = "pdf"
    EPUB = "epub"
    AUDIO = "audio"
    VIDEO = "video"


class LoanStatus(str, enum.Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"


# Quotas d'emprunt simultané par rôle (Cahier d'Architecture §3)
LOAN_LIMITS_BY_ROLE: dict[UserRole, int] = {
    UserRole.STUDENT: 5,
    UserRole.LECTURER: 10,
    UserRole.STAFF: 7,
    UserRole.LIBRARIAN: 999,
    UserRole.ADMIN: 999,
}