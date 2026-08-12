"""Tests du module Auth : inscription, connexion, profil."""


def test_register_creates_user(client):
    response = client.post("/api/v1/auth/register", json={
        "full_name": "Alice Test",
        "email": "alice@test.cm",
        "password": "motdepasse123",
        "role": "student",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@test.cm"
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email_fails(client):
    payload = {
        "full_name": "Bob Test",
        "email": "bob@test.cm",
        "password": "motdepasse123",
        "role": "student",
    }
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


def test_login_success(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Carla Test",
        "email": "carla@test.cm",
        "password": "motdepasse123",
        "role": "student",
    })
    response = client.post("/api/v1/auth/login", data={
        "username": "carla@test.cm",
        "password": "motdepasse123",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password_fails(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Dan Test",
        "email": "dan@test.cm",
        "password": "motdepasse123",
        "role": "student",
    })
    response = client.post("/api/v1/auth/login", data={
        "username": "dan@test.cm",
        "password": "mauvais_mdp",
    })
    assert response.status_code == 401


def test_me_requires_authentication(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
