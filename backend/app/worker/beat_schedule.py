"""
Celery Beat Schedule configuration for AtlasOS.
"""

from celery.schedules import crontab

BEAT_SCHEDULE = {
    "compress-memories-daily": {
        "task": "app.worker.tasks.compression.compress_all_tenants_memories",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    "decay-importance-scores-daily": {
        "task": "app.worker.tasks.retention.decay_importance_scores",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    "sweep-expired-memories-hourly": {
        "task": "app.worker.tasks.retention.sweep_expired_memories",
        "schedule": crontab(minute=0),  # Hourly
    },
    "run-system-evaluations-daily": {
        "task": "app.worker.tasks.evaluation.run_system_evaluations",
        "schedule": crontab(hour=4, minute=0),  # Daily at 4 AM
    },
}
