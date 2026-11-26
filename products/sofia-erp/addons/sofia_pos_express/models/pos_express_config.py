# -*- coding: utf-8 -*-
import logging
from odoo import api, exceptions, fields, models

_logger = logging.getLogger(__name__)


class PosExpressConfig(models.Model):
    _name = 'pos.express.config'
    _description = 'Configuración de Caja POS Express'

    name = fields.Char(string='Nombre de la Caja', required=True, default='Caja Principal')
    header_title = fields.Char(
        string='Título en Terminal POS',
        default='POS Express',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        default=lambda self: self.env.company,
        required=True,
    )
    journal_ids = fields.Many2many(
        'account.journal',
        relation='sofia_pos_express_sale_journals',
        string='Diarios de Venta (SUNAT)',
        domain="[('type', '=', 'sale'), ('company_id', '=', company_id)]",
        default=lambda self: self._default_sale_journals(),
        required=True,
    )
    payment_journal_ids = fields.Many2many(
        'account.journal',
        relation='sofia_pos_express_pay_journals',
        string='Métodos de Pago (Efectivo / Yape / Plin / Banco)',
        domain="[('type', 'in', ('cash', 'bank')), ('company_id', '=', company_id)]",
        default=lambda self: self._default_payment_journals(),
        required=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Cajero Principal (opcional)',
        help='Dejar vacío para permitir a cualquier usuario de la empresa.',
    )
    active = fields.Boolean(default=True)

    # Inventario (rebaja automática de stock al cobrar)
    auto_deduct_stock = fields.Boolean(
        string='Descontar Stock Automáticamente',
        default=True,
        help='Genera y valida automáticamente la salida de almacén por cada venta POS.',
    )
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Operación de Entrega (Stock)',
        domain="[('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company_id)]",
        default=lambda self: self._default_picking_type_id(),
    )
    stock_location_id = fields.Many2one(
        'stock.location',
        string='Ubicación de Salida',
        compute='_compute_stock_location_id',
        store=True,
        readonly=False,
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    # Opciones de venta, impuestos y SUNAT
    price_includes_tax = fields.Boolean(
        string='Precios con IGV Incluido',
        default=True,
        help='Si está activo, el precio mostrado en el POS incluye IGV (en NRUS 0% no aplica descuento de IGV).',
    )
    enable_discount = fields.Boolean(
        string='Habilitar Descuento por Línea (%)',
        default=False,
    )
    auto_send_sunat = fields.Boolean(
        string='Enviar a SUNAT / Sofia Gateway al Cobrar',
        default=True,
        help='Firma localmente y despacha el comprobante electrónico a SUNAT / Sofia Gateway inmediatamente al cobrar.',
    )
    ticket_footer = fields.Char(
        string='Pie de Ticket',
        default='¡Gracias por su compra! Consulte su comprobante en gateway.sofiaerp.com/consulta',
    )
    yape_info = fields.Char(
        string='Datos Yape / Plin (opcional)',
        help='Ejemplo: Yape/Plin 999-888-777 a nombre de MI EMPRESA',
    )

    current_session_id = fields.Many2one(
        'pos.express.session',
        string='Turno Abierto Actual',
        compute='_compute_current_session',
    )
    open_session_count = fields.Integer(compute='_compute_current_session')

    @api.model
    def _default_sale_journals(self):
        return self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
            ('active', '=', True),
        ])

    @api.model
    def _default_payment_journals(self):
        return self.env['account.journal'].search([
            ('type', 'in', ('cash', 'bank')),
            ('company_id', '=', self.env.company.id),
            ('active', '=', True),
        ])

    @api.model
    def _default_picking_type_id(self):
        return self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('warehouse_id.company_id', '=', self.env.company.id),
        ], limit=1)

    @api.depends('picking_type_id')
    def _compute_stock_location_id(self):
        for rec in self:
            if rec.picking_type_id and rec.picking_type_id.default_location_src_id:
                rec.stock_location_id = rec.picking_type_id.default_location_src_id.id
            else:
                rec.stock_location_id = False

    def _compute_current_session(self):
        for config in self:
            session = self.env['pos.express.session'].search([
                ('config_id', '=', config.id),
                ('state', '=', 'opened'),
            ], limit=1)
            config.current_session_id = session.id if session else False
            config.open_session_count = 1 if session else 0

    @api.model
    def ensure_default_config(self, company=None):
        """Garantiza que exista al menos una Caja POS Express lista para usar en la empresa."""
        company = company or self.env.company
        cfg = self.sudo().search([('company_id', '=', company.id), ('active', '=', True)], limit=1)
        if cfg:
            return cfg
        sale_j = self.env['account.journal'].sudo().search([
            ('type', '=', 'sale'), ('company_id', '=', company.id), ('active', '=', True)
        ])
        pay_j = self.env['account.journal'].sudo().search([
            ('type', 'in', ('cash', 'bank')), ('company_id', '=', company.id), ('active', '=', True)
        ])
        if not sale_j or not pay_j:
            raise exceptions.UserError(
                'Configura al menos un diario de Ventas y uno de Pago (Efectivo/Banco) antes de abrir POS Express.'
            )
        pick_type = self.env['stock.picking.type'].sudo().search([
            ('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company.id)
        ], limit=1)
        return self.sudo().create({
            'name': f'Caja Principal — {company.name}',
            'header_title': company.name or 'POS Express',
            'company_id': company.id,
            'journal_ids': [(6, 0, sale_j.ids)],
            'payment_journal_ids': [(6, 0, pay_j.ids)],
            'picking_type_id': pick_type.id if pick_type else False,
        })

    def action_open_session(self):
        self.ensure_one()
        if self.current_session_id:
            return self.action_resume_session()
        new_session = self.env['pos.express.session'].create({
            'config_id': self.id,
            'user_id': self.env.uid,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/pos_express?pos_session_id={new_session.id}',
            'target': 'self',
        }

    def action_resume_session(self):
        self.ensure_one()
        if not self.current_session_id:
            raise exceptions.UserError('No hay ningún turno abierto para reanudar.')
        return {
            'type': 'ir.actions.act_url',
            'url': f'/pos_express?pos_session_id={self.current_session_id.id}',
            'target': 'self',
        }
