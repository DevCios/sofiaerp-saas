# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Peru - Stock Reports",
    "countries": ["pe"],
    "description": """
Electronic stock reports
    - PLE 12.1: Permanent Inventory Record in Physical Units
    - PLE 13.1: Permanent Valued Inventory Record
    """,
    "author": "HFoc",
    "category": "Accounting/Localizations/Reporting",
    "website": "https://olitech.dev",
    "license": "GPL-3",
    "depends": [
        "l10n_pe_edi",
        "purchase",
        "sale_stock",
    ],
    "data": [
        "views/product_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_warehouse_views.xml",
        "wizard/stock_move_ple_report.xml",
        'security/ir.access.csv',
    ],
}
