from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    exchange_rate = fields.Float(
        string='Tipo de Cambio',
        digits=(16, 6),
        compute='_compute_currency_rate',
        store=True,
        readonly=False
    )

    @api.depends('currency_id', 'company_id', 'date', 'invoice_date')
    def _compute_currency_rate(self):
        """Calcula el tipo de cambio del día; si no existe en Odoo, consulta Migo."""
        for move in self:
            move.exchange_rate = move._get_actual_currency_rate()

    def _get_actual_currency_rate(self):
        """Obtiene el tipo de cambio del día usando la función nativa de Odoo."""
        if not self.currency_id or self.currency_id == self.company_currency_id:
            return 1.0

        fecha = self.date or self.invoice_date or fields.Date.context_today(self)

        rate = self.env['res.currency']._get_conversion_rate(
            self.currency_id,
            self.company_currency_id,
            self.company_id,
            fecha
        )
        return rate
