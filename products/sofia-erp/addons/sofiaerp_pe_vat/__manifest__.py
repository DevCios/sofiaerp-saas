# -*- coding: utf-8 -*-
{
    'name': 'SofiaERP - Actualizar RUC y DNI (SUNAT / RENIEC)',
    'summary': 'Consulta y validación de RUC y DNI de alta velocidad con API y respaldo SUNAT',
    'description': """
Módulo SofiaERP para consulta y validación de RUC y DNI
-------------------------------------------------------
* Consulta de RUC con API REST de alta disponibilidad y respaldo SUNAT.
* Auto-completado de Razón Social, Estado (Activo), Condición (Habido) y Dirección Fiscal.
* Enlace automático con Ubigeo (Departamento, Provincia, Distrito y Código Postal).
* Consulta de DNI con nombres y apellidos completos.
* Soporte para representantes legales y locales anexos.
    """,
    'author': 'SofiaERP / DevCios',
    'maintainers': ['SofiaERP'],
    'website': 'https://sofiaerp.com',
    'category': 'Localization/Peruvian',
    'version': '20.0.1.0.0',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'l10n_pe',
    ],
    'data': [
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
