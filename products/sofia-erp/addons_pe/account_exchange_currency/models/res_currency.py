from odoo import models
from odoo.exceptions import UserError


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def action_sync_exchange_rate_from_provider(self):
        self.ensure_one()

        provider, token = self.env['api.data.provider.credential']._get_credentials('currency_rate')

        if not provider:
            raise UserError(self.env._("Configure una credencial activa para el tipo de cambio."))

        result = False
        if provider == 'migo':
            if not token:
                raise UserError(self.env._("Configure el token del proveedor antes de sincronizar el tipo de cambio."))
            result = self.env['res.currency.rate'].sync_from_migo(self, company=self.env.company)
        elif provider == 'apisnetpe_free':
            result = self.env['res.currency.rate'].sync_from_apisnetpe_free(self, company=self.env.company)
        else:
            raise UserError(self.env._("El proveedor configurado no tiene sincronizacion manual implementada."))

        if not result:
            raise UserError(self.env._("No se pudo sincronizar el tipo de cambio. Revise la configuracion o la respuesta del proveedor."))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._("Tipo de cambio actualizado"),
                'message': self.env._("La moneda %(currency)s fue sincronizada correctamente.", currency=self.name),
                'type': 'success',
                'sticky': False,
            },
        }
