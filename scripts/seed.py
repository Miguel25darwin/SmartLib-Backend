"""
Script de seed SmartLib.

Peuple la base de donnees avec des comptes de test et un catalogue de
demonstration, pour que les collaborateurs (frontend Flutter, tests manuels)
disposent immediatement de donnees exploitables sans les creer a la main.

Usage :
    python scripts/seed.py

Le script est idempotent au niveau des comptes (ne recree pas un utilisateur
si l'email existe deja), mais AJOUTE toujours de nouveaux livres/exemplaires
a chaque execution (pas de verification de doublon sur le catalogue) - a
executer une seule fois sur une base fraiche pour un resultat propre.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models.book import Book
from app.models.copy import Copy
from app.models.enums import BookType, LanguagePref, UserRole
from app.models.user import User, generate_card_number
from app.core.security import hash_password

SEED_PASSWORD = "SmartLib2026!"

USERS_TO_SEED = [
    {"full_name": "Admin Systeme", "email": "admin@smartlib.cm", "role": UserRole.ADMIN},
    {"full_name": "Marie Bibliothecaire", "email": "bibliothecaire@smartlib.cm", "role": UserRole.LIBRARIAN},
    {"full_name": "Paul Enseignant", "email": "enseignant@smartlib.cm", "role": UserRole.LECTURER},
    {"full_name": "Sophie Personnel", "email": "personnel@smartlib.cm", "role": UserRole.STAFF},
    {"full_name": "Alice Etudiante", "email": "etudiant1@smartlib.cm", "role": UserRole.STUDENT},
    {"full_name": "Bob Etudiant", "email": "etudiant2@smartlib.cm", "role": UserRole.STUDENT},
    {"full_name": "Claire Etudiante", "email": "etudiant3@smartlib.cm", "role": UserRole.STUDENT},
]

BOOKS_TO_SEED = [
    {
        "title_fr": "Introduction a l'Algorithmique", "title_en": "Introduction to Algorithms",
        "author": "T. Cormen", "isbn": "978-2-1000-0001-1", "publisher": "MIT Press",
        "publication_year": 2022, "dewey_classification": "005.1",
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 3,
    },
    {
        "title_fr": "Bases de Donnees Relationnelles", "title_en": "Relational Databases",
        "author": "S. Fotso", "isbn": "978-2-1000-0002-2", "publisher": "Editions ABC",
        "publication_year": 2023, "dewey_classification": "005.74",
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 2,
    },
    {
        "title_fr": "Securite Informatique et Cybersecurite", "title_en": "Cybersecurity Fundamentals",
        "author": "L. Moyou", "isbn": "978-2-1000-0003-3", "publisher": "Editions XYZ",
        "publication_year": 2026, "dewey_classification": "005.8",
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 4,
    },
    {
        "title_fr": "Philosophie des Sciences", "title_en": "Philosophy of Science",
        "author": "M. Ateba", "isbn": "978-2-1000-0004-4", "publisher": "Presses Universitaires",
        "publication_year": 2021, "dewey_classification": "100",
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 2,
    },
    {
        "title_fr": "Introduction a l'Economie", "title_en": "Principles of Economics",
        "author": "R. Nguemo", "isbn": "978-2-1000-0005-5", "publisher": "Editions ABC",
        "publication_year": 2024, "dewey_classification": "330",
        "type": BookType.DIGITAL, "language": LanguagePref.FR, "copies_count": 0,
    },
]


def seed_users(db) -> dict[str, User]:
    """Cree les comptes de test s'ils n'existent pas deja. Retourne un dict email -> User."""
    created = {}
    for entry in USERS_TO_SEED:
        existing = db.query(User).filter(User.email == entry["email"]).first()
        if existing is not None:
            print(f"  [existe deja] {entry['email']} ({entry['role'].value})")
            created[entry["email"]] = existing
            continue

        user = User(
            full_name=entry["full_name"],
            email=entry["email"],
            password_hash=hash_password(SEED_PASSWORD),
            role=entry["role"],
            language_pref=LanguagePref.FR,
            card_number=generate_card_number(entry["role"]),
        )
        db.add(user)
        db.flush()
        print(f"  [cree] {entry['email']} ({entry['role'].value}) - carte {user.card_number}")
        created[entry["email"]] = user

    db.commit()
    return created


def seed_catalogue(db) -> None:
    """Cree les livres de demonstration avec leurs exemplaires physiques (QR auto-generes)."""
    for entry in BOOKS_TO_SEED:
        existing = db.query(Book).filter(Book.isbn == entry["isbn"]).first()
        if existing is not None:
            print(f"  [existe deja] {entry['title_fr']}")
            continue

        copies_count = entry.pop("copies_count")
        book = Book(**entry)
        db.add(book)
        db.flush()

        for i in range(copies_count):
            copy = Copy(book_id=book.id, location=f"RAY-{book.id:02d}")
            db.add(copy)

        db.flush()
        print(f"  [cree] {book.title_fr} - {copies_count} exemplaire(s), ISBN {book.isbn}")

    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        print("=== Seed des utilisateurs ===")
        seed_users(db)

        print("")
        print("=== Seed du catalogue ===")
        seed_catalogue(db)

        print("")
        print("=== Termine ===")
        print(f"Mot de passe commun a tous les comptes de test : {SEED_PASSWORD}")
        print("")
        print("Comptes disponibles :")
        for entry in USERS_TO_SEED:
            print(f"  {entry['role'].value:12s} | {entry['email']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
