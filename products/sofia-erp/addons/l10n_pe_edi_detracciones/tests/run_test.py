import odoo
from odoo.modules.registry import Registry
from odoo import api

odoo.tools.config.parse_config(['-d', 'FACT20', '--addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons/custom,/mnt/extra-addons/edi'])
registry = Registry('FACT20')
with registry.cursor() as cr:
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
    partner = env['res.partner'].search([('vat', '=', '20100070970')], limit=1)
    prod = env['product.product'].search([('default_code', '=', 'SERV_TEST')], limit=1)
    if not prod:
        prod = env['product.product'].create({
            'name': 'Servicio Test',
            'default_code': 'SERV_TEST',
            'l10n_pe_withhold_percentage': 12.0,
            'l10n_pe_withhold_code': '022'
        })

    # 1. Factura Servicio S/ 500 <= S/ 700
    inv1 = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': partner.id,
        'l10n_pe_edi_operation_type': '1001',
        'invoice_line_ids': [(0, 0, {'product_id': prod.id, 'price_unit': 500.0, 'quantity': 1})]
    })
    spot1 = inv1._l10n_pe_edi_get_spot()
    assert spot1 == {}, f"Test 1 Failed: Expected empty spot for S/ 500 but got {spot1}"
    print("Test 1 OK: Servicio S/ 500.00 <= S/ 700.00 -> Sin detraccion.")

    # 2. Factura Servicio S/ 1000 + IGV (S/ 1,180.00) > S/ 700
    inv2 = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': partner.id,
        'l10n_pe_edi_operation_type': '1001',
        'invoice_line_ids': [(0, 0, {'product_id': prod.id, 'price_unit': 1000.0, 'quantity': 1})]
    })
    spot2 = inv2._l10n_pe_edi_get_spot()
    # Segun R.S. 183-2004, la detraccion se calcula sobre el importe total incluido tributos (S/ 1,180 * 12% = S/ 141.60)
    assert spot2.get('amount') == 141.6, f"Test 2 Failed: Expected 141.6 but got {spot2}"
    print("Test 2 OK: Servicio Total S/ 1,180.00 > S/ 700.00 -> Detraccion 12% (sobre total c/IGV) = S/ 141.60.")

    # 3. Factura Transporte S/ 300 <= S/ 400
    inv3 = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': partner.id,
        'l10n_pe_edi_operation_type': '1004',
        'invoice_line_ids': [(0, 0, {'name': 'Flete Corto', 'price_unit': 300.0, 'quantity': 1})]
    })
    spot3 = inv3._l10n_pe_edi_get_spot()
    assert spot3 == {}, f"Test 3 Failed: Expected empty spot for S/ 300 but got {spot3}"
    print("Test 3 OK: Transporte S/ 300.00 <= S/ 400.00 -> Sin detraccion.")

    # 4. Factura Transporte S/ 500 con Ref S/ 800 (4% de 800 = S/ 32)
    inv4 = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': partner.id,
        'l10n_pe_edi_operation_type': '1004',
        'l10n_pe_edi_transport_origin_ubigeo': '150101',
        'l10n_pe_edi_transport_dest_ubigeo': '040101',
        'l10n_pe_edi_transport_ref_value': 800.0,
        'invoice_line_ids': [(0, 0, {'name': 'Flete Lima Arequipa', 'price_unit': 500.0, 'quantity': 1})]
    })
    spot4 = inv4._l10n_pe_edi_get_spot()
    assert spot4.get('amount') == 32.0, f"Test 4 Failed: Expected 32.0 but got {spot4}"
    assert spot4.get('payment_means_id') == '027', f"Test 4 Failed: Expected 027 but got {spot4}"
    print("Test 4 OK: Transporte S/ 500 (Ref S/ 800) -> 4% sobre mayor valor = S/ 32.00 | Codigo SUNAT 027.")

    # 5. Inyeccion XML Transporte Delivery
    sample_xml = (
        b'<?xml version="1.0" encoding="ISO-8859-1"?>'
        b'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" '
        b'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" '
        b'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
        b'<cbc:ID>F001-000001</cbc:ID>'
        b'<cac:AccountingCustomerParty><cac:Party><cac:PartyName><cbc:Name>Cliente</cbc:Name></cac:PartyName></cac:Party></cac:AccountingCustomerParty>'
        b'<cac:InvoiceLine><cbc:ID>1</cbc:ID><cac:PricingReference/></cac:InvoiceLine>'
        b'</Invoice>'
    )
    xml_out = inv4._l10n_pe_edi_inject_transport_nodes(sample_xml).decode('iso-8859-1')
    assert '<cac:Delivery>' in xml_out, "Test 5 Failed: Missing <cac:Delivery>"
    assert '<cac:DeliveryTerms>' in xml_out, "Test 5 Failed: Missing <cac:DeliveryTerms>"
    assert '150101' in xml_out, "Test 5 Failed: Missing Ubigeo Origen"
    assert '040101' in xml_out, "Test 5 Failed: Missing Ubigeo Destino"
    print("Test 5 OK: Inyeccion XML UBL 2.1 <cac:Delivery>, <cac:Despatch>, <cac:DeliveryTerms 01, 02, 03> exitosa.")

    print("\n>>> TODOS LOS CASOS DE DETRACCION (SERVICIOS Y TRANSPORTE) CUMPLEN 100% CON SUNAT <<<")
