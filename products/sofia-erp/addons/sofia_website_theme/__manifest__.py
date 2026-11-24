# -*- coding: utf-8 -*-
{
    'name': 'SOFIA ERP — Tema Web & Portal SaaS Corporativo',
    'version': '20.0.1.0.0',
    'category': 'Theme/Corporate',
    'summary': 'Identidad visual, mega-menú con Verticales y Aplicaciones, y bloques SaaS para sofiaerp.com',
    'description': """
Módulo de Identidad Visual y Experiencia Web para SOFIA ERP (Odoo 20)
=====================================================================
* Cabecera SaaS con Mega-menús interactivos: Aplicaciones, Verticales, Comunidad, Precios, Soporte e Inicio de sesión.
* 11 Verticales de negocio: Bodegas, Ferreterías, Retail, Industria, Odontología, Servicios, Restaurante, Comercio Electrónico, Gestión de Flotas, Recursos Humanos, Contabilidad.
* Footer institucional con Libro de Reclamaciones virtual y cumplimiento normativo peruano.
* Snippets prediseñados de alto impacto (Hero SaaS, Grilla de Verticales, Tabla de Precios con integración Mercado Pago).
* Estilos SCSS con diseño premium, tipografía moderna y micro-interacciones.
    """,
    'author': 'SOFIA ERP Platform Architecture Team',
    'website': 'https://sofiaerp.com',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'data/website_menu_data.xml',
        'views/header_templates.xml',
        'views/footer_templates.xml',
        'views/snippets/snippets.xml',
        'views/homepage.xml',
        'views/pricing_page.xml',
        'views/support_page.xml',
        'views/verticales_page.xml',
        'views/libro_reclamaciones_page.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'sofia_website_theme/static/src/scss/theme.scss',
        ],
    },
    'application': False,
    'installable': True,
    'auto_install': False,
}
