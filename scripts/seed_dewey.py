"""
Script de seed du referentiel Dewey (MDS - Systeme Decimal de Melvil Dewey).

IMPORTANT (contrainte legale) : contient uniquement les 10 classes principales
(fournies par l'etablissement via le document "Consignes de Gestion du catalogue")
et une selection de divisions courantes formulees en termes generaux et factuels
par l'equipe SmartLib. Aucun contenu n'est copie d'une edition sous licence OCLC.

Usage :
    python scripts/seed_dewey.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models.dewey_classification import DeweyClassification

# Les 10 classes principales (source : document client "Consignes de Gestion du catalogue")
MAIN_CLASSES = [
    ("000", "Informatique, information et ouvrages generaux", "Computer science, information and general works"),
    ("100", "Philosophie et psychologie", "Philosophy and psychology"),
    ("200", "Religion", "Religion"),
    ("300", "Sciences sociales", "Social sciences"),
    ("400", "Langues", "Language"),
    ("500", "Sciences naturelles et mathematiques", "Natural sciences and mathematics"),
    ("600", "Technologie et sciences appliquees", "Technology and applied sciences"),
    ("700", "Arts et loisirs", "Arts and recreation"),
    ("800", "Litterature", "Literature"),
    ("900", "Histoire et geographie", "History and geography"),
]

# Divisions courantes, formulees en termes generaux par l'equipe SmartLib
# (etiquettes courtes factuelles, pas de notes explicatives issues d'une edition sous licence)
DIVISIONS = {
    "000": [("004", "Informatique", "Computer science"), ("005", "Programmation et logiciels", "Programming and software"), ("006", "Intelligence artificielle et methodes speciales", "AI and special computing")],
    "500": [("510", "Mathematiques", "Mathematics"), ("520", "Astronomie", "Astronomy"), ("530", "Physique", "Physics"), ("540", "Chimie", "Chemistry"), ("570", "Sciences de la vie et biologie", "Life sciences and biology")],
    "600": [("610", "Medecine et sante", "Medicine and health"), ("620", "Ingenierie", "Engineering"), ("630", "Agriculture", "Agriculture"), ("650", "Gestion et administration", "Management and administration")],
    "300": [("330", "Economie", "Economics"), ("340", "Droit", "Law"), ("370", "Education", "Education")],
    "800": [("840", "Litterature francaise", "French literature"), ("820", "Litterature anglaise", "English literature")],
}


def seed_dewey(db) -> None:
    code_to_id: dict[str, int] = {}

    print("=== Seed des classes principales ===")
    for code, label_fr, label_en in MAIN_CLASSES:
        existing = db.query(DeweyClassification).filter(DeweyClassification.code == code).first()
        if existing is not None:
            print(f"  [existe deja] {code} - {existing.label_fr}")
            code_to_id[code] = existing.id
            continue

        classification = DeweyClassification(
            code=code, label_fr=label_fr, label_en=label_en, parent_id=None, level=0,
        )
        db.add(classification)
        db.flush()
        code_to_id[code] = classification.id
        print(f"  [cree] {code} - {label_fr}")

    db.commit()

    print("")
    print("=== Seed des divisions ===")
    for parent_code, divisions in DIVISIONS.items():
        parent_id = code_to_id.get(parent_code)
        if parent_id is None:
            print(f"  [ignore] parent {parent_code} introuvable")
            continue

        for code, label_fr, label_en in divisions:
            existing = db.query(DeweyClassification).filter(DeweyClassification.code == code).first()
            if existing is not None:
                print(f"  [existe deja] {code} - {existing.label_fr}")
                continue

            classification = DeweyClassification(
                code=code, label_fr=label_fr, label_en=label_en, parent_id=parent_id, level=1,
            )
            db.add(classification)
            print(f"  [cree] {code} - {label_fr} (parent: {parent_code})")

    db.commit()
    print("")
    print("=== Termine ===")


def main() -> None:
    db = SessionLocal()
    try:
        seed_dewey(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
