"""
Servicio de Resolución de Tenants y Verificación de Dominios Personalizados.
Permite enrutar dinámicamente peticiones y verificar la titularidad DNS mediante TXT y CNAME.
"""
import re
import secrets
from typing import Optional, Dict, Any


class TenantNotFoundException(Exception):
    pass


class TenantSuspendedException(Exception):
    pass


class DomainService:
    # Patrón para identificar subdominios de la plataforma (ej. slug.erp.sofiaerp.com)
    PLATFORM_DOMAIN_PATTERN = re.compile(
        r"^([a-z0-9-]+)\.(?:erp\.)?sofiaerp\.com$", re.IGNORECASE
    )

    @classmethod
    async def resolve_host(cls, host: str, db: Any) -> Dict[str, Any]:
        """
        Resuelve el host entrante (cabecera HTTP Host) determinando el tenant y base de datos correspondiente.
        Protege contra Host Header Injection forzando la búsqueda estricta.
        """
        from sqlalchemy import select
        from app.models.tenant import Tenant, TenantDomain

        clean_host = host.split(":")[0].strip().lower()

        # 1. Verificar si es un subdominio de la plataforma
        match = cls.PLATFORM_DOMAIN_PATTERN.match(clean_host)
        if match:
            slug = match.group(1).lower()
            stmt = select(Tenant).where(Tenant.slug == slug)
            res = await db.execute(stmt)
            tenant = res.scalar_one_or_none()
            if not tenant:
                raise TenantNotFoundException(f"No existe ningún tenant para el subdominio: {clean_host}")
            
            if tenant.status == "SUSPENDED":
                raise TenantSuspendedException(f"El tenant '{slug}' se encuentra temporalmente suspendido.")

            return cls._build_resolution_payload(tenant, clean_host)

        # 2. Verificar si es un Dominio Personalizado del cliente (ej. erp.empresa.pe)
        domain_stmt = select(TenantDomain).where(TenantDomain.domain == clean_host)
        d_res = await db.execute(domain_stmt)
        tenant_domain = d_res.scalar_one_or_none()

        if not tenant_domain:
            raise TenantNotFoundException(f"Dominio no registrado en SOFIA Platform: {clean_host}")

        if tenant_domain.status not in ("VERIFIED", "SSL_ACTIVE"):
            raise TenantNotFoundException(f"El dominio '{clean_host}' está pendiente de validación DNS.")

        # Obtener el tenant asociado
        t_stmt = select(Tenant).where(Tenant.id == tenant_domain.tenant_id)
        t_res = await db.execute(t_stmt)
        tenant = t_res.scalar_one_or_none()

        if not tenant:
            raise TenantNotFoundException("Tenant asociado al dominio no encontrado.")

        if tenant.status == "SUSPENDED":
            raise TenantSuspendedException(f"El tenant '{tenant.slug}' se encuentra suspendido.")

        return cls._build_resolution_payload(tenant, clean_host)

    @staticmethod
    def _build_resolution_payload(tenant: Any, resolved_host: str) -> Dict[str, Any]:
        """Construye el payload de resolución para Nginx y el puente de autenticación."""
        return {
            "resolved": True,
            "tenant_id": str(tenant.id),
            "tenant_slug": tenant.slug,
            "tenant_name": tenant.name,
            "database_name": tenant.database_name,
            # Inyección de dbfilter para Odoo
            "odoo_dbfilter": f"^{tenant.database_name}$",
            "runtime_mode": tenant.runtime_mode,
            "dedicated_host": tenant.dedicated_host,
            "host": resolved_host,
            "status": tenant.status,
        }

    @staticmethod
    def generate_verification_token() -> str:
        """Genera un token seguro para el registro DNS TXT."""
        return f"sofia-verification-{secrets.token_hex(16)}"

    @classmethod
    async def verify_dns_txt_record(cls, domain: str, expected_token: str) -> bool:
        """
        Consulta servidores DNS para comprobar si el registro TXT '_sofia-challenge.domain'
        contiene el token de verificación esperado.
        """
        challenge_subdomain = f"_sofia-challenge.{domain}"
        try:
            import dns.resolver
            resolver = dns.resolver.Resolver()
            resolver.timeout = 5.0
            resolver.lifetime = 5.0
            answers = resolver.resolve(challenge_subdomain, "TXT")
            for rdata in answers:
                for txt_string in rdata.strings:
                    if txt_string.decode("utf-8").strip() == expected_token.strip():
                        return True
            return False
        except Exception:
            # En entornos sin DNS real o durante pruebas unitarias locales
            return False
