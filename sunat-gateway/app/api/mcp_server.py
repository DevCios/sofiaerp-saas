# -*- coding: utf-8 -*-
"""
Servidor Remote MCP (Model Context Protocol - Streamable HTTP / JSON-RPC 2.0)
y Esquema OpenAPI AI curado para API SUNAT (ADR-010).

Compatible con:
- Claude (claude.ai, Claude Desktop, Claude Code)
- ChatGPT (Connectors / Apps MCP y Custom GPT Actions vía /openapi-ai.json)
- Cursor, Windsurf, VS Code Copilot, Gemini CLI, n8n, Make y Zapier
"""
import json
import time
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import assert_ruc_access, get_actor_workspace_id, get_api_client_or_admin
from app.api.v1.routes import emit_document as v1_emit_document
from app.core.config import get_settings
from app.core.database import get_db
from app.models import ApiClient, ApiRequestLog, Document, DocumentStatus, Issuer
from app.schemas import CustomerSchema, DocumentItemSchema, EmitDocumentRequest
from app.services.lookup_service import get_exchange_rate_cached, lookup_dni_cached, lookup_ruc_cached
from app.services.sunat_soap import classify_sunat_code

router = APIRouter()
settings = get_settings()

MCP_PROTOCOL_VERSION = "2025-03-26"
SUPPORTED_PROTOCOL_VERSIONS = {"2025-03-26", "2024-11-05"}

SUNAT_ERROR_CATALOG: dict[str, dict[str, str]] = {
    "0": {
        "title": "Aceptado por SUNAT",
        "cause": "El comprobante cumple todas las validaciones UBL 2.1 y tributarias.",
        "action": "Ninguna acción requerida. Almacena el XML y CDR oficial.",
    },
    "0130": {
        "title": "Servicio SUNAT temporalmente saturado / mantenimiento",
        "cause": "El servidor SOAP de SUNAT no pudo procesar el envío en este momento.",
        "action": "API SUNAT reintentará automáticamente en cola resiliente (no dupliques el comprobante).",
    },
    "1033": {
        "title": "Comprobante registrado previamente con otros datos",
        "cause": "SUNAT ya recibió antes este (RUC, tipo, serie, correlativo), normalmente por un timeout de red.",
        "action": "No reenviar sendBill. API SUNAT ejecuta automáticamente getStatusCdr para recuperar el CDR oficial.",
    },
    "2017": {
        "title": "Número de RUC del receptor no existe o no está activo",
        "cause": "El RUC del cliente en una Factura (01) es inválido o está de baja en SUNAT.",
        "action": "Verifica el RUC del cliente (11 dígitos, activo y habido) o emite Boleta (03) con DNI si es persona natural.",
    },
    "2325": {
        "title": "Certificado digital vencido o firma XML inválida",
        "cause": "El certificado .pfx configurado venció o no corresponde al RUC emisor.",
        "action": "Sube un nuevo certificado .pfx vigente en Empresas y Certificados de API SUNAT.",
    },
    "2335": {
        "title": "RUC del certificado no coincide con el RUC emisor",
        "cause": "El certificado digital pertenece a otra razón social/RUC.",
        "action": "Carga el certificado .pfx emitido específicamente para este RUC.",
    },
    "2800": {
        "title": "Fecha de emisión fuera del plazo permitido",
        "cause": "La fecha de emisión supera el plazo legal de envío SUNAT (3 días para Facturas, 7 días para Boletas).",
        "action": "Emite el comprobante con fecha vigente dentro del plazo legal SUNAT.",
    },
    "4000": {
        "title": "Aceptado con observaciones SUNAT",
        "cause": "El comprobante tiene validez tributaria pero presenta advertencias menores en campos opcionales.",
        "action": "Revisa sunat_notes en la respuesta para corregir el dato en futuras emisiones.",
    },
}


