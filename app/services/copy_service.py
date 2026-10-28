"""Couche service pour l'entite Copy (exemplaires physiques) et le scan QR Code."""

import re

from sqlalchemy.orm import Session

from datetime import datetime, timezone

from app.models.book import Book
from app.models.copy import Copy
from app.models.dewey_classification import DeweyClassification
from app.models.loan import Loan
from app.schemas.copy import CopyCreate, CopyUpdate
from app.models.enums import CopyStatus, LoanStatus


def build_call_number(
    dewey_code: str | None, author: str, *, index: int = 1, total: int = 1
) -> str:
    """
    Construit une cote de rangement selon la convention
    '<code Dewey> <code auteur 3 lettres>[-<numero d'exemplaire>]'.

    Exemples : "005 COR" (exemplaire unique), "005 COR-1"/"005 COR-2" (plusieurs
    exemplaires du meme ouvrage). Le suffixe n'apparait que s'il y a plusieurs
    exemplaires, pour rester coherent avec le formulaire admin.
    """
    code = (dewey_code or "000").strip() or "000"
    # Code auteur : 3 premieres lettres du NOM (dernier mot), convention usuelle
    # de catalogage ("T. Cormen" -> "COR", "H. de Blij" -> "BLI").
    tokens = re.findall(r"[A-Za-z]+", author or "")
    surname = tokens[-1] if tokens else ""
    author_code = (surname[:3] or "XXX").upper()
    base = f"{code} {author_code}"
    return f"{base}-{index}" if total > 1 else base


def _resolve_dewey_code(db: Session, book: Book) -> str | None:
    """Retourne le code Dewey lisible du livre (via sa FK dewey_id), ou None."""
    if book.dewey_id is None:
        return None
    dewey = db.get(DeweyClassification, book.dewey_id)
    return dewey.code if dewey is not None else None


class CopyNotFoundError(Exception):
    pass


class QrCodeNotFoundError(Exception):
    """
    Levee quand le QR Code scanne ne correspond a aucun exemplaire connu.
    Cas reel frequent (etiquette abimee, exemplaire retire du catalogue) :
    message distinct de CopyNotFoundError pour un diagnostic clair cote bibliothecaire.
    """
    pass


class BookNotFoundForCopyError(Exception):
    pass
class CopyNotRepairableError(Exception):
    """Levee quand on tente de reparer un exemplaire qui n'est pas dans l'etat 'damaged'."""
    pass

def create_copy(db: Session, copy_in: CopyCreate) -> Copy:
    """
    Cree un exemplaire. Le qr_code est genere automatiquement par le modele
    (default=generate_qr_identifier) : c'est cette valeur qu'il faudra
    imprimer et coller sur le livre physique, conformement au workflow
    "Consignes de Gestion du catalogue" (creation -> generation QR -> impression/collage).
    """
    book = db.get(Book, copy_in.book_id)
    if book is None:
        raise BookNotFoundForCopyError(
            f"Livre id={copy_in.book_id} introuvable, impossible de creer l'exemplaire."
        )
    copy = Copy(**copy_in.model_dump())

    # Cote de rangement : si le bibliothecaire n'en a pas fourni, on la genere
    # automatiquement (code Dewey + code auteur) afin qu'aucun exemplaire
    # physique n'entre au catalogue sans adresse de rangement.
    if copy.call_number is None:
        total = db.query(Copy).filter(Copy.book_id == book.id).count() + 1
        copy.call_number = build_call_number(
            _resolve_dewey_code(db, book), book.author, index=total, total=total
        )

    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy


def list_copies_for_book(db: Session, book_id: int) -> list[Copy]:
    return db.query(Copy).filter(Copy.book_id == book_id).all()


def update_copy(db: Session, copy_id: int, copy_update: CopyUpdate) -> Copy:
    copy = db.get(Copy, copy_id)
    if copy is None:
        raise CopyNotFoundError(f"Exemplaire id={copy_id} introuvable.")
    update_data = copy_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(copy, field, value)
    db.commit()
    db.refresh(copy)
    return copy


def scan_qr_code(db: Session, qr_code: str) -> dict:
    """
    Resout un QR Code scanne vers les informations de l'exemplaire + du livre.
    C'est le point d'entree utilise par emprunt/retour/inventaire par scan (etape 14).
    """
    copy = db.query(Copy).filter(Copy.qr_code == qr_code).first()
    if copy is None:
        raise QrCodeNotFoundError(f"Aucun exemplaire ne correspond au QR Code '{qr_code}'.")

    book = db.get(Book, copy.book_id)
    title = (book.title_fr or book.title_en or "Sans titre") if book else "Livre introuvable"
    author = book.author if book else "Inconnu"

    return {
        "copy_id": copy.id,
        "qr_code": copy.qr_code,
        "status": copy.status,
        "location": copy.location,
        "call_number": copy.call_number,
        "book_id": copy.book_id,
        "book_title": title,
        "book_author": author,
    }
def mark_copy_as_lost(db: Session, copy_id: int) -> Copy:
    """Marque un exemplaire comme perdu et clôture son emprunt actif associé s'il existe."""
    copy = db.get(Copy, copy_id)
    if copy is None:
        raise CopyNotFoundError(f"Exemplaire id={copy_id} introuvable.")

    active_loan = (
        db.query(Loan)
        .filter(Loan.copy_id == copy_id, Loan.status == LoanStatus.ACTIVE)
        .first()
    )
    if active_loan is not None:
        active_loan.status = LoanStatus.RETURNED
        active_loan.returned_at = datetime.now(timezone.utc)

    copy.status = CopyStatus.LOST
    db.commit()
    db.refresh(copy)
    return copy


def mark_copy_as_repaired(db: Session, copy_id: int) -> Copy:
    """
    Remet un exemplaire endommage en circulation (statut -> available).
    Refuse l'operation si l'exemplaire n'est pas actuellement 'damaged',
    pour eviter de rendre disponible par erreur un exemplaire emprunte ou perdu.
    """
    copy = db.get(Copy, copy_id)
    if copy is None:
        raise CopyNotFoundError(f"Exemplaire id={copy_id} introuvable.")
    if copy.status != CopyStatus.DAMAGED:
        raise CopyNotRepairableError(
            f"Exemplaire id={copy_id} n'est pas endommage (statut actuel : {copy.status.value}), "
            "impossible de le marquer comme repare."
        )
    copy.status = CopyStatus.AVAILABLE
    db.commit()
    db.refresh(copy)
    return copy