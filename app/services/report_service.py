"""
Couche service pour le module Rapports et Analyses.
Reflète les endpoints du Cahier d'Architecture §6.4.

NOTE (Phase 2) : ces requêtes sont volontairement simples et lisibles pour le
prototype. Si le volume de données augmente significativement, elles seront
optimisées (index composites, vues matérialisées, cache Redis - cf §8.2).
"""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.copy import Copy
from app.models.enums import CopyStatus, LoanStatus
from app.models.loan import Loan
from app.models.user import User


def get_most_borrowed_books(db: Session, limit: int = 10) -> list[dict]:
    """Livres les plus empruntés, tous statuts d'emprunt confondus."""
    rows = (
        db.query(
            Book.id.label("book_id"),
            Book.author.label("author"),
            Book.title_fr.label("title_fr"),
            Book.title_en.label("title_en"),
            func.count(Loan.id).label("borrow_count"),
        )
        .join(Copy, Copy.book_id == Book.id)
        .join(Loan, Loan.copy_id == Copy.id)
        .group_by(Book.id, Book.author, Book.title_fr, Book.title_en)
        .order_by(func.count(Loan.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "book_id": r.book_id,
            "title": r.title_fr or r.title_en or "Sans titre",
            "author": r.author,
            "borrow_count": r.borrow_count,
        }
        for r in rows
    ]


def get_most_active_users(db: Session, limit: int = 10) -> list[dict]:
    """Utilisateurs les plus actifs, classés par nombre total d'emprunts."""
    rows = (
        db.query(
            User.id.label("user_id"),
            User.full_name.label("full_name"),
            User.email.label("email"),
            func.count(Loan.id).label("loan_count"),
        )
        .join(Loan, Loan.user_id == User.id)
        .group_by(User.id, User.full_name, User.email)
        .order_by(func.count(Loan.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "user_id": str(r.user_id),
            "full_name": r.full_name,
            "email": r.email,
            "loan_count": r.loan_count,
        }
        for r in rows
    ]


def get_overdue_stats(db: Session) -> dict:
    """
    Statistiques des retards.
    Un emprunt "actif" dont la due_date est dépassée est compté comme en retard,
    même si son statut stocké est encore ACTIVE (le job de bascule automatique
    ACTIVE -> OVERDUE est prévu en Phase 2 / tâche planifiée).
    """
    now = datetime.now(timezone.utc)

    total_active = db.query(Loan).filter(Loan.status == LoanStatus.ACTIVE).count()
    total_overdue = (
        db.query(Loan)
        .filter(Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]), Loan.due_date < now)
        .count()
    )
    rate = (total_overdue / total_active * 100) if total_active > 0 else 0.0

    return {
        "total_overdue": total_overdue,
        "total_active": total_active,
        "overdue_rate_percent": round(rate, 2),
    }


def get_summary(db: Session) -> dict:
    """Tableau de bord général — GET /reports/summary."""
    total_books = db.query(Book).count()
    total_copies = db.query(Copy).count()
    copies_available = db.query(Copy).filter(Copy.status == CopyStatus.AVAILABLE).count()
    copies_borrowed = db.query(Copy).filter(Copy.status == CopyStatus.BORROWED).count()
    total_users = db.query(User).count()
    total_loans_active = db.query(Loan).filter(Loan.status == LoanStatus.ACTIVE).count()
    total_loans_overdue = db.query(Loan).filter(Loan.status == LoanStatus.OVERDUE).count()
    total_loans_returned = db.query(Loan).filter(Loan.status == LoanStatus.RETURNED).count()

    return {
        "total_books": total_books,
        "total_copies": total_copies,
        "copies_available": copies_available,
        "copies_borrowed": copies_borrowed,
        "total_users": total_users,
        "total_loans_active": total_loans_active,
        "total_loans_overdue": total_loans_overdue,
        "total_loans_returned": total_loans_returned,
    }