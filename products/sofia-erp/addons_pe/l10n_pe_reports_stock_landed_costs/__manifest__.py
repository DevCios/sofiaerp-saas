# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Peru - Stock Reports Landed Costs",
    "countries": ["pe"],
    "description": """
Bridge module to include landed costs as separate lines in the
Peruvian Kardex PLE 13.1 report (operation type 26).
    """,
    "author": "HFoc",
    "category": "Accounting/Localizations/Reporting",
    "website": "https://olitech.dev",
    "license": "GPL-3",
    "depends": [
        "l10n_pe_reports_stock",
        "stock_landed_costs",
    ],
    "auto_install": True,
}
