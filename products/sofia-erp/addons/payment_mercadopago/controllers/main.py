# -*- coding: utf-8 -*-
import json
import logging
import pprint
from odoo import http, _
from odoo.http import request, Response
from odoo.addons.payment import utils as payment_utils
from odoo.exceptions import ValidationError
from ..models.mercadopago_request import MercadoPagoAPI

_logger = logging.getLogger(__name__)


class MercadoPagoController(http.Controller):

    @http.route('/payment/mercadopago/get_provider_info', type='json', auth='public')
    def mercadopago_get_provider_info(self, rec_id, flow='direct'):
        """ Retorna información pública del proveedor para inicializar el checkout JS """
        bin_num = False
        provider_ref = False

        if flow == "token":
            token_sudo = request.env['payment.token'].browse(rec_id).sudo()
            provider_sudo = token_sudo.provider_id.sudo()
            provider_ref = token_sudo.provider_ref
            bin_num = token_sudo.bin
        else:
            provider_sudo = request.env['payment.provider'].sudo().browse(rec_id).exists()

        return {
            'publishable_key': provider_sudo.mercadopago_publishable_key,
            'bin': bin_num,
            'provider_ref': provider_ref,
        }

    @http.route('/payment/mercadopago/payment', type='json', auth='public')
    def mercadopago_payment(self, reference, partner_id, access_token, **kwargs):
        """ Procesa el pago directo desde el formulario web / portal """
        if not payment_utils.check_access_token(access_token, reference, partner_id):
            raise ValidationError(_("Mercado Pago: Datos de pago no verificados o alterados."))

        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)], limit=1)
        if not tx_sudo:
            raise ValidationError(_("Mercado Pago: Transacción no encontrada para la referencia %s.") % reference)

        response_content = tx_sudo._mercadopago_create_transaction_request(kwargs)
        _logger.info("Respuesta de pago Mercado Pago:\n%s", pprint.pformat(response_content))

        notification_data = {'reference': tx_sudo.reference, 'response': response_content}
        tx_sudo._handle_notification_data('mercadopago', notification_data)
        return {'status': response_content.get('status')}

    @http.route([
        '/payment/mercadopago/notify',
        '/payment/mercadopago/notify/<int:provider_id>'
    ], type='json', auth='none', methods=['POST'], csrf=False)
    def mercadopago_notification(self, provider_id=False):
        """ Webhook receptor de notificaciones de pago desde los servidores de Mercado Pago """
        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            data = {}

        _logger.debug("Mercado Pago Webhook Notificación Recibida:\n%s", pprint.pformat(data))

        event_type = data.get('type') or data.get('action')
        if event_type in ['payment', 'payment.created', 'payment.updated']:
            try:
                payment_id = data.get('data', {}).get('id') or data.get('id')
                if not payment_id:
                    return Response('missing payment id', status=200)

                domain = [('provider', '=', 'mercadopago')]
                if provider_id:
                    domain.append(('id', '=', int(provider_id)))
                provider = request.env["payment.provider"].sudo().search(domain, limit=1)

                if provider:
                    mp_api = MercadoPagoAPI(provider)
                    payment_data = mp_api.get_payment(payment_id)
                    external_ref = payment_data.get('external_reference')
                    if external_ref:
                        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', external_ref)], limit=1)
                        if tx_sudo:
                            notification_data = {'reference': external_ref, 'response': payment_data}
                            tx_sudo._handle_notification_data('mercadopago', notification_data)
            except Exception as e:
                _logger.exception("Error procesando webhook de Mercado Pago: %s", e)

        return Response('success', status=200)
