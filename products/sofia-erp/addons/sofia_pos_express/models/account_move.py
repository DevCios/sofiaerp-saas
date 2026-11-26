# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    pos_express_session_id = fields.Many2one(
        'pos.express.session',
        string='Turno POS Express',
        copy=False,
        index=True,
    )


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    pos_express_session_id = fields.Many2one(
        'pos.express.session',
        string='Turno POS Express',
        copy=False,
        index=True,
    )


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    pos_express_session_id = fields.Many2one(
        'pos.express.session',
        string='Turno POS Express',
        copy=False,
        index=True,
    )
