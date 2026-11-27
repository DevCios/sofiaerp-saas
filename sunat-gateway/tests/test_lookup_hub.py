# -*- coding: utf-8 -*-
import pytest

from app.api.mcp_server import MCP_TOOLS, openapi_ai_schema
from app.services.lookup_service import today_lima_str, validate_peru_dni, validate_peru_ruc


def test_peru_ruc_and_dni_algorithmic_validation():
    # RUCs reales válidos (módulo 11 SUNAT)
    assert validate_peru_ruc("20100047218") is True   # BCP
    assert validate_peru_ruc("20131312955") is True   # SUNAT
    # RUCs inválidos (dígito verificador incorrecto / longitud / prefijo)
    assert validate_peru_ruc("20100047219") is False
    assert validate_peru_ruc("99100047218") is False
    assert validate_peru_ruc("1234567") is False

    # DNIs
    assert validate_peru_dni("72345678") is True
    assert validate_peru_dni("1234567") is False
    assert validate_peru_dni("1234567A") is False

    today = today_lima_str()
    assert len(today) == 10 and today[4] == "-" and today[7] == "-"


@pytest.mark.asyncio
async def test_lookup_tools_registered_in_mcp_and_openapi():
    names = {t["name"] for t in MCP_TOOLS}
    assert {"lookup_ruc", "lookup_dni", "get_exchange_rate"} <= names

    spec = await openapi_ai_schema()
    assert "/api/v1/lookup/ruc/{ruc}" in spec["paths"]
    assert "/api/v1/lookup/dni/{dni}" in spec["paths"]
    assert "/api/v1/lookup/exchange-rate" in spec["paths"]
