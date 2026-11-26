"""
Endpoint de Métricas Abiertas para Prometheus (OpenMetrics).
Expone métricas reales de infraestructura, salud de tenants y backups.
"""
import os
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db_session
from app.api.deps import verify_admin_or_internal
from app.models.tenant import Tenant

router = APIRouter(prefix="/metrics", tags=["Observabilidad"])


@router.get("", summary="Métricas de telemetría en formato estándar Prometheus")
async def prometheus_metrics(
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_admin_or_internal),
):
    """
    Expone métricas reales en formato texto plano OpenMetrics/Prometheus.
    Protegido mediante JWT Superadmin o clave de servicio interna.
    """
    db_healthy = 0
    active_tenants = 0
    suspended_tenants = 0

    try:
        if (await db.execute(text("SELECT 1"))).scalar() == 1:
            db_healthy = 1
        active_tenants = (
            await db.execute(select(func.count(Tenant.id)).where(Tenant.status == "ACTIVE"))
        ).scalar() or 0
        suspended_tenants = (
            await db.execute(select(func.count(Tenant.id)).where(Tenant.status == "SUSPENDED"))
        ).scalar() or 0
    except Exception:
        db_healthy = 0

    backups_count = 0
    if os.path.exists(settings.SOFIA_BACKUPS_DIR):
        for _, _, files in os.walk(settings.SOFIA_BACKUPS_DIR):
            backups_count += sum(1 for f in files if f.endswith(".sql.gz") or f.endswith(".sql"))

    metrics_lines = [
        "# HELP sofia_platform_info Metadatos generales de SOFIA Platform",
        "# TYPE sofia_platform_info gauge",
        f'sofia_platform_info{{version="{settings.VERSION}",environment="{settings.ENVIRONMENT}"}} 1',
        "",
        "# HELP sofia_active_tenants_total Total de tenants activos en la plataforma",
        "# TYPE sofia_active_tenants_total gauge",
        f'sofia_active_tenants_total{{runtime="odoo-20"}} {active_tenants}',
        "",
        "# HELP sofia_suspended_tenants_total Total de tenants suspendidos por mora",
        "# TYPE sofia_suspended_tenants_total gauge",
        f'sofia_suspended_tenants_total{{runtime="odoo-20"}} {suspended_tenants}',
        "",
        "# HELP sofia_backup_files_total Total de archivos de respaldo almacenados localmente",
        "# TYPE sofia_backup_files_total gauge",
        f"sofia_backup_files_total {backups_count}",
        "",
        "# HELP sofia_database_health Estado de conexión a PostgreSQL (1=healthy, 0=unhealthy)",
        "# TYPE sofia_database_health gauge",
        f"sofia_database_health {db_healthy}",
    ]

    content = "\n".join(metrics_lines) + "\n"
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")
