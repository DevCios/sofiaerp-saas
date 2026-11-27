# -*- coding: utf-8 -*-
import asyncio
import base64
import hmac
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    assert_ruc_access,
    get_actor_workspace_id,
    get_api_client_or_admin,
    get_gateway_admin,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_admin_jwt,
    create_workspace_user_jwt,
    decrypt_bytes,
    decrypt_secret,
    encrypt_bytes,
    encrypt_secret,
    generate_api_key,
    verify_password,
)
from app.models import (
    ApiClient,
    ApiRequestLog,
    DeliveryAttempt,
    DispatchPolicy,
    Document,
    DocumentStatus,
    GatewayUser,
    Issuer,
    WebhookLog,
    Workspace,
)
from app.schemas import (
    AdminLoginRequest,
    ApiClientCreateRequest,
    EmitDocumentRequest,
    EmitDocumentResponse,
    IssuerCreateRequest,
)
from app.services.sunat_soap import extract_cdr_xml_from_zip, send_bill_to_sunat
from app.services.ubl_builder import build_ubl21_xml
from app.services.validator import FiscalValidationError, validate_emit_request
from app.services.xml_signer import (
    build_sunat_qr_string,
    extract_digest_from_signed_xml,
    generate_demo_pfx,
    inspect_pfx,
    save_artifact_file,
    sign_ubl_xml,
)
from app.tasks.dispatcher import _next_retry_time, dispatch_document_task, recover_cdr_task, send_webhook_task

router = APIRouter(prefix="/api/v1")
settings = get_settings()


# ==============================================================================
# 1. Salud del Gateway y Semáforo en Vivo de Servidores SUNAT
# ==============================================================================
@router.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}


