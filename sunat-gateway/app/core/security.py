# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from cryptography.fernet import Fernet

from app.core.config import get_settings

settings = get_settings()


def _derive_fernet_key(raw_key: str) -> bytes:
    """Deriva una clave Fernet válida de 32 bytes urlsafe a partir de SUNAT_VAULT_MASTER_KEY."""
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_vault() -> Fernet:
    return Fernet(_derive_fernet_key(settings.SUNAT_VAULT_MASTER_KEY))


def encrypt_secret(plaintext: Optional[str]) -> Optional[str]:
    if not plaintext:
        return None
    return get_vault().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: Optional[str]) -> Optional[str]:
    if not ciphertext:
        return None
    return get_vault().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def encrypt_bytes(data: Optional[bytes]) -> Optional[bytes]:
    if not data:
        return None
    return get_vault().encrypt(data)


def decrypt_bytes(token: Optional[bytes]) -> Optional[bytes]:
    if not token:
        return None
    return get_vault().decrypt(token)


def generate_api_key(prefix: str = "sk_live_") -> tuple[str, str, str]:
    """Genera (raw_key, key_prefix, sha256_hash). Solo raw_key se muestra una vez."""
    raw_secret = secrets.token_urlsafe(32)
    full_key = f"{prefix}{raw_secret}"
    key_prefix = full_key[:14]
    key_hash = hash_api_key(full_key)
    return full_key, key_prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def sign_webhook_payload(secret: str, payload_bytes: bytes) -> str:
    """Firma HMAC-SHA256 para header X-Sofia-Signature."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def create_admin_jwt(email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "role": "gateway_admin",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.GATEWAY_JWT_SECRET, algorithm="HS256")


def verify_admin_jwt(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.GATEWAY_JWT_SECRET, algorithms=["HS256"])
        if payload.get("role") != "gateway_admin":
            return None
        return payload
    except jwt.PyJWTError:
        return None


def create_public_download_token(doc_id: str, ttl_minutes: int = 10) -> str:
    """Genera token JWT temporal (10 min) atado exclusivamente a un doc_id para descargas públicas."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": doc_id,
        "scope": "public_doc_download",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.GATEWAY_JWT_SECRET, algorithm="HS256")


def verify_public_download_token(token: str, doc_id: str) -> bool:
    """Valida firma, vigencia y correspondencia exacta del doc_id en descargas públicas."""
    try:
        payload = jwt.decode(token, settings.GATEWAY_JWT_SECRET, algorithms=["HS256"])
        return payload.get("scope") == "public_doc_download" and hmac.compare_digest(str(payload.get("sub", "")), doc_id)
    except jwt.PyJWTError:
        return False
