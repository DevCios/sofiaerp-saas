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
from app.models import BillingOrder, GatewayUser, Issuer, Workspace

router = APIRouter(prefix="/api/v1", tags=["Workspaces & Billing"])
settings = get_settings()
_logger = logging.getLogger(__name__)

MP_PREFERENCE_API = "https://api.mercadopago.com/checkout/preferences"
MP_PAYMENT_API = "https://api.mercadopago.com/v1/payments/{payment_id}"

PLANS_CATALOG: dict[str, dict] = {
    "FREE": {
        "code": "FREE",
        "name": "Gratis (Sandbox / Inicio)",
        "monthly_quota": 50,
        "price_pen": 0.00,
        "description": "50 comprobantes/mes · API REST + Remote MCP + SUNAT Beta y Prod.",
    },
    "STARTER": {
        "code": "STARTER",
        "name": "Starter",
        "monthly_quota": 500,
        "price_pen": 39.00,
        "description": "500 comprobantes/mes · Multi-RUC + Webhooks HMAC + Cola anti-1033.",
    },
    "PRO": {
        "code": "PRO",
        "name": "Pro",
        "monthly_quota": 3000,
        "price_pen": 99.00,
        "description": "3,000 comprobantes/mes · OAuth 2.1 MCP + Prioridad en cola SUNAT.",
    },
    "ENTERPRISE": {
        "code": "ENTERPRISE",
        "name": "Enterprise",
        "monthly_quota": 15000,
        "price_pen": 249.00,
        "description": "15,000 comprobantes/mes · Alto volumen + Soporte prioritario.",
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


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register_workspace(body: RegisterWorkspaceRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    if email == settings.GATEWAY_ADMIN_EMAIL.strip().lower():
        raise HTTPException(status_code=409, detail="Este correo ya está registrado.")
    existing = (await db.execute(select(GatewayUser).where(GatewayUser.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta registrada con este correo.")

    ws_name = (body.workspace_name or f"Workspace de {body.full_name.strip().split()[0]}").strip()
    ws = Workspace(
        name=ws_name,
        slug=_slugify(ws_name),
        plan_name="FREE",
        monthly_quota=PLANS_CATALOG["FREE"]["monthly_quota"],
    )
    db.add(ws)
    await db.flush()

    user = GatewayUser(
        workspace_id=ws.id,
        email=email,
        full_name=body.full_name.strip(),
        password_hash=hash_password(body.password),
        role="workspace_owner",
    )
    db.add(user)
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


class BillingCheckoutRequest(BaseModel):
    plan_code: str = Field(..., pattern="^(STARTER|PRO|ENTERPRISE)$")


@router.post("/billing/checkout")
async def create_billing_checkout(
    body: BillingCheckoutRequest,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    ws_id = get_actor_workspace_id(actor)
    if not ws_id:
        raise HTTPException(
            status_code=400,
            detail="El Superadmin Global no requiere suscripción. Inicia sesión con una cuenta de Workspace para probar pagos.",
        )
    ws = await db.get(Workspace, ws_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace no encontrado.")

    plan = PLANS_CATALOG[body.plan_code]
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
        amount_pen=plan["price_pen"],
        status="PENDING",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    base = settings.PUBLIC_BASE_URL.rstrip("/")
    preference = {
        "items": [
            {
                "id": plan["code"],
                "title": f"{settings.APP_NAME} — Plan {plan['name']} ({plan['monthly_quota']} comprobantes/mes)",
                "quantity": 1,
                "currency_id": "PEN",
                "unit_price": float(plan["price_pen"]),
            }
        ],
        "external_reference": f"GW-PLAN-{order.id}",
        "payer": {"email": actor.get("sub") or "cliente@apisunat.pro"},
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
