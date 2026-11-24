# -*- coding: utf-8 -*-
import logging
import pprint
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.payment import utils as payment_utils
from .mercadopago_request import MercadoPagoAPI

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    mercadopago_txn_id = fields.Char('Transaction ID (Mercado Pago)')
    mercadopago_txn_type = fields.Char('Transaction Type', help='Tipo informativo de transacción')
    mercadopago_tmp_token = fields.Char('Token Temporal Mercado Pago')

    def _get_specific_processing_values(self, processing_values):
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'mercadopago' and self.provider_id.provider != 'mercadopago':
            return res

        return {
            'access_token': payment_utils.generate_access_token(
                processing_values['reference'], processing_values['partner_id']
            )
        }

    def _get_mercadopago_amount(self):
        self.ensure_one()
        if self.provider_id.mercadopago_currency_id and self.currency_id != self.provider_id.mercadopago_currency_id:
            return self.currency_id._convert(
                self.amount,
                self.provider_id.mercadopago_currency_id,
                self.company_id,
                self.create_date or fields.Date.today()
            )
        return self.amount

    def _mercadopago_create_transaction_request(self, kwargs):
        self.ensure_one()
        self.mercadopago_tmp_token = kwargs.get('mercadopago_token')
        mp_api = MercadoPagoAPI(self.provider_id)
        kwargs['validation'] = True if self.provider_id.capture_manually or self.operation == 'validation' else False
        return mp_api.payment(self, form_data=kwargs, amount=self._get_mercadopago_amount())

    def _send_payment_request(self):
        """ Envía cobro automático a Mercado Pago (para suscripciones sin CVV) """
        super()._send_payment_request()
        if self.provider_code != 'mercadopago' and self.provider_id.provider != 'mercadopago':
            return

        if not self.token_id:
            raise UserError(_("Mercado Pago: La transacción no está asociada a ningún token de tarjeta."))

        mp_api = MercadoPagoAPI(self.provider_id)
        # Si es suscripción recurrente, el pago se procesa sin solicitar CVV
        cvv = False if self.operation == 'offline' else True

        res_content = mp_api.payment(self, token=self.token_id, cvv=cvv, amount=self._get_mercadopago_amount())
        _logger.info("Mercado Pago Payment Response:\n%s", pprint.pformat(res_content))

        notification_data = {'reference': self.reference, 'response': res_content}
        self._handle_notification_data('mercadopago', notification_data)

    def _send_refund_request(self, amount_to_refund=None):
        if self.provider_code != 'mercadopago' and self.provider_id.provider != 'mercadopago':
            return super()._send_refund_request(amount_to_refund=amount_to_refund)

        mp_api = MercadoPagoAPI(self.provider_id)
        refund_amount = amount_to_refund or self.amount
        if self.provider_id.mercadopago_currency_id and self.currency_id != self.provider_id.mercadopago_currency_id:
            refund_amount = self.currency_id._convert(
                refund_amount,
                self.provider_id.mercadopago_currency_id,
                self.company_id,
                fields.Date.today()
            )

        res = mp_api.payment_refund(self.provider_reference, amount=refund_amount)
        _logger.info("Mercado Pago Refund Response:\n%s", pprint.pformat(res))

        refund_tx = self._create_refund_transaction(amount_to_refund=amount_to_refund)
        refund_tx._set_done()
        return refund_tx

    def _send_void_request(self, amount_to_void=None):
        super()._send_void_request(amount_to_void=amount_to_void)
        if self.provider_code != 'mercadopago' and self.provider_id.provider != 'mercadopago':
            return

        mp_api = MercadoPagoAPI(self.provider_id)
        res = mp_api.payment_cancel(self.provider_reference)
        _logger.info("Mercado Pago Void Response:\n%s", pprint.pformat(res))
        self._set_canceled()

    @api.model
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'mercadopago':
            return tx

        reference = notification_data.get('external_reference') or notification_data.get('reference')
        if not reference:
            raise ValidationError(_("Mercado Pago: No se recibió la referencia de la transacción."))

        tx = self.search([('reference', '=', reference)], limit=1)
        if not tx:
            raise ValidationError(_("Mercado Pago: No se encontró transacción para la referencia %s.") % reference)
        return tx

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != 'mercadopago' and self.provider_id.provider != 'mercadopago':
            return

        response_content = notification_data.get('response') or notification_data
        mp_id = response_content.get('id') or response_content.get('x_trans_id')
        if mp_id:
            self.provider_reference = str(mp_id)

        status = response_content.get('status')
        message = self._get_mercadopago_response_msg(response_content)

        if status in ['approved', 'processed']:
            if self.state != 'done':
                self._set_done(state_message=message)
            if self.tokenize and not self.token_id:
                self._mercadopago_tokenize_from_response(response_content)
        elif status == 'authorized':
            self._set_authorized(state_message=message)
            if self.tokenize and not self.token_id:
                self._mercadopago_tokenize_from_response(response_content)
        elif status in ['cancelled', 'refunded', 'charged_back', 'rejected']:
            _logger.info('Mercado Pago pago rechazado/cancelado: %s', self.reference)
            self._set_error(state_message=message)
        elif status in ['pending', 'in_process', 'in_mediation']:
            _logger.info('Mercado Pago pago pendiente de revisión: %s', self.reference)
            self._set_pending(state_message=message)
        else:
            error_code = response_content.get('error', 'desconocido')
            self._set_error(f"Mercado Pago: Código de estado inválido '{status}'. Error: {error_code}")

    def _mercadopago_tokenize_from_response(self, data):
        self.ensure_one()
        mp_api = MercadoPagoAPI(self.provider_id)
        customer_id = mp_api.get_customer_profile(self.partner_id.email)
        if customer_id and self.mercadopago_tmp_token:
            try:
                card = mp_api.create_customer_card(customer_id, self.mercadopago_tmp_token)
                token = self.env['payment.token'].create({
                    'provider_id': self.provider_id.id,
                    'payment_details': f"•••• {card.get('last_four_digits', '****')}",
                    'provider_ref': data.get('payment_method_id', 'credit_card'),
                    'bin': card.get('first_six_digits', ''),
                    'partner_id': self.partner_id.id,
                    'card_token': card.get('id', ''),
                    'email': self.partner_id.email,
                    'customer_id': customer_id,
                })
                self.token_id = token.id
                self.tokenize = False
                _logger.info("Token Mercado Pago creado con ID: %s para partner: %s", token.id, self.partner_id.name)
            except Exception as e:
                _logger.exception("Error al tokenizar tarjeta en Mercado Pago: %s", e)

    def _get_mercadopago_response_msg(self, data):
        mercadopago_messages = {
            'accredited': _("¡Listo! Se acreditó tu pago exitosamente."),
            'pending_contingency': _("Estamos procesando tu pago en Mercado Pago. Te avisaremos por email cuando se confirme."),
            'pending_review_manual': _("Pago en revisión manual de seguridad en Mercado Pago."),
            'cc_rejected_bad_filled_card_number': _("Revisa el número de tarjeta ingresado."),
            'cc_rejected_bad_filled_date': _("Revisa la fecha de vencimiento de la tarjeta."),
            'cc_rejected_bad_filled_other': _("Revisa los datos de la tarjeta."),
            'cc_rejected_bad_filled_security_code': _("Código de seguridad CVV incorrecto."),
            'cc_rejected_blacklist': _("No se pudo procesar tu pago. Por favor utiliza otra tarjeta."),
            'cc_rejected_call_for_authorize': _("Debes autorizar el pago ante el banco emisor de tu tarjeta."),
            'cc_rejected_card_disabled': _("Llama a tu banco para activar tu tarjeta o usa otro medio de pago."),
            'cc_rejected_card_error': _("No se pudo procesar el pago. Revisa la información de tu tarjeta."),
            'cc_rejected_duplicated_payment': _("Ya hiciste un pago por este monto. Si necesitas volver a pagar usa otra tarjeta."),
            'cc_rejected_high_risk': _("Pago rechazado por políticas de riesgo de Mercado Pago."),
            'cc_rejected_insufficient_amount': _("Tu tarjeta no tiene fondos suficientes."),
            'cc_rejected_max_attempts': _("Llegaste al límite de intentos permitidos. Intenta con otra tarjeta."),
            'cc_rejected_other_reason': _("Tu banco no procesó el pago. Utiliza otra tarjeta.")
        }
        status_detail = data.get('status_detail')
        return mercadopago_messages.get(status_detail, _("Estado de transacción Mercado Pago: %s") % data.get('status'))
