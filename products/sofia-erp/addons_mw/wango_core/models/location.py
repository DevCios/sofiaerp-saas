from odoo import models, fields, api

class WangoCity(models.Model):
    _name = 'wango.city'
    _inherit = ['wango.base.mixin']
    _description = 'Ciudad WanGO'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True)
    state_id = fields.Many2one('res.country.state', string='Departamento / Estado', required=True)
    country_id = fields.Many2one('res.country', related='state_id.country_id', store=True)

    # Cities should be shared across companies usually, so we make company_id optional
    company_id = fields.Many2one('res.company', string='Company', required=False, default=False)


class WangoAgency(models.Model):
    _name = 'wango.agency'
    _inherit = ['wango.base.mixin']
    _description = 'Agencia WanGO'

    name = fields.Char(string='Nombre', required=True)
    city_id = fields.Many2one('wango.city', string='Ciudad', required=True)
    address = fields.Char(string='Dirección')
    latitude = fields.Float(string='Latitud')
    longitude = fields.Float(string='Longitud')
    phone = fields.Char(string='Teléfono')

class WangoPoint(models.Model):
    _name = 'wango.point'
    _inherit = ['wango.base.mixin']
    _description = 'Punto de Interés'

    name = fields.Char(string='Nombre', required=True)
    city_id = fields.Many2one('wango.city', string='Ciudad', required=True)
    type = fields.Selection([
        ('pickup', 'Recogida'),
        ('dropoff', 'Destino'),
        ('both', 'Ambos')
    ], string='Tipo', default='both', required=True)
    latitude = fields.Float(string='Latitud')
    longitude = fields.Float(string='Longitud')
