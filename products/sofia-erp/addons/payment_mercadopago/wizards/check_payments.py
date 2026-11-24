# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, _
from odoo.exceptions import UserError
from ..models.mercadopago_request import MercadoPagoAPI

_logger = logging.getLogger(__name__)


class PaymentMercadopagoCheckPayment(models.TransientModel):
    _name = "payment.mercadopago.check_payment"
    _description = "Conciliador y Verificador de Pagos Mercado Pago"

    provider_id = fields.Many2one('payment.provider', domain="[('code', '=', 'mercadopago')]", required=True)
    date_from = fields.Date(string='Desde', required=True, default=fields.Date.today)
    date_to = fields.Date(string='Hasta', required=True, default=fields.Date.today)
    line_ids = fields.One2many('payment.mercadopago.check_payment.line', 'check_id', string='Líneas')
    confirmed = fields.Boolean('Solo Confirmados', default=True)
    no_match = fields.Boolean('Solo Diferencias')

    def check_status(self, mp_status, odoo_state):
        states = {
            'pending': 'pending',
            'approved': 'done',
            'authorized': 'authorized',
            'in_process': 'pending',
            'in_mediation': 'pending',
            'rejected': 'cancel',
            'cancelled': 'cancel',
            'refunded': 'done',
            'charged_back': 'done'
        }
        return odoo_state == states.get(mp_status)

    def action_search_payments(self):
        mp_api = MercadoPagoAPI(self.provider_id)
        lines = []
        self.line_ids = False
        try:
            payments = mp_api.mp.payment().search(filters={
                'begin_date': f"{self.date_from}T00:00:00.000Z",
                'end_date': f"{self.date_to}T23:59:59.000Z",
                'limit': 100
            })
            results = payments.get('response', {}).get('results', [])
            for payment in results:
                ext_ref = payment.get('external_reference')
                tx = self.env['payment.transaction'].search([('reference', '=', ext_ref)], limit=1)
                if self.no_match and tx and self.check_status(payment.get('status'), tx.state):
                    continue
                lines.append((0, 0, {
                    'mp_id': str(payment.get('id')),
                    'mp_amount': payment.get('transaction_amount', 0.0),
                    'mp_state': payment.get('status'),
                    'mp_external_reference': ext_ref,
                    'transaction_id': tx.id if tx else False
                }))
        except Exception as e:
            raise UserError(_("Error al consultar pagos en Mercado Pago: %s") % e)

        self.line_ids = lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.mercadopago.check_payment',
            'res_id': self.id,
            'target': 'new',
            'views': [(self.env.ref('payment_mercadopago.check_payments_view_form').id, 'form')],
        }


class PaymentMercadopagoCheckPaymentLine(models.TransientModel):
    _name = "payment.mercadopago.check_payment.line"
    _description = "Línea de Conciliación Mercado Pago"

    check_id = fields.Many2one('payment.mercadopago.check_payment')
    transaction_id = fields.Many2one('payment.transaction', string='Transacción Odoo')
    transaction_state = fields.Selection(string='Estado Odoo', related='transaction_id.state')
    mp_amount = fields.Float(string='Monto MP')
    mp_id = fields.Char(string='ID Pago MP')
    mp_state = fields.Char(string='Estado MP')
    mp_external_reference = fields.Char(string='Referencia Externa')
