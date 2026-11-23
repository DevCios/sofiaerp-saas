"""
Servicio Evaluador de Capacidades y Entitlements Comerciales (ADR-001 y Sección 11).
Valida las capacidades habilitadas por plan (custom_domain, branding, white_label)
garantizando la degradación elegante y no destructiva de configuraciones.
"""
from typing import Dict, Any, List, Optional
from uuid import UUID


class EntitlementCode:
    CUSTOM_DOMAIN = "custom_domain"
    CUSTOM_LOGIN_BRANDING = "custom_login_branding"
    CUSTOM_LOGO = "custom_logo"
    CUSTOM_COLORS = "custom_colors"
    WHITE_LABEL = "white_label"
    MULTIPLE_PRODUCTS = "multiple_products"
    ADVANCED_SUPPORT = "advanced_support"


# Matriz de capacidades base por nivel de plan (Tier)
TIER_ENTITLEMENTS_MAP: Dict[str, List[str]] = {
    "BASIC": [
        EntitlementCode.CUSTOM_LOGO,
    ],
    "PROFESSIONAL": [
        EntitlementCode.CUSTOM_DOMAIN,
        EntitlementCode.CUSTOM_LOGIN_BRANDING,
        EntitlementCode.CUSTOM_LOGO,
        EntitlementCode.CUSTOM_COLORS,
    ],
    "ENTERPRISE": [
        EntitlementCode.CUSTOM_DOMAIN,
        EntitlementCode.CUSTOM_LOGIN_BRANDING,
        EntitlementCode.CUSTOM_LOGO,
        EntitlementCode.CUSTOM_COLORS,
        EntitlementCode.WHITE_LABEL,
        EntitlementCode.MULTIPLE_PRODUCTS,
        EntitlementCode.ADVANCED_SUPPORT,
    ],
}


class EntitlementService:
    @classmethod
    def get_entitlements_for_tier(cls, tier: str) -> List[str]:
        """Retorna las capacidades habilitadas por nivel de plan comercial."""
        clean_tier = tier.strip().upper()
        return TIER_ENTITLEMENTS_MAP.get(clean_tier, TIER_ENTITLEMENTS_MAP["BASIC"])

    @classmethod
    async def get_tenant_entitlements(cls, tenant_id: UUID, db: Any) -> Dict[str, Any]:
        """
        Consulta la suscripción activa del tenant y calcula sus capacidades contratadas.
        Si la suscripción está suspendida o en mora (PAST_DUE), aplica degradación temporal
        sin destruir configuraciones en base de datos.
        """
        from sqlalchemy import select
        from app.models.product import ProductPlan, Subscription

        sub_stmt = (
            select(Subscription, ProductPlan)
            .join(ProductPlan, Subscription.plan_id == ProductPlan.id)
            .where(
                Subscription.tenant_id == tenant_id,
                Subscription.status.in_(["ACTIVE", "TRIAL", "PAST_DUE"]),
            )
            .order_by(Subscription.current_period_end.desc())
        )
        res = await db.execute(sub_stmt)
        record = res.first()

        if not record:
            # Plan por defecto Básico degradado
            return {
                "tier": "BASIC",
                "subscription_status": "NONE",
                "entitlements": TIER_ENTITLEMENTS_MAP["BASIC"],
                "limits": {"max_users": 5, "max_concurrent_sessions": 5, "storage_gb": 10},
            }

        subscription, plan = record
        tier = plan.tier.upper()
        entitlements = list(cls.get_entitlements_for_tier(tier))

        # En estado PAST_DUE (mora), se mantiene la operación básica pero se bloquean adiciones avanzadas
        is_grace_period = subscription.status == "PAST_DUE"

        return {
            "tier": tier,
            "plan_code": plan.code,
            "subscription_status": subscription.status,
            "is_grace_period": is_grace_period,
            "entitlements": entitlements,
            "limits": {
                "max_users": plan.max_users + subscription.extra_users,
                "max_concurrent_sessions": plan.max_concurrent_sessions,
                "storage_gb": plan.storage_gb_limit + subscription.extra_storage_gb,
            },
        }

    @classmethod
    def check_entitlement(cls, active_entitlements: List[str], required_capability: str) -> bool:
        """Verifica si una capacidad requerida está presente en la lista de derechos activos."""
        return required_capability in active_entitlements

    @classmethod
    def apply_branding_with_entitlements(
        cls,
        active_entitlements: List[str],
        logo_url: Optional[str] = None,
        primary_color: Optional[str] = None,
        custom_company_name: Optional[str] = None,
        enable_white_label: bool = False,
    ) -> Dict[str, Any]:
        """
        Evalúa y aplica la personalización de marca según las capacidades contratadas.
        Si el cliente no tiene contratado custom_colors o white_label, no los activa,
        pero preserva los datos para cuando regularice su plan (Degradación no destructiva).
        """
        result = {
            "applied_logo": logo_url if cls.check_entitlement(active_entitlements, EntitlementCode.CUSTOM_LOGO) else None,
            "applied_color": primary_color if cls.check_entitlement(active_entitlements, EntitlementCode.CUSTOM_COLORS) else "#3B82F6",
            "applied_company_name": custom_company_name or "SOFIA ERP",
            "white_label_active": enable_white_label and cls.check_entitlement(active_entitlements, EntitlementCode.WHITE_LABEL),
            "stored_preferences": {
                "logo_url": logo_url,
                "primary_color": primary_color,
                "custom_company_name": custom_company_name,
                "white_label_requested": enable_white_label,
            },
        }
        return result
