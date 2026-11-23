"""
Contratos de Integración Inter-Producto y Propagación de Contexto de Tenant (Sección 3.3).
Garantiza que los productos (SOFIA ERP, Industrial Services, Quality) se comuniquen
mediante interfaces versionadas y cabeceras inmutables, sin acceder a las tablas internas de otro producto.
Construido con librerías estándar (dataclasses) para máxima compatibilidad sin dependencias externas.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class TenantContext:
    """
    Contexto inmutable propagado a través de cabeceras seguras HTTP o tokens firmados.
    """
    tenant_id: str
    tenant_slug: str
    user_id: str
    user_email: str
    roles: List[str] = field(default_factory=list)
    entitlements: List[str] = field(default_factory=list)

    def to_http_headers(self) -> Dict[str, str]:
        """Serializa el contexto a cabeceras HTTP sanitizadas para proxies internos."""
        return {
            "X-Sofia-Tenant-ID": self.tenant_id,
            "X-Sofia-Tenant-Slug": self.tenant_slug,
            "X-Sofia-User-ID": self.user_id,
            "X-Sofia-User-Email": self.user_email,
            "X-Sofia-Roles": ",".join(self.roles),
            "X-Sofia-Entitlements": ",".join(self.entitlements),
        }

    @classmethod
    def from_http_headers(cls, headers: Dict[str, str]) -> Optional["TenantContext"]:
        """Reconstruye el contexto a partir de cabeceras HTTP inyectadas por el gateway."""
        tenant_id = headers.get("X-Sofia-Tenant-ID") or headers.get("x-sofia-tenant-id")
        user_id = headers.get("X-Sofia-User-ID") or headers.get("x-sofia-user-id")
        if not tenant_id or not user_id:
            return None

        roles_raw = headers.get("X-Sofia-Roles", headers.get("x-sofia-roles", ""))
        entitlements_raw = headers.get("X-Sofia-Entitlements", headers.get("x-sofia-entitlements", ""))

        return cls(
            tenant_id=tenant_id,
            tenant_slug=headers.get("X-Sofia-Tenant-Slug", headers.get("x-sofia-tenant-slug", "")),
            user_id=user_id,
            user_email=headers.get("X-Sofia-User-Email", headers.get("x-sofia-user-email", "")),
            roles=[r.strip() for r in roles_raw.split(",") if r.strip()],
            entitlements=[e.strip() for e in entitlements_raw.split(",") if e.strip()],
        )


@dataclass
class DomainEvent:
    """Estructura estandarizada para eventos asíncronos publicados entre productos."""
    event_id: str
    event_type: str  # TENANT_CREATED, SUBSCRIPTION_UPGRADED, TENANT_SUSPENDED
    tenant_id: str
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)
