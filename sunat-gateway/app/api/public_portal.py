# -*- coding: utf-8 -*-
"""
Portal Público de Consulta y Descarga de Comprobantes Electrónicos (Sofia Gateway).
Sigue estrictamente el Sistema de Diseño Oficial SOFIA / Odoo 20 (docs/design-system-odoo20.md).
"""
import time
from collections import defaultdict, deque
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_public_download_token, verify_public_download_token
from app.models import Document, Issuer

router = APIRouter()

# Rate limit ligero en memoria: máximo 20 consultas por minuto por IP
_RATE_LIMIT_MAX = 20
_RATE_LIMIT_WINDOW_SEC = 60.0
_IP_HITS: dict[str, deque[float]] = defaultdict(deque)


def _check_rate_limit(request: Request) -> None:
    ip = (
        request.headers.get("x-real-ip")
        or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    now = time.monotonic()
    bucket = _IP_HITS[ip]
    while bucket and (now - bucket[0]) > _RATE_LIMIT_WINDOW_SEC:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas consultas en poco tiempo. Espera un minuto e intenta nuevamente.",
        )
    bucket.append(now)


class PublicConsultRequest(BaseModel):
    issuer_ruc: str = Field(..., pattern=r"^\d{11}$")
    doc_type: Literal["01", "03", "07", "08"]
    serie: str = Field(..., min_length=4, max_length=4)
    correlativo: str = Field(..., min_length=1, max_length=8)
    issue_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    total_amount: Decimal = Field(..., gt=0)

    @field_validator("serie")
    @classmethod
    def norm_serie(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("correlativo")
    @classmethod
    def norm_correlativo(cls, v: str) -> str:
        clean = v.strip().lstrip("0") or "1"
        if not clean.isdigit():
            raise ValueError("El número correlativo debe ser numérico.")
        return clean.zfill(8)


@router.post("/api/v1/public/consult", tags=["Public Portal"])
async def public_consult_document(
    body: PublicConsultRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Consulta pública anti-enumeración: exige coincidencia exacta de los 6 datos fiscales
    (RUC emisor, tipo, serie, correlativo, fecha de emisión y monto total).
    """
    _check_rate_limit(request)

    res = await db.execute(
        select(Document, Issuer)
        .join(Issuer, Issuer.id == Document.issuer_id)
        .where(
            Document.issuer_ruc == body.issuer_ruc,
            Document.doc_type == body.doc_type,
            Document.serie == body.serie,
            Document.correlativo == body.correlativo,
            Document.issue_date == body.issue_date,
        )
    )
    row = res.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró un comprobante que coincida exactamente con los datos ingresados.",
        )

    doc, issuer = row
    try:
        stored_total = Decimal(str(doc.total_amount)).quantize(Decimal("0.01"))
        req_total = body.total_amount.quantize(Decimal("0.01"))
    except InvalidOperation:
        raise HTTPException(status_code=400, detail="Monto total inválido.")

    if stored_total != req_total:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró un comprobante que coincida exactamente con los datos ingresados.",
        )

    dl_token = create_public_download_token(doc.id, ttl_minutes=10)
    has_xml = bool(doc.xml_path and Path(doc.xml_path).exists())
    has_cdr = bool(doc.cdr_path and Path(doc.cdr_path).exists())

    doc_type_labels = {
        "01": "Factura Electrónica",
        "03": "Boleta de Venta Electrónica",
        "07": "Nota de Crédito Electrónica",
        "08": "Nota de Débito Electrónica",
    }

    return {
        "document_id": doc.id,
        "issuer_ruc": issuer.ruc,
        "issuer_name": issuer.business_name,
        "issuer_address": issuer.address,
        "is_beta": issuer.is_beta,
        "doc_type": doc.doc_type,
        "doc_type_label": doc_type_labels.get(doc.doc_type, doc.doc_type),
        "number": f"{doc.serie}-{doc.correlativo}",
        "issue_date": doc.issue_date,
        "currency": doc.currency,
        "igv_amount": float(doc.igv_amount),
        "total_amount": float(doc.total_amount),
        "customer_doc_type": doc.customer_doc_type,
        "customer_doc_number": doc.customer_doc_number,
        "customer_name": doc.customer_name,
        "status": doc.status.value,
        "sunat_code": doc.sunat_code,
        "sunat_message": doc.sunat_message,
        "digest_value": doc.digest_value,
        "accepted_at": doc.accepted_at.isoformat() if doc.accepted_at else None,
        "has_xml": has_xml,
        "has_cdr": has_cdr,
        "xml_download_url": f"/api/v1/public/download/{doc.id}/xml?token={dl_token}" if has_xml else None,
        "cdr_download_url": f"/api/v1/public/download/{doc.id}/cdr?token={dl_token}" if has_cdr else None,
    }


@router.get("/api/v1/public/download/{doc_id}/{kind}", tags=["Public Portal"])
async def public_download_artifact(
    doc_id: str,
    kind: Literal["xml", "cdr"],
    token: str = Query(..., min_length=20),
    db: AsyncSession = Depends(get_db),
):
    """Descarga pública segura de XML o CDR mediante token JWT temporal de 10 minutos."""
    if not verify_public_download_token(token, doc_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El enlace de descarga expiró o es inválido. Realiza la consulta nuevamente.",
        )

    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")

    if kind == "xml":
        if not doc.xml_path or not Path(doc.xml_path).exists():
            raise HTTPException(status_code=404, detail="Archivo XML no disponible.")
        return Response(
            content=Path(doc.xml_path).read_bytes(),
            media_type="application/xml",
            headers={"Content-Disposition": f'attachment; filename="{doc.xml_filename}"'},
        )

    if not doc.cdr_path or not Path(doc.cdr_path).exists():
        raise HTTPException(status_code=404, detail="Constancia CDR aún no disponible.")
    cdr_name = Path(doc.cdr_path).name
    return Response(
        content=Path(doc.cdr_path).read_bytes(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{cdr_name}"'},
    )


PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Consulta de Comprobantes Electrónicos — Sofia Gateway</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
  <style>
    :root {
      --o20-navbar: #66598F;
      --o20-primary: #714B67;
      --o20-primary-h: #5C3B53;
      --o20-primary-soft: #EAE6F8;
      --o20-teal: #017E84;
      --o20-teal-h: #01666B;
      --o20-teal-soft: #D9F2EE;
      --bg: #F6F7F9;
      --card: #FFFFFF;
      --border: #E2E5EC;
      --text: #1F2937;
      --muted: #6B7280;
      --ok: #0F766E;
      --warn: #B45309;
      --err: #B91C1C;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }
    .hidden { display: none !important; }

    /* Navbar Centrado Estilo Odoo 20 / SOFIA Platform */
    header { background: var(--o20-navbar); color: #FFFFFF; box-shadow: 0 1px 3px rgba(17,24,39,.12); }
    .nav-inner { max-width: 1120px; margin: 0 auto; padding: 0 24px; min-height: 56px; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
    .brand { font-weight: 700; font-size: 16px; display: flex; align-items: center; gap: 10px; color: #FFFFFF; text-decoration: none; }
    .brand-mark { width: 32px; height: 32px; border-radius: 8px; background: rgba(255,255,255,.20); display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 15px; }
    .brand-sub { display: block; font-size: 11px; font-weight: 400; color: rgba(255,255,255,.80); margin-top: -1px; }
    .nav-btn { background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.25); color: #FFFFFF; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; text-decoration: none; transition: background .15s; }
    .nav-btn:hover { background: rgba(255,255,255,.25); }

    main { flex: 1; max-width: 880px; width: 100%; margin: 32px auto; padding: 0 20px; }
    .banner { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 22px 26px; margin-bottom: 20px; box-shadow: 0 1px 2px rgba(16,24,40,.03); }
    .banner h1 { margin: 0; font-size: 21px; font-weight: 700; letter-spacing: -0.02em; }
    .banner p { margin: 6px 0 0 0; font-size: 13px; color: var(--muted); line-height: 1.5; }

    .card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 24px 26px; margin-bottom: 20px; box-shadow: 0 1px 2px rgba(16,24,40,.03); }
    .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
    label { display: block; font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 5px; }
    input, select { background: #FFFFFF; border: 1px solid #D1D5DB; color: var(--text); padding: 9px 11px; border-radius: 8px; width: 100%; font-size: 13.5px; transition: border-color .15s, box-shadow .15s; }
    input:focus, select:focus { outline: none; border-color: var(--o20-primary); box-shadow: 0 0 0 3px rgba(113,75,103,.12); }

    .actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; flex-wrap: wrap; }
    .btn { background: var(--o20-primary); color: #FFFFFF; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13.5px; text-decoration: none; display: inline-flex; align-items: center; gap: 7px; transition: background .15s; }
    .btn:hover { background: var(--o20-primary-h); }
    .btn-teal { background: var(--o20-teal); }
    .btn-teal:hover { background: var(--o20-teal-h); }
    .btn-sec { background: #FFFFFF; color: #374151; border: 1px solid #D1D5DB; }
    .btn-sec:hover { background: #F3F4F6; }

    .alert-err { margin-top: 14px; padding: 12px 14px; border-radius: 8px; background: #FDF0F0; border: 1px solid #F6CECE; color: var(--err); font-size: 13px; }
    .badge { padding: 4px 11px; border-radius: 999px; font-size: 11.5px; font-weight: 700; display: inline-flex; align-items: center; gap: 5px; }
    .b-ok { background: var(--o20-teal-soft); color: var(--ok); }
    .b-warn { background: #FDE8D7; color: var(--warn); }
    .b-err { background: #FDE2E2; color: var(--err); }
    .b-info { background: var(--o20-primary-soft); color: #5B4B8A; }

    .res-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; padding-bottom: 16px; border-bottom: 1px solid var(--border); margin-bottom: 18px; }
    .res-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; margin-bottom: 18px; }
    .res-item { background: #F9FAFB; border: 1px solid #EEF0F4; border-radius: 10px; padding: 12px 14px; }
    .res-item .k { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
    .res-item .v { font-size: 14px; font-weight: 600; color: var(--text); margin-top: 4px; word-break: break-word; }
    .hash-box { background: #F4F1FB; border: 1px solid #DED7F2; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #492E42; word-break: break-all; margin-bottom: 18px; }
    .dl-bar { display: flex; gap: 10px; flex-wrap: wrap; }

    footer { text-align: center; padding: 18px 20px; font-size: 12px; color: var(--muted); border-top: 1px solid var(--border); background: var(--card); }

    @media print {
      header, .no-print, footer { display: none !important; }
      body { background: #FFFFFF; }
      main { margin: 0; max-width: 100%; }
      .card { border: none; box-shadow: none; padding: 0; }
    }
  </style>
</head>
<body>

<header>
  <div class="nav-inner">
    <a href="/consulta" class="brand">
      <span class="brand-mark">S</span>
      <div>
        <span>Sofia Gateway</span>
        <span class="brand-sub">Consulta Pública de Comprobantes Electrónicos • SUNAT Perú</span>
      </div>
    </a>
    <div style="display:flex;gap:8px;align-items:center">
      <a href="https://sofiaerp.com" target="_blank" class="nav-btn">SOFIA ERP</a>
      <a href="/" class="nav-btn">Acceso Admin</a>
    </div>
  </div>
</header>

<main>
  <div class="banner no-print">
    <h1>Consulta y Descarga tu Comprobante Electrónico</h1>
    <p>Ingresa los datos exactos de tu Factura, Boleta o Nota emitida a través de <strong>SOFIA ERP / Sofia Gateway</strong> para verificar su estado ante SUNAT y descargar el archivo XML y la Constancia de Recepción (CDR).</p>
  </div>

  <div class="card no-print">
    <form id="consultForm" onsubmit="doConsult(event)">
      <div class="form-grid">
        <div>
          <label for="fRuc">RUC del Emisor (11 dígitos)</label>
          <input id="fRuc" required pattern="\d{11}" maxlength="11" placeholder="20600994345" />
        </div>
        <div>
          <label for="fType">Tipo de Comprobante</label>
          <select id="fType" required>
            <option value="01">01 — Factura Electrónica</option>
            <option value="03">03 — Boleta de Venta Electrónica</option>
            <option value="07">07 — Nota de Crédito Electrónica</option>
            <option value="08">08 — Nota de Débito Electrónica</option>
          </select>
        </div>
        <div>
          <label for="fSerie">Serie (4 caracteres)</label>
          <input id="fSerie" required minlength="4" maxlength="4" placeholder="FE01" style="text-transform:uppercase" />
        </div>
        <div>
          <label for="fCorr">Número Correlativo</label>
          <input id="fCorr" required pattern="\d{1,8}" maxlength="8" placeholder="00000001 o 1" />
        </div>
        <div>
          <label for="fDate">Fecha de Emisión</label>
          <input id="fDate" type="date" required />
        </div>
        <div>
          <label for="fTotal">Importe Total Exacto</label>
          <input id="fTotal" type="number" step="0.01" min="0.01" required placeholder="118.00" />
        </div>
      </div>

      <div id="errBox" class="alert-err hidden"></div>

      <div class="actions">
        <button type="button" class="btn btn-sec" onclick="resetForm()">Limpiar</button>
        <button type="submit" id="btnSubmit" class="btn">Consultar Comprobante</button>
      </div>
    </form>
  </div>

  <div id="resultCard" class="card hidden">
    <div class="res-header">
      <div>
        <div id="rDocTitle" style="font-size:18px;font-weight:700;color:var(--o20-primary)"></div>
        <div id="rIssuer" style="font-size:13px;color:var(--muted);margin-top:3px"></div>
      </div>
      <div id="rBadges" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"></div>
    </div>

    <div class="res-grid">
      <div class="res-item"><div class="k">Fecha de Emisión</div><div class="v" id="rDate">-</div></div>
      <div class="res-item"><div class="k">Importe Total</div><div class="v" id="rTotal">-</div></div>
      <div class="res-item"><div class="k">IGV</div><div class="v" id="rIgv">-</div></div>
      <div class="res-item"><div class="k">Cliente / Receptor</div><div class="v" id="rCustomer">-</div></div>
      <div class="res-item"><div class="k">Respuesta SUNAT</div><div class="v" id="rSunatMsg">-</div></div>
      <div class="res-item"><div class="k">Código SUNAT</div><div class="v" id="rSunatCode">-</div></div>
    </div>

    <div id="rHashBox" class="hash-box hidden">
      <strong>Resumen Digital (DigestValue / Hash XMLDSig):</strong> <span id="rDigest"></span>
    </div>

    <div class="dl-bar no-print">
      <a id="btnXml" class="btn hidden" href="#" download>Descargar XML Firmado</a>
      <a id="btnCdr" class="btn btn-teal hidden" href="#" download>Descargar CDR SUNAT (.zip)</a>
      <button type="button" class="btn btn-sec" onclick="window.print()">Imprimir Constancia</button>
    </div>
  </div>
</main>

<footer>
  Portal de Verificación de Comprobantes Electrónicos · <strong>Sofia Gateway</strong> (`gateway.sofiaerp.com`) · Ecosistema SOFIA ERP
</footer>

<script>
function statusBadgeHtml(st) {
  if (st === 'ACCEPTED') return '<span class="badge b-ok">ACEPTADO POR SUNAT</span>';
  if (st === 'ACCEPTED_WITH_OBS') return '<span class="badge b-warn">ACEPTADO CON OBSERVACIONES</span>';
  if (st === 'REJECTED' || st === 'VALIDATION_ERROR') return '<span class="badge b-err">RECHAZADO</span>';
  return '<span class="badge b-warn">EN PROCESO / ENVIANDO A SUNAT</span>';
}

function resetForm() {
  document.getElementById('consultForm').reset();
  document.getElementById('errBox').classList.add('hidden');
  document.getElementById('resultCard').classList.add('hidden');
}

async function doConsult(e) {
  e.preventDefault();
  const errBox = document.getElementById('errBox');
  const resCard = document.getElementById('resultCard');
  const btn = document.getElementById('btnSubmit');
  errBox.classList.add('hidden');
  resCard.classList.add('hidden');
  btn.disabled = true;
  btn.textContent = 'Consultando...';

  try {
    const payload = {
      issuer_ruc: document.getElementById('fRuc').value.trim(),
      doc_type: document.getElementById('fType').value,
      serie: document.getElementById('fSerie').value.trim().toUpperCase(),
      correlativo: document.getElementById('fCorr').value.trim(),
      issue_date: document.getElementById('fDate').value,
      total_amount: parseFloat(document.getElementById('fTotal').value),
    };
    const r = await fetch('/api/v1/public/consult', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      throw new Error(typeof data.detail === 'string' ? data.detail : 'No se pudo consultar el comprobante.');
    }

    document.getElementById('rDocTitle').textContent = `${data.doc_type_label} ${data.number}`;
    document.getElementById('rIssuer').textContent = `RUC ${data.issuer_ruc} — ${data.issuer_name}`;
    document.getElementById('rBadges').innerHTML =
      statusBadgeHtml(data.status) +
      (data.is_beta ? '<span class="badge b-info">ENTORNO BETA (SIN VALIDEZ TRIBUTARIA)</span>' : '');

    document.getElementById('rDate').textContent = data.issue_date;
    document.getElementById('rTotal').textContent = `${data.currency} ${Number(data.total_amount).toFixed(2)}`;
    document.getElementById('rIgv').textContent = `${data.currency} ${Number(data.igv_amount).toFixed(2)}`;
    document.getElementById('rCustomer').textContent =
      [data.customer_doc_number, data.customer_name].filter(Boolean).join(' — ') || 'Cliente Varios';
    document.getElementById('rSunatMsg').textContent = data.sunat_message || 'Registrado en Sofia Gateway.';
    document.getElementById('rSunatCode').textContent = data.sunat_code || 'En proceso';

    const hashBox = document.getElementById('rHashBox');
    if (data.digest_value) {
      document.getElementById('rDigest').textContent = data.digest_value;
      hashBox.classList.remove('hidden');
    } else {
      hashBox.classList.add('hidden');
    }

    const btnXml = document.getElementById('btnXml');
    if (data.xml_download_url) {
      btnXml.href = data.xml_download_url;
      btnXml.classList.remove('hidden');
    } else {
      btnXml.classList.add('hidden');
    }

    const btnCdr = document.getElementById('btnCdr');
    if (data.cdr_download_url) {
      btnCdr.href = data.cdr_download_url;
      btnCdr.classList.remove('hidden');
    } else {
      btnCdr.classList.add('hidden');
    }

    resCard.classList.remove('hidden');
    resCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (err) {
    errBox.textContent = err.message;
    errBox.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Consultar Comprobante';
  }
}

// Autocompletar si viene con parámetros URL (?ruc=...&tipo=...&serie=...&num=...&fecha=...&total=...)
(function prefillFromQuery() {
  const q = new URLSearchParams(window.location.search);
  if (q.get('ruc')) document.getElementById('fRuc').value = q.get('ruc');
  if (q.get('tipo')) document.getElementById('fType').value = q.get('tipo');
  if (q.get('serie')) document.getElementById('fSerie').value = q.get('serie');
  if (q.get('num')) document.getElementById('fCorr').value = q.get('num');
  if (q.get('fecha')) document.getElementById('fDate').value = q.get('fecha');
  if (q.get('total')) document.getElementById('fTotal').value = q.get('total');
})();
</script>
</body>
</html>
"""


@router.get("/consulta", response_class=HTMLResponse, include_in_schema=False)
async def public_consultation_portal():
    return HTMLResponse(content=PORTAL_HTML)
