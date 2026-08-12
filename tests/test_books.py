"""Tests du module Catalogue : RBAC et creation de livres."""

from tests.conftest import auth_headers


def test_student_cannot_create_book(client, student_user):
    response = client.post(
        "/api/v1/books",
        json={"author": "Auteur Test", "type": "physical", "language": "fr"},
        headers=auth_headers(student_user),
    )
    assert response.status_code == 403


def test_librarian_can_create_book(client, librarian_user):
    response = client.post(
        "/api/v1/books",
        json={"author": "Auteur Test", "type": "physical", "language": "fr", "title_fr": "Titre Test"},
        headers=auth_headers(librarian_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["copies_total"] == 0
    assert data["copies_available"] == 0


def test_search_books_public_access(client, librarian_user):
    client.post(
        "/api/v1/books",
        json={"author": "Recherche Auteur", "type": "physical", "language": "fr", "title_fr": "Livre Recherchable"},
        headers=auth_headers(librarian_user),
    )
    response = client.get("/api/v1/books?search=Recherchable")
    assert response.status_code == 200
    assert len(response.json()) >= 1