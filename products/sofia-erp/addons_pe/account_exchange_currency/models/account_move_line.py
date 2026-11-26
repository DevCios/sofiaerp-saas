from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id', 'price_unit', 'quantity', 'move_id.exchange_rate', 'move_id.currency_id')
    def _onchange_convert_amount_currency(self):
        for line in self:
            move = line.move_id
            if not move or not move.exchange_rate or not move.currency_id:
                continue
            if move.currency_id.name != 'PEN':
                rate = move.exchange_rate

                amount_currency = line.amount_currency
                if not amount_currency:
                    amount_currency = (
                        line.price_subtotal
                        if line.price_subtotal
                        else line.price_unit * line.quantity
                    )

                if amount_currency:
                    amount_pen = abs(amount_currency) * rate

                    if amount_currency > 0:
                        line.debit = amount_pen
                        line.credit = 0.0
                    else:
                        line.debit = 0.0
                        line.credit = amount_pen

                else:
                    line.debit = line.credit = 0.0

            else:
                base_amount = (
                    line.price_subtotal
                    if line.price_subtotal
                    else line.price_unit * line.quantity
                )
                line.debit = base_amount if base_amount > 0 else 0.0
                line.credit = abs(base_amount) if base_amount < 0 else 0.0
