# -*- coding: utf-8 -*-

from odoo import models

class Website(models.Model):
    _inherit = 'website'

    def sale_get_order(self, force_create=False, code=False, update_pricelist=False, force_pricelist=False):
        order = super(Website, self).sale_get_order(
            force_create=force_create,
            code=code,
            update_pricelist=update_pricelist,
            force_pricelist=force_pricelist
        )
        if order:
            # Recalcular restricciones y limpiar si es necesario
            order._check_delivery_restrictions()
        return order
