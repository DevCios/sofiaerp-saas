# -*- coding: utf-8 -*-
import base64
import io
import time
import zipfile
from dataclasses import dataclass
from typing import Optional

import httpx
from lxml import etree

from app.core.config import get_settings

settings = get_settings()

SOAP_SEND_BILL_TPL = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ser="http://service.sunat.gob.pe"
                  xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
  <soapenv:Header>
    <wsse:Security>
      <wsse:UsernameToken>
        <wsse:Username>{username}</wsse:Username>
        <wsse:Password>{password}</wsse:Password>
      </wsse:UsernameToken>
    </wsse:Security>
  </soapenv:Header>
  <soapenv:Body>
    <ser:sendBill>
      <fileName>{zip_filename}</fileName>
      <contentFile>{zip_b64}</contentFile>
    </ser:sendBill>
  </soapenv:Body>
</soapenv:Envelope>"""

SOAP_GET_STATUS_CDR_TPL = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ser="http://service.sunat.gob.pe"
                  xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
  <soapenv:Header>
    <wsse:Security>
      <wsse:UsernameToken>
        <wsse:Username>{username}</wsse:Username>
        <wsse:Password>{password}</wsse:Password>
      </wsse:UsernameToken>
    </wsse:Security>
  </soapenv:Header>
  <soapenv:Body>
    <ser:getStatusCdr>
      <rucComprobante>{ruc}</rucComprobante>
      <tipoComprobante>{doc_type}</tipoComprobante>
      <serieComprobante>{serie}</serieComprobante>
      <numeroComprobante>{correlativo}</numeroComprobante>
    </ser:getStatusCdr>
  </soapenv:Body>
</soapenv:Envelope>"""


@dataclass
class SunatResponse:
    outcome: str  # ACCEPTED, ACCEPTED_WITH_OBS, REJECTED, RETRYABLE, RECOVER_CDR
    http_status: Optional[int] = None
    sunat_code: Optional[str] = None
    sunat_message: Optional[str] = None
    notes: Optional[list[str]] = None
    cdr_zip_bytes: Optional[bytes] = None
    latency_ms: int = 0
    endpoint_url: str = ""


def classify_sunat_code(code: Optional[str]) -> str:
    """
    Clasificación oficial SUNAT:
    - 0: Aceptado
    - >= 4000: Aceptado con observaciones
    - 1033: Registrado previamente -> recuperar CDR vía getStatusCdr
    - 0100 - 1999: Excepción temporal/sistema -> Reintentar
    - 2000 - 3999: Rechazo definitivo de negocio -> No reintentar
    """
    if not code:
        return "RETRYABLE"
    clean = code.strip().split(".")[-1]
    if clean == "0":
        return "ACCEPTED"
    if clean == "1033":
        return "RECOVER_CDR"
    if clean.isdigit():
        num = int(clean)
        if num >= 4000:
            return "ACCEPTED_WITH_OBS"
        if 2000 <= num <= 3999:
            return "REJECTED"
        if 100 <= num <= 1999:
            return "RETRYABLE"
    return "RETRYABLE"


def extract_cdr_xml_from_zip(cdr_zip_bytes: bytes) -> bytes:
    """Extrae los bytes del archivo XML contenido dentro del CDR .zip de SUNAT."""
    with zipfile.ZipFile(io.BytesIO(cdr_zip_bytes), "r") as zf:
        xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if not xml_names:
            raise ValueError("El CDR .zip devuelto por SUNAT no contiene ningún archivo XML.")
        return zf.read(xml_names[0])


