{
    'name': 'Mercado Wanka — Core',
    'version': '20.0.1.0.0',
    'summary': 'Núcleo de infraestructura y logística para Mercado Wanka',
    'description': """
Mercado Wanka Core Infrastructure
=================================
Defines the base structure for the Mercado Wanka platform.
- Abstract base models (UUID, company, active)
- Locations (Cities, Agencies, Points)
- Vehicles & Drivers
- Transaction Logging
- Audit System
    """,
    'category': 'Transport',
    'author': 'SOFIA ERP / Mercado Wanka',
    'website': 'https://tienda.sofiaerp.com',
    'depends': ['base', 'mail', 'web', 'account', 'payment', 'fleet'],
    'data': [
        'security/wango_security.xml',
        'security/ir.access.csv',
        'views/wango_views.xml',
        'views/wango_menus.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
