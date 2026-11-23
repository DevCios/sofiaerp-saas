"""
Pruebas Unitarias para Formatos SUNAT (Facturas, Boletas, Guías de Remisión QR y UBL).
"""
import sys
import os
import unittest

# Incluir ruta de addons para importar servicios de SUNAT
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../products/sofia-erp/addons/l10n_pe_edi_sofia")))

from services.qr_generator import SUNATQRGenerator


class TestSunatFormats(unittest.TestCase):
    def test_invoice_qr_generation(self):
        qr_text = SUNATQRGenerator.generate_invoice_qr(
            company_ruc="20601234567",
            doc_type="01",
            serie="F001",
            correlativo="00000123",
            igv_amount=18.00,
            total_amount=118.00,
            invoice_date="2026-11-16",
            client_doc_type="6",
            client_doc_number="20509876543",
            digest_value="a1b2c3d4e5f6g7h8i9j0=",
        )

        # Debe contener los campos separados por '|'
        parts = qr_text.split("|")
        self.assertEqual(parts[0], "20601234567")
        self.assertEqual(parts[1], "01")
        self.assertEqual(parts[2], "F001")
        self.assertEqual(parts[3], "123")  # Correlativo limpio
        self.assertEqual(parts[4], "18.00")
        self.assertEqual(parts[5], "118.00")
        self.assertEqual(parts[6], "2026-11-16")
        self.assertEqual(parts[7], "6")
        self.assertEqual(parts[8], "20509876543")
        self.assertEqual(parts[9], "a1b2c3d4e5f6g7h8i9j0=")

    def test_gre_qr_generation(self):
        qr_text = SUNATQRGenerator.generate_gre_qr(
            company_ruc="20601234567",
            gre_type="09",
            serie="T001",
            correlativo="00000045",
            dest_doc_number="20100000001",
            transfer_date="2026-11-16",
            gross_weight=350.50,
            digest_value="hash_gre_12345",
        )

        parts = qr_text.split("|")
        self.assertEqual(parts[0], "20601234567")
        self.assertEqual(parts[1], "09")  # GRE Remitente
        self.assertEqual(parts[2], "T001")
        self.assertEqual(parts[3], "45")
        self.assertEqual(parts[4], "20100000001")
        self.assertEqual(parts[5], "2026-11-16")
        self.assertEqual(parts[6], "350.50")
        self.assertEqual(parts[7], "hash_gre_12345")


if __name__ == "__main__":
    unittest.main()
