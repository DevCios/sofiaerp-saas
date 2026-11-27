# -*- coding: utf-8 -*-
{
    'name': 'SOFIA ERP — Conector Mercado Wanka (1-Clic)',
    'version': '20.0.1.0.0',
    'category': 'Sales/Marketplace',
    'summary': 'Crea tu tienda en Mercado Wanka desde el Wizard, publica productos con 1 clic y recibe pedidos listos para facturar SUNAT.',
    'author': 'SOFIA ERP',
    'website': 'https://tienda.sofiaerp.com',
    'depends': ['base', 'product', 'sale_management', 'stock', 'l10n_pe_sunat'],
    'data': [
        'security/ir.access.csv',
        'views/product_template_views.xml',
        'views/sunat_wizard_marketplace_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
