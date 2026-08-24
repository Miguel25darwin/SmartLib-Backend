"""
Service d'import/export en masse du catalogue (CSV).
Conforme aux "Consignes de Gestion du catalogue".
"""

import csv
import io

from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.dewey_classification import DeweyClassification
from app.models.enums import BookType, LanguagePref
from app.schemas.import_export import ImportResult, ImportRowError

CSV_FIELDNAMES = [
    "id", "title_fr", "title_en", "author", "isbn",
    "publisher", "publication_year", "dewey_code", "dewey_label_fr",
    "type", "language", "cover_url",
]

REQUIRED_FIELDS_FOR_IMPORT = ["author", "type"]


def export_books_to_csv(db: Session) -> str:
    """Exporte l'integralite du catalogue au format CSV, avec le libelle Dewey lisible."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()

    books = db.query(Book).order_by(Book.id).all()
    for book in books:
        dewey_code = ""
        dewey_label_fr = ""
        if book.dewey_id is not None:
            dewey = db.get(DeweyClassification, book.dewey_id)
            if dewey is not None:
                dewey_code = dewey.code
                dewey_label_fr = dewey.label_fr

        writer.writerow({
            "id": book.id,
            "title_fr": book.title_fr or "",
            "title_en": book.title_en or "",
            "author": book.author,
            "isbn": book.isbn or "",
            "publisher": book.publisher or "",
            "publication_year": book.publication_year or "",
            "dewey_code": dewey_code,
            "dewey_label_fr": dewey_label_fr,
            "type": book.type.value,
            "language": book.language.value,
            "cover_url": book.cover_url or "",
        })

    return output.getvalue()


def _parse_row(db: Session, row: dict, row_number: int) -> Book:
    """Convertit une ligne CSV en instance Book. dewey_code (si fourni) est resolu vers dewey_id."""
    for field in REQUIRED_FIELDS_FOR_IMPORT:
        if not row.get(field, "").strip():
            raise ValueError(f"Champ obligatoire manquant : '{field}'")

    try:
        book_type = BookType(row["type"].strip().lower())
    except ValueError as exc:
        raise ValueError(f"type invalide : '{row['type']}' (attendu : 'physical' ou 'digital')") from exc

    language_raw = row.get("language", "fr").strip().lower() or "fr"
    try:
        language = LanguagePref(language_raw)
    except ValueError as exc:
        raise ValueError(f"language invalide : '{language_raw}' (attendu : 'fr' ou 'en')") from exc

    publication_year = None
    if row.get("publication_year", "").strip():
        try:
            publication_year = int(row["publication_year"])
        except ValueError as exc:
            raise ValueError(f"publication_year invalide : '{row['publication_year']}'") from exc

    dewey_id = None
    dewey_code_raw = row.get("dewey_code", "").strip()
    if dewey_code_raw:
        dewey = db.query(DeweyClassification).filter(DeweyClassification.code == dewey_code_raw).first()
        if dewey is None:
            raise ValueError(f"dewey_code '{dewey_code_raw}' introuvable dans le referentiel")
        dewey_id = dewey.id

    return Book(
        title_fr=row.get("title_fr", "").strip() or None,
        title_en=row.get("title_en", "").strip() or None,
        author=row["author"].strip(),
        isbn=row.get("isbn", "").strip() or None,
        publisher=row.get("publisher", "").strip() or None,
        publication_year=publication_year,
        dewey_id=dewey_id,
        type=book_type,
        language=language,
        cover_url=row.get("cover_url", "").strip() or None,
    )


def import_books_from_csv(db: Session, csv_content: str) -> ImportResult:
    """Importe des livres en masse depuis un contenu CSV."""
    reader = csv.DictReader(io.StringIO(csv_content))
    errors: list[ImportRowError] = []
    created_count = 0
    total_rows = 0

    for row_number, row in enumerate(reader, start=2):
        total_rows += 1
        try:
            book = _parse_row(db, row, row_number)
            if book.isbn:
                existing = db.query(Book).filter(Book.isbn == book.isbn).first()
                if existing is not None:
                    raise ValueError(f"ISBN '{book.isbn}' deja present au catalogue")
            db.add(book)
            db.flush()
            created_count += 1
        except Exception as exc:
            db.rollback()
            errors.append(ImportRowError(row_number=row_number, error=str(exc), raw_data=dict(row)))

    db.commit()

    return ImportResult(
        total_rows=total_rows,
        created_count=created_count,
        skipped_count=len(errors),
        errors=errors,
    )
