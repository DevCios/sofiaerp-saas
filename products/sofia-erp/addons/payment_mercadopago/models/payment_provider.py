# -*- coding: utf-8 -*-
import logging
from odoo import _, api, fields, models
from .mercadopago_request import MercadoPagoAPI

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    provider = fields.Selection(
        selection_add=[('mercadopago', 'Mercado Pago')],
        ondelete={'mercadopago': 'set default'}
    )
    mercadopago_publishable_key = fields.Char(
        string='Public Key (Mercado Pago)',
        required_if_provider='mercadopago',
        groups='base.group_system'
    )
    mercadopago_access_token = fields.Char(
        string='Access Token (Mercado Pago)',
        required_if_provider='mercadopago',
        groups='base.group_system'
    )
    mercadopago_site_id = fields.Selection(
        selection=[
            ('MPE', 'Perú (MPE - PEN)'),
            ('MLA', 'Argentina (MLA - ARS)'),
            ('MLM', 'México (MLM - MXN)'),
            ('MLC', 'Chile (MLC - CLP)'),
            ('MCO', 'Colombia (MCO - COP)'),
            ('MLB', 'Brasil (MLB - BRL)'),
        ],
        string='País / Región Mercado Pago',
        default='MPE',
        required_if_provider='mercadopago',
        help="Código de país para usuarios de prueba y validación de moneda en Mercado Pago."
    )
    mercadopago_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda de Cobro Forzada',
        help="Moneda opcional en la que se procesarán los pagos en Mercado Pago (ej. PEN / Soles)."
    )
    is_validation = fields.Boolean(
        string='Modo de Validación',
        help="Indica si la operación actual es una validación de tarjeta."
    )

    # Configuración de Ítem en Mercado Pago
    mercadopago_item_id = fields.Char('Item ID', default='SOFIA_ERP')
    mercadopago_item_title = fields.Char('Título de Ítem', default='Suscripción SOFIA ERP SaaS')
    mercadopago_item_description = fields.Char('Descripción de Ítem', default='Servicio de Facturación Electrónica SUNAT')
    mercadopago_item_category = fields.Selection(
        selection=[
            ('services', "Servicios Generales"),
            ('virtual_goods', "Bienes Virtuales / Software"),
            ('computing', "Computación & Software"),
            ('others', "Otras Categorías"),
        ],
        string='Categoría en Mercado Pago',
        default='virtual_goods'
    )
    mercadopago_capture_method = fields.Selection(
        selection=[
            ('deferred_capture', 'Captura diferida'),
            ('refund_payment', 'Reembolsar pago tras validación'),
        ],
        string='Método de captura en validación',
        default='refund_payment'
    )

    def action_create_mercadopago_test_user(self):
        """
        Genera un usuario de prueba en Sandbox para el país configurado (MPE Perú por defecto)
        """
        self.ensure_one()
        mp_api = MercadoPagoAPI(self)
        values = mp_api.create_test_user(site_id=self.mercadopago_site_id or "MPE")
        
        msg = _(
            "Usuario de Prueba Mercado Pago ({site_status}):\n\n"
            "• Email: {email}\n"
            "• Password: {password}\n"
            "• Nickname: {nickname}\n"
            "• ID: {id}\n"
        ).format(**values)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Usuario Sandbox Creado con Éxito"),
                "message": msg,
                "type": "success",
                "sticky": True,
            },
        }

    @api.model
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """ Filtrar compatibilidad de proveedores en Odoo 20 """
        providers = super()._get_compatible_providers(*args, currency_id=currency_id, **kwargs)
        return providers
