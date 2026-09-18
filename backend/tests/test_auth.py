def test_register_and_login(client, registered_org):
    resp = client.post(
        "/api/auth/login",
        data={"username": registered_org["admin_email"], "password": registered_org["admin_password"]},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_rejects_wrong_password(client, registered_org):
    resp = client.post(
        "/api/auth/login", data={"username": registered_org["admin_email"], "password": "wrong-password"}
    )
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, auth_headers, registered_org):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == registered_org["admin_email"]


def test_duplicate_registration_rejected(client, registered_org):
    resp = client.post(
        "/api/auth/register",
        json={
            "organization": {"name": "Another Co"},
            "admin_email": registered_org["admin_email"],
            "admin_password": "AnotherPass123",
            "admin_full_name": "Someone Else",
        },
    )
    assert resp.status_code == 400
