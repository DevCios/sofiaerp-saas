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
    assert set(PLANS_CATALOG.keys()) == {"FREE", "STARTER", "PRO", "ENTERPRISE"}
    assert PLANS_CATALOG["FREE"]["monthly_quota"] == 50
    assert PLANS_CATALOG["FREE"]["price_pen"] == 0.0
    assert PLANS_CATALOG["STARTER"]["monthly_quota"] == 500
    assert PLANS_CATALOG["PRO"]["monthly_quota"] == 3000
    assert PLANS_CATALOG["ENTERPRISE"]["monthly_quota"] == 15000

    slug = _slugify("Workspace de Luis S.A.C.")
    assert slug.startswith("workspace-de-luis-s-a-c-")
    assert len(slug) > 24
