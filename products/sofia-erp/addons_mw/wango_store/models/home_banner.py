# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WangoHomeBanner(models.Model):
    _name = 'wango.home.banner'
    _description = 'WanGO Banners de Portada'
    _order = 'sequence asc, id desc'

    name = fields.Char(string='Título / Referencia', required=True)
    subtitle = fields.Char(string='Subtítulo promocional')
    image = fields.Binary(string='Imagen Desktop (Recomendado 1600x420 px)', required=True, attachment=True)
    image_mobile = fields.Binary(string='Imagen Mobile (Opcional 800x600 px)', attachment=True)
    url_redirect = fields.Char(string='URL de Redirección', default='/shop', required=True)
    sequence = fields.Integer(string='Orden', default=10)
    is_active = fields.Boolean(string='Activo', default=True)
    date_start = fields.Datetime(string='Fecha Inicio')
    date_end = fields.Datetime(string='Fecha Fin')
    website_id = fields.Many2one('website', string='Sitio Web', ondelete='cascade')

    @api.model
    def get_active_banners(self, website_id=None):
        """Retorna los banners activos y vigentes para el sitio web actual."""
        domain = [('is_active', '=', True)]
        
        # Manejo ultra seguro de website_id
        target_website = website_id
        if not target_website and hasattr(self.env, 'website') and self.env.website:
            target_website = self.env.website.id
        elif hasattr(target_website, 'id'):
            target_website = target_website.id
            
        if target_website:
            domain += ['|', ('website_id', '=', False), ('website_id', '=', target_website)]
            
        banners = self.search(domain, order='sequence asc, id desc')
        
        # Filtro de vigencia de fechas en memoria (100% seguro contra timezone o NULLs)
        now = fields.Datetime.now()
        return banners.filtered(
            lambda b: (not b.date_start or b.date_start <= now) and (not b.date_end or b.date_end >= now)
        )
