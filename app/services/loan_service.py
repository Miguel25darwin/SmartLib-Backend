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
from app.models.book import Book
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


class LoanNotPendingError(Exception):
    pass


def refresh_overdue_loans(db: Session) -> None:
    """Met à jour les prêts actifs expirés au statut OVERDUE."""
    now = datetime.now(timezone.utc)
    expired_loans = (
        db.query(Loan)
        .filter(Loan.status == LoanStatus.ACTIVE, Loan.due_date < now)
        .all()
    )
    for loan in expired_loans:
        loan.status = LoanStatus.OVERDUE
    if expired_loans:
        db.commit()


def _refresh_overdue_statuses(db: Session) -> None:
    """Bascule en retard les emprunts actifs dont la date limite est depassee."""
    db.query(Loan).filter(
        Loan.status == LoanStatus.ACTIVE,
        Loan.due_date < datetime.now(timezone.utc),
    ).update({"status": LoanStatus.OVERDUE}, synchronize_session=False)
    db.commit()


def _enrich_loan(db: Session, loan: Loan) -> Loan:
    """Attache dynamiquement book_title et user_name a l'objet loan (attributs non-colonnes)."""
    user = db.get(UserModel, loan.user_id)
    loan.user_name = user.full_name if user else None

    if loan.copy_id is not None:
        copy = db.get(Copy, loan.copy_id)
        if copy is not None:
            book = db.get(Book, copy.book_id)
            loan.book_title = (book.title_fr or book.title_en) if book else None
        else:
            loan.book_title = None
    elif loan.digital_resource_id is not None:
        resource = db.get(DigitalResource, loan.digital_resource_id)
        if resource is not None:
            book = db.get(Book, resource.book_id)
            loan.book_title = (book.title_fr or book.title_en) if book else None
        else:
            loan.book_title = None
    else:
        loan.book_title = None

    return loan

def _count_open_loans(
    db: Session,
    user_id: uuid.UUID,
    exclude_loan_id: uuid.UUID | None = None,
) -> int:
    """Emprunts occupant le quota : actifs, en retard et demandes en attente."""
    query = db.query(Loan).filter(
        Loan.user_id == user_id,
        Loan.status.in_(
            [LoanStatus.ACTIVE, LoanStatus.OVERDUE, LoanStatus.PENDING]
        ),
    )
    if exclude_loan_id is not None:
        query = query.filter(Loan.id != exclude_loan_id)
    return query.count()


