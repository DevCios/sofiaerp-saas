# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase, tagged
from ..services.commission_service import (
    compute_line_commission,
    compute_order_commission_breakdown,
    resolve_commission_rate,
)


@tagged('post_install', '-at_install', 'mercado_wanka')
class TestMercadoWankaCore(TransactionCase):

    def setUp(self):
        super().setUp()
        self.seller_a = self.env['res.partner'].create({
            'name': 'Tienda Piloto Alpha SAC',
            'vat': '20600994345',
            'email': 'alpha@test.pe',
            'is_company': True,
            'is_marketplace_seller': True,
            'marketplace_seller_status': 'approved',
            'sofia_tenant_slug': 'alpha',
            'sofia_tenant_url': 'https://alpha.sofiaerp.com',
            'sofia_subscription_active': True,
        })
        self.seller_b = self.env['res.partner'].create({
            'name': 'Tienda Piloto Beta EIRL',
            'vat': '20555111222',
            'email': 'beta@test.pe',
            'is_company': True,
            'is_marketplace_seller': True,
            'marketplace_seller_status': 'approved',
            'marketplace_custom_commission_rate': 7.5,
            'sofia_tenant_slug': 'beta',
            'sofia_tenant_url': 'https://beta.sofiaerp.com',
            'sofia_subscription_active': True,
        })
        self.buyer = self.env['res.partner'].create({
            'name': 'Comprador Prueba',
            'email': 'comprador@test.pe',
        })
        self.prod_a = self.env['product.product'].create({
            'name': 'Laptop Alpha',
            'type': 'consu',
            'list_price': 200.0,
            'marketplace_seller_id': self.seller_a.id,
            'marketplace_status': 'approved',
            'taxes_id': False,
        })
        self.prod_b = self.env['product.product'].create({
            'name': 'Mouse Beta',
            'type': 'consu',
            'list_price': 100.0,
            'marketplace_seller_id': self.seller_b.id,
            'marketplace_status': 'approved',
            'taxes_id': False,
        })

    def test_01_commission_service_formula(self):
        # 5% de 200 = 10.00 + 0.50 plataforma = 10.50 -> neto vendedor 189.50
        rate = resolve_commission_rate(seller=self.seller_a)
        self.assertEqual(rate, 5.0)
        line_comm = compute_line_commission(200.0, rate)
        self.assertEqual(line_comm, 10.0)
        bd = compute_order_commission_breakdown([line_comm], 200.0, 0.50)
        self.assertEqual(bd['commission_variable'], 10.0)
        self.assertEqual(bd['platform_fee'], 0.50)
        self.assertEqual(bd['commission_total'], 10.50)
        self.assertEqual(bd['seller_net'], 189.50)

        # Vendedor con tasa personalizada 7.5%
        self.assertEqual(resolve_commission_rate(seller=self.seller_b), 7.5)

    def test_02_multivendor_split_and_async_outbox(self):
        order = self.env['sale.order'].create({
            'partner_id': self.buyer.id,
            'order_line': [
                (0, 0, {'product_id': self.prod_a.id, 'product_uom_qty': 1, 'price_unit': 200.0, 'tax_ids': False}),
                (0, 0, {'product_id': self.prod_b.id, 'product_uom_qty': 1, 'price_unit': 100.0, 'tax_ids': False}),
            ],
        })
        order.action_confirm()

        # Deben existir 2 órdenes (principal para seller_a + dividida para seller_b)
        split_orders = self.env['sale.order'].search([('origin', '=', order.name)])
        self.assertEqual(len(split_orders), 1)
        self.assertEqual(order.marketplace_seller_id, self.seller_a)
        self.assertEqual(split_orders.marketplace_seller_id, self.seller_b)

        # Verificar comisiones: Alpha = 10.00 + 0.50 = 10.50 | Beta = 7.50 + 0.50 = 8.00
        self.assertAlmostEqual(order.marketplace_commission_total, 10.50, places=2)
        self.assertAlmostEqual(split_orders.marketplace_commission_total, 8.00, places=2)

        # Verificar encolado asíncrono en mw.webhook.outbox (sin bloquear checkout)
        outbox_jobs = self.env['mw.webhook.outbox'].search([('order_id', 'in', [order.id, split_orders.id])])
        self.assertEqual(len(outbox_jobs), 2)
        self.assertTrue(all(j.state == 'pending' for j in outbox_jobs))

    def test_03_bank_account_audit_trail(self):
        self.seller_a.write({
            'seller_bank_name': 'bcp',
            'seller_bank_account': '191-12345678-0-01',
            'seller_bank_cci': '00219100123456780015',
        })
        audits = self.env['mw.bank.audit'].search([('seller_id', '=', self.seller_a.id)])
        self.assertEqual(len(audits), 1)
        self.assertIn('00219100123456780015', audits.new_bank_info)

    def test_04_settlement_invoices_only_commission(self):
        order = self.env['sale.order'].create({
            'partner_id': self.buyer.id,
            'order_line': [
                (0, 0, {'product_id': self.prod_a.id, 'product_uom_qty': 1, 'price_unit': 200.0, 'tax_ids': False}),
            ],
        })
        order.action_confirm()
        today = date.today()
        settlement = self.env['marketplace.settlement'].create({
            'seller_id': self.seller_a.id,
            'date_start': today,
            'date_end': today,
            'only_delivered_escrow': True,
        })
        settlement.action_fetch_lines()
        self.assertEqual(len(settlement.line_ids), 1)
        self.assertAlmostEqual(settlement.commission_total, 10.50, places=2)
        self.assertAlmostEqual(settlement.amount_to_pay, 189.50, places=2)
