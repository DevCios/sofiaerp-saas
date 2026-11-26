from odoo.tests.common import TransactionCase
from odoo.tests.common import Form
from datetime import datetime
from unittest.mock import patch

class TestAccountExchangeCurrency(TransactionCase):

    def setUp(self):
        super(TestAccountExchangeCurrency, self).setUp()
        self.currency_usd = self.env['res.currency'].search([('name', '=', 'USD')])

    def test_validate_currency_date(self):
        date = datetime.now()
        currency_rate = self.env['res.currency.rate'].create({
            'name': date,
            'company_id': self.env.ref("base.main_company").id,
            'currency_id': self.currency_usd.id,
            'rate': 0.269970401720
        })
        account_form = self.env['account.move'].search([('date','=',currency_rate.name)])
        val_pen = round(account_form.exchange_rate,6)
        val_usd = round(1 / currency_rate.rate, 6)
        
        self.assertEqual(val_pen, val_usd)
        self.assertEqual(account_form._get_actual_currency_rate(),account_form.exchange_rate)

    def test_sync_from_migo_uses_sunat_endpoint_for_usd(self):
        credential_model = self.env['api.data.provider.credential']

        class Response:
            status_code = 200
            text = '{"success": true}'

            def json(self):
                return {
                    'success': True,
                    'precio_compra': 3.400,
                    'precio_venta': 3.402,
                    'fecha': '2026-06-10',
                }

        with patch.object(type(credential_model), '_get_credentials', lambda self, service: ('migo', 'token')):
            with patch('requests.get', return_value=Response()) as request_get:
                self.env['res.currency.rate'].sync_from_migo(self.currency_usd, company=self.env.company)

        currency_rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', self.currency_usd.id),
            ('company_id', '=', self.env.company.id),
            ('name', '=', '2026-06-10'),
        ], limit=1)

        request_get.assert_called_once()
        self.assertEqual(request_get.call_args[0][0], 'https://api.migo.pe/api/v2/tipo-cambio/sunat/ultimo')
        self.assertEqual(request_get.call_args[1]['params'], {})
        self.assertTrue(currency_rate)
        self.assertEqual(round(currency_rate.inverse_company_rate, 3), 3.402)

    def test_sync_from_migo_uses_sbs_adjusted_date_for_eur(self):
        currency_eur = self.env['res.currency'].with_context(active_test=False).search([('name', '=', 'EUR')], limit=1)
        currency_eur.active = True
        credential_model = self.env['api.data.provider.credential']

        class Response:
            status_code = 200
            text = '{"success": true}'

            def json(self):
                return {
                    'success': True,
                    'precio_compra': 3.671,
                    'precio_venta': 4.123,
                    'fecha': '2026-06-10',
                }

        with patch.object(type(credential_model), '_get_credentials', lambda self, service: ('migo', 'token')):
            with patch('requests.get', return_value=Response()) as request_get:
                self.env['res.currency.rate'].sync_from_migo(currency_eur, company=self.env.company)

        currency_rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', currency_eur.id),
            ('company_id', '=', self.env.company.id),
            ('name', '=', '2026-06-11'),
        ], limit=1)

        request_get.assert_called_once()
        self.assertEqual(request_get.call_args[0][0], 'https://api.migo.pe/api/v2/tipo-cambio/sbs/ultimo')
        self.assertEqual(request_get.call_args[1]['params'], {'moneda': 'EUR'})
        self.assertTrue(currency_rate)
        self.assertEqual(round(currency_rate.inverse_company_rate, 3), 4.123)
        

