"""
Moteur SQLAlchemy + gestion des sessions.
`get_db` est la dépendance FastAPI à injecter dans chaque router qui accède à la base.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : ouvre une session, la ferme toujours à la fin."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()