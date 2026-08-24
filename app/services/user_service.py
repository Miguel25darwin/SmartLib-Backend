"""
Couche service pour l'entite User.
Separe la logique metier (creation, authentification, scan carte) des routes FastAPI.
"""

import uuid

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User, generate_card_number
from app.schemas.user import UserCreate


class EmailAlreadyExistsError(Exception):
    """Levee quand on tente de creer un compte avec un email deja utilise."""
    pass


class UserNotFoundError(Exception):
    """Levee quand un utilisateur demande (par id ou carte) n'existe pas."""
    pass


class InvalidCurrentPasswordError(Exception):
    """Levee quand le mot de passe actuel fourni est incorrect."""
    pass


def update_user_admin(db: Session, user_id, data) -> User:
    """Modifie un compte (role, nom, langue, statut actif)."""
    user = db.get(User, user_id)
    if user is None:
        raise UserNotFoundError(f"Utilisateur id={user_id} introuvable.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user_id) -> User:
    """Desactive un compte sans supprimer son historique d'emprunts."""
    user = db.get(User, user_id)
    if user is None:
        raise UserNotFoundError(f"Utilisateur id={user_id} introuvable.")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    """Change le mot de passe apres verification de l'ancien."""
    if not verify_password(current_password, user.password_hash):
        raise InvalidCurrentPasswordError("Mot de passe actuel incorrect.")
    user.password_hash = hash_password(new_password)
    db.commit()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_card_number(db: Session, card_number: str) -> User:
    user = db.query(User).filter(User.card_number == card_number).first()
    if user is None:
        raise UserNotFoundError(f"Aucun utilisateur ne correspond a la carte '{card_number}'.")
    return user


def create_user(db: Session, user_in: UserCreate) -> User:
    """Cree un compte utilisateur. Leve EmailAlreadyExistsError si l'email existe deja."""
    if get_user_by_email(db, user_in.email) is not None:
        raise EmailAlreadyExistsError(f"L'email {user_in.email} est deja utilise.")

    user = User(
        full_name=user_in.full_name,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=user_in.role,
        language_pref=user_in.language_pref,
        # Genere explicitement avec le bon prefixe selon le role
        # (le default du modele ne connait pas encore le role a ce stade).
        card_number=generate_card_number(user_in.role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Retourne l'utilisateur si email + mot de passe sont corrects et le compte actif, sinon None."""
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def change_user_password(db: Session, user: User, current_password: str, new_password: str) -> User:
    """Change le mot de passe de l'utilisateur après validation de l'ancien mot de passe."""
    if not verify_password(current_password, user.password_hash):
        raise InvalidCurrentPasswordError("Le mot de passe actuel est incorrect.")
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, role_filter: str | None = None, skip: int = 0, limit: int = 50) -> list[User]:
    """
    Liste tous les utilisateurs, avec filtre optionnel par role.
    Reserve bibliothecaire/admin (donnee sensible : cartes membres, statut de compte).
    """
    query = db.query(User)
    if role_filter is not None:
        query = query.filter(User.role == role_filter)
    return query.order_by(User.full_name).offset(skip).limit(limit).all()