def calculate_totals_data(items: list[dict[str, Any]], currency: str = "PEN") -> dict[str, Any]:
    """Calcula subtotal gravado/exonerado/inafecto, IGV y total con redondeo SUNAT a 2 decimales."""
    taxable = Decimal("0.00")
    exonerated = Decimal("0.00")
    unaffected = Decimal("0.00")
    igv_total = Decimal("0.00")
    computed_items = []

    for idx, item in enumerate(items, start=1):
        qty = Decimal(str(item.get("quantity", 1)))
        unit_price = Decimal(str(item.get("unit_price_without_tax", 0)))
        affect = str(item.get("igv_affectation_code", "10")).strip()
        rate = Decimal(str(item.get("igv_rate", "0.18")))

        line_sub = (qty * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if affect.startswith("1"):
            line_igv = (line_sub * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            taxable += line_sub
            igv_total += line_igv
        elif affect.startswith("2"):
            line_igv = Decimal("0.00")
            exonerated += line_sub
        else:
            line_igv = Decimal("0.00")
            unaffected += line_sub

        computed_items.append({
            "line": idx,
            "description": str(item.get("description", "")),
            "quantity": float(qty),
            "unit_price_without_tax": float(unit_price),
            "igv_affectation_code": affect,
            "line_subtotal": float(line_sub),
            "line_igv": float(line_igv),
            "line_total": float(line_sub + line_igv),
        })

    grand_total = (taxable + exonerated + unaffected + igv_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "currency": currency.upper(),
        "taxable_amount": float(taxable),
        "exonerated_amount": float(exonerated),
        "unaffected_amount": float(unaffected),
        "igv_amount": float(igv_total),
        "total_amount": float(grand_total),
        "items": computed_items,
    }


def explain_sunat_code_data(code: str) -> dict[str, Any]:
    """Clasifica y explica un código SUNAT con recomendación operativa."""
    clean = str(code or "").strip()
    classification = classify_sunat_code(clean)
    info = SUNAT_ERROR_CATALOG.get(clean)
    if not info:
        if classification == "ACCEPTED_WITH_OBS":
            info = SUNAT_ERROR_CATALOG["4000"]
        elif classification == "RETRYABLE":
            info = {
                "title": f"Error transitorio SUNAT ({clean})",
                "cause": "Incidencia temporal de red o servicio en SUNAT.",
                "action": "Mantener en cola de reintentos automáticos de API SUNAT.",
            }
        elif classification == "REJECTED":
            info = {
                "title": f"Rechazo fiscal SUNAT ({clean})",
                "cause": "Error de estructura UBL 2.1 o regla de negocio tributaria SUNAT.",
                "action": "Corrige el dato observado en el comprobante y emite con un nuevo correlativo si aplica.",
            }
        else:
            info = {
                "title": f"Código SUNAT {clean}",
                "cause": "Consulta el detalle de sunat_message y sunat_notes del documento.",
                "action": "Revisa la pestaña Observaciones o Logs en apisunat.pro.",
            }
    return {
        "sunat_code": clean,
        "classification": classification,
        "title": info["title"],
        "cause": info["cause"],
        "recommended_action": info["action"],
    }


# ==============================================================================
# Definición de Tools MCP (JSON Schema 2020-12)
# ==============================================================================
MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "calculate_totals_igv",
        "description": (
            "Calcula montos gravados, exonerados, inafectos, IGV (18% o 10%) y total de un comprobante SUNAT "
            "SIN enviarlo a SUNAT. Úsalo siempre antes de emitir para confirmar montos con el usuario."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "currency": {"type": "string", "enum": ["PEN", "USD"], "default": "PEN"},
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "quantity": {"type": "number", "default": 1},
                            "unit_price_without_tax": {"type": "number"},
                            "igv_affectation_code": {
                                "type": "string",
                                "default": "10",
                                "description": "10=Gravado IGV, 20=Exonerado, 30=Inafecto",
                            },
                            "igv_rate": {"type": "number", "default": 0.18},
                        },
                        "required": ["description", "quantity", "unit_price_without_tax"],
                    },
                },
            },
            "required": ["items"],
        },
    },
    {
        "name": "explain_sunat_error",
        "description": "Explica un código de respuesta o error SUNAT (ej. 0, 1033, 2017, 2325, 4005) y la acción recomendada.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sunat_code": {"type": "string", "description": "Código numérico SUNAT (ej. '1033', '2017', '4005')."},
            },
            "required": ["sunat_code"],
        },
    },
    {
        "name": "list_issuers",
        "description": "Lista las empresas emisoras (RUCs) autorizadas para tu API Key en API SUNAT, indicando si operan en BETA o PRODUCCIÓN.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_documents",
        "description": "Lista los comprobantes electrónicos recientes en API SUNAT (filtrables por RUC y estado).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ruc": {"type": "string", "description": "RUC emisor de 11 dígitos (opcional)."},
                "status": {
                    "type": "string",
                    "description": "Estado opcional: QUEUED, ACCEPTED, ACCEPTED_WITH_OBS, RETRY_SCHEDULED, RECOVERING_CDR, REJECTED.",
                },
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
            },
        },
    },
    {
        "name": "lookup_document",
        "description": "Consulta el estado SUNAT, código CDR y URLs de descarga XML/CDR de un comprobante específico por RUC, tipo, serie y correlativo.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issuer_ruc": {"type": "string", "description": "RUC del emisor (11 dígitos)."},
                "doc_type": {"type": "string", "enum": ["01", "03", "07", "08"], "description": "01=Factura, 03=Boleta, 07=NC, 08=ND."},
                "serie": {"type": "string", "description": "Serie de 4 caracteres (ej. FE01, BE01)."},
                "correlativo": {"type": "string", "description": "Correlativo numérico (ej. 1 o 00000001)."},
            },
            "required": ["issuer_ruc", "doc_type", "serie", "correlativo"],
        },
    },
    {
        "name": "lookup_ruc",
        "description": "Consulta los datos oficiales SUNAT de un RUC peruano (11 dígitos): razón social, dirección, ubigeo, estado y condición (con caché compartido).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ruc": {"type": "string", "description": "RUC peruano de 11 dígitos (ej. 20100047218)."},
            },
            "required": ["ruc"],
        },
    },
    {
        "name": "lookup_dni",
        "description": "Consulta los nombres y apellidos de un DNI peruano (8 dígitos) en RENIEC (con caché compartido).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dni": {"type": "string", "description": "DNI peruano de 8 dígitos."},
            },
            "required": ["dni"],
        },
    },
    {
        "name": "get_exchange_rate",
        "description": "Obtiene el Tipo de Cambio oficial SUNAT (USD a PEN: compra y venta) del día o de una fecha específica (YYYY-MM-DD).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Fecha opcional YYYY-MM-DD (por defecto hoy en Lima)."},
            },
        },
    },
    {
        "name": "emit_document",
        "description": (
            "Emite una Factura (01) o Boleta (03) electrónica a SUNAT vía API SUNAT con idempotencia estricta por (RUC, tipo, serie, correlativo). "
            "IMPORTANTE: antes de invocar esta herramienta en producción, muestra el cálculo al usuario con calculate_totals_igv y pide confirmación."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "issuer_ruc": {"type": "string", "description": "RUC del emisor (11 dígitos)."},
                "doc_type": {"type": "string", "enum": ["01", "03"], "default": "01"},
                "serie": {"type": "string", "description": "Serie de 4 caracteres (FE01 para Factura, BE01 para Boleta)."},
                "correlativo": {"type": "string", "description": "Número correlativo (ej. '1')."},
                "issue_date": {"type": "string", "description": "Fecha YYYY-MM-DD (hora Lima)."},
                "currency": {"type": "string", "enum": ["PEN", "USD"], "default": "PEN"},
                "customer_doc_type": {"type": "string", "default": "6", "description": "6=RUC, 1=DNI, 0=Sin documento."},
                "customer_doc_number": {"type": "string", "description": "RUC (11 dígitos) o DNI (8 dígitos) del cliente."},
                "customer_name": {"type": "string", "description": "Razón social o nombre completo del cliente."},
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "default": "GEN"},
                            "description": {"type": "string"},
                            "unit_code": {"type": "string", "default": "NIU"},
                            "quantity": {"type": "number", "default": 1},
                            "unit_price_without_tax": {"type": "number"},
                            "igv_affectation_code": {"type": "string", "default": "10"},
                            "igv_rate": {"type": "number", "default": 0.18},
                        },
                        "required": ["description", "quantity", "unit_price_without_tax"],
                    },
                },
                "try_sync": {"type": "boolean", "default": True},
            },
            "required": [
                "issuer_ruc",
                "doc_type",
                "serie",
                "correlativo",
                "issue_date",
                "customer_doc_number",
                "customer_name",
                "items",
            ],
        },
    },
]


