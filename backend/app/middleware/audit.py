"""audit trail: one audit_logs row per successful api mutation.

fail-open by default — an audit hiccup must not 500 a real write; the
exception is logged instead. tenant/user come from the jwt, entity from
the path, entity_id from the path uuid or the response body's id."""

import json
import logging
from uuid import UUID

from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.security import decode_access_token

logger = logging.getLogger("credscore.audit")

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
ACTION_BY_METHOD = {"POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}


def _identity(request: Request) -> tuple[str, str] | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        payload = decode_access_token(auth_header[len("Bearer "):])
        tenant_id, user_id = payload.get("tenant_id"), payload.get("sub")
        if tenant_id and user_id:
            return tenant_id, user_id
    except JWTError:
        pass
    return None


def _entity(path: str) -> tuple[str, str | None]:
    parts = [p for p in path.split("/") if p and p not in ("api", "v1")]
    if not parts:
        return "unknown", None
    entity = parts[0]
    if len(parts) > 1:
        try:
            return entity, str(UUID(parts[1]))
        except ValueError:
            pass
    return entity, None


async def _body_bytes(response: Response) -> bytes:
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
    return b"".join(chunks)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in MUTATING_METHODS:
            return await call_next(request)

        response = await call_next(request)
        identity = _identity(request)
        if identity is None or response.status_code >= 400:
            return response

        # consume and rebuild so the created id in the body can be logged
        raw = await _body_bytes(response)
        rebuilt = Response(
            content=raw,
            status_code=response.status_code,
            headers={k: v for k, v in response.headers.items() if k.lower() != "content-length"},
            media_type=response.media_type,
        )

        tenant_id, user_id = identity
        entity, entity_id = _entity(request.url.path)
        if entity_id is None and raw:
            try:
                entity_id = str(json.loads(raw).get("id") or "") or None
            except ValueError:
                pass

        try:
            from app.database import SessionLocal
            from app.models import AuditLog

            db = SessionLocal()
            try:
                db.add(AuditLog(
                    tenant_id=UUID(tenant_id),
                    user_id=UUID(user_id),
                    action=ACTION_BY_METHOD[request.method],
                    entity=entity,
                    entity_id=entity_id,
                    details={"path": request.url.path, "status": response.status_code},
                ))
                db.commit()
            finally:
                db.close()
        except Exception:
            logger.exception("audit write failed for %s %s", request.method, request.url.path)

        return rebuilt