def create_loan(
    db: Session,
    current_user: User,
    loan_in: LoanCreate,
    *,
    auto_approve: bool = False,
) -> Loan:
    """
    Cree une demande d'emprunt pour l'utilisateur courant.

    Par defaut (`auto_approve=False`), la demande reste au statut PENDING :
    un bibliothecaire/admin doit la verifier puis l'autoriser avant que le
    membre n'entre en possession du document.

    Les flux assistes au guichet (scan double, creation admin) passent
    `auto_approve=True` : le gestionnaire est deja en train d'autoriser.
    """
    # 1. Verification du quota (Cahier d'Architecture §3)
    limit = LOAN_LIMITS_BY_ROLE[current_user.role]
    if _count_open_loans(db, current_user.id) >= limit:
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
        if auto_approve:
            copy.status = CopyStatus.BORROWED
    else:
        resource = db.get(DigitalResource, loan_in.digital_resource_id)
        if resource is None:
            raise DigitalResourceNotFoundError(
                f"Ressource numérique id={loan_in.digital_resource_id} introuvable."
            )

    loan = Loan(
        user_id=current_user.id,
        copy_id=loan_in.copy_id,
        digital_resource_id=loan_in.digital_resource_id,
        borrowed_at=now,
        due_date=due_date,
        status=LoanStatus.ACTIVE if auto_approve else LoanStatus.PENDING,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return _enrich_loan(db, loan)


def approve_loan(
    db: Session,
    loan_id: uuid.UUID,
    *,
    note: str | None = None,
) -> Loan:
    """Autorise une demande en attente et met l'exemplaire a disposition."""
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise LoanNotFoundError(f"Demande id={loan_id} introuvable.")
    if loan.status != LoanStatus.PENDING:
        raise LoanNotPendingError(
            f"Cette demande a deja ete traitee (statut : {loan.status.value})."
        )

    user = db.get(UserModel, loan.user_id)
    if user is None:
        raise LoanNotFoundError("Utilisateur de la demande introuvable.")

    limit = LOAN_LIMITS_BY_ROLE[user.role]
    if _count_open_loans(db, user.id, exclude_loan_id=loan.id) >= limit:
        raise LoanQuotaExceededError(
            f"Quota d'emprunts atteint pour ce membre (limite : {limit})."
        )

    now = datetime.now(timezone.utc)
    if loan.copy_id is not None:
        copy = db.get(Copy, loan.copy_id)
        if copy is None:
            raise CopyNotFoundError(f"Exemplaire id={loan.copy_id} introuvable.")
        if copy.status != CopyStatus.AVAILABLE:
            raise CopyNotAvailableError(
                "Cet exemplaire n'est plus disponible : il a ete emprunte ou retire du rayon."
            )
        copy.status = CopyStatus.BORROWED

    loan.borrowed_at = now
    loan.due_date = now + timedelta(days=settings.LOAN_DURATION_DAYS)
    loan.status = LoanStatus.ACTIVE
    loan.decided_at = now
    loan.decision_note = note
    db.commit()
    db.refresh(loan)
    return _enrich_loan(db, loan)


def reject_loan(
    db: Session,
    loan_id: uuid.UUID,
    *,
    note: str | None = None,
) -> Loan:
    """Refuse une demande en attente ; l'exemplaire reste disponible."""
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise LoanNotFoundError(f"Demande id={loan_id} introuvable.")
    if loan.status != LoanStatus.PENDING:
        raise LoanNotPendingError(
            f"Cette demande a deja ete traitee (statut : {loan.status.value})."
        )

    loan.status = LoanStatus.REJECTED
    loan.decided_at = datetime.now(timezone.utc)
    loan.decision_note = note
    db.commit()
    db.refresh(loan)
    return _enrich_loan(db, loan)


def list_pending_loans(db: Session) -> list[Loan]:
    """Demandes d'emprunt en attente d'autorisation (bibliothecaire/admin)."""
    loans = (
        db.query(Loan)
        .filter(Loan.status == LoanStatus.PENDING)
        .order_by(Loan.borrowed_at.asc())
        .all()
    )
    return [_enrich_loan(db, loan) for loan in loans]


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

    if loan.status not in (LoanStatus.ACTIVE, LoanStatus.OVERDUE):
        raise LoanAlreadyReturnedError(
            f"Cet emprunt a le statut '{loan.status.value}' et ne peut pas être retourné."
        )

    loan.returned_at = datetime.now(timezone.utc)
    loan.status = LoanStatus.RETURNED

    if loan.copy_id is not None:
        copy = db.get(Copy, loan.copy_id)
        if copy is not None:
            copy.status = CopyStatus.AVAILABLE

    db.commit()
    db.refresh(loan)
    return _enrich_loan(db, loan)


def list_loans_for_user(db: Session, user_id: uuid.UUID) -> list[Loan]:
    """Emprunts en cours + historique de l'utilisateur (GET /loans/me)."""
    _refresh_overdue_statuses(db)
    loans = (
        db.query(Loan)
        .filter(Loan.user_id == user_id)
        .order_by(Loan.borrowed_at.desc())
        .all()
    )
    return [_enrich_loan(db, loan) for loan in loans]


def list_all_loans(db: Session, status_filter: LoanStatus | None = None) -> list[Loan]:
    """Tous les emprunts (bibliothécaire / admin) — GET /loans."""
    _refresh_overdue_statuses(db)
    query = db.query(Loan)
    if status_filter is not None:
        query = query.filter(Loan.status == status_filter)
    loans = query.order_by(Loan.borrowed_at.desc()).all()
    return [_enrich_loan(db, loan) for loan in loans]


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

    loan = create_loan(db, user, LoanCreate(copy_id=copy.id), auto_approve=True)
    return _enrich_loan(db, loan)


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
        .filter(
            Loan.copy_id == copy.id,
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
        )
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

    return _enrich_loan(db, active_loan)
def create_loan_for_user(
    db: Session,
    target_user: "UserModel",
    copy_id: int | None,
    digital_resource_id: int | None,
    due_date_override: datetime | None = None,
) -> Loan:
    """
    Cree un emprunt pour un utilisateur cible, au nom d'un bibliothecaire/admin
    (pret assiste au guichet - POST /loans/admin). Reutilise les memes regles
    metier que create_loan (quota par role, disponibilite) pour ne jamais les
    dupliquer, avec une seule difference : la date d'echeance peut etre
    surchargee manuellement par le bibliothecaire (due_date_override).
    """
    from app.schemas.loan import LoanCreate

    loan = create_loan(
        db,
        target_user,
        LoanCreate(copy_id=copy_id, digital_resource_id=digital_resource_id),
        auto_approve=True,
    )

    if due_date_override is not None:
        loan.due_date = due_date_override
        db.commit()
        db.refresh(loan)

    return _enrich_loan(db, loan)
