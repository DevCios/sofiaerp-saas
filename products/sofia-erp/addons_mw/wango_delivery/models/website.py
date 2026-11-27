# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request


class Website(models.Model):
    _inherit = 'website'

    def sale_get_order(self, force_create=False, code=False, update_pricelist=False, force_pricelist=False):
        """
        Adaptador de compatibilidad Odoo 20:
        En Odoo 20 website.sale_get_order() fue reemplazado por request.cart / _get_cart().
        Este método mantiene compatibilidad total con templates y controladores de Mercado Wanka.
        """
        order = self.env['sale.order']
        if hasattr(super(Website, self), 'sale_get_order'):
            order = super(Website, self).sale_get_order(
                force_create=force_create,
                code=code,
                update_pricelist=update_pricelist,
                force_pricelist=force_pricelist,
            )
        elif request:
            if hasattr(request, 'cart') and request.cart:
                order = request.cart
            elif hasattr(self, '_get_cart'):
                order = self._get_cart()
            else:
                sale_order_id = request.session.get('sale_order_id')
                if sale_order_id:
                    cand = self.env['sale.order'].sudo().browse(sale_order_id)
                    if cand.exists() and cand.state == 'draft':
                        order = cand
        if order and hasattr(order, '_check_delivery_restrictions'):
            try:
                order._check_delivery_restrictions()
            except Exception:
                pass
        return order
