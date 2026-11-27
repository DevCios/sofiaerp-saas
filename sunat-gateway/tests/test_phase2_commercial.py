# -*- coding: utf-8 -*-
import base64
import hashlib

import pytest

from app.api.docs_portal import docs_portal
from app.api.oauth_mcp import oauth_authorization_server, oauth_protected_resource
from app.core.security import create_mcp_oauth_jwt, verify_mcp_oauth_jwt, verify_pkce_s256


def test_pkce_s256_verification_roundtrip():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")

    assert verify_pkce_s256(verifier, challenge) is True
    assert verify_pkce_s256("wrong-verifier", challenge) is False
    assert verify_pkce_s256("", challenge) is False


def test_mcp_oauth_jwt_roundtrip_and_scope():
    token = create_mcp_oauth_jwt(subject="admin@sofiaerp.com", client_id="mcp_demo_1", allowed_rucs=["20600994345"])
    payload = verify_mcp_oauth_jwt(token)
    assert payload is not None
    assert payload["scope"] == "mcp:sunat"
    assert payload["cid"] == "mcp_demo_1"
    assert payload["allowed_rucs"] == ["20600994345"]
    assert verify_mcp_oauth_jwt("invalid.token.here") is None


@pytest.mark.asyncio
async def test_oauth_well_known_discovery_and_docs_portal():
    pr = await oauth_protected_resource()
    assert pr["resource"].endswith("/mcp")
    assert "mcp:sunat" in pr["scopes_supported"]

    auth_srv = await oauth_authorization_server()
    assert auth_srv["authorization_endpoint"].endswith("/oauth/authorize")
    assert auth_srv["token_endpoint"].endswith("/oauth/token")
    assert auth_srv["registration_endpoint"].endswith("/oauth/register")
    assert "S256" in auth_srv["code_challenge_methods_supported"]

    resp = await docs_portal()
    assert resp.status_code == 200
    assert b"/openapi-ai.json" in resp.body
    assert b"Sofia SUNAT Gateway" in resp.body
