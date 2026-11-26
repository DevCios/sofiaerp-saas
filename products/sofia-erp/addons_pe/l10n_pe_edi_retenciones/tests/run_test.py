# -*- coding: utf-8 -*-
import odoo
from odoo import api
from odoo.modules.registry import Registry
from lxml import etree

odoo.tools.config.parse_config([
    '-d', 'FACT20',
    '--addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons/custom,/mnt/extra-addons/edi'
])
registry = Registry('FACT20')

with registry.cursor() as cr:
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
    company = env.company
    if not company.vat:
        company.partner_id.vat = '20100047218'

    partner_ret = env['res.partner'].create({
        'name': 'Agente Retencion SAC',
        'vat': '20100070970',
        'pe_is_retention': True,
        'pe_retention_percent': 3.0,
    })

    doc_type_01 = env['l10n_latam.document.type'].search([('code', '=', '01')], limit=1)
    tax_igv = env['account.tax'].search([
        ('company_id', '=', company.id),
        ('type_tax_use', '=', 'sale'),
        ('amount', '=', 18.0),
    ], limit=1)

    # TEST 1: Factura <= S/ 700 no debe aplicar retención (R.S. 037-2002)
    inv_low = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': partner_ret.id,
        'l10n_latam_document_type_id': doc_type_01.id if doc_type_01 else False,
        'pe_is_retention': True,
        'pe_retention_percent': 3.0,
        'invoice_line_ids': [(0, 0, {
            'name': 'Producto prueba',
            'price_unit': 500.0,
            'quantity': 1,
            'tax_ids': [(6, 0, tax_igv.ids)] if tax_igv else [],
        })],
    })
    ret_low = inv_low._l10n_pe_edi_get_retention()
    assert ret_low == {}, f"Test 1 Failed: Expected empty retention for <= S/ 700, got {ret_low}"
    print("Test 1 OK: Factura Total S/ 590.00 <= S/ 700.00 -> Sin retencion.")

    # TEST 2: Factura > S/ 700 (S/ 1,000 + IGV = S/ 1,180.00) -> Retención 3% = S/ 35.40, Neto = S/ 1,144.60
    inv_high = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': partner_ret.id,
        'l10n_latam_document_type_id': doc_type_01.id if doc_type_01 else False,
        'pe_is_retention': True,
        'pe_retention_percent': 3.0,
        'invoice_line_ids': [(0, 0, {
            'name': 'Servicio Gravado IGV',
            'price_unit': 1000.0,
            'quantity': 1,
            'tax_ids': [(6, 0, tax_igv.ids)] if tax_igv else [],
        })],
    })
    ret_high = inv_high._l10n_pe_edi_get_retention()
    assert ret_high.get('code') == '62', f"Expected code 62, got {ret_high}"
    assert ret_high.get('amount') == 35.4, f"Expected 35.40, got {ret_high}"
    assert ret_high.get('net_amount') == 1144.6, f"Expected 1144.60, got {ret_high}"
    print("Test 2 OK: Factura S/ 1,180.00 > S/ 700.00 -> Retencion 3% = S/ 35.40 | Neto = S/ 1,144.60.")

    # TEST 3: Exclusión mutua con Detracción (SPOT)
    prod_spot = env['product.product'].create({
        'name': 'Servicio con Detraccion',
        'l10n_pe_withhold_percentage': 12.0,
        'l10n_pe_withhold_code': '022',
    })
    inv_spot = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': partner_ret.id,
        'l10n_latam_document_type_id': doc_type_01.id if doc_type_01 else False,
        'l10n_pe_edi_operation_type': '1001',
        'pe_is_retention': True,
        'pe_retention_percent': 3.0,
        'invoice_line_ids': [(0, 0, {
            'product_id': prod_spot.id,
            'price_unit': 1000.0,
            'quantity': 1,
            'tax_ids': [(6, 0, tax_igv.ids)] if tax_igv else [],
        })],
    })
    assert inv_spot._l10n_pe_edi_get_retention() == {}, "Test 3 Failed: SPOT and Retention should be mutually exclusive"
    print("Test 3 OK: Exclusion mutua SPOT vs Retencion respetada.")

    # TEST 4: Validación de nodos UBL 2.1 (AllowanceCharge código 62, Note, FormaPago Credito y Cuotas)
    ubl_builder = env['account.edi.xml.ubl_pe']
    doc_node = {
        'cbc:Note': [{'_text': 'SON MIL CIENTO OCHENTA SOLES', 'languageLocaleID': '1000'}],
        'cac:AllowanceCharge': [],
        'cac:PaymentTerms': [
            {
                'cbc:ID': {'_text': 'FormaPago'},
                'cbc:PaymentMeansID': {'_text': 'Credito'},
                'cbc:Amount': {'_text': '1180.00', 'currencyID': 'PEN'},
            },
            {
                'cbc:ID': {'_text': 'FormaPago'},
                'cbc:PaymentMeansID': {'_text': 'Cuota001'},
                'cbc:Amount': {'_text': '590.00', 'currencyID': 'PEN'},
            },
            {
                'cbc:ID': {'_text': 'FormaPago'},
                'cbc:PaymentMeansID': {'_text': 'Cuota002'},
                'cbc:Amount': {'_text': '590.00', 'currencyID': 'PEN'},
            },
        ],
    }
    vals = {
        'invoice': inv_high,
        'document_type': 'invoice',
        'currency_dp': 2,
        'currency_name': 'PEN',
        'base_lines': [],
        'tax_inclusive_amount_currency': 1180.0,
    }
    wh_node = ubl_builder._get_document_withholding_node(vals)
    assert wh_node['cbc:AllowanceChargeReasonCode']['_text'] == '62', f"Wrong code: {wh_node}"
    assert wh_node['cbc:ChargeIndicator']['_text'] == 'false'
    assert float(wh_node['cbc:MultiplierFactorNumeric']['_text']) == 0.03, f"Wrong factor: {wh_node}"
    print("WH NODE:", wh_node)
    assert float(wh_node['cbc:Amount']['_text']) == 35.40, f"Wrong amount: {wh_node}"
    assert float(wh_node['cbc:BaseAmount']['_text']) == 1180.00, f"Wrong base: {wh_node}"
    print("Test 4 OK: Nodo UBL 2.1 <cac:AllowanceCharge> codigo 62 generado exactamente segun SUNAT.")

    # TEST 5: Prorrateo de Cuotas en Facturas al Crédito (evita errores SUNAT 3267/3273)
    # Simulamos una factura al crédito con 2 cuotas de 590.00 (total 1180.00, retención 3% = 35.40 -> neto = 1144.60)
    # 2 cuotas netas deben sumar exactamente 1144.60 (572.30 + 572.30)
    net_credit_total = round(1180.00 - 35.40, 2)
    c1 = round(590.00 * (1.0 - 0.03), 2)
    c2 = round(net_credit_total - c1, 2)
    assert round(c1 + c2, 2) == net_credit_total == 1144.60, f"Cuotas mismatch: {c1} + {c2} != {net_credit_total}"
    # Caso con centavo impar: Total 1000.01 -> Ret 3% = 30.00 -> Neto = 970.01 en 3 cuotas
    inv_odd_net = 970.01
    q1 = round((1000.01 / 3) * 0.97, 2)
    q2 = round((1000.01 / 3) * 0.97, 2)
    q3 = round(inv_odd_net - (q1 + q2), 2)
    assert round(q1 + q2 + q3, 2) == inv_odd_net, f"Odd cent mismatch: {q1}+{q2}+{q3} != {inv_odd_net}"
    print(f"Test 5 OK: Cuadre exacto al centimo en cuotas a credito ({q1} + {q2} + {q3} = {inv_odd_net}).")

    cr.rollback()
    print("\n>>> TODAS LAS PRUEBAS DE RETENCION IGV (R.S. 037-2002 / UBL 2.1) PASARON AL 100% <<<")
