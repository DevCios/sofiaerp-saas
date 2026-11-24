# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError
from .mercadopago_request import MercadoPagoAPI


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    email = fields.Char('Email Comprador', readonly=True)
    customer_id = fields.Char('Mercado Pago Customer ID', readonly=True)
    issuer = fields.Char('Emisor de Tarjeta', readonly=True)
    card_token = fields.Char('Card Token', readonly=True)
    bin = fields.Char('BIN')

    def unlink(self):
        for token in self:
            if token.provider_id.provider == 'mercadopago' and token.customer_id and token.card_token:
                try:
                    mp_api = MercadoPagoAPI(token.provider_id)
                    mp_api.unlink_card_token(token.customer_id, token.card_token)
                except Exception:
                    pass
        return super().unlink()

    def _handle_deactivation_request(self):
        self.ensure_one()
        if self.provider_id.provider == 'mercadopago' and self.customer_id and self.card_token:
            try:
                mp_api = MercadoPagoAPI(self.provider_id)
                mp_api.unlink_card_token(self.customer_id, self.card_token)
            except Exception:
                pass
        return super()._handle_deactivation_request()

    def _handle_reactivation_request(self):
        if self.provider_id.provider == 'mercadopago':
            raise UserError(_('No se puede reactivar un token de Mercado Pago. Debe registrar la tarjeta nuevamente.'))
        return super()._handle_reactivation_request()
