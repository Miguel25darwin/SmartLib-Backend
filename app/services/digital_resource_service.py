"""Service de gestion des ressources numériques liées à un livre."""

from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.digital_resource import DigitalResource
from app.schemas.digital_resource import DigitalResourceCreate, DigitalResourceUpdate


class DigitalResourceNotFoundError(Exception):
    pass


class BookNotFoundError(Exception):
    pass


def list_digital_resources_for_book(db: Session, book_id: int) -> list[DigitalResource]:
    book = db.get(Book, book_id)
    if book is None:
        raise BookNotFoundError(f"Livre id={book_id} introuvable.")
    return db.query(DigitalResource).filter(DigitalResource.book_id == book_id).order_by(DigitalResource.id).all()


def create_digital_resource(db: Session, resource_in: DigitalResourceCreate) -> DigitalResource:
    book = db.get(Book, resource_in.book_id)
    if book is None:
        raise BookNotFoundError(f"Livre id={resource_in.book_id} introuvable.")

    resource = DigitalResource(**resource_in.model_dump())
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def update_digital_resource(db: Session, resource_id: int, resource_update: DigitalResourceUpdate) -> DigitalResource:
    resource = db.get(DigitalResource, resource_id)
    if resource is None:
        raise DigitalResourceNotFoundError(f"Ressource numérique id={resource_id} introuvable.")

    update_data = resource_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resource, field, value)

    db.commit()
    db.refresh(resource)
    return resource


def delete_digital_resource(db: Session, resource_id: int) -> None:
    resource = db.get(DigitalResource, resource_id)
    if resource is None:
        raise DigitalResourceNotFoundError(f"Ressource numérique id={resource_id} introuvable.")

    db.delete(resource)
    db.commit()
