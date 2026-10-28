"""Tests du module Utilisateurs : suppression definitive d'un compte (admin)."""

from tests.conftest import auth_headers


def _create_book_with_copy(client, librarian_user) -> int:
    """Cree un livre + un exemplaire et renvoie l'id de l'exemplaire."""
    book_resp = client.post(
        "/api/v1/books",
        json={"author": "Auteur Suppr", "type": "physical", "language": "fr", "title_fr": "Livre Suppr"},
        headers=auth_headers(librarian_user),
    )
    book_id = book_resp.json()["id"]
    copy_resp = client.post(
        f"/api/v1/books/{book_id}/copies",
        json={"book_id": book_id, "location": "Test"},
        headers=auth_headers(librarian_user),
    )
    return copy_resp.json()["id"]


def test_delete_user_removes_account(client, admin_user, student_user):
    """Un compte sans emprunt est reellement supprime (plus dans la liste)."""
    resp = client.delete(f"/api/v1/users/{student_user.id}", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    assert resp.json()["id"] == str(student_user.id)

    listing = client.get("/api/v1/users", headers=auth_headers(admin_user)).json()
    assert all(u["id"] != str(student_user.id) for u in listing)


def test_delete_user_with_loans_is_refused(client, admin_user, student_user, librarian_user):
    """Un compte avec un historique d'emprunts ne peut pas etre supprime (409)."""
    copy_id = _create_book_with_copy(client, librarian_user)
    borrow = client.post(
        "/api/v1/loans", json={"copy_id": copy_id}, headers=auth_headers(student_user)
    )
    assert borrow.status_code == 201

    resp = client.delete(f"/api/v1/users/{student_user.id}", headers=auth_headers(admin_user))
    assert resp.status_code == 409

    # Le compte est toujours present apres le refus.
    listing = client.get("/api/v1/users", headers=auth_headers(admin_user)).json()
    assert any(u["id"] == str(student_user.id) for u in listing)


def test_delete_self_is_refused(client, admin_user):
    """Un admin ne peut pas supprimer son propre compte."""
    resp = client.delete(f"/api/v1/users/{admin_user.id}", headers=auth_headers(admin_user))
    assert resp.status_code == 409


def test_delete_unknown_user_returns_404(client, admin_user):
    resp = client.delete(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 404


def test_delete_user_forbidden_for_librarian(client, librarian_user, student_user):
    """La suppression de compte est reservee aux admins."""
    resp = client.delete(f"/api/v1/users/{student_user.id}", headers=auth_headers(librarian_user))
    assert resp.status_code == 403
