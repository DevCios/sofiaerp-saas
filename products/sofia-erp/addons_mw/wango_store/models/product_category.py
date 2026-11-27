# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    is_featured_home = fields.Boolean(
        string='Mostrar en Portada', 
        default=False,
        help='Marcar para mostrar esta categoría en la cuadrícula de categorías de la portada (estilo Mercado Libre).'
    )
    home_sequence = fields.Integer(
        string='Orden en Portada', 
        default=10,
        help='Orden en el que se listará en la cuadrícula de la portada.'
    )

    @api.model
    def get_wango_home_categories(self, website=None, limit=24):
        """Retorna las categorías destacadas para la portada con fallback automático."""
        domain = [('is_featured_home', '=', True)]
        if website:
            domain += [('website_id', 'in', (False, website.id))]
            
        cats = self.search(domain, order='home_sequence asc, id asc', limit=limit)
        
        # Fallback: Si no hay ninguna marcada como destacada, traer las primeras categorías públicas existentes
        if not cats:
            domain_fallback = [('website_id', 'in', (False, website.id))] if website else []
            cats = self.search(domain_fallback, order='sequence asc, id asc', limit=limit)
            
        return cats
