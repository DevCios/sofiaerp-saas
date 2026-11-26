# -*- coding: utf-8 -*-
{
    'name': 'SOFIA ERP - Suite Fiscal SUNAT, GRE & SIRE Perú (Odoo 20)',
    'version': '20.0.2.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Suite completa de Facturación Electrónica UBL 2.1, GRE 09/31, SIRE, PLE, PDT 621, Detracciones y Retenciones para SUNAT Perú',
    'description': """
Meta-módulo troncal de Facturación Electrónica y Cumplimiento Tributario SUNAT para SOFIA ERP (Odoo Community 20):
- Facturas Electrónicas (01), Boletas (03), Notas de Crédito (07), Notas de Débito (08) en UBL 2.1.
- Guías de Remisión Electrónica Remitente (09) y Transportista (31) bajo RS SUNAT vigentes.
- SIRE (Sistema Integrado de Registros Electrónicos — Compras y Ventas).
- Centro de Operaciones SUNAT, PLE Libro Diario (5.1/5.2), PDT 621, Detracciones SPOT y Retenciones IGV.
- Formato Ticket 80mm, Secuencias LATAM, Consulta RUC/DNI (SUNAT/RENIEC) y Tipo de Cambio SUNAT.
    """,
    'author': 'SOFIA Platform Architecture Team',
    'website': 'https://sofiaerp.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'stock',
        'sofia_auth_bridge',
        'l10n_pe_edi',
        'l10n_pe_edi_stock',
        'l10n_pe_sire',
        'l10n_pe_sunat',
        'l10n_pe_invoice_ticket',
        'sofiaerp_pe_vat',
        'account_move_sequence_latam',
        'account_exchange_currency',
    ],
    'data': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
