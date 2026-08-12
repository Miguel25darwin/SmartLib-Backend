
"""
Module Rapports et Analyses.
Reflète les endpoints du Cahier d'Architecture §6.4.
Accès reserve bibliothecaire / admin (donnees de gestion interne).
"""

from fastapi import APIRouter, Depends

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.schemas.report import (
    ActiveUserItem,
    MostBorrowedItem,
    OverdueStats,
    ReportSummary,
)
from app.services.report_service import (
    get_most_active_users,
    get_most_borrowed_books,
    get_overdue_stats,
    get_summary,
)
from sqlalchemy.orm import Session
from fastapi import Depends as FastAPIDepends

router = APIRouter(
    prefix="/reports",
    tags=["rapports"],
    dependencies=[Depends(require_roles(UserRole.LIBRARIAN, UserRole.ADMIN))],
)


@router.get("/most-borrowed", response_model=list[MostBorrowedItem])
def most_borrowed(limit: int = 10, db: Session = FastAPIDepends(get_db)) -> list[MostBorrowedItem]:
    """Livres les plus empruntés."""
    return get_most_borrowed_books(db, limit=limit)


@router.get("/active-users", response_model=list[ActiveUserItem])
def active_users(limit: int = 10, db: Session = FastAPIDepends(get_db)) -> list[ActiveUserItem]:
    """Utilisateurs les plus actifs."""
    return get_most_active_users(db, limit=limit)


@router.get("/overdue-stats", response_model=OverdueStats)
def overdue_stats(db: Session = FastAPIDepends(get_db)) -> OverdueStats:
    """Statistiques des retards."""
    return get_overdue_stats(db)


@router.get("/summary", response_model=ReportSummary)
def summary(db: Session = FastAPIDepends(get_db)) -> ReportSummary:
    """Résumé général (tableau de bord)."""
    return get_summary(db)

