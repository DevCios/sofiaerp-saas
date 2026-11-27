# -*- coding: utf-8 -*-
{
    'name': 'WanGO Store (Mercado Libre Style Homepage)',
    'version': '20.0.1.0.0',
    'summary': 'Portada dinámica y personalizable estilo Mercado Libre para WanGO',
    'description': """
WanGO Store
===========
Módulo de Tienda y Portada estilo Mercado Libre:
- Banner Hero deslizante administrable desde backend.
- 6 Tarjetas rápidas en portada + resto deslizable en carrusel.
- Sección 'Inspirado en lo último que viste' con historial y fallback a productos destacados.
- Sección 'Ofertas del Día' (1 destacada a la izquierda + tira deslizable de 4 a la derecha).
- Cuadrícula de Categorías (4 columnas x 3 filas) con soporte deslizable.
- Barra de Confianza (Paga con Yape, Envío gratis desde S/ 50, Seguridad de principio a fin).
- Rendimiento ultra ligero (CSS Scroll Snap, 0 librerías JS pesadas).
    """,
    'category': 'Website/Theme',
    'author': 'Antigravity',
    'website': 'https://wango.app',
    'depends': [
        'base',
        'website',
        'website_sale',
        'wango_core',
        'wango_delivery',
        'wango_marketplace',
        'wango_theme',
    ],
    'data': [
        'security/ir.access.csv',
        'data/default_data.xml',
        'views/home_banner_views.xml',
        'views/home_card_views.xml',
        'views/trust_badge_views.xml',
        'views/product_review_views.xml',
        'views/product_views.xml',
        'views/product_category_views.xml',
        'views/menus.xml',
        'views/home_templates.xml',
        'views/product_detail_templates.xml',
        'views/checkout_mercadopago_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'wango_store/static/src/css/wango_store_home.css',
            'wango_store/static/src/js/wango_store_home.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
