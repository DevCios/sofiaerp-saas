# -*- coding: utf-8 -*-
{
    'name': 'Perú - Facturación con Retención del IGV (SUNAT UBL 2.1)',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Facturación electrónica UBL 2.1 para operaciones sujetas a Retención del IGV (3%, Código 62 y Cuotas Netas)',
    'description': """
Módulo de Facturación con Retención del IGV para Perú (SUNAT)
-------------------------------------------------------------
Implementa la normativa oficial de la R.S. 037-2002/SUNAT y R.S. 193-2020/SUNAT para facturas emitidas a Agentes de Retención:
* Detección automática de Agente de Retención en el contacto (sincronizado con padrón SUNAT).
* Validación del umbral mínimo legal de S/ 700.00 (incluyendo conversión de moneda extranjera al TC oficial).
* Exclusión mutua automática con Detracciones (SPOT) conforme a norma SUNAT.
* Generación oficial en XML UBL 2.1: nodo AllowanceCharge código 62, nota legal y prorrateo exacto de cuotas en crédito (evita errores SUNAT 3267/3273).
* Representación impresa en Factura PDF A4 y Ticket Térmico 80mm.
    """,
    'author': 'SofiaERP / DevCios',
    'website': 'https://sofiaerp.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'l10n_pe',
        'l10n_pe_edi',
        'l10n_pe_edi_detracciones',
        'l10n_pe_invoice_ticket',
        'sofiaerp_pe_vat',
    ],
    'data': [
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'report/report_invoice_retention.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
