from odoo import api, fields, models
from odoo.exceptions import UserError

# Providers that work without a token (free public endpoints)
FREE_PROVIDERS = {'apisnetpe_free'}


class ApiDataProviderCredential(models.Model):
    _name = 'api.data.provider.credential'
    _description = 'API Data Provider Credential'
    _order = 'operation, sequence, id'

    name = fields.Char(compute='_compute_name', store=True)
    provider = fields.Selection(
        [
            ('migo', 'Migo.pe'),
            ('apisnetpe', 'APIS.NET.PE'),
            ('apisnetpe_free', 'APIS.NET.PE Free'),
            ('apiperu', 'APIPERU'),
            ('jsonpe', 'JSON-PE'),
        ],
        required=True,
        default='migo',
    )
    operation = fields.Selection(
        [
            ('vat_document', 'Consulta DNI/RUC'),
            ('currency_rate', 'Tipo de cambio'),
            ('afp_rates', 'Tasas AFP'),
        ],
        required=True,
        default='vat_document',
    )
    token = fields.Char()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _provider_operation_unique = models.Constraint(
        'unique(provider, operation)',
        'Ya existe una credencial para este proveedor y operacion.',
    )

    def init(self):
        self.env.cr.execute(
            """
            UPDATE api_data_provider_credential
               SET provider = 'migo'
             WHERE provider = 'apimigo'
            """
        )

    @api.model
    def _provider_requires_token(self, provider):
        return provider not in FREE_PROVIDERS

    @api.model
    def _normalize_operation(self, operation):
        return {
            'vat': 'vat_document',
            'currency': 'currency_rate',
            'afp': 'afp_rates',
        }.get(operation, operation)

    @api.depends('provider', 'operation')
    def _compute_name(self):
        provider_labels = dict(self._fields['provider'].selection)
        operation_labels = dict(self._fields['operation'].selection)
        for credential in self:
            credential.name = '%s - %s' % (
                operation_labels.get(credential.operation, credential.operation or ''),
                provider_labels.get(credential.provider, credential.provider or ''),
            )

    @api.model
    def _legacy_param_keys(self, operation):
        operation = self._normalize_operation(operation)
        return {
            'vat_document': [
                'api_data_provider.vat_token',
                'api.access_token',
                'api.access_token_first',
            ],
            'currency_rate': [
                'api_data_provider.currency_token',
                'api.access_token',
                'api.access_token_first',
            ],
            'afp_rates': [
                'api_data_provider.afp_token',
                'api.access_token',
                'api.access_token_first',
            ],
        }.get(operation, [])

    @api.model
    def _legacy_provider(self, operation):
        operation = self._normalize_operation(operation)
        params = self.env['ir.config_parameter'].sudo()
        provider_keys = {
            'vat_document': ('api_data_provider.vat_provider', 'migo'),
            'currency_rate': ('api_data_provider.currency_provider', 'migo'),
            'afp_rates': ('api_data_provider.afp_provider', 'migo'),
        }
        key, default = provider_keys.get(operation, (False, False))
        return (params.get_str(key) if key else False) or default

    @api.model
    def _get_credentials(self, operation, raise_if_missing=False):
        operation = self._normalize_operation(operation)
        credentials = self.sudo().search([
            ('operation', '=', operation),
            ('active', '=', True),
        ], order='sequence, id')
        for credential in credentials:
            if credential.token:
                return credential.provider, credential.token
            if not self._provider_requires_token(credential.provider):
                return credential.provider, False

        params = self.env['ir.config_parameter'].sudo()
        for key in self._legacy_param_keys(operation):
            token = params.get_str(key)
            if token:
                return self._legacy_provider(operation), token

        if raise_if_missing:
            raise UserError(self.env._("Configure una credencial activa para la operacion solicitada."))
        return False, False

    @api.model
    def _upsert_compat_credential(self, operation, provider, token):
        operation = self._normalize_operation(operation)
        credential = self.search([
            ('operation', '=', operation),
            ('provider', '=', provider),
        ], limit=1)
        vals = {
            'operation': operation,
            'provider': provider,
            'token': token,
            'active': True,
        }
        if credential:
            credential.write(vals)
        else:
            credential.create(vals)

    @api.model
    def _get_tokens(self, operation, raise_if_missing=False):
        operation = self._normalize_operation(operation)
        credentials = self.sudo().search([
            ('operation', '=', operation),
            ('active', '=', True),
            ('token', '!=', False),
        ], order='sequence, id')

        provider = credentials[:1].provider if credentials else self._legacy_provider(operation)
        tokens = []
        for credential in credentials:
            if credential.token not in tokens:
                tokens.append(credential.token)

        params = self.env['ir.config_parameter'].sudo()
        for key in self._legacy_param_keys(operation):
            token = params.get_str(key)
            if token and token not in tokens:
                tokens.append(token)

        if not tokens and raise_if_missing:
            raise UserError(self.env._("Configure una credencial activa para la operacion solicitada."))
        return provider, tokens
