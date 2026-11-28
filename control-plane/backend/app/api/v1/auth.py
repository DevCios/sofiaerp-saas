"""
Endpoints de Identidad, Autenticación Central, MFA y OIDC con PKCE.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from app.core.database import get_db_session
from app.core.security import verify_password, create_access_token, decode_token
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User, UserTenantMembership
from app.models.tenant import Tenant
from app.schemas.user import UserLogin, Token
from app.services.mfa_service import MFAService
from app.services.oidc_service import OIDCService

router = APIRouter(prefix="/auth", tags=["Identidad & Autenticación (OIDC & MFA)"])


# ------------------------------------------------------------------------------
# Esquemas Pydantic específicos para MFA y PKCE
# ------------------------------------------------------------------------------
class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    recovery_codes: List[str]


class MFAEnableRequest(BaseModel):
    user_id: str
    secret: str
    code: str
    recovery_code_hashes: List[str]


class AuthorizeRequest(BaseModel):
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str = "S256"
    state: Optional[str] = None
    nonce: Optional[str] = None
    tenant_slug: Optional[str] = None
    email: EmailStr
    password: str
    mfa_code: Optional[str] = None


class TokenExchangeRequest(BaseModel):
    grant_type: str = "authorization_code"
    client_id: str
    code: str
    redirect_uri: str
    code_verifier: str


# ------------------------------------------------------------------------------
# Endpoints de Login y JWKS
# ------------------------------------------------------------------------------
@router.post("/login", response_model=Token, summary="Inicio de sesión centralizado con soporte MFA")
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db_session)):
    stmt = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de acceso inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")

    # Verificación de MFA si está activado
    if user.mfa_enabled:
        if not credentials.mfa_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="MFA_REQUIRED: Ingrese el código de su aplicación autenticadora.",
            )
        if not MFAService.verify_totp_code(user.mfa_secret, credentials.mfa_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Código MFA inválido o expirado.",
            )

    tenant_id = None
    roles = []
    if credentials.tenant_slug:
        t_res = await db.execute(select(Tenant).where(Tenant.slug == credentials.tenant_slug))
        tenant = t_res.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant no encontrado.")
        
        mem_res = await db.execute(
            select(UserTenantMembership).where(
                UserTenantMembership.user_id == user.id,
                UserTenantMembership.tenant_id == tenant.id,
                UserTenantMembership.is_enabled == True,
            )
        )
        membership = mem_res.scalar_one_or_none()
        if not membership and not user.is_superadmin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado en este tenant.")
        tenant_id = str(tenant.id)
        if membership:
            roles.append(membership.role)

    token = create_access_token(
        subject=str(user.id),
        tenant_id=tenant_id,
        roles=roles,
        extra_claims={"email": user.email, "name": user.full_name},
    )

    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        tenant_id=tenant_id,
        roles=roles,
    )


# ------------------------------------------------------------------------------
# Endpoints de Multi-Factor Authentication (MFA)
# ------------------------------------------------------------------------------
@router.post("/mfa/setup", response_model=MFASetupResponse, summary="Generar configuración de MFA")
async def mfa_setup(
    user_email: EmailStr,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.email != user_email and not current_user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para configurar MFA de otro usuario.")

    stmt = select(User).where(User.email == user_email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    secret = MFAService.generate_totp_secret()
    provisioning_uri = MFAService.get_provisioning_uri(secret, user.email)
    plain_codes, hashed_codes = MFAService.generate_recovery_codes()

    return MFASetupResponse(
        secret=secret,
        provisioning_uri=provisioning_uri,
        recovery_codes=plain_codes,
    )


@router.post("/mfa/enable", summary="Confirmar y activar MFA en la cuenta del usuario")
async def mfa_enable(
    payload: MFAEnableRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    if str(current_user.id) != str(payload.user_id) and not current_user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para activar MFA en otra cuenta.")

    # Validar que el código suministrado corresponda al secreto
    if not MFAService.verify_totp_code(payload.secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código suministrado no es válido. Verifique la hora de su dispositivo.",
        )

    stmt = select(User).where(User.id == payload.user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    user.mfa_enabled = True
    user.mfa_secret = payload.secret
    await db.commit()

    return {"status": "SUCCESS", "message": "Autenticación Multifactor activada exitosamente."}


# ------------------------------------------------------------------------------
# Endpoints OIDC con PKCE
# ------------------------------------------------------------------------------
@router.post("/oauth/authorize", summary="Solicitar código de autorización OIDC con PKCE")
async def oauth_authorize(payload: AuthorizeRequest, db: AsyncSession = Depends(get_db_session)):
    """
    Valida las credenciales del usuario y emite un authorization code vinculado al code_challenge (S256).
    """
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas.")

    if user.mfa_enabled:
        if not payload.mfa_code or not MFAService.verify_totp_code(user.mfa_secret, payload.mfa_code):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código MFA requerido o incorrecto.")

    tenant_id = None
    roles = []
    if payload.tenant_slug:
        t_res = await db.execute(select(Tenant).where(Tenant.slug == payload.tenant_slug))
        tenant = t_res.scalar_one_or_none()
        if tenant:
            tenant_id = str(tenant.id)

    oidc = OIDCService(redis_client=None)  # En producción inyecta el cliente Redis
    auth_code = await oidc.create_authorization_code(
        client_id=payload.client_id,
        redirect_uri=payload.redirect_uri,
        user_id=str(user.id),
        tenant_id=tenant_id,
        roles=roles,
        code_challenge=payload.code_challenge,
        code_challenge_method=payload.code_challenge_method,
        state=payload.state,
        nonce=payload.nonce,
    )

    return {
        "code": auth_code,
        "state": payload.state,
        "redirect_uri": f"{payload.redirect_uri}?code={auth_code}&state={payload.state or ''}",
    }


@router.post("/oauth/token", summary="Canjear código de autorización y code_verifier por Access Token")
async def oauth_token(payload: TokenExchangeRequest):
    """
    Valida el code_verifier contra el code_challenge previo y emite el token JWT asimétrico.
    """
    if payload.grant_type != "authorization_code":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grant type no soportado.")

    oidc = OIDCService(redis_client=None)
    try:
        tokens = await oidc.exchange_code_for_token(
            auth_code=payload.code,
            code_verifier=payload.code_verifier,
            redirect_uri=payload.redirect_uri,
            client_id=payload.client_id,
        )
        return tokens
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/.well-known/jwks.json", summary="Claves públicas JWKS (RFC 7517) para validación offline")
async def get_jwks():
    import json
    import jwt as pyjwt
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    try:
        with open(settings.JWT_PUBLIC_KEY_PATH, "rb") as f:
            pub_pem_bytes = f.read()
        pub_key_obj = load_pem_public_key(pub_pem_bytes)
        jwk_dict = json.loads(pyjwt.algorithms.RSAAlgorithm.to_jwk(pub_key_obj))
        jwk_dict.update(
            {
                "use": "sig",
                "alg": settings.JWT_ALGORITHM,
                "kid": "sofia-auth-key-1",
                "public_key": pub_pem_bytes.decode("utf-8"),
            }
        )
        return {"keys": [jwk_dict]}
    except (FileNotFoundError, IOError):
        return {
            "status": "development_mode",
            "message": "Claves asimétricas no configuradas en ruta local. Usando fallback de desarrollo.",
        }
