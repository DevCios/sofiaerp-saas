"""
Pruebas Unitarias para el Control de Sesiones y Concurrencia.
"""
import pytest
from app.services.session_service import SessionService, ConcurrencyLimitExceededException


@pytest.mark.asyncio
async def test_session_registration_mock_fallback():
    service = SessionService(redis_client=None)
    result = await service.register_session(
        session_id="sess_123",
        user_id="user_456",
        tenant_id="tenant_789",
        max_concurrent_sessions=5,
    )
    assert result["allowed"] is True
    assert result["session_id"] == "sess_123"