async def _execute_mcp_tool(
    tool_name: str,
    arguments: dict[str, Any],
    auth: tuple[Optional[ApiClient], Optional[dict]],
    db: AsyncSession,
) -> dict[str, Any]:
    api_client, actor = auth
    ws_id = (api_client.workspace_id if api_client else None) or get_actor_workspace_id(actor)

    if tool_name == "calculate_totals_igv":
        items = arguments.get("items") or []
        if not items:
            raise ValueError("Debes proporcionar al menos un ítem en 'items'.")
        return calculate_totals_data(items, currency=arguments.get("currency", "PEN"))

    if tool_name == "explain_sunat_error":
        return explain_sunat_code_data(str(arguments.get("sunat_code", "")))

    if tool_name == "list_issuers":
        stmt = select(Issuer).where(Issuer.is_active.is_(True)).order_by(desc(Issuer.created_at))
        if ws_id:
            stmt = stmt.where(Issuer.workspace_id == ws_id)
        if api_client and api_client.allowed_rucs:
            stmt = stmt.where(Issuer.ruc.in_(api_client.allowed_rucs))
        res = await db.execute(stmt)
        issuers = res.scalars().all()
        return {
            "count": len(issuers),
            "issuers": [
                {
                    "ruc": iss.ruc,
                    "business_name": iss.business_name,
                    "environment": "BETA" if iss.is_beta else "PRODUCTION",
                    "is_nrus": iss.is_nrus,
                    "has_certificate": bool(iss.pfx_content_enc),
                    "has_sol": bool(iss.sol_username_enc),
                }
                for iss in issuers
            ],
        }

    if tool_name == "list_documents":
        ruc = arguments.get("ruc")
        status_filter = arguments.get("status")
        limit = min(max(int(arguments.get("limit", 20)), 1), 100)
        stmt = select(Document).order_by(desc(Document.created_at)).limit(limit)
        ws_rucs: Optional[list[str]] = None
        if ws_id:
            ws_rows = await db.execute(select(Issuer.ruc).where(Issuer.workspace_id == ws_id))
            ws_rucs = [r[0] for r in ws_rows.all()]
        if api_client and api_client.allowed_rucs:
            if ruc:
                assert_ruc_access(api_client, ruc)
                if ws_rucs is not None and ruc not in ws_rucs:
                    raise PermissionError(f"Sin permisos para el RUC {ruc}.")
                stmt = stmt.where(Document.issuer_ruc == ruc)
            else:
                allowed = [r for r in api_client.allowed_rucs if ws_rucs is None or r in ws_rucs]
                stmt = stmt.where(Document.issuer_ruc.in_(allowed or ["__none__"]))
        elif ws_rucs is not None:
            if ruc:
                if ruc not in ws_rucs:
                    raise PermissionError(f"Sin permisos para el RUC {ruc}.")
                stmt = stmt.where(Document.issuer_ruc == ruc)
            else:
                stmt = stmt.where(Document.issuer_ruc.in_(ws_rucs or ["__none__"]))
        elif ruc:
            stmt = stmt.where(Document.issuer_ruc == ruc)
        if status_filter:
            stmt = stmt.where(Document.status == DocumentStatus(status_filter))
        res = await db.execute(stmt)
        docs = res.scalars().all()
        return {
            "count": len(docs),
            "documents": [
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
                }
                for d in docs
            ],
        }

    if tool_name == "lookup_document":
        issuer_ruc = str(arguments["issuer_ruc"]).strip()
        assert_ruc_access(api_client, issuer_ruc)
        if ws_id:
            ws_check = await db.execute(select(Issuer.id).where(Issuer.ruc == issuer_ruc, Issuer.workspace_id == ws_id))
            if not ws_check.scalar_one_or_none():
                raise PermissionError(f"Sin permisos para consultar el RUC {issuer_ruc}.")
        doc_type = str(arguments["doc_type"]).strip()
        serie = str(arguments["serie"]).strip().upper()
        clean_corr = (str(arguments["correlativo"]).strip().lstrip("0") or "1").zfill(8)
        res = await db.execute(
            select(Document).where(
                Document.issuer_ruc == issuer_ruc,
                Document.doc_type == doc_type,
                Document.serie == serie,
                Document.correlativo == clean_corr,
            )
        )
        doc = res.scalar_one_or_none()
        if not doc:
            return {"found": False, "message": f"Comprobante {serie}-{clean_corr} no encontrado para RUC {issuer_ruc}."}
        return {
            "found": True,
            "document_id": doc.id,
            "number": f"{doc.serie}-{doc.correlativo}",
            "status": doc.status.value,
            "sunat_code": doc.sunat_code,
            "sunat_message": doc.sunat_message,
            "sunat_notes": doc.sunat_notes or [],
            "xml_url": f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{doc.id}/xml",
            "cdr_url": f"{settings.PUBLIC_BASE_URL}/api/v1/documents/{doc.id}/cdr" if doc.cdr_path else None,
        }

    if tool_name == "lookup_ruc":
        return await lookup_ruc_cached(db, str(arguments.get("ruc", "")))

    if tool_name == "lookup_dni":
        return await lookup_dni_cached(db, str(arguments.get("dni", "")))

    if tool_name == "get_exchange_rate":
        return await get_exchange_rate_cached(db, rate_date=arguments.get("date"))

    if tool_name == "emit_document":
        req_items = [
            DocumentItemSchema(
                code=str(it.get("code") or "GEN"),
                description=str(it["description"]),
                unit_code=str(it.get("unit_code") or "NIU"),
                quantity=Decimal(str(it.get("quantity", 1))),
                unit_price_without_tax=Decimal(str(it["unit_price_without_tax"])),
                igv_affectation_code=str(it.get("igv_affectation_code") or "10"),
                igv_rate=Decimal(str(it.get("igv_rate", "0.18"))),
            )
            for it in (arguments.get("items") or [])
        ]
        emit_req = EmitDocumentRequest(
            issuer_ruc=str(arguments["issuer_ruc"]).strip(),
            doc_type=str(arguments.get("doc_type") or "01").strip(),
            serie=str(arguments["serie"]).strip().upper(),
            correlativo=str(arguments["correlativo"]).strip(),
            issue_date=str(arguments["issue_date"]).strip(),
            currency=str(arguments.get("currency") or "PEN").strip().upper(),
            customer=CustomerSchema(
                doc_type=str(arguments.get("customer_doc_type") or ("6" if arguments.get("doc_type") == "01" else "1")),
                doc_number=str(arguments["customer_doc_number"]).strip(),
                name=str(arguments["customer_name"]).strip(),
            ),
            items=req_items,
            try_sync=bool(arguments.get("try_sync", True)),
        )
        resp = await v1_emit_document(body=emit_req, auth=auth, db=db)
        return resp.model_dump()

    raise ValueError(f"Herramienta MCP desconocida: '{tool_name}'.")


