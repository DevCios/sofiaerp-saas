# -*- coding: utf-8 -*-
import hmac
import json
import logging
import os

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class SofiaMarketplaceOrderWebhook(http.Controller):
    """
    Recibe en el tenant SOFIA ERP los pedidos pagados desde Mercado Wanka (tienda.sofiaerp.com),
    crea el cliente y la Orden de Venta lista para despacho y emisión de Boleta/Factura SUNAT.
    """

    @http.route('/api/sofia_marketplace/webhook/order', type='http', auth='public', methods=['POST'], csrf=False)
    def receive_marketplace_order(self, **kwargs):
        expected_key = os.getenv('INTERNAL_SERVICE_KEY', 'sofia_internal_mesh_key_change_in_prod')
        provided_key = request.httprequest.headers.get('X-Internal-Service-Key', '')
        if not provided_key or not hmac.compare_digest(provided_key, expected_key):
            return Response(json.dumps({'error': 'Unauthorized'}), status=403, mimetype='application/json')

        try:
            data = json.loads(request.httprequest.data.decode('utf-8') or '{}')
        except Exception:
            return Response(json.dumps({'error': 'Invalid JSON'}), status=400, mimetype='application/json')

        order_ref = data.get('marketplace_order_ref') or ''
        SaleOrder = request.env['sale.order'].sudo()
        if order_ref:
            existing = SaleOrder.search([('client_order_ref', '=', f'MW:{order_ref}')], limit=1)
            if existing:
                return Response(
                    json.dumps({'ok': True, 'sale_order_id': existing.id, 'idempotent': True}),
                    status=200,
                    mimetype='application/json',
                )

        buyer_info = data.get('buyer') or {}
        Partner = request.env['res.partner'].sudo()
        buyer = False
        if buyer_info.get('vat'):
            buyer = Partner.search([('vat', '=', buyer_info['vat'])], limit=1)
        if not buyer and buyer_info.get('email'):
            buyer = Partner.search([('email', '=', buyer_info['email'])], limit=1)
        if not buyer:
            buyer = Partner.create({
                'name': buyer_info.get('name') or 'Cliente Mercado Wanka',
                'email': buyer_info.get('email') or False,
                'phone': buyer_info.get('phone') or False,
                'vat': buyer_info.get('vat') or False,
                'street': buyer_info.get('street') or False,
            })

        Product = request.env['product.product'].sudo()
        order_lines = []
        for item in data.get('lines') or []:
            prod = False
            if item.get('sku'):
                prod = Product.search([('default_code', '=', item['sku'])], limit=1)
            if not prod:
                prod = Product.search([('name', 'ilike', item.get('name') or '')], limit=1)
            if not prod:
                prod = Product.search([('sale_ok', '=', True)], limit=1)
            if prod:
                order_lines.append((0, 0, {
                    'product_id': prod.id,
                    'name': item.get('name') or prod.name,
                    'product_uom_qty': float(item.get('quantity') or 1.0),
                    'price_unit': float(item.get('price_unit') or 0.0),
                }))

        so = SaleOrder.create({
            'partner_id': buyer.id,
            'client_order_ref': f'MW:{order_ref}',
            'origin': f'Mercado Wanka {order_ref}',
            'note': (
                f"Pedido recibido de Mercado Wanka ({order_ref}). "
                f"Comisión Mercado Wanka: S/ {float(data.get('commission_total') or 0):.2f} "
                f"(incl. S/ {float(data.get('platform_fee') or 0.50):.2f} plataforma). "
                f"Neto a recibir: S/ {float(data.get('seller_net') or 0):.2f}. "
                f"Emitir Boleta/Factura Electrónica SUNAT al comprador desde este ERP."
            ),
            'order_line': order_lines,
        })
        so.action_confirm()
        _logger.info("SOFIA ERP: Pedido Mercado Wanka %s creado como %s", order_ref, so.name)

        return Response(
            json.dumps({'ok': True, 'sale_order_id': so.id, 'sale_order_name': so.name}),
            status=200,
            mimetype='application/json',
        )
