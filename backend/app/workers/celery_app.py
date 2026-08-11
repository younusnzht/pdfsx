"""
Celery app. Runs as a separate systemd service on the VPS (no Docker) —
see deploy/statement-extractor-worker.service.
"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "statement_extractor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Toronto",
    enable_utc=True,
    task_track_started=True,
    # OCR jobs can be slow — don't let one tenant's huge scanned statement
    # starve the queue indefinitely.
    task_time_limit=600,
    task_soft_time_limit=540,
)
