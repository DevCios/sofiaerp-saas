# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from app.core.config import get_settings
from app.core.database import SyncSessionLocal
from app.core.security import decrypt_secret, sign_webhook_payload
from app.models import (
    ApiClient,
    DeliveryAttempt,
    DispatchPolicy,
    Document,
    DocumentStatus,
    Issuer,
    WebhookLog,
)
from app.services.sunat_soap import (
    get_summary_status_from_sunat,
    recover_cdr_from_sunat,
    send_bill_to_sunat,
    send_summary_to_sunat,
)
from app.services.xml_signer import save_artifact_file
from app.tasks.celery_app import celery_app

logger = logging.getLogger("sunat_gateway.dispatcher")
settings = get_settings()

# Escalera de backoff exponencial (en minutos): 2m, 10m, 30m, 2h, 4h, luego ventana nocturna
BACKOFF_MINUTES = [2, 10, 30, 120, 240]


def _next_retry_time(attempt_count: int, night_start: int) -> datetime:
    now_utc = datetime.now(timezone.utc)
    if attempt_count <= len(BACKOFF_MINUTES):
        return now_utc + timedelta(minutes=BACKOFF_MINUTES[attempt_count - 1])
    # A partir del 6to intento, programa en la próxima ventana nocturna (hora Lima)
    lima_tz = ZoneInfo(settings.LIMA_TZ)
    now_lima = now_utc.astimezone(lima_tz)
    target_lima = now_lima.replace(hour=night_start, minute=5, second=0, microsecond=0)
    if target_lima <= now_lima:
        target_lima += timedelta(days=1)
    return target_lima.astimezone(timezone.utc)


def _apply_sunat_result(db, doc: Document, issuer: Issuer, resp, action_name: str):
    doc.attempt_count += 1
    doc.last_attempt_at = datetime.now(timezone.utc)
    doc.sunat_code = resp.sunat_code
    doc.sunat_message = resp.sunat_message
    if resp.notes:
        doc.sunat_notes = resp.notes

    attempt = DeliveryAttempt(
        document_id=doc.id,
        attempt_number=doc.attempt_count,
        action=action_name,
        endpoint_url=resp.endpoint_url,
        http_status=resp.http_status,
        sunat_code=resp.sunat_code,
        sunat_message=resp.sunat_message,
        latency_ms=resp.latency_ms,
        outcome=resp.outcome,
    )
    db.add(attempt)

    webhook_event = None

    if getattr(resp, "ticket", None):
        doc.sunat_ticket = resp.ticket

    if resp.outcome in ("ACCEPTED", "ACCEPTED_WITH_OBS"):
        if resp.cdr_zip_bytes:
            cdr_filename = f"R-{doc.xml_filename[:-4]}.zip"
            doc.cdr_path = save_artifact_file(doc.issuer_ruc, doc.issue_date, cdr_filename, resp.cdr_zip_bytes)
        doc.status = (
            DocumentStatus.ACCEPTED if resp.outcome == "ACCEPTED" else DocumentStatus.ACCEPTED_WITH_OBS
        )
        doc.accepted_at = datetime.now(timezone.utc)
        doc.next_retry_at = None
        webhook_event = "document.accepted"
    elif resp.outcome == "TICKET_PENDING":
        doc.status = DocumentStatus.RETRY_SCHEDULED
        doc.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=20)
        db.commit()
        dispatch_document_task.apply_async(args=[doc.id], countdown=15)
        return
    elif resp.outcome == "RECOVER_CDR":
        doc.status = DocumentStatus.RECOVERING_CDR
        doc.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=15)
        db.commit()
        recover_cdr_task.apply_async(args=[doc.id], countdown=5)
        return
    elif resp.outcome == "REJECTED":
        doc.status = DocumentStatus.REJECTED
        doc.next_retry_at = None
        webhook_event = "document.rejected"
    else:
        doc.status = DocumentStatus.RETRY_SCHEDULED
        doc.next_retry_at = _next_retry_time(doc.attempt_count, issuer.night_window_start)

    db.commit()

    if webhook_event and doc.client_id:
        send_webhook_task.delay(doc.id, webhook_event)


