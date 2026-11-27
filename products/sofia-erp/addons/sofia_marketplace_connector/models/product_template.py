# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    mw_published = fields.Boolean(
        string='Publicado en Mercado Wanka',
        default=False,
        copy=False,
        help='Activa con 1 clic para publicar este producto en Mercado Wanka (tienda.sofiaerp.com).',
    )
    mw_remote_id = fields.Integer(string='ID en Mercado Wanka', readonly=True, copy=False)
    mw_product_url = fields.Char(string='Enlace Mercado Wanka', readonly=True, copy=False)

    def _sync_to_mercado_wanka(self, publish=True):
        self.ensure_one()
        company = self.company_id or self.env.company
        if not company.mw_store_enabled:
            company.action_register_mercado_wanka_store()

        slug = company._get_sofia_tenant_slug()
        img_b64 = self.image_1920.decode('utf-8') if isinstance(self.image_1920, bytes) else (self.image_1920 or False)
        payload = {
            'tenant_slug': slug,
            'remote_product_id': str(self.id),
            'name': self.name,
            'list_price': float(self.list_price or 0.0),
            'default_code': self.default_code or '',
            'description_sale': self.description_sale or '',
            'category_name': self.categ_id.name if self.categ_id else '',
            'weight': float(self.weight or 0.0),
            'qty_available': float(getattr(self, 'qty_available', 0.0) or 0.0),
            'image_b64': img_b64,
            'publish': bool(publish),
        }
        data = company._mw_hub_request('/api/marketplace/v1/products/sync', payload)
        self.sudo().write({
            'mw_published': bool(data.get('is_published', publish)),
            'mw_remote_id': data.get('marketplace_product_id') or self.mw_remote_id,
            'mw_product_url': data.get('product_url') or self.mw_product_url,
        })
        return data

    def action_toggle_mercado_wanka_publish(self):
        """Botón 1-Clic en ficha de producto (igual a Publicar en eCommerce)."""
        for rec in self:
            target_state = not rec.mw_published
            rec._sync_to_mercado_wanka(publish=target_state)
        return True

    def write(self, vals):
        res = super().write(vals)
        sync_triggers = {'name', 'list_price', 'default_code', 'description_sale', 'image_1920', 'weight', 'categ_id'}
        if sync_triggers.intersection(vals.keys()):
            for rec in self.filtered('mw_published'):
                try:
                    rec._sync_to_mercado_wanka(publish=True)
                except Exception as exc:
                    _logger.warning("Mercado Wanka auto-sync omitido para producto %s: %s", rec.id, exc)
        return res
