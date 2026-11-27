# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class DeliveryCoverage(models.Model):
    _name = 'delivery.coverage'
    _description = 'Cobertura de Delivery a Domicilio'
    _order = 'department_id, province_id, district_id'

    department_id = fields.Many2one('res.country.state', string='Departamento', required=True, domain="[('country_id.code', '=', 'PE')]")
    province_id = fields.Many2one('wango.province', string='Provincia', domain="[('state_id', '=', department_id)]")
    district_id = fields.Many2one('wango.district', string='Distrito', domain="[('province_id', '=', province_id)]")
    excluded_district_ids = fields.Many2many(
        'wango.district',
        'delivery_coverage_excluded_district_rel',
        'coverage_id',
        'district_id',
        string='Distritos Excluidos (Sin Cobertura)',
        domain="[('province_id', '=', province_id)]",
        help='Distritos de esta provincia a los que NO se realiza reparto a domicilio.'
    )
    active = fields.Boolean(string='Activo', default=True)
    time_min = fields.Integer(string='Tiempo Mínimo', default=1)
    time_max = fields.Integer(string='Tiempo Máximo', default=2)
    time_unit = fields.Selection([
        ('hours', 'Horas'),
        ('days', 'Días')
    ], string='Unidad de Tiempo', default='days', required=True)
    
    origin_department_id = fields.Many2one('res.country.state', string='Departamento de Origen', domain="[('country_id.code', '=', 'PE')]")
    
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id')
    cost = fields.Monetary(string='Costo de Envío', currency_field='currency_id', default=0.0, required=True)
    free_shipping_min = fields.Monetary(string='Monto Mínimo Envío Gratis', currency_field='currency_id', default=0.0)

    _sql_constraints = [
        ('district_origin_uniq', 'unique(department_id, province_id, district_id, company_id, origin_department_id)', 'Ya existe una regla de cobertura para esta ubicación y origen.')
    ]

    @api.constrains('department_id', 'province_id', 'district_id', 'company_id', 'origin_department_id')
    def _check_unique_route_origin(self):
        for rec in self:
            domain = [
                ('id', '!=', rec.id),
                ('department_id', '=', rec.department_id.id),
                ('province_id', '=', rec.province_id.id if rec.province_id else False),
                ('district_id', '=', rec.district_id.id if rec.district_id else False),
                ('company_id', '=', rec.company_id.id),
                ('origin_department_id', '=', rec.origin_department_id.id if rec.origin_department_id else False)
            ]
            duplicate = self.search(domain, limit=1)
            if duplicate:
                loc_name = rec.district_id.name or rec.province_id.name or rec.department_id.name
                raise ValidationError(_("Ya existe una regla de cobertura para %s con el mismo origen.") % loc_name)

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id:
            if self.province_id and self.province_id.state_id != self.department_id:
                self.province_id = False
                self.district_id = False
                self.excluded_district_ids = [(5, 0, 0)]
        else:
            self.province_id = False
            self.district_id = False
            self.excluded_district_ids = [(5, 0, 0)]

    @api.onchange('province_id')
    def _onchange_province_id(self):
        if self.province_id:
            if self.district_id and self.district_id.province_id != self.province_id:
                self.district_id = False
            if self.excluded_district_ids:
                self.excluded_district_ids = self.excluded_district_ids.filtered(lambda d: d.province_id == self.province_id)
        else:
            self.district_id = False
            self.excluded_district_ids = [(5, 0, 0)]

    @api.onchange('district_id')
    def _onchange_district_id(self):
        if self.district_id:
            self.excluded_district_ids = [(5, 0, 0)]


