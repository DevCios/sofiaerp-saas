# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class DeliveryInterstateCost(models.Model):
    _name = 'delivery.interstate.cost'
    _description = 'Costo de Transporte Inter-Departamental'
    _order = 'state_from_id, state_to_id'

    state_from_id = fields.Many2one(
        'res.country.state', 
        string='Departamento de Origen', 
        required=True, 
        domain="[('country_id.code', '=', 'PE')]"
    )
    state_to_id = fields.Many2one(
        'res.country.state', 
        string='Departamento de Destino', 
        required=True, 
        domain="[('country_id.code', '=', 'PE')]"
    )
    
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id')
    cost = fields.Monetary(string='Recargo de Envío (Interprovincial)', currency_field='currency_id', default=0.0, required=True)

    _sql_constraints = [
        ('state_from_to_uniq', 'unique(state_from_id, state_to_id, company_id)', 'Ya existe una regla de costo inter-departamental para esta ruta.')
    ]