@router.get("/health/sunat", tags=["Health"])
async def sunat_health():
    results = {}
    targets = {
        "sunat_beta": f"{settings.SUNAT_BILL_BETA_URL}?wsdl",
        "sunat_prod": f"{settings.SUNAT_BILL_PROD_URL}?wsdl",
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        for name, url in targets.items():
            t0 = time.monotonic()
            try:
                r = await client.get(url)
                results[name] = {
                    "online": r.status_code < 500,
                    "http_status": r.status_code,
                    "latency_ms": int((time.monotonic() - t0) * 1000),
                }
            except Exception as exc:
                results[name] = {
                    "online": False,
                    "http_status": None,
                    "latency_ms": int((time.monotonic() - t0) * 1000),
                    "error": str(exc)[:120],
                }
    return results


async def _get_workspace_rucs(db: AsyncSession, actor: Optional[dict]) -> Optional[list[str]]:
    """Retorna None para Superadmin (global) o la lista exacta de RUCs del Workspace."""
    ws_id = get_actor_workspace_id(actor)
    if not ws_id:
        return None
    rows = await db.execute(select(Issuer.ruc).where(Issuer.workspace_id == ws_id))
    return [r[0] for r in rows.all()]


# ==============================================================================
# 2. Autenticación del Panel Web (Superadmin + Usuarios de Workspace)
# ==============================================================================
@router.post("/auth/login", tags=["Auth"])
async def admin_login(body: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    email_ok = hmac.compare_digest(email, settings.GATEWAY_ADMIN_EMAIL.strip().lower())
    pass_ok = hmac.compare_digest(body.password, settings.GATEWAY_ADMIN_PASSWORD)
    if email_ok and pass_ok:
        token = create_admin_jwt(settings.GATEWAY_ADMIN_EMAIL)
        return {"access_token": token, "token_type": "bearer", "email": settings.GATEWAY_ADMIN_EMAIL, "role": "gateway_admin"}

    user = (
        await db.execute(select(GatewayUser).where(GatewayUser.email == email, GatewayUser.is_active.is_(True)))
    ).scalar_one_or_none()
    if user and verify_password(body.password, user.password_hash):
        ws = await db.get(Workspace, user.workspace_id)
        if not ws or not ws.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace inactivo.")
        token = create_workspace_user_jwt(
            email=user.email,
            user_id=user.id,
            workspace_id=ws.id,
            workspace_name=ws.name,
            full_name=user.full_name,
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "workspace": {"id": ws.id, "name": ws.name, "slug": ws.slug, "plan_name": ws.plan_name, "monthly_quota": ws.monthly_quota},
        }

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas.")


# ==============================================================================
# 3. KPIs del Dashboard Operativo (con aislamiento por Workspace)
# ==============================================================================
@router.get("/stats", tags=["Dashboard"])
async def get_stats(
    ruc: Optional[str] = Query(default=None),
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    ws_id = get_actor_workspace_id(actor)
    ws_rucs = await _get_workspace_rucs(db, actor)

    stmt = select(Document.status, func.count(Document.id)).group_by(Document.status)
    if ws_rucs is not None:
        if ruc and ruc not in ws_rucs:
            return {"total_documents": 0, "accepted": 0, "accepted_with_obs": 0, "queued_or_retrying": 0, "rejected": 0, "at_risk_deadline": 0, "acceptance_rate_pct": 100.0, "issuers_count": len(ws_rucs), "active_clients": 0, "breakdown": {}}
        stmt = stmt.where(Document.issuer_ruc == ruc) if ruc else stmt.where(Document.issuer_ruc.in_(ws_rucs or ["__none__"]))
    elif ruc:
        stmt = stmt.where(Document.issuer_ruc == ruc)

    rows = await db.execute(stmt)
    counts = {st.value: cnt for st, cnt in rows.all()}
    total = sum(counts.values())
    accepted = counts.get("ACCEPTED", 0) + counts.get("ACCEPTED_WITH_OBS", 0)
    with_obs = counts.get("ACCEPTED_WITH_OBS", 0)
    queued = counts.get("QUEUED", 0) + counts.get("RETRY_SCHEDULED", 0) + counts.get("SENDING", 0) + counts.get("RECOVERING_CDR", 0)
    rejected = counts.get("REJECTED", 0) + counts.get("VALIDATION_ERROR", 0)
    at_risk = counts.get("EXPIRED_ALERT", 0)

    iss_q = select(func.count(Issuer.id))
    cli_q = select(func.count(ApiClient.id)).where(ApiClient.is_active.is_(True))
    if ws_id:
        iss_q = iss_q.where(Issuer.workspace_id == ws_id)
        cli_q = cli_q.where(ApiClient.workspace_id == ws_id)
    issuers_count = (await db.execute(iss_q)).scalar() or 0
    clients_count = (await db.execute(cli_q)).scalar() or 0

    return {
        "total_documents": total,
        "accepted": accepted,
        "accepted_with_obs": with_obs,
        "queued_or_retrying": queued,
        "rejected": rejected,
        "at_risk_deadline": at_risk,
        "acceptance_rate_pct": round((accepted / total) * 100, 1) if total else 100.0,
        "issuers_count": issuers_count,
        "active_clients": clients_count,
        "breakdown": counts,
    }


@router.get("/quota", tags=["Dashboard"])
async def get_monthly_quota(
    ruc: Optional[str] = Query(default=None),
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    """Consumo mensual de comprobantes vs cuota configurada por Workspace / empresa (ADR-011/012)."""
    now_lima = datetime.now(timezone.utc).astimezone(ZoneInfo(settings.LIMA_TZ))
    month_start = now_lima.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)

    ws_id = get_actor_workspace_id(actor)
    ws_rucs = await _get_workspace_rucs(db, actor)

    doc_stmt = select(func.count(Document.id)).where(Document.created_at >= month_start)
    if ws_id:
        ws = await db.get(Workspace, ws_id)
        if ruc and ruc in (ws_rucs or []):
            doc_stmt = doc_stmt.where(Document.issuer_ruc == ruc)
        else:
            doc_stmt = doc_stmt.where(Document.issuer_ruc.in_(ws_rucs or ["__none__"]))
        used_this_month = (await db.execute(doc_stmt)).scalar() or 0
        total_quota = int(ws.monthly_quota) if ws else 50
        plan_label = ws.plan_name if ws else "FREE"
    else:
        iss_stmt = select(Issuer).where(Issuer.is_active.is_(True))
        if ruc:
            iss_stmt = iss_stmt.where(Issuer.ruc == ruc)
            doc_stmt = doc_stmt.where(Document.issuer_ruc == ruc)
        issuers = list((await db.execute(iss_stmt)).scalars().all())
        used_this_month = (await db.execute(doc_stmt)).scalar() or 0
        total_quota = sum(max(1, int(i.monthly_quota or 500)) for i in issuers) if issuers else 500
        plan_label = issuers[0].plan_name if len(issuers) == 1 else ("MULTI-EMPRESA" if issuers else "STARTER")

    remaining = max(0, total_quota - used_this_month)
    pct = min(100.0, round((used_this_month / total_quota) * 100, 1)) if total_quota else 0.0

    return {
        "month": now_lima.strftime("%Y-%m"),
        "ruc": ruc,
        "plan_name": plan_label,
        "monthly_quota": total_quota,
        "used_this_month": used_this_month,
        "remaining": remaining,
        "usage_pct": pct,
    }


@router.get("/logs", tags=["Dashboard"])
async def list_api_logs(
    ruc: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    limit: int = Query(default=80, ge=1, le=200),
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    """Visor de Logs de peticiones REST y herramientas MCP (ADR-011/012)."""
    ws_id = get_actor_workspace_id(actor)
    ws_rucs = await _get_workspace_rucs(db, actor)
    stmt = select(ApiRequestLog).order_by(desc(ApiRequestLog.created_at)).limit(limit)
    if ws_id:
        if ruc and ruc in (ws_rucs or []):
            stmt = stmt.where(ApiRequestLog.issuer_ruc == ruc)
        else:
            stmt = stmt.where(
                (ApiRequestLog.workspace_id == ws_id) | (ApiRequestLog.issuer_ruc.in_(ws_rucs or ["__none__"]))
            )
    elif ruc:
        stmt = stmt.where(ApiRequestLog.issuer_ruc == ruc)
    if source and source.upper() in ("REST", "MCP"):
        stmt = stmt.where(ApiRequestLog.source == source.upper())
    res = await db.execute(stmt)
    return [
        {
            "id": lg.id,
            "source": lg.source,
            "method": lg.method,
            "action": lg.action,
            "issuer_ruc": lg.issuer_ruc,
            "client_label": lg.client_label,
            "status_code": lg.status_code,
            "latency_ms": lg.latency_ms,
            "error_summary": lg.error_summary,
            "created_at": lg.created_at.isoformat(),
        }
        for lg in res.scalars().all()
    ]


@router.get("/observations", tags=["Dashboard"])
async def list_observations(
    ruc: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    """Resumen de Observaciones (>=4000) y Rechazos (2xxx/3xxx) estilo operador.pe."""
    ws_rucs = await _get_workspace_rucs(db, actor)
    stmt = (
        select(Document)
        .where(Document.status.in_([DocumentStatus.ACCEPTED_WITH_OBS, DocumentStatus.REJECTED, DocumentStatus.VALIDATION_ERROR]))
        .order_by(desc(Document.updated_at))
        .limit(limit)
    )
    if ws_rucs is not None:
        if ruc and ruc not in ws_rucs:
            return []
        stmt = stmt.where(Document.issuer_ruc == ruc) if ruc else stmt.where(Document.issuer_ruc.in_(ws_rucs or ["__none__"]))
    elif ruc:
        stmt = stmt.where(Document.issuer_ruc == ruc)
    res = await db.execute(stmt)
    return [
        {
            "id": d.id,
            "issuer_ruc": d.issuer_ruc,
            "doc_type": d.doc_type,
            "number": f"{d.serie}-{d.correlativo}",
            "issue_date": d.issue_date,
            "status": d.status.value,
            "sunat_code": d.sunat_code,
            "sunat_message": d.sunat_message,
            "sunat_notes": d.sunat_notes or [],
            "updated_at": d.updated_at.isoformat(),
        }
        for d in res.scalars().all()
    ]


@router.get("/contingencies", tags=["Dashboard"])
async def list_contingencies(
    ruc: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    """Bandeja de Contingencias: comprobantes en cola, reintento, recuperación 1033 o alerta de plazo legal."""
    ws_rucs = await _get_workspace_rucs(db, actor)
    stmt = (
        select(Document)
        .where(
            Document.status.in_([
                DocumentStatus.QUEUED,
                DocumentStatus.SENDING,
                DocumentStatus.RETRY_SCHEDULED,
                DocumentStatus.RECOVERING_CDR,
                DocumentStatus.EXPIRED_ALERT,
            ])
        )
        .order_by(Document.deadline_at.asc().nullslast(), desc(Document.created_at))
        .limit(limit)
    )
    if ws_rucs is not None:
        if ruc and ruc not in ws_rucs:
            return []
        stmt = stmt.where(Document.issuer_ruc == ruc) if ruc else stmt.where(Document.issuer_ruc.in_(ws_rucs or ["__none__"]))
    elif ruc:
        stmt = stmt.where(Document.issuer_ruc == ruc)
    res = await db.execute(stmt)
    now = datetime.now(timezone.utc)
    items = []
    for d in res.scalars().all():
        hours_left = round((d.deadline_at - now).total_seconds() / 3600, 1) if d.deadline_at else None
        items.append({
            "id": d.id,
            "issuer_ruc": d.issuer_ruc,
            "doc_type": d.doc_type,
            "number": f"{d.serie}-{d.correlativo}",
            "issue_date": d.issue_date,
            "status": d.status.value,
            "sunat_code": d.sunat_code,
            "sunat_message": d.sunat_message,
            "attempt_count": d.attempt_count,
            "next_retry_at": d.next_retry_at.isoformat() if d.next_retry_at else None,
            "deadline_at": d.deadline_at.isoformat() if d.deadline_at else None,
            "hours_left": hours_left,
        })
    return items


# ==============================================================================
# 4. Gestión de Empresas Emisoras (RUCs + Certificados .pfx cifrados)
# ==============================================================================
@router.get("/issuers", tags=["Issuers"])
async def list_issuers(actor: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    ws_id = get_actor_workspace_id(actor)
    stmt = select(Issuer).order_by(desc(Issuer.created_at))
    if ws_id:
        stmt = stmt.where(Issuer.workspace_id == ws_id)
    res = await db.execute(stmt)
    items = []
    now = datetime.now(timezone.utc)
    for iss in res.scalars().all():
        days_left = (iss.cert_expires_at - now).days if iss.cert_expires_at else None
        items.append({
            "id": iss.id,
            "ruc": iss.ruc,
            "business_name": iss.business_name,
            "trade_name": iss.trade_name,
            "address": iss.address,
            "ubigeo": iss.ubigeo,
            "is_beta": iss.is_beta,
            "is_nrus": iss.is_nrus,
            "dispatch_policy": iss.dispatch_policy.value,
            "night_window_start": iss.night_window_start,
            "night_window_end": iss.night_window_end,
            "is_active": iss.is_active,
            "has_certificate": bool(iss.pfx_content_enc),
            "signing_mode": "gateway_vault" if iss.pfx_content_enc else "tenant_local",
            "cert_is_demo": iss.cert_is_demo,
            "cert_subject": iss.cert_subject,
            "cert_expires_at": iss.cert_expires_at.isoformat() if iss.cert_expires_at else None,
            "cert_days_left": days_left,
            "has_sol": bool(iss.sol_username_enc),
            "has_gre": bool(iss.gre_client_id_enc),
            "alert_email": iss.alert_email,
        })
    return items


@router.post("/issuers", tags=["Issuers"], status_code=status.HTTP_201_CREATED)
async def upsert_issuer(
    body: IssuerCreateRequest,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    ws_id = get_actor_workspace_id(actor)
    res = await db.execute(select(Issuer).where(Issuer.ruc == body.ruc))
    issuer = res.scalar_one_or_none()
    if issuer and ws_id and issuer.workspace_id != ws_id:
        raise HTTPException(status_code=403, detail=f"El RUC {body.ruc} pertenece a otro Workspace.")
    if not issuer:
        ws = await db.get(Workspace, ws_id) if ws_id else None
        issuer = Issuer(
            ruc=body.ruc,
            business_name=body.business_name,
            workspace_id=ws_id,
            plan_name=ws.plan_name if ws else "STARTER",
            monthly_quota=ws.monthly_quota if ws else 500,
        )
        db.add(issuer)

    issuer.business_name = body.business_name.strip()
    issuer.trade_name = (body.trade_name or body.business_name).strip()
    issuer.address = body.address
    issuer.ubigeo = body.ubigeo or "150101"
    issuer.establishment_code = body.establishment_code or "0000"
    issuer.is_beta = body.is_beta
    issuer.is_nrus = body.is_nrus
    issuer.dispatch_policy = DispatchPolicy(body.dispatch_policy)
    issuer.night_window_start = body.night_window_start
    issuer.night_window_end = body.night_window_end
    issuer.alert_email = body.alert_email

    # Credenciales SOL
    if body.is_beta and not body.sol_username and not issuer.sol_username_enc:
        issuer.sol_username_enc = encrypt_secret("MODDATOS")
        issuer.sol_password_enc = encrypt_secret("MODDATOS")
    else:
        if body.sol_username:
            issuer.sol_username_enc = encrypt_secret(body.sol_username.strip())
        if body.sol_password:
            issuer.sol_password_enc = encrypt_secret(body.sol_password.strip())

    # GRE 2.0
    if body.gre_client_id:
        issuer.gre_client_id_enc = encrypt_secret(body.gre_client_id.strip())
    if body.gre_client_secret:
        issuer.gre_client_secret_enc = encrypt_secret(body.gre_client_secret.strip())

    # Certificado .pfx (subido o demo autofirmado en Beta; omitido si tenant_local_signing=True)
    if body.pfx_base64:
        try:
            pfx_bytes = base64.b64decode(body.pfx_base64)
            subject, expires = inspect_pfx(pfx_bytes, body.pfx_password or "")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Certificado .pfx inválido o contraseña incorrecta: {exc}")
        issuer.pfx_content_enc = encrypt_bytes(pfx_bytes)
        issuer.pfx_password_enc = encrypt_secret(body.pfx_password or "")
        issuer.cert_subject = subject[:255]
        issuer.cert_expires_at = expires
        issuer.cert_is_demo = False
    elif not body.tenant_local_signing and body.is_beta and (body.generate_demo_cert or not issuer.pfx_content_enc):
        pfx_bytes, demo_pwd, subject, expires = generate_demo_pfx(body.ruc, body.business_name)
        issuer.pfx_content_enc = encrypt_bytes(pfx_bytes)
        issuer.pfx_password_enc = encrypt_secret(demo_pwd)
        issuer.cert_subject = subject[:255]
        issuer.cert_expires_at = expires
        issuer.cert_is_demo = True

    await db.commit()
    await db.refresh(issuer)
    return {
        "id": issuer.id,
        "ruc": issuer.ruc,
        "is_beta": issuer.is_beta,
        "is_nrus": issuer.is_nrus,
        "cert_is_demo": issuer.cert_is_demo,
        "signing_mode": "gateway_vault" if issuer.pfx_content_enc else "tenant_local",
    }


@router.get("/summaries", tags=["Dashboard"])
async def list_summaries(
    ruc: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    """Bandeja de Resúmenes Diarios (RC) y Comunicaciones de Baja (RA) con seguimiento de Ticket SUNAT."""
    ws_rucs = await _get_workspace_rucs(db, actor)
    stmt = (
        select(Document)
        .where(Document.doc_type.in_(["RA", "RC"]))
        .order_by(desc(Document.created_at))
        .limit(limit)
    )
    if ws_rucs is not None:
        if ruc and ruc not in ws_rucs:
            return []
        stmt = stmt.where(Document.issuer_ruc == ruc) if ruc else stmt.where(Document.issuer_ruc.in_(ws_rucs or ["__none__"]))
    elif ruc:
        stmt = stmt.where(Document.issuer_ruc == ruc)
    res = await db.execute(stmt)
    return [
        {
            "id": d.id,
            "issuer_ruc": d.issuer_ruc,
            "doc_type": d.doc_type,
            "number": f"{d.doc_type}-{d.serie}-{int(d.correlativo)}",
            "issue_date": d.issue_date,
            "status": d.status.value,
            "sunat_ticket": d.sunat_ticket,
            "sunat_code": d.sunat_code,
            "sunat_message": d.sunat_message,
            "attempt_count": d.attempt_count,
            "has_cdr": bool(d.cdr_path),
            "created_at": d.created_at.isoformat(),
        }
        for d in res.scalars().all()
    ]


@router.delete("/issuers/{ruc}/beta-documents", tags=["Issuers"])
async def purge_issuer_beta_documents(
    ruc: str,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    """Limpia comprobantes de prueba de un RUC en modo Beta antes de pasarlo a Producción Real."""
    ws_id = get_actor_workspace_id(actor)
    res = await db.execute(select(Issuer).where(Issuer.ruc == ruc))
    issuer = res.scalar_one_or_none()
    if not issuer:
        raise HTTPException(status_code=404, detail=f"Empresa RUC {ruc} no encontrada.")
    if ws_id and issuer.workspace_id != ws_id:
        raise HTTPException(status_code=403, detail=f"No tienes permiso sobre el RUC {ruc}.")
    if not issuer.is_beta:
        raise HTTPException(
            status_code=400,
            detail="Por seguridad tributaria, solo se pueden limpiar documentos cuando la empresa está en modo BETA.",
        )

    docs_res = await db.execute(select(Document).where(Document.issuer_ruc == ruc))
    docs = docs_res.scalars().all()
    doc_ids = [d.id for d in docs]
    removed_files = 0
    for d in docs:
        for fpath in (d.xml_path, d.cdr_path):
            if fpath and Path(fpath).exists():
                try:
                    Path(fpath).unlink()
                    removed_files += 1
                except OSError:
                    pass

    if doc_ids:
        await db.execute(delete(WebhookLog).where(WebhookLog.document_id.in_(doc_ids)))
        await db.execute(delete(DeliveryAttempt).where(DeliveryAttempt.document_id.in_(doc_ids)))
        await db.execute(delete(Document).where(Document.id.in_(doc_ids)))
        await db.commit()

    return {"ruc": ruc, "deleted_documents": len(doc_ids), "removed_files": removed_files}


@router.delete("/issuers/{issuer_id}", tags=["Issuers"])
async def toggle_issuer(issuer_id: str, _admin: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    issuer = await db.get(Issuer, issuer_id)
    if not issuer:
        raise HTTPException(status_code=404, detail="Empresa emisora no encontrada.")
    issuer.is_active = not issuer.is_active
    await db.commit()
    return {"id": issuer.id, "is_active": issuer.is_active}


# ==============================================================================
# 5. Gestión de Aplicaciones Cliente y API Keys
# ==============================================================================
@router.get("/clients", tags=["API Clients"])
async def list_clients(actor: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    ws_id = get_actor_workspace_id(actor)
    stmt = select(ApiClient).order_by(desc(ApiClient.created_at))
    if ws_id:
        stmt = stmt.where(ApiClient.workspace_id == ws_id)
    res = await db.execute(stmt)
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "key_prefix": c.key_prefix,
            "is_active": c.is_active,
            "allowed_rucs": c.allowed_rucs,
            "webhook_url": c.webhook_url,
            "has_webhook_secret": bool(c.webhook_secret_enc),
            "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
            "created_at": c.created_at.isoformat(),
        }
        for c in res.scalars().all()
    ]


@router.post("/clients", tags=["API Clients"], status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ApiClientCreateRequest,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    ws_id = get_actor_workspace_id(actor)
    ws_rucs = await _get_workspace_rucs(db, actor)
    allowed_rucs = body.allowed_rucs
    if ws_id:
        if allowed_rucs:
            invalid = [r for r in allowed_rucs if r not in (ws_rucs or [])]
            if invalid:
                raise HTTPException(status_code=403, detail=f"RUCs no pertenecen a tu Workspace: {', '.join(invalid)}")
        else:
            allowed_rucs = ws_rucs or ["__workspace_empty__"]

    raw_key, key_prefix, key_hash = generate_api_key("sk_live_")
    client = ApiClient(
        workspace_id=ws_id,
        name=body.name.strip(),
        description=body.description,
        key_prefix=key_prefix,
        key_hash=key_hash,
        allowed_rucs=allowed_rucs,
        webhook_url=body.webhook_url,
        webhook_secret_enc=encrypt_secret(body.webhook_secret) if body.webhook_secret else None,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return {
        "id": client.id,
        "name": client.name,
        "api_key": raw_key,  # Se muestra una única vez
        "key_prefix": key_prefix,
        "warning": "Guarda esta API Key ahora. No se volverá a mostrar.",
    }


@router.delete("/clients/{client_id}", tags=["API Clients"])
async def revoke_client(client_id: str, actor: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    ws_id = get_actor_workspace_id(actor)
    client = await db.get(ApiClient, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada.")
    if ws_id and client.workspace_id != ws_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para revocar esta API Key.")
    client.is_active = False
    await db.commit()
    return {"id": client.id, "revoked": True}


# ==============================================================================
# 6. Emisión Instantánea, Consulta, Reintento y Descarga XML/CDR
# ==============================================================================
def _read_cdr_xml_b64(cdr_path: Optional[str]) -> Optional[str]:
    if not cdr_path or not Path(cdr_path).exists():
        return None
    try:
        cdr_xml = extract_cdr_xml_from_zip(Path(cdr_path).read_bytes())
        return base64.b64encode(cdr_xml).decode("ascii")
    except Exception:
        return None


@router.post("/documents/emit", response_model=EmitDocumentResponse, tags=["Documents"])
async def emit_document(
    body: EmitDocumentRequest,
    auth=Depends(get_api_client_or_admin),
    db: AsyncSession = Depends(get_db),
):
    api_client, actor = auth
    assert_ruc_access(api_client, body.issuer_ruc)
    ws_rucs = await _get_workspace_rucs(db, actor)
    if ws_rucs is not None and body.issuer_ruc not in ws_rucs:
        raise HTTPException(status_code=403, detail=f"El RUC {body.issuer_ruc} no pertenece a tu Workspace.")

    # 1. Idempotencia estricta por (RUC, tipo, serie, correlativo)
    existing_q = await db.execute(
        select(Document).where(
            Document.issuer_ruc == body.issuer_ruc,
            Document.doc_type == body.doc_type,
            Document.serie == body.serie,
            Document.correlativo == body.correlativo,
        )
    )
    existing = existing_q.scalar_one_or_none()
    if existing:
        return EmitDocumentResponse(
            document_id=existing.id,
            status=existing.status.value,
            idempotent_replay=True,
            xml_filename=existing.xml_filename,
            digest_value=existing.digest_value,
            qr_string=existing.qr_string,
            sunat_code=existing.sunat_code,
            sunat_message=existing.sunat_message,
            sunat_notes=existing.sunat_notes or [],
            cdr_xml_base64=_read_cdr_xml_b64(existing.cdr_path),
            xml_url=f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{existing.id}/xml",
            cdr_url=f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{existing.id}/cdr",
            status_url=f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{existing.id}",
        )

    # 2. Buscar emisor
    iss_q = await db.execute(select(Issuer).where(Issuer.ruc == body.issuer_ruc))
    issuer = iss_q.scalar_one_or_none()
    if not issuer:
        raise HTTPException(status_code=404, detail=f"Empresa emisora RUC {body.issuer_ruc} no registrada en el Gateway.")

    # 3. Pre-validación fiscal anti-rechazos
    try:
        totals = validate_emit_request(body, issuer)
    except FiscalValidationError as exc:
        raise HTTPException(status_code=422, detail={"validation_errors": exc.errors})

    # 4. Construir / Decodificar XML UBL 2.1 + Firma Local Instantánea (.pfx)
    if body.doc_type in ("RA", "RC"):
        xml_filename = f"{body.issuer_ruc}-{body.doc_type}-{body.serie}-{int(body.correlativo)}.xml"
    else:
        xml_filename = f"{body.issuer_ruc}-{body.doc_type}-{body.serie}-{body.correlativo}.xml"
    if body.raw_xml_base64:
        try:
            raw_xml = base64.b64decode(body.raw_xml_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="raw_xml_base64 inválido.")
        if body.already_signed:
            signed_xml = raw_xml
            digest_value = extract_digest_from_signed_xml(signed_xml)
        else:
            pfx_bytes = decrypt_bytes(issuer.pfx_content_enc)
            pfx_pwd = decrypt_secret(issuer.pfx_password_enc) or ""
            signed_xml, digest_value = sign_ubl_xml(raw_xml, pfx_bytes, pfx_pwd)
    else:
        unsigned_xml = build_ubl21_xml(body, issuer, totals)
        pfx_bytes = decrypt_bytes(issuer.pfx_content_enc)
        pfx_pwd = decrypt_secret(issuer.pfx_password_enc) or ""
        signed_xml, digest_value = sign_ubl_xml(unsigned_xml, pfx_bytes, pfx_pwd)

    xml_path = save_artifact_file(body.issuer_ruc, body.issue_date, xml_filename, signed_xml)

    cust_doc_type = body.customer.doc_type if body.customer else "0"
    cust_doc_num = body.customer.doc_number if body.customer else "-"
    qr_string = build_sunat_qr_string(
        issuer_ruc=body.issuer_ruc,
        doc_type=body.doc_type,
        serie=body.serie,
        correlativo=body.correlativo,
        igv_amount=float(totals["igv_amount"]),
        total_amount=float(totals["total_amount"]),
        issue_date=body.issue_date,
        customer_doc_type=cust_doc_type,
        customer_doc_number=cust_doc_num,
        digest_value=digest_value,
    )

    # Plazo legal SUNAT: 3 días calendario para Facturas/Notas, 7 días para Boletas
    deadline_days = 7 if body.doc_type == "03" else 3
    deadline_at = datetime.now(timezone.utc) + timedelta(days=deadline_days)

    # Política de despacho: inmediato vs ventana nocturna
    next_retry_at = None
    dispatch_now = True
    if issuer.dispatch_policy == DispatchPolicy.SCHEDULED_NIGHT:
        lima_tz = ZoneInfo(settings.LIMA_TZ)
        now_lima = datetime.now(timezone.utc).astimezone(lima_tz)
        if not (issuer.night_window_start <= now_lima.hour < issuer.night_window_end):
            target = now_lima.replace(hour=issuer.night_window_start, minute=5, second=0, microsecond=0)
            if target <= now_lima:
                target += timedelta(days=1)
            next_retry_at = target.astimezone(timezone.utc)
            dispatch_now = False

    doc = Document(
        issuer_id=issuer.id,
        client_id=api_client.id if api_client else None,
        issuer_ruc=body.issuer_ruc,
        doc_type=body.doc_type,
        serie=body.serie,
        correlativo=body.correlativo,
        issue_date=body.issue_date,
        currency=body.currency,
        total_amount=totals["total_amount"],
        igv_amount=totals["igv_amount"],
        customer_doc_type=cust_doc_type,
        customer_doc_number=cust_doc_num,
        customer_name=body.customer.name if body.customer else None,
        external_ref=body.external_ref,
        status=DocumentStatus.QUEUED,
        xml_filename=xml_filename,
        xml_path=xml_path,
        digest_value=digest_value,
        qr_string=qr_string,
        next_retry_at=next_retry_at,
        deadline_at=deadline_at,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Encolar envío asíncrono a SUNAT o intento rápido síncrono (Modo Híbrido SOFIA ERP)
    cdr_xml_b64 = None
    response_msg = "Firmado y encolado en Sofia Gateway para envío a SUNAT."
    if dispatch_now and body.try_sync and body.doc_type not in ("RA", "RC"):
        sol_user = decrypt_secret(issuer.sol_username_enc) or ""
        sol_pass = decrypt_secret(issuer.sol_password_enc) or ""
        resp = await asyncio.to_thread(
            send_bill_to_sunat,
            issuer.ruc,
            doc.xml_filename,
            signed_xml,
            sol_user,
            sol_pass,
            issuer.is_beta,
            settings.SYNC_DISPATCH_TIMEOUT_SECONDS,
        )
        doc.attempt_count = 1
        doc.last_attempt_at = datetime.now(timezone.utc)
        doc.sunat_code = resp.sunat_code
        doc.sunat_message = resp.sunat_message
        if resp.notes:
            doc.sunat_notes = resp.notes
        db.add(DeliveryAttempt(
            document_id=doc.id,
            attempt_number=1,
            action="sendBill",
            endpoint_url=resp.endpoint_url,
            http_status=resp.http_status,
            sunat_code=resp.sunat_code,
            sunat_message=resp.sunat_message,
            latency_ms=resp.latency_ms,
            outcome=resp.outcome,
        ))
        if resp.outcome in ("ACCEPTED", "ACCEPTED_WITH_OBS"):
            if resp.cdr_zip_bytes:
                cdr_filename = f"R-{doc.xml_filename[:-4]}.zip"
                doc.cdr_path = save_artifact_file(doc.issuer_ruc, doc.issue_date, cdr_filename, resp.cdr_zip_bytes)
                cdr_xml_b64 = _read_cdr_xml_b64(doc.cdr_path)
            doc.status = DocumentStatus.ACCEPTED if resp.outcome == "ACCEPTED" else DocumentStatus.ACCEPTED_WITH_OBS
            doc.accepted_at = datetime.now(timezone.utc)
            doc.next_retry_at = None
            response_msg = resp.sunat_message or "Aceptado por SUNAT."
            await db.commit()
            if doc.client_id:
                send_webhook_task.delay(doc.id, "document.accepted")
        elif resp.outcome == "RECOVER_CDR":
            doc.status = DocumentStatus.RECOVERING_CDR
            doc.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=15)
            response_msg = "Comprobante ya registrado en SUNAT (1033). Recuperando CDR automáticamente."
            await db.commit()
            recover_cdr_task.apply_async(args=[doc.id], countdown=5)
        elif resp.outcome == "REJECTED":
            doc.status = DocumentStatus.REJECTED
            doc.next_retry_at = None
            response_msg = resp.sunat_message or "Comprobante rechazado por SUNAT."
            await db.commit()
            if doc.client_id:
                send_webhook_task.delay(doc.id, "document.rejected")
        else:
            doc.status = DocumentStatus.RETRY_SCHEDULED
            doc.next_retry_at = _next_retry_time(doc.attempt_count, issuer.night_window_start)
            response_msg = "SUNAT saturado o sin respuesta. Encolado en Sofia Gateway para reintento automático."
            await db.commit()
    elif dispatch_now:
        dispatch_document_task.delay(doc.id)

    return EmitDocumentResponse(
        document_id=doc.id,
        status=doc.status.value,
        idempotent_replay=False,
        xml_filename=doc.xml_filename,
        digest_value=doc.digest_value,
        qr_string=doc.qr_string,
        sunat_code=doc.sunat_code,
        sunat_message=response_msg,
        sunat_notes=doc.sunat_notes or [],
        cdr_xml_base64=cdr_xml_b64,
        xml_url=f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{doc.id}/xml",
        cdr_url=f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{doc.id}/cdr",
        status_url=f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{doc.id}",
    )


@router.get("/documents/lookup", tags=["Documents"])
async def lookup_document_by_number(
    issuer_ruc: str = Query(..., pattern=r"^\d{11}$"),
    doc_type: str = Query(..., min_length=2, max_length=2),
    serie: str = Query(..., min_length=4, max_length=4),
    correlativo: str = Query(..., min_length=1, max_length=12),
    auth=Depends(get_api_client_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Consulta estado y CDR XML por (RUC, tipo, serie, correlativo) para sincronización desde SOFIA ERP."""
    api_client, _admin = auth
    assert_ruc_access(api_client, issuer_ruc)
    clean_corr = (correlativo.strip().lstrip("0") or "1").zfill(8)
    res = await db.execute(
        select(Document).where(
            Document.issuer_ruc == issuer_ruc,
            Document.doc_type == doc_type,
            Document.serie == serie.strip().upper(),
            Document.correlativo == clean_corr,
        )
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado en Sofia Gateway.")
    return {
        "document_id": doc.id,
        "status": doc.status.value,
        "sunat_code": doc.sunat_code,
        "sunat_message": doc.sunat_message,
        "sunat_notes": doc.sunat_notes or [],
        "attempt_count": doc.attempt_count,
        "has_cdr": bool(doc.cdr_path),
        "cdr_xml_base64": _read_cdr_xml_b64(doc.cdr_path),
        "next_retry_at": doc.next_retry_at.isoformat() if doc.next_retry_at else None,
    }


@router.get("/documents", tags=["Documents"])
async def list_documents(
    ruc: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    auth=Depends(get_api_client_or_admin),
    db: AsyncSession = Depends(get_db),
):
    api_client, actor = auth
    ws_rucs = await _get_workspace_rucs(db, actor)
    stmt = select(Document).order_by(desc(Document.created_at)).limit(limit)
    if api_client and api_client.allowed_rucs:
        if ruc:
            assert_ruc_access(api_client, ruc)
            stmt = stmt.where(Document.issuer_ruc == ruc)
        else:
            stmt = stmt.where(Document.issuer_ruc.in_(api_client.allowed_rucs))
    elif ws_rucs is not None:
        if ruc:
            if ruc not in ws_rucs:
                return []
            stmt = stmt.where(Document.issuer_ruc == ruc)
        else:
            stmt = stmt.where(Document.issuer_ruc.in_(ws_rucs or ["__none__"]))
    elif ruc:
        stmt = stmt.where(Document.issuer_ruc == ruc)
    if status_filter:
        stmt = stmt.where(Document.status == DocumentStatus(status_filter))
    res = await db.execute(stmt)
    return [
        {
            "id": d.id,
            "issuer_ruc": d.issuer_ruc,
            "doc_type": d.doc_type,
            "number": f"{d.serie}-{d.correlativo}",
            "issue_date": d.issue_date,
            "currency": d.currency,
            "total_amount": float(d.total_amount),
            "customer_name": d.customer_name,
            "status": d.status.value,
            "sunat_code": d.sunat_code,
            "sunat_message": d.sunat_message,
            "attempt_count": d.attempt_count,
            "has_cdr": bool(d.cdr_path),
            "next_retry_at": d.next_retry_at.isoformat() if d.next_retry_at else None,
            "deadline_at": d.deadline_at.isoformat() if d.deadline_at else None,
            "created_at": d.created_at.isoformat(),
        }
        for d in res.scalars().all()
    ]


@router.get("/documents/{doc_id}", tags=["Documents"])
async def get_document(doc_id: str, auth=Depends(get_api_client_or_admin), db: AsyncSession = Depends(get_db)):
    api_client, _admin = auth
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
    assert_ruc_access(api_client, doc.issuer_ruc)
    att_res = await db.execute(
        select(DeliveryAttempt).where(DeliveryAttempt.document_id == doc.id).order_by(desc(DeliveryAttempt.attempt_number))
    )
    return {
        "id": doc.id,
        "issuer_ruc": doc.issuer_ruc,
        "doc_type": doc.doc_type,
        "serie": doc.serie,
        "correlativo": doc.correlativo,
        "issue_date": doc.issue_date,
        "currency": doc.currency,
        "total_amount": float(doc.total_amount),
        "igv_amount": float(doc.igv_amount),
        "status": doc.status.value,
        "digest_value": doc.digest_value,
        "qr_string": doc.qr_string,
        "sunat_code": doc.sunat_code,
        "sunat_message": doc.sunat_message,
        "sunat_notes": doc.sunat_notes or [],
        "attempt_count": doc.attempt_count,
        "has_cdr": bool(doc.cdr_path),
        "xml_url": f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{doc.id}/xml",
        "cdr_url": f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{doc.id}/cdr",
        "attempts": [
            {
                "attempt_number": a.attempt_number,
                "action": a.action,
                "http_status": a.http_status,
                "sunat_code": a.sunat_code,
                "sunat_message": a.sunat_message,
                "latency_ms": a.latency_ms,
                "outcome": a.outcome,
                "created_at": a.created_at.isoformat(),
            }
            for a in att_res.scalars().all()
        ],
    }


@router.post("/documents/{doc_id}/retry", tags=["Documents"])
async def retry_document(doc_id: str, auth=Depends(get_api_client_or_admin), db: AsyncSession = Depends(get_db)):
    api_client, _admin = auth
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
    assert_ruc_access(api_client, doc.issuer_ruc)
    dispatch_document_task.delay(doc.id, force=True)
    return {"document_id": doc.id, "queued": True, "action": "sendBill"}


@router.post("/documents/{doc_id}/recover-cdr", tags=["Documents"])
async def recover_document_cdr(doc_id: str, auth=Depends(get_api_client_or_admin), db: AsyncSession = Depends(get_db)):
    api_client, _admin = auth
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
    assert_ruc_access(api_client, doc.issuer_ruc)
    recover_cdr_task.delay(doc.id)
    return {"document_id": doc.id, "queued": True, "action": "getStatusCdr"}


@router.get("/documents/{doc_id}/xml", tags=["Documents"])
async def download_xml(doc_id: str, auth=Depends(get_api_client_or_admin), db: AsyncSession = Depends(get_db)):
    api_client, _admin = auth
    doc = await db.get(Document, doc_id)
    if not doc or not doc.xml_path or not Path(doc.xml_path).exists():
        raise HTTPException(status_code=404, detail="XML no disponible.")
    assert_ruc_access(api_client, doc.issuer_ruc)
    return Response(
        content=Path(doc.xml_path).read_bytes(),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{doc.xml_filename}"'},
    )


@router.get("/documents/{doc_id}/cdr", tags=["Documents"])
async def download_cdr(doc_id: str, auth=Depends(get_api_client_or_admin), db: AsyncSession = Depends(get_db)):
    api_client, _admin = auth
    doc = await db.get(Document, doc_id)
    if not doc or not doc.cdr_path or not Path(doc.cdr_path).exists():
        raise HTTPException(status_code=404, detail="CDR aún no emitido por SUNAT.")
    assert_ruc_access(api_client, doc.issuer_ruc)
    cdr_name = Path(doc.cdr_path).name
    return Response(
        content=Path(doc.cdr_path).read_bytes(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{cdr_name}"'},
    )
