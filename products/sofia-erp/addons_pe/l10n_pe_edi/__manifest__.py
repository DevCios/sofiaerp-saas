# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'EDI for Peru',
    'version': '0.3',
    'summary': 'Electronic Invoicing for Peru (OSE method) and UBL 2.1',
    'category': 'Accounting/Localizations/EDI',
    'author': 'HFoc',
    'website': 'https://olitech.dev',
    'license': 'GPL-3',
'description': """
EDI Peru Localization
======================
Allow the user to generate the EDI document for Peruvian invoicing.

You can send your documents to Estela (formerly Digiflow) as your OSE
with the certificate, user and password they provided you, or report
directly to SUNAT with your own certificate, SOL user and password,
including contingency sending to SUNAT.

We support sending and cancelling of customer invoices.
    """,
    'depends': [
        'l10n_pe',
        'product_unspsc',
        'account_edi_ubl_cii',
        'certificate',
    ],
    'auto_install': ['l10n_pe'],
    "data": [
        'data/ubl_pe_21_templates.xml',
        'data/uom_data.xml',
        'data/ir_sequence_data.xml',
        'wizards/account_invoice_refund_views.xml',
        'wizards/account_debit_note_views.xml',
        'wizards/account_cancel_wizard_views.xml',
        'views/res_company_views.xml',
        'views/uom_uom_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/res_config_settings_views.xml',
        'views/report_invoice.xml',
        'views/account_menuitem.xml',
        'views/product_views.xml',
        'security/ir.access.csv',
    ],
    'demo': [
        'demo/l10n_pe_edi_demo.xml',
        'demo/product_product_demo.xml',
    ],
    'post_init_hook': 'post_init_hook',
}
