# -*- coding: utf-8 -*-
{
    'name': 'Perú - PLE Libro Diario (5.1 y 5.2 Simplificado)',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Generación de Libro Diario y Libro Diario de Formato Simplificado (PLE 5.1 y 5.2 SUNAT)',
    'description': """
Módulo de Libro Diario Electrónico para el Programa de Libros Electrónicos (PLE) SUNAT
--------------------------------------------------------------------------------------
* Soporte para Libro Diario de Formato Simplificado - Libro 5.2 (Código SUNAT 050200) - Obligatorio para Régimen MYPE Tributario (RMT).
* Soporte para Libro Diario Completo - Libro 5.1 (Código SUNAT 050100) - Régimen General.
* Generación del archivo TXT con la nomenclatura oficial SUNAT: LE{RUC}{AAAA}{MM}00050200001111.txt
* Empaquetado automático en formato ZIP listo para importar y validar en el aplicativo PLE de SUNAT.
* Resumen previo del total de Debe, Haber y balance del periodo.
* Compatible con el Plan Contable General Empresarial (PCGE).
    """,
    'author': 'DevCios / HFoc',
    'website': 'https://olitech.dev',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'l10n_pe',
    ],
    'data': [
        'security/ir.access.csv',
        'wizard/ple_diario_wizard_views.xml',
        'views/ple_diario_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
