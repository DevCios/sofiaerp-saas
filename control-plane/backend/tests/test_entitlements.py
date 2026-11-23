"""
Pruebas Unitarias para el Motor de Capacidades (Entitlements) y Degradación No Destructiva.
"""
import unittest
from app.services.entitlement_service import EntitlementService, EntitlementCode


class TestEntitlements(unittest.TestCase):
    def test_tier_entitlements_mapping(self):
        basic = EntitlementService.get_entitlements_for_tier("BASIC")
        pro = EntitlementService.get_entitlements_for_tier("PROFESSIONAL")
        enterprise = EntitlementService.get_entitlements_for_tier("ENTERPRISE")

        # Plan básico solo tiene logo
        self.assertIn(EntitlementCode.CUSTOM_LOGO, basic)
        self.assertNotIn(EntitlementCode.CUSTOM_DOMAIN, basic)
        self.assertNotIn(EntitlementCode.WHITE_LABEL, basic)

        # Plan Pro tiene dominio y branding, pero no white label
        self.assertIn(EntitlementCode.CUSTOM_DOMAIN, pro)
        self.assertIn(EntitlementCode.CUSTOM_COLORS, pro)
        self.assertNotIn(EntitlementCode.WHITE_LABEL, pro)

        # Plan Enterprise tiene todas las capacidades
        self.assertIn(EntitlementCode.WHITE_LABEL, enterprise)
        self.assertIn(EntitlementCode.MULTIPLE_PRODUCTS, enterprise)
        self.assertIn(EntitlementCode.ADVANCED_SUPPORT, enterprise)

    def test_non_destructive_degradation(self):
        # Cliente solicita personalización avanzada pero está en plan BASIC
        active_entitlements = [EntitlementCode.CUSTOM_LOGO]
        
        applied = EntitlementService.apply_branding_with_entitlements(
            active_entitlements=active_entitlements,
            logo_url="https://empresa.pe/logo.png",
            primary_color="#EF4444",
            custom_company_name="Empresa Minera",
            enable_white_label=True,
        )

        # Logo es permitido en Basic
        self.assertEqual(applied["applied_logo"], "https://empresa.pe/logo.png")
        # Color no permitido -> Fallback predeterminado seguro (#3B82F6)
        self.assertEqual(applied["applied_color"], "#3B82F6")
        # White label no permitido -> Inactivo
        self.assertFalse(applied["white_label_active"])

        # Sin embargo, las preferencias quedan intactas en base de datos para cuando actualice su plan
        self.assertEqual(applied["stored_preferences"]["primary_color"], "#EF4444")
        self.assertTrue(applied["stored_preferences"]["white_label_requested"])


if __name__ == "__main__":
    unittest.main()
