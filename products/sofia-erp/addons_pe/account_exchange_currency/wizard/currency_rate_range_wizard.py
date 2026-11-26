from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class CurrencyRateRangeWizard(models.TransientModel):
    _name = 'currency.rate.range.wizard'
    _description = 'Asistente para consultar tipo de cambio SUNAT por rango de fechas'

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Moneda',
        required=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(
        string='Fecha inicial',
        required=True,
    )
    date_to = fields.Date(
        string='Fecha final',
        required=True,
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            today = fields.Date.context_today(wizard)
            if wizard.date_from and wizard.date_from > today:
                raise ValidationError(self.env._("La fecha inicial no puede ser futura."))
            if wizard.date_to and wizard.date_to > today:
                raise ValidationError(self.env._("La fecha final no puede ser futura."))
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(self.env._("La fecha inicial no puede ser mayor que la fecha final."))
            if wizard.date_from and wizard.date_to:
                delta = (wizard.date_to - wizard.date_from).days
                if delta > 365:
                    raise ValidationError(self.env._("El rango no puede superar los 365 días."))

    def action_apply(self):
        self.ensure_one()
        if self.currency_id.name != 'USD':
            raise UserError(self.env._("El histórico SUNAT solo está disponible para USD."))
        if not self.date_from or not self.date_to:
            raise UserError(self.env._("Indique un rango de fechas válido."))

        created, updated, skipped = self.env['res.currency.rate'].sync_range_from_migo(
            currency=self.currency_id,
            date_from=self.date_from,
            date_to=self.date_to,
            company=self.company_id,
        )

        total = created + updated
        message_parts = [self.env._("%(n)d tasa(s) procesada(s).", n=total)]
        if created:
            message_parts.append(self.env._("%(n)d creada(s).", n=created))
        if updated:
            message_parts.append(self.env._("%(n)d actualizada(s).", n=updated))
        if skipped:
            message_parts.append(self.env._("%(n)d sin cambio (día no hábil).", n=skipped))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._("Histórico sincronizado"),
                'message': " ".join(message_parts),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
