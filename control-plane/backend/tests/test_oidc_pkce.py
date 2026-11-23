"""
Pruebas Unitarias para OIDC y PKCE (RFC 7636).
"""
from app.services.oidc_service import OIDCService


def test_code_verifier_generation():
    verifier = OIDCService.generate_code_verifier(length=64)
    assert len(verifier) == 64
    assert isinstance(verifier, str)


def test_code_challenge_calculation():
    # Vector de prueba estándar RFC 7636
    # Si verifier es "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    
    calculated = OIDCService.calculate_code_challenge(verifier)
    assert calculated == expected_challenge


def test_pkce_verification():
    verifier = OIDCService.generate_code_verifier(length=80)
    challenge = OIDCService.calculate_code_challenge(verifier)

    # Verificación válida
    assert OIDCService.verify_pkce(verifier, challenge, method="S256") is True

    # Verificación con verifier alterado
    tampered_verifier = verifier[:-1] + ("A" if verifier[-1] != "A" else "B")
    assert OIDCService.verify_pkce(tampered_verifier, challenge, method="S256") is False

    # Verificación con método no soportado
    assert OIDCService.verify_pkce(verifier, challenge, method="plain") is False
