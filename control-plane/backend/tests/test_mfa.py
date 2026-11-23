"""
Pruebas Unitarias para el Servicio MFA (RFC 6238 TOTP y Códigos de Recuperación).
"""
import time
from app.services.mfa_service import MFAService


def test_totp_secret_generation():
    secret = MFAService.generate_totp_secret()
    assert isinstance(secret, str)
    assert len(secret) >= 16


def test_totp_provisioning_uri():
    secret = "JBSWY3DPEHPK3PXP"
    uri = MFAService.get_provisioning_uri(secret, "admin@empresa.pe")
    assert uri.startswith("otpauth://totp/SOFIA%20ERP:admin@empresa.pe")
    assert "secret=JBSWY3DPEHPK3PXP" in uri
    assert "issuer=SOFIA%20ERP" in uri


def test_totp_code_generation_and_verification():
    secret = MFAService.generate_totp_secret()
    current_time = int(time.time())
    
    # Generar código para el instante actual
    code = MFAService.generate_totp_code(secret, for_time=current_time)
    assert len(code) == 6
    assert code.isdigit()

    # Validar código correcto
    assert MFAService.verify_totp_code(secret, code) is True

    # Validar código erróneo
    assert MFAService.verify_totp_code(secret, "000000" if code != "000000" else "111111") is False


def test_recovery_codes_generation_and_consumption():
    plain_codes, hashed_codes = MFAService.generate_recovery_codes(count=5)
    assert len(plain_codes) == 5
    assert len(hashed_codes) == 5

    # Consumir el primer código
    test_code = plain_codes[0]
    is_valid, remaining_hashes = MFAService.verify_recovery_code(test_code, hashed_codes)
    assert is_valid is True
    assert len(remaining_hashes) == 4

    # Intentar reutilizar el mismo código (debe fallar por ser One-Time Use)
    reused_valid, _ = MFAService.verify_recovery_code(test_code, remaining_hashes)
    assert reused_valid is False
