"""Webhook delivery: HMAC signature (the lender-side verification recipe),
HTTP attempt against a real local receiver, and the retry policy."""

import hashlib
import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import pytest

import app.database
from app.models import Tenant, WebhookLog
from app.services.webhook_service import MAX_ATTEMPTS, attempt_delivery, sign_body
from app.workers import webhook_tasks
from app.workers.webhook_tasks import deliver_webhook_task

RECEIVED: dict = {}


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        RECEIVED.clear()
        RECEIVED["headers"] = dict(self.headers)
        RECEIVED["body"] = self.rfile.read(length)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


@pytest.fixture()
def receiver():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/score"
    server.shutdown()


@pytest.fixture()
def use_test_db(db_session, monkeypatch):
    """attempt_delivery opens its own session — point it at the SQLite fixture."""
    monkeypatch.setattr(app.database, "SessionLocal", lambda: db_session)
    return db_session


def _log(db, url=None, secret="test-secret", attempts="0", payload=None) -> WebhookLog:
    tenant = Tenant(
        name="Wh Lender",
        org_type="mfi",
        contact_email="ops@example.com",
        webhook_url=url,
        webhook_secret=secret,
    )
    db.add(tenant)
    db.commit()
    log = WebhookLog(
        tenant_id=tenant.id,
        event_type="score.completed",
        payload=payload or {"event": "score.completed", "score": {"risk_tag": "strong"}},
        attempts=attempts,
        delivered=False,
    )
    db.add(log)
    db.commit()
    return log


def _reload(db, log_id) -> WebhookLog:
    """attempt_delivery closed the session, detaching our instance."""
    if isinstance(log_id, str):
        from uuid import UUID

        log_id = UUID(log_id)
    return db.query(WebhookLog).filter(WebhookLog.id == log_id).one()


def test_signature_matches_rfc4231_known_answer():
    # RFC 4231 test case 1: key = 0x0b * 20, data = "Hi There"
    signature = sign_body("Hi There", "\x0b" * 20)
    assert signature == (
        "sha256=b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"
    )


def test_attempt_delivery_posts_verifiable_signature(use_test_db, receiver):
    log_id = _log(use_test_db, url=receiver, payload={"score": {"risk_tag": "strong"}}).id
    attempt_delivery(log_id)

    assert RECEIVED, "receiver got nothing"
    log = _reload(use_test_db, log_id)
    assert log.delivered is True
    assert log.response_status == "200"

    # This is exactly what a lender does on their end.
    body = RECEIVED["body"]
    expected = "sha256=" + hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(RECEIVED["headers"]["X-CredScore-Signature"], expected)
    assert RECEIVED["headers"]["X-CredScore-Event"] == "score.completed"
    assert json.loads(body)["score"]["risk_tag"] == "strong"


def test_retries_in_production(use_test_db, monkeypatch):
    log_id = _log(use_test_db, url="http://127.0.0.1:1/unreachable").id
    monkeypatch.setattr(webhook_tasks, "settings", SimpleNamespace(environment="production"))

    result = deliver_webhook_task.apply(args=[str(log_id)])

    log = _reload(use_test_db, log_id)
    # eager mode runs retries synchronously: it burned every attempt, not one
    assert int(log.attempts) == MAX_ATTEMPTS
    assert log.delivered is False
    assert result.state == "SUCCESS"  # gave up cleanly, worker not poisoned


def test_stops_after_first_failure_in_development(use_test_db, monkeypatch):
    log_id = _log(use_test_db, url="http://127.0.0.1:1/unreachable").id
    monkeypatch.setattr(webhook_tasks, "settings", SimpleNamespace(environment="development"))

    deliver_webhook_task.apply(args=[str(log_id)])

    log = _reload(use_test_db, log_id)
    assert log.attempts == "1"  # no broker locally → no retry loop


def test_gives_up_after_three_attempts(use_test_db):
    log_id = _log(use_test_db, url="http://127.0.0.1:1/unreachable", attempts="2").id

    result = deliver_webhook_task.apply(args=[str(log_id)])

    log = _reload(use_test_db, log_id)
    assert int(log.attempts) == MAX_ATTEMPTS
    assert log.delivered is False
    assert result.state == "SUCCESS"  # gave up without erroring the worker


def test_settings_endpoint_validates_webhook_url(client, monkeypatch):
    from app.config import settings as config_settings

    token = client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": "Wh Lender",
            "org_type": "mfi",
            "contact_email": "ops@example.com",
            "admin_name": "Ada",
            "admin_email": "webhook-admin@example.com",
            "password": "Password123!",
        },
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # a bad scheme or a credential-bearing URL is refused everywhere
    for bad_url in ("ftp://example.com/hook", "not-a-url",
                    "https://user:pass@hooks.example.com/hook"):
        response = client.put(
            "/api/v1/settings", json={"webhook_url": bad_url}, headers=headers
        )
        assert response.status_code == 400, bad_url

    # private/loopback targets are refused in production (SSRF)
    monkeypatch.setattr(config_settings, "environment", "production")
    for bad_url in ("http://localhost:9999/hook", "http://10.0.0.5/hook",
                    "http://169.254.169.254/latest/meta-data"):
        response = client.put(
            "/api/v1/settings", json={"webhook_url": bad_url}, headers=headers
        )
        assert response.status_code == 400, bad_url

    # ...but a local receiver is the whole dev workflow
    monkeypatch.setattr(config_settings, "environment", "development")
    response = client.put(
        "/api/v1/settings",
        json={"webhook_url": "http://127.0.0.1:8899/hook"},
        headers=headers,
    )
    assert response.status_code == 200

    response = client.put(
        "/api/v1/settings",
        json={"webhook_url": "https://hooks.whlender.example.com/credscore"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["webhook_url"] == "https://hooks.whlender.example.com/credscore"
    assert body["webhook_secret"]  # generated on first save

    # second save keeps the same secret unless rotation is requested
    response = client.put(
        "/api/v1/settings",
        json={"webhook_url": "https://hooks.whlender.example.com/credscore",
              "rotate_webhook_secret": True},
        headers=headers,
    )
    assert response.json()["webhook_secret"] != body["webhook_secret"]
