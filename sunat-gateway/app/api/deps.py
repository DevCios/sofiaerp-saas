# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_api_key, verify_admin_jwt
from app.models import ApiClient


async def get_gateway_admin(authorization: Optional[str] = Header(default=None)) -> dict:
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
    db: AsyncSession = Depends(get_db),
) -> tuple[Optional[ApiClient], Optional[dict]]:
    """Permite acceso tanto por API Key (apps/Odoo/POS) como por JWT Admin (Panel Web)."""
    raw_key = x_api_key
    if not raw_key and authorization and authorization.lower().startswith("bearer "):
        candidate = authorization.split(" ", 1)[1].strip()
        if candidate.startswith("sk_"):
            raw_key = candidate
        else:
            admin = verify_admin_jwt(candidate)
            if admin:
                return None, admin
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
