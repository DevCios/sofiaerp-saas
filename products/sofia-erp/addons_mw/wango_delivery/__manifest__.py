# -*- coding: utf-8 -*-
{
    'name': 'WanGO Delivery - Gestión Avanzada de Entregas',
    'version': '20.0.1.0.0',
    'summary': 'Módulo de entregas avanzadas: Retiro en tienda, Delivery a domicilio y Agencia.',
    'description': """
        Módulo avanzado de logística y entregas para el e-commerce de WanGO.
        Permite seleccionar:
        - Retiro en Tienda (con stock en tiempo real y mapa Leaflet).
        - Entrega a Domicilio (cobertura por departamento, provincia y distrito).
        - Envío por Agencia (tarifas por peso y volumen del carrito).
    """,
    'category': 'Website/Logistics',
    'author': 'Antigravity',
    'depends': ['website_sale', 'wango_core', 'delivery'],
    'data': [
        'security/ir.access.csv',
        'data/geographic_data.xml',
        'data/delivery_sequence_data.xml',
        'views/store_branch_views.xml',
        'views/delivery_coverage_views.xml',
        'views/delivery_interstate_cost_views.xml',
        'views/agency_views.xml',
        'views/shipment_views.xml',
        'views/shipment_label_report.xml',
        'views/sale_order_views.xml',
        'views/product_views.xml',
        'views/delivery_carrier_views.xml',
        'views/checkout_delivery_templates.xml',
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
            'wango_delivery/static/src/css/delivery_checkout.css',
            'wango_delivery/static/src/js/delivery_checkout.js',
            'wango_delivery/static/src/js/product_delivery_widget.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
