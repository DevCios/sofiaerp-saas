# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.core.security import decrypt_secret, encrypt_secret, generate_api_key, hash_api_key, sign_webhook_payload
from app.models import Issuer
from app.schemas import CustomerSchema, DocumentItemSchema, EmitDocumentRequest
from app.services.sunat_soap import classify_sunat_code
from app.services.ubl_builder import build_ubl21_xml
from app.services.validator import FiscalValidationError, validate_emit_request
from app.services.xml_signer import build_sunat_qr_string, generate_demo_pfx, inspect_pfx, sign_ubl_xml


def test_vault_roundtrip_and_api_key_hashing():
    secret = "ClaveSOL_SuperSecreta_2026!"
    enc = encrypt_secret(secret)
    assert enc != secret
    assert decrypt_secret(enc) == secret

    raw, prefix, digest = generate_api_key("sk_live_")
    assert raw.startswith("sk_live_")
    assert prefix == raw[:14]
    assert hash_api_key(raw) == digest
    assert len(sign_webhook_payload("whsec_test", b'{"ok":true}')) == 64


def test_sunat_error_classification():
    assert classify_sunat_code("0") == "ACCEPTED"
    assert classify_sunat_code("4005") == "ACCEPTED_WITH_OBS"
    assert classify_sunat_code("1033") == "RECOVER_CDR"
    assert classify_sunat_code("0130") == "RETRYABLE"
    assert classify_sunat_code("2325") == "REJECTED"
    assert classify_sunat_code("3100") == "REJECTED"


def test_ubl21_build_and_xmldsig_sign_with_demo_pfx():
    pfx_bytes, pwd, subject, expires = generate_demo_pfx("20600994345", "SOFIA ERP S.A.C.")
    inspected_sub, inspected_exp = inspect_pfx(pfx_bytes, pwd)
    assert "20600994345" in inspected_sub
    assert inspected_exp > datetime.now(timezone.utc)

    issuer = Issuer(
        ruc="20600994345",
        business_name="SOFIA ERP S.A.C.",
        trade_name="SOFIA ERP",
        address="AV. JAVIER PRADO 123",
        ubigeo="150101",
        is_beta=True,
        is_active=True,
        pfx_content_enc=b"encrypted",
        cert_is_demo=True,
        cert_expires_at=expires,
    )
    req = EmitDocumentRequest(
        issuer_ruc="20600994345",
        doc_type="01",
        serie="FE01",
        correlativo="1",
        issue_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        currency="PEN",
        customer=CustomerSchema(doc_type="6", doc_number="20100047218", name="CLIENTE DEMO S.A.C."),
        items=[
            DocumentItemSchema(
                code="SRV01",
                description="Suscripción SOFIA ERP",
                quantity=Decimal("1"),
                unit_price_without_tax=Decimal("100.00"),
                igv_affectation_code="10",
                igv_rate=Decimal("0.18"),
            )
        ],
    )
    totals = validate_emit_request(req, issuer)
    assert totals["total_amount"] == Decimal("118.00")
    assert totals["igv_amount"] == Decimal("18.00")

    xml_bytes = build_ubl21_xml(req, issuer, totals)
    signed_xml, digest_val = sign_ubl_xml(xml_bytes, pfx_bytes, pwd)
    assert b"SignatureValue" in signed_xml
    assert digest_val and len(digest_val) > 10

    qr = build_sunat_qr_string("20600994345", "01", "FE01", "00000001", 18.0, 118.0, req.issue_date, "6", "20100047218", digest_val)
    assert qr.startswith("20600994345|01|FE01|00000001|18.00|118.00|")


def test_validator_blocks_demo_cert_in_production_and_bad_series():
    issuer_prod = Issuer(
        ruc="20600994345",
        business_name="SOFIA ERP S.A.C.",
        is_beta=False,
        is_active=True,
        pfx_content_enc=b"encrypted",
        cert_is_demo=True,
        cert_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    req = EmitDocumentRequest(
        issuer_ruc="20600994345",
        doc_type="01",
        serie="BE01",  # Serie inválida para Factura
        correlativo="1",
        issue_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        customer=CustomerSchema(doc_type="1", doc_number="12345678", name="DNI en Factura"),
        items=[DocumentItemSchema(description="Test", quantity=Decimal("1"), unit_price_without_tax=Decimal("10.00"))],
    )
    with pytest.raises(FiscalValidationError) as exc_info:
        validate_emit_request(req, issuer_prod)
    joined = " ".join(exc_info.value.errors)
    assert "DEMO BETA" in joined
    assert "serie 'BE01'" in joined
    assert "RUC válido" in joined


def test_hybrid_mode_allows_already_signed_without_gateway_pfx():
    """En modo híbrido SOFIA ERP, el .pfx vive en Odoo y el Gateway acepta already_signed=True sin .pfx propio."""
    issuer_hybrid = Issuer(
        ruc="20600994345",
        business_name="SOFIA TENANT S.A.C.",
        is_beta=False,
        is_active=True,
        pfx_content_enc=None,
        cert_is_demo=False,
    )
    req = EmitDocumentRequest(
        issuer_ruc="20600994345",
        doc_type="01",
        serie="FE01",
        correlativo="15",
        issue_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        currency="PEN",
        raw_xml_base64="PFhtbC8+",
        already_signed=True,
        try_sync=True,
        total_amount_hint=Decimal("118.00"),
        igv_amount_hint=Decimal("18.00"),
    )
    totals = validate_emit_request(req, issuer_hybrid)
    assert totals["mode"] == "xml_passthrough"
    assert totals["total_amount"] == Decimal("118.00")
    assert totals["igv_amount"] == Decimal("18.00")


def test_multitenant_ruc_access_enforcement():
    from fastapi import HTTPException
    from app.api.deps import assert_ruc_access
    from app.models import ApiClient

    restricted = ApiClient(name="POS A", key_prefix="sk_live_abc", key_hash="h1", allowed_rucs=["20600994345"])
    assert_ruc_access(restricted, "20600994345")  # permitido
    with pytest.raises(HTTPException) as exc:
        assert_ruc_access(restricted, "20100047218")
    assert exc.value.status_code == 403
