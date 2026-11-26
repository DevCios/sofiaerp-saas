# -*- coding: utf-8 -*-
{
    'name': 'SOFIA ERP - Suite Fiscal SUNAT, GRE & SIRE Perú (Odoo 20)',
    'version': '20.0.2.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Módulo único consolidado: Facturación Electrónica UBL 2.1, GRE 09/31, SIRE, PLE, PDT 621, Detracciones, Retenciones, Ticket 80mm, RUC/DNI y Tipo de Cambio SUNAT',
    'description': """
Módulo único y consolidado de Facturación Electrónica y Cumplimiento Tributario SUNAT para SOFIA ERP (Odoo Community 20):
- Facturas Electrónicas (01), Boletas (03), Notas de Crédito (07), Notas de Débito (08) en UBL 2.1 con código UNSPSC.
- Guías de Remisión Electrónica Remitente (09) y Transportista (31) bajo RS SUNAT vigentes.
- SIRE (Sistema Integrado de Registros Electrónicos — Compras y Ventas).
- Centro de Operaciones SUNAT, PLE Libro Diario (5.1/5.2), PDT 621, Detracciones SPOT y Retenciones IGV.
- Formato Ticket 80mm, Secuencias LATAM, Consulta RUC/DNI (SUNAT/RENIEC) y Tipo de Cambio SUNAT automático.
    """,
    'author': 'SOFIA Platform Architecture Team',
    'website': 'https://sofiaerp.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'base_setup',
        'account',
        'stock',
        'stock_delivery',
        'sale_stock',
        'purchase',
        'stock_landed_costs',
        'point_of_sale',
        'l10n_pe',
        'l10n_latam_invoice_document',
        'account_edi_ubl_cii',
        'certificate',
        'sofia_auth_bridge',
    ],
    'data': [
        # 1. UNSPSC
        'modules/product_unspsc/views/product_views.xml',
        'modules/product_unspsc/security/ir.access.csv',

        # 2. API Data Token (SUNAT / RENIEC / Tipo de Cambio)
        'modules/api_data_token/security/ir.access.csv',
        'modules/api_data_token/data/ir_config_parameter.xml',
        'modules/api_data_token/data/api_data_provider_credential.xml',
        'modules/api_data_token/views/api_data_provider_credential_views.xml',
        'modules/api_data_token/views/res_config_settings_views.xml',

        # 3. Consulta RUC / DNI Perú
        'modules/sofiaerp_pe_vat/views/res_partner_view.xml',

        # 4. Tipo de Cambio SUNAT
        'modules/account_exchange_currency/security/ir.access.csv',
        'modules/account_exchange_currency/data/ir_cron.xml',
        'modules/account_exchange_currency/wizard/currency_rate_range_wizard_views.xml',
        'modules/account_exchange_currency/views/account_move_views.xml',
        'modules/account_exchange_currency/views/res_currency_views.xml',
        'modules/account_exchange_currency/views/res_currency_rate_views.xml',
        'modules/account_exchange_currency/views/res_company_views.xml',

        # 5. Facturación Electrónica SUNAT UBL 2.1
        'modules/l10n_pe_edi/data/ubl_pe_21_templates.xml',
        'modules/l10n_pe_edi/data/uom_data.xml',
        'modules/l10n_pe_edi/data/ir_sequence_data.xml',
        'modules/l10n_pe_edi/wizards/account_invoice_refund_views.xml',
        'modules/l10n_pe_edi/wizards/account_debit_note_views.xml',
        'modules/l10n_pe_edi/wizards/account_cancel_wizard_views.xml',
        'modules/l10n_pe_edi/views/res_company_views.xml',
        'modules/l10n_pe_edi/views/uom_uom_views.xml',
        'modules/l10n_pe_edi/views/account_move_views.xml',
        'modules/l10n_pe_edi/views/account_tax_views.xml',
        'modules/l10n_pe_edi/views/res_config_settings_views.xml',
        'modules/l10n_pe_edi/views/report_invoice.xml',
        'modules/l10n_pe_edi/views/account_menuitem.xml',
        'modules/l10n_pe_edi/views/product_views.xml',
        'modules/l10n_pe_edi/security/ir.access.csv',

        # 6. Guías de Remisión Electrónica (GRE 09/31)
        'modules/l10n_pe_edi_stock/data/edi_delivery_guide.xml',
        'modules/l10n_pe_edi_stock/views/product_template_view.xml',
        'modules/l10n_pe_edi_stock/views/report_deliveryslip.xml',
        'modules/l10n_pe_edi_stock/views/res_config_settings_views.xml',
        'modules/l10n_pe_edi_stock/views/res_partner_view.xml',
        'modules/l10n_pe_edi_stock/views/stock_picking_views.xml',
        'modules/l10n_pe_edi_stock/views/vehicle_views.xml',
        'modules/l10n_pe_edi_stock/security/ir.access.csv',

        # 6b. Facturación Electrónica en Punto de Venta (POS)
        'modules/l10n_pe_edi_pos/views/pos_order_views.xml',
        'modules/l10n_pe_edi_pos/receipt/pos_order_receipt.xml',

        # 6c. Kardex Físico/Valorizado SUNAT (PLE 12.1 / 13.1) y Costos en Destino (Importadores)
        'modules/l10n_pe_reports_stock/views/product_views.xml',
        'modules/l10n_pe_reports_stock/views/stock_picking_views.xml',
        'modules/l10n_pe_reports_stock/views/stock_warehouse_views.xml',
        'modules/l10n_pe_reports_stock/wizard/stock_move_ple_report.xml',
        'modules/l10n_pe_reports_stock/security/ir.access.csv',

        # 7. Secuencias LATAM para Comprobantes
        'modules/account_move_sequence_latam/security/ir.access.csv',
        'modules/account_move_sequence_latam/views/account_journal_views.xml',
        'modules/account_move_sequence_latam/views/l10n_latam_document_type.xml',

        # 8. Detracciones SPOT
        'modules/l10n_pe_edi_detracciones/views/account_move_views.xml',

        # 9. Formato Ticket 80mm FE
        'modules/l10n_pe_invoice_ticket/report/paperformat.xml',
        'modules/l10n_pe_invoice_ticket/report/report_invoice_ticket_templates.xml',
        'modules/l10n_pe_invoice_ticket/report/report_actions.xml',

        # 10. Retenciones IGV UBL 2.1
        'modules/l10n_pe_edi_retenciones/views/res_partner_views.xml',
        'modules/l10n_pe_edi_retenciones/views/account_move_views.xml',
        'modules/l10n_pe_edi_retenciones/report/report_invoice_retention.xml',

        # 11. SIRE (Registro de Compras y Ventas Electrónico)
        'modules/l10n_pe_sire/security/ir.access.csv',
        'modules/l10n_pe_sire/views/account_move_views.xml',
        'modules/l10n_pe_sire/wizard/sire_export_wizard_views.xml',
        'modules/l10n_pe_sire/views/sire_menus.xml',

        # 12. PLE Libro Diario (5.1 y 5.2)
        'modules/l10n_pe_ple_diario/security/ir.access.csv',
        'modules/l10n_pe_ple_diario/wizard/ple_diario_wizard_views.xml',
        'modules/l10n_pe_ple_diario/views/ple_diario_menus.xml',

        # 13. Declara Fácil PDT 621
        'modules/l10n_pe_pdt_621/security/ir.access.csv',
        'modules/l10n_pe_pdt_621/wizard/pdt621_wizard_views.xml',
        'modules/l10n_pe_pdt_621/views/pdt621_menus.xml',

        # 14. Centro de Operaciones SUNAT (Seguridad, Asistente Rápido y Menú Unificado)
        'modules/l10n_pe_sunat/security/sunat_security.xml',
        'modules/l10n_pe_sunat/security/ir.access.csv',
        'modules/l10n_pe_sunat/wizard/sunat_setup_wizard_views.xml',
        'modules/l10n_pe_sunat/views/sunat_menus.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_pe_edi_sofia/static/src/pos/**/*',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
}
