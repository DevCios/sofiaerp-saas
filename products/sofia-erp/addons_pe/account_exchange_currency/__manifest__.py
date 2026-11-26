{
    'name': 'Account Exchange Currency',
    'version': '20.0.1.3.4',
    'author': 'HFoc',
    'website': 'https://olitech.dev',
    'category': 'Accounting/Accounting',
    'summary': 'Allows you to store the exchange rate value on the invoice which is updated based on the date and currency',
    'description': """
This module allows you to store the exchange rate value on the invoice, which is updated based on the date and currency. This exchange rate is the same one Odoo uses to convert values to the company's currency, but we make it visible on the invoice and store it, allowing it to be easily retrieved in a report. We recommend that modules that require knowing the exchange rate of Invoices for reporting use this module as a dependency.
""",
    'depends': [
        'account',
        'api_data_token',
    ],
    'data': [
        'security/ir.access.csv',
        'data/ir_cron.xml',
        'wizard/currency_rate_range_wizard_views.xml',
        'views/account_move_views.xml',
        'views/res_currency_views.xml',
        'views/res_currency_rate_views.xml',
        'views/res_company_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'GPL-3',
}
