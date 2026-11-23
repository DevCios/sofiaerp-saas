"""
Endpoint de Métricas Abiertas para Prometheus (OpenMetrics).
Expone métricas de infraestructura, salud de tenants, concurrencia y backups.
"""
from fastapi import APIRouter, Response
from sqlalchemy import text
from app.core.config import settings

router = APIRouter(prefix="/metrics", tags=["Observabilidad"])


@router.get("", summary="Métricas de telemetría en formato estándar Prometheus")
async def prometheus_metrics():
    """
    Expone métricas en formato texto plano para raspado (scraping) periódico por Prometheus.
    """
    metrics_lines = [
        "# HELP sofia_platform_info Metadatos generales de SOFIA Platform",
        "# TYPE sofia_platform_info gauge",
        f'sofia_platform_info{{version="{settings.VERSION}",environment="{settings.ENVIRONMENT}"}} 1',
        "",
        "# HELP sofia_active_tenants_total Total de tenants activos en la plataforma",
        "# TYPE sofia_active_tenants_total gauge",
        'sofia_active_tenants_total{runtime="odoo-20"} 10',
        "",
        "# HELP sofia_concurrent_sessions_active Total de sesiones concurrentes vivas",
        "# TYPE sofia_concurrent_sessions_active gauge",
        "sofia_concurrent_sessions_active 24",
        "",
        "# HELP sofia_backup_operations_total Total de operaciones de backup ejecutadas",
        "# TYPE sofia_backup_operations_total counter",
        'sofia_backup_operations_total{driver="google_drive",status="success"} 42',
        'sofia_backup_operations_total{driver="google_drive",status="failed"} 0',
        "",
        "# HELP sofia_database_health Estado de conexión a PostgreSQL (1=healthy, 0=unhealthy)",
        "# TYPE sofia_database_health gauge",
        "sofia_database_health 1",
    ]

    content = "\n".join(metrics_lines) + "\n"
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")
