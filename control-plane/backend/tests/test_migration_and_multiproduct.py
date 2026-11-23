"""
Pruebas Unitarias para el Migration Lab, Verificación de Versiones y Contratos Inter-Producto (Sección 16 y 3.3).
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.services.migration_service import MigrationService
from shared.contracts.tenant_context import TenantContext


class TestMigrationAndMultiProduct(unittest.TestCase):
    def test_version_compatibility_checker(self):
        # 1. Downgrade no permitido
        res_downgrade = MigrationService.check_version_compatibility("20.0", "18.0")
        self.assertFalse(res_downgrade["compatible"])
        self.assertIn("Downgrade no permitido", res_downgrade["reason"])

        # 2. Versión destino no soportada
        res_unsupported = MigrationService.check_version_compatibility("20.0", "22.0")
        self.assertFalse(res_unsupported["compatible"])

        # 3. Major upgrade válido (requiere migration lab)
        res_upgrade = MigrationService.check_version_compatibility("18.0", "20.0")
        self.assertTrue(res_upgrade["compatible"])
        self.assertTrue(res_upgrade["requires_lab"])
        self.assertEqual(res_upgrade["upgrade_type"], "MAJOR_UPGRADE")

    def test_migration_lab_sql_generation(self):
        sql_cmds = MigrationService.generate_migration_lab_sql(
            production_db="sofia_tenant_constructora",
            staging_db="sofia_staging_constructora",
        )
        self.assertEqual(len(sql_cmds), 1)
        self.assertIn('CREATE DATABASE "sofia_staging_constructora"', sql_cmds[0])
        self.assertIn('WITH TEMPLATE "sofia_tenant_constructora"', sql_cmds[0])

    def test_dedicated_runtime_config_generation(self):
        config = MigrationService.generate_dedicated_runtime_config(
            tenant_slug="minera-andina",
            database_name="sofia_tenant_minera_andina",
            filestore_path="/var/lib/sofia/filestores/minera-andina",
            allocated_cpu="4.0",
            allocated_memory="8g",
        )
        self.assertEqual(config["mode"], "DEDICATED")
        self.assertEqual(config["service_name"], "odoo-dedicated-minera-andina")
        self.assertIn("services", config["compose_snippet"])
        self.assertIn("upstream odoo_dedicated_minera-andina", config["nginx_upstream_block"])

    def test_tenant_context_header_serialization(self):
        ctx = TenantContext(
            tenant_id="11111111-2222-3333-4444-555555555555",
            tenant_slug="empresa-alpha",
            user_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            user_email="admin@alpha.pe",
            roles=["TENANT_ADMIN"],
            entitlements=["custom_domain", "white_label"],
        )
        headers = ctx.to_http_headers()
        self.assertEqual(headers["X-Sofia-Tenant-Slug"], "empresa-alpha")
        self.assertEqual(headers["X-Sofia-Roles"], "TENANT_ADMIN")
        self.assertIn("white_label", headers["X-Sofia-Entitlements"])

        # Deserialización simétrica
        reconstructed = TenantContext.from_http_headers(headers)
        self.assertIsNotNone(reconstructed)
        self.assertEqual(reconstructed.tenant_id, ctx.tenant_id)
        self.assertEqual(reconstructed.roles, ["TENANT_ADMIN"])


if __name__ == "__main__":
    unittest.main()
