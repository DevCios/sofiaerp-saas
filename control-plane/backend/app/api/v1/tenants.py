"""
Endpoints para Administración de Tenants, Dominios, Verificación DNS y Resolución Dinámica.
"""
from typing import List
from datetime import datetime, timedelta, timezone
import re
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.core.security import get_password_hash
from app.models.tenant import Tenant, TenantDomain
from app.models.user import User, UserTenantMembership
from app.schemas.tenant import (
    TenantCreate,
    TenantResponse,
    TenantStatusUpdate,
    TenantDomainCreate,
    TenantDomainResponse,
)
from app.services.domain_service import (
    DomainService,
    TenantNotFoundException,
    TenantSuspendedException,
)
from app.tasks.provisioning import dispatch_tenant_provisioning

router = APIRouter(prefix="/tenants", tags=["Tenants, Dominios & Resolución"])


# ------------------------------------------------------------------------------
# CRUD y Verificación de Disponibilidad de Tenants
# ------------------------------------------------------------------------------
@router.get("/check-availability/{slug}", summary="Comprobar disponibilidad de subdominio en tiempo real")
async def check_slug_availability(slug: str, db: AsyncSession = Depends(get_db_session)):
    clean_slug = slug.strip().lower()
    reserved = [
        "admin", "api", "www", "mail", "smtp", "app", "sofia", "sofiaerp", 
        "control-plane", "portal", "status", "test", "demo", "billing", "auth",
        "root", "support", "soporte", "help", "dev", "staging", "prod"
    ]
    if clean_slug in reserved:
        return {
            "available": False,
            "slug": clean_slug,
            "reason": "RESERVED",
            "message": "Este subdominio es un nombre reservado del sistema."
        }
    
    if len(clean_slug) < 3 or len(clean_slug) > 63 or not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", clean_slug):
        return {
            "available": False,
            "slug": clean_slug,
            "reason": "INVALID_FORMAT",
            "message": "El subdominio debe tener entre 3 y 63 caracteres (solo letras minúsculas, números y guiones simples)."
        }
    
    stmt = select(Tenant).where(Tenant.slug == clean_slug)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        return {
            "available": False,
            "slug": clean_slug,
            "reason": "ALREADY_EXISTS",
            "message": "El subdominio ya está registrado por otra empresa. Por favor elige otro."
        }
        
    return {
        "available": True,
        "slug": clean_slug,
        "message": f"¡Subdominio disponible! https://{clean_slug}.sofiaerp.com"
    }


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED, summary="Registrar y aprovisionar un nuevo Tenant")
async def create_tenant(payload: TenantCreate, db: AsyncSession = Depends(get_db_session)):
    existing_tenant = await db.execute(select(Tenant).where(Tenant.slug == payload.slug))
    if existing_tenant.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El identificador (slug) '{payload.slug}' ya se encuentra en uso.",
        )

    db_name = f"sofia_tenant_{payload.slug.replace('-', '_')}"
    filestore_dir = f"/var/lib/sofia/filestores/{payload.slug}"

    cycle = (payload.billing_cycle or "MONTHLY").upper()
    duration_days = 365 if cycle == "ANNUAL" else 30
    expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)

    new_tenant = Tenant(
        name=payload.name,
        slug=payload.slug,
        database_name=db_name,
        filestore_path=filestore_dir,
        status="PROVISIONING",
        runtime_mode=payload.runtime_mode or "SHARED_PROTECTED",
        plan_code=payload.plan_code or "SOFIA-ERP-PRO",
        billing_cycle=cycle,
        subscription_expires_at=expires_at,
        payment_status="PAID",
        last_payment_date=datetime.now(timezone.utc),
        last_payment_reference=payload.payment_reference,
    )
    db.add(new_tenant)
    await db.flush()

    user_stmt = select(User).where(User.email == payload.admin_email)
    user_res = await db.execute(user_stmt)
    admin_user = user_res.scalar_one_or_none()

    if not admin_user:
        admin_user = User(
            email=payload.admin_email,
            password_hash=get_password_hash(payload.admin_password),
            full_name=f"Admin {payload.name}",
            is_active=True,
        )
        db.add(admin_user)
        await db.flush()

    membership = UserTenantMembership(
        user_id=admin_user.id,
        tenant_id=new_tenant.id,
        role="TENANT_ADMIN",
        is_enabled=True,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(new_tenant)

    # Despachar tarea en Celery
    dispatch_tenant_provisioning(str(new_tenant.id), new_tenant.database_name, new_tenant.filestore_path)

    return new_tenant


@router.get("", response_model=List[TenantResponse], summary="Listar todos los tenants")
async def list_tenants(db: AsyncSession = Depends(get_db_session)):
    stmt = select(Tenant).order_by(Tenant.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{tenant_id}", response_model=TenantResponse, summary="Obtener detalle de un tenant")
async def get_tenant(tenant_id: UUID, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant no encontrado.")
    return tenant


@router.patch("/{tenant_id}/status", response_model=TenantResponse, summary="Actualizar estado del tenant (ACTIVE, SUSPENDED, ARCHIVED)")
@router.put("/{tenant_id}/status", response_model=TenantResponse, summary="Actualizar estado del tenant (ACTIVE, SUSPENDED, ARCHIVED)")
async def update_tenant_status(
    tenant_id: UUID,
    payload: TenantStatusUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant no encontrado.")
    
    tenant.status = payload.status
    now = datetime.now(timezone.utc)

    if payload.extend_days and payload.extend_days > 0:
        base_date = tenant.subscription_expires_at or now
        if base_date < now:
            base_date = now
        tenant.subscription_expires_at = base_date + timedelta(days=payload.extend_days)
        tenant.payment_status = "PAID"
        tenant.last_payment_date = now
        tenant.status = "ACTIVE"
    elif payload.status == "ACTIVE":
        tenant.payment_status = "PAID"
        if not tenant.subscription_expires_at or tenant.subscription_expires_at < now:
            tenant.subscription_expires_at = now + timedelta(days=30)
    elif payload.status == "SUSPENDED":
        tenant.payment_status = "OVERDUE"

    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.post("/evaluate-subscriptions", summary="Verificar vigencia de suscripciones y suspender tenants morosos")
async def evaluate_subscriptions(db: AsyncSession = Depends(get_db_session)):
    """
    Tarea ejecutada periódicamente (cron diario o webhook):
    - Revisa todos los tenants con suscripción activa.
    - Si pasaron más de 3 días de gracia tras su fecha de vencimiento: SUSPENDED (Corte de servicio).
    - Si venció hoy pero está dentro de los 3 días de gracia: DUE_SOON.
    """
    now = datetime.now(timezone.utc)
    stmt = select(Tenant).where(Tenant.status.in_(["ACTIVE", "SUSPENDED"]))
    result = await db.execute(stmt)
    tenants = result.scalars().all()

    suspended_list = []
    due_soon_list = []

    for t in tenants:
        if not t.subscription_expires_at:
            continue
        
        # 3 días de gracia
        grace_deadline = t.subscription_expires_at + timedelta(days=3)
        if now > grace_deadline:
            if t.status != "SUSPENDED":
                t.status = "SUSPENDED"
                suspended_list.append(t.slug)
            t.payment_status = "OVERDUE"
        elif now > t.subscription_expires_at:
            t.payment_status = "DUE_SOON"
            due_soon_list.append(t.slug)
        else:
            t.payment_status = "PAID"

    await db.commit()
    return {
        "checked_total": len(tenants),
        "suspended_count": len(suspended_list),
        "suspended_tenants": suspended_list,
        "due_soon_count": len(due_soon_list),
        "due_soon_tenants": due_soon_list,
    }



# ------------------------------------------------------------------------------
# Gestión de Dominios Personalizados y Validación DNS
# ------------------------------------------------------------------------------
@router.post("/{tenant_id}/domains", response_model=TenantDomainResponse, status_code=status.HTTP_201_CREATED, summary="Registrar un dominio personalizado para el tenant")
async def register_domain(
    tenant_id: UUID,
    payload: TenantDomainCreate,
    db: AsyncSession = Depends(get_db_session),
):
    # Verificar que el tenant exista
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant no encontrado.")

    clean_domain = payload.domain.strip().lower()

    # Comprobar unicidad global del dominio
    existing = (await db.execute(select(TenantDomain).where(TenantDomain.domain == clean_domain))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El dominio ya está registrado por otra empresa.")

    token = DomainService.generate_verification_token()
    domain_record = TenantDomain(
        tenant_id=tenant_id,
        domain=clean_domain,
        is_primary=payload.is_primary,
        verification_token=token,
        status="PENDING_DNS",
    )
    db.add(domain_record)
    await db.commit()
    await db.refresh(domain_record)
    return domain_record


@router.get("/{tenant_id}/domains", response_model=List[TenantDomainResponse], summary="Listar dominios del tenant")
async def list_domains(tenant_id: UUID, db: AsyncSession = Depends(get_db_session)):
    stmt = select(TenantDomain).where(TenantDomain.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{tenant_id}/domains/{domain_id}/verify", summary="Verificar registro DNS TXT del dominio")
async def verify_domain(
    tenant_id: UUID,
    domain_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(TenantDomain).where(
        TenantDomain.id == domain_id,
        TenantDomain.tenant_id == tenant_id,
    )
    domain_record = (await db.execute(stmt)).scalar_one_or_none()
    if not domain_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dominio no encontrado.")

    # Validar DNS TXT
    is_valid = await DomainService.verify_dns_txt_record(
        domain=domain_record.domain,
        expected_token=domain_record.verification_token,
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Verificación DNS fallida. Asegúrese de haber creado un registro TXT en '_sofia-challenge.{domain_record.domain}' con el valor '{domain_record.verification_token}'.",
        )

    domain_record.status = "VERIFIED"
    await db.commit()

    return {
        "status": "VERIFIED",
        "domain": domain_record.domain,
        "message": "Dominio verificado exitosamente. Listo para emisión de SSL.",
    }


# ------------------------------------------------------------------------------
# Endpoint de Resolución Dinámica para Nginx / Edge Proxy
# ------------------------------------------------------------------------------
@router.get("/resolve/{host}", summary="Resolver tenant y dbfilter a partir del Host HTTP")
async def resolve_host(host: str, response: Response, db: AsyncSession = Depends(get_db_session)):
    """
    Invocado por el Edge Proxy (Nginx) para determinar a qué base de datos y upstream
    debe enrutarse la solicitud, protegiendo contra Host Header Injection.
    """
    try:
        resolution = await DomainService.resolve_host(host, db)
        response.headers["X-Odoo-dbfilter"] = resolution["odoo_dbfilter"]
        response.headers["X-Sofia-Tenant-ID"] = resolution["tenant_id"]
        response.headers["X-Sofia-Tenant-Slug"] = resolution["tenant_slug"]
        return resolution
    except TenantNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TenantSuspendedException as e:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(e))
