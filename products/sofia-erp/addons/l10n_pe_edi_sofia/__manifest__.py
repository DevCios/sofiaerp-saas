# -*- coding: utf-8 -*-
{
    'name': 'SOFIA ERP - Paquete Completo SUNAT, GRE, SIRE, POS & Kardex (Meta-Módulo)',
    'version': '20.0.3.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Meta-módulo opcional 1-clic que instala todos los módulos unitarios fiscales de Perú (addons_pe)',
    'description': """
Meta-módulo orquestador de SOFIA ERP para Odoo Community 20.
Todos los módulos fiscales de Perú residen de forma unitaria e independiente en products/sofia-erp/addons_pe/
para permitir instalación, actualización o desinstalación individual desde Aplicaciones.
Instalar este paquete activa de una sola vez la suite completa.
    """,
    'author': 'SOFIA Platform Architecture Team',
    'website': 'https://sofiaerp.com',
    'license': 'LGPL-3',
    'depends': [
        'sofia_auth_bridge',
        'product_unspsc',
        'api_data_token',
        'sofiaerp_pe_vat',
        'account_exchange_currency',
        'l10n_pe_edi',
        'l10n_pe_edi_pos',
        'l10n_pe_edi_stock',
        'l10n_pe_reports_stock',
        'l10n_pe_reports_stock_landed_costs',
        'account_move_sequence_latam',
        'l10n_pe_edi_detracciones',
        'l10n_pe_invoice_ticket',
        'l10n_pe_edi_retenciones',
        'l10n_pe_sire',
        'l10n_pe_ple_diario',
        'l10n_pe_pdt_621',
        'l10n_pe_sunat',
    ],
    'data': [
        'data/ir_cron_exchange_rate.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
