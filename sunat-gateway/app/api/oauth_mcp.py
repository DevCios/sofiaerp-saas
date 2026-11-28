# -*- coding: utf-8 -*-
"""
OAuth 2.1 + PKCE (S256) & Dynamic Client Registration (RFC 7591 / RFC 8414 / RFC 9728)
para Conexión 1-Clic de Remote MCP en Claude.ai, ChatGPT Connectors y clientes MCP (ADR-011).
"""
import html
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_actor_workspace_id, get_gateway_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_mcp_oauth_jwt, hash_api_key, verify_password, verify_pkce_s256
from app.models import ApiClient, GatewayUser, Issuer, OAuthAuthCode, OAuthClient, Workspace

router = APIRouter(tags=["OAuth 2.1 MCP"])
settings = get_settings()


# ==============================================================================
# 1. Discovery RFC 9728 (Protected Resource) & RFC 8414 (Authorization Server)
# ==============================================================================
@router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource():
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return {
        "resource": f"{base}/mcp",
        "authorization_servers": [base],
        "scopes_supported": ["mcp:sunat"],
        "bearer_methods_supported": ["header"],
    }


@router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server():
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/oauth/authorize",
        "token_endpoint": f"{base}/oauth/token",
        "registration_endpoint": f"{base}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": ["mcp:sunat"],
    }


# ==============================================================================
# 2. Dynamic Client Registration (RFC 7591) — requerido por Claude.ai / ChatGPT
# ==============================================================================
class OAuthRegisterRequest(BaseModel):
    client_name: str = Field(default="MCP AI Client", max_length=160)
    redirect_uris: list[str] = Field(..., min_length=1)
    token_endpoint_auth_method: str = Field(default="none")


