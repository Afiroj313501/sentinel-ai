"""Tests for authentication, registration, login, and scan isolation."""

import pytest


def test_register_success(client) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "supersecurepassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"
    assert len(data["user"]["id"]) > 0


def test_register_duplicate_email(client) -> None:
    client.post(
        "/api/auth/register",
        json={"email": "bob@example.com", "password": "password12345"},
    )
    response = client.post(
        "/api/auth/register",
        json={"email": "BOB@example.com", "password": "password12345"},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("invalid-email", "validpassword123"),
        ("user@domain", "validpassword123"),
        ("user@domain.com", "short"),
    ],
)
def test_register_invalid_input(client, email: str, password: str) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 422


def test_login_success(client) -> None:
    client.post(
        "/api/auth/register",
        json={"email": "charlie@example.com", "password": "mypassword123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "charlie@example.com", "password": "mypassword123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_incorrect_credentials(client) -> None:
    client.post(
        "/api/auth/register",
        json={"email": "dave@example.com", "password": "correctpassword1"},
    )
    # Wrong password
    bad_pass = client.post(
        "/api/auth/login",
        json={"email": "dave@example.com", "password": "wrongpassword1"},
    )
    assert bad_pass.status_code == 401
    assert "Incorrect email or password" in bad_pass.json()["detail"]

    # Nonexistent user
    no_user = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"},
    )
    assert no_user.status_code == 401


def test_get_profile(client) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"email": "eve@example.com", "password": "password12345"},
    )
    token = reg.json()["access_token"]

    # Authenticated
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "eve@example.com"

    # Unauthenticated
    unauth = client.get("/api/auth/me")
    assert unauth.status_code == 401


def test_user_scan_isolation(client, make_zip) -> None:
    # 1. Register User A
    token_a = client.post(
        "/api/auth/register",
        json={"email": "usera@example.com", "password": "password12345"},
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B
    token_b = client.post(
        "/api/auth/register",
        json={"email": "userb@example.com", "password": "password12345"},
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A uploads a scan
    upload = client.post(
        "/api/scans/upload",
        files={"file": ("repo.zip", make_zip({"app.py": "x = 1"}), "application/zip")},
        headers=headers_a,
    )
    assert upload.status_code == 200
    scan_id = upload.json()["metadata"]["scan_id"]

    # 4. User A sees 1 scan in history
    history_a = client.get("/api/scans", headers=headers_a)
    assert history_a.status_code == 200
    assert history_a.json()["total"] == 1

    # 5. User B sees 0 scans in history
    history_b = client.get("/api/scans", headers=headers_b)
    assert history_b.status_code == 200
    assert history_b.json()["total"] == 0

    # 6. User B cannot access User A's scan
    forbidden_detail = client.get(f"/api/scans/{scan_id}", headers=headers_b)
    assert forbidden_detail.status_code == 404

    # 7. User B cannot delete User A's scan
    forbidden_delete = client.delete(f"/api/scans/{scan_id}", headers=headers_b)
    assert forbidden_delete.status_code == 404

    # 8. User A can delete their own scan
    ok_delete = client.delete(f"/api/scans/{scan_id}", headers=headers_a)
    assert ok_delete.status_code == 204
