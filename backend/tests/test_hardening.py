"""hardening: upload rate limit, security headers, consent export,
statement requeue, and whatsapp payload validation."""

from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "momo_sample.csv"

CSV_ROW = "Date,Type,Amount,Balance,Counter Party,Reason,Payment Ref\n01/09/2026,Debit,10.00,100.00,X,coffee,r1\n"


def _register(client, email="hardening@example.com"):
    body = client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": "Hardening Lender",
            "org_type": "mfi",
            "contact_email": f"ops-{email}",
            "admin_name": "Ada",
            "admin_email": email,
            "password": "Password123!",
        },
    ).json()
    return {"Authorization": f"Bearer {body['access_token']}"}


def test_security_headers_on_every_response(client):
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_twenty_first_upload_is_rate_limited(client):
    import uuid

    headers = _register(client, "ratelimit@example.com")
    codes = []
    for _ in range(21):
        response = client.post(
            "/api/v1/statements/upload",
            headers=headers,
            data={"merchant_id": str(uuid.uuid4())},
            files={"file": ("s.csv", CSV_ROW.encode(), "text/csv")},
        )
        codes.append(response.status_code)
    assert codes[-1] == 429
    assert all(code == 404 for code in codes[:-1])  # merchant missing, still counted


def test_consent_export_csv(client):
    headers = _register(client, "consent@example.com")
    client.post(
        "/api/v1/merchants",
        headers=headers,
        json={"full_name": "Kwame Mensah", "phone": "+233201234567"},
    )

    response = client.get("/api/v1/dashboard/consent-export", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "consent_verified" in response.text
    assert "Kwame Mensah" in response.text


def test_requeue_flips_failed_to_pending(client, db_session):
    import uuid

    from app.models import Statement
    from app.services.storage_service import upload_statement_file

    headers = _register(client, "requeue@example.com")
    merchant = client.post(
        "/api/v1/merchants",
        headers=headers,
        json={"full_name": "Ama Serwaa", "phone": "+233209876543"},
    ).json()

    key = upload_statement_file(FIXTURE.read_bytes(), "momo.csv", "test-tenant")
    statement = Statement(
        merchant_id=uuid.UUID(merchant["id"]),
        source_channel="web_upload",
        file_url=key,
        parse_status="failed",
        parse_error="boom",
    )
    db_session.add(statement)
    db_session.commit()
    statement_id = statement.id

    response = client.post(
        f"/api/v1/statements/{statement_id}/requeue", headers=headers
    )
    assert response.status_code == 202
    body = response.json()
    assert body["parse_status"] in ("pending", "parsed")

    # a parsed statement cannot be requeued — the inline parse detached our
    # instance (it closed the shared session), so re-query
    row = db_session.query(Statement).filter(Statement.id == statement_id).one()
    row.parse_status = "parsed"
    db_session.commit()
    assert (
        client.post(f"/api/v1/statements/{statement_id}/requeue", headers=headers)
        .status_code == 409
    )


def test_requeue_is_tenant_scoped(client, db_session):
    import uuid

    from app.models import Statement

    headers = _register(client, "requeue-a@example.com")
    other = _register(client, "requeue-b@example.com")
    merchant = client.post(
        "/api/v1/merchants",
        headers=headers,
        json={"full_name": "Kofi Owusu", "phone": "+233205551234"},
    ).json()

    statement = Statement(
        merchant_id=uuid.UUID(merchant["id"]),
        source_channel="web_upload",
        file_url="statements/x/y.csv",
        parse_status="failed",
    )
    db_session.add(statement)
    db_session.commit()

    assert (
        client.post(f"/api/v1/statements/{statement.id}/requeue", headers=other)
        .status_code == 404
    )


def test_whatsapp_payload_must_be_a_json_object(client):
    # a body that is not a json object now fails with 422, not a 500
    response = client.post(
        "/api/v1/webhooks/whatsapp", content=b"not json at all",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422

    response = client.post("/api/v1/webhooks/whatsapp", json={"object": "whatsapp_business_account", "entry": []})
    assert response.status_code == 200
