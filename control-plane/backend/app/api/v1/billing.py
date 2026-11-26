"""
Endpoints de Facturación Comercial SaaS de SOFIA Platform y Gestión de Suscripciones.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.api.deps import get_current_superadmin, verify_admin_or_internal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.product import Subscription, ProductPlan
from app.services.billing_service import BillingService, SubscriptionState

router = APIRouter(prefix="/billing", tags=["Facturación Comercial SaaS"])


class AddonsUpdateRequest(BaseModel):
    extra_users: int = Field(0, ge=0, example=2)
    extra_storage_gb: int = Field(0, ge=0, example=10)


class UpgradePlanRequest(BaseModel):
    plan_code: str = Field(..., example="SOFIA-PLAN-PRO")


class RenewSubscriptionRequest(BaseModel):
    cycle: str = Field("monthly", pattern="^(monthly|annual)$", example="monthly")
    payment_reference: Optional[str] = Field(None, example="MP-123456789")


@router.get("/subscriptions/{tenant_id}", summary="Obtener estado de facturación y suscripción del tenant")
async def get_tenant_billing_status(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_admin_or_internal),
):
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
    _auth: str = Depends(verify_admin_or_internal),
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


@router.post("/subscriptions/{tenant_id}/upgrade", summary="Cambiar o mejorar el plan comercial del tenant")
async def upgrade_subscription_plan(
    tenant_id: UUID,
    payload: UpgradePlanRequest,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_admin_or_internal),
):
    sub = (await db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))).scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suscripción no encontrada.")

    plan = (await db.execute(select(ProductPlan).where(ProductPlan.code == payload.plan_code))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan '{payload.plan_code}' no encontrado.")

    sub.plan_id = plan.id
    sub.status = SubscriptionState.ACTIVE
    await db.commit()
    await db.refresh(sub)

    return {
        "status": "UPGRADED",
        "tenant_id": str(tenant_id),
        "new_plan_code": plan.code,
        "new_tier": plan.tier,
        "max_users": plan.max_users + sub.extra_users,
    }


@router.post("/subscriptions/{tenant_id}/renew", summary="Renovar suscripción y reactivar tenant suspendido")
async def renew_subscription(
    tenant_id: UUID,
    payload: RenewSubscriptionRequest,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_admin_or_internal),
):
    sub = (await db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))).scalar_one_or_none()
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()

    if not sub or not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant o suscripción no encontrada.")

    now = datetime.now(timezone.utc)
    days_to_add = 365 if payload.cycle == "annual" else 30
    base_date = sub.current_period_end if (sub.current_period_end and sub.current_period_end > now) else now

    sub.current_period_start = now
    sub.current_period_end = base_date + timedelta(days=days_to_add)
    sub.status = SubscriptionState.ACTIVE

    tenant.subscription_expires_at = sub.current_period_end
    tenant.payment_status = "PAID"
    tenant.last_payment_date = now
    if payload.payment_reference:
        tenant.last_payment_reference = payload.payment_reference
    if tenant.status == "SUSPENDED":
        tenant.status = "ACTIVE"

    await db.commit()
    await db.refresh(sub)

    return {
        "status": "RENEWED",
        "tenant_id": str(tenant_id),
        "tenant_status": tenant.status,
        "subscription_status": sub.status,
        "new_period_end": sub.current_period_end.isoformat(),
        "payment_reference": payload.payment_reference,
    }


@router.post("/evaluate-dunning", summary="Disparar evaluación manual de morosidad y suspensiones (Admin)")
async def trigger_dunning_evaluation(_admin: User = Depends(get_current_superadmin)):
    """Encola inmediatamente la evaluación de vencimientos y suspensiones en Celery."""
    from app.tasks.billing_tasks import evaluate_all_subscriptions_task

    task = evaluate_all_subscriptions_task.delay()
    return {
        "status": "QUEUED",
        "task_id": str(task.id),
        "message": "Evaluación de morosidad y periodos de gracia encolada exitosamente.",
    }
