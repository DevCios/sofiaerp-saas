# -*- coding: utf-8 -*-
import json
import logging
import os
import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

MP_PREFERENCE_API = "https://api.mercadopago.com/checkout/preferences"
MP_PAYMENT_API = "https://api.mercadopago.com/v1/payments/{payment_id}"


class MercadoWankaMercadoPagoCheckout(http.Controller):
    """
    Reutiliza el mismo motor Mercado Pago Checkout Pro de SOFIA ERP (MP_ACCESS_TOKEN)
    para cobrar carritos multi-vendedor en Mercado Wanka (tienda.sofiaerp.com)
    y confirmar/dividir las órdenes por vendedor al recibir pago aprobado.
    """

    def _get_mp_access_token(self):
        token = os.getenv("MP_ACCESS_TOKEN") or ""
        if not token:
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 'sofia.mercadopago.access_token')], limit=1)
            token = param.value if param else ""
        return token.strip()

    def _get_base_url(self):
        param = request.env['ir.config_parameter'].sudo().search([('key', '=', 'web.base.url')], limit=1)
        return (param.value if param else 'https://tienda.sofiaerp.com').rstrip('/')

    @http.route('/shop/mercadopago/pay', type='http', auth='public', website=True, csrf=False)
    def start_mercadopago_payment(self, **kwargs):
        order = request.website.sale_get_order()
        if not order or not order.order_line:
            return request.redirect('/shop/cart')

        access_token = self._get_mp_access_token()
        if not access_token:
            _logger.error("Mercado Wanka: MP_ACCESS_TOKEN no configurado.")
            return request.redirect('/shop/payment?error=mp_not_configured')

        base_url = self._get_base_url()
        mp_items = [
            {
                "id": str(line.product_id.id),
                "title": (line.name or line.product_id.name)[:120],
                "quantity": int(max(1, round(line.product_uom_qty))),
                "currency_id": order.currency_id.name or "PEN",
                "unit_price": round(float(line.price_total) / max(1.0, float(line.product_uom_qty)), 2),
            }
            for line in order.order_line
            if line.price_total > 0
        ]

        preference = {
            "items": mp_items,
            "external_reference": f"MW-{order.id}-{order.name}",
            "payer": {
                "name": order.partner_id.name or "Cliente Mercado Wanka",
                "email": order.partner_id.email or "cliente@tienda.sofiaerp.com",
            },
            "back_urls": {
                "success": f"{base_url}/shop/mercadopago/callback?order_id={order.id}",
                "pending": f"{base_url}/shop/mercadopago/callback?order_id={order.id}",
                "failure": f"{base_url}/shop/payment?mp_status=failure",
            },
            "auto_return": "approved",
            "notification_url": f"{base_url}/shop/mercadopago/webhook",
            "statement_descriptor": "MERCADO WANKA",
        }

        try:
            resp = requests.post(
                MP_PREFERENCE_API,
                json=preference,
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                timeout=15,
            )
            data = resp.json()
            init_point = data.get("init_point") or data.get("sandbox_init_point")
            if resp.status_code in (200, 201) and init_point:
                return request.redirect(init_point, local=False)
            _logger.error("Mercado Wanka MP preference error (%s): %s", resp.status_code, resp.text)
        except Exception as exc:
            _logger.error("Mercado Wanka MP exception: %s", exc)

        return request.redirect('/shop/payment?error=mp_unavailable')

    def _verify_and_confirm_order(self, order, payment_id):
        access_token = self._get_mp_access_token()
        if not access_token or not payment_id:
            return False
        try:
            resp = requests.get(
                MP_PAYMENT_API.format(payment_id=payment_id),
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=12,
            )
            if resp.status_code != 200:
                return False
            pdata = resp.json()
            if pdata.get("status") == "approved":
                if order.state in ('draft', 'sent'):
                    order.sudo().write({'client_order_ref': f'MP-{payment_id}'})
                    order.sudo().action_confirm()
                return True
        except Exception as exc:
            _logger.error("Mercado Wanka: error verificando pago MP %s: %s", payment_id, exc)
        return False

    @http.route('/shop/mercadopago/callback', type='http', auth='public', website=True, csrf=False)
    def mercadopago_callback(self, order_id=None, payment_id=None, status=None, **kwargs):
        if order_id and payment_id:
            order = request.env['sale.order'].sudo().browse(int(order_id))
            if order.exists():
                self._verify_and_confirm_order(order, payment_id)
                request.session['sale_last_order_id'] = order.id
                request.website.sale_reset()
                return request.redirect('/shop/confirmation')
        return request.redirect('/shop/cart')

    @http.route('/shop/mercadopago/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def mercadopago_webhook(self, **kwargs):
        try:
            body = json.loads(request.httprequest.data.decode('utf-8') or '{}')
            payment_id = (body.get('data') or {}).get('id') or kwargs.get('data.id')
            if payment_id:
                access_token = self._get_mp_access_token()
                r = requests.get(
                    MP_PAYMENT_API.format(payment_id=payment_id),
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=12,
                )
                if r.status_code == 200:
                    pdata = r.json()
                    ext_ref = pdata.get('external_reference') or ''
                    if ext_ref.startswith('MW-') and pdata.get('status') == 'approved':
                        oid = int(ext_ref.split('-')[1])
                        order = request.env['sale.order'].sudo().browse(oid)
                        if order.exists() and order.state in ('draft', 'sent'):
                            order.sudo().write({'client_order_ref': f'MP-{payment_id}'})
                            order.sudo().action_confirm()
        except Exception as exc:
            _logger.warning("Mercado Wanka MP webhook warning: %s", exc)
        return http.Response("OK", status=200)
