# -*- coding: utf-8 -*-
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sofia_sunat_gateway",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.dispatcher"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Lima",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.dispatcher.dispatch_document_task": {"queue": "sunat_realtime"},
        "app.tasks.dispatcher.recover_cdr_task": {"queue": "sunat_retry"},
        "app.tasks.dispatcher.send_webhook_task": {"queue": "sunat_webhooks"},
        "app.tasks.dispatcher.sweep_retry_and_night_queue": {"queue": "sunat_night_batch"},
        "app.tasks.dispatcher.check_deadline_alerts": {"queue": "sunat_night_batch"},
        "app.tasks.dispatcher.sync_daily_exchange_rate_task": {"queue": "sunat_night_batch"},
    },
    beat_schedule={
        # Barrido de cola de reintentos y ventana nocturna cada 2 minutos
        "sweep-sunat-retry-and-night-queue": {
            "task": "app.tasks.dispatcher.sweep_retry_and_night_queue",
            "schedule": 120.0,
        },
        # Monitor de alertas de plazo legal (24h / 48h antes de los 3 días) cada 30 minutos
        "check-sunat-deadline-alerts": {
            "task": "app.tasks.dispatcher.check_deadline_alerts",
            "schedule": crontab(minute="*/30"),
        },
        # Sincronización diaria del Tipo de Cambio oficial SUNAT (07:30 AM hora Lima)
        "sync-daily-sunat-exchange-rate": {
            "task": "app.tasks.dispatcher.sync_daily_exchange_rate_task",
            "schedule": crontab(hour=7, minute=30),
        },
    },
)
