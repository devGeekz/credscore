"""audit trail: one row per successful mutation, none for reads or failures."""

from app.models import AuditLog


def _register(client):
    body = client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": "Audit Lender",
            "org_type": "mfi",
            "contact_email": "ops-audit@example.com",
            "admin_name": "Ada",
            "admin_email": "audit-admin@example.com",
            "password": "Password123!",
        },
    ).json()
    return {"Authorization": f"Bearer {body['access_token']}"}


def test_create_is_audited_with_entity_id(client, db_session):
    headers = _register(client)

    merchant = client.post(
        "/api/v1/merchants",
        headers=headers,
        json={"full_name": "Kwame Mensah", "phone": "+233201234567"},
    ).json()

    rows = db_session.query(AuditLog).filter(AuditLog.action == "create").all()
    row = next(r for r in rows if r.entity == "merchants")
    assert row.entity_id == merchant["id"]
    assert row.tenant_id is not None
    assert row.user_id is not None
    assert row.details["path"] == "/api/v1/merchants"
    assert row.details["status"] == 201


def test_failed_mutation_is_not_audited(client, db_session):
    headers = _register(client)

    client.post(
        "/api/v1/merchants",
        headers=headers,
        json={"full_name": "X" * 5},  # valid
    )
    before = db_session.query(AuditLog).count()
    client.post("/api/v1/merchants", headers=headers, json={})  # 422

    assert db_session.query(AuditLog).count() == before


def test_reads_are_not_audited(client, db_session):
    headers = _register(client)

    client.get("/api/v1/merchants", headers=headers)

    assert db_session.query(AuditLog).count() == 0
