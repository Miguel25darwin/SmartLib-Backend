"""
Point d'entree de l'application SmartLib.
Assemble la configuration, le middleware CORS, et les routers versionnes (/api/v1/...).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, books, catalogue_bulk, isbn_lookup, loans, reports, users

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
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


@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Verifie que l'API repond (utilise par le monitoring / load balancer)."""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


@app.post("/seed", tags=["admin"])
def run_seed():
    """Endpoint temporaire — peuple la base avec des comptes de test. A SUPPRIMER APRES USAGE."""
    from scripts.seed import main as seed_main
    import io, sys
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        seed_main()
    finally:
        sys.stdout = old_stdout
    return {"status": "ok", "output": buf.getvalue()}