"""Service d'upload de fichiers (couvertures de livres)."""

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class InvalidImageError(Exception):
    pass


class ImageTooLargeError(Exception):
    pass


async def save_cover_image(file: UploadFile) -> str:
    """Sauvegarde une couverture et retourne son URL relative."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidImageError(
            f"Type de fichier non autorise : {file.content_type} (jpeg/png/webp attendus)."
        )

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise ImageTooLargeError(
            f"Image trop volumineuse (max {settings.MAX_UPLOAD_SIZE_MB} Mo)."
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    extension = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{extension}"
    (upload_dir / filename).write_bytes(content)
    return f"/static/covers/{filename}"