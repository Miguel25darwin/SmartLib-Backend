"""Logique metier du module Recommandations d'ouvrages.

Une recommandation relie un cours (code + intitule), un ouvrage du catalogue
et le membre du personnel qui l'a formulee. Le statut de couverture est calcule
en temps reel a partir des exemplaires physiques du catalogue.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.book import Book
from app.models.enums import CopyStatus, UserRole
from app.models.recommendation import BookRecommendation
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationCreate,
    RecommendationRead,
    RecommendationUpdate,
)


class RecommendationNotFoundError(Exception):
    pass


class RecommendationForbiddenError(Exception):
    pass


class DuplicateRecommendationError(Exception):
    pass


class RecommendationBookNotFoundError(Exception):
    pass


MANAGER_ROLES = (UserRole.LIBRARIAN, UserRole.ADMIN)


def _book_title(book: Book) -> str:
    return book.title_fr or book.title_en or f"Livre #{book.id}"


def _to_read(
    recommendation: BookRecommendation,
    current_user: User,
) -> RecommendationRead:
    book = recommendation.book
    copies = book.copies if book is not None else []
    total_copies = len(copies)
    available_copies = sum(1 for copy in copies if copy.status == CopyStatus.AVAILABLE)
    missing_copies = max(recommendation.required_quantity - available_copies, 0)
    is_owner = recommendation.lecturer_id == current_user.id
    can_delete = is_owner or current_user.role in MANAGER_ROLES

    return RecommendationRead(
        id=recommendation.id,
        course_code=recommendation.course_code,
        course_title=recommendation.course_title,
        lecturer_id=recommendation.lecturer_id,
        lecturer_name=recommendation.lecturer.full_name if recommendation.lecturer else "—",
        book_id=recommendation.book_id,
        book_title=_book_title(book) if book is not None else f"Livre #{recommendation.book_id}",
        book_author=book.author if book is not None else "—",
        book_type=book.type.value if book is not None else "physical",
        required_quantity=recommendation.required_quantity,
        available_copies=available_copies,
        total_copies=total_copies,
        missing_copies=missing_copies,
        is_sufficient=missing_copies == 0,
        is_owner=is_owner,
        can_delete=can_delete,
        created_at=recommendation.created_at,
    )


def _base_query():
    return select(BookRecommendation).options(
        selectinload(BookRecommendation.book).selectinload(Book.copies),
        selectinload(BookRecommendation.lecturer),
    )


def list_recommendations(
    db: Session,
    current_user: User,
    *,
    mine: bool = False,
    course_code: str | None = None,
) -> list[RecommendationRead]:
    query = _base_query()
    if mine:
        query = query.where(BookRecommendation.lecturer_id == current_user.id)
    if course_code:
        query = query.where(
            BookRecommendation.course_code == course_code.strip().upper()
        )
    query = query.order_by(
        BookRecommendation.course_code,
        BookRecommendation.course_title,
        BookRecommendation.id,
    )
    recommendations = db.scalars(query).all()
    return [_to_read(recommendation, current_user) for recommendation in recommendations]


def get_recommendation(
    db: Session, recommendation_id: int, current_user: User
) -> RecommendationRead:
    recommendation = db.scalar(
        _base_query().where(BookRecommendation.id == recommendation_id)
    )
    if recommendation is None:
        raise RecommendationNotFoundError("Recommandation introuvable.")
    return _to_read(recommendation, current_user)


def _get_book(db: Session, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise RecommendationBookNotFoundError(
            f"Livre #{book_id} introuvable dans le catalogue."
        )
    return book


def create_recommendation(
    db: Session, payload: RecommendationCreate, current_user: User
) -> RecommendationRead:
    _get_book(db, payload.book_id)

    duplicate = db.scalar(
        select(BookRecommendation).where(
            BookRecommendation.course_code == payload.course_code,
            BookRecommendation.book_id == payload.book_id,
            BookRecommendation.lecturer_id == current_user.id,
        )
    )
    if duplicate is not None:
        raise DuplicateRecommendationError(
            "Cet ouvrage est deja recommande par vous pour ce cours."
        )

    recommendation = BookRecommendation(
        course_code=payload.course_code,
        course_title=payload.course_title,
        lecturer_id=current_user.id,
        book_id=payload.book_id,
        required_quantity=payload.required_quantity,
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return get_recommendation(db, recommendation.id, current_user)


def _get_manageable(
    db: Session, recommendation_id: int, current_user: User
) -> BookRecommendation:
    recommendation = db.scalars(
        _base_query().where(BookRecommendation.id == recommendation_id)
    ).first()
    if recommendation is None:
        raise RecommendationNotFoundError("Recommandation introuvable.")
    if (
        recommendation.lecturer_id != current_user.id
        and current_user.role not in MANAGER_ROLES
    ):
        raise RecommendationForbiddenError(
            "Seul l'auteur de la recommandation ou un gestionnaire peut la modifier."
        )
    return recommendation


def update_recommendation(
    db: Session,
    recommendation_id: int,
    payload: RecommendationUpdate,
    current_user: User,
) -> RecommendationRead:
    recommendation = _get_manageable(db, recommendation_id, current_user)

    if payload.book_id is not None and payload.book_id != recommendation.book_id:
        _get_book(db, payload.book_id)
        recommendation.book_id = payload.book_id
    if payload.course_code is not None:
        recommendation.course_code = payload.course_code
    if payload.course_title is not None:
        recommendation.course_title = payload.course_title
    if payload.required_quantity is not None:
        recommendation.required_quantity = payload.required_quantity

    duplicate = db.scalar(
        select(BookRecommendation).where(
            BookRecommendation.id != recommendation.id,
            BookRecommendation.course_code == recommendation.course_code,
            BookRecommendation.book_id == recommendation.book_id,
            BookRecommendation.lecturer_id == recommendation.lecturer_id,
        )
    )
    if duplicate is not None:
        raise DuplicateRecommendationError(
            "Cet ouvrage est deja recommande par vous pour ce cours."
        )

    db.commit()
    db.refresh(recommendation)
    return get_recommendation(db, recommendation.id, current_user)


def delete_recommendation(
    db: Session, recommendation_id: int, current_user: User
) -> None:
    recommendation = _get_manageable(db, recommendation_id, current_user)
    db.delete(recommendation)
    db.commit()
