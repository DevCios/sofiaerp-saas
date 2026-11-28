# -*- coding: utf-8 -*-
import hashlib
import hmac
import html
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
    Motor de Pagos Producción de Mercado Wanka (reutiliza MP_ACCESS_TOKEN de SOFIA ERP):
    - Checkout Pro (Tarjetas, Yape, Plin, PagoEfectivo).
    - Validación HMAC-SHA256 del webhook oficial de Mercado Pago (x-signature).
    - Idempotencia estricta por payment_id (evita doble confirmación/división).
    - Confirmación multi-vendedor + despacho automático al ERP del vendedor.
    """

    def _get_mp_access_token(self):
        token = os.getenv("MP_ACCESS_TOKEN") or ""
        if not token:
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 'sofia.mercadopago.access_token')], limit=1)
            token = param.value if param else ""
        return token.strip()

    def _get_mp_webhook_secret(self):
        secret = os.getenv("MP_WEBHOOK_SECRET") or ""
        if not secret:
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 'sofia.mercadopago.webhook_secret')], limit=1)
            secret = param.value if param else ""
        return secret.strip()

    def _get_base_url(self):
        param = request.env['ir.config_parameter'].sudo().search([('key', '=', 'web.base.url')], limit=1)
        return (param.value if param else 'https://mercadowanka.com').rstrip('/')

    def _verify_mp_signature(self, data_id):
        """Verifica cabecera x-signature de Mercado Pago (HMAC-SHA256) fail-closed."""
        secret = self._get_mp_webhook_secret()
        if not secret:
            _logger.error("Mercado Wanka MP webhook: MP_WEBHOOK_SECRET no configurado (rechazado fail-closed).")
            return False
        x_sig = request.httprequest.headers.get("x-signature", "")
        x_req_id = request.httprequest.headers.get("x-request-id", "")
        parts = {}
        for piece in x_sig.split(","):
            if "=" in piece:
                k, v = piece.split("=", 1)
                parts[k.strip()] = v.strip()
        ts = parts.get("ts", "")
        v1 = parts.get("v1", "")
        if not ts or not v1:
            return False
        manifest = f"id:{data_id};request-id:{x_req_id};ts:{ts};"
        expected = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, v1)

    def _get_current_website(self):
        return getattr(request, 'website', None) or request.env['website'].get_current_website()

    def _get_current_order(self):
        order = getattr(request, 'cart', None)
        if order and order.exists():
            return order
        website = self._get_current_website()
        if website and hasattr(website, 'sale_get_order'):
            order = website.sale_get_order()
            if order and order.exists():
                return order
        order_id = request.session.get('sale_order_id')
        if order_id:
            so = request.env['sale.order'].sudo().browse(order_id)
            if so.exists() and so.state in ('draft', 'sent'):
                return so
        return request.env['sale.order']

    @http.route('/shop/mercadopago/set_delivery', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def set_delivery_preference(self, delivery_mode='home_delivery', delivery_notes='', receipt_type='boleta', receipt_doc_number='', **kwargs):
        """Guarda la modalidad de entrega y comprobante SUNAT elegidos por el comprador antes de pagar en Mercado Pago."""
        order = self._get_current_order()
        if order and order.exists() and order.state in ('draft', 'sent'):
            valid_modes = ('store_pickup', 'home_delivery', 'agency_shipping')
            safe_mode = delivery_mode if delivery_mode in valid_modes else 'home_delivery'
            vals = {}
            if 'delivery_type' in order._fields:
                vals['delivery_type'] = safe_mode
            clean_receipt = 'factura' if receipt_type == 'factura' else 'boleta'
            clean_doc = ''.join(ch for ch in (receipt_doc_number or '') if ch.isdigit())[:11]
            note_parts = [f"Entrega: {safe_mode}"]
            if clean_doc:
                note_parts.append(f"Comprobante SUNAT: {clean_receipt.upper()} ({clean_doc})")
            else:
                note_parts.append(f"Comprobante SUNAT: {clean_receipt.upper()}")
            if delivery_notes and delivery_notes.strip():
                safe_notes = html.escape(delivery_notes.strip().replace('|', '-')[:300])
                note_parts.append(f"Ref: {safe_notes}")
            vals['note'] = " | ".join(note_parts)
            if vals:
                order.sudo().write(vals)
        return request.redirect('/shop/mercadopago/pay')

    @http.route('/shop/mercadopago/pay', type='http', auth='public', website=True, csrf=False)
    def start_mercadopago_payment(self, **kwargs):
        order = self._get_current_order()
        if not order or not order.order_line:
            return request.redirect('/shop/cart')

        access_token = self._get_mp_access_token()
        if not access_token:
            _logger.error("Mercado Wanka: MP_ACCESS_TOKEN no configurado.")
            return request.redirect('/shop/cart?error=mp_not_configured')

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
                "email": order.partner_id.email or "cliente@mercadowanka.com",
            },
            "back_urls": {
                "success": f"{base_url}/shop/mercadopago/callback?order_id={order.id}",
                "pending": f"{base_url}/shop/mercadopago/callback?order_id={order.id}",
                "failure": f"{base_url}/shop/cart?mp_status=failure",
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

        return request.redirect('/shop/cart?error=mp_unavailable')

    def _verify_and_confirm_order(self, order, payment_id):
        """Verifica el pago directamente en la API oficial de Mercado Pago con idempotencia estricta."""
        access_token = self._get_mp_access_token()
        pid = str(payment_id or "").strip()
        if not access_token or not pid or not pid.isdigit():
            return False

        ref_tag = f"MP-{pid}"
        # Idempotencia: si ya fue procesado este payment_id en cualquier orden, no duplicar
        already = request.env['sale.order'].sudo().search([('client_order_ref', '=', ref_tag)], limit=1)
        if already:
            _logger.info("Mercado Wanka: pago %s ya procesado previamente en orden %s (idempotente).", ref_tag, already.name)
            return already.id == order.id

        try:
            resp = requests.get(
                MP_PAYMENT_API.format(payment_id=pid),
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=12,
            )
            if resp.status_code != 200:
                return False
            pdata = resp.json()
            expected_ref = f"MW-{order.id}-{order.name}"
            expected_currency = (order.currency_id.name or "PEN").upper()
            paid_currency = (pdata.get("currency_id") or "PEN").upper()
            paid_amount = float(pdata.get("transaction_amount") or 0.0)
            expected_amount = float(order.amount_total or 0.0)
            if (
                pdata.get("status") == "approved"
                and (pdata.get("external_reference") or "") == expected_ref
                and paid_currency == expected_currency
                and paid_amount + 0.05 >= expected_amount
            ):
                if order.state in ('draft', 'sent'):
                    order.sudo().write({'client_order_ref': ref_tag})
                    order.sudo().action_confirm()
                    _logger.info("Mercado Wanka: orden %s confirmada con pago verificado %s (S/ %.2f)", order.name, ref_tag, paid_amount)
                return True
        except Exception as exc:
            _logger.error("Mercado Wanka: error verificando pago MP %s: %s", pid, exc)
        return False

    @http.route('/shop/mercadopago/callback', type='http', auth='public', website=True, csrf=False)
    def mercadopago_callback(self, order_id=None, payment_id=None, status=None, **kwargs):
        if order_id and str(order_id).isdigit() and payment_id:
            order = request.env['sale.order'].sudo().browse(int(order_id))
            if order.exists() and self._verify_and_confirm_order(order, payment_id):
                request.session['sale_last_order_id'] = order.id
                website = self._get_current_website()
                if website and hasattr(website, 'sale_reset'):
                    website.sale_reset()
                else:
                    request.session.pop('sale_order_id', None)
                return request.redirect('/shop/confirmation')
        return request.redirect('/shop/cart')

    @http.route('/shop/mercadopago/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def mercadopago_webhook(self, **kwargs):
        try:
            body = json.loads(request.httprequest.data.decode('utf-8') or '{}')
            payment_id = str((body.get('data') or {}).get('id') or kwargs.get('data.id') or '').strip()
            if not payment_id:
                return http.Response("OK", status=200)
            if not self._verify_mp_signature(payment_id):
                _logger.warning("Mercado Wanka MP webhook: firma HMAC inválida para payment_id=%s", payment_id)
                return http.Response("Invalid signature", status=403)

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
                    if order.exists():
                        self._verify_and_confirm_order(order, payment_id)
        except Exception as exc:
            _logger.warning("Mercado Wanka MP webhook warning: %s", exc)
        return http.Response("OK", status=200)
