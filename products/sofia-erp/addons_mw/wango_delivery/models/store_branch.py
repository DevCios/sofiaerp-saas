# -*- coding: utf-8 -*-

from odoo import models, fields, api

class DeliveryStoreBranch(models.Model):
    _name = 'delivery.store.branch'
    _description = 'Puntos de Retiro y Agentes Wanka'
    _order = 'point_type asc, name asc'

    name = fields.Char(string='Nombre del Punto', required=True, help='Ej: Agente Wanka Pilcomayo, o Tienda Central Huancayo')
    point_type = fields.Selection([
        ('agent', 'Agente Wanka (Red de Retiro Oficial - Multivendedor)'),
        ('seller_store', 'Local Propio de Vendedor (Solo sus productos)'),
    ], string='Tipo de Punto de Retiro', default='agent', required=True)
    
    seller_id = fields.Many2one(
        'res.partner',
        string='Vendedor Propietario',
        help='Si es un local propio, selecciona al vendedor dueño de este local.',
        
    )
    
    reference = fields.Char(
        string='Referencia / Negocio Aliado',
        help='Ej: Bodega Don Pepe, frente a la comisaría o Farmacia San Pedro'
    )
    
    address = fields.Char(string='Dirección Física', required=True)
    department_id = fields.Many2one('res.country.state', string='Departamento', required=True, domain="[('country_id.code', '=', 'PE')]")
    province_id = fields.Many2one('wango.province', string='Provincia', required=True, domain="[('state_id', '=', department_id)]")
    district_id = fields.Many2one('wango.district', string='Distrito', required=True, domain="[('province_id', '=', province_id)]")
    latitude = fields.Float(string='Latitud', digits=(10, 7))
    longitude = fields.Float(string='Longitud', digits=(10, 7))
    warehouse_id = fields.Many2one('stock.warehouse', string='Almacén Odoo (Opcional)', required=False, help='Opcional. Si se deja vacío, el punto asume disponibilidad si el producto está a la venta.')
    partner_id = fields.Many2one('res.partner', string='Contacto / Encargado del Punto')
    phone = fields.Char(string='Teléfono de Contacto')
    schedule = fields.Char(string='Horario de Atención', default='Lunes a Sábado 8:00 AM - 8:00 PM')
    active = fields.Boolean(string='Activo', default=True)

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id:
            if self.province_id and self.province_id.state_id != self.department_id:
                self.province_id = False
                self.district_id = False
        else:
            self.province_id = False
            self.district_id = False

    @api.onchange('province_id')
    def _onchange_province_id(self):
        if self.province_id:
            if self.district_id and self.district_id.province_id != self.province_id:
                self.district_id = False
        else:
            self.district_id = False
