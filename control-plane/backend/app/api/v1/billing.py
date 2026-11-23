"""
Endpoints de Facturación Comercial SaaS de SOFIA Platform y Gestión de Suscripciones.
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.models.tenant import Tenant
from app.models.product import Subscription, ProductPlan
from app.services.billing_service import BillingService, SubscriptionState

router = APIRouter(prefix="/billing", tags=["Facturación Comercial SaaS"])


class AddonsUpdateRequest(BaseModel):
    extra_users: int = Field(0, ge=0, example=2)
    extra_storage_gb: int = Field(0, ge=0, example=10)


@router.get("/subscriptions/{tenant_id}", summary="Obtener estado de facturación y suscripción del tenant")
async def get_tenant_billing_status(tenant_id: UUID, db: AsyncSession = Depends(get_db_session)):
    stmt = (
        select(Subscription, ProductPlan, Tenant)
        .join(ProductPlan, Subscription.plan_id == ProductPlan.id)
        .join(Tenant, Subscription.tenant_id == Tenant.id)
        .where(Subscription.tenant_id == tenant_id)
    )
    res = await db.execute(stmt)
    record = res.first()

    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suscripción no encontrada para este tenant.")

    sub, plan, tenant = record

    calculation = BillingService.calculate_invoice_amount(
        base_price=float(plan.base_price),
        extra_users=sub.extra_users,
        extra_storage_gb=sub.extra_storage_gb,
    )

    evaluation = BillingService.evaluate_subscription_status(
        current_status=sub.status,
        period_end=sub.current_period_end,
        is_paid=(sub.status == SubscriptionState.ACTIVE),
    )

    return {
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "plan": {
            "code": plan.code,
            "name": plan.name,
            "tier": plan.tier,
            "base_price": float(plan.base_price),
        },
        "subscription": {
            "id": str(sub.id),
            "status": evaluation["new_status"],
            "is_service_blocked": evaluation["is_service_blocked"],
            "period_start": sub.current_period_start,
            "period_end": sub.current_period_end,
            "extra_users": sub.extra_users,
            "extra_storage_gb": sub.extra_storage_gb,
        },
        "billing_estimate": calculation,
    }


@router.post("/subscriptions/{tenant_id}/addons", summary="Actualizar complementos (usuarios y almacenamiento extra)")
async def update_subscription_addons(
    tenant_id: UUID,
    payload: AddonsUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(Subscription).where(Subscription.tenant_id == tenant_id)
    res = await db.execute(stmt)
    sub = res.scalar_one_or_none()

    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suscripción no encontrada.")

    sub.extra_users = payload.extra_users
    sub.extra_storage_gb = payload.extra_storage_gb
    await db.commit()
    await db.refresh(sub)

    return {
        "status": "UPDATED",
        "tenant_id": str(tenant_id),
        "extra_users": sub.extra_users,
        "extra_storage_gb": sub.extra_storage_gb,
    }
