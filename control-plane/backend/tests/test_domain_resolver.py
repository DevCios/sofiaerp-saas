"""
Pruebas Unitarias para el Servicio de Resolución de Dominios y Saneamiento de dbfilter.
"""
from app.services.domain_service import DomainService


def test_platform_subdomain_pattern_matching():
    # Coincidencias válidas
    match1 = DomainService.PLATFORM_DOMAIN_PATTERN.match("constructora.erp.sofiaerp.com")
    assert match1 is not None
    assert match1.group(1) == "constructora"

    match2 = DomainService.PLATFORM_DOMAIN_PATTERN.match("minera-andina.sofiaerp.com")
    assert match2 is not None
    assert match2.group(1) == "minera-andina"

    # No coincidencias (dominios externos o no autorizados)
    assert DomainService.PLATFORM_DOMAIN_PATTERN.match("erp.empresa.pe") is None
    assert DomainService.PLATFORM_DOMAIN_PATTERN.match("malicious-site.com") is None


def test_verification_token_generation():
    token = DomainService.generate_verification_token()
    assert token.startswith("sofia-verification-")
    assert len(token) > 30
