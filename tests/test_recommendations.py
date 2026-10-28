"""Tests du module Recommandations d'ouvrages."""

import uuid

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from tests.conftest import auth_headers


def _create_book(client, librarian_user, *, title="Livre Recommande"):
    response = client.post(
        "/api/v1/books",
        json={
            "author": "Auteur Recommandation",
            "type": "physical",
            "language": "fr",
            "title_fr": title,
        },
        headers=auth_headers(librarian_user),
    )
    assert response.status_code == 201
    return response.json()["id"]


def _add_copy(client, librarian_user, book_id):
    response = client.post(
        f"/api/v1/books/{book_id}/copies",
        json={"book_id": book_id, "location": "Rayon test"},
        headers=auth_headers(librarian_user),
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_recommendation(client, user, book_id, *, code="INFO101", qty=2):
    return client.post(
        "/api/v1/recommendations",
        json={
            "course_code": code,
            "course_title": "Algorithmique",
            "book_id": book_id,
            "required_quantity": qty,
        },
        headers=auth_headers(user),
    )


def test_lecturer_recommends_book_and_student_can_read(
    client, lecturer_user, student_user, librarian_user
):
    book_id = _create_book(client, librarian_user)
    _add_copy(client, librarian_user, book_id)

    created = _create_recommendation(client, lecturer_user, book_id, qty=2)
    assert created.status_code == 201
    body = created.json()
    assert body["course_code"] == "INFO101"
    assert body["lecturer_name"] == lecturer_user.full_name
    assert body["book_title"] == "Livre Recommande"
    assert body["required_quantity"] == 2
    assert body["available_copies"] == 1
    assert body["total_copies"] == 1
    assert body["missing_copies"] == 1
    assert body["is_sufficient"] is False
    assert body["is_owner"] is True
    assert body["can_delete"] is True

    listed = client.get("/api/v1/recommendations", headers=auth_headers(student_user))
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["can_delete"] is False


def test_student_cannot_create_recommendation(
    client, student_user, librarian_user
):
    book_id = _create_book(client, librarian_user)
    response = _create_recommendation(client, student_user, book_id)
    assert response.status_code == 403


def test_duplicate_recommendation_is_rejected(
    client, lecturer_user, librarian_user
):
    book_id = _create_book(client, librarian_user)
    first = _create_recommendation(client, lecturer_user, book_id)
    assert first.status_code == 201

    duplicate = _create_recommendation(client, lecturer_user, book_id)
    assert duplicate.status_code == 409


def test_other_lecturer_cannot_delete_but_librarian_can(
    client, lecturer_user, librarian_user, db_session
):
    book_id = _create_book(client, librarian_user)
    created = _create_recommendation(client, lecturer_user, book_id)
    recommendation_id = created.json()["id"]

    other_lecturer = User(
        full_name="Autre Enseignant",
        email=f"autre.{uuid.uuid4().hex[:8]}@test.cm",
        password_hash=hash_password("testpass123"),
        role=UserRole.LECTURER,
    )
    db_session.add(other_lecturer)
    db_session.commit()
    db_session.refresh(other_lecturer)

    forbidden = client.delete(
        f"/api/v1/recommendations/{recommendation_id}",
        headers=auth_headers(other_lecturer),
    )
    assert forbidden.status_code == 403

    deleted = client.delete(
        f"/api/v1/recommendations/{recommendation_id}",
        headers=auth_headers(librarian_user),
    )
    assert deleted.status_code == 204

    listed = client.get("/api/v1/recommendations", headers=auth_headers(librarian_user))
    assert listed.json() == []


def test_course_code_is_normalized_and_unknown_book_rejected(
    client, lecturer_user, librarian_user
):
    book_id = _create_book(client, librarian_user)
    created = _create_recommendation(client, lecturer_user, book_id, code="  info 101 ")
    assert created.status_code == 201
    assert created.json()["course_code"] == "INFO 101"

    missing = _create_recommendation(client, lecturer_user, 999999)
    assert missing.status_code == 404
