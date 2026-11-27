# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class WangoStoreController(http.Controller):

    @http.route('/wango_store/recently_viewed', type='jsonrpc', auth='public', website=True)
    def get_recently_viewed(self, product_ids=None):
        """Retorna el HTML renderizado de los productos vistos recientemente con fallback a destacados."""
        product_obj = request.env['product.template'].sudo()
        website = getattr(request, 'website', None) or request.env['website'].get_current_website()
        is_fallback = False

        products = product_obj.browse()
        if product_ids and isinstance(product_ids, list):
            # Filtrar solo IDs válidos enteros
            clean_ids = [int(p) for p in product_ids if str(p).isdigit()]
            if clean_ids:
                # Mantener el orden del historial del usuario
                found = product_obj.browse(clean_ids).filtered(lambda p: p.website_published)
                # Ordenar según el orden en clean_ids
                products = found.sorted(key=lambda p: clean_ids.index(p.id) if p.id in clean_ids else 999)

        if not products:
            is_fallback = True
            products = product_obj.get_wango_featured_products(website=website, limit=6)

        # Renderizar la plantilla QWeb parcial
        html = request.env['ir.ui.view']._render_template(
            'wango_store.recently_viewed_items_template',
            {
                'products': products,
                'website': website,
                'is_fallback': is_fallback,
            }
        )

        return {
            'html': html,
            'is_fallback': is_fallback,
            'count': len(products),
        }

    @http.route('/shop/product/submit_review', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def submit_product_review(self, **post):
        """Permite que solo clientes que hayan comprado el producto envíen una reseña.
        Queda SIEMPRE en estado 'pending' (sin aprobación) y no publicada hasta revisión del admin.
        """
        product_tmpl_id = int(post.get('product_tmpl_id', 0))
        product = request.env['product.template'].sudo().browse(product_tmpl_id)
        if not product.exists():
            return request.redirect('/shop')

        partner = request.env.user.partner_id
        can_review, reason = product.can_user_review(partner=partner)
        if not can_review:
            return request.redirect(f'/shop/product/{product.id}?review_error={reason}#wango_product_reviews_section')

        rating = str(post.get('rating', '5'))
        if rating not in ['1', '2', '3', '4', '5']:
            rating = '5'

        title = (post.get('title') or 'Excelente producto').strip()
        content = (post.get('content') or '').strip()
        if not content:
            return request.redirect(f'/shop/product/{product.id}?review_error=empty_content#wango_product_reviews_section')

        author_location = (partner.city or (partner.state_id and partner.state_id.name) or 'Huancayo')

        # Registrar la reseña pendiente de aprobación por el admin
        request.env['wango.product.review'].sudo().create({
            'product_tmpl_id': product.id,
            'partner_id': partner.id,
            'author_name': partner.name or 'Comprador verificado',
            'author_location': author_location,
            'rating': rating,
            'title': title,
            'content': content,
            'date_display': 'Reciente',
            'is_verified_purchase': True,
            'is_published': False,  # QUEDA SIN APROBACIÓN POR DEFECTO
            'state': 'pending',     # PENDIENTE DE REVISIÓN
            'sequence': 10,
        })

        return request.redirect(f'/shop/product/{product.id}?review_submitted=1#wango_product_reviews_section')
