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
from app.services.copy_service import build_call_number

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
    # Informatique (000)
    {
        "title_fr": "Introduction a l'Algorithmique", "title_en": "Introduction to Algorithms",
        "author": "T. Cormen", "isbn": "978-2-1000-0001-1", "publisher": "MIT Press",
        "publication_year": 2022,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 3,
        "dewey_code": "005",
    },
    {
        "title_fr": "Bases de Donnees Relationnelles", "title_en": "Relational Databases",
        "author": "S. Fotso", "isbn": "978-2-1000-0002-2", "publisher": "Editions ABC",
        "publication_year": 2023,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 2,
        "dewey_code": "005",
    },
    {
        "title_fr": "Securite Informatique et Cybersecurite", "title_en": "Cybersecurity Fundamentals",
        "author": "L. Moyou", "isbn": "978-2-1000-0003-3", "publisher": "Editions XYZ",
        "publication_year": 2026,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 4,
        "dewey_code": "005",
    },
    {
        "title_fr": "Python pour Data Science", "title_en": "Python for Data Science",
        "author": "J. VanderPlas", "isbn": "978-2-1000-0006-6", "publisher": "O'Reilly",
        "publication_year": 2023,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 3,
        "dewey_code": "005",
    },
    {
        "title_fr": "Machine Learning Practice", "title_en": "Machine Learning Practice",
        "author": "A. Geron", "isbn": "978-2-1000-0007-7", "publisher": "O'Reilly",
        "publication_year": 2024,
        "type": BookType.DIGITAL, "language": LanguagePref.EN, "copies_count": 0,
        "dewey_code": "006",
    },
    # Philosophie (100)
    {
        "title_fr": "Philosophie des Sciences", "title_en": "Philosophy of Science",
        "author": "M. Ateba", "isbn": "978-2-1000-0004-4", "publisher": "Presses Universitaires",
        "publication_year": 2021,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 2,
        "dewey_code": "100",
    },
    {
        "title_fr": "Ethique Contemporaine", "title_en": "Contemporary Ethics",
        "author": "P. Singer", "isbn": "978-2-1000-0008-8", "publisher": "Presses Universitaires",
        "publication_year": 2022,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 2,
        "dewey_code": "100",
    },
    {
        "title_fr": "Histoire de la Philosophie", "title_en": "History of Philosophy",
        "author": "B. Russell", "isbn": "978-2-1000-0009-9", "publisher": "Editions ABC",
        "publication_year": 2020,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 3,
        "dewey_code": "100",
    },
    # Sciences Sociales (300)
    {
        "title_fr": "Introduction a l'Economie", "title_en": "Principles of Economics",
        "author": "R. Nguemo", "isbn": "978-2-1000-0005-5", "publisher": "Editions ABC",
        "publication_year": 2024,
        "type": BookType.DIGITAL, "language": LanguagePref.FR, "copies_count": 0,
        "dewey_code": "330",
    },
    {
        "title_fr": "Sociologie Generale", "title_en": "General Sociology",
        "author": "E. Durkheim", "isbn": "978-2-1000-0010-0", "publisher": "Presses Universitaires",
        "publication_year": 2021,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 2,
        "dewey_code": "300",
    },
    {
        "title_fr": "Politique Internationale", "title_en": "International Politics",
        "author": "H. Morgenthau", "isbn": "978-2-1000-0011-1", "publisher": "Editions XYZ",
        "publication_year": 2023,
        "type": BookType.PHYSICAL, "language": LanguagePref.EN, "copies_count": 3,
        "dewey_code": "300",
    },
    # Langues (400)
    {
        "title_fr": "Grammaire Francaise", "title_en": "French Grammar",
        "author": "M. Grevisse", "isbn": "978-2-1000-0012-2", "publisher": "Editions ABC",
        "publication_year": 2022,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 4,
        "dewey_code": "400",
    },
    {
        "title_fr": "English Linguistics", "title_en": "English Linguistics",
        "author": "N. Chomsky", "isbn": "978-2-1000-0013-3", "publisher": "Cambridge Press",
        "publication_year": 2021,
        "type": BookType.PHYSICAL, "language": LanguagePref.EN, "copies_count": 2,
        "dewey_code": "400",
    },
    # Sciences (500)
    {
        "title_fr": "Physique Quantique", "title_en": "Quantum Physics",
        "author": "R. Feynman", "isbn": "978-2-1000-0014-4", "publisher": "MIT Press",
        "publication_year": 2023,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 2,
        "dewey_code": "530",
    },
    {
        "title_fr": "Chimie Organique", "title_en": "Organic Chemistry",
        "author": "J. McMurry", "isbn": "978-2-1000-0015-5", "publisher": "Editions ABC",
        "publication_year": 2022,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 3,
        "dewey_code": "540",
    },
    {
        "title_fr": "Biologie Cellulaire", "title_en": "Cell Biology",
        "author": "B. Alberts", "isbn": "978-2-1000-0016-6", "publisher": "Garland Science",
        "publication_year": 2024,
        "type": BookType.PHYSICAL, "language": LanguagePref.EN, "copies_count": 2,
        "dewey_code": "570",
    },
    # Technologie (600)
    {
        "title_fr": "Medecine Interne", "title_en": "Internal Medicine",
        "author": "H. Harrison", "isbn": "978-2-1000-0017-7", "publisher": "McGraw-Hill",
        "publication_year": 2023,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 2,
        "dewey_code": "610",
    },
    {
        "title_fr": "Genie Civil", "title_en": "Civil Engineering",
        "author": "J. Smith", "isbn": "978-2-1000-0018-8", "publisher": "Wiley",
        "publication_year": 2022,
        "type": BookType.PHYSICAL, "language": LanguagePref.EN, "copies_count": 3,
        "dewey_code": "620",
    },
    # Arts (700)
    {
        "title_fr": "Histoire de l'Art", "title_en": "Art History",
        "author": "E. Gombrich", "isbn": "978-2-1000-0019-9", "publisher": "Phaidon",
        "publication_year": 2021,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 2,
        "dewey_code": "700",
    },
    {
        "title_fr": "Theatre Contemporain", "title_en": "Contemporary Theater",
        "author": "A. Miller", "isbn": "978-2-1000-0020-0", "publisher": "Penguin",
        "publication_year": 2023,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 2,
        "dewey_code": "700",
    },
    # Litterature (800)
    {
        "title_fr": "Litterature Francaise", "title_en": "French Literature",
        "author": "V. Hugo", "isbn": "978-2-1000-0021-1", "publisher": "Gallimard",
        "publication_year": 2020,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 3,
        "dewey_code": "840",
    },
    {
        "title_fr": "English Poetry", "title_en": "English Poetry",
        "author": "W. Shakespeare", "isbn": "978-2-1000-0022-2", "publisher": "Oxford Press",
        "publication_year": 2021,
        "type": BookType.PHYSICAL, "language": LanguagePref.EN, "copies_count": 2,
        "dewey_code": "820",
    },
    # Histoire (900)
    {
        "title_fr": "Histoire Mondiale", "title_en": "World History",
        "author": "J.M. Roberts", "isbn": "978-2-1000-0023-3", "publisher": "Penguin",
        "publication_year": 2022,
        "type": BookType.PHYSICAL, "language": LanguagePref.FR, "copies_count": 2,
        "dewey_code": "900",
    },
    {
        "title_fr": "Geographie Humaine", "title_en": "Human Geography",
        "author": "H. de Blij", "isbn": "978-2-1000-0024-4", "publisher": "Wiley",
        "publication_year": 2023,
        "type": BookType.PHYSICAL, "language": LanguagePref.EN, "copies_count": 2,
        "dewey_code": "900",
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
    from app.models.dewey_classification import DeweyClassification
    
    for entry in BOOKS_TO_SEED:
        existing = db.query(Book).filter(Book.isbn == entry["isbn"]).first()
        if existing is not None:
            print(f"  [existe deja] {entry['title_fr']}")
            continue

        copies_count = entry.pop("copies_count")
        dewey_code = entry.pop("dewey_code", None)
        
        book = Book(**entry)
        db.add(book)
        db.flush()

        # Lier le livre à la catégorie Dewey appropriée
        if dewey_code:
            dewey_cat = db.query(DeweyClassification).filter(
                DeweyClassification.code == dewey_code
            ).first()
            if dewey_cat:
                book.dewey_id = dewey_cat.id
                print(f"  [lie] {book.title_fr} -> Dewey {dewey_code}")
            else:
                print(f"  [avertissement] Categorie Dewey {dewey_code} non trouvee pour {book.title_fr}")

        for i in range(copies_count):
            copy = Copy(
                book_id=book.id,
                location=f"RAY-{book.id:02d}",
                call_number=build_call_number(
                    dewey_code, book.author, index=i + 1, total=copies_count
                ),
            )
            db.add(copy)

        db.flush()
        print(f"  [cree] {book.title_fr} - {copies_count} exemplaire(s), ISBN {book.isbn}")

    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        print("=== Seed du referentiel Dewey ===")
        from scripts.seed_dewey import seed_dewey
        seed_dewey(db)

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
