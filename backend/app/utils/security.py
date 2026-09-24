from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt, JWTError

from app.config import settings

ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    # bcrypt truncates at 72 bytes silently otherwise; enforce it explicitly.
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))


def _parse_expires_in(expires_in: str) -> timedelta:
    """Turns '7d', '24h', '30m' into a timedelta. Defaults to 7 days on a bad value."""
    try:
        unit = expires_in[-1]
        amount = int(expires_in[:-1])
        if unit == "d":
            return timedelta(days=amount)
        if unit == "h":
            return timedelta(hours=amount)
        if unit == "m":
            return timedelta(minutes=amount)
    except (ValueError, IndexError):
        pass
    return timedelta(days=7)


def create_access_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + _parse_expires_in(settings.jwt_expires_in)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
