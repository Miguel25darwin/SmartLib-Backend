
"""
Configuration pytest partagee.

Utilise une base de donnees PostgreSQL DEDIEE aux tests (smartlib_test_db),
distincte de smartlib_db, pour ne jamais toucher aux donnees de developpement.
Chaque test tourne dans une transaction annulee a la fin (isolation totale).
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models import Base
from app.models.enums import UserRole
from app.models.user import User

TEST_DATABASE_URL = "postgresql+psycopg2://smartlib_user:smartlib_pass@localhost:5432/smartlib_test_db"

engine = create_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Cree toutes les tables une fois pour toute la session de tests, les supprime a la fin."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Session DB isolee par test, avec rollback systematique a la fin."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Client de test FastAPI, avec la DB de test injectee via override de dependance."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def student_user(db_session):
    """Cree un utilisateur etudiant directement en base pour les tests."""
    user = User(
        full_name="Test Etudiant",
        email=f"etudiant.{uuid.uuid4().hex[:8]}@test.cm",
        password_hash=hash_password("testpass123"),
        role=UserRole.STUDENT,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def librarian_user(db_session):
    """Cree un utilisateur bibliothecaire directement en base pour les tests."""
    user = User(
        full_name="Test Biblio",
        email=f"biblio.{uuid.uuid4().hex[:8]}@test.cm",
        password_hash=hash_password("testpass123"),
        role=UserRole.LIBRARIAN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(user) -> dict:
    """Genere un header Authorization Bearer valide pour un utilisateur donne."""
    from app.core.security import create_access_token
    token = create_access_token(subject=str(user.id), role=user.role.value, expires_minutes=480)
    return {"Authorization": f"Bearer {token}"}