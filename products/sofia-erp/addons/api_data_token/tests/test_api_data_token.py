from odoo.tests.common import TransactionCase


class TestApiDataProviderCredential(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Credential = self.env['api.data.provider.credential']

    def test_get_credentials_from_operation(self):
        credential = self.Credential.search([
            ('operation', '=', 'vat_document'),
            ('provider', '=', 'migo'),
        ], limit=1)
        credential.write({'token': 'test-token'})

        provider, token = self.Credential._get_credentials('vat_document')

        self.assertEqual(provider, 'migo')
        self.assertEqual(token, 'test-token')

    def test_legacy_operation_alias(self):
        credential = self.Credential.search([
            ('operation', '=', 'currency_rate'),
            ('provider', '=', 'migo'),
        ], limit=1)
        credential.write({'token': 'currency-token'})

        provider, token = self.Credential._get_credentials('currency')

        self.assertEqual(provider, 'migo')
        self.assertEqual(token, 'currency-token')
