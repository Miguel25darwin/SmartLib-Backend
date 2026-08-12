"""
Point d'entrée de l'application SmartLib.
Assemble la configuration et les routers versionnés (/api/v1/...).
"""

from fastapi import FastAPI

from app.core.config import settings
from app.routers import auth, books, catalogue_bulk, isbn_lookup, loans, reports, users
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(books.router, prefix=settings.API_V1_PREFIX)
app.include_router(catalogue_bulk.router, prefix=settings.API_V1_PREFIX)
app.include_router(isbn_lookup.router, prefix=settings.API_V1_PREFIX)
app.include_router(loans.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)

@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Vérifie que l'API répond (utilisé par le monitoring / load balancer)."""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}

