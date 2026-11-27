# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    marketplace_seller_id = fields.Many2one(
        'res.partner', 
        string="Vendedor", 
        domain="[('is_marketplace_seller', '=', True)]",
        help="Vendedor al que pertenece este producto."
    )
    
    marketplace_status = fields.Selection([
        ('pending', 'Pendiente de Aprobación'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado')
    ], string="Estado en Marketplace", default='pending', tracking=True)

    # Campos relacionados de reputación del vendedor (accesibles y editables directamente desde el producto)
    seller_rating_avg = fields.Float(
        related='marketplace_seller_id.seller_rating_avg',
        string="Calificación de la Tienda (1.0 - 5.0)",
        readonly=False,
    )
    seller_rating_count = fields.Integer(
        related='marketplace_seller_id.seller_rating_count',
        string="Opiniones de la Tienda",
        readonly=False,
    )
    seller_sales_completed = fields.Integer(
        related='marketplace_seller_id.seller_sales_completed',
        string="Ventas Concretadas de la Tienda",
        readonly=False,
    )
    seller_is_official_store = fields.Boolean(
        related='marketplace_seller_id.seller_is_official_store',
        string="Tienda Oficial / Mercado Wanka Líder",
        readonly=False,
    )
    seller_on_time_delivery_pct = fields.Integer(
        related='marketplace_seller_id.seller_on_time_delivery_pct',
        string="% Despacho a Tiempo",
        readonly=False,
    )
    seller_good_service_pct = fields.Integer(
        related='marketplace_seller_id.seller_good_service_pct',
        string="% Buena Atención",
        readonly=False,
    )

    # Mapeo con el ERP origen (SOFIA Tenant)
    sofia_remote_product_id = fields.Char(
        string="ID Producto en ERP Vendedor",
        index=True,
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        is_seller_only = (
            self.env.user.has_group('wango_marketplace.group_marketplace_seller')
            and not self.env.user.has_group('wango_marketplace.group_marketplace_manager')
        )
        for vals in vals_list:
            if is_seller_only:
                vals['marketplace_seller_id'] = self.env.user.partner_id.id
                if self.env.user.partner_id.sofia_subscription_active:
                    vals.setdefault('marketplace_status', 'approved')
                else:
                    vals['marketplace_status'] = 'pending'
                    vals['is_published'] = False
        return super(ProductTemplate, self).create(vals_list)

    def action_approve_product(self):
        for rec in self:
            rec.marketplace_status = 'approved'
            rec.is_published = True

    def action_reject_product(self):
        for rec in self:
            rec.marketplace_status = 'rejected'
            rec.is_published = False
