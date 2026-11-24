# -*- coding: utf-8 -*-
{
    'name': 'Mercado Pago Payment Provider',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Pasarela de Pago Mercado Pago con soporte de Checkout Transparente y Suscripciones para Odoo 20',
    'description': """
Mercado Pago Payment Provider para Odoo 20
==========================================
* Integración con Mercado Pago API (Perú y Latinoamérica).
* Soporte para pagos únicos con tarjetas de crédito / débito.
* Tokenización de tarjetas para pagos recurrentes de suscripciones sin CVV.
* Generador de usuarios de prueba para entorno Sandbox.
* Compatible con la arquitectura multi-tenant de SOFIA ERP.
    """,
    'author': 'Axadoo / SOFIA ERP SaaS Platform',
    'website': 'https://sofiaerp.com',
    'license': 'LGPL-3',
    'depends': ['payment', 'account'],
    'external_dependencies': {
        'python': ['mercadopago'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/payment_provider_views.xml',
        'views/payment_mercadopago_templates.xml',
        'data/payment_provider_data.xml',
        'wizards/check_payments.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}
