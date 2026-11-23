# -*- coding: utf-8 -*-
{
    'name': 'SOFIA ERP - Localización Fiscal SUNAT & GRE Perú (Odoo 20)',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Facturación Electrónica UBL 2.1 y Guías de Remisión Electrónica (GRE 09/31) para SUNAT Perú',
    'description': """
Módulo troncal de Facturación Electrónica y Logística Fiscal para Odoo Community 20:
- Facturas Electrónicas (01), Boletas (03), Notas de Crédito (07), Notas de Débito (08).
- Guías de Remisión Electrónica Remitente (09) y Transportista (31) bajo RS SUNAT vigentes.
- Firma digital de XML con certificado X.509 (.pfx) cifrado en reposo.
- Generación de Código QR normativo de 8 campos y representación PDF con Hash.
- Comunicación SOAP/REST con OSE y servidores directos de SUNAT.
- Almacenamiento y parseo de Constancia de Recepción (CDR).
    """,
    'author': 'SOFIA Platform Architecture Team',
    'website': 'https://sofiaerp.com',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'stock', 'sofia_auth_bridge'],
    'data': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
