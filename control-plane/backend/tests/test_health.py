"""
Pruebas de disponibilidad y endpoints raíz.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "SOFIA Platform"
    assert data["status"] == "operational"


@pytest.mark.asyncio
async def test_jwks_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/auth/.well-known/jwks.json")
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data or "status" in data
