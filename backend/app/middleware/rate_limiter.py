from fastapi import Request
from jose import JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.utils.security import decode_access_token


def _rate_limit_key(request: Request) -> str:
    """per-tenant limiting once authenticated (decoded from the jwt, no db
    hit needed); falls back to ip for unauthenticated routes like /login."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        try:
            payload = decode_access_token(token)
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                return f"tenant:{tenant_id}"
        except JWTError:
            pass
    return get_remote_address(request)


limiter = Limiter(
    key_func=_rate_limit_key,
    storage_uri=settings.rate_limit_storage_uri or settings.redis_url,
    default_limits=["100/minute"],
)