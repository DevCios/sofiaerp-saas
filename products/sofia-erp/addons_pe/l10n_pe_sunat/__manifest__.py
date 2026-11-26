# -*- coding: utf-8 -*-
{
    'name': 'Perú - Centro de Operaciones SUNAT',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Módulo centralizador de obligaciones tributarias SUNAT: SIRE, PLE, Declara Fácil 621 y Consultas',
    'description': """
Centro de Operaciones Tributarias SUNAT (Perú)
----------------------------------------------
Aplicación centralizada para la gestión de las obligaciones tributarias ante la SUNAT:
* Acceso directo e independiente desde el menú principal (App Drawer).
* SIRE: Registro de Ventas (RVIE) y Registro de Compras (RCE).
* Libros Electrónicos (PLE): Libro Diario Simplificado 5.2 (MYPE) y General 5.1.
* Declaraciones Mensuales: Precálculo Declara Fácil 621 (IGV / Renta MYPE).
* Comprobantes Electrónicos de Ventas y Compras.
* Directorio y consulta de RUC / DNI con SUNAT.
* Control de acceso enfocado para el personal contable y administrativo.
    """,
    'author': 'DevCios / HFoc',
    'website': 'https://olitech.dev',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'stock',
        'l10n_pe',
        'l10n_pe_edi',
        'l10n_pe_edi_stock',
        'account_move_sequence_latam',
        'l10n_pe_sire',
        'l10n_pe_ple_diario',
        'l10n_pe_pdt_621',
        'l10n_pe_edi_detracciones',
        'l10n_pe_edi_retenciones',
    ],
    'data': [
        'security/sunat_security.xml',
        'security/ir.access.csv',
        'wizard/sunat_setup_wizard_views.xml',
        'views/sunat_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
