"""
Configuración de la instancia de Celery para tareas asíncronas de SOFIA Platform.
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "sofia_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.provisioning",
        "app.tasks.backup_tasks",
        "app.tasks.billing_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutos máximo por tarea
    worker_prefetch_multiplier=1,
    beat_schedule={
        "sofia-daily-dunning-evaluation": {
            "task": "app.tasks.billing_tasks.evaluate_all_subscriptions_task",
            "schedule": crontab(hour=8, minute=0),  # 03:00 AM hora Perú (UTC-5)
        },
    },
)
