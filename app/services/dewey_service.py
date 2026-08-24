"""Couche service pour le referentiel Dewey."""

from sqlalchemy.orm import Session

from app.models.dewey_classification import DeweyClassification
from app.schemas.dewey import DeweyClassificationCreate


class DeweyNotFoundError(Exception):
    pass


class DeweyParentNotFoundError(Exception):
    pass


class DeweyCodeAlreadyExistsError(Exception):
    pass


def create_classification(db: Session, data: DeweyClassificationCreate) -> DeweyClassification:
    """
    Cree une categorie Dewey. Calcule automatiquement le niveau hierarchique
    a partir du parent (0 si racine, parent.level + 1 sinon).
    """
    existing = db.query(DeweyClassification).filter(DeweyClassification.code == data.code).first()
    if existing is not None:
        raise DeweyCodeAlreadyExistsError(f"Le code Dewey '{data.code}' existe deja.")

    level = 0
    if data.parent_id is not None:
        parent = db.get(DeweyClassification, data.parent_id)
        if parent is None:
            raise DeweyParentNotFoundError(f"Categorie parente id={data.parent_id} introuvable.")
        level = parent.level + 1

    classification = DeweyClassification(
        code=data.code, label_fr=data.label_fr, label_en=data.label_en,
        parent_id=data.parent_id, level=level,
    )
    db.add(classification)
    db.commit()
    db.refresh(classification)
    return classification


def get_classification(db: Session, classification_id: int) -> DeweyClassification:
    classification = db.get(DeweyClassification, classification_id)
    if classification is None:
        raise DeweyNotFoundError(f"Categorie Dewey id={classification_id} introuvable.")
    return classification


def list_root_classifications(db: Session) -> list[DeweyClassification]:
    """Liste les 10 classes principales (level=0), utilisees comme racines de l'arbre."""
    return (
        db.query(DeweyClassification)
        .filter(DeweyClassification.parent_id.is_(None), DeweyClassification.is_active.is_(True))
        .order_by(DeweyClassification.code)
        .all()
    )


def list_all_classifications(db: Session) -> list[DeweyClassification]:
    """Liste plate de toutes les categories actives, triees par code (pour un dropdown simple)."""
    return (
        db.query(DeweyClassification)
        .filter(DeweyClassification.is_active.is_(True))
        .order_by(DeweyClassification.code)
        .all()
    )


def get_descendants(db: Session, classification_id: int) -> list[DeweyClassification]:
    """
    Recupere tous les descendants d'une categorie (sous-classes a tous niveaux),
    via une requete recursive PostgreSQL (WITH RECURSIVE). Utile pour filtrer
    le catalogue par grande categorie (ex: tous les livres sous "500 - Sciences").
    """
    from sqlalchemy import text

    query = text("""
        WITH RECURSIVE descendants AS (
            SELECT id FROM dewey_classifications WHERE id = :root_id
            UNION ALL
            SELECT dc.id FROM dewey_classifications dc
            INNER JOIN descendants d ON dc.parent_id = d.id
        )
        SELECT id FROM descendants WHERE id != :root_id
    """)
    result = db.execute(query, {"root_id": classification_id})
    descendant_ids = [row[0] for row in result]

    if not descendant_ids:
        return []
    return db.query(DeweyClassification).filter(DeweyClassification.id.in_(descendant_ids)).all()
