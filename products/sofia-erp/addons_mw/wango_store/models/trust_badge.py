# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WangoHomeTrustBadge(models.Model):
    _name = 'wango.home.trust.badge'
    _description = 'WanGO Beneficios de Confianza'
    _order = 'sequence asc, id asc'

    title = fields.Char(string='Título', required=True)
    description = fields.Text(string='Descripción corta', required=True)
    icon_image = fields.Binary(string='Ícono personalizado (PNG/SVG)', attachment=True)
    icon_class = fields.Char(string='Ícono FontAwesome de respaldo', default='fa fa-shield')
    link_text = fields.Char(string='Texto del Enlace', help='Ejemplo: Cómo pagar con Yape')
    link_url = fields.Char(string='URL del Enlace', default='#')
    sequence = fields.Integer(string='Orden', default=10)
    is_active = fields.Boolean(string='Activo', default=True)
    website_id = fields.Many2one('website', string='Sitio Web', ondelete='cascade')

    @api.model
    def get_active_badges(self, website_id=None):
        domain = [('is_active', '=', True)]
        if website_id:
            domain += ['|', ('website_id', '=', False), ('website_id', '=', website_id)]
        return self.search(domain, order='sequence asc, id asc')
