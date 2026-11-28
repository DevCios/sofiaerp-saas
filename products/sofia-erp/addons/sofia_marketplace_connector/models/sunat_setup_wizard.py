# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SofiaSunatSetupWizardMarketplace(models.TransientModel):
    _inherit = 'sofia.sunat.setup.wizard'

    enable_mercado_wanka = fields.Boolean(
        string='Activar mi Tienda en Mercado Wanka (mercadowanka.com)',
        default=True,
        help='Habilitado automáticamente con cualquier plan pagado de SOFIA ERP. Comisión: 5% del valor total + S/ 0.50 por uso de plataforma.',
    )
    mw_store_name = fields.Char(
        string='Nombre Comercial de tu Tienda',
        help='Cómo verán tu tienda los compradores en Mercado Wanka.',
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        company = self.env.company
        vals.update({
            'enable_mercado_wanka': bool(company.mw_store_enabled or True),
            'mw_store_name': company.mw_store_name or company.name or '',
        })
        return vals

    def action_apply_configuration(self):
        res = super().action_apply_configuration()
        for wiz in self:
            if wiz.enable_mercado_wanka:
                try:
                    wiz.company_id.sudo().action_register_mercado_wanka_store(
                        store_name=wiz.mw_store_name or wiz.company_name
                    )
                except Exception as exc:
                    _logger.warning("Mercado Wanka: no se pudo registrar tienda desde Wizard (se podrá reintentar al publicar): %s", exc)
        return res
