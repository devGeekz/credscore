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


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_admin_adds_team_member_and_they_can_log_in(client):
    token = _register(client, email="teamadmin@example.com").json()["access_token"]
    created = client.post(
        "/api/v1/auth/users",
        headers=_auth(token),
        json={
            "name": "Osei Officer",
            "email": "officer@example.com",
            "password": "Password123!",
            "role": "underwriter",
        },
    )
    assert created.status_code == 201
    assert created.json()["role"] == "underwriter"
    assert created.json()["tenant_id"]  # belongs to admin's tenant

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "officer@example.com", "password": "Password123!"},
    )
    assert login.status_code == 200

    team = client.get("/api/v1/auth/users", headers=_auth(token))
    assert {u["email"] for u in team.json()} == {
        "teamadmin@example.com",
        "officer@example.com",
    }


def test_non_admin_cannot_add_team_member(client):
    token = _register(client, email="boss@example.com").json()["access_token"]
    client.post(
        "/api/v1/auth/users",
        headers=_auth(token),
        json={
            "name": "Osei Officer",
            "email": "officer2@example.com",
            "password": "Password123!",
            "role": "underwriter",
        },
    )
    officer = client.post(
        "/api/v1/auth/login",
        json={"email": "officer2@example.com", "password": "Password123!"},
    ).json()["access_token"]

    denied = client.post(
        "/api/v1/auth/users",
        headers=_auth(officer),
        json={
            "name": "Sneaky",
            "email": "sneaky@example.com",
            "password": "Password123!",
            "role": "admin",
        },
    )
    assert denied.status_code == 403


def test_duplicate_team_email_rejected(client):
    token = _register(client, email="dupadmin@example.com").json()["access_token"]
    body = {
        "name": "Twice",
        "email": "twice@example.com",
        "password": "Password123!",
        "role": "viewer",
    }
    assert client.post("/api/v1/auth/users", headers=_auth(token), json=body).status_code == 201
    assert client.post("/api/v1/auth/users", headers=_auth(token), json=body).status_code == 409


def test_invalid_role_rejected(client):
    token = _register(client, email="roleadmin@example.com").json()["access_token"]
    bad = client.post(
        "/api/v1/auth/users",
        headers=_auth(token),
        json={
            "name": "Bad Role",
            "email": "badrole@example.com",
            "password": "Password123!",
            "role": "superuser",
        },
    )
    assert bad.status_code == 422


def _make_member(client, admin_token, email, role):
    created = client.post(
        "/api/v1/auth/users",
        headers=_auth(admin_token),
        json={"name": role.title(), "email": email, "password": "Password123!", "role": role},
    )
    assert created.status_code == 201
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    ).json()["access_token"]


def test_viewer_is_read_only(client):
    admin = _register(client, email="roadmin@example.com").json()["access_token"]
    viewer = _make_member(client, admin, "viewer1@example.com", "viewer")

    # reads still work
    assert client.get("/api/v1/dashboard/stats", headers=_auth(viewer)).status_code == 200
    # writes are rejected
    merchant = client.post(
        "/api/v1/merchants",
        headers=_auth(viewer),
        json={"full_name": "Nope", "phone": "+233200000002"},
    )
    assert merchant.status_code == 403
    assert client.put(
        "/api/v1/settings",
        headers=_auth(viewer),
        json={"webhook_url": ""},
    ).status_code == 403
    assert client.post("/api/v1/auth/api-keys", headers=_auth(viewer)).status_code == 403


def test_underwriter_can_write_but_not_admin_things(client):
    admin = _register(client, email="uwadmin@example.com").json()["access_token"]
    officer = _make_member(client, admin, "uw@example.com", "underwriter")

    merchant = client.post(
        "/api/v1/merchants",
        headers=_auth(officer),
        json={"full_name": "Allowed", "phone": "+233200000003"},
    )
    assert merchant.status_code == 201
    # admin-only: settings, api keys, team
    assert client.put(
        "/api/v1/settings", headers=_auth(officer), json={"webhook_url": ""}
    ).status_code == 403
    assert client.post("/api/v1/auth/api-keys", headers=_auth(officer)).status_code == 403
    assert client.post(
        "/api/v1/auth/users",
        headers=_auth(officer),
        json={"name": "X", "email": "x@example.com", "password": "Password123!", "role": "viewer"},
    ).status_code == 403