def parse_cdr_zip(cdr_zip_bytes: bytes) -> tuple[str, str, list[str]]:
    """Extrae ResponseCode, Description y Notes del XML contenido dentro del CDR .zip de SUNAT."""
    cdr_xml = extract_cdr_xml_from_zip(cdr_zip_bytes)

    root = etree.fromstring(cdr_xml)
    ns = {
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    }
    code_nodes = root.xpath(".//cac:DocumentResponse/cac:Response/cbc:ResponseCode/text()", namespaces=ns)
    desc_nodes = root.xpath(".//cac:DocumentResponse/cac:Response/cbc:Description/text()", namespaces=ns)
    notes = [n.strip() for n in root.xpath(".//cbc:Note/text()", namespaces=ns) if n.strip()]

    code = code_nodes[0].strip() if code_nodes else "0"
    desc = desc_nodes[0].strip() if desc_nodes else "Comprobante procesado por SUNAT."
    return code, desc, notes


def _zip_xml_bytes(xml_filename: str, xml_bytes: bytes) -> tuple[str, str]:
    base_name = xml_filename[:-4] if xml_filename.lower().endswith(".xml") else xml_filename
    zip_filename = f"{base_name}.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_name}.xml", xml_bytes)
    return zip_filename, base64.b64encode(buf.getvalue()).decode("ascii")


def _extract_soap_fault(xml_text: bytes) -> tuple[Optional[str], Optional[str]]:
    try:
        root = etree.fromstring(xml_text)
        faultcode = root.xpath(".//*[local-name()='faultcode']/text()")
        faultstring = root.xpath(".//*[local-name()='faultstring']/text()")
        code = faultcode[0].strip() if faultcode else None
        msg = faultstring[0].strip() if faultstring else None
        return code, msg
    except Exception:
        return None, None


def send_bill_to_sunat(
    ruc: str,
    xml_filename: str,
    xml_bytes: bytes,
    sol_username: str,
    sol_password: str,
    is_beta: bool = True,
    timeout_seconds: Optional[int] = None,
) -> SunatResponse:
    """Envía un comprobante firmado (sendBill) a SUNAT Beta o Producción."""
    url = settings.SUNAT_BILL_BETA_URL if is_beta else settings.SUNAT_BILL_PROD_URL
    ws_user = "MODDATOS" if is_beta else (sol_username if sol_username.startswith(ruc) else f"{ruc}{sol_username}")
    ws_pass = "MODDATOS" if is_beta else sol_password

    zip_filename, zip_b64 = _zip_xml_bytes(xml_filename, xml_bytes)
    envelope = SOAP_SEND_BILL_TPL.format(
        username=ws_user,
        password=ws_pass,
        zip_filename=zip_filename,
        zip_b64=zip_b64,
    ).encode("utf-8")

    t0 = time.monotonic()
    try:
        with httpx.Client(timeout=timeout_seconds or settings.SUNAT_TIMEOUT_SECONDS) as client:
            resp = client.post(
                url,
                content=envelope,
                headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "urn:sendBill"},
            )
        latency_ms = int((time.monotonic() - t0) * 1000)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        return SunatResponse(
            outcome="RETRYABLE",
            http_status=None,
            sunat_code="NET_ERR",
            sunat_message=f"Error de red/timeout hacia SUNAT: {exc}",
            latency_ms=int((time.monotonic() - t0) * 1000),
            endpoint_url=url,
        )

    if resp.status_code >= 500:
        code, msg = _extract_soap_fault(resp.content)
        outcome = classify_sunat_code(code) if code else "RETRYABLE"
        return SunatResponse(
            outcome=outcome,
            http_status=resp.status_code,
            sunat_code=code or f"HTTP_{resp.status_code}",
            sunat_message=msg or f"SUNAT devolvió HTTP {resp.status_code}",
            latency_ms=latency_ms,
            endpoint_url=url,
        )

    try:
        root = etree.fromstring(resp.content)
        app_resp = root.xpath(".//*[local-name()='applicationResponse']/text()")
        if app_resp:
            cdr_bytes = base64.b64decode(app_resp[0].strip())
            code, desc, notes = parse_cdr_zip(cdr_bytes)
            return SunatResponse(
                outcome=classify_sunat_code(code),
                http_status=resp.status_code,
                sunat_code=code,
                sunat_message=desc,
                notes=notes,
                cdr_zip_bytes=cdr_bytes,
                latency_ms=latency_ms,
                endpoint_url=url,
            )
        code, msg = _extract_soap_fault(resp.content)
        return SunatResponse(
            outcome=classify_sunat_code(code),
            http_status=resp.status_code,
            sunat_code=code or "SOAP_FAULT",
            sunat_message=msg or "Respuesta SOAP sin applicationResponse.",
            latency_ms=latency_ms,
            endpoint_url=url,
        )
    except Exception as exc:
        return SunatResponse(
            outcome="RETRYABLE",
            http_status=resp.status_code,
            sunat_code="PARSE_ERR",
            sunat_message=f"No se pudo interpretar respuesta SUNAT: {exc}",
            latency_ms=latency_ms,
            endpoint_url=url,
        )


