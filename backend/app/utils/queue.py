"""Shared Celery broker liveness probe.

Celery's publish/result retries block for ~110s when Redis is down — an API
request must never absorb that, so callers probe before touching Celery.
"""

import socket
from urllib.parse import urlparse

from app.config import settings


def broker_reachable(timeout: float = 0.25) -> bool:
    parsed = urlparse(settings.redis_url)
    address = (parsed.hostname or "localhost", parsed.port or 6379)
    try:
        with socket.create_connection(address, timeout=timeout):
            return True
    except OSError:
        return False
