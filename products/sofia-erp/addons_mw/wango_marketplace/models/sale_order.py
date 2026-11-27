# -*- coding: utf-8 -*-
import logging
import os
import requests
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

DEFAULT_COMMISSION_RATE = 5.0
DEFAULT_PLATFORM_FEE = 0.50


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    marketplace_seller_id = fields.Many2one(
        'res.partner',
        string="Vendedor (Mercado Wanka)",
        readonly=True,
        help="Vendedor responsable de despachar y emitir el comprobante SUNAT de los productos.",
    )

    marketplace_commission_variable = fields.Monetary(
        string="Comisión Variable (%)",
        compute='_compute_marketplace_commission_total',
        store=True,
    )

    marketplace_platform_fee = fields.Monetary(
        string="Cargo Uso de Plataforma",
        default=DEFAULT_PLATFORM_FEE,
        help="Cargo fijo por uso de plataforma Mercado Wanka por venta (por defecto S/ 0.50).",
    )

    marketplace_commission_total = fields.Monetary(
        string="Total Comisión Mercado Wanka",
        compute='_compute_marketplace_commission_total',
        store=True,
        help="Comisión variable (5% por defecto del precio total) + cargo fijo uso de plataforma (S/ 0.50). Solo este monto factura Mercado Wanka al vendedor.",
    )

    marketplace_seller_net = fields.Monetary(
        string="Neto para el Vendedor",
        compute='_compute_marketplace_commission_total',
        store=True,
    )

    sofia_pushed_to_tenant = fields.Boolean(
        string="Enviado a ERP del Vendedor",
        default=False,
        readonly=True,
    )

    @api.depends('order_line.marketplace_commission_amount', 'marketplace_platform_fee', 'amount_total', 'marketplace_seller_id')
    def _compute_marketplace_commission_total(self):
        for order in self:
            if order.marketplace_seller_id:
                var_comm = sum(order.order_line.mapped('marketplace_commission_amount'))
                fee = order.marketplace_platform_fee if order.marketplace_platform_fee is not None else DEFAULT_PLATFORM_FEE
                order.marketplace_commission_variable = var_comm
                order.marketplace_commission_total = var_comm + fee
                order.marketplace_seller_net = max(0.0, (order.amount_total or 0.0) - order.marketplace_commission_total)
            else:
                order.marketplace_commission_variable = 0.0
                order.marketplace_commission_total = 0.0
                order.marketplace_seller_net = 0.0

    def action_confirm(self):
        """Intercepta la confirmación para dividir carritos multi-vendedor y notificar al ERP del vendedor."""
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue

            sellers = order.order_line.mapped('product_id.marketplace_seller_id')
            if len(sellers) > 1:
                order._split_marketplace_order(sellers)
            elif len(sellers) == 1:
                order.marketplace_seller_id = sellers[0].id
                if not order.marketplace_platform_fee:
                    order.marketplace_platform_fee = DEFAULT_PLATFORM_FEE

        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.marketplace_seller_id:
                order._send_seller_new_order_email()
                order._push_order_to_seller_tenant()
        return res

    def _split_marketplace_order(self, sellers):
        """Divide la orden principal dejando 1 vendedor aquí y creando sub-órdenes para el resto."""
        first_seller = sellers[0]
        self.marketplace_seller_id = first_seller.id
        if not self.marketplace_platform_fee:
            self.marketplace_platform_fee = DEFAULT_PLATFORM_FEE

        other_sellers = sellers - first_seller
        for seller in other_sellers:
            seller_lines = self.order_line.filtered(lambda l: l.product_id.marketplace_seller_id == seller)
            if not seller_lines:
                continue

            new_order_vals = self.copy_data({
                'marketplace_seller_id': seller.id,
                'marketplace_platform_fee': DEFAULT_PLATFORM_FEE,
                'origin': self.name,
                'client_order_ref': self.client_order_ref,
            })[0]
            new_order = self.env['sale.order'].create(new_order_vals)
            for line in seller_lines:
                line.order_id = new_order.id

            new_order.action_confirm()

    def _send_seller_new_order_email(self):
        base_url = (
            self.env['ir.config_parameter'].sudo().search([('key', '=', 'web.base.url')], limit=1).value
            or 'https://tienda.sofiaerp.com'
        ).rstrip('/')
        for order in self:
            seller = order.marketplace_seller_id
            if seller and seller.email:
                body = (
                    f"<h2>¡Felicidades {seller.name}! Tienes una nueva venta en Mercado Wanka.</h2>"
                    f"<p>Orden: <strong>{order.name}</strong></p>"
                    f"<p>Total Venta: {order.currency_id.symbol} {order.amount_total:.2f}</p>"
                    f"<p>Comisión Mercado Wanka (incl. S/ {order.marketplace_platform_fee:.2f} plataforma): "
                    f"{order.currency_id.symbol} {order.marketplace_commission_total:.2f}</p>"
                    f"<p><strong>Neto a Liquidar: {order.currency_id.symbol} {order.marketplace_seller_net:.2f}</strong></p>"
                    f"<p>Recuerda emitir la Boleta/Factura Electrónica al comprador desde tu SOFIA ERP.</p>"
                    f"<p>Revisa tu <a href='{base_url}/my/seller/dashboard'>Panel de Vendedor</a>.</p>"
                )
                try:
                    self.env['mail.mail'].sudo().create({
                        'subject': f'Nueva Venta Mercado Wanka - {order.name}',
                        'body_html': body,
                        'email_to': seller.email,
                    }).send()
                except Exception as exc:
                    _logger.warning("Mercado Wanka: no se pudo enviar correo al vendedor %s: %s", seller.name, exc)

    def _push_order_to_seller_tenant(self):
        """Empuja la sub-orden pagada al tenant SOFIA ERP del vendedor para despacho y facturación SUNAT."""
        internal_key = os.getenv("INTERNAL_SERVICE_KEY", "sofia_internal_mesh_key_change_in_prod")
        for order in self:
            seller = order.marketplace_seller_id
            if order.sofia_pushed_to_tenant or not seller or not seller.sofia_tenant_url:
                continue
            endpoint = f"{seller.sofia_tenant_url.rstrip('/')}/api/sofia_marketplace/webhook/order"
            payload = {
                'marketplace_order_ref': order.name,
                'seller_ruc': seller.vat or '',
                'buyer': {
                    'name': order.partner_id.name,
                    'email': order.partner_id.email or '',
                    'phone': order.partner_id.phone or '',
                    'vat': order.partner_id.vat or '',
                    'street': order.partner_shipping_id.street or order.partner_id.street or '',
                },
                'currency': order.currency_id.name or 'PEN',
                'amount_total': order.amount_total,
                'commission_total': order.marketplace_commission_total,
                'platform_fee': order.marketplace_platform_fee,
                'seller_net': order.marketplace_seller_net,
                'lines': [
                    {
                        'sku': l.product_id.default_code or '',
                        'name': l.name,
                        'quantity': l.product_uom_qty,
                        'price_unit': l.price_unit,
                        'price_total': l.price_total,
                    }
                    for l in order.order_line
                    if not l.is_delivery
                ],
            }
            try:
                resp = requests.post(
                    endpoint,
                    json=payload,
                    headers={
                        'X-Internal-Service-Key': internal_key,
                        'X-Marketplace-Seller-Token': seller.sofia_seller_token or '',
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    order.sudo().write({'sofia_pushed_to_tenant': True})
                    _logger.info("Mercado Wanka: orden %s sincronizada al ERP %s", order.name, seller.sofia_tenant_url)
                else:
                    _logger.warning("Mercado Wanka: ERP %s devolvió HTTP %s al recibir orden %s", seller.sofia_tenant_url, resp.status_code, order.name)
            except Exception as exc:
                _logger.warning("Mercado Wanka: error enviando orden %s al ERP %s: %s", order.name, seller.sofia_tenant_url, exc)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    marketplace_commission_rate = fields.Float(
        string="Tasa de Comisión (%)",
        compute='_compute_marketplace_commission',
        store=True,
    )

    marketplace_commission_amount = fields.Monetary(
        string="Comisión Variable Mercado Wanka",
        compute='_compute_marketplace_commission',
        store=True,
        help="Calculada sobre el valor total (price_total) de la línea (5% por defecto).",
    )

    @api.depends('product_id', 'price_total', 'order_id.marketplace_seller_id')
    def _compute_marketplace_commission(self):
        for line in self:
            seller = line.order_id.marketplace_seller_id
            if seller and line.product_id and not getattr(line, 'is_delivery', False):
                if seller.marketplace_custom_commission_rate and seller.marketplace_custom_commission_rate > 0:
                    rate = seller.marketplace_custom_commission_rate
                elif line.product_id.categ_id and line.product_id.categ_id.marketplace_commission_rate > 0:
                    rate = line.product_id.categ_id.marketplace_commission_rate
                else:
                    rate = DEFAULT_COMMISSION_RATE

                line.marketplace_commission_rate = rate
                line.marketplace_commission_amount = (line.price_total * rate) / 100.0
            else:
                line.marketplace_commission_rate = 0.0
                line.marketplace_commission_amount = 0.0
