# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WangoHomeCard(models.Model):
    _name = 'wango.home.card'
    _description = 'WanGO Tarjetas Rápidas de Portada'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Título', required=True)
    subtitle = fields.Char(string='Descripción Corta', required=True)
    icon_image = fields.Binary(string='Ícono Ilustrado (PNG/SVG)', attachment=True)
    icon_class = fields.Char(string='Clase FontAwesome de respaldo', default='fa fa-star')
    button_text = fields.Char(string='Texto del Botón', default='Ver más', required=True)
    url_redirect = fields.Char(string='URL de Enlace', default='/shop')
    
    card_type = fields.Selection([
        ('login', 'Ingresa a tu cuenta / Perfil'),
        ('location', 'Ingresa tu ubicación (Abre Modal GPS)'),
        ('favorites', 'Producto favorito / Deseos'),
        ('free_shipping', 'Envío gratis por compras > S/ 50'),
        ('best_sellers', 'Producto más vendido'),
        ('stores', 'Tiendas oficiales'),
        ('categories', 'Todas las categorías'),
        ('recently_viewed', 'Visto recientemente'),
        ('custom', 'Personalizado'),
    ], string='Tipo de Tarjeta', default='custom', required=True)
    
    sequence = fields.Integer(string='Orden', default=10)
    is_active = fields.Boolean(string='Activo', default=True)
    website_id = fields.Many2one('website', string='Sitio Web', ondelete='cascade')

    @api.model
    def get_active_cards(self, website_id=None):
        domain = [('is_active', '=', True)]
        target_website = website_id
        if not target_website and hasattr(self.env, 'website') and self.env.website:
            target_website = self.env.website.id
        elif hasattr(target_website, 'id'):
            target_website = target_website.id
            
        if target_website:
            domain += ['|', ('website_id', '=', False), ('website_id', '=', target_website)]
        return self.search(domain, order='sequence asc, id asc')
