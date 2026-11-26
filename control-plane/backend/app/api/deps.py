"""
Dependencias de Seguridad, Autenticación JWT (Superadmin) y Comunicación Interna entre Servicios.
"""
import hmac
from typing import Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_superadmin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Valida que la petición incluya un token JWT válido perteneciente a un Superadministrador activo.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Token sin sujeto (sub).")
        user_uuid = UUID(str(user_id))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == user_uuid)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not user.is_active or not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren privilegios de Superadministrador activo.",
        )

    return user


async def verify_admin_or_internal(
    x_internal_service_key: Optional[str] = Header(default=None, alias="X-Internal-Service-Key"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> str:
    """
    Permite acceso autorizado a:
    1. Servicios internos de confianza en sofia-net-app (Odoo Runtime / Checkout) mediante X-Internal-Service-Key.
    2. Superadministradores autenticados mediante JWT Bearer desde /admin.
    """
    if x_internal_service_key and settings.INTERNAL_SERVICE_KEY:
        if hmac.compare_digest(x_internal_service_key, settings.INTERNAL_SERVICE_KEY):
            return "internal_service"

    user = await get_current_superadmin(credentials=credentials, db=db)
    return str(user.id)
