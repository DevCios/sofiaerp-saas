# -*- coding: utf-8 -*-
import logging
import pprint
import requests
from babel.dates import format_datetime
from werkzeug import urls

from odoo import _
from odoo.exceptions import UserError

MP_URL = "https://api.mercadopago.com/"

_logger = logging.getLogger(__name__)

try:
    import mercadopago
    from mercadopago.config import RequestOptions
except ImportError:
    mercadopago = None
    RequestOptions = None
    _logger.debug('Cannot import external_dependency mercadopago')


class MercadoPagoAPI:
    """ Mercado Pago API integration adaptada para Odoo 20 """

    def __init__(self, provider):
        if not mercadopago:
            raise UserError(_("La librería python 'mercadopago' no está instalada."))
        
        request_options = RequestOptions(
            provider.mercadopago_access_token,
            platform_id="SOFIAERP_SAAS_PERU"
        )
        self.mp = mercadopago.SDK(provider.mercadopago_access_token, request_options=request_options)
        self.sandbox = provider.state != "enabled"
        self.mercadopago_access_token = provider.mercadopago_access_token
        self.provider = provider

    def check_response(self, resp):
        if resp.get('status') in [200, 201]:
            return resp.get('response', {})
        elif resp.get('response', {}).get('cause'):
            causes = resp['response']['cause']
            msg = causes[0].get('description') if causes else "Error desconocido"
            code = causes[0].get('code') if causes else 400
            return {'err_code': code, 'err_msg': msg}
        elif resp.get('response', {}).get('error'):
            return {
                'err_code': resp['response'].get('status', 0),
                'err_msg': resp['response'].get('error')
            }
        else:
            return {'err_code': 500, 'err_msg': "Mercado Pago Server Error"}

    def check_api_response(self, resp):
        try:
            resp_json = resp.json()
        except Exception:
            resp_json = {}

        if resp.ok:
            return resp_json
        elif resp_json.get('cause'):
            causes = resp_json['cause']
            msg = causes[0].get('description') if causes else "Error en API"
            code = causes[0].get('code') if causes else resp.status_code
            return {'err_code': code, 'err_msg': msg}
        elif resp_json.get('error'):
            return {
                'err_code': resp_json.get('status', resp.status_code),
                'err_msg': resp_json.get('error')
            }
        else:
            return {'err_code': resp.status_code, 'err_msg': resp.text or "Error HTTP en Mercado Pago"}

    def unlink_card_token(self, customer_id, card_id):
        api_url = MP_URL + f"v1/customers/{customer_id}/cards/{card_id}"
        headers = {"Authorization": f"Bearer {self.mercadopago_access_token}"}
        requests.delete(api_url, headers=headers, timeout=10)

    def create_test_user(self, site_id="MPE"):
        """
        Crea un usuario de prueba en Sandbox (MPE para Perú por defecto)
        """
        api_url = MP_URL + "users/test_user"
        headers = {"Authorization": f"Bearer {self.mercadopago_access_token}"}
        request_data = {"site_id": site_id or "MPE"}
        response = requests.post(api_url, headers=headers, json=request_data, timeout=15)
        resp = self.check_api_response(response)

        if resp.get('err_code'):
            raise UserError(_("Error Mercado Pago al crear usuario de prueba:\nCódigo: %s\nMensaje: %s") % (resp.get('err_code'), resp.get('err_msg')))
        return resp

    def create_preference(self, preference):
        resp = self.mp.preference().create(preference)
        if self.sandbox:
            _logger.info('Preference Result Sandbox:\n%s', resp)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("Mercado Pago Error:\nCódigo: %s\nMensaje: %s") % (resp.get('err_code'), resp.get('err_msg')))
        return resp['sandbox_init_point'] if self.sandbox else resp['init_point']

    def get_customer_profile(self, email):
        values = {'email': email}
        resp = self.mp.customer().search(values)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("Mercado Pago Error:\nCódigo: %s\nMensaje: %s") % (resp.get('err_code'), resp.get('err_msg')))
        try:
            return resp['results'][0].get('id')
        except (IndexError, KeyError):
            return self.create_customer_profile(email)

    def create_customer_profile(self, email):
        values = {'email': email}
        resp = self.mp.customer().create(values)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("Mercado Pago Error:\nCódigo: %s\nMensaje: %s") % (resp.get('err_code'), resp.get('err_msg')))
        return resp.get('id')

    def get_customer_cards(self, customer_id):
        resp = self.mp.card().list_all(customer_id)
        resp = self.check_response(resp)
        if isinstance(resp, dict) and resp.get('err_code'):
            raise UserError(_("Mercado Pago Error:\nCódigo: %s\nMensaje: %s") % (resp.get('err_code'), resp.get('err_msg')))
        return resp

    def token_get_info(self, customer_id, card_token):
        customer_cards = self.get_customer_cards(customer_id)
        if isinstance(customer_cards, list):
            for card in customer_cards:
                if card_token == card.get('id'):
                    return card
        return False

    def create_customer_card(self, customer_id, token):
        values = {"token": token}
        resp = self.mp.card().create(customer_id, values)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("Mercado Pago Error:\nCódigo: %s\nMensaje: %s") % (resp.get('err_code'), resp.get('err_msg')))
        return resp

    def get_card_token(self, card_id):
        values = {"card_id": card_id}
        resp = self.mp.card_token().create(values)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("Mercado Pago Error:\nCódigo: %s\nMensaje: %s") % (resp.get('err_code'), resp.get('err_msg')))
        return resp.get('id')

    def payment(self, tx, token=None, form_data=None, cvv=True, amount=None):
        form_data = form_data or {}
        if token:
            payment_token = tx.mercadopago_tmp_token if cvv and tx.mercadopago_tmp_token else self.get_card_token(token.card_token)
        elif 'mercadopago_token' in form_data:
            payment_token = form_data['mercadopago_token']
        else:
            payment_token = None

        capture, validation_capture_method = self.validation_capture_method(tx, form_data, token)

        base_url = tx.provider_id.get_base_url()
        notification_url = urls.url_join(base_url, f'/payment/mercadopago/notify/{tx.provider_id.id}?source_news=webhooks')

        tx_amount = float(amount or tx.amount)

        values = {
            "token": payment_token,
            "installments": int(form_data.get('installments') or 1),
            "transaction_amount": tx_amount,
            "description": f"SOFIA ERP ~ Pago {tx.reference}",
            "payment_method_id": token.provider_ref if token else form_data.get('mercadopago_payment_method'),
            "binary_mode": True,
            "external_reference": tx.reference,
            "payer": {
                "type": "customer",
                "id": token.customer_id if token else None,
                "email": token.email if token else form_data.get('email'),
                "first_name": tx.partner_name,
            },
            "additional_info": {
                "items": [{
                    "id": tx.provider_id.mercadopago_item_id or tx.reference,
                    "title": tx.provider_id.mercadopago_item_title or f"Orden {tx.reference}",
                    "description": tx.provider_id.mercadopago_item_description or "Servicios ERP",
                    "category_id": tx.provider_id.mercadopago_item_category or "services",
                    "quantity": 1,
                    "unit_price": tx_amount,
                }],
                "payer": {
                    "first_name": tx.partner_name,
                    "phone": {
                        "number": tx.partner_phone or ""
                    },
                    "address": {
                        "zip_code": tx.partner_zip or "15001",
                        "street_name": tx.partner_address or "Lima",
                    },
                },
            },
            "notification_url": notification_url,
            "capture": capture,
        }

        if hasattr(tx.partner_id, 'vat') and tx.partner_id.vat:
            doc_type = "DNI" if len(tx.partner_id.vat) == 8 else "RUC"
            values['payer']['identification'] = {
                "number": tx.partner_id.vat,
                "type": doc_type,
            }

        if form_data.get("issuer"):
            values["issuer_id"] = form_data['issuer']

        _logger.info("Mercado Pago Payment Payload:\n%s", pprint.pformat(values))

        resp = self.mp.payment().create(values)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            _logger.error("Mercado Pago Error Response: %s", resp)
            raise UserError(_("Mercado Pago Error:\nCódigo: %s\nMensaje: %s") % (resp.get('err_code'), resp.get('err_msg')))

        if validation_capture_method == 'refund_payment' and 'id' in resp:
            _logger.info('Refund validation payment ID: %s', resp['id'])
            self.payment_refund(resp['id'])

        return resp

    def payment_refund(self, payment_id, amount=0):
        if amount:
            resp = self.mp.refund().create(payment_id, {"amount": amount})
        else:
            resp = self.mp.refund().create(payment_id)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("Mercado Pago Error al reembolsar:\nCódigo: %s\nMensaje: %s") % (resp.get('err_code'), resp.get('err_msg')))
        return resp

    def payment_cancel(self, payment_id):
        resp = self.mp.payment().update(payment_id, {"status": "cancelled"})
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("Mercado Pago Error al cancelar:\nCódigo: %s\nMensaje: %s") % (resp.get('err_code'), resp.get('err_msg')))
        return resp

    def get_payment(self, payment_id):
        resp = self.mp.payment().get(payment_id)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("Mercado Pago Error al consultar pago:\nCódigo: %s\nMensaje: %s") % (resp.get('err_code'), resp.get('err_msg')))
        return resp

    def validation_capture_method(self, tx, form_data, token):
        if tx.operation != 'validation':
            return True, None
        return True, 'refund_payment'