@celery_app.task(name="app.tasks.dispatcher.dispatch_document_task")
def dispatch_document_task(document_id: str, force: bool = False):
    """Envía el XML firmado a SUNAT respetando política de envío, reintentos y anti-1033."""
    with SyncSessionLocal() as db:
        doc = db.get(Document, document_id)
        if not doc:
            return {"error": "document_not_found"}
        if doc.status in (DocumentStatus.ACCEPTED, DocumentStatus.ACCEPTED_WITH_OBS, DocumentStatus.REJECTED) and not force:
            return {"skipped": doc.status.value}

        issuer = db.get(Issuer, doc.issuer_id)
        if not issuer or not doc.xml_path or not Path(doc.xml_path).exists():
            doc.status = DocumentStatus.VALIDATION_ERROR
            doc.sunat_message = "Archivo XML firmado no encontrado en almacenamiento."
            db.commit()
            return {"error": "xml_missing"}

        doc.status = DocumentStatus.SENDING
        db.commit()

        xml_bytes = Path(doc.xml_path).read_bytes()
        sol_user = decrypt_secret(issuer.sol_username_enc) or ""
        sol_pass = decrypt_secret(issuer.sol_password_enc) or ""

        if doc.doc_type in ("RA", "RC"):
            if doc.sunat_ticket:
                resp = get_summary_status_from_sunat(
                    ruc=issuer.ruc,
                    ticket=doc.sunat_ticket,
                    sol_username=sol_user,
                    sol_password=sol_pass,
                    is_beta=issuer.is_beta,
                )
                _apply_sunat_result(db, doc, issuer, resp, "getStatus")
            else:
                resp = send_summary_to_sunat(
                    ruc=issuer.ruc,
                    xml_filename=doc.xml_filename,
                    xml_bytes=xml_bytes,
                    sol_username=sol_user,
                    sol_password=sol_pass,
                    is_beta=issuer.is_beta,
                )
                _apply_sunat_result(db, doc, issuer, resp, "sendSummary")
            return {"document_id": doc.id, "status": doc.status.value, "sunat_code": doc.sunat_code, "ticket": doc.sunat_ticket}

        resp = send_bill_to_sunat(
            ruc=issuer.ruc,
            xml_filename=doc.xml_filename,
            xml_bytes=xml_bytes,
            sol_username=sol_user,
            sol_password=sol_pass,
            is_beta=issuer.is_beta,
        )
        _apply_sunat_result(db, doc, issuer, resp, "sendBill")
        return {"document_id": doc.id, "status": doc.status.value, "sunat_code": doc.sunat_code}


@celery_app.task(name="app.tasks.dispatcher.recover_cdr_task")
def recover_cdr_task(document_id: str):
    """Recupera el CDR oficial desde SUNAT vía getStatusCdr ante error 1033 o cortes."""
    with SyncSessionLocal() as db:
        doc = db.get(Document, document_id)
        if not doc:
            return {"error": "document_not_found"}
        issuer = db.get(Issuer, doc.issuer_id)
        if not issuer:
            return {"error": "issuer_not_found"}

        sol_user = decrypt_secret(issuer.sol_username_enc) or ""
        sol_pass = decrypt_secret(issuer.sol_password_enc) or ""

        resp = recover_cdr_from_sunat(
            ruc=issuer.ruc,
            doc_type=doc.doc_type,
            serie=doc.serie,
            correlativo=doc.correlativo,
            sol_username=sol_user,
            sol_password=sol_pass,
            is_beta=issuer.is_beta,
        )
        _apply_sunat_result(db, doc, issuer, resp, "getStatusCdr")
        return {"document_id": doc.id, "status": doc.status.value, "sunat_code": doc.sunat_code}


