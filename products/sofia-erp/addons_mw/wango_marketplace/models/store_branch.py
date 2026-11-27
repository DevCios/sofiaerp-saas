# -*- coding: utf-8 -*-
from odoo import models, api

class DeliveryStoreBranch(models.Model):
    _inherit = 'delivery.store.branch'

    @api.model
    def default_get(self, fields_list):
        res = super(DeliveryStoreBranch, self).default_get(fields_list)
        # Si el usuario es un vendedor, autocompletar su partner_id y un warehouse genérico
        if self.env.user.has_group('wango_marketplace.group_marketplace_seller') and not self.env.user.has_group('wango_marketplace.group_marketplace_manager'):
            res['partner_id'] = self.env.user.partner_id.id
            
            # Buscar el almacén principal para evitar errores de required=True
            warehouse = self.env['stock.warehouse'].search([], limit=1)
            if warehouse:
                res['warehouse_id'] = warehouse.id
        return res
