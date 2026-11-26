# -*- coding: utf-8 -*-
import base64
import hmac
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_api_client_or_admin, get_gateway_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_admin_jwt,
    decrypt_bytes,
    decrypt_secret,
    encrypt_bytes,
    encrypt_secret,
    generate_api_key,
)
from app.models import (
    ApiClient,
    DeliveryAttempt,
    DispatchPolicy,
    Document,
    DocumentStatus,
    Issuer,
)
from app.schemas import (
    AdminLoginRequest,
    ApiClientCreateRequest,
    EmitDocumentRequest,
    EmitDocumentResponse,
    IssuerCreateRequest,
)
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
from app.tasks.dispatcher import dispatch_document_task, recover_cdr_task

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


# ==============================================================================
# 2. Autenticación del Panel Web (gateway.sofiaerp.com)
# ==============================================================================
@router.post("/auth/login", tags=["Auth"])
async def admin_login(body: AdminLoginRequest):
    email_ok = hmac.compare_digest(body.email.strip().lower(), settings.GATEWAY_ADMIN_EMAIL.strip().lower())
    pass_ok = hmac.compare_digest(body.password, settings.GATEWAY_ADMIN_PASSWORD)
    if not (email_ok and pass_ok):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas.")
    token = create_admin_jwt(settings.GATEWAY_ADMIN_EMAIL)
    return {"access_token": token, "token_type": "bearer", "email": settings.GATEWAY_ADMIN_EMAIL}


