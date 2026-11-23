"""
Pruebas Unitarias para Recuperación ante Desastres (DR), Checksums y Comandos de Restauración (ADR-006).
"""
import os
import shutil
import tempfile
import unittest
from app.services.recovery_service import RecoveryService, DisasterRecoveryError


class TestRecoveryService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_file = os.path.join(self.temp_dir, "sample_backup.sql.gz")
        with open(self.sample_file, "wb") as f:
            f.write(b"MOCK_POSTGRESQL_BACKUP_CONTENT_SOFIA_2026")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_checksum_calculation_and_integrity(self):
        checksum = RecoveryService.calculate_file_checksum(self.sample_file)
        self.assertIsInstance(checksum, str)
        self.assertEqual(len(checksum), 64)  # Longitud SHA-256

        # Verificación con checksum correcto
        self.assertTrue(RecoveryService.verify_backup_integrity(self.sample_file, expected_checksum=checksum))

        # Verificación con checksum erróneo
        self.assertFalse(RecoveryService.verify_backup_integrity(self.sample_file, expected_checksum="invalid_hash_12345"))

    def test_simulate_tenant_restore(self):
        target_filestore = os.path.join(self.temp_dir, "restored_filestore")
        result = RecoveryService.simulate_tenant_restore(
            tenant_slug="minera-andina",
            backup_file=self.sample_file,
            target_db_name="sofia_tenant_minera_andina",
            target_filestore_dir=target_filestore,
        )

        self.assertEqual(result["status"], "RESTORED")
        self.assertEqual(result["tenant_slug"], "minera-andina")
        self.assertTrue(result["consistency_verified"])
        self.assertGreaterEqual(result["measured_rto_seconds"], 0.0)
        self.assertTrue(os.path.isdir(target_filestore))

    def test_rclone_and_pg_restore_command_builders(self):
        rclone_cmd = RecoveryService.build_rclone_download_command("backups/tenant_a.sql.gz", "/tmp/local.gz")
        self.assertIn("rclone", rclone_cmd)
        self.assertIn("gdrive:backups/tenant_a.sql.gz", rclone_cmd)

        pg_cmd = RecoveryService.build_pg_restore_command("sofia_tenant_a", "/tmp/local.gz")
        self.assertIn("pg_restore", pg_cmd)
        self.assertIn("--clean", pg_cmd)
        self.assertIn("sofia_tenant_a", pg_cmd)


if __name__ == "__main__":
    unittest.main()
