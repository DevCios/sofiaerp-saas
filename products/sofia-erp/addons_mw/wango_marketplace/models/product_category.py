# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = 'product.category'

    marketplace_commission_rate = fields.Float(
        string="Comisión Mercado Wanka (%)",
        default=5.0,
        help="Porcentaje variable sobre el precio total de venta que Mercado Wanka cobra al vendedor (por defecto 5%).",
    )
