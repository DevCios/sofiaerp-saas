{
    'name': 'WanGO Core',
    'version': '20.0.1.0.0',
    'summary': 'Core module for WanGO transport and logistics platform',
    'description': """
WanGO Core Infrastructure
=========================
Defines the base structure for the WanGO platform.
- Abstract base models (UUID, company, active)
- Locations (Cities, Agencies, Points)
- Vehicles & Drivers
- Transaction Logging
- Audit System
    """,
    'category': 'Transport',
    'author': 'Antigravity',
    'website': 'https://wango.app',
    'depends': ['base', 'mail', 'web', 'fleet'],
    'data': [
        'security/wango_security.xml',
        'security/ir.access.csv',
        'views/wango_views.xml',
        'views/wango_menus.xml',
        'views/res_config_settings_views.xml',
                'demo/demo_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
