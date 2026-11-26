# -*- coding: utf-8 -*-
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class DocumentItemSchema(BaseModel):
    code: str = Field(default="P001", max_length=30)
    description: str = Field(..., min_length=1, max_length=250)
    unit_code: str = Field(default="NIU", max_length=10)
    quantity: Decimal = Field(..., gt=0)
    unit_price_without_tax: Decimal = Field(..., ge=0)
    igv_affectation_code: str = Field(default="10", pattern=r"^\d{2}$")  # 10=Gravado, 20=Exonerado, 30=Inafecto
    igv_rate: Decimal = Field(default=Decimal("0.18"), ge=0, le=1)


class CustomerSchema(BaseModel):
    doc_type: str = Field(..., pattern=r"^[01467A]$")  # 6=RUC, 1=DNI, 0=Sin doc, 4=CE, 7=Pasaporte
    doc_number: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=250)
    address: Optional[str] = None


class EmitDocumentRequest(BaseModel):
    """
    Acepta 2 modos de emisión:
    1) Modo JSON estructurado (para POS / apps externas): enviar items + customer.
    2) Modo XML Passthrough (para SOFIA ERP / Odoo 20): enviar raw_xml_base64 (firmado o sin firmar).
    """
    issuer_ruc: str = Field(..., pattern=r"^\d{11}$")
    doc_type: Literal["01", "03", "07", "08", "RA", "RC"]
    serie: str = Field(..., min_length=4, max_length=10)
    correlativo: str = Field(..., min_length=1, max_length=8)
    issue_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    issue_time: Optional[str] = Field(default="12:00:00", pattern=r"^\d{2}:\d{2}:\d{2}$")
    currency: Literal["PEN", "USD"] = "PEN"
    external_ref: Optional[str] = Field(default=None, max_length=120)

    # Modo JSON estructurado
    customer: Optional[CustomerSchema] = None
    items: Optional[list[DocumentItemSchema]] = None
    # Notas de crédito / débito
    related_doc_type: Optional[Literal["01", "03"]] = None
    related_doc_number: Optional[str] = None
    note_reason_code: Optional[str] = None
    note_reason_desc: Optional[str] = None

    # Modo XML Passthrough (Odoo / sistemas externos)
    raw_xml_base64: Optional[str] = None
    already_signed: bool = False
    try_sync: bool = False  # Si True, intenta un envío rápido a SUNAT antes de pasar a cola Celery
    total_amount_hint: Optional[Decimal] = None
    igv_amount_hint: Optional[Decimal] = None

    @field_validator("serie")
    @classmethod
    def uppercase_serie(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("correlativo")
    @classmethod
    def digits_correlativo(cls, v: str) -> str:
        clean = v.strip().lstrip("0") or "1"
        if not clean.isdigit():
            raise ValueError("El correlativo debe ser numérico.")
        return clean.zfill(8)


class EmitDocumentResponse(BaseModel):
    document_id: str
    status: str
    idempotent_replay: bool = False
    xml_filename: str
    digest_value: Optional[str] = None
    qr_string: Optional[str] = None
    sunat_code: Optional[str] = None
    sunat_message: Optional[str] = None
    sunat_notes: Optional[list[str]] = None
    cdr_xml_base64: Optional[str] = None
    xml_url: str
    cdr_url: str
    status_url: str


class IssuerCreateRequest(BaseModel):
    ruc: str = Field(..., pattern=r"^\d{11}$")
    business_name: str = Field(..., min_length=2, max_length=255)
    trade_name: Optional[str] = None
    address: Optional[str] = None
    ubigeo: Optional[str] = Field(default="150101", pattern=r"^\d{6}$")
    establishment_code: str = Field(default="0000", pattern=r"^\d{4}$")
    is_beta: bool = True
    is_nrus: bool = False
    dispatch_policy: Literal["INSTANT_WITH_RETRY", "SCHEDULED_NIGHT", "HYBRID_BOLETA_SUMMARY"] = "INSTANT_WITH_RETRY"
    night_window_start: int = Field(default=1, ge=0, le=23)
    night_window_end: int = Field(default=5, ge=0, le=23)
    sol_username: Optional[str] = None
    sol_password: Optional[str] = None
    pfx_base64: Optional[str] = None
    pfx_password: Optional[str] = None
    generate_demo_cert: bool = False
    tenant_local_signing: bool = False  # Modo Híbrido SOFIA ERP: el .pfx vive solo en el tenant Odoo
    gre_client_id: Optional[str] = None
    gre_client_secret: Optional[str] = None
    alert_email: Optional[str] = None


class ApiClientCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None
    allowed_rucs: Optional[list[str]] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None


class AdminLoginRequest(BaseModel):
    email: str
    password: str
