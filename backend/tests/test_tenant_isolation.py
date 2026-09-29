import uuid

from app.models import Statement


def _register(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": f"Lender {email}",
            "org_type": "mfi",
            "contact_email": f"ops-{email}",
            "admin_name": "Admin",
            "admin_email": email,
            "password": "Password123!",
        },
    )
    assert response.status_code == 201
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}


def _create_merchant(client, headers, name="Kwame Mensah"):
    response = client.post(
        "/api/v1/merchants",
        headers=headers,
        json={"full_name": name, "phone": "+233201234567"},
    )
    assert response.status_code == 201
    return response.json()


def test_merchant_not_visible_across_tenants(client):
    tenant_a = _register(client, "lender-a@example.com")
    tenant_b = _register(client, "lender-b@example.com")

    merchant = _create_merchant(client, tenant_a)

    # a sees it
    assert client.get(
        f"/api/v1/merchants/{merchant['id']}", headers=tenant_a
    ).status_code == 200

    # b gets 404, not 403 — no existence leak across tenants
    assert client.get(
        f"/api/v1/merchants/{merchant['id']}", headers=tenant_b
    ).status_code == 404
    assert client.get("/api/v1/merchants", headers=tenant_b).json() == []


def test_statement_not_visible_across_tenants(client, db_session):
    tenant_a = _register(client, "lender-c@example.com")
    tenant_b = _register(client, "lender-d@example.com")

    merchant = _create_merchant(client, tenant_a)
    statement = Statement(
        merchant_id=uuid.UUID(merchant["id"]),
        source_channel="web_upload",
        file_url="statements/x/y.csv",
        parse_status="parsed",
    )
    db_session.add(statement)
    db_session.commit()

    assert client.get(
        f"/api/v1/statements/{statement.id}", headers=tenant_a
    ).status_code == 200
    assert client.get(
        f"/api/v1/statements/{statement.id}", headers=tenant_b
    ).status_code == 404


def test_upload_rejects_merchant_from_another_tenant(client):
    tenant_a = _register(client, "lender-e@example.com")
    tenant_b = _register(client, "lender-f@example.com")
    merchant = _create_merchant(client, tenant_a)

    response = client.post(
        "/api/v1/statements/upload",
        headers=tenant_b,
        data={"merchant_id": merchant["id"]},
        files={"file": ("statement.csv", b"Date,Amount\n01/09/2026,10.00", "text/csv")},
    )
    assert response.status_code == 404
