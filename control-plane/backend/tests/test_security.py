"""
Pruebas de Criptografía, Hashes y Validación de Tokens JWT.
"""
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
)


def test_password_hashing():
    raw_pass = "Empresarial_2026_Secure!"
    hashed = get_password_hash(raw_pass)
    
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("PasswordErroneo", hashed) is False


def test_jwt_token_generation_and_decoding():
    user_id = "11111111-2222-3333-4444-555555555555"
    tenant_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    roles = ["TENANT_ADMIN"]

    token = create_access_token(subject=user_id, tenant_id=tenant_id, roles=roles)
    assert isinstance(token, str)
    assert len(token) > 20

    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["tenant_id"] == tenant_id
    assert payload["roles"] == roles
    assert payload["iss"] == "https://auth.sofiaerp.com"
