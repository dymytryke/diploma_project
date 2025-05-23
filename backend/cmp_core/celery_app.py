from celery import Celery
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
)
