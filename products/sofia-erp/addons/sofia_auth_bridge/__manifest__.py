# -*- coding: utf-8 -*-
{
    'name': 'SOFIA ERP Auth Bridge',
    'version': '20.0.1.0.0',
    'category': 'Technical/Authentication',
    'summary': 'Puente de Autenticación OIDC con Validación Criptográfica Offline JWKS',
    'author': 'SOFIA Platform Architecture Team',
    'website': 'https://sofiaerp.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'portal'],
    'data': [
        'views/subscription_portal_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
