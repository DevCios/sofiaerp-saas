"""
Tareas Celery Programadas de Facturación, Renovación y Morosidad (Dunning).
Evalúa diariamente todas las suscripciones activas, gestiona periodos de gracia (PAST_DUE)
y suspende de forma elegante (SUSPENDED) los tenants que superen los días de gracia sin pago.
"""
import logging
import os
from datetime import datetime, timezone
import psycopg2
from app.tasks.celery_app import celery_app
from app.services.billing_service import BillingService, SubscriptionState

logger = logging.getLogger(__name__)


def run_dunning_evaluation_sync(current_time: datetime | None = None) -> dict:
    """
    Ejecuta la máquina de estados de morosidad contra la base de datos central PostgreSQL:
    - ACTIVE con period_end vencido <= 5 días -> PAST_DUE (periodo de gracia)
    - ACTIVE / PAST_DUE con period_end vencido > 5 días -> SUSPENDED (bloquea tenant en Nginx)
    """
    pg_host = os.getenv("POSTGRES_HOST", "postgres")
    pg_port = int(os.getenv("POSTGRES_PORT", 5432))
    admin_user = os.getenv("POSTGRES_USER", "sofia_admin")
    admin_password = os.getenv("POSTGRES_PASSWORD", "sofia_pass")
    central_db = os.getenv("POSTGRES_DB", "sofia_central_db")

    now = current_time or datetime.now(timezone.utc)
    summary = {
        "evaluated": 0,
        "moved_to_past_due": 0,
        "suspended": 0,
        "reminders_due": 0,
        "timestamp": now.isoformat(),
    }

    conn = psycopg2.connect(
        dbname=central_db,
        user=admin_user,
        password=admin_password,
        host=pg_host,
        port=pg_port,
        connect_timeout=10,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id, s.tenant_id, s.status, s.current_period_end, t.slug, t.status
                FROM subscriptions s
                JOIN tenants t ON t.id = s.tenant_id
                WHERE s.status IN ('ACTIVE', 'TRIAL', 'PAST_DUE')
                  AND s.current_period_end IS NOT NULL;
                """
            )
            rows = cur.fetchall()
            summary["evaluated"] = len(rows)

            for sub_id, tenant_id, sub_status, period_end, slug, tenant_status in rows:
                if period_end.tzinfo is None:
                    period_end = period_end.replace(tzinfo=timezone.utc)

                days_until_expiry = (period_end - now).days
                if 0 <= days_until_expiry <= 5:
                    summary["reminders_due"] += 1
                    logger.info(
                        "[DUNNING] Recordatorio de renovación para tenant '%s' (vence en %d días).",
                        slug,
                        days_until_expiry,
                    )
                    continue

                evaluation = BillingService.evaluate_subscription_status(
                    current_status=sub_status,
                    period_end=period_end,
                    is_paid=False,
                    current_time=now,
                )
                new_status = evaluation["new_status"]

                if new_status != sub_status:
                    cur.execute(
                        "UPDATE subscriptions SET status = %s WHERE id = %s;",
                        (new_status, sub_id),
                    )
                    if new_status == SubscriptionState.PAST_DUE:
                        summary["moved_to_past_due"] += 1
                        logger.warning(
                            "[DUNNING] Tenant '%s' movido a PAST_DUE (periodo de gracia hasta %s).",
                            slug,
                            evaluation.get("grace_deadline"),
                        )
                    elif new_status == SubscriptionState.SUSPENDED:
                        summary["suspended"] += 1
                        if tenant_status != "SUSPENDED":
                            cur.execute(
                                "UPDATE tenants SET status = 'SUSPENDED' WHERE id = %s;",
                                (tenant_id,),
                            )
                        logger.error(
                            "[DUNNING] Tenant '%s' SUSPENDIDO por vencimiento del periodo de gracia.",
                            slug,
                        )
        conn.commit()
    finally:
        conn.close()

    return summary


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def evaluate_all_subscriptions_task(self):
    """Tarea diaria de Celery Beat para evaluar vencimientos y morosidad SaaS."""
    try:
        return run_dunning_evaluation_sync()
    except Exception as exc:
        logger.exception("Error ejecutando evaluación de morosidad: %s", exc)
        raise self.retry(exc=exc)
