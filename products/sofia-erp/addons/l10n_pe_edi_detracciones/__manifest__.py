# -*- coding: utf-8 -*-
{
    'name': 'Perú - Detracciones SPOT (Servicios y Transporte de Carga)',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Control normativo de detracciones SPOT: servicios (S/ 700), transporte de carga (S/ 400) y UBL 2.1',
    'description': """
Módulo de Detracciones SPOT para la Localización Peruana (SUNAT)
----------------------------------------------------------------
* Cumplimiento estricto de la R.S. 183-2004/SUNAT (Servicios > S/ 700.00).
* Cumplimiento estricto de la R.S. 073-2006/SUNAT (Transporte de Carga > S/ 400.00 y tasa 4%).
* Cálculo sobre el mayor valor entre el precio pactado y el valor referencial del MTC.
* Campos especializados para facturas de transporte: Ubigeos de origen/destino y tramo de viaje.
* Inyección de nodos UBL 2.1 oficiales: cac:Delivery, cac:Despatch y cac:DeliveryTerms (01, 02, 03).
* Detección flexible de la cuenta del Banco de la Nación (evita bloqueos innecesarios).
    """,
    'author': 'SofiaERP / DevCios',
    'website': 'https://sofiaerp.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'l10n_pe',
        'l10n_pe_edi',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
