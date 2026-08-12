
"""
Configuration centralisée du backend SmartLib.
Toutes les valeurs sensibles ou dépendantes de l'environnement (DB, JWT, CORS...)
passent par ici. Rien n'est codé en dur ailleurs dans l'application.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Application ---
    APP_NAME: str = "SmartLib API"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # --- Base de données ---
    DATABASE_URL: str

    # --- Sécurité JWT ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES_CAMPUS: int = 480
    ACCESS_TOKEN_EXPIRE_MINUTES_REMOTE: int = 120
# --- Règles métier emprunts ---
    LOAN_DURATION_DAYS: int = 14
    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Singleton de configuration (mise en cache pour éviter de relire le .env à chaque appel)."""
    return Settings()


settings = get_settings()