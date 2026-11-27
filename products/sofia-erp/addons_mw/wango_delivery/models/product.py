# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    wango_only_pickup = fields.Boolean(
        string='Solo Retiro en Tienda',
        help='Si está marcado, este producto no puede ser entregado a domicilio ni enviado por agencia.',
        default=False
    )
    wango_no_agency = fields.Boolean(
        string='Excluir de Envío por Agencia',
        help='Si está marcado, este producto no se puede enviar a través de agencias de transporte.',
        default=False
    )
    wango_no_home_delivery = fields.Boolean(
        string='Excluir de Entrega a Domicilio',
        help='Si está marcado, este producto no se puede entregar a domicilio.',
        default=False
    )
    
    wango_custom_home_time = fields.Char(
        string='Tiempo de Despacho (Personalizado)',
        help='Opcional. Ej: "Llega en 2 a 5 días laborables". Si se llena, se ignorará el cálculo de tiempo automático por distrito para este producto.'
    )
    
    wango_custom_pickup_time = fields.Char(
        string='Tiempo de Retiro (Personalizado)',
        help='Opcional. Ej: "Disponible en 2 horas" o "A partir del viernes". Si se llena, se mostrará esto en lugar del tiempo general de la tienda.'
    )

    wango_origin_department_id = fields.Many2one(
        'res.country.state',
        string='Departamento de Origen',
        domain="[('country_id.code', '=', 'PE')]"
    )
    wango_origin_province_id = fields.Many2one(
        'wango.province',
        string='Provincia de Origen',
        domain="[('state_id', '=', wango_origin_department_id)]"
    )
    wango_origin_district_id = fields.Many2one(
        'wango.district',
        string='Distrito de Origen',
        domain="[('province_id', '=', wango_origin_province_id)]"
    )

    @api.onchange('wango_origin_department_id')
    def _onchange_wango_origin_department_id(self):
        if self.wango_origin_department_id:
            if self.wango_origin_province_id and self.wango_origin_province_id.state_id != self.wango_origin_department_id:
                self.wango_origin_province_id = False
                self.wango_origin_district_id = False
        else:
            self.wango_origin_province_id = False
            self.wango_origin_district_id = False

    @api.onchange('wango_origin_province_id')
    def _onchange_wango_origin_province_id(self):
        if self.wango_origin_province_id:
            if self.wango_origin_district_id and self.wango_origin_district_id.province_id != self.wango_origin_province_id:
                self.wango_origin_district_id = False
        else:
            self.wango_origin_district_id = False
