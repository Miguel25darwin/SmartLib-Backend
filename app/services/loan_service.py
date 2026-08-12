"""
Couche service pour l'entité Loan (emprunts).

Applique les règles métier du Cahier d'Architecture :
- quota d'emprunts actifs simultanés par rôle (§3, LOAN_LIMITS_BY_ROLE)
- un exemplaire physique emprunté passe au statut "borrowed"
- un exemplaire rendu repasse au statut "available"
- durée de prêt configurable (settings.LOAN_DURATION_DAYS)
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.copy import Copy
from app.models.digital_resource import DigitalResource
from app.models.enums import LOAN_LIMITS_BY_ROLE, CopyStatus, LoanStatus
from app.models.loan import Loan
from app.models.user import User
from app.models.user import User as UserModel
from app.schemas.loan import LoanCreate


class CopyNotFoundError(Exception):
    pass


class CopyNotAvailableError(Exception):
    pass


class DigitalResourceNotFoundError(Exception):
    pass


class LoanQuotaExceededError(Exception):
    pass


class LoanNotFoundError(Exception):
    pass


class LoanAlreadyReturnedError(Exception):
    pass


class NotLoanOwnerError(Exception):
    pass


def _count_active_loans(db: Session, user_id: uuid.UUID) -> int:
    return (
        db.query(Loan)
        .filter(Loan.user_id == user_id, Loan.status == LoanStatus.ACTIVE)
        .count()
    )


def create_loan(db: Session, current_user: User, loan_in: LoanCreate) -> Loan:
    """
    Crée un emprunt pour l'utilisateur courant.
    La validation "exactement un des deux champs" est déjà faite par le schéma
    Pydantic LoanCreate ; ici on vérifie les règles métier au niveau base.
    """
    # 1. Vérification du quota (Cahier d'Architecture §3)
    limit = LOAN_LIMITS_BY_ROLE[current_user.role]
    if _count_active_loans(db, current_user.id) >= limit:
        raise LoanQuotaExceededError(
            f"Quota d'emprunts atteint pour le rôle '{current_user.role.value}' (limite : {limit})."
        )

    now = datetime.now(timezone.utc)
    due_date = now + timedelta(days=settings.LOAN_DURATION_DAYS)

    copy: Copy | None = None
    if loan_in.copy_id is not None:
        copy = db.get(Copy, loan_in.copy_id)
        if copy is None:
            raise CopyNotFoundError(f"Exemplaire id={loan_in.copy_id} introuvable.")
        if copy.status != CopyStatus.AVAILABLE:
            raise CopyNotAvailableError(
                f"Exemplaire id={copy.id} non disponible (statut actuel : {copy.status.value})."
            )
        copy.status = CopyStatus.BORROWED
    else:
        resource = db.get(DigitalResource, loan_in.digital_resource_id)
        if resource is None:
            raise DigitalResourceNotFoundError(
                f"Ressource numérique id={loan_in.digital_resource_id} introuvable."
            )
        # NOTE (Phase 2) : le contrôle DRM du nombre d'accès simultanés par licence
        # n'est pas encore modélisé dans le prototype — pas de vérification de
        # disponibilité pour les ressources numériques à ce stade.

    loan = Loan(
        user_id=current_user.id,
        copy_id=loan_in.copy_id,
        digital_resource_id=loan_in.digital_resource_id,
        borrowed_at=now,
        due_date=due_date,
        status=LoanStatus.ACTIVE,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def return_loan(db: Session, loan_id: uuid.UUID, current_user: User) -> Loan:
    """
    Retourne un document.
    Autorisé si l'utilisateur est le propriétaire de l'emprunt, OU s'il est
    bibliothécaire/admin (retour assisté au guichet — Cahier d'Architecture §2.1).
    """
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise LoanNotFoundError(f"Emprunt id={loan_id} introuvable.")

    is_owner = loan.user_id == current_user.id
    is_staff = current_user.role.value in ("librarian", "admin")
    if not is_owner and not is_staff:
        raise NotLoanOwnerError("Vous n'êtes pas autorisé à retourner cet emprunt.")

    if loan.status != LoanStatus.ACTIVE:
        raise LoanAlreadyReturnedError(f"Cet emprunt a déjà le statut '{loan.status.value}'.")

    loan.returned_at = datetime.now(timezone.utc)
    loan.status = LoanStatus.RETURNED

    if loan.copy_id is not None:
        copy = db.get(Copy, loan.copy_id)
        if copy is not None:
            copy.status = CopyStatus.AVAILABLE

    db.commit()
    db.refresh(loan)
    return loan


def list_loans_for_user(db: Session, user_id: uuid.UUID) -> list[Loan]:
    """Emprunts en cours + historique de l'utilisateur (GET /loans/me)."""
    return (
        db.query(Loan)
        .filter(Loan.user_id == user_id)
        .order_by(Loan.borrowed_at.desc())
        .all()
    )


def list_all_loans(db: Session, status_filter: LoanStatus | None = None) -> list[Loan]:
    """Tous les emprunts (bibliothécaire / admin) — GET /loans."""
    query = db.query(Loan)
    if status_filter is not None:
        query = query.filter(Loan.status == status_filter)
    return query.order_by(Loan.borrowed_at.desc()).all()


def borrow_by_scan(db: Session, card_number: str, qr_code: str) -> Loan:
    """
    Emprunt assisté par double scan (bibliothécaire au poste de prêt).
    Réutilise create_loan() pour ne pas dupliquer les règles métier
    (quota par rôle, disponibilité de l'exemplaire).
    """
    from app.services.user_service import UserNotFoundError, get_user_by_card_number

    user = get_user_by_card_number(db, card_number)

    copy = db.query(Copy).filter(Copy.qr_code == qr_code).first()
    if copy is None:
        raise CopyNotFoundError(f"Aucun exemplaire ne correspond au QR Code '{qr_code}'.")

    return create_loan(db, user, LoanCreate(copy_id=copy.id))


def return_by_scan(db: Session, qr_code: str) -> Loan:
    """
    Retour par scan du QR Code de l'exemplaire (§4 du document).
    Recherche l'emprunt actif correspondant à cet exemplaire, sans avoir
    besoin de connaitre le loan_id à l'avance.
    """
    copy = db.query(Copy).filter(Copy.qr_code == qr_code).first()
    if copy is None:
        raise CopyNotFoundError(f"Aucun exemplaire ne correspond au QR Code '{qr_code}'.")

    active_loan = (
        db.query(Loan)
        .filter(Loan.copy_id == copy.id, Loan.status == LoanStatus.ACTIVE)
        .first()
    )

    if active_loan is None:
        raise LoanNotFoundError(
            f"Aucun emprunt actif trouvé pour l'exemplaire '{qr_code}'."
        )

    active_loan.returned_at = datetime.now(timezone.utc)
    active_loan.status = LoanStatus.RETURNED
    copy.status = CopyStatus.AVAILABLE

    db.commit()
    db.refresh(active_loan)

    return active_loan