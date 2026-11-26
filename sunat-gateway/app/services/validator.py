# -*- coding: utf-8 -*-
import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from app.models import Issuer
from app.schemas import EmitDocumentRequest

SERIE_FACTURA_RE = re.compile(r"^F[A-Z0-9]{3}$")
SERIE_BOLETA_RE = re.compile(r"^B[A-Z0-9]{3}$")
SERIE_NOTA_RE = re.compile(r"^[FB][A-Z0-9]{3}$")


class FiscalValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def q2(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_emit_request(req: EmitDocumentRequest, issuer: Issuer) -> dict:
    """
    Pre-validador fiscal SUNAT anti-rechazos.
    Detecta errores tributarios antes de firmar o enviar para evitar rechazos irreversibles (2xxx/3xxx).
    Retorna resumen de totales calculados (subtotal, igv, total).
    """
    errors: list[str] = []

    if not issuer.is_active:
        errors.append(f"La empresa emisora RUC {issuer.ruc} está desactivada en el Gateway.")

    # 1. Validación de certificado vigente y protección Producción vs Beta
    if not req.already_signed:
        if not issuer.pfx_content_enc:
            errors.append(f"La empresa RUC {issuer.ruc} no tiene un certificado digital (.pfx) configurado.")
        else:
            if not issuer.is_beta and issuer.cert_is_demo:
                errors.append("No se puede emitir en Producción Real con un certificado DEMO BETA. Sube el .pfx oficial.")
            if issuer.cert_expires_at and issuer.cert_expires_at < datetime.now(timezone.utc):
                errors.append(f"El certificado digital de RUC {issuer.ruc} venció el {issuer.cert_expires_at.date()}.")

    # 2. Validación de Serie vs Tipo de Comprobante según RS SUNAT
    if req.doc_type == "01" and not SERIE_FACTURA_RE.match(req.serie):
        errors.append(f"La serie '{req.serie}' no es válida para Factura (01): debe iniciar con 'F' (ej. F001, FE01).")
    elif req.doc_type == "03" and not SERIE_BOLETA_RE.match(req.serie):
        errors.append(f"La serie '{req.serie}' no es válida para Boleta (03): debe iniciar con 'B' (ej. B001, BE01).")
    elif req.doc_type in ("07", "08") and not SERIE_NOTA_RE.match(req.serie):
        errors.append(f"La serie '{req.serie}' no es válida para Nota (07/08): debe iniciar con 'F' o 'B'.")

    # 3. Validación de fecha de emisión (alerta si excede 3 días hacia atrás en Producción)
    try:
        issue_dt = datetime.strptime(req.issue_date, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        delta_days = (today - issue_dt).days
        if not issuer.is_beta and req.doc_type in ("01", "07", "08") and delta_days > 3:
            errors.append(
                f"Fecha de emisión {req.issue_date} excede el plazo legal SUNAT de 3 días calendario ({delta_days} días)."
            )
        if delta_days < -2:
            errors.append(f"Fecha de emisión {req.issue_date} no puede ser futura.")
    except ValueError:
        errors.append("Formato de fecha inválido (use YYYY-MM-DD).")

    # 4. Modo Passthrough vs Modo JSON estructurado
    if req.raw_xml_base64:
        if errors:
            raise FiscalValidationError(errors)
        return {
            "mode": "xml_passthrough",
            "taxable_amount": Decimal("0.00"),
            "exempt_amount": Decimal("0.00"),
            "unaffected_amount": Decimal("0.00"),
            "igv_amount": q2(req.igv_amount_hint or Decimal("0.00")),
            "total_amount": q2(req.total_amount_hint or Decimal("0.00")),
        }

    # Modo JSON estructurado
    if not req.customer:
        errors.append("En modo JSON debes enviar 'customer' (datos del cliente).")
    if not req.items or len(req.items) == 0:
        errors.append("En modo JSON debes enviar al menos 1 ítem en 'items'.")

    if req.customer:
        if req.doc_type == "01":
            if req.customer.doc_type != "6" or not re.match(r"^\d{11}$", req.customer.doc_number):
                errors.append("Factura Electrónica (01) requiere cliente con RUC válido de 11 dígitos (doc_type='6').")
        elif req.doc_type == "03":
            if req.customer.doc_type == "1" and not re.match(r"^\d{8}$", req.customer.doc_number):
                errors.append("DNI del cliente debe tener exactamente 8 dígitos.")
            if req.customer.doc_type == "6" and not re.match(r"^\d{11}$", req.customer.doc_number):
                errors.append("RUC del cliente debe tener exactamente 11 dígitos.")

    if req.doc_type in ("07", "08"):
        if not req.related_doc_number or not req.related_doc_type or not req.note_reason_code:
            errors.append("Notas de Crédito/Débito (07/08) requieren related_doc_type, related_doc_number y note_reason_code.")

    taxable = Decimal("0.00")
    exempt = Decimal("0.00")
    unaffected = Decimal("0.00")
    igv_total = Decimal("0.00")

    for idx, item in enumerate(req.items or [], start=1):
        line_base = q2(item.quantity * item.unit_price_without_tax)
        if item.igv_affectation_code.startswith("1"):
            line_igv = q2(line_base * item.igv_rate)
            taxable += line_base
            igv_total += line_igv
        elif item.igv_affectation_code.startswith("2"):
            exempt += line_base
        else:
            unaffected += line_base
        if line_base < 0:
            errors.append(f"Ítem #{idx} tiene importe base negativo.")

    total_amount = q2(taxable + exempt + unaffected + igv_total)
    if req.items and total_amount <= Decimal("0.00"):
        errors.append("El importe total del comprobante debe ser mayor a 0.00.")

    # Regla SUNAT: Boleta > S/ 700 requiere DNI/RUC/CE (no puede ser doc_type='0')
    if req.doc_type == "03" and req.customer and req.customer.doc_type == "0":
        if req.currency == "PEN" and total_amount > Decimal("700.00"):
            errors.append("Boleta de Venta mayor a S/ 700.00 requiere identificar al cliente (DNI/RUC/CE).")

    if errors:
        raise FiscalValidationError(errors)

    return {
        "mode": "json",
        "taxable_amount": q2(taxable),
        "exempt_amount": q2(exempt),
        "unaffected_amount": q2(unaffected),
        "igv_amount": q2(igv_total),
        "total_amount": total_amount,
    }
