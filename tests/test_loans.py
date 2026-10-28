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
    assert borrow_resp.json()["status"] == "pending"

    approve_resp = client.put(
        f"/api/v1/loans/{loan_id}/approve", headers=auth_headers(librarian_user)
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "active"

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
    loan_id = first.json()["id"]

    approve = client.put(
        f"/api/v1/loans/{loan_id}/approve", headers=auth_headers(librarian_user)
    )
    assert approve.status_code == 200

    second = client.post(
        "/api/v1/loans", json={"copy_id": copy_id}, headers=auth_headers(student_user)
    )
    assert second.status_code == 409


def test_loan_quota_is_enforced_including_pending_requests(client, student_user, librarian_user):
    copy_id = _create_book_with_copy(client, librarian_user)

    # Le quota etudiant est de 5 emprunts simultanes, demandes en attente incluses.
    for _ in range(5):
        response = client.post(
            "/api/v1/loans", json={"copy_id": copy_id}, headers=auth_headers(student_user)
        )
        assert response.status_code == 201
        assert response.json()["status"] == "pending"

    sixth = client.post(
        "/api/v1/loans", json={"copy_id": copy_id}, headers=auth_headers(student_user)
    )
    assert sixth.status_code == 403
    response = client.post(
        "/api/v1/loans", json={}, headers=auth_headers(student_user)
    )
    assert response.status_code == 422


def test_loan_config_is_exposed_to_staff_only(client, student_user, librarian_user):
    response = client.get("/api/v1/loans/config", headers=auth_headers(librarian_user))
    assert response.status_code == 200
    body = response.json()
    assert body["duration_days"] > 0
    assert body["limits_by_role"]["student"] == 5
    assert body["limits_by_role"]["lecturer"] == 10
    assert body["limits_by_role"]["admin"] == 999

    forbidden = client.get("/api/v1/loans/config", headers=auth_headers(student_user))
    assert forbidden.status_code == 403
