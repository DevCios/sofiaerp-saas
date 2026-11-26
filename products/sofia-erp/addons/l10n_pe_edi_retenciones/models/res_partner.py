# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    pe_is_retention = fields.Boolean(
        string='Agente de Retención IGV',
        copy=False,
        help='Indica si el cliente/contribuyente está designado por SUNAT como Agente de Retención del IGV (R.S. 037-2002).'
    )
    pe_retention_percent = fields.Float(
        string='Porcentaje de Retención (%)',
        default=3.0,
        copy=False,
        help='Tasa oficial de retención del IGV (3.0% según normativa SUNAT vigente).'
    )

    def CheckRetentionAgent(self, vat):
        """Extiende la consulta al padrón oficial de SUNAT de sofiaerp_pe_vat para
        sincronizar automáticamente el check pe_is_retention y su tasa del 3%."""
        res = super().CheckRetentionAgent(vat)
        if self.is_retention_agent:
            self.pe_is_retention = True
            if not self.pe_retention_percent:
                self.pe_retention_percent = 3.0
        else:
            self.pe_is_retention = False
        return res

    @api.onchange('is_retention_agent')
    def _onchange_sync_pe_is_retention(self):
        self.pe_is_retention = self.is_retention_agent
        if self.pe_is_retention and not self.pe_retention_percent:
            self.pe_retention_percent = 3.0
