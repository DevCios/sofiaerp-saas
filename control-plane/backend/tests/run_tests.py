"""
Runner de pruebas unitarias compatible con entornos estándar sin dependencias externas.
"""
import sys
import os
import unittest
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.mfa_service import MFAService
from app.services.oidc_service import OIDCService
from app.services.domain_service import DomainService
from app.services.provisioning_service import ProvisioningService
from app.services.entitlement_service import EntitlementService, EntitlementCode
from app.services.billing_service import BillingService, SubscriptionState
from app.services.recovery_service import RecoveryService
from app.services.migration_service import MigrationService

# Añadir ruta del workspace para contratos compartidos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from shared.contracts.tenant_context import TenantContext

# Añadir ruta para servicios de SUNAT
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../products/sofia-erp/addons/l10n_pe_edi_sofia")))
from services.qr_generator import SUNATQRGenerator


class TestMFAService(unittest.TestCase):
    def test_totp_secret_and_uri(self):
        secret = MFAService.generate_totp_secret()
        self.assertGreaterEqual(len(secret), 16)
        uri = MFAService.get_provisioning_uri(secret, "admin@empresa.pe")
        self.assertTrue(uri.startswith("otpauth://totp/SOFIA%20ERP:admin@empresa.pe"))

    def test_totp_code_verification(self):
        secret = MFAService.generate_totp_secret()
        now = int(time.time())
        code = MFAService.generate_totp_code(secret, for_time=now)
        self.assertEqual(len(code), 6)
        self.assertTrue(MFAService.verify_totp_code(secret, code))
        self.assertFalse(MFAService.verify_totp_code(secret, "999999" if code != "999999" else "000000"))

    def test_recovery_codes(self):
        plain, hashes = MFAService.generate_recovery_codes(4)
        self.assertEqual(len(plain), 4)
        valid, remaining = MFAService.verify_recovery_code(plain[0], hashes)
        self.assertTrue(valid)
        self.assertEqual(len(remaining), 3)
        # Código ya usado debe fallar
        reused, _ = MFAService.verify_recovery_code(plain[0], remaining)
        self.assertFalse(reused)


class TestOIDCPKCE(unittest.TestCase):
    def test_verifier_and_challenge(self):
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        expected = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
        self.assertEqual(OIDCService.calculate_code_challenge(verifier), expected)
        self.assertTrue(OIDCService.verify_pkce(verifier, expected, "S256"))


class TestDomainResolver(unittest.TestCase):
    def test_subdomain_pattern(self):
        match = DomainService.PLATFORM_DOMAIN_PATTERN.match("constructora.erp.sofiaerp.com")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "constructora")

        self.assertIsNone(DomainService.PLATFORM_DOMAIN_PATTERN.match("external-site.com"))

    def test_token_generation(self):
        token = DomainService.generate_verification_token()
        self.assertTrue(token.startswith("sofia-verification-"))


class TestProvisioning(unittest.TestCase):
    def test_database_name_sanitization(self):
        slug = "Minera-Andina! 2026_S.A.C."
        db_name = ProvisioningService.sanitize_database_name(slug)
        self.assertTrue(db_name.startswith("sofia_tenant_"))
        self.assertNotIn(" ", db_name)
        self.assertNotIn("!", db_name)
        self.assertLessEqual(len(db_name), 63)

    def test_dry_run_pipeline(self):
        result = ProvisioningService.provision_tenant_pipeline(
            slug="transportes-peru",
            dry_run=True,
            max_connections=25,
        )
        self.assertEqual(result["status"], "DRY_RUN_SUCCESS")
        self.assertEqual(result["database_name"], "sofia_tenant_transportes_peru")
        self.assertEqual(result["max_connections"], 25)


