# -*- coding: utf-8 -*-
from app.api.billing import PLANS_CATALOG, _slugify
from app.api.deps import get_actor_workspace_id, is_superadmin
from app.core.security import (
    create_admin_jwt,
    create_workspace_user_jwt,
    hash_password,
    verify_admin_jwt,
    verify_password,
)


def test_pbkdf2_password_hashing_and_verification():
    h = hash_password("MiClaveSegura2026!")
    assert h.startswith("pbkdf2_sha256$200000$")
    assert verify_password("MiClaveSegura2026!", h) is True
    assert verify_password("ClaveIncorrecta", h) is False


def test_workspace_user_jwt_vs_superadmin_jwt():
    admin_token = create_admin_jwt("admin@sofiaerp.com")
    admin_payload = verify_admin_jwt(admin_token)
    assert admin_payload is not None
    assert is_superadmin(admin_payload) is True
    assert get_actor_workspace_id(admin_payload) is None

    ws_token = create_workspace_user_jwt(
        email="luis@empresa.pe",
        user_id="usr-123",
        workspace_id="ws-999",
        workspace_name="Workspace de Luis",
        full_name="Luis Pérez",
    )
    ws_payload = verify_admin_jwt(ws_token)
    assert ws_payload is not None
    assert is_superadmin(ws_payload) is False
    assert get_actor_workspace_id(ws_payload) == "ws-999"
    assert ws_payload["workspace_name"] == "Workspace de Luis"


def test_plans_catalog_and_slugify():
    from app.api.billing import BillingCheckoutRequest, BillingProfileRequest

    assert set(PLANS_CATALOG.keys()) == {"FREE", "STARTER", "PRO", "ENTERPRISE"}
    assert PLANS_CATALOG["FREE"]["monthly_quota"] == 50
    assert PLANS_CATALOG["FREE"]["price_pen"] == 0.0
    assert PLANS_CATALOG["STARTER"]["monthly_quota"] == 5000
    assert PLANS_CATALOG["STARTER"]["price_pen"] == 6.90
    assert PLANS_CATALOG["STARTER"]["annual_price_pen"] == 69.00
    assert PLANS_CATALOG["PRO"]["price_pen"] == 9.90
    assert PLANS_CATALOG["PRO"]["annual_price_pen"] == 99.00

    chk = BillingCheckoutRequest(plan_code="PRO", billing_cycle="yearly")
    assert chk.billing_cycle == "yearly"
    prof = BillingProfileRequest(doc_type_receipt="01", identity_type="6", identity_number="20600994345", business_name="EMPRESA DEMO S.A.C.")
    assert prof.identity_number == "20600994345"

    slug = _slugify("Workspace de Luis S.A.C.")
    assert slug.startswith("workspace-de-luis-s-a-c-")
    assert len(slug) > 24


def test_sofia_sso_rs256_jwks_verification():
    import json
    from datetime import datetime, timedelta, timezone

    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    from app.api.billing import verify_sofia_rs256_token

    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(priv.public_key()))
    pub_jwk["kid"] = "sofia-key-1"

    token = jwt.encode(
        {
            "sub": "user-42",
            "email": "cliente@sofiaerp.com",
            "name": "Cliente Sofia",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
        },
        priv,
        algorithm="RS256",
        headers={"kid": "sofia-key-1"},
    )
    claims = verify_sofia_rs256_token(token, [pub_jwk])
    assert claims is not None
    assert claims["email"] == "cliente@sofiaerp.com"
    assert claims["name"] == "Cliente Sofia"

    # Token con firma manipulada debe ser rechazado
    tampered = token[:-4] + "XXXX"
    assert verify_sofia_rs256_token(tampered, [pub_jwk]) is None


def test_workspace_member_model_and_create_request():
    from app.api.billing import InviteMemberRequest, WorkspaceCreateRequest, _assert_can_manage_workspace
    from app.models import WorkspaceInvitation, WorkspaceMember
    from fastapi import HTTPException
    import pytest

    req = WorkspaceCreateRequest(name="Agencia Dev Lima S.A.C.")
    assert req.name == "Agencia Dev Lima S.A.C."
    mem = WorkspaceMember(user_id="usr-1", workspace_id="ws-2", role="owner")
    assert mem.user_id == "usr-1"
    assert mem.workspace_id == "ws-2"
    assert mem.role == "owner"

    inv_req = InviteMemberRequest(email="dev@empresa.pe", role="member")
    assert inv_req.role == "member"
    inv = WorkspaceInvitation(workspace_id="ws-2", email="dev@empresa.pe", role="admin", token="tok-123", invited_by="owner@empresa.pe")
    assert inv.role == "admin"

    # RBAC: owner y admin pueden gestionar; member recibe 403
    _assert_can_manage_workspace({"role": "workspace_owner", "ws_role": "owner"})
    _assert_can_manage_workspace({"role": "workspace_owner", "ws_role": "admin"})
    with pytest.raises(HTTPException) as exc:
        _assert_can_manage_workspace({"role": "workspace_owner", "ws_role": "member"})
    assert exc.value.status_code == 403


def test_insecure_secret_warnings_detection():
    from app.core.config import Settings

    weak = Settings(
        SUNAT_VAULT_MASTER_KEY="sofia_change_vault_master_key_in_env",
        GATEWAY_JWT_SECRET="short",
        INTERNAL_SERVICE_KEY="sofia_internal_mesh_key_change_in_prod",
        GATEWAY_ADMIN_PASSWORD="SofiaAdmin2026!",
    )
    warnings = weak.get_insecure_secret_warnings()
    assert len(warnings) == 4

    strong = Settings(
        SUNAT_VAULT_MASTER_KEY="A9x!kP2#mQ7$vL4@nR8&wZ5*cB3^yT6%",
        GATEWAY_JWT_SECRET="J8d@pK4#sW9$xM2!qF7&bN5*hV3^cL6%",
        INTERNAL_SERVICE_KEY="M3z!tR6#yP8$kN2@wQ5&vD9*jH4^bF7%",
        GATEWAY_ADMIN_PASSWORD="SuperStrongProdPass#2026!",
    )
    assert strong.get_insecure_secret_warnings() == []
