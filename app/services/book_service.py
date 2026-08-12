"""
Couche service pour l'entité Book (catalogue).
Gère la recherche avec filtres et le calcul des compteurs d'exemplaires
(copies_total / copies_available), non stockés en base mais calculés à la volée.
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.copy import Copy
from app.models.enums import BookType, CopyStatus, LanguagePref
from app.schemas.book import BookCreate, BookUpdate


class BookNotFoundError(Exception):
    """Levée quand un livre demandé n'existe pas."""
    pass


class IsbnAlreadyExistsError(Exception):
    """Levée quand on tente de créer un livre avec un ISBN déjà utilisé."""
    pass


def _with_copy_counts(db: Session, book: Book) -> Book:
    """
    Attache dynamiquement copies_total / copies_available au livre
    (attributs non-colonnes, lus par BookRead via from_attributes).
    """
    copies = db.query(Copy).filter(Copy.book_id == book.id).all()
    book.copies_total = len(copies)
    book.copies_available = sum(1 for c in copies if c.status == CopyStatus.AVAILABLE)
    return book


def get_book(db: Session, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise BookNotFoundError(f"Livre id={book_id} introuvable.")
    return _with_copy_counts(db, book)


def search_books(
    db: Session,
    search: str | None = None,
    book_type: BookType | None = None,
    language: LanguagePref | None = None,
    available_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> list[Book]:
    """
    Recherche avec filtres — reflète GET /books?search=&type=&language=&available=
    du Cahier d'Architecture §6.2.
    """
    query = db.query(Book)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Book.title_fr.ilike(pattern),
                Book.title_en.ilike(pattern),
                Book.author.ilike(pattern),
            )
        )
    if book_type is not None:
        query = query.filter(Book.type == book_type)
    if language is not None:
        query = query.filter(Book.language == language)

    books = query.offset(skip).limit(limit).all()
    books = [_with_copy_counts(db, b) for b in books]

    if available_only:
        books = [b for b in books if b.copies_available > 0]

    return books


def create_book(db: Session, book_in: BookCreate) -> Book:
    if book_in.isbn:
        existing = db.query(Book).filter(Book.isbn == book_in.isbn).first()
        if existing is not None:
            raise IsbnAlreadyExistsError(f"ISBN {book_in.isbn} déjà présent au catalogue.")

    book = Book(**book_in.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return _with_copy_counts(db, book)


def update_book(db: Session, book_id: int, book_update: BookUpdate) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise BookNotFoundError(f"Livre id={book_id} introuvable.")

    update_data = book_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return _with_copy_counts(db, book)


def delete_book(db: Session, book_id: int) -> None:
    book = db.get(Book, book_id)
    if book is None:
        raise BookNotFoundError(f"Livre id={book_id} introuvable.")
    db.delete(book)
    db.commit()
