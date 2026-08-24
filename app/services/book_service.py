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
from app.models.dewey_classification import DeweyClassification
from app.services.dewey_service import get_descendants


class BookNotFoundError(Exception):
    """Levée quand un livre demandé n'existe pas."""
    pass


class IsbnAlreadyExistsError(Exception):
    """Levée quand on tente de créer un livre avec un ISBN déjà utilisé."""
    pass


class DeweyIdInvalidError(Exception):
    """Levee quand le dewey_id fourni ne correspond a aucune categorie existante."""
    pass


class DeweyRootNotFoundError(Exception):
    """Levee quand le code racine Dewey fourni n'existe pas."""
    pass


class BookInUseError(Exception):
    """Levee quand un livre ne peut pas être supprimé car il est référencé par des emprunts."""
    pass


class BookHasLoanHistoryError(Exception):
    pass


def _validate_dewey_id(db: Session, dewey_id: int | None) -> None:
    """Verifie que le dewey_id fourni existe reellement dans le referentiel."""
    if dewey_id is None:
        return
    dewey = db.get(DeweyClassification, dewey_id)
    if dewey is None:
        raise DeweyIdInvalidError(f"Categorie Dewey id={dewey_id} introuvable dans le referentiel.")


def _with_copy_counts(db: Session, book: Book) -> Book:
    """
    Attache dynamiquement copies_total / copies_available / infos Dewey lisibles
    au livre (attributs non-colonnes, lus par BookRead via from_attributes).
    """
    copies = db.query(Copy).filter(Copy.book_id == book.id).all()
    book.copies_total = len(copies)
    book.copies_available = sum(1 for c in copies if c.status == CopyStatus.AVAILABLE)

    if book.dewey_id is not None:
        dewey = db.get(DeweyClassification, book.dewey_id)
        if dewey is not None:
            book.dewey_code = dewey.code
            book.dewey_label_fr = dewey.label_fr
            book.dewey_label_en = dewey.label_en
            book.dewey_label = dewey.label_fr  # libelle unifie pour Flutter
    else:
        book.dewey_code = None
        book.dewey_label_fr = None
        book.dewey_label_en = None
        book.dewey_label = None

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
    dewey_category_id: int | None = None,
    dewey_root: str | None = None,
    available_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> list[Book]:
    """
    Recherche avec filtres — reflète GET /books?search=&type=&language=&dewey_category_id=&available=
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
    if dewey_category_id is not None:
        query = query.filter(Book.dewey_id == dewey_category_id)
    if dewey_root:
        root = (
            db.query(DeweyClassification)
            .filter(DeweyClassification.code == dewey_root)
            .first()
        )
        if root is None:
            raise DeweyRootNotFoundError(
                f"Racine Dewey '{dewey_root}' introuvable dans le referentiel."
            )
        descendant_ids = [
            classification.id
            for classification in get_descendants(db, root.id)
        ]
        query = query.filter(Book.dewey_id.in_([root.id, *descendant_ids]))

    if available_only:
        available_book_ids = (
            db.query(Copy.book_id)
            .filter(Copy.status == CopyStatus.AVAILABLE)
            .distinct()
        )
        query = query.filter(Book.id.in_(available_book_ids))

    books = query.offset(skip).limit(limit).all()
    return [_with_copy_counts(db, b) for b in books]


def create_book(db: Session, book_in: BookCreate) -> Book:
    if book_in.isbn:
        existing = db.query(Book).filter(Book.isbn == book_in.isbn).first()
        if existing is not None:
            raise IsbnAlreadyExistsError(f"ISBN {book_in.isbn} déjà présent au catalogue.")

    _validate_dewey_id(db, book_in.dewey_id)

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
    if "dewey_id" in update_data:
        _validate_dewey_id(db, update_data["dewey_id"])

    for field, value in update_data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return _with_copy_counts(db, book)


def delete_book(db: Session, book_id: int) -> None:
    from app.models.loan import Loan

    book = db.get(Book, book_id)
    if book is None:
        raise BookNotFoundError(f"Livre id={book_id} introuvable.")

    copy_ids = [copy.id for copy in db.query(Copy).filter(Copy.book_id == book_id).all()]
    if copy_ids and db.query(Loan).filter(Loan.copy_id.in_(copy_ids)).first() is not None:
        raise BookHasLoanHistoryError(
            f"Livre id={book_id} a un historique d'emprunts, suppression refusee."
        )

    db.delete(book)
    db.commit()
