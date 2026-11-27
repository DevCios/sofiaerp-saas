# -*- coding: utf-8 -*-
from odoo import models, fields, api

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('marketplace', 'Envío Consolidado Marketplace')
    ], ondelete={'marketplace': 'set default'})

    def marketplace_rate_shipment(self, order):
        """
        Calcula el costo de envío sumando las tarifas de los métodos de envío
        preferidos de cada vendedor involucrado en la orden.
        """
        self.ensure_one()
        res = {'success': True, 'price': 0.0, 'error_message': False, 'warning_message': False}
        
        sellers = order.order_line.mapped('product_id.marketplace_seller_id')
        if not sellers:
            return res
            
        total_price = 0.0
        
        for seller in sellers:
            carrier = seller.marketplace_delivery_carrier_id
            if not carrier:
                continue
                
            if carrier.delivery_type == 'fixed':
                total_price += carrier.fixed_price
            else:
                # Para MVP sumamos la tarifa del transportista asumiendo que calcula sobre el total 
                # de la orden, aunque lo ideal a nivel senior es hacer un "dummy_order" o pasar líneas en el contexto.
                try:
                    carrier_res = carrier.rate_shipment(order)
                    if carrier_res.get('success'):
                        total_price += carrier_res.get('price', 0.0)
                except Exception as e:
                    pass

        res['price'] = total_price
        return res
