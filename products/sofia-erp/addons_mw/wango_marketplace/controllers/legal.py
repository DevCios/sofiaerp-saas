# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request

class WangoLegalController(http.Controller):

    @http.route(['/libro-de-reclamaciones'], type='http', auth="public", website=True, methods=['GET', 'POST'], csrf=True)
    def libro_reclamaciones(self, **post):
        if request.httprequest.method == 'POST':
            consumer_name = post.get('consumer_name')
            doc_type = post.get('doc_type', 'dni')
            doc_number = post.get('doc_number')
            consumer_email = post.get('consumer_email')
            consumer_phone = post.get('consumer_phone')
            consumer_address = post.get('consumer_address')
            is_minor = bool(post.get('is_minor'))
            parent_name = post.get('parent_name') or ''
            
            contracted_good = post.get('contracted_good', 'product')
            try:
                claimed_amount = max(0.0, float(post.get('claimed_amount') or 0.0))
            except (ValueError, TypeError):
                claimed_amount = 0.0
            order_ref = post.get('order_ref') or ''
            good_description = post.get('good_description') or ''

            claim_type = post.get('claim_type', 'claim')
            detail = post.get('detail') or ''
            consumer_request = post.get('consumer_request') or ''

            if not (consumer_name and doc_number and consumer_email and consumer_phone and detail and consumer_request):
                return request.render("wango_marketplace.claim_form_template", {
                    'error_msg': 'Por favor, completa todos los campos obligatorios del formulario.',
                    'post': post
                })

            claim_vals = {
                'consumer_name': consumer_name,
                'doc_type': doc_type,
                'doc_number': doc_number,
                'consumer_email': consumer_email,
                'consumer_phone': consumer_phone,
                'consumer_address': consumer_address,
                'is_minor': is_minor,
                'parent_name': parent_name,
                'contracted_good': contracted_good,
                'claimed_amount': claimed_amount,
                'order_ref': order_ref,
                'good_description': good_description,
                'claim_type': claim_type,
                'detail': detail,
                'consumer_request': consumer_request,
            }
            claim = request.env['wango.claim'].sudo().create(claim_vals)

            # Enviar constancia por correo electrónico al consumidor (Exigencia INDECOPI)
            try:
                base_url = (request.env['ir.config_parameter'].sudo().search([('key', '=', 'web.base.url')], limit=1).value or 'https://mercadowanka.com')
                email_body = f"""
                <div style="font-family:sans-serif;max-width:600px;margin:auto;border:1px solid #e0e0e0;border-radius:10px;padding:25px;">
                    <h2 style="color:#00a650;margin-top:0;">Mercado Wanka - Hoja de Reclamación</h2>
                    <p>Estimado(a) <b>{claim.consumer_name}</b>,</p>
                    <p>Hemos recibido satisfactoriamente su comunicación a través de nuestro <b>Libro de Reclamaciones Virtual</b> conforme al D.S. Nº 011-2011-PCM.</p>
                    <div style="background:#f8f9fa;padding:15px;border-radius:8px;margin:15px 0;">
                        <p style="margin:4px 0;"><b>Nº de Hoja de Reclamación:</b> <span style="font-size:16px;color:#d63031;font-weight:bold;">{claim.name}</span></p>
                        <p style="margin:4px 0;"><b>Fecha de Registro:</b> {claim.date.strftime('%d/%m/%Y %H:%M')}</p>
                        <p style="margin:4px 0;"><b>Tipo:</b> {'Reclamo' if claim.claim_type == 'claim' else 'Queja'}</p>
                        <p style="margin:4px 0;"><b>Bien:</b> {'Producto' if claim.contracted_good == 'product' else 'Servicio'} - S/ {claim.claimed_amount:.2f}</p>
                    </div>
                    <p>Conforme a la normativa de INDECOPI, daremos respuesta a su requerimiento en un plazo no mayor a <b>15 días hábiles</b> al correo proporcionado.</p>
                    <p>Puede visualizar e imprimir su hoja de reclamación en el siguiente enlace: <a href="{base_url}/libro-de-reclamaciones/hoja/{claim.name}">Ver Hoja de Reclamación</a></p>
                    <hr style="border:none;border-top:1px solid #eee;margin:20px 0;"/>
                    <p style="font-size:12px;color:#888;">Mercado Wanka - Red de Comercio Electrónico y Encomiendas de la Región Central.</p>
                </div>
                """
                request.env['mail.mail'].sudo().create({
                    'subject': f'Constancia de Hoja de Reclamación {claim.name} - Mercado Wanka',
                    'body_html': email_body,
                    'email_to': claim.consumer_email,
                }).send()
            except Exception:
                pass

            return request.render("wango_marketplace.claim_success_template", {
                'claim': claim
            })

        return request.render("wango_marketplace.claim_form_template", {})

    @http.route(['/libro-de-reclamaciones/hoja/<string:claim_code>'], type='http', auth="public", website=True)
    def imprimir_hoja_reclamacion(self, claim_code, **kw):
        claim = request.env['wango.claim'].sudo().search([('name', '=', claim_code)], limit=1)
        if not claim:
            return request.redirect('/libro-de-reclamaciones')
        return request.render("wango_marketplace.claim_sheet_print_template", {
            'claim': claim
        })

    @http.route(['/terminos-y-condiciones', '/terminos', '/legal/terminos'], type='http', auth="public", website=True)
    def terminos_condiciones(self, **kw):
        return request.render("wango_marketplace.terms_conditions_template", {})

    @http.route(['/politica-de-privacidad', '/privacidad'], type='http', auth="public", website=True)
    def politica_privacidad(self, **kw):
        return request.render("wango_marketplace.privacy_policy_template", {})

    @http.route(['/politica-de-devoluciones', '/devoluciones', '/ayuda'], type='http', auth="public", website=True)
    def politica_devoluciones(self, **kw):
        return request.render("wango_marketplace.return_policy_template", {})
