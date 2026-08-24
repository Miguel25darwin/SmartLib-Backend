"""
Point d'entree de l'application SmartLib.
Assemble la configuration, le middleware CORS, et les routers versionnes (/api/v1/...).
"""

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import auth, books, catalogue_bulk, dewey, isbn_lookup, loans, reports, users

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
)

os.makedirs("uploads/covers", exist_ok=True)
app.mount("/static/covers", StaticFiles(directory="uploads/covers"), name="covers")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Retourne une enveloppe d'erreur stable pour tous les endpoints."""
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        content = exc.detail
    else:
        content = {
            "code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
        }
    return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Les donnees envoyees sont invalides.",
            "details": exc.errors(),
        },
    )

# --- CORS ---
# allow_methods=["*"] et allow_headers=["*"] sont indispensables pour que le
# navigateur autorise les requetes "preflight" (OPTIONS) que Flutter Web envoie
# automatiquement avant chaque requete non-triviale (POST/PUT avec JSON, headers
# Authorization personnalises, etc). Sans ca, le navigateur bloque la requete
# reelle meme si l'API elle-meme y repondrait correctement.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(books.router, prefix=settings.API_V1_PREFIX)
app.include_router(loans.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(catalogue_bulk.router, prefix=settings.API_V1_PREFIX)
app.include_router(isbn_lookup.router, prefix=settings.API_V1_PREFIX)
app.include_router(dewey.router, prefix=settings.API_V1_PREFIX)

@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Verifie que l'API repond (utilise par le monitoring / load balancer)."""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}