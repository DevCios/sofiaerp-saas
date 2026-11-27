# -*- coding: utf-8 -*-
import pytest

from app.api.mcp_server import (
    MCP_PROTOCOL_VERSION,
    MCP_TOOLS,
    calculate_totals_data,
    explain_sunat_code_data,
    mcp_discovery,
    openapi_ai_schema,
)


def test_calculate_totals_igv_mixed_affectations():
    result = calculate_totals_data(
        [
            {"description": "Servicio gravado", "quantity": 2, "unit_price_without_tax": 100, "igv_affectation_code": "10", "igv_rate": 0.18},
            {"description": "Producto exonerado", "quantity": 1, "unit_price_without_tax": 50, "igv_affectation_code": "20"},
            {"description": "Concepto inafecto", "quantity": 1, "unit_price_without_tax": 25, "igv_affectation_code": "30"},
        ],
        currency="PEN",
    )
    assert result["currency"] == "PEN"
    assert result["taxable_amount"] == 200.0
    assert result["exonerated_amount"] == 50.0
    assert result["unaffected_amount"] == 25.0
    assert result["igv_amount"] == 36.0
    assert result["total_amount"] == 311.0
    assert len(result["items"]) == 3


def test_explain_sunat_error_known_and_classified_codes():
    r1033 = explain_sunat_code_data("1033")
    assert r1033["classification"] == "RECOVER_CDR"
    assert "getStatusCdr" in r1033["recommended_action"]

    r2017 = explain_sunat_code_data("2017")
    assert r2017["classification"] == "REJECTED"

    r4005 = explain_sunat_code_data("4005")
    assert r4005["classification"] == "ACCEPTED_WITH_OBS"

    r0 = explain_sunat_code_data("0")
    assert r0["classification"] == "ACCEPTED"


@pytest.mark.asyncio
async def test_mcp_discovery_and_openapi_ai_schema():
    disc = await mcp_discovery()
    assert disc["protocolVersion"] == MCP_PROTOCOL_VERSION
    assert disc["transport"] == "streamable-http"
    assert disc["tools_count"] == len(MCP_TOOLS)

    tool_names = {t["name"] for t in MCP_TOOLS}
    assert {"calculate_totals_igv", "explain_sunat_error", "list_issuers", "list_documents", "lookup_document", "emit_document"} <= tool_names

    spec = await openapi_ai_schema()
    assert spec["openapi"] == "3.1.0"
    assert "/api/v1/documents/emit" in spec["paths"]
    assert "/api/v1/ai/calculate-totals" in spec["paths"]
    assert "BearerAuth" in spec["components"]["securitySchemes"]
