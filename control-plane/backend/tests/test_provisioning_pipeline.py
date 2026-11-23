"""
Pruebas Unitarias para el Pipeline de Aprovisionamiento Seguro de Tenants (ADR-002 y ADR-005).
"""
import os
import shutil
import tempfile
import unittest
from app.services.provisioning_service import ProvisioningService, ProvisioningError


class TestProvisioningPipeline(unittest.TestCase):
    def test_database_name_sanitization(self):
        # Slug con guiones y caracteres especiales
        slug = "Minera-Andina! 2026_S.A.C."
        db_name = ProvisioningService.sanitize_database_name(slug)
        self.assertTrue(db_name.startswith("sofia_tenant_"))
        # No debe contener espacios ni caracteres inválidos para PostgreSQL
        self.assertNotIn(" ", db_name)
        self.assertNotIn("!", db_name)
        self.assertNotIn(".", db_name)
        # Longitud máxima permitida por PostgreSQL
        self.assertLessEqual(len(db_name), 63)

    def test_filestore_path_construction(self):
        base_dir = "/var/lib/sofia/filestores"
        slug = "empresa-norte"
        db_name = "sofia_tenant_empresa_norte"
        path = ProvisioningService.get_filestore_path(base_dir, slug, db_name)
        expected = os.path.join(base_dir, slug, "filestore", db_name)
        self.assertEqual(path, expected)

    def test_dry_run_pipeline(self):
        result = ProvisioningService.provision_tenant_pipeline(
            slug="transportes-peru",
            dry_run=True,
            max_connections=25,
        )
        self.assertEqual(result["status"], "DRY_RUN_SUCCESS")
        self.assertEqual(result["database_name"], "sofia_tenant_transportes_peru")
        self.assertEqual(result["max_connections"], 25)

    def test_filestore_directory_initialization(self):
        temp_dir = tempfile.mkdtemp()
        try:
            target_path = os.path.join(temp_dir, "tenants", "tenant_a", "filestore", "db_a")
            success = ProvisioningService.initialize_filestore(target_path)
            self.assertTrue(success)
            self.assertTrue(os.path.isdir(target_path))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
