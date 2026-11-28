# -*- coding: utf-8 -*-
"""
Registro Self-Service de Workspaces / Usuarios y Planes con Mercado Pago Checkout Pro (ADR-012).
"""
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_actor_workspace_id, get_gateway_admin, is_superadmin
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_workspace_user_jwt, hash_password
from app.models import BillingOrder, GatewayUser, Issuer, Workspace, WorkspaceInvitation, WorkspaceMember

router = APIRouter(prefix="/api/v1", tags=["Workspaces & Billing"])
settings = get_settings()
_logger = logging.getLogger(__name__)

MP_PREFERENCE_API = "https://api.mercadopago.com/checkout/preferences"
MP_PAYMENT_API = "https://api.mercadopago.com/v1/payments/{payment_id}"

PLANS_CATALOG: dict[str, dict] = {
    "FREE": {
        "code": "FREE",
        "name": "Gratis",
        "monthly_quota": 50,
        "price_pen": 0.00,
        "annual_price_pen": 0.00,
        "period_label": "/ 30 días",
        "headline": "50 operaciones durante 30 días",
        "features": [
            "1 RUC en producción",
            "Facturas, boletas, notas y guías",
            "Conector MCP para IA",
            "Consultas RUC / DNI / Tipo de cambio",
        ],
        "description": "50 comprobantes/mes · API REST + Remote MCP + SUNAT Beta y Prod.",
    },
    "STARTER": {
        "code": "STARTER",
        "name": "Básico",
        "monthly_quota": 5000,
        "price_pen": 6.90,
        "annual_price_pen": 69.00,
        "period_label": "/mes",
        "headline": "5,000 operaciones al mes",
        "features": [
            "1 RUC en producción",
            "Facturas, boletas, notas y guías",
            "Conector MCP para IA (Claude / ChatGPT)",
            "Consultas RUC / DNI / TC + Webhooks",
        ],
        "description": "5,000 comprobantes/mes · 1 RUC + Webhooks HMAC + Cola anti-1033.",
    },
    "PRO": {
        "code": "PRO",
        "name": "Profesional",
        "monthly_quota": 100000,
        "price_pen": 9.90,
        "annual_price_pen": 99.00,
        "period_label": "/mes",
        "headline": "Operaciones ilimitadas",
        "features": [
            "RUCs ilimitados",
            "Facturas, boletas, notas y guías",
            "Conector MCP + OAuth 2.1 (1-clic)",
            "Webhooks HMAC + Prioridad en cola",
        ],
        "description": "Operaciones y RUCs ilimitados · OAuth 2.1 MCP + Prioridad SUNAT.",
    },
    "ENTERPRISE": {
        "code": "ENTERPRISE",
        "name": "A medida",
        "monthly_quota": 500000,
        "price_pen": 249.00,
        "annual_price_pen": 2490.00,
        "custom_contact": True,
        "period_label": "",
        "headline": "Volumen personalizado",
        "features": [
            "Varios RUC y multi-workspace",
            "Integración asistida",
            "Soporte prioritario WhatsApp",
            "SLA empresarial dedicado",
        ],
        "description": "Volumen personalizado · Integración asistida + Soporte prioritario.",
    },
}


