# -*- coding: utf-8 -*-
{
    'name': 'Perú - Declara Fácil 621 (Precálculo IGV y Renta MYPE)',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Precálculo mensual del Formulario Virtual 621 (Declara Fácil SUNAT) para Régimen MYPE y General',
    'description': """
Módulo de Precálculo Declara Fácil 621 para Perú
------------------------------------------------
* Resumen de Casillas oficiales de SUNAT para Ventas (100, 101, 105, 109, 112).
* Resumen de Casillas oficiales de SUNAT para Compras (107, 108, 110, 113).
* Determinación del Impuesto Resultante de IGV (Casillas 140, 145, 184).
* Cálculo automático del Pago a Cuenta del Impuesto a la Renta MYPE al 1.0% (Casillas 301, 312, 302).
* Total a pagar consolidado para pago directo en SUNAT Operaciones en Línea.
    """,
    'author': 'DevCios / HFoc',
    'website': 'https://olitech.dev',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'l10n_pe',
        'l10n_pe_sire',
    ],
    'data': [
        'security/ir.access.csv',
        'wizard/pdt621_wizard_views.xml',
        'views/pdt621_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
