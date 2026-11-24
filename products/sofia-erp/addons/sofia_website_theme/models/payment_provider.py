# -*- coding: utf-8 -*-
from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    mercado_pago_access_token = fields.Char(
        string="Access Token de Mercado Pago",
        help="Token de acceso directo de producción (APP_USR-...) o de prueba (TEST-...).",
        copy=False,
    )
