# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tools.float_utils import float_round


class TestL10nPeSpot(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.partner = self.env['res.partner'].create({
            'name': 'Cliente Test SAC',
            'vat': '20100070970',
        })
        self.product_serv = self.env['product.product'].create({
            'name': 'Servicio Legal',
            'l10n_pe_withhold_percentage': 12.0,
            'l10n_pe_withhold_code': '022',
        })

    def test_spot_thresholds(self):
        # 1. Factura menor a S/ 700 no debe tener detracción
        inv_low = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'l10n_pe_edi_operation_type': '1001',
            'invoice_line_ids': [(0, 0, {'product_id': self.product_serv.id, 'price_unit': 500.0, 'quantity': 1})],
        })
        self.assertEqual(inv_low._l10n_pe_edi_get_spot(), {})

        # 2. Factura mayor a S/ 700 debe calcular detracción al 12%
        inv_high = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'l10n_pe_edi_operation_type': '1001',
            'invoice_line_ids': [(0, 0, {'product_id': self.product_serv.id, 'price_unit': 1000.0, 'quantity': 1})],
        })
        spot = inv_high._l10n_pe_edi_get_spot()
        self.assertEqual(spot.get('payment_percent'), 12.0)
        self.assertEqual(spot.get('amount'), 120.0)

        # 3. Transporte menor a S/ 400 no debe tener detracción
        inv_trans_low = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'l10n_pe_edi_operation_type': '1004',
            'invoice_line_ids': [(0, 0, {'name': 'Flete Corto', 'price_unit': 350.0, 'quantity': 1})],
        })
        self.assertEqual(inv_trans_low._l10n_pe_edi_get_spot(), {})

        # 4. Transporte con Valor Referencial mayor calcula sobre el valor referencial (4%)
        inv_trans_ref = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'l10n_pe_edi_operation_type': '1004',
            'l10n_pe_edi_transport_origin_ubigeo': '150101',
            'l10n_pe_edi_transport_dest_ubigeo': '040101',
            'l10n_pe_edi_transport_ref_value': 800.0,
            'invoice_line_ids': [(0, 0, {'name': 'Flete Lima Arequipa', 'price_unit': 500.0, 'quantity': 1})],
        })
        spot_trans = inv_trans_ref._l10n_pe_edi_get_spot()
        self.assertEqual(spot_trans.get('payment_percent'), 4.0)
        self.assertEqual(spot_trans.get('amount'), 32.0)  # 4% de 800
