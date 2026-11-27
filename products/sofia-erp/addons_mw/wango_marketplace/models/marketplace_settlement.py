# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MarketplaceSettlement(models.Model):
    _name = 'marketplace.settlement'
    _description = 'Liquidación de Comisiones — Mercado Wanka'
    _order = 'date_end desc, id desc'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nueva Liquidación'),
    )
    seller_id = fields.Many2one(
        'res.partner',
        string='Vendedor',
        required=True,
        domain=[('is_marketplace_seller', '=', True)],
    )
    date_start = fields.Date(string='Fecha Inicio', required=True)
    date_end = fields.Date(string='Fecha Fin', required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('paid', 'Pagado'),
    ], string='Estado', default='draft')

    line_ids = fields.One2many('sale.order.line', 'marketplace_settlement_id', string='Líneas de Venta')

    amount_total = fields.Monetary(string='Ventas Brutas (Total)', compute='_compute_amounts', store=True)
    commission_variable_total = fields.Monetary(string='Comisión Variable (%)', compute='_compute_amounts', store=True)
    platform_fee_total = fields.Monetary(string='Cargo Uso de Plataforma (S/ 0.50/venta)', compute='_compute_amounts', store=True)
    commission_total = fields.Monetary(string='Total Comisión Mercado Wanka', compute='_compute_amounts', store=True)
    amount_to_pay = fields.Monetary(string='Neto a Transferir al Vendedor', compute='_compute_amounts', store=True)

    commission_invoice_id = fields.Many2one(
        'account.move',
        string='Factura de Comisión Mercado Wanka',
        readonly=True,
        copy=False,
        help='Factura emitida por Mercado Wanka al vendedor únicamente por el servicio de comisión y uso de plataforma (nunca por el producto).',
    )

    currency_id = fields.Many2one('res.currency', related='seller_id.currency_id', store=True)

    @api.depends('line_ids.price_total', 'line_ids.marketplace_commission_amount', 'line_ids.order_id.marketplace_platform_fee')
    def _compute_amounts(self):
        for rec in self:
            orders = rec.line_ids.mapped('order_id')
            rec.amount_total = sum(rec.line_ids.mapped('price_total'))
            rec.commission_variable_total = sum(rec.line_ids.mapped('marketplace_commission_amount'))
            rec.platform_fee_total = sum(orders.mapped('marketplace_platform_fee'))
            rec.commission_total = rec.commission_variable_total + rec.platform_fee_total
            rec.amount_to_pay = max(0.0, rec.amount_total - rec.commission_total)

    def action_fetch_lines(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            lines = self.env['sale.order.line'].search([
                ('order_id.marketplace_seller_id', '=', rec.seller_id.id),
                ('order_id.state', 'in', ['sale', 'done']),
                ('order_id.date_order', '>=', rec.date_start),
                ('order_id.date_order', '<=', rec.date_end),
                ('marketplace_settlement_id', '=', False),
            ])
            rec.line_ids = [(6, 0, lines.ids)]

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_('No puedes confirmar una liquidación sin líneas de venta.'))
            if rec.name == _('Nueva Liquidación'):
                rec.name = self.env['ir.sequence'].next_by_code('marketplace.settlement') or 'LIQ-MW'
            rec.state = 'confirmed'

    def action_create_commission_invoice(self):
        """
        Genera la factura de cliente (out_invoice) de Mercado Wanka hacia el Vendedor
        ÚNICAMENTE por la comisión de intermediación + uso de plataforma.
        Los productos son facturados directamente por el vendedor al comprador final.
        """
        for rec in self:
            if rec.commission_invoice_id:
                raise UserError(_('Esta liquidación ya tiene una factura de comisión generada (%s).') % rec.commission_invoice_id.name)
            if rec.commission_total <= 0:
                raise UserError(_('El monto total de comisión debe ser mayor a 0.'))

            invoice_lines = []
            if rec.commission_variable_total > 0:
                invoice_lines.append((0, 0, {
                    'name': f'Comisión por Intermediación Marketplace Mercado Wanka ({rec.name} | {rec.date_start} a {rec.date_end})',
                    'quantity': 1.0,
                    'price_unit': rec.commission_variable_total,
                }))
            if rec.platform_fee_total > 0:
                order_count = len(rec.line_ids.mapped('order_id'))
                invoice_lines.append((0, 0, {
                    'name': f'Uso de Plataforma Mercado Wanka ({order_count} ventas x S/ 0.50)',
                    'quantity': 1.0,
                    'price_unit': rec.platform_fee_total,
                }))

            inv = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': rec.seller_id.id,
                'invoice_origin': rec.name,
                'invoice_line_ids': invoice_lines,
            })
            rec.commission_invoice_id = inv.id
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': inv.id,
                'view_mode': 'form',
            }

    def action_pay(self):
        for rec in self:
            if not rec.commission_invoice_id and rec.commission_total > 0:
                rec.action_create_commission_invoice()
            rec.state = 'paid'


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    marketplace_settlement_id = fields.Many2one('marketplace.settlement', string='Liquidación', readonly=True, copy=False)
