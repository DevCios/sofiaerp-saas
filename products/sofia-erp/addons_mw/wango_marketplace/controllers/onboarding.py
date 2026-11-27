# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class MarketplaceOnboarding(http.Controller):

    @http.route('/vende-con-nosotros', type='http', auth="public", website=True)
    def seller_onboarding_form(self, **kw):
        """ Renderiza el formulario público para nuevos vendedores """
        return request.render('wango_marketplace.seller_onboarding_form_template', {})

    @http.route('/vende-con-nosotros/submit', type='http', auth="public", website=True, methods=['POST'])
    def seller_onboarding_submit(self, **post):
        """ Procesa el formulario y crea el vendedor en estado pendiente """
        if post:
            # Crear el partner como Vendedor Pendiente
            partner_vals = {
                'name': post.get('company_name') or post.get('name'),
                'email': post.get('email'),
                'phone': post.get('phone'),
                'vat': post.get('vat'),
                'company_type': 'company',
                'is_marketplace_seller': True,
                'marketplace_status': 'pending',
                'comment': f"Solicitud web.\nNombre Contacto: {post.get('name')}\nCategoría de interés: {post.get('category', 'No especificada')}"
            }
            # Se usa sudo() porque el usuario público no tiene permisos para crear partners vendedores
            request.env['res.partner'].sudo().create(partner_vals)
            
            return request.render('wango_marketplace.seller_onboarding_success_template', {})
        
        return request.redirect('/vende-con-nosotros')
