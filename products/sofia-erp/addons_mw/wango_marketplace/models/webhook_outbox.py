# -*- coding: utf-8 -*-
import json
import logging
import os
from datetime import timedelta

import requests
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Escalera de reintentos (minutos): 2m, 10m, 30m, 2h, 6h
RETRY_DELAYS_MINUTES = [2, 10, 30, 120, 360]


class MarketplaceWebhookOutbox(models.Model):
    """
    Cola Asíncrona Persistente (Transactional Outbox Pattern):
    Desacopla la confirmación de pedidos en Mercado Wanka del envío HTTP hacia el ERP
    de cada vendedor (SOFIA Tenant). Si el ERP del vendedor está lento o reiniciando,
    el checkout del comprador responde en <200ms y el cron reintenta con backoff exponencial.
    """
    _name = 'mw.webhook.outbox'
    _description = 'Cola Asíncrona de Webhooks Mercado Wanka -> SOFIA ERP'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Referencia', required=True, index=True)
    order_id = fields.Many2one('sale.order', string='Orden Marketplace', ondelete='set null', index=True)
    seller_id = fields.Many2one('res.partner', string='Vendedor', ondelete='set null', index=True)
    target_url = fields.Char(string='Endpoint Destino', required=True)
    payload_json = fields.Text(string='Payload JSON', required=True)
    seller_token = fields.Char(string='Token Tienda', copy=False)

    state = fields.Selection([
        ('pending', 'En Cola'),
        ('sent', 'Entregado'),
        ('retry', 'Reintentando'),
        ('failed', 'Fallido (Requiere Revisión)'),
    ], string='Estado', default='pending', index=True)

    attempt_count = fields.Integer(string='Intentos', default=0)
    next_retry_at = fields.Datetime(string='Próximo Reintento', default=fields.Datetime.now, index=True)
    last_http_status = fields.Integer(string='Último HTTP')
    last_error = fields.Text(string='Última Respuesta / Error')
    delivered_at = fields.Datetime(string='Entregado el')

    def action_deliver_now(self):
        internal_key = os.getenv('INTERNAL_SERVICE_KEY', 'sofia_internal_mesh_key_change_in_prod')
        now = fields.Datetime.now()
        for rec in self:
            if rec.state == 'sent':
                continue
            rec.attempt_count += 1
            headers = {
                'Content-Type': 'application/json',
                'X-Internal-Service-Key': internal_key,
                'X-Marketplace-Seller-Token': rec.seller_token or '',
            }
            try:
                resp = requests.post(
                    rec.target_url,
                    data=(rec.payload_json or '{}').encode('utf-8'),
                    headers=headers,
                    timeout=10,
                )
                rec.last_http_status = resp.status_code
                if 200 <= resp.status_code < 300:
                    rec.write({
                        'state': 'sent',
                        'delivered_at': now,
                        'last_error': False,
                        'next_retry_at': False,
                    })
                    if rec.order_id:
                        rec.order_id.sudo().write({'sofia_pushed_to_tenant': True})
                    continue
                err_msg = f"HTTP {resp.status_code}: {(resp.text or '')[:400]}"
            except Exception as exc:
                rec.last_http_status = 0
                err_msg = str(exc)[:400]

            if rec.attempt_count <= len(RETRY_DELAYS_MINUTES):
                delay = RETRY_DELAYS_MINUTES[rec.attempt_count - 1]
                rec.write({
                    'state': 'retry',
                    'last_error': err_msg,
                    'next_retry_at': now + timedelta(minutes=delay),
                })
            else:
                rec.write({
                    'state': 'failed',
                    'last_error': err_msg,
                    'next_retry_at': False,
                })
                _logger.error("Mercado Wanka Outbox %s agotó reintentos: %s", rec.name, err_msg)

    @api.model
    def cron_process_outbox(self, batch_size=30):
        now = fields.Datetime.now()
        jobs = self.sudo().search([
            ('state', 'in', ('pending', 'retry')),
            '|', ('next_retry_at', '=', False), ('next_retry_at', '<=', now),
        ], order='next_retry_at asc, id asc', limit=batch_size)
        if jobs:
            jobs.action_deliver_now()
        return len(jobs)


class MarketplaceBankAudit(models.Model):
    """Bitácora inmutable de cambios de cuenta bancaria / CCI de vendedores (antifraude)."""
    _name = 'mw.bank.audit'
    _description = 'Auditoría de Cambios Bancarios de Vendedores'
    _order = 'create_date desc, id desc'

    seller_id = fields.Many2one('res.partner', string='Vendedor', required=True, ondelete='cascade', index=True)
    changed_by_id = fields.Many2one('res.users', string='Modificado por', default=lambda self: self.env.user, readonly=True)
    old_bank_info = fields.Char(string='Cuenta Anterior', readonly=True)
    new_bank_info = fields.Char(string='Cuenta Nueva', readonly=True)
    note = fields.Char(string='Detalle', readonly=True)