def _slugify(text: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", (text or "workspace").lower()).strip("-")
    return (clean[:48] or "workspace") + "-" + secrets.token_hex(3)


def _get_mp_access_token() -> str:
    return (settings.MP_ACCESS_TOKEN or os.getenv("MP_ACCESS_TOKEN") or "").strip()


def _get_mp_webhook_secret() -> str:
    return (settings.MP_WEBHOOK_SECRET or os.getenv("MP_WEBHOOK_SECRET") or "").strip()


def _verify_mp_signature(request: Request, data_id: str) -> bool:
    secret = _get_mp_webhook_secret()
    if not secret:
        return True
    x_sig = request.headers.get("x-signature", "")
    x_req_id = request.headers.get("x-request-id", "")
    parts = {}
    for piece in x_sig.split(","):
        if "=" in piece:
            k, v = piece.split("=", 1)
            parts[k.strip()] = v.strip()
    ts = parts.get("ts", "")
    v1 = parts.get("v1", "")
    if not ts or not v1:
        return False
    manifest = f"id:{data_id};request-id:{x_req_id};ts:{ts};"
    expected = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


async def apply_paid_order_upgrade(db: AsyncSession, order: BillingOrder, mp_payment_id: str) -> None:
    """Aplica de forma idempotente el upgrade de plan al Workspace y a sus Issuers."""
    if order.status == "PAID":
        return
    now = datetime.now(timezone.utc)
    order.status = "PAID"
    order.mp_payment_id = mp_payment_id
    order.paid_at = now

    ws = await db.get(Workspace, order.workspace_id)
    if ws:
        ws.plan_name = order.plan_code
        ws.monthly_quota = order.quota_granted
        ws.plan_expires_at = now + timedelta(days=30)
        await db.execute(
            update(Issuer)
            .where(Issuer.workspace_id == ws.id)
            .values(plan_name=order.plan_code, monthly_quota=order.quota_granted)
        )
    await db.commit()


# ==============================================================================
# 1. Registro Self-Service & Perfil Actual
# ==============================================================================
class RegisterWorkspaceRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=160)
    workspace_name: Optional[str] = Field(default=None, max_length=160)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    invite_token: Optional[str] = Field(default=None, max_length=120)


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register_workspace(body: RegisterWorkspaceRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    if email == settings.GATEWAY_ADMIN_EMAIL.strip().lower():
        raise HTTPException(status_code=409, detail="Este correo ya está registrado.")
    existing = (await db.execute(select(GatewayUser).where(GatewayUser.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta registrada con este correo.")

    # Si viene con token de invitación válido, unirlo al Workspace invitado
    inv = None
    if body.invite_token:
        inv = (
            await db.execute(
                select(WorkspaceInvitation).where(
                    WorkspaceInvitation.token == body.invite_token.strip(),
                    WorkspaceInvitation.status == "PENDING",
                )
            )
        ).scalar_one_or_none()
        if inv and inv.expires_at < datetime.now(timezone.utc):
            inv = None

    if inv:
        ws = await db.get(Workspace, inv.workspace_id)
        ws_role = inv.role
        inv.status = "ACCEPTED"
    else:
        ws_name = (body.workspace_name or f"Workspace de {body.full_name.strip().split()[0]}").strip()
        ws = Workspace(
            name=ws_name,
            slug=_slugify(ws_name),
            plan_name="FREE",
            monthly_quota=PLANS_CATALOG["FREE"]["monthly_quota"],
        )
        db.add(ws)
        await db.flush()
        ws_role = "owner"

    user = GatewayUser(
        workspace_id=ws.id,
        email=email,
        full_name=body.full_name.strip(),
        password_hash=hash_password(body.password),
        role="workspace_owner",
    )
    db.add(user)
    await db.flush()
    db.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=ws_role))
    await db.commit()

    token = create_workspace_user_jwt(
        email=user.email,
        user_id=user.id,
        workspace_id=ws.id,
        workspace_name=ws.name,
        full_name=user.full_name,
        ws_role=ws_role,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "workspace": {
            "id": ws.id,
            "name": ws.name,
            "slug": ws.slug,
            "plan_name": ws.plan_name,
            "monthly_quota": ws.monthly_quota,
        },
    }


@router.get("/auth/me")
async def auth_me(actor: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    if is_superadmin(actor):
        return {
            "email": actor.get("sub"),
            "full_name": "Administrador Global",
            "role": "gateway_admin",
            "is_superadmin": True,
            "workspace": None,
        }
    ws_id = get_actor_workspace_id(actor)
    ws = await db.get(Workspace, ws_id) if ws_id else None
    return {
        "email": actor.get("sub"),
        "full_name": actor.get("full_name") or actor.get("sub"),
        "role": actor.get("role"),
        "is_superadmin": False,
        "workspace": {
            "id": ws.id,
            "name": ws.name,
            "slug": ws.slug,
            "source": ws.source,
            "plan_name": ws.plan_name,
            "monthly_quota": ws.monthly_quota,
            "plan_expires_at": ws.plan_expires_at.isoformat() if ws.plan_expires_at else None,
        }
        if ws
        else None,
    }


# ==============================================================================
# 1B. SSO con SOFIA Control Plane (Usuarios Internos de sofiaerp.com)
# ==============================================================================
_JWKS_CACHE: dict[str, object] = {"keys": [], "fetched_at": 0.0}


def verify_sofia_rs256_token(token: str, jwks_keys: list[dict]) -> Optional[dict]:
    """Verifica criptográficamente un JWT RS256 emitido por SOFIA Control Plane usando su JWKS."""
    if not token or not jwks_keys:
        return None
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
    except jwt.PyJWTError:
        return None

    candidates = [k for k in jwks_keys if not kid or k.get("kid") == kid] or jwks_keys
    for jwk in candidates:
        try:
            pub_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
            return jwt.decode(
                token,
                pub_key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
        except Exception:
            continue
    return None


async def _fetch_sofia_jwks(force: bool = False) -> list[dict]:
    import time

    now = time.monotonic()
    if not force and _JWKS_CACHE["keys"] and (now - float(_JWKS_CACHE["fetched_at"])) < 300:
        return list(_JWKS_CACHE["keys"])  # type: ignore[arg-type]
    base = settings.SOFIA_CONTROL_PLANE_URL.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(f"{base}/api/v1/auth/.well-known/jwks.json")
        if r.status_code == 200:
            keys = r.json().get("keys") or []
            _JWKS_CACHE["keys"] = keys
            _JWKS_CACHE["fetched_at"] = now
            return keys
    except Exception as exc:
        _logger.warning("No se pudo obtener JWKS de SOFIA Control Plane: %s", exc)
    return list(_JWKS_CACHE["keys"])  # type: ignore[arg-type]


class SofiaSSORequest(BaseModel):
    sofia_token: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    mfa_code: Optional[str] = None


@router.post("/auth/sofia-sso")
async def sofia_sso_login(body: SofiaSSORequest, db: AsyncSession = Depends(get_db)):
    """
    Permite a usuarios registrados en sofiaerp.com ingresar directamente al Gateway
    (con credenciales SOFIA ERP + MFA o mediante JWT RS256 ya emitido) con JIT Provisioning.
    """
    raw_token = (body.sofia_token or "").strip()

    if not raw_token:
        if not body.email or not body.password:
            raise HTTPException(status_code=400, detail="Envía sofia_token o correo y contraseña de SOFIA ERP.")
        base = settings.SOFIA_CONTROL_PLANE_URL.rstrip("/")
        payload_login: dict[str, object] = {"email": body.email.strip().lower(), "password": body.password}
        if body.mfa_code:
            payload_login["mfa_code"] = body.mfa_code.strip()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{base}/api/v1/auth/login", json=payload_login)
        except Exception as exc:
            _logger.error("Error conectando con SOFIA Control Plane SSO: %s", exc)
            raise HTTPException(status_code=503, detail="SOFIA Control Plane no disponible temporalmente.")
        if resp.status_code != 200:
            detail = "Credenciales de SOFIA ERP inválidas."
            try:
                detail = resp.json().get("detail") or detail
            except Exception:
                pass
            raise HTTPException(status_code=resp.status_code, detail=detail)
        raw_token = resp.json().get("access_token") or ""

    keys = await _fetch_sofia_jwks(force=False)
    claims = verify_sofia_rs256_token(raw_token, keys)
    if not claims:
        keys = await _fetch_sofia_jwks(force=True)
        claims = verify_sofia_rs256_token(raw_token, keys)
    if not claims or not claims.get("email"):
        raise HTTPException(status_code=401, detail="Token SSO de SOFIA ERP inválido o expirado.")

    email = str(claims["email"]).strip().lower()
    full_name = str(claims.get("name") or email.split("@")[0]).strip()

    # JIT Provisioning: crear o recuperar usuario + Workspace SOFIA ERP
    user = (await db.execute(select(GatewayUser).where(GatewayUser.email == email))).scalar_one_or_none()
    if user:
        ws = await db.get(Workspace, user.workspace_id)
        if not ws or not ws.is_active or not user.is_active:
            raise HTTPException(status_code=403, detail="Cuenta o Workspace inactivo.")
    else:
        ws_name = f"SOFIA ERP — {full_name}"
        ws = Workspace(
            name=ws_name[:160],
            slug=_slugify(ws_name),
            source="sofia_erp",
            plan_name="SOFIA_ERP",
            monthly_quota=2000,
        )
        db.add(ws)
        await db.flush()
        user = GatewayUser(
            workspace_id=ws.id,
            email=email,
            full_name=full_name[:160],
            password_hash=hash_password(secrets.token_urlsafe(32)),
            auth_provider="sofia_sso",
            role="workspace_owner",
        )
        db.add(user)
        await db.flush()
        db.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role="owner"))
        await db.commit()

    token = create_workspace_user_jwt(
        email=user.email,
        user_id=user.id,
        workspace_id=ws.id,
        workspace_name=ws.name,
        full_name=user.full_name,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "auth_provider": "sofia_sso",
        "workspace": {
            "id": ws.id,
            "name": ws.name,
            "slug": ws.slug,
            "source": ws.source,
            "plan_name": ws.plan_name,
            "monthly_quota": ws.monthly_quota,
        },
    }


# ==============================================================================
# 1C. Gestión Multi-Workspace (Listar, Crear y Cambiar de Workspace)
# ==============================================================================
class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)


async def _ensure_user_memberships(db: AsyncSession, user_id: str) -> list[Workspace]:
    """Retorna todos los workspaces activos del usuario (haciendo backfill de su workspace principal si faltara)."""
    user = await db.get(GatewayUser, user_id)
    if not user:
        return []
    mem_rows = (
        await db.execute(select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id))
    ).scalars().all()
    ws_ids = list(mem_rows)
    if user.workspace_id and user.workspace_id not in ws_ids:
        db.add(WorkspaceMember(user_id=user.id, workspace_id=user.workspace_id, role="owner"))
        await db.commit()
        ws_ids.append(user.workspace_id)
    if not ws_ids:
        return []
    res = await db.execute(
        select(Workspace)
        .where(Workspace.id.in_(ws_ids), Workspace.is_active.is_(True))
        .order_by(Workspace.created_at.asc())
    )
    return list(res.scalars().all())


