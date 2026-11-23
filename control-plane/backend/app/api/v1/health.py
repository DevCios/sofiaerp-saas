"""
Endpoint de Health Check y Telemetría de Disponibilidad.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Salud & Diagnóstico"])


@router.get("", summary="Verificar estado de salud general de la plataforma")
async def check_health(db: AsyncSession = Depends(get_db_session)):
    """
    Retorna el estado operativo del Control Plane y verifica conectividad con PostgreSQL.
    """
    db_status = "unhealthy"
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status = "healthy"
    except Exception as e:
        db_status = f"unreachable: {str(e)}"

    return {
        "status": "online" if db_status == "healthy" else "degraded",
        "platform": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "components": {
            "api": "healthy",
            "database": db_status,
        }
    }
