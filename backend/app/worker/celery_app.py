"""
AtlasOS Celery Application Instance.
"""

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "atlasos_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.worker.tasks.compression",
        "app.worker.tasks.retention",
        "app.worker.tasks.evaluation",
        "app.worker.tasks.webhooks",
    ],
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 mins
)

from app.worker.beat_schedule import BEAT_SCHEDULE
celery_app.conf.beat_schedule = BEAT_SCHEDULE


if __name__ == "__main__":
    celery_app.start()
