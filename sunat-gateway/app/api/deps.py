# -*- coding: utf-8 -*-
import hmac
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_api_key, verify_admin_jwt, verify_mcp_oauth_jwt
from app.models import ApiClient

settings = get_settings()


def _is_valid_internal_key(x_internal_service_key: Optional[str]) -> bool:
    if not x_internal_service_key or not settings.INTERNAL_SERVICE_KEY:
        return False
    return hmac.compare_digest(x_internal_service_key.strip(), settings.INTERNAL_SERVICE_KEY)


async def get_gateway_admin(
    authorization: Optional[str] = Header(default=None),
    x_internal_service_key: Optional[str] = Header(default=None),
) -> dict:
    if _is_valid_internal_key(x_internal_service_key):
        return {"sub": "sofia-erp-internal", "role": "gateway_admin", "internal": True}
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de administrador requerido.")
    token = authorization.split(" ", 1)[1].strip()
    payload = verify_admin_jwt(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado.")
    return payload


async def get_api_client_or_admin(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
    x_internal_service_key: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> tuple[Optional[ApiClient], Optional[dict]]:
    """Permite acceso por Mesh Interno (SOFIA ERP), API Key (apps/POS) o JWT Admin (Panel Web)."""
    if _is_valid_internal_key(x_internal_service_key):
        return None, {"sub": "sofia-erp-internal", "role": "gateway_admin", "internal": True}

    raw_key = x_api_key
    if not raw_key and authorization and authorization.lower().startswith("bearer "):
        candidate = authorization.split(" ", 1)[1].strip()
        if candidate.startswith("sk_"):
            raw_key = candidate
        else:
            admin = verify_admin_jwt(candidate)
            if admin:
                return None, admin
            oauth_payload = verify_mcp_oauth_jwt(candidate)
            if oauth_payload:
                # Cliente virtual OAuth 2.1 con aislamiento estricto de allowed_rucs
                virtual_client = ApiClient(
                    id=None,
                    name=f"OAuth MCP ({oauth_payload.get('sub', 'ai')})",
                    key_prefix="oauth_mcp",
                    key_hash="",
                    is_active=True,
                    allowed_rucs=oauth_payload.get("allowed_rucs"),
                )
                return virtual_client, oauth_payload
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT inválido o expirado.")

    if not raw_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key o Token requerido.")

    key_hash = hash_api_key(raw_key)
    res = await db.execute(select(ApiClient).where(ApiClient.key_hash == key_hash, ApiClient.is_active.is_(True)))
    client = res.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key inválida o revocada.")

    client.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return client, None


def assert_ruc_access(api_client: Optional[ApiClient], ruc: str) -> None:
    """Garantiza aislamiento multi-tenant: una API Key solo accede a sus allowed_rucs."""
    if api_client and api_client.allowed_rucs and ruc not in api_client.allowed_rucs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Esta API Key no tiene permiso para acceder al RUC {ruc}.",
        )
