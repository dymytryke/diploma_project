from celery import Celery
from celery.schedules import crontab
from cmp_core.core.config import settings

celery_app = Celery(
    "cmp_core",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[  # ← explicitly include your task module
        "cmp_core.tasks.pulumi",
    ],
)

# optional: if you want JSON-only and avoid pickle payloads
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
)

celery_app.conf.beat_schedule = {
    # run reconciliation for all projects every 5 minutes
    "reconcile-all-projects-every-5min": {
        "task": "cmp_core.tasks.reconcile_all_projects",
        "schedule": crontab(minute="*/5"),
    },
}