def _jsonrpc_ok(req_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _jsonrpc_err(req_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


# ==============================================================================
# Endpoints Remote MCP (/mcp)
# ==============================================================================
@router.get("/mcp", tags=["AI Connectors"])
async def mcp_discovery():
    """Metadatos de descubrimiento del servidor Remote MCP de API SUNAT."""
    return {
        "name": "sofia-sunat-gateway-mcp",
        "version": settings.APP_VERSION,
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "transport": "streamable-http",
        "endpoint": f"{settings.PUBLIC_BASE_URL}/mcp",
        "openapi_ai": f"{settings.PUBLIC_BASE_URL}/openapi-ai.json",
        "auth": "Authorization: Bearer <sk_live_...> o X-API-Key: <sk_live_...>",
        "tools_count": len(MCP_TOOLS),
    }


@router.post("/mcp", tags=["AI Connectors"])
async def mcp_jsonrpc_endpoint(
    request: Request,
    auth=Depends(get_api_client_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Endpoint oficial Remote MCP (JSON-RPC 2.0 sobre Streamable HTTP)."""
    try:
        payload = await request.json()
    except Exception:
        return _jsonrpc_err(None, -32700, "Parse error: JSON inválido.")

    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0" or "method" not in payload:
        return _jsonrpc_err(payload.get("id") if isinstance(payload, dict) else None, -32600, "Invalid Request.")

    req_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    # Notificaciones JSON-RPC (sin id): aceptar con 202 Accepted
    if method == "notifications/initialized" or req_id is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)

    if method == "initialize":
        requested_version = params.get("protocolVersion", MCP_PROTOCOL_VERSION)
        negotiated = requested_version if requested_version in SUPPORTED_PROTOCOL_VERSIONS else MCP_PROTOCOL_VERSION
        return _jsonrpc_ok(
            req_id,
            {
                "protocolVersion": negotiated,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "sofia-sunat-gateway",
                    "version": settings.APP_VERSION,
                },
                "instructions": (
                    "Eres un asistente conectado a API SUNAT (Perú). "
                    "Antes de emitir un comprobante con emit_document, calcula y muestra los totales con calculate_totals_igv "
                    "y confirma con el usuario el RUC, monto y entorno (BETA o PRODUCCIÓN)."
                ),
            },
        )

    if method == "ping":
        return _jsonrpc_ok(req_id, {})

    if method == "tools/list":
        return _jsonrpc_ok(req_id, {"tools": MCP_TOOLS})

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        if not tool_name:
            return _jsonrpc_err(req_id, -32602, "Parámetro 'name' requerido en tools/call.")
        t0 = time.monotonic()
        api_client, admin = auth
        client_label = api_client.name if api_client else (admin.get("sub") if admin else "gateway")
        arg_ruc = arguments.get("issuer_ruc") or arguments.get("ruc")
        try:
            result_data = await _execute_mcp_tool(tool_name, arguments, auth, db)
            db.add(
                ApiRequestLog(
                    source="MCP",
                    method="TOOL",
                    action=f"mcp:{tool_name}",
                    issuer_ruc=str(arg_ruc)[:11] if arg_ruc else None,
                    client_label=str(client_label)[:120],
                    status_code=200,
                    latency_ms=int((time.monotonic() - t0) * 1000),
                )
            )
            await db.commit()
            return _jsonrpc_ok(
                req_id,
                {
                    "content": [{"type": "text", "text": json.dumps(result_data, ensure_ascii=False, indent=2)}],
                    "structuredContent": result_data,
                    "isError": False,
                },
            )
        except HTTPException as exc:
            err_payload = {"error": exc.detail, "http_status": exc.status_code}
            db.add(
                ApiRequestLog(
                    source="MCP",
                    method="TOOL",
                    action=f"mcp:{tool_name}",
                    issuer_ruc=str(arg_ruc)[:11] if arg_ruc else None,
                    client_label=str(client_label)[:120],
                    status_code=exc.status_code,
                    latency_ms=int((time.monotonic() - t0) * 1000),
                    error_summary=str(exc.detail)[:280],
                )
            )
            await db.commit()
            return _jsonrpc_ok(
                req_id,
                {
                    "content": [{"type": "text", "text": json.dumps(err_payload, ensure_ascii=False)}],
                    "isError": True,
                },
            )
        except Exception as exc:
            err_payload = {"error": str(exc)}
            db.add(
                ApiRequestLog(
                    source="MCP",
                    method="TOOL",
                    action=f"mcp:{tool_name}",
                    issuer_ruc=str(arg_ruc)[:11] if arg_ruc else None,
                    client_label=str(client_label)[:120],
                    status_code=400,
                    latency_ms=int((time.monotonic() - t0) * 1000),
                    error_summary=str(exc)[:280],
                )
            )
            await db.commit()
            return _jsonrpc_ok(
                req_id,
                {
                    "content": [{"type": "text", "text": json.dumps(err_payload, ensure_ascii=False)}],
                    "isError": True,
                },
            )

    return _jsonrpc_err(req_id, -32601, f"Method not found: {method}")


# ==============================================================================
# Endpoints REST auxiliares para Custom GPT Actions / n8n / Make
# ==============================================================================
class CalculateTotalsRequest(BaseModel):
    currency: str = Field(default="PEN", pattern="^(PEN|USD)$")
    items: list[dict[str, Any]] = Field(..., min_length=1)


@router.post("/api/v1/ai/calculate-totals", tags=["AI Connectors"])
async def rest_calculate_totals(
    body: CalculateTotalsRequest,
    _auth=Depends(get_api_client_or_admin),
):
    return calculate_totals_data(body.items, currency=body.currency)


@router.get("/api/v1/ai/explain-sunat-error/{sunat_code}", tags=["AI Connectors"])
async def rest_explain_sunat_error(
    sunat_code: str,
    _auth=Depends(get_api_client_or_admin),
):
    return explain_sunat_code_data(sunat_code)


@router.get("/openapi-ai.json", tags=["AI Connectors"])
async def openapi_ai_schema():
    """Esquema OpenAPI 3.1 curado para ChatGPT Custom GPT Actions, n8n, Make y Zapier."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "API SUNAT — AI Actions API",
            "version": settings.APP_VERSION,
            "description": (
                "API oficial de facturación electrónica SUNAT (Perú) para asistentes de IA (ChatGPT Actions, n8n, Make). "
                "Autenticación mediante Bearer API Key (sk_live_...) aislada por RUC."
            ),
        },
        "servers": [{"url": settings.PUBLIC_BASE_URL}],
        "components": {
            "securitySchemes": {
                "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "API Key (sk_live_...)"}
            }
        },
        "security": [{"BearerAuth": []}],
        "paths": {
            "/api/v1/ai/calculate-totals": {
                "post": {
                    "operationId": "calculateTotalsIgv",
                    "summary": "Calcular subtotal, IGV y total sin emitir a SUNAT",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "currency": {"type": "string", "enum": ["PEN", "USD"], "default": "PEN"},
                                        "items": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "description": {"type": "string"},
                                                    "quantity": {"type": "number", "default": 1},
                                                    "unit_price_without_tax": {"type": "number"},
                                                    "igv_affectation_code": {"type": "string", "default": "10"},
                                                    "igv_rate": {"type": "number", "default": 0.18},
                                                },
                                                "required": ["description", "quantity", "unit_price_without_tax"],
                                            },
                                        },
                                    },
                                    "required": ["items"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "Cálculo de totales e IGV"}},
                }
            },
            "/api/v1/ai/explain-sunat-error/{sunat_code}": {
                "get": {
                    "operationId": "explainSunatError",
                    "summary": "Explicar un código de error u observación SUNAT",
                    "parameters": [
                        {"name": "sunat_code", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "Explicación y acción correctiva"}},
                }
            },
            "/api/v1/lookup/ruc/{ruc}": {
                "get": {
                    "operationId": "lookupPeruRuc",
                    "summary": "Consultar RUC peruano en SUNAT (razón social, dirección, estado, condición)",
                    "parameters": [{"name": "ruc", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Datos oficiales del RUC"}},
                }
            },
            "/api/v1/lookup/dni/{dni}": {
                "get": {
                    "operationId": "lookupPeruDni",
                    "summary": "Consultar DNI peruano en RENIEC (nombres y apellidos)",
                    "parameters": [{"name": "dni", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Datos del DNI"}},
                }
            },
            "/api/v1/lookup/exchange-rate": {
                "get": {
                    "operationId": "getSunatExchangeRate",
                    "summary": "Consultar Tipo de Cambio oficial SUNAT (USD -> PEN compra y venta)",
                    "parameters": [{"name": "date", "in": "query", "required": False, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Tipo de cambio del día"}},
                }
            },
            "/api/v1/documents/emit": {
                "post": {
                    "operationId": "emitSunatDocument",
                    "summary": "Emitir Factura (01) o Boleta (03) electrónica SUNAT (idempotente)",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "issuer_ruc": {"type": "string", "description": "RUC emisor de 11 dígitos"},
                                        "doc_type": {"type": "string", "enum": ["01", "03"], "default": "01"},
                                        "serie": {"type": "string", "description": "Serie de 4 caracteres (ej. FE01, BE01)"},
                                        "correlativo": {"type": "string", "description": "Correlativo numérico (ej. '10')"},
                                        "issue_date": {"type": "string", "description": "Fecha YYYY-MM-DD (hora Lima)"},
                                        "currency": {"type": "string", "enum": ["PEN", "USD"], "default": "PEN"},
                                        "try_sync": {"type": "boolean", "default": True},
                                        "customer": {
                                            "type": "object",
                                            "properties": {
                                                "doc_type": {"type": "string", "description": "6=RUC, 1=DNI, 0=Sin doc"},
                                                "doc_number": {"type": "string", "description": "RUC (11) o DNI (8) del cliente"},
                                                "name": {"type": "string", "description": "Razón social o nombre del cliente"},
                                            },
                                            "required": ["doc_type", "doc_number", "name"],
                                        },
                                        "items": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "code": {"type": "string", "default": "GEN"},
                                                    "description": {"type": "string"},
                                                    "unit_code": {"type": "string", "default": "NIU"},
                                                    "quantity": {"type": "number", "default": 1},
                                                    "unit_price_without_tax": {"type": "number"},
                                                    "igv_affectation_code": {"type": "string", "default": "10"},
                                                    "igv_rate": {"type": "number", "default": 0.18},
                                                },
                                                "required": ["description", "quantity", "unit_price_without_tax"],
                                            },
                                        },
                                    },
                                    "required": [
                                        "issuer_ruc",
                                        "doc_type",
                                        "serie",
                                        "correlativo",
                                        "issue_date",
                                        "customer",
                                        "items",
                                    ],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "Comprobante firmado y enviado/encolado en SUNAT"}},
                }
            },
            "/api/v1/documents/lookup": {
                "get": {
                    "operationId": "lookupSunatDocument",
                    "summary": "Consultar estado SUNAT y CDR por RUC, tipo, serie y correlativo",
                    "parameters": [
                        {"name": "issuer_ruc", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "doc_type", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "serie", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "correlativo", "in": "query", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "Estado del comprobante"}},
                }
            },
            "/api/v1/documents": {
                "get": {
                    "operationId": "listSunatDocuments",
                    "summary": "Listar últimos comprobantes electrónicos",
                    "parameters": [
                        {"name": "ruc", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "status", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "default": 20}},
                    ],
                    "responses": {"200": {"description": "Lista de comprobantes"}},
                }
            },
        },
    }
