"""
Two Redis-backed concerns: OTP consent (CredScore's own consent record —
separate from any telco USSD OTP) and message idempotency (Meta retries
webhook deliveries on anything but a fast 200).
"""

import random
import string

from app.utils.redis_client import redis_client

OTP_TTL_SECONDS = 600
SEEN_MESSAGE_TTL_SECONDS = 60 * 60 * 24


def _otp_key(phone: str) -> str:
    return f"whatsapp:otp:{phone}"


def generate_and_store_otp(phone: str) -> str:
    code = "".join(random.choices(string.digits, k=6))
    redis_client.set(_otp_key(phone), code, ex=OTP_TTL_SECONDS)
    return code


def verify_otp(phone: str, submitted_code: str) -> bool:
    key = _otp_key(phone)
    stored = redis_client.get(key)
    if stored is None:
        return False
    if stored == submitted_code.strip():
        redis_client.delete(key)
        return True
    return False


def is_duplicate_message(wamid: str) -> bool:
    key = f"whatsapp:seen:{wamid}"
    was_set = redis_client.set(key, "1", nx=True, ex=SEEN_MESSAGE_TTL_SECONDS)
    return not was_set