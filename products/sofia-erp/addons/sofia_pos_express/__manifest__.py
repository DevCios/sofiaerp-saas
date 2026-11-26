# -*- coding: utf-8 -*-
{
    'name': 'SOFIA POS Express (Ultraligero + SUNAT)',
    'version': '20.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'POS ultraligero de bajo consumo integrado con Facturación SUNAT, Sofia Gateway, NRUS, Diarios y Stock',
    'description': """
POS Express — Punto de Venta Ultraligero para SOFIA ERP (Odoo 20)
=================================================================
- Interfaz standalone ultraligera (Diseño Oficial Odoo 20, Mobile-First y Desktop).
- Búsqueda local ultrarrápida (<5ms) + escáner USB y cámara del celular (BarcodeDetector).
- Integración nativa con Diarios de Venta (FE01/BE01), Facturación SUNAT y Sofia Gateway.
- Soporte automático para Régimen Nuevo RUS (NRUS): solo Boletas sin IGV 0%.
- Consulta RUC/DNI en vivo (sofiaerp_pe_vat), pago mixto (Efectivo/Yape/Plin/Tarjeta),
  rebaja automática de stock, turnos/arqueo de caja, notas de crédito y ticket 58mm/80mm + WhatsApp.
    """,
    'author': 'SOFIA ERP / DevCios',
    'website': 'https://sofiaerp.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'stock',
        'l10n_pe',
        'l10n_pe_edi',
        'l10n_pe_sunat',
    ],
    'data': [
        'security/pos_express_security.xml',
        'security/ir.access.csv',
        'data/pos_express_sequence.xml',
        'views/pos_express_views.xml',
        'views/pos_express_terminal.xml',
    ],
    'post_init_hook': 'post_init_create_yape_plin',
    'installable': True,
    'application': True,
    'auto_install': False,
}
