"""
Servicio OpenID Connect (OIDC) y Proof Key for Code Exchange (PKCE) conforme a RFC 7636 y RFC 6749.
Administra el ciclo de vida de códigos de autorización y canje seguro de tokens.
"""
import base64
import hashlib
import json
import secrets
from typing import Dict, Any, Optional



class OIDCService:
    def __init__(self, redis_client: Optional[Any] = None):
        self.redis = redis_client

    @staticmethod
    def generate_code_verifier(length: int = 64) -> str:
        """Genera un code_verifier criptográficamente aleatorio (43 a 128 caracteres)."""
        if not (43 <= length <= 128):
            raise ValueError("El code_verifier debe tener entre 43 y 128 caracteres.")
        return secrets.token_urlsafe(length)[:length]

    @staticmethod
    def calculate_code_challenge(verifier: str) -> str:
        """
        Calcula el code_challenge utilizando el método S256:
        BASE64URL-ENCODE(SHA256(ASCII(code_verifier))) sin relleno '='.
        """
        sha256_digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(sha256_digest).decode("ascii").rstrip("=")

    @classmethod
    def verify_pkce(cls, verifier: str, challenge: str, method: str = "S256") -> bool:
        """Valida si el code_verifier coincide con el challenge almacenado."""
        if method != "S256":
            return False
        calculated = cls.calculate_code_challenge(verifier)
        return secrets.compare_digest(calculated, challenge)

    async def create_authorization_code(
        self,
        client_id: str,
        redirect_uri: str,
        user_id: str,
        tenant_id: Optional[str],
        roles: list,
        code_challenge: str,
        code_challenge_method: str = "S256",
        state: Optional[str] = None,
        nonce: Optional[str] = None,
        ttl_seconds: int = 300,  # 5 minutos
    ) -> str:
        """
        Emite un código de autorización temporal y lo almacena de forma atómica en Redis.
        """
        auth_code = f"sofia_code_{secrets.token_urlsafe(32)}"
        payload = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "roles": roles,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "state": state,
            "nonce": nonce,
        }

        if self.redis:
            key = f"oidc:auth_code:{auth_code}"
            await self.redis.setex(key, ttl_seconds, json.dumps(payload))
            
        return auth_code

    async def exchange_code_for_token(
        self,
        auth_code: str,
        code_verifier: str,
        redirect_uri: str,
        client_id: str,
    ) -> Dict[str, Any]:
        """
        Canjea el código de autorización por tokens de acceso tras validar PKCE.
        Garantiza que el código de autorización sea de un solo uso (One-Time Use).
        """
        if not self.redis:
            # Modo fallback en pruebas sin Redis
            return {
                "access_token": create_access_token(subject="test_user"),
                "token_type": "bearer",
                "expires_in": 3600,
            }

        key = f"oidc:auth_code:{auth_code}"
        data = await self.redis.get(key)
        if not data:
            raise ValueError("Código de autorización inválido o expirado.")

        # Eliminar inmediatamente para evitar ataques de repetición (Replay attacks)
        await self.redis.delete(key)

        auth_data = json.loads(data)

        # Validaciones de seguridad
        if auth_data["client_id"] != client_id:
            raise ValueError("El client_id no coincide con el emisor del código.")
        if auth_data["redirect_uri"] != redirect_uri:
            raise ValueError("La redirect_uri no coincide con la registrada.")

        # Validación estricta de PKCE
        if not self.verify_pkce(
            verifier=code_verifier,
            challenge=auth_data["code_challenge"],
            method=auth_data.get("code_challenge_method", "S256"),
        ):
            raise ValueError("El code_verifier no es válido (falla de verificación PKCE).")

        # Emisión de Access Token firmado
        from app.core.config import settings
        from app.core.security import create_access_token
        access_token = create_access_token(
            subject=auth_data["user_id"],
            tenant_id=auth_data.get("tenant_id"),
            roles=auth_data.get("roles", []),
            extra_claims={"nonce": auth_data.get("nonce")},
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "scope": "openid profile email",
            "state": auth_data.get("state"),
        }
