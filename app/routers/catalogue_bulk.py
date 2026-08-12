"""
Module Import/Export en masse du catalogue.
Conforme aux "Consignes de Gestion du catalogue".
Reserve bibliothecaire/admin (operation sensible sur le catalogue).
"""

import io

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.schemas.import_export import ImportResult
from app.services.catalogue_import_export import export_books_to_csv, import_books_from_csv

router = APIRouter(prefix="/catalogue", tags=["catalogue", "import-export"])

LIBRARIAN_OR_ADMIN = require_roles(UserRole.LIBRARIAN, UserRole.ADMIN)


@router.get("/export", dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
def export_catalogue(db: Session = Depends(get_db)) -> StreamingResponse:
    """
    Exporte l'integralite du catalogue au format CSV, telechargeable directement
    (ouvrable dans Excel/LibreOffice).
    """
    csv_content = export_books_to_csv(db)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=smartlib_catalogue_export.csv"},
    )


@router.post("/import", response_model=ImportResult, status_code=status.HTTP_200_OK,
             dependencies=[Depends(LIBRARIAN_OR_ADMIN)])
async def import_catalogue(
    file: UploadFile,
    db: Session = Depends(get_db),
) -> ImportResult:
    """
    Importe des livres en masse depuis un fichier CSV.
    Colonnes attendues (header) : title_fr,title_en,author,isbn,publisher,
    publication_year,dewey_classification,type,language,cover_url
    (seuls 'author' et 'type' sont obligatoires).
    """
    raw_bytes = await file.read()
    csv_content = raw_bytes.decode("utf-8-sig")  # utf-8-sig gere le BOM d'Excel Windows
    return import_books_from_csv(db, csv_content)