@router.get("/workspaces")
async def list_my_workspaces(actor: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    current_ws_id = get_actor_workspace_id(actor)
    if is_superadmin(actor):
        res = await db.execute(select(Workspace).where(Workspace.is_active.is_(True)).order_by(desc(Workspace.created_at)).limit(100))
        workspaces = list(res.scalars().all())
    else:
        uid = actor.get("uid")
        workspaces = await _ensure_user_memberships(db, uid) if uid else []
    return [
        {
            "id": w.id,
            "name": w.name,
            "slug": w.slug,
            "source": w.source,
            "plan_name": w.plan_name,
            "monthly_quota": w.monthly_quota,
            "is_current": (w.id == current_ws_id),
            "created_at": w.created_at.isoformat(),
        }
        for w in workspaces
    ]


@router.post("/workspaces", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceCreateRequest,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    ws_name = body.name.strip()
    ws = Workspace(
        name=ws_name,
        slug=_slugify(ws_name),
        source="external",
        plan_name="FREE",
        monthly_quota=PLANS_CATALOG["FREE"]["monthly_quota"],
    )
    db.add(ws)
    await db.flush()

    new_token = None
    if not is_superadmin(actor):
        uid = actor.get("uid")
        user = await db.get(GatewayUser, uid) if uid else None
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado.")
        db.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role="owner"))
        user.workspace_id = ws.id
        new_token = create_workspace_user_jwt(
            email=user.email,
            user_id=user.id,
            workspace_id=ws.id,
            workspace_name=ws.name,
            full_name=user.full_name,
        )
    await db.commit()
    return {
        "workspace": {
            "id": ws.id,
            "name": ws.name,
            "slug": ws.slug,
            "plan_name": ws.plan_name,
            "monthly_quota": ws.monthly_quota,
        },
        "access_token": new_token,
    }


