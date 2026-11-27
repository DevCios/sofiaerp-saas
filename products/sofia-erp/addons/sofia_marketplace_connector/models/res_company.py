# -*- coding: utf-8 -*-
import logging
import os
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    mw_store_enabled = fields.Boolean(string='Tienda Mercado Wanka Activa', default=False)
    mw_store_name = fields.Char(string='Nombre Comercial en Mercado Wanka')
    mw_seller_id = fields.Integer(string='ID Vendedor Mercado Wanka', readonly=True)
    mw_seller_token = fields.Char(string='Token Tienda Mercado Wanka', readonly=True, copy=False)
    mw_store_url = fields.Char(string='URL Tienda Mercado Wanka', readonly=True)

    def _mw_hub_request(self, path, payload):
        """
        Invoca la API Interna del Hub Mercado Wanka (sofia_tenant_tienda).
        Usa red interna Docker por defecto (latencia <20ms) o MARKETPLACE_HUB_URL.
        """
        hub_url = os.getenv('MARKETPLACE_HUB_URL', 'http://127.0.0.1:8069').rstrip('/')
        internal_key = os.getenv('INTERNAL_SERVICE_KEY', 'sofia_internal_mesh_key_change_in_prod')
        headers = {
            'Content-Type': 'application/json',
            'X-Internal-Service-Key': internal_key,
            'X-Odoo-dbfilter': os.getenv('MARKETPLACE_DB_NAME', 'sofia_tenant_tienda'),
            'Host': os.getenv('MARKETPLACE_PUBLIC_HOST', 'tienda.sofiaerp.com'),
        }
        try:
            resp = requests.post(f'{hub_url}{path}', json=payload, headers=headers, timeout=15)
            data = resp.json() if resp.content else {}
            if resp.status_code not in (200, 201):
                raise UserError(_("Mercado Wanka respondió (%s): %s") % (resp.status_code, data.get('error') or resp.text))
            return data
        except UserError:
            raise
        except Exception as exc:
            raise UserError(_("No se pudo conectar con Mercado Wanka (%s): %s") % (hub_url, exc))

    def _get_sofia_tenant_slug(self):
        dbname = self.env.cr.dbname or ''
        if dbname.startswith('sofia_tenant_'):
            return dbname[len('sofia_tenant_'):]
        return dbname or 'sofiaerp'

    def action_register_mercado_wanka_store(self, store_name=None):
        self.ensure_one()
        slug = self._get_sofia_tenant_slug()
        base_url = (
            self.env['ir.config_parameter'].sudo().search([('key', '=', 'web.base.url')], limit=1).value
            or f'https://{slug}.sofiaerp.com'
        ).rstrip('/')

        logo_b64 = self.logo.decode('utf-8') if isinstance(self.logo, bytes) else (self.logo or False)
        payload = {
            'tenant_slug': slug,
            'tenant_url': base_url,
            'ruc': (self.vat or '').strip(),
            'company_name': self.name or '',
            'store_name': (store_name or self.mw_store_name or self.name or '').strip(),
            'email': self.email or '',
            'phone': self.phone or '',
            'street': self.street or '',
            'zip': self.zip or '',
            'logo_b64': logo_b64,
            'plan_paid': True,
        }
        data = self._mw_hub_request('/api/marketplace/v1/sellers/upsert', payload)
        self.sudo().write({
            'mw_store_enabled': True,
            'mw_store_name': payload['store_name'],
            'mw_seller_id': data.get('seller_id') or 0,
            'mw_seller_token': data.get('seller_token') or '',
            'mw_store_url': data.get('store_url') or '',
        })
        return data