def recover_cdr_from_sunat(
    ruc: str,
    doc_type: str,
    serie: str,
    correlativo: str,
    sol_username: str,
    sol_password: str,
    is_beta: bool = True,
) -> SunatResponse:
    """
    Antídoto contra el Error 1033 y cortes tras envío:
    Consulta getStatusCdr en SUNAT para recuperar el CDR oficial sin reenviar el comprobante.
    """
    url = settings.SUNAT_BILL_BETA_URL if is_beta else settings.SUNAT_CDR_PROD_URL
    ws_user = "MODDATOS" if is_beta else (sol_username if sol_username.startswith(ruc) else f"{ruc}{sol_username}")
    ws_pass = "MODDATOS" if is_beta else sol_password

    num_int = str(int(correlativo))
    envelope = SOAP_GET_STATUS_CDR_TPL.format(
        username=ws_user,
        password=ws_pass,
        ruc=ruc,
        doc_type=doc_type,
        serie=serie,
        correlativo=num_int,
    ).encode("utf-8")

    t0 = time.monotonic()
    try:
        with httpx.Client(timeout=settings.SUNAT_TIMEOUT_SECONDS) as client:
            resp = client.post(
                url,
                content=envelope,
                headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "urn:getStatusCdr"},
            )
        latency_ms = int((time.monotonic() - t0) * 1000)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        return SunatResponse(
            outcome="RETRYABLE",
            sunat_code="NET_ERR",
            sunat_message=f"Error de red consultando getStatusCdr: {exc}",
            latency_ms=int((time.monotonic() - t0) * 1000),
            endpoint_url=url,
        )

    try:
        root = etree.fromstring(resp.content)
        content_nodes = root.xpath(".//*[local-name()='content']/text()")
        status_code = root.xpath(".//*[local-name()='statusCode']/text()")
        status_msg = root.xpath(".//*[local-name()='statusMessage']/text()")
        if content_nodes and content_nodes[0].strip():
            cdr_bytes = base64.b64decode(content_nodes[0].strip())
            code, desc, notes = parse_cdr_zip(cdr_bytes)
            return SunatResponse(
                outcome=classify_sunat_code(code),
                http_status=resp.status_code,
                sunat_code=code,
                sunat_message=f"[CDR Recuperado] {desc}",
                notes=notes,
                cdr_zip_bytes=cdr_bytes,
                latency_ms=latency_ms,
                endpoint_url=url,
            )
        return SunatResponse(
            outcome="RETRYABLE",
            http_status=resp.status_code,
            sunat_code=status_code[0].strip() if status_code else "NO_CDR",
            sunat_message=status_msg[0].strip() if status_msg else "SUNAT aún no devuelve CDR.",
            latency_ms=latency_ms,
            endpoint_url=url,
        )
    except Exception as exc:
        return SunatResponse(
            outcome="RETRYABLE",
            http_status=resp.status_code,
            sunat_code="PARSE_ERR",
            sunat_message=f"Error leyendo getStatusCdr: {exc}",
            latency_ms=latency_ms,
            endpoint_url=url,
        )
