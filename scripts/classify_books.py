"""
Script one-off : associe les livres existants a leur categorie Dewey.

Contexte : le seed historique utilisait des codes Dewey fins (ex: "005.1",
"170", "301"...) absents du referentiel `dewey_classifications` (qui ne contient
que les classes principales et quelques divisions : "005", "100", "300"...).
L'association `dewey_id` echouait donc silencieusement et les livres restaient
non classes -> la representation Dewey de l'admin affichait des compteurs a 0.

Ce script rejoue l'association a partir de `BOOKS_TO_SEED` (source de verite),
en se basant sur l'ISBN (stable). Il est idempotent : relancable sans risque.

Usage :
    python scripts/classify_books.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models.book import Book
from app.models.dewey_classification import DeweyClassification
from scripts.seed import BOOKS_TO_SEED

MAIN_CLASSES = ["000", "100", "200", "300", "400", "500", "600", "700", "800", "900"]


def classify(db) -> None:
    """Associe chaque livre (par ISBN) a la categorie Dewey de BOOKS_TO_SEED."""
    updated = skipped = missing = 0

    for entry in BOOKS_TO_SEED:
        code = entry.get("dewey_code")
        if not code:
            continue

        book = db.query(Book).filter(Book.isbn == entry["isbn"]).first()
        if book is None:
            print(f"  [absent]    {entry['title_fr']} (ISBN {entry['isbn']})")
            missing += 1
            continue

        dewey = (
            db.query(DeweyClassification)
            .filter(DeweyClassification.code == code)
            .first()
        )
        if dewey is None:
            print(f"  [introuvable] Dewey {code} pour {entry['title_fr']}")
            missing += 1
            continue

        if book.dewey_id == dewey.id:
            skipped += 1
            continue

        book.dewey_id = dewey.id
        updated += 1
        print(f"  [ok]        {book.title_fr} -> {code} ({dewey.label_fr})")

    db.commit()
    print(f"\nBilan : {updated} mis a jour, {skipped} deja corrects, {missing} ignores.")


def print_distribution(db) -> None:
    """Affiche le nombre de livres par classe Dewey principale."""
    print("=== Repartition par classe principale ===")
    total = 0
    for code in MAIN_CLASSES:
        count = (
            db.query(Book)
            .join(DeweyClassification, Book.dewey_id == DeweyClassification.id)
            .filter(DeweyClassification.code.like(f"{code[0]}%"))
            .count()
        )
        total += count
        print(f"  {code} : {count}")
    unclassified = db.query(Book).filter(Book.dewey_id.is_(None)).count()
    print(f"  (non classes) : {unclassified}")
    print(f"  TOTAL classes : {total}")


def main() -> None:
    db = SessionLocal()
    try:
        print("=== Classification Dewey des livres ===")
        classify(db)
        print("")
        print_distribution(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