@router.post("/oauth/register", status_code=status.HTTP_201_CREATED)
async def oauth_register_client(
    body: OAuthRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    client_id = f"mcp_{secrets.token_urlsafe(18)}"
    client = OAuthClient(
        id=client_id,
        client_name=body.client_name.strip()[:160],
        redirect_uris=body.redirect_uris,
        token_endpoint_auth_method=body.token_endpoint_auth_method or "none",
    )
    db.add(client)
    await db.commit()
    return {
        "client_id": client.id,
        "client_name": client.client_name,
        "redirect_uris": client.redirect_uris,
        "token_endpoint_auth_method": client.token_endpoint_auth_method,
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
    }


# ==============================================================================
# 3. Consentimiento OAuth 2.1 (Design System Odoo 20)
# ==============================================================================
def _render_consent_html(
    *,
    client_name: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
    issuers: list[Issuer],
    error_msg: str = "",
) -> str:
    ruc_options = '<option value="">Todas las empresas autorizadas</option>' + "".join(
        f'<option value="{html.escape(i.ruc)}">{html.escape(i.ruc)} — {html.escape(i.business_name)} [{"BETA" if i.is_beta else "PROD"}]</option>'
        for i in issuers
    )
    err_html = (
        f'<div style="background:#FDE2E2;color:#B91C1C;padding:10px 12px;border-radius:8px;font-size:12.5px;margin-bottom:14px">{html.escape(error_msg)}</div>'
        if error_msg
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Autorizar Conector IA — API SUNAT</title>
  <style>
    body {{ margin:0; font-family: Inter, system-ui, -apple-system, sans-serif; background: linear-gradient(180deg, #F4F1FB 0%, #F6F7F9 100%); color:#1F2937; min-height:100vh; display:flex; align-items:center; justify-content:center; padding:20px; }}
    .box {{ max-width:440px; width:100%; background:#FFFFFF; border:1px solid #E2E5EC; border-radius:14px; padding:28px; box-shadow:0 12px 30px rgba(102,89,143,.12); }}
    .logo {{ width:46px; height:46px; border-radius:10px; background:#714B67; color:#FFFFFF; font-weight:800; font-size:20px; display:flex; align-items:center; justify-content:center; margin:0 auto 12px auto; }}
    h2 {{ margin:0 0 4px 0; text-align:center; font-size:19px; }}
    .sub {{ text-align:center; font-size:12.5px; color:#6B7280; margin:0 0 18px 0; }}
    .pill {{ background:#EAE6F8; color:#5B4B8A; padding:6px 12px; border-radius:8px; font-size:12px; font-weight:600; text-align:center; margin-bottom:16px; }}
    label {{ display:block; font-size:12px; font-weight:600; color:#374151; margin:10px 0 4px 0; }}
    input, select {{ width:100%; box-sizing:border-box; padding:9px 10px; border:1px solid #D1D5DB; border-radius:6px; font-size:13px; }}
    .btn {{ width:100%; margin-top:16px; background:#714B67; color:#FFFFFF; border:none; padding:11px; border-radius:8px; font-weight:700; font-size:13.5px; cursor:pointer; }}
    .btn:hover {{ background:#5C3B53; }}
    .hint {{ font-size:11.5px; color:#6B7280; margin-top:12px; text-align:center; }}
  </style>
</head>
<body>
  <div class="box">
    <div class="logo">A</div>
    <h2>Autorizar Conector IA</h2>
    <p class="sub">API SUNAT · OAuth 2.1 PKCE</p>
    <div class="pill"><strong>{html.escape(client_name)}</strong> solicita acceso <code>mcp:sunat</code></div>
    {err_html}
    <form method="post" action="/oauth/authorize">
      <input type="hidden" name="client_id" value="{html.escape(client_id)}" />
      <input type="hidden" name="redirect_uri" value="{html.escape(redirect_uri)}" />
      <input type="hidden" name="state" value="{html.escape(state)}" />
      <input type="hidden" name="code_challenge" value="{html.escape(code_challenge)}" />
      <input type="hidden" name="code_challenge_method" value="{html.escape(code_challenge_method)}" />

      <label>Correo Administrador Gateway (o deja vacío si usas API Key)</label>
      <input type="email" name="email" placeholder="admin@sofiaerp.com" />

      <label>Contraseña Administrador</label>
      <input type="password" name="password" placeholder="••••••••" />

      <label>— o autentica con una API Key existente (sk_live_...)</label>
      <input type="password" name="api_key" placeholder="sk_live_..." />

      <label>Restringir acceso a un RUC específico (recomendado)</label>
      <select name="restricted_ruc">{ruc_options}</select>

      <button type="submit" class="btn">Autorizar y Conectar Asistente IA</button>
    </form>
    <p class="hint">Puedes revocar o limitar el acceso en cualquier momento desde <strong>apisunat.pro</strong>.</p>
  </div>
</body>
</html>"""


@router.get("/oauth/authorize", response_class=HTMLResponse)
async def oauth_authorize_form(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query(default="code"),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query(default="S256"),
    state: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    if response_type != "code":
        raise HTTPException(status_code=400, detail="response_type debe ser 'code'.")
    if code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="Solo se soporta PKCE S256.")

    client = await db.get(OAuthClient, client_id)
    if not client or redirect_uri not in (client.redirect_uris or []):
        raise HTTPException(status_code=400, detail="client_id o redirect_uri no registrado.")

    return HTMLResponse(
        _render_consent_html(
            client_name=client.client_name,
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            issuers=[],
        )
    )


@router.post("/oauth/authorize")
async def oauth_authorize_submit(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    state: str = Form(default=""),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form(default="S256"),
    email: str = Form(default=""),
    password: str = Form(default=""),
    api_key: str = Form(default=""),
    restricted_ruc: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    client = await db.get(OAuthClient, client_id)
    if not client or redirect_uri not in (client.redirect_uris or []):
        raise HTTPException(status_code=400, detail="client_id o redirect_uri inválido.")

    subject: Optional[str] = None
    allowed_rucs: Optional[list[str]] = None

    if api_key.strip():
        kh = hash_api_key(api_key.strip())
        res = await db.execute(select(ApiClient).where(ApiClient.key_hash == kh, ApiClient.is_active.is_(True)))
        ac = res.scalar_one_or_none()
        if ac:
            subject = ac.name
            allowed_rucs = list(ac.allowed_rucs) if ac.allowed_rucs else None
    elif email.strip() and password:
        clean_email = email.strip().lower()
        email_ok = hmac.compare_digest(clean_email, settings.GATEWAY_ADMIN_EMAIL.strip().lower())
        pass_ok = hmac.compare_digest(password, settings.GATEWAY_ADMIN_PASSWORD)
        if email_ok and pass_ok:
            subject = settings.GATEWAY_ADMIN_EMAIL
        else:
            gw_user = (
                await db.execute(
                    select(GatewayUser).where(GatewayUser.email == clean_email, GatewayUser.is_active.is_(True))
                )
            ).scalar_one_or_none()
            if gw_user and verify_password(password, gw_user.password_hash):
                ws = await db.get(Workspace, gw_user.workspace_id)
                if ws and ws.is_active:
                    subject = gw_user.email
                    ws_rows = await db.execute(
                        select(Issuer.ruc).where(Issuer.workspace_id == ws.id, Issuer.is_active.is_(True))
                    )
                    allowed_rucs = [r[0] for r in ws_rows.all()]

    if not subject:
        return HTMLResponse(
            _render_consent_html(
                client_name=client.client_name,
                client_id=client_id,
                redirect_uri=redirect_uri,
                state=state,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                issuers=[],
                error_msg="Credenciales o API Key inválidas.",
            ),
            status_code=401,
        )

    clean_ruc = restricted_ruc.strip()
    if clean_ruc:
        if allowed_rucs and clean_ruc not in allowed_rucs:
            raise HTTPException(status_code=403, detail="La API Key no tiene permiso sobre el RUC elegido.")
        allowed_rucs = [clean_ruc]

    code = secrets.token_urlsafe(32)
    db.add(
        OAuthAuthCode(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            subject=subject,
            allowed_rucs=allowed_rucs,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )
    await db.commit()

    params = {"code": code}
    if state:
        params["state"] = state
    sep = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(url=f"{redirect_uri}{sep}{urlencode(params)}", status_code=302)


# ==============================================================================
# 4. Token Endpoint (Intercambio PKCE -> Access Token JWT)
# ==============================================================================
@router.post("/oauth/token")
async def oauth_token_exchange(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    grant_type = data.get("grant_type")
    code = str(data.get("code") or "").strip()
    code_verifier = str(data.get("code_verifier") or "").strip()
    client_id = str(data.get("client_id") or "").strip()
    redirect_uri = str(data.get("redirect_uri") or "").strip()

    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="grant_type no soportado.")
    if not code or not code_verifier:
        raise HTTPException(status_code=400, detail="code y code_verifier son obligatorios.")

    auth_code = await db.get(OAuthAuthCode, code)
    if not auth_code or auth_code.used:
        raise HTTPException(status_code=400, detail="Código de autorización inválido o ya utilizado.")
    if auth_code.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Código de autorización expirado.")
    if client_id and auth_code.client_id != client_id:
        raise HTTPException(status_code=400, detail="client_id no coincide.")
    if redirect_uri and auth_code.redirect_uri != redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri no coincide.")
    if not verify_pkce_s256(code_verifier, auth_code.code_challenge):
        raise HTTPException(status_code=400, detail="Verificación PKCE S256 fallida.")

    auth_code.used = True
    await db.commit()

    access_token = create_mcp_oauth_jwt(
        subject=auth_code.subject,
        client_id=auth_code.client_id,
        allowed_rucs=auth_code.allowed_rucs,
        ttl_days=30,
    )
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 30 * 24 * 3600,
        "scope": "mcp:sunat",
    }


# ==============================================================================
# 5. Listado y Revocación de Conexiones de IA (Consola Conectores)
# ==============================================================================
@router.get("/api/v1/connectors/connections")
async def list_ai_connections(
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    ws_id = get_actor_workspace_id(actor)
    items = []

    # Clientes OAuth 2.1 globales (solo visibles para Superadmin; workspaces ven sus API Keys)
    if not ws_id:
        oc_res = await db.execute(select(OAuthClient).order_by(OAuthClient.created_at.desc()).limit(30))
        for oc in oc_res.scalars().all():
            items.append(
                {
                    "id": oc.id,
                    "kind": "oauth",
                    "app_name": oc.client_name,
                    "auth_type": "OAuth 2.1 PKCE",
                    "detail": oc.id[:18] + "...",
                    "connected_at": oc.created_at.isoformat(),
                }
            )

    # API Keys activas del workspace
    cli_stmt = select(ApiClient).where(ApiClient.is_active.is_(True)).order_by(ApiClient.created_at.desc()).limit(30)
    if ws_id:
        cli_stmt = cli_stmt.where(ApiClient.workspace_id == ws_id)
    cli_res = await db.execute(cli_stmt)
    for c in cli_res.scalars().all():
        items.append(
            {
                "id": c.id,
                "kind": "api_key",
                "app_name": c.name,
                "auth_type": "API Key (Bearer)",
                "detail": c.key_prefix + "...",
                "connected_at": c.created_at.isoformat(),
            }
        )
    return items


@router.delete("/api/v1/connectors/oauth/{client_id}")
async def delete_oauth_connection(
    client_id: str,
    actor: dict = Depends(get_gateway_admin),
    db: AsyncSession = Depends(get_db),
):
    if get_actor_workspace_id(actor):
        raise HTTPException(status_code=403, detail="Solo el administrador de plataforma puede eliminar clientes OAuth globales.")
    oc = await db.get(OAuthClient, client_id)
    if not oc:
        raise HTTPException(status_code=404, detail="Conexión OAuth no encontrada.")
    await db.delete(oc)
    await db.commit()
    return {"disconnected": True}
