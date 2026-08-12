"""
Service d'import/export en masse du catalogue (CSV).
Conforme aux "Consignes de Gestion du catalogue" : "Importation/exportation
en masse de infos de catalogue aux formats CSV/Excel".

Le format Excel (.xlsx) n'est pas couvert dans cette version — le CSV s'ouvre
et s'edite nativement dans Excel/LibreOffice, ce qui couvre l'usage reel du
bibliothecaire sans dependance supplementaire (openpyxl) pour le prototype.
"""

import csv
import io

from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.enums import BookType, LanguagePref
from app.schemas.import_export import ImportResult, ImportRowError

# Colonnes attendues dans le CSV, dans cet ordre exact pour l'export
# (l'import accepte l'ordre des colonnes du header, pas une position fixe).
CSV_FIELDNAMES = [
    "id", "title_fr", "title_en", "author", "isbn",
    "publisher", "publication_year", "dewey_classification",
    "type", "language", "cover_url",
]

REQUIRED_FIELDS_FOR_IMPORT = ["author", "type"]


def export_books_to_csv(db: Session) -> str:
    """
    Exporte l'integralite du catalogue au format CSV (chaine de caracteres).
    Utilise io.StringIO pour construire le CSV en memoire, sans fichier temporaire.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()

    books = db.query(Book).order_by(Book.id).all()
    for book in books:
        writer.writerow({
            "id": book.id,
            "title_fr": book.title_fr or "",
            "title_en": book.title_en or "",
            "author": book.author,
            "isbn": book.isbn or "",
            "publisher": book.publisher or "",
            "publication_year": book.publication_year or "",
            "dewey_classification": book.dewey_classification or "",
            "type": book.type.value,
            "language": book.language.value,
            "cover_url": book.cover_url or "",
        })

    return output.getvalue()


def _parse_row(row: dict, row_number: int) -> Book:
    """
    Convertit une ligne CSV en instance Book, ou leve ValueError avec un
    message explicite si la ligne est invalide. Ne touche pas a la base ici :
    validation pure, la transaction est geree par l'appelant (import_books_from_csv).
    """
    for field in REQUIRED_FIELDS_FOR_IMPORT:
        if not row.get(field, "").strip():
            raise ValueError(f"Champ obligatoire manquant : '{field}'")

    try:
        book_type = BookType(row["type"].strip().lower())
    except ValueError as exc:
        raise ValueError(
            f"type invalide : '{row['type']}' (attendu : 'physical' ou 'digital')"
        ) from exc

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

    dewey = row.get("dewey_classification", "").strip() or None
    if dewey is not None:
        prefix = dewey.split(".")[0]
        if not prefix.isdigit() or not (0 <= int(prefix) <= 999):
            raise ValueError(f"dewey_classification invalide : '{dewey}'")

    return Book(
        title_fr=row.get("title_fr", "").strip() or None,
        title_en=row.get("title_en", "").strip() or None,
        author=row["author"].strip(),
        isbn=row.get("isbn", "").strip() or None,
        publisher=row.get("publisher", "").strip() or None,
        publication_year=publication_year,
        dewey_classification=dewey,
        type=book_type,
        language=language,
        cover_url=row.get("cover_url", "").strip() or None,
    )


def import_books_from_csv(db: Session, csv_content: str) -> ImportResult:
    """
    Importe des livres en masse depuis un contenu CSV.

    Comportement volontaire : une ligne invalide n'interrompt PAS tout l'import.
    Elle est consignee dans errors[] et les autres lignes valides sont quand
    meme creees — un bibliothecaire import 500 lignes ne doit pas perdre
    499 lignes correctes a cause d'une seule faute de frappe.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    errors: list[ImportRowError] = []
    created_count = 0
    total_rows = 0

    for row_number, row in enumerate(reader, start=2):  # ligne 1 = header
        total_rows += 1
        try:
            book = _parse_row(row, row_number)
            if book.isbn:
                existing = db.query(Book).filter(Book.isbn == book.isbn).first()
                if existing is not None:
                    raise ValueError(f"ISBN '{book.isbn}' deja present au catalogue")
            db.add(book)
            db.flush()  # detecte les erreurs d'integrite avant le commit final
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