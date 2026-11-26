# -*- coding: utf-8 -*-
{
    'name': 'Perú - Formato Ticket 80mm para Facturación Electrónica',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Impresión en formato Ticket térmico de 80mm para Facturas y Boletas Electrónicas SUNAT',
    'description': """
Formato Ticket 80mm para Perú:
==============================
* Impresión optimizada para impresoras térmicas de 80mm (Epson, Bixolon, Xprinter, etc.).
* Incluye Código QR oficial de SUNAT.
* Incluye Código Hash / Digest Value.
* Importe en letras en español ("SON: ...").
* Leyenda de detracción (SPOT) y cuenta del Banco de la Nación si aplica.
* Cronograma de cuotas para ventas al crédito.
    """,
    'author': 'DevCios / HFoc',
    'website': 'https://olitech.dev',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'l10n_pe',
        'l10n_pe_edi',
    ],
    'data': [
        'report/paperformat.xml',
        'report/report_invoice_ticket_templates.xml',
        'report/report_actions.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
