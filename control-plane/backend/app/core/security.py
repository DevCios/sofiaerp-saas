"""
Módulo de Seguridad, Criptografía y Gestión de Tokens JWT para SOFIA Central.
Implementa hashing seguro de contraseñas y firma asimétrica RS256.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from passlib.context import CryptContext
from app.core.config import settings

# Contexto de hashing moderno con soporte Argon2 y bcrypt
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4,
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña plana coincide con el hash almacenado."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera un hash criptográfico Argon2id seguro para la contraseña."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    tenant_id: Optional[str] = None,
    roles: Optional[list] = None,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Genera un token JWT firmado asimétricamente para autenticación central.
    En desarrollo utiliza una firma HS256/RS256 según disponibilidad de claves.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "iss": "https://auth.sofiaerp.com",
        "sub": subject,
        "aud": "sofia-platform",
        "iat": now,
        "exp": expire,
        "nbf": now,
    }

    if tenant_id:
        payload["tenant_id"] = tenant_id
    if roles:
        payload["roles"] = roles
    if extra_claims:
        payload.update(extra_claims)

    # Por defecto emite con clave secreta si la ruta PEM no existe en local
    try:
        with open(settings.JWT_PRIVATE_KEY_PATH, "r") as f:
            private_key = f.read()
        return jwt.encode(payload, private_key, algorithm=settings.JWT_ALGORITHM)
    except (FileNotFoundError, IOError):
        # Fallback de desarrollo seguro con HMAC-SHA256
        return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> Dict[str, Any]:
    """Decodifica y valida la firma, vigencia y claims del token JWT."""
    try:
        with open(settings.JWT_PUBLIC_KEY_PATH, "r") as f:
            public_key = f.read()
        return jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
            audience="sofia-platform",
        )
    except (FileNotFoundError, IOError):
        return jwt.decode(
            token,
            settings.APP_SECRET_KEY,
            algorithms=["HS256"],
            audience="sofia-platform",
        )
