# -*- coding: utf-8 -*-

from odoo import models, fields

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    wango_delivery_type = fields.Selection([
        ('store_pickup', 'Retiro en tienda'),
        ('home_delivery', 'Despacho a domicilio'),
        ('agency_shipping', 'Recibir en agencia')
    ], string='Tipo de Entrega WanGO', help='Vincular este método de envío nativo de Odoo con la interfaz del checkout de WanGO.')

    store_branch_id = fields.Many2one(
        'delivery.store.branch',
        string='Sucursal de Retiro',
        help='Si es Retiro en Tienda, selecciona qué tienda física se asociará a este método.'
    )
    agency_id = fields.Many2one(
        'wango.agency',
        string='Agencia de Envío',
        help='Si es Envío por Agencia, selecciona qué agencia de transporte se asociará a este método.'
    )

    def _prepare_delivery_line_vals(self, order, price):
        vals = super(DeliveryCarrier, self)._prepare_delivery_line_vals(order, price)
        # Asegurar que currency_id esté poblado para evitar fallos de campos obligatorios en localizaciones/EDI
        if order and order.currency_id:
            vals['currency_id'] = order.currency_id.id
        return vals
