"""Schémas Pydantic pour les réponses du module Rapports et Analyses."""

from pydantic import BaseModel


class MostBorrowedItem(BaseModel):
    book_id: int
    title: str
    author: str
    borrow_count: int


class ActiveUserItem(BaseModel):
    user_id: str
    full_name: str
    email: str
    loan_count: int


class OverdueStats(BaseModel):
    total_overdue: int
    total_active: int
    overdue_rate_percent: float


class ReportSummary(BaseModel):
    """Tableau de bord general (GET /reports/summary)."""
    total_books: int
    total_copies: int
    copies_available: int
    copies_borrowed: int
    total_users: int
    total_loans_active: int
    total_loans_overdue: int
    total_loans_returned: int
