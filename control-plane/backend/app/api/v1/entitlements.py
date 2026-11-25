"""
Endpoints para Consulta de Entitlements y Configuración de Branding por Tenant.
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.models.tenant import Tenant
from app.services.entitlement_service import EntitlementService, EntitlementCode

router = APIRouter(prefix="/tenants", tags=["Entitlements & Branding"])


class BrandingUpdateRequest(BaseModel):
    logo_url: Optional[str] = None
    primary_color: Optional[str] = "#3B82F6"
    custom_company_name: Optional[str] = None
    enable_white_label: bool = False


@router.get("/{tenant_id}/entitlements", summary="Consultar capacidades contratadas del tenant")
async def get_tenant_entitlements(tenant_id: UUID, db: AsyncSession = Depends(get_db_session)):
    entitlements_info = await EntitlementService.get_tenant_entitlements(tenant_id, db)
    return entitlements_info


@router.get("/by-db/{db_name}/entitlements", summary="Consultar límites y capacidades por nombre de base de datos (Odoo Runtime)")
async def get_tenant_entitlements_by_db(db_name: str, db: AsyncSession = Depends(get_db_session)):
    """
    Endpoint interno invocado por el runtime Odoo (sofia_auth_bridge) para validar
    cuotas activas de usuarios y almacenamiento sin depender del UUID del tenant.
    """
    stmt = select(Tenant).where(Tenant.database_name == db_name)
    tenant = (await db.execute(stmt)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant con base de datos '{db_name}' no encontrado.",
        )

    entitlements_info = await EntitlementService.get_tenant_entitlements(tenant.id, db)
    entitlements_info["tenant_id"] = str(tenant.id)
    entitlements_info["tenant_slug"] = tenant.slug
    entitlements_info["tenant_status"] = tenant.status
    return entitlements_info


@router.post("/{tenant_id}/branding", summary="Actualizar personalización visual y marca del tenant")
async def update_tenant_branding(
    tenant_id: UUID,
    payload: BrandingUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Actualiza la configuración visual de la empresa validando las capacidades contratadas.
    Aplica degradación no destructiva si la suscripción no cuenta con capacidades avanzadas.
    """
    entitlements_info = await EntitlementService.get_tenant_entitlements(tenant_id, db)
    active_entitlements = entitlements_info["entitlements"]

    applied_branding = EntitlementService.apply_branding_with_entitlements(
        active_entitlements=active_entitlements,
        logo_url=payload.logo_url,
        primary_color=payload.primary_color,
        custom_company_name=payload.custom_company_name,
        enable_white_label=payload.enable_white_label,
    )

    return {
        "status": "UPDATED",
        "tenant_id": str(tenant_id),
        "branding": applied_branding,
    }
