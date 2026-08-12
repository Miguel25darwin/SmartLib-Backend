"""Tests du module Emprunts : regles metier (quota, disponibilite, retour)."""

from tests.conftest import auth_headers


def _create_book_with_copy(client, librarian_user):
    book_resp = client.post(
        "/api/v1/books",
        json={"author": "Auteur Emprunt", "type": "physical", "language": "fr", "title_fr": "Livre Emprunt"},
        headers=auth_headers(librarian_user),
    )
    book_id = book_resp.json()["id"]
    copy_resp = client.post(
        f"/api/v1/books/{book_id}/copies",
        json={"book_id": book_id, "location": "Test"},
        headers=auth_headers(librarian_user),
    )
    return copy_resp.json()["id"]


def test_borrow_and_return_flow(client, student_user, librarian_user):
    copy_id = _create_book_with_copy(client, librarian_user)

    borrow_resp = client.post(
        "/api/v1/loans", json={"copy_id": copy_id}, headers=auth_headers(student_user)
    )
    assert borrow_resp.status_code == 201
    loan_id = borrow_resp.json()["id"]
    assert borrow_resp.json()["status"] == "active"

    return_resp = client.put(
        f"/api/v1/loans/{loan_id}/return", headers=auth_headers(student_user)
    )
    assert return_resp.status_code == 200
    assert return_resp.json()["status"] == "returned"


def test_cannot_borrow_already_borrowed_copy(client, student_user, librarian_user):
    copy_id = _create_book_with_copy(client, librarian_user)

    first = client.post(
        "/api/v1/loans", json={"copy_id": copy_id}, headers=auth_headers(student_user)
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/loans", json={"copy_id": copy_id}, headers=auth_headers(student_user)
    )
    assert second.status_code == 409


def test_loan_requires_exactly_one_target(client, student_user):
    response = client.post(
        "/api/v1/loans", json={}, headers=auth_headers(student_user)
    )
    assert response.status_code == 422
