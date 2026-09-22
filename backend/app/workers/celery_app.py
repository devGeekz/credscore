from celery import Celery
from app.config import settings

celery_app = Celery("credscore", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
)

celery_app.autodiscover_tasks(["app.workers"])