@celery_app.task(name="app.tasks.dispatcher.send_webhook_task")
def send_webhook_task(document_id: str, event_type: str):
    """Notifica por Webhook firmado con HMAC-SHA256 a la app cliente (SOFIA ERP, POS, etc.)."""
    with SyncSessionLocal() as db:
        doc = db.get(Document, document_id)
        if not doc or not doc.client_id:
            return
        client = db.get(ApiClient, doc.client_id)
        if not client or not client.webhook_url:
            return

        payload = {
            "event": event_type,
            "document_id": doc.id,
            "issuer_ruc": doc.issuer_ruc,
            "doc_type": doc.doc_type,
            "serie": doc.serie,
            "correlativo": doc.correlativo,
            "external_ref": doc.external_ref,
            "status": doc.status.value,
            "sunat_code": doc.sunat_code,
            "sunat_message": doc.sunat_message,
            "sunat_notes": doc.sunat_notes or [],
            "digest_value": doc.digest_value,
            "cdr_url": f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{doc.id}/cdr",
            "xml_url": f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{doc.id}/xml",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "X-Sofia-Event": event_type}

        secret = decrypt_secret(client.webhook_secret_enc)
        if secret:
            headers["X-Sofia-Signature"] = f"sha256={sign_webhook_payload(secret, body_bytes)}"

        http_status = None
        resp_text = None
        delivered = False
        try:
            with httpx.Client(timeout=10) as http_client:
                r = http_client.post(client.webhook_url, content=body_bytes, headers=headers)
                http_status = r.status_code
                resp_text = r.text[:500]
                delivered = 200 <= r.status_code < 300
        except Exception as exc:
            resp_text = str(exc)[:500]

        db.add(WebhookLog(
            document_id=doc.id,
            client_id=client.id,
            event_type=event_type,
            target_url=client.webhook_url,
            http_status=http_status,
            response_body=resp_text,
            delivered=delivered,
        ))
        db.commit()


@celery_app.task(name="app.tasks.dispatcher.sweep_retry_and_night_queue")
def sweep_retry_and_night_queue():
    """Barre comprobantes programados para reintento o ventana nocturna cuyo horario ya llegó."""
    now_utc = datetime.now(timezone.utc)
    enqueued = 0
    with SyncSessionLocal() as db:
        pending = (
            db.query(Document)
            .filter(
                Document.status.in_([DocumentStatus.RETRY_SCHEDULED, DocumentStatus.QUEUED]),
                Document.next_retry_at.is_not(None),
                Document.next_retry_at <= now_utc,
            )
            .limit(50)
            .all()
        )
        for doc in pending:
            doc.next_retry_at = now_utc + timedelta(minutes=5)  # lock suave mientras se procesa
            dispatch_document_task.delay(doc.id)
            enqueued += 1
        db.commit()
    return {"enqueued": enqueued}


@celery_app.task(name="app.tasks.dispatcher.check_deadline_alerts")
def check_deadline_alerts():
    """Marca alerta crítica cuando un documento lleva >48h sin CDR (riesgo de vencer plazo de 3 días)."""
    now_utc = datetime.now(timezone.utc)
    flagged = 0
    with SyncSessionLocal() as db:
        at_risk = (
            db.query(Document)
            .filter(
                Document.status.in_([DocumentStatus.QUEUED, DocumentStatus.RETRY_SCHEDULED, DocumentStatus.RECOVERING_CDR]),
                Document.deadline_at.is_not(None),
                Document.deadline_at <= now_utc + timedelta(hours=24),
                Document.alert_sent_48h.is_(False),
            )
            .all()
        )
        for doc in at_risk:
            doc.alert_sent_48h = True
            if doc.deadline_at <= now_utc:
                doc.status = DocumentStatus.EXPIRED_ALERT
            flagged += 1
            if doc.client_id:
                send_webhook_task.delay(doc.id, "document.deadline_warning")
        db.commit()
    return {"flagged": flagged}
