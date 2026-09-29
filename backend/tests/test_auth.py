def _register(client, email="admin@example.com", password="Password123!"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": "Test Lender",
            "org_type": "mfi",
            "contact_email": f"ops-{email}",
            "admin_name": "Ada Admin",
            "admin_email": email,
            "password": password,
        },
    )


def test_register_returns_token_and_me_works(client):
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "admin"

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"


def test_duplicate_email_rejected(client):
    assert _register(client).status_code == 201
    assert _register(client).status_code == 400


def test_login_with_wrong_password_rejected(client):
    _register(client, email="login@example.com")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_returns_token(client):
    _register(client, email="goodlogin@example.com")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "goodlogin@example.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_me_requires_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)
