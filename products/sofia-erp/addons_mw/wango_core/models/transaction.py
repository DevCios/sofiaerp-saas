from odoo import models, fields, api

class WangoTransaction(models.Model):
    _name = 'wango.transaction'
    _inherit = ['wango.base.mixin']
    _description = 'Transacción Financiera WanGO'
    _order = 'date desc'

    reference = fields.Char(string='Referencia Interna', required=True, copy=False)
    external_reference = fields.Char(string='Referencia Externa (Mercado Pago)')
    
    amount = fields.Monetary(string='Monto', required=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id)
    
    type = fields.Selection([
        ('payment', 'Pago'),
        ('refund', 'Reembolso'),
        ('adjustment', 'Ajuste')
    ], required=True, string='Tipo')
    
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('refunded', 'Reembolsado')
    ], default='pending', string='Estado')
    
    date = fields.Datetime(string='Fecha', default=fields.Datetime.now)
    
    payment_transaction_id = fields.Many2one('payment.transaction', string='Transacción de Pago (Odoo)')
    partner_id = fields.Many2one('res.partner', string='Cliente')
    payment_method_id = fields.Many2one('account.journal', string='Método de Pago')

    notes = fields.Text(string='Notas')
