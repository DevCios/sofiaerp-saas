from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def action_open_api_data_provider_credentials(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Credenciales de API',
            'res_model': 'api.data.provider.credential',
            'view_mode': 'list,form',
            'target': 'current',
        }