@router.post("/workspaces/{workspace_id}/switch")
async def switch_workspace(
    workspace_id: str,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    ws = await db.get(Workspace, workspace_id)
    if not ws or not ws.is_active:
        raise HTTPException(status_code=404, detail="Workspace no encontrado.")

    if is_superadmin(actor):
        # Superadmin puede inspeccionar cualquier Workspace generando un JWT acotado a ese Workspace
        token = create_workspace_user_jwt(
            email=actor.get("sub") or settings.GATEWAY_ADMIN_EMAIL,
            user_id="superadmin",
            workspace_id=ws.id,
            workspace_name=ws.name,
            full_name="Admin",
        )
        return {"access_token": token, "workspace": {"id": ws.id, "name": ws.name, "slug": ws.slug, "plan_name": ws.plan_name}}

    uid = actor.get("uid")
    user = await db.get(GatewayUser, uid) if uid else None
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado.")

    workspaces = await _ensure_user_memberships(db, user.id)
    if not any(w.id == ws.id for w in workspaces):
        raise HTTPException(status_code=403, detail="No perteneces a este Workspace.")

    user.workspace_id = ws.id
    await db.commit()
    mem = (
        await db.execute(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user.id, WorkspaceMember.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    ws_role = mem.role if mem else "owner"
    token = create_workspace_user_jwt(
        email=user.email,
        user_id=user.id,
        workspace_id=ws.id,
        workspace_name=ws.name,
        full_name=user.full_name,
        ws_role=ws_role,
    )
    return {"access_token": token, "workspace": {"id": ws.id, "name": ws.name, "slug": ws.slug, "plan_name": ws.plan_name}}


# ==============================================================================
# 1D. Gestión de Equipo e Invitaciones por Workspace (Propietario / Admin / Miembro)
# ==============================================================================
def _assert_can_manage_workspace(actor: dict) -> None:
    if is_superadmin(actor):
        return
    if (actor.get("ws_role") or "owner") not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un Propietario o Administrador puede gestionar facturación o equipo.",
        )


@router.get("/workspaces/team")
async def get_workspace_team(actor: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    ws_id = get_actor_workspace_id(actor)
    if not ws_id:
        return {
            "workspace_id": None,
            "my_role": "owner",
            "can_manage": True,
            "members": [
                {
                    "id": "superadmin",
                    "full_name": "Administrador Global",
                    "email": actor.get("sub") or settings.GATEWAY_ADMIN_EMAIL,
                    "role": "owner",
                    "is_me": True,
                    "joined_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
            "invitations": [],
        }

    uid = actor.get("uid")
    if uid:
        await _ensure_user_memberships(db, uid)

    mem_rows = (
        await db.execute(
            select(WorkspaceMember, GatewayUser)
            .join(GatewayUser, WorkspaceMember.user_id == GatewayUser.id)
            .where(WorkspaceMember.workspace_id == ws_id, GatewayUser.is_active.is_(True))
            .order_by(WorkspaceMember.created_at.asc())
        )
    ).all()

    inv_rows = (
        await db.execute(
            select(WorkspaceInvitation)
            .where(WorkspaceInvitation.workspace_id == ws_id, WorkspaceInvitation.status == "PENDING")
            .order_by(desc(WorkspaceInvitation.created_at))
        )
    ).scalars().all()

    base = settings.PUBLIC_BASE_URL.rstrip("/")
    my_role = actor.get("ws_role") or "owner"
    return {
        "workspace_id": ws_id,
        "my_role": my_role,
        "can_manage": my_role in ("owner", "admin"),
        "members": [
            {
                "id": m.id,
                "user_id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "role": m.role,
                "is_me": (u.id == uid),
                "joined_at": m.created_at.isoformat(),
            }
            for m, u in mem_rows
        ],
        "invitations": [
            {
                "id": inv.id,
                "email": inv.email,
                "role": inv.role,
                "status": inv.status,
                "invite_url": f"{base}/?invite={inv.token}",
                "expires_at": inv.expires_at.isoformat(),
                "created_at": inv.created_at.isoformat(),
            }
            for inv in inv_rows
        ],
    }


class InviteMemberRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    role: str = Field(default="member", pattern="^(member|admin)$")


@router.post("/workspaces/team/invite", status_code=status.HTTP_201_CREATED)
async def invite_workspace_member(
    body: InviteMemberRequest,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    _assert_can_manage_workspace(actor)
    ws_id = get_actor_workspace_id(actor)
    if not ws_id:
        raise HTTPException(
            status_code=400,
            detail="Selecciona o crea un Workspace primero desde el selector superior para invitar miembros.",
        )
    email = body.email.strip().lower()
    # Si el usuario ya tiene cuenta, verificar si ya es miembro
    existing_user = (await db.execute(select(GatewayUser).where(GatewayUser.email == email))).scalar_one_or_none()
    if existing_user:
        already = (
            await db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.user_id == existing_user.id,
                    WorkspaceMember.workspace_id == ws_id,
                )
            )
        ).scalar_one_or_none()
        if already:
            raise HTTPException(status_code=409, detail="Este correo ya es miembro del workspace.")

    token = secrets.token_urlsafe(24)
    inv = WorkspaceInvitation(
        workspace_id=ws_id,
        email=email,
        role=body.role,
        token=token,
        invited_by=actor.get("sub") or "admin",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(inv)
    await db.commit()
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return {
        "id": inv.id,
        "email": inv.email,
        "role": inv.role,
        "invite_url": f"{base}/?invite={inv.token}",
    }


@router.post("/workspaces/invitations/{token}/accept")
async def accept_workspace_invitation(
    token: str,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    inv = (
        await db.execute(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.token == token.strip(),
                WorkspaceInvitation.status == "PENDING",
            )
        )
    ).scalar_one_or_none()
    if not inv or inv.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=404, detail="Invitación inválida o expirada.")

    uid = actor.get("uid")
    user = await db.get(GatewayUser, uid) if uid else None
    if not user:
        raise HTTPException(status_code=400, detail="Inicia sesión con una cuenta de usuario para aceptar la invitación.")

    exists = (
        await db.execute(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user.id, WorkspaceMember.workspace_id == inv.workspace_id)
        )
    ).scalar_one_or_none()
    if not exists:
        db.add(WorkspaceMember(user_id=user.id, workspace_id=inv.workspace_id, role=inv.role))
    inv.status = "ACCEPTED"
    user.workspace_id = inv.workspace_id
    ws = await db.get(Workspace, inv.workspace_id)
    await db.commit()

    new_token = create_workspace_user_jwt(
        email=user.email,
        user_id=user.id,
        workspace_id=ws.id,
        workspace_name=ws.name,
        full_name=user.full_name,
        ws_role=inv.role,
    )
    return {"access_token": new_token, "workspace": {"id": ws.id, "name": ws.name}}


@router.delete("/workspaces/team/members/{member_id}")
async def remove_workspace_member(
    member_id: str,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    _assert_can_manage_workspace(actor)
    ws_id = get_actor_workspace_id(actor)
    mem = await db.get(WorkspaceMember, member_id)
    if not mem or (ws_id and mem.workspace_id != ws_id):
        raise HTTPException(status_code=404, detail="Miembro no encontrado.")
    if mem.role == "owner":
        raise HTTPException(status_code=400, detail="No puedes eliminar al Propietario del workspace.")
    await db.delete(mem)
    await db.commit()
    return {"removed": True}


@router.delete("/workspaces/team/invitations/{inv_id}")
async def revoke_workspace_invitation(
    inv_id: str,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    _assert_can_manage_workspace(actor)
    ws_id = get_actor_workspace_id(actor)
    inv = await db.get(WorkspaceInvitation, inv_id)
    if not inv or (ws_id and inv.workspace_id != ws_id):
        raise HTTPException(status_code=404, detail="Invitación no encontrada.")
    inv.status = "REVOKED"
    await db.commit()
    return {"revoked": True}


# ==============================================================================
# 2. Catálogo de Planes y Checkout Mercado Pago
# ==============================================================================
@router.get("/billing/plans")
async def get_billing_plans(actor: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    ws_id = get_actor_workspace_id(actor)
    ws = await db.get(Workspace, ws_id) if ws_id else None
    return {
        "mp_configured": bool(_get_mp_access_token()),
        "current_plan": ws.plan_name if ws else "GLOBAL",
        "current_quota": ws.monthly_quota if ws else None,
        "plans": list(PLANS_CATALOG.values()),
    }


@router.get("/billing/orders")
async def list_billing_orders(actor: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    ws_id = get_actor_workspace_id(actor)
    stmt = select(BillingOrder).order_by(desc(BillingOrder.created_at)).limit(50)
    if ws_id:
        stmt = stmt.where(BillingOrder.workspace_id == ws_id)
    res = await db.execute(stmt)
    return [
        {
            "id": o.id,
            "workspace_id": o.workspace_id,
            "plan_code": o.plan_code,
            "quota_granted": o.quota_granted,
            "amount_pen": float(o.amount_pen),
            "status": o.status,
            "mp_payment_id": o.mp_payment_id,
            "paid_at": o.paid_at.isoformat() if o.paid_at else None,
            "created_at": o.created_at.isoformat(),
        }
        for o in res.scalars().all()
    ]


class BillingProfileRequest(BaseModel):
    doc_type_receipt: str = Field(default="01", pattern="^(01|03)$")  # 01=Factura, 03=Boleta
    identity_type: str = Field(default="6", pattern="^(6|1)$")        # 6=RUC, 1=DNI
    identity_number: str = Field(default="", max_length=15)
    business_name: str = Field(..., min_length=2, max_length=200)
    address: str = Field(default="", max_length=250)
    address2: str = Field(default="", max_length=150)
    city: str = Field(default="", max_length=100)
    department: str = Field(default="", max_length=100)
    postal_code: str = Field(default="", max_length=20)
    billing_email: str = Field(default="", max_length=200)


@router.get("/billing/profile")
async def get_billing_profile(actor: dict = Depends(get_gateway_admin), db: AsyncSession = Depends(get_db)):
    ws_id = get_actor_workspace_id(actor)
    ws = await db.get(Workspace, ws_id) if ws_id else None
    profile = (ws.billing_profile if ws and ws.billing_profile else {})
    return {
        "workspace_id": ws_id,
        "doc_type_receipt": profile.get("doc_type_receipt", "01"),
        "identity_type": profile.get("identity_type", "6"),
        "identity_number": profile.get("identity_number", ""),
        "business_name": profile.get("business_name", ws.name if ws else ""),
        "address": profile.get("address", ""),
        "address2": profile.get("address2", ""),
        "city": profile.get("city", ""),
        "department": profile.get("department", ""),
        "postal_code": profile.get("postal_code", ""),
        "billing_email": profile.get("billing_email", actor.get("sub") or ""),
    }


@router.put("/billing/profile")
async def save_billing_profile(
    body: BillingProfileRequest,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    _assert_can_manage_workspace(actor)
    ws_id = get_actor_workspace_id(actor)
    if not ws_id:
        raise HTTPException(
            status_code=400,
            detail="Selecciona o crea un Workspace primero desde el selector superior para guardar datos de facturación.",
        )
    ws = await db.get(Workspace, ws_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace no encontrado.")
    ws.billing_profile = body.model_dump()
    await db.commit()
    return {"saved": True, "profile": ws.billing_profile}


class BillingCheckoutRequest(BaseModel):
    plan_code: str = Field(..., pattern="^(STARTER|PRO|ENTERPRISE)$")
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")


@router.post("/billing/checkout")
async def create_billing_checkout(
    body: BillingCheckoutRequest,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    _assert_can_manage_workspace(actor)
    ws_id = get_actor_workspace_id(actor)
    if not ws_id:
        raise HTTPException(
            status_code=400,
            detail="El Superadmin Global no requiere suscripción. Crea o selecciona un Workspace para probar pagos.",
        )
    ws = await db.get(Workspace, ws_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace no encontrado.")

    plan = PLANS_CATALOG[body.plan_code]
    is_annual = body.billing_cycle == "yearly"
    amount = float(plan.get("annual_price_pen") if is_annual else plan["price_pen"])
    cycle_label = "Anual (2 meses gratis)" if is_annual else "Mensual"

    access_token = _get_mp_access_token()
    if not access_token:
        raise HTTPException(
            status_code=503,
            detail="Mercado Pago no está configurado aún en el servidor (falta MP_ACCESS_TOKEN en .env).",
        )

    order = BillingOrder(
        workspace_id=ws.id,
        plan_code=plan["code"],
        quota_granted=plan["monthly_quota"],
        amount_pen=amount,
        status="PENDING",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    base = settings.PUBLIC_BASE_URL.rstrip("/")
    payer_email = (ws.billing_profile or {}).get("billing_email") or actor.get("sub") or "cliente@apisunat.pro"
    preference = {
        "items": [
            {
                "id": f"{plan['code']}_{body.billing_cycle}",
                "title": f"{settings.APP_NAME} — Plan {plan['name']} {cycle_label}",
                "quantity": 1,
                "currency_id": "PEN",
                "unit_price": amount,
            }
        ],
        "external_reference": f"GW-PLAN-{order.id}",
        "payer": {"email": payer_email},
        "back_urls": {
            "success": f"{base}/api/v1/billing/mp-callback?order_id={order.id}",
            "pending": f"{base}/api/v1/billing/mp-callback?order_id={order.id}",
            "failure": f"{base}/?billing=failure",
        },
        "auto_return": "approved",
        "notification_url": f"{base}/api/v1/billing/mp-webhook",
        "statement_descriptor": "API SUNAT",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            MP_PREFERENCE_API,
            json=preference,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        )
    if resp.status_code not in (200, 201):
        _logger.error("Gateway MP checkout error (%s): %s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail="No se pudo generar el enlace de pago con Mercado Pago.")

    pdata = resp.json()
    order.mp_preference_id = pdata.get("id")
    await db.commit()

    return {
        "order_id": order.id,
        "plan_code": plan["code"],
        "amount_pen": plan["price_pen"],
        "checkout_url": pdata.get("init_point") or pdata.get("sandbox_init_point"),
    }


async def _verify_mp_payment_and_apply(db: AsyncSession, order: BillingOrder, payment_id: str) -> bool:
    access_token = _get_mp_access_token()
    if not access_token or not payment_id:
        return False
    # Idempotencia por payment_id
    dup = (await db.execute(select(BillingOrder).where(BillingOrder.mp_payment_id == payment_id))).scalar_one_or_none()
    if dup:
        return True
    async with httpx.AsyncClient(timeout=12.0) as client:
        r = await client.get(
            MP_PAYMENT_API.format(payment_id=payment_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if r.status_code != 200:
        return False
    pdata = r.json()
    paid = float(pdata.get("transaction_amount") or 0.0)
    if pdata.get("status") == "approved" and paid + 0.05 >= float(order.amount_pen):
        await apply_paid_order_upgrade(db, order, payment_id)
        return True
    return False


@router.get("/billing/mp-callback")
async def billing_mp_callback(
    order_id: str,
    payment_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    pid = (payment_id or collection_id or "").strip()
    order = await db.get(BillingOrder, order_id)
    if order and pid:
        ok = await _verify_mp_payment_and_apply(db, order, pid)
        if ok:
            return RedirectResponse(url="/?billing=success", status_code=302)
    return RedirectResponse(url="/?billing=pending", status_code=302)


@router.post("/billing/mp-webhook")
async def billing_mp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        body = {}
    payment_id = str((body.get("data") or {}).get("id") or request.query_params.get("data.id") or "").strip()
    if not payment_id:
        return {"ok": True}
    if not _verify_mp_signature(request, payment_id):
        raise HTTPException(status_code=403, detail="Firma HMAC inválida.")

    access_token = _get_mp_access_token()
    if not access_token:
        return {"ok": True}
    async with httpx.AsyncClient(timeout=12.0) as client:
        r = await client.get(
            MP_PAYMENT_API.format(payment_id=payment_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if r.status_code == 200:
        pdata = r.json()
        ext_ref = pdata.get("external_reference") or ""
        if ext_ref.startswith("GW-PLAN-") and pdata.get("status") == "approved":
            oid = ext_ref.replace("GW-PLAN-", "", 1)
            order = await db.get(BillingOrder, oid)
            if order:
                await _verify_mp_payment_and_apply(db, order, payment_id)
    return {"ok": True}