# ==============================================================================
# 3. KPIs del Dashboard Operativo
# ==============================================================================
@router.get("/stats", tags=["Dashboard"])
async def get_stats(
    _admin: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(select(Document.status, func.count(Document.id)).group_by(Document.status))
    counts = {st.value: cnt for st, cnt in rows.all()}
    total = sum(counts.values())
    accepted = counts.get("ACCEPTED", 0) + counts.get("ACCEPTED_WITH_OBS", 0)
    queued = counts.get("QUEUED", 0) + counts.get("RETRY_SCHEDULED", 0) + counts.get("SENDING", 0) + counts.get("RECOVERING_CDR", 0)
    rejected = counts.get("REJECTED", 0) + counts.get("VALIDATION_ERROR", 0)
    at_risk = counts.get("EXPIRED_ALERT", 0)

    issuers_count = (await db.execute(select(func.count(Issuer.id)))).scalar() or 0
    clients_count = (await db.execute(select(func.count(ApiClient.id)).where(ApiClient.is_active.is_(True)))).scalar() or 0

    return {
        "total_documents": total,
        "accepted": accepted,
        "queued_or_retrying": queued,
        "rejected": rejected,
        "at_risk_deadline": at_risk,
        "acceptance_rate_pct": round((accepted / total) * 100, 1) if total else 100.0,
        "issuers_count": issuers_count,
        "active_clients": clients_count,
        "breakdown": counts,
    }


# ==============================================================================
# 4. Gestión de Empresas Emisoras (RUCs + Certificados .pfx cifrados)
# ==============================================================================
@router.get("/issuers", tags=["Issuers"])
async def list_issuers(_admin: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Issuer).order_by(desc(Issuer.created_at)))
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
            "dispatch_policy": iss.dispatch_policy.value,
            "night_window_start": iss.night_window_start,
            "night_window_end": iss.night_window_end,
            "is_active": iss.is_active,
            "has_certificate": bool(iss.pfx_content_enc),
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
    _admin: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Issuer).where(Issuer.ruc == body.ruc))
    issuer = res.scalar_one_or_none()
    if not issuer:
        issuer = Issuer(ruc=body.ruc, business_name=body.business_name)
        db.add(issuer)

    issuer.business_name = body.business_name.strip()
    issuer.trade_name = (body.trade_name or body.business_name).strip()
    issuer.address = body.address
    issuer.ubigeo = body.ubigeo or "150101"
    issuer.establishment_code = body.establishment_code or "0000"
    issuer.is_beta = body.is_beta
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

    # Certificado .pfx (subido o demo autofirmado en Beta)
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
    elif body.is_beta and (body.generate_demo_cert or not issuer.pfx_content_enc):
        pfx_bytes, demo_pwd, subject, expires = generate_demo_pfx(body.ruc, body.business_name)
        issuer.pfx_content_enc = encrypt_bytes(pfx_bytes)
        issuer.pfx_password_enc = encrypt_secret(demo_pwd)
        issuer.cert_subject = subject[:255]
        issuer.cert_expires_at = expires
        issuer.cert_is_demo = True

    await db.commit()
    await db.refresh(issuer)
    return {"id": issuer.id, "ruc": issuer.ruc, "is_beta": issuer.is_beta, "cert_is_demo": issuer.cert_is_demo}


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
async def list_clients(_admin: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ApiClient).order_by(desc(ApiClient.created_at)))
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
    _admin: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    raw_key, key_prefix, key_hash = generate_api_key("sk_live_")
    client = ApiClient(
        name=body.name.strip(),
        description=body.description,
        key_prefix=key_prefix,
        key_hash=key_hash,
        allowed_rucs=body.allowed_rucs,
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
async def revoke_client(client_id: str, _admin: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    client = await db.get(ApiClient, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada.")
    client.is_active = False
    await db.commit()
    return {"id": client.id, "revoked": True}


# ==============================================================================
# 6. Emisión Instantánea, Consulta, Reintento y Descarga XML/CDR
# ==============================================================================
@router.post("/documents/emit", response_model=EmitDocumentResponse, tags=["Documents"])
async def emit_document(
    body: EmitDocumentRequest,
    auth=Depends(get_api_client_or_admin),
    db: AsyncSession = Depends(get_db),
):
    api_client, _admin = auth
    if api_client and api_client.allowed_rucs and body.issuer_ruc not in api_client.allowed_rucs:
        raise HTTPException(status_code=403, detail=f"Esta API Key no tiene permiso para emitir por el RUC {body.issuer_ruc}.")

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

    # Encolar envío asíncrono a SUNAT sin bloquear al POS/ERP
    if dispatch_now:
        dispatch_document_task.delay(doc.id)

    return EmitDocumentResponse(
        document_id=doc.id,
        status=doc.status.value,
        idempotent_replay=False,
        xml_filename=doc.xml_filename,
        digest_value=doc.digest_value,
        qr_string=doc.qr_string,
        sunat_code=doc.sunat_code,
        sunat_message="Firmado localmente y encolado para envío a SUNAT.",
        xml_url=f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{doc.id}/xml",
        cdr_url=f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{doc.id}/cdr",
        status_url=f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{doc.id}",
    )


@router.get("/documents", tags=["Documents"])
async def list_documents(
    ruc: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    _auth=Depends(get_api_client_or_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document).order_by(desc(Document.created_at)).limit(limit)
    if ruc:
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
async def get_document(doc_id: str, _auth=Depends(get_api_client_or_admin), db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
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
async def retry_document(doc_id: str, _auth=Depends(get_api_client_or_admin), db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
    dispatch_document_task.delay(doc.id, force=True)
    return {"document_id": doc.id, "queued": True, "action": "sendBill"}


@router.post("/documents/{doc_id}/recover-cdr", tags=["Documents"])
async def recover_document_cdr(doc_id: str, _auth=Depends(get_api_client_or_admin), db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
    recover_cdr_task.delay(doc.id)
    return {"document_id": doc.id, "queued": True, "action": "getStatusCdr"}


@router.get("/documents/{doc_id}/xml", tags=["Documents"])
async def download_xml(doc_id: str, _auth=Depends(get_api_client_or_admin), db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc or not doc.xml_path or not Path(doc.xml_path).exists():
        raise HTTPException(status_code=404, detail="XML no disponible.")
    return Response(
        content=Path(doc.xml_path).read_bytes(),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{doc.xml_filename}"'},
    )


@router.get("/documents/{doc_id}/cdr", tags=["Documents"])
async def download_cdr(doc_id: str, _auth=Depends(get_api_client_or_admin), db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc or not doc.cdr_path or not Path(doc.cdr_path).exists():
        raise HTTPException(status_code=404, detail="CDR aún no emitido por SUNAT.")
    cdr_name = Path(doc.cdr_path).name
    return Response(
        content=Path(doc.cdr_path).read_bytes(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{cdr_name}"'},
    )
