# -*- coding: utf-8 -*-
{
    'name': 'WanGO Theme (Falabella Style)',
    'version': '20.0.1.0.0',
    'summary': 'Custom Ecommerce Theme mimicking Falabella header',
    'description': 'A completely clean module providing the Falabella.com top search bar, menu, and bottom link bar layout.',
    'category': 'Theme/eCommerce',
    'author': 'Antigravity',
    'company': 'WanGO',
    'depends': ['website_sale'],
    'data': [
        'views/header_falabella.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400;1,600&amp;display=swap',
            'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
            'wango_theme/static/src/css/wango_design_system.css',
            'wango_theme/static/src/css/falabella_header.css',
            'wango_theme/static/src/css/marketplace_header.css',
            'wango_theme/static/src/css/marketplace_sidebar.css',
            'wango_theme/static/src/css/marketplace_megamenu.css',
            'wango_theme/static/src/css/odoo20_compat.css',
            'wango_theme/static/src/js/marketplace_menu.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