class TestEntitlements(unittest.TestCase):
    def test_tier_entitlements_mapping(self):
        basic = EntitlementService.get_entitlements_for_tier("BASIC")
        pro = EntitlementService.get_entitlements_for_tier("PROFESSIONAL")
        enterprise = EntitlementService.get_entitlements_for_tier("ENTERPRISE")
        self.assertIn(EntitlementCode.CUSTOM_LOGO, basic)
        self.assertNotIn(EntitlementCode.CUSTOM_DOMAIN, basic)
        self.assertIn(EntitlementCode.CUSTOM_DOMAIN, pro)
        self.assertIn(EntitlementCode.WHITE_LABEL, enterprise)

    def test_non_destructive_degradation(self):
        active = [EntitlementCode.CUSTOM_LOGO]
        applied = EntitlementService.apply_branding_with_entitlements(
            active_entitlements=active,
            logo_url="https://empresa.pe/logo.png",
            primary_color="#EF4444",
            enable_white_label=True,
        )
        self.assertEqual(applied["applied_logo"], "https://empresa.pe/logo.png")
        self.assertEqual(applied["applied_color"], "#3B82F6")  # Fallback seguro
        self.assertFalse(applied["white_label_active"])
        self.assertEqual(applied["stored_preferences"]["primary_color"], "#EF4444")


class TestSunatFormats(unittest.TestCase):
    def test_invoice_and_gre_qr(self):
        inv_qr = SUNATQRGenerator.generate_invoice_qr(
            "20601234567", "01", "F001", "123", 18.0, 118.0, "2026-11-16", "6", "20509876543", "hash1"
        )
        self.assertTrue(inv_qr.startswith("20601234567|01|F001|123|18.00|118.00|2026-11-16|6|20509876543|hash1|"))

        gre_qr = SUNATQRGenerator.generate_gre_qr(
            "20601234567", "09", "T001", "45", "20100000001", "2026-11-16", 50.0, "hash2"
        )
        self.assertTrue(gre_qr.startswith("20601234567|09|T001|45|20100000001|2026-11-16|50.00|hash2|"))


class TestBillingService(unittest.TestCase):
    def test_invoice_calculation(self):
        calc = BillingService.calculate_invoice_amount(base_price=100.0, extra_users=2, extra_storage_gb=10)
        self.assertEqual(calc["subtotal_neto"], 139.0)
        self.assertEqual(calc["total_amount"], 164.02)

    def test_grace_period_and_suspension(self):
        now = datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)
        recent_end = now - timedelta(days=2)
        res_grace = BillingService.evaluate_subscription_status(SubscriptionState.ACTIVE, recent_end, False, now)
        self.assertEqual(res_grace["new_status"], SubscriptionState.PAST_DUE)
        self.assertFalse(res_grace["is_service_blocked"])

        old_end = now - timedelta(days=8)
        res_susp = BillingService.evaluate_subscription_status(SubscriptionState.PAST_DUE, old_end, False, now)
        self.assertEqual(res_susp["new_status"], SubscriptionState.SUSPENDED)
        self.assertTrue(res_susp["is_service_blocked"])


class TestRecoveryService(unittest.TestCase):
    def test_rclone_and_pg_restore_commands(self):
        rclone_cmd = RecoveryService.build_rclone_download_command("backup.sql.gz", "/tmp")
        self.assertIn("rclone", rclone_cmd)
        self.assertIn("gdrive:backup.sql.gz", rclone_cmd)

        pg_cmd = RecoveryService.build_pg_restore_command("sofia_tenant_1", "/tmp/backup.sql.gz")
        self.assertIn("pg_restore", pg_cmd)
        self.assertIn("--clean", pg_cmd)


class TestMigrationAndMultiProduct(unittest.TestCase):
    def test_version_compatibility_and_dedicated_runtime(self):
        self.assertFalse(MigrationService.check_version_compatibility("20.0", "18.0")["compatible"])
        self.assertTrue(MigrationService.check_version_compatibility("18.0", "20.0")["compatible"])
        
        cfg = MigrationService.generate_dedicated_runtime_config(
            "tenant-corp", "sofia_tenant_corp", "/var/lib/sofia/filestores/corp"
        )
        self.assertEqual(cfg["mode"], "DEDICATED")
        self.assertIn("odoo_dedicated_tenant-corp", cfg["nginx_upstream_block"])

    def test_tenant_context_contract(self):
        ctx = TenantContext(
            tenant_id="t1", tenant_slug="corp", user_id="u1", user_email="a@corp.pe", roles=["TENANT_ADMIN"]
        )
        headers = ctx.to_http_headers()
        self.assertEqual(headers["X-Sofia-Tenant-Slug"], "corp")
        reconstructed = TenantContext.from_http_headers(headers)
        self.assertEqual(reconstructed.tenant_id, "t1")


if __name__ == "__main__":
    unittest.main()
