{
    'name': 'WanGO Marketplace',
    'version': '20.0.1.0.0',
    'summary': 'Módulo Multi-vendedor para WanGO',
    'description': """
WanGO Marketplace
=================
Permite la operación de un sistema multi-vendedor integrado con E-commerce y WanGO Delivery.
- División de carritos multi-vendedor en órdenes separadas.
- Comisiones calculadas por categoría de producto.
- Panel administrativo restringido para vendedores.
- Aprobación manual de vendedores y productos.
    """,
    'category': 'Website/Marketplace',
    'author': 'Antigravity',
    'website': 'https://wango.app',
    'depends': ['base', 'website_sale', 'sale_management', 'wango_delivery', 'contacts', 'utm', 'stock', 'website_sale_stock'],
    'data': [
        'security/marketplace_groups.xml',
        'security/ir.access.csv',
                'security/hide_menus.xml',
        'data/claim_sequence.xml',
        'data/outbox_cron.xml',
        'views/marketplace_menus.xml',
        'views/marketplace_settlement_views.xml',
        'views/webhook_outbox_views.xml',
        'views/res_partner_views.xml',
        'views/product_category_views.xml',
        'views/product_template_views.xml',
        'views/website_sale_templates.xml',
        'views/portal_templates.xml',
        'views/claim_views.xml',
        'views/legal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'wango_marketplace/static/src/scss/custom_font.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
