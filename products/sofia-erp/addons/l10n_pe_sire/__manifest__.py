# -*- coding: utf-8 -*-
{
    'name': 'Perú - SIRE (Sistema Integrado de Registros Electrónicos)',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Generación de archivos RVIE (Ventas) y RCE (Compras) para el SIRE de SUNAT',
    'description': """
Módulo de SIRE para la Localización Peruana en Odoo 20
======================================================
* Registro de Ventas e Ingresos Electrónico (RVIE) - Libro 140400 (Anexo 2).
* Registro de Compras Electrónico (RCE) - Libro 080400 (Anexo 8).
* Registro de Compras No Domiciliados - Libro 080500 (Anexo 9).
* Generación de archivos TXT y compresión ZIP con la estructura oficial SUNAT.
* Cálculo automático del Código de Anotación de Registro (CAR).
* Control de detracciones, clasificación de crédito fiscal y validaciones previas.
    """,
    'author': 'DevCios / HFoc',
    'website': 'https://olitech.dev',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'l10n_pe',
        'l10n_latam_invoice_document',
    ],
    'data': [
        'security/ir.access.csv',
        'views/account_move_views.xml',
        'wizard/sire_export_wizard_views.xml',
        'views/sire_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
