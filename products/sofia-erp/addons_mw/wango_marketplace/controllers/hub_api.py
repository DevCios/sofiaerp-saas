# -*- coding: utf-8 -*-
import hmac
import json
import logging
import os
import secrets

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


def _json_response(payload, status=200):
    return Response(
        json.dumps(payload, ensure_ascii=False),
        status=status,
        mimetype='application/json',
    )


def _verify_internal_key():
    expected = os.getenv("INTERNAL_SERVICE_KEY", "sofia_internal_mesh_key_change_in_prod")
    provided = request.httprequest.headers.get("X-Internal-Service-Key", "")
    return bool(provided and expected and hmac.compare_digest(provided, expected))


class MercadoWankaHubAPI(http.Controller):
    """
    API Interna Hub de Mercado Wanka (tienda.sofiaerp.com) para el ecosistema SOFIA ERP:
    - Alta/actualización automática de tiendas desde el Wizard del tenant (plan pagado).
    - Publicación / despublicación de productos con 1 clic desde product.template.
    - Sincronización de stock en tiempo real.
    - Suspensión / reactivación automática según estado de suscripción SOFIA ERP.
    """

    @http.route('/api/marketplace/v1/sellers/upsert', type='http', auth='public', methods=['POST'], csrf=False)
    def upsert_seller(self, **kwargs):
        if not _verify_internal_key():
            return _json_response({'error': 'Unauthorized internal service key'}, status=403)

        try:
            data = json.loads(request.httprequest.data.decode('utf-8') or '{}')
        except Exception:
            return _json_response({'error': 'Invalid JSON payload'}, status=400)

        slug = (data.get('tenant_slug') or '').strip().lower()
        ruc = (data.get('ruc') or '').strip()
        name = (data.get('store_name') or data.get('company_name') or '').strip()
        if not slug or not name:
            return _json_response({'error': 'tenant_slug y store_name son obligatorios'}, status=400)

        Partner = request.env['res.partner'].sudo()
        seller = Partner.search([('sofia_tenant_slug', '=', slug)], limit=1)
        if not seller and ruc:
            seller = Partner.search([('vat', '=', ruc), ('is_marketplace_seller', '=', True)], limit=1)

        plan_paid = bool(data.get('plan_paid', True))
        vals = {
            'name': name,
            'vat': ruc or False,
            'email': data.get('email') or False,
            'phone': data.get('phone') or False,
            'street': data.get('street') or False,
            'zip': data.get('zip') or False,
            'is_company': True,
            'is_marketplace_seller': True,
            'marketplace_seller_status': 'approved' if plan_paid else 'pending',
            'sofia_tenant_slug': slug,
            'sofia_tenant_url': (data.get('tenant_url') or f'https://{slug}.sofiaerp.com').rstrip('/'),
            'sofia_subscription_active': plan_paid,
        }
        if data.get('logo_b64'):
            vals['image_1920'] = data['logo_b64']

        if seller:
            if not seller.sofia_seller_token:
                vals['sofia_seller_token'] = 'mw_' + secrets.token_urlsafe(24)
            seller.write(vals)
        else:
            vals['sofia_seller_token'] = 'mw_' + secrets.token_urlsafe(24)
            seller = Partner.create(vals)

        base_url = (
            request.env['ir.config_parameter'].sudo().search([('key', '=', 'web.base.url')], limit=1).value
            or 'https://tienda.sofiaerp.com'
        ).rstrip('/')

        return _json_response({
            'ok': True,
            'seller_id': seller.id,
            'seller_token': seller.sofia_seller_token,
            'status': seller.marketplace_seller_status,
            'store_url': f'{base_url}/shop?seller={seller.id}',
            'commission_policy': '5.0% del precio total + S/ 0.50 uso de plataforma',
        })

    @http.route('/api/marketplace/v1/products/sync', type='http', auth='public', methods=['POST'], csrf=False)
    def sync_product(self, **kwargs):
        if not _verify_internal_key():
            return _json_response({'error': 'Unauthorized'}, status=403)

        try:
            data = json.loads(request.httprequest.data.decode('utf-8') or '{}')
        except Exception:
            return _json_response({'error': 'Invalid JSON payload'}, status=400)

        slug = (data.get('tenant_slug') or '').strip().lower()
        remote_id = str(data.get('remote_product_id') or '').strip()
        if not slug or not remote_id:
            return _json_response({'error': 'tenant_slug y remote_product_id son obligatorios'}, status=400)

        seller = request.env['res.partner'].sudo().search([('sofia_tenant_slug', '=', slug)], limit=1)
        if not seller:
            return _json_response({'error': f'Tienda para tenant {slug} no registrada en Mercado Wanka.'}, status=404)

        if not seller.sofia_subscription_active:
            return _json_response({'error': 'Tu suscripción de SOFIA ERP no está activa. Renueva tu plan para publicar en Mercado Wanka.'}, status=402)

        Product = request.env['product.template'].sudo()
        prod = Product.search([
            ('marketplace_seller_id', '=', seller.id),
            ('sofia_remote_product_id', '=', remote_id),
        ], limit=1)

        publish = bool(data.get('publish', True))
        vals = {
            'name': (data.get('name') or 'Producto').strip(),
            'list_price': float(data.get('list_price') or 0.0),
            'default_code': data.get('default_code') or False,
            'description_sale': data.get('description_sale') or False,
            'weight': float(data.get('weight') or 0.0),
            'marketplace_seller_id': seller.id,
            'sofia_remote_product_id': remote_id,
            'marketplace_status': 'approved',
            'is_published': publish,
            'website_published': publish,
            'sale_ok': True,
        }
        if data.get('image_b64'):
            vals['image_1920'] = data['image_b64']

        # Categoría pública / interna por nombre si existe
        categ_name = (data.get('category_name') or '').strip()
        if categ_name:
            categ = request.env['product.category'].sudo().search([('name', 'ilike', categ_name)], limit=1)
            if categ:
                vals['categ_id'] = categ.id

        if prod:
            prod.write(vals)
        else:
            vals['type'] = 'consu'
            prod = Product.create(vals)

        # Actualizar stock disponible en almacén si viene qty_available
        if 'qty_available' in data and prod.product_variant_id:
            try:
                qty = max(0.0, float(data.get('qty_available') or 0.0))
                loc = request.env['stock.warehouse'].sudo().search([], limit=1).lot_stock_id
                if loc:
                    Quant = request.env['stock.quant'].sudo()
                    quant = Quant.search([
                        ('product_id', '=', prod.product_variant_id.id),
                        ('location_id', '=', loc.id),
                    ], limit=1)
                    if quant:
                        quant.write({'quantity': qty})
                    else:
                        Quant.create({'product_id': prod.product_variant_id.id, 'location_id': loc.id, 'quantity': qty})
            except Exception as exc:
                _logger.warning("Mercado Wanka: no se pudo sincronizar stock para prod %s: %s", prod.id, exc)

        base_url = (
            request.env['ir.config_parameter'].sudo().search([('key', '=', 'web.base.url')], limit=1).value
            or 'https://tienda.sofiaerp.com'
        ).rstrip('/')

        return _json_response({
            'ok': True,
            'marketplace_product_id': prod.id,
            'is_published': prod.is_published,
            'product_url': f'{base_url}/shop/product/{prod.id}',
        })

    @http.route('/api/marketplace/v1/sellers/subscription_status', type='http', auth='public', methods=['POST'], csrf=False)
    def update_subscription_status(self, **kwargs):
        """Oculta o reactiva automáticamente los productos de una tienda según el plan pagado en SOFIA ERP."""
        if not _verify_internal_key():
            return _json_response({'error': 'Unauthorized'}, status=403)
        try:
            data = json.loads(request.httprequest.data.decode('utf-8') or '{}')
        except Exception:
            return _json_response({'error': 'Invalid JSON payload'}, status=400)

        slug = (data.get('tenant_slug') or '').strip().lower()
        active = bool(data.get('active', False))
        seller = request.env['res.partner'].sudo().search([('sofia_tenant_slug', '=', slug)], limit=1)
        if not seller:
            return _json_response({'ok': True, 'found': False})

        seller.write({
            'sofia_subscription_active': active,
            'marketplace_seller_status': 'approved' if active else 'pending',
        })
        prods = request.env['product.template'].sudo().search([('marketplace_seller_id', '=', seller.id)])
        if not active and prods:
            prods.write({'is_published': False, 'website_published': False})
        return _json_response({'ok': True, 'found': True, 'active': active, 'products_affected': len(prods)})
