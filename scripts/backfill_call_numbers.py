"""
Script one-off : genere les cotes de rangement (call_number) manquantes.

Contexte : le seed et certaines creations directes ne renseignaient pas la cote
des exemplaires physiques. La chaine de localisation
`Livre -> Dewey -> Exemplaire -> Cote -> Emplacement` etait donc incomplete :
impossible, pour un bibliothecaire, de ranger/retrouver l'ouvrage dans l'ordre
du rayon.

Genere une cote `<code Dewey> <code auteur 3 lettres>[-<n>]` pour chaque
exemplaire qui n'en a pas (ex: "005 COR" ou "005 COR-1"/"005 COR-2").
Les cotes deja renseignees ne sont jamais ecrasees. Idempotent.

Usage :
    python scripts/backfill_call_numbers.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func

from app.db.session import SessionLocal
from app.models.book import Book
from app.models.copy import Copy
from app.services.copy_service import _resolve_dewey_code, build_call_number


def backfill(db) -> int:
    """Renseigne la cote de chaque exemplaire qui n'en a pas. Retourne le total."""
    updated = 0
    for book in db.query(Book).order_by(Book.id).all():
        copies = db.query(Copy).filter(Copy.book_id == book.id).order_by(Copy.id).all()
        total = len(copies)
        if total == 0:
            continue
        dewey_code = _resolve_dewey_code(db, book)
        for index, copy in enumerate(copies, start=1):
            if copy.call_number:
                continue
            copy.call_number = build_call_number(
                dewey_code, book.author, index=index, total=total
            )
            updated += 1
    db.commit()
    return updated


def main() -> None:
    db = SessionLocal()
    try:
        print("=== Backfill des cotes de rangement ===")
        updated = backfill(db)
        print(f"  {updated} cote(s) generee(s).")

        total = db.query(Copy).count()
        without = db.query(Copy).filter(Copy.call_number.is_(None)).count()
        print(f"\nExemplaires : {total} | sans cote : {without}")

        dups = (
            db.query(Copy.call_number, func.count(Copy.id))
            .filter(Copy.call_number.isnot(None))
            .group_by(Copy.call_number)
            .having(func.count(Copy.id) > 1)
            .all()
        )
        print(f"Cotes en double : {len(dups)}")
        for code, count in dups:
            print(f"  {code} x{count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
