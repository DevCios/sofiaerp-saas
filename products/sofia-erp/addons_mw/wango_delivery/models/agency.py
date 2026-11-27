# -*- coding: utf-8 -*-

from odoo import models, fields, api

class WangoAgency(models.Model):
    _inherit = 'wango.agency'

    logo = fields.Binary(string='Logo de Agencia')
    active = fields.Boolean(string='Activo', default=True)
    tracking_url = fields.Char(string='URL de Seguimiento / Tracking')
    phone = fields.Char(string='Teléfono')


class DeliveryAgencyCost(models.Model):
    _name = 'delivery.agency.cost'
    _description = 'Tarifas de Agencia de Transporte'
    _order = 'agency_id, department_id, province_id, district_id, cost'

    agency_id = fields.Many2one('wango.agency', string='Agencia', required=True, ondelete='cascade')
    department_id = fields.Many2one('res.country.state', string='Departamento', domain="[('country_id.code', '=', 'PE')]")
    province_id = fields.Many2one('wango.province', string='Provincia', domain="[('state_id', '=', department_id)]")
    district_id = fields.Many2one('wango.district', string='Distrito', domain="[('province_id', '=', province_id)]")
    
    weight_max = fields.Float(string='Peso Máximo (kg)', default=999.0)
    volume_max = fields.Float(string='Volumen Máximo (m³)', default=999.0)
    
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id')
    cost = fields.Monetary(string='Costo de Envío', currency_field='currency_id', default=0.0, required=True)
    
    time_min = fields.Integer(string='Tiempo Mínimo (días)', default=2)
    time_max = fields.Integer(string='Tiempo Máximo (días)', default=3)

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
