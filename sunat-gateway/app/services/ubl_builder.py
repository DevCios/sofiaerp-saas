# -*- coding: utf-8 -*-
from decimal import Decimal, ROUND_HALF_UP
from lxml import etree

from app.models import Issuer
from app.schemas import EmitDocumentRequest

NS_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
NS_CREDIT_NOTE = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
NS_DEBIT_NOTE = "urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
NS_DS = "http://www.w3.org/2000/09/xmldsig#"


def _q2(val: Decimal) -> str:
    return f"{val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def _sub(parent, ns: str, tag: str, text: str | None = None, **attrs):
    el = etree.SubElement(parent, f"{{{ns}}}{tag}", **attrs)
    if text is not None:
        el.text = str(text)
    return el


def build_ubl21_xml(req: EmitDocumentRequest, issuer: Issuer, totals: dict) -> bytes:
    """Genera XML UBL 2.1 oficial SUNAT para Factura (01), Boleta (03), NC (07) y ND (08)."""
    if req.doc_type == "07":
        root_ns, root_tag, line_tag, qty_tag = NS_CREDIT_NOTE, "CreditNote", "CreditNoteLine", "CreditedQuantity"
    elif req.doc_type == "08":
        root_ns, root_tag, line_tag, qty_tag = NS_DEBIT_NOTE, "DebitNote", "DebitNoteLine", "DebitedQuantity"
    else:
        root_ns, root_tag, line_tag, qty_tag = NS_INVOICE, "Invoice", "InvoiceLine", "InvoicedQuantity"

    nsmap = {
        None: root_ns,
        "cac": NS_CAC,
        "cbc": NS_CBC,
        "ext": NS_EXT,
        "ds": NS_DS,
    }
    root = etree.Element(f"{{{root_ns}}}{root_tag}", nsmap=nsmap)

    # 1. Contenedor de Firma Digital XMLDSig
    exts = _sub(root, NS_EXT, "UBLExtensions")
    ext = _sub(exts, NS_EXT, "UBLExtension")
    _sub(ext, NS_EXT, "ExtensionContent")

    # 2. Cabecera UBL 2.1
    _sub(root, NS_CBC, "UBLVersionID", "2.1")
    _sub(root, NS_CBC, "CustomizationID", "2.0")
    doc_number = f"{req.serie}-{req.correlativo}"
    _sub(root, NS_CBC, "ID", doc_number)
    _sub(root, NS_CBC, "IssueDate", req.issue_date)
    _sub(root, NS_CBC, "IssueTime", req.issue_time or "12:00:00")

    if req.doc_type in ("01", "03"):
        _sub(root, NS_CBC, "InvoiceTypeCode", req.doc_type, listID="0101")

    _sub(root, NS_CBC, "DocumentCurrencyCode", req.currency)

    # Referencia para Notas de Crédito / Débito
    if req.doc_type in ("07", "08"):
        disp = _sub(root, NS_CAC, "DiscrepancyResponse")
        _sub(disp, NS_CBC, "ReferenceID", req.related_doc_number)
        _sub(disp, NS_CBC, "ResponseCode", req.note_reason_code or "01")
        _sub(disp, NS_CBC, "Description", req.note_reason_desc or "Anulación / ajuste de operación")

        bref = _sub(root, NS_CAC, "BillingReference")
        iref = _sub(bref, NS_CAC, "InvoiceDocumentReference")
        _sub(iref, NS_CBC, "ID", req.related_doc_number)
        _sub(iref, NS_CBC, "DocumentTypeCode", req.related_doc_type or "01")

    # 3. Referencia a Firma
    sig = _sub(root, NS_CAC, "Signature")
    _sub(sig, NS_CBC, "ID", f"IDSign{issuer.ruc}")
    sparty = _sub(sig, NS_CAC, "SignatoryParty")
    spid = _sub(sparty, NS_CAC, "PartyIdentification")
    _sub(spid, NS_CBC, "ID", issuer.ruc)
    spname = _sub(sparty, NS_CAC, "PartyName")
    _sub(spname, NS_CBC, "Name", issuer.business_name)
    datt = _sub(sig, NS_CAC, "DigitalSignatureAttachment")
    eref = _sub(datt, NS_CAC, "ExternalReference")
    _sub(eref, NS_CBC, "URI", f"#SignatureSOFIA")

    # 4. Emisor (AccountingSupplierParty)
    sup = _sub(root, NS_CAC, "AccountingSupplierParty")
    sup_party = _sub(sup, NS_CAC, "Party")
    sup_pid = _sub(sup_party, NS_CAC, "PartyIdentification")
    _sub(sup_pid, NS_CBC, "ID", issuer.ruc, schemeID="6")
    sup_pname = _sub(sup_party, NS_CAC, "PartyName")
    _sub(sup_pname, NS_CBC, "Name", issuer.trade_name or issuer.business_name)
    sup_legal = _sub(sup_party, NS_CAC, "PartyLegalEntity")
    _sub(sup_legal, NS_CBC, "RegistrationName", issuer.business_name)
    sup_addr = _sub(sup_legal, NS_CAC, "RegistrationAddress")
    _sub(sup_addr, NS_CBC, "ID", issuer.ubigeo or "150101")
    _sub(sup_addr, NS_CBC, "AddressTypeCode", issuer.establishment_code or "0000")
    if issuer.address:
        addr_line = _sub(sup_addr, NS_CAC, "AddressLine")
        _sub(addr_line, NS_CBC, "Line", issuer.address)
    sup_country = _sub(sup_addr, NS_CAC, "Country")
    _sub(sup_country, NS_CBC, "IdentificationCode", "PE")

    # 5. Cliente (AccountingCustomerParty)
    cust = _sub(root, NS_CAC, "AccountingCustomerParty")
    cust_party = _sub(cust, NS_CAC, "Party")
    cust_pid = _sub(cust_party, NS_CAC, "PartyIdentification")
    _sub(cust_pid, NS_CBC, "ID", req.customer.doc_number, schemeID=req.customer.doc_type)
    cust_legal = _sub(cust_party, NS_CAC, "PartyLegalEntity")
    _sub(cust_legal, NS_CBC, "RegistrationName", req.customer.name)

    # Forma de pago al contado para Factura (requisito UBL 2.1 SUNAT)
    if req.doc_type == "01":
        pterms = _sub(root, NS_CAC, "PaymentTerms")
        _sub(pterms, NS_CBC, "ID", "FormaPago")
        _sub(pterms, NS_CBC, "PaymentMeansID", "Contado")

    # 6. Totales de Impuestos (TaxTotal)
    tax_total = _sub(root, NS_CAC, "TaxTotal")
    _sub(tax_total, NS_CBC, "TaxAmount", _q2(totals["igv_amount"]), currencyID=req.currency)

    def _add_tax_subtotal(base: Decimal, tax: Decimal, cat_id: str, scheme_id: str, scheme_name: str, tax_type_code: str):
        if base <= Decimal("0.00"):
            return
        st = _sub(tax_total, NS_CAC, "TaxSubtotal")
        _sub(st, NS_CBC, "TaxableAmount", _q2(base), currencyID=req.currency)
        _sub(st, NS_CBC, "TaxAmount", _q2(tax), currencyID=req.currency)
        cat = _sub(st, NS_CAC, "TaxCategory")
        _sub(cat, NS_CBC, "ID", cat_id)
        sch = _sub(cat, NS_CAC, "TaxScheme")
        _sub(sch, NS_CBC, "ID", scheme_id)
        _sub(sch, NS_CBC, "Name", scheme_name)
        _sub(sch, NS_CBC, "TaxTypeCode", tax_type_code)

    _add_tax_subtotal(totals["taxable_amount"], totals["igv_amount"], "S", "1000", "IGV", "VAT")
    _add_tax_subtotal(totals["exempt_amount"], Decimal("0.00"), "E", "9997", "EXO", "VAT")
    _add_tax_subtotal(totals["unaffected_amount"], Decimal("0.00"), "O", "9998", "INA", "FRE")

    # 7. Totales Monetarios (LegalMonetaryTotal / RequestedMonetaryTotal)
    mon_tag = "RequestedMonetaryTotal" if req.doc_type == "08" else "LegalMonetaryTotal"
    mon = _sub(root, NS_CAC, mon_tag)
    line_ext = totals["taxable_amount"] + totals["exempt_amount"] + totals["unaffected_amount"]
    _sub(mon, NS_CBC, "LineExtensionAmount", _q2(line_ext), currencyID=req.currency)
    _sub(mon, NS_CBC, "TaxInclusiveAmount", _q2(totals["total_amount"]), currencyID=req.currency)
    _sub(mon, NS_CBC, "PayableAmount", _q2(totals["total_amount"]), currencyID=req.currency)

    # 8. Líneas de detalle
    for idx, item in enumerate(req.items or [], start=1):
        line_base = (item.quantity * item.unit_price_without_tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        is_gravado = item.igv_affectation_code.startswith("1")
        line_igv = (line_base * item.igv_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if is_gravado else Decimal("0.00")
        unit_with_tax = (
            item.unit_price_without_tax * (Decimal("1.00") + item.igv_rate) if is_gravado else item.unit_price_without_tax
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        line = _sub(root, NS_CAC, line_tag)
        _sub(line, NS_CBC, "ID", str(idx))
        _sub(line, NS_CBC, qty_tag, f"{item.quantity:.4f}", unitCode=item.unit_code)
        _sub(line, NS_CBC, "LineExtensionAmount", _q2(line_base), currencyID=req.currency)

        pref = _sub(line, NS_CAC, "PricingReference")
        alt = _sub(pref, NS_CAC, "AlternativeConditionPrice")
        _sub(alt, NS_CBC, "PriceAmount", _q2(unit_with_tax), currencyID=req.currency)
        _sub(alt, NS_CBC, "PriceTypeCode", "01")

        ltax = _sub(line, NS_CAC, "TaxTotal")
        _sub(ltax, NS_CBC, "TaxAmount", _q2(line_igv), currencyID=req.currency)
        lst = _sub(ltax, NS_CAC, "TaxSubtotal")
        _sub(lst, NS_CBC, "TaxableAmount", _q2(line_base), currencyID=req.currency)
        _sub(lst, NS_CBC, "TaxAmount", _q2(line_igv), currencyID=req.currency)
        lcat = _sub(lst, NS_CAC, "TaxCategory")
        _sub(lcat, NS_CBC, "Percent", f"{(item.igv_rate * 100 if is_gravado else Decimal('0')):.2f}")
        _sub(lcat, NS_CBC, "TaxExemptionReasonCode", item.igv_affectation_code)
        lsch = _sub(lcat, NS_CAC, "TaxScheme")
        if is_gravado:
            _sub(lsch, NS_CBC, "ID", "1000")
            _sub(lsch, NS_CBC, "Name", "IGV")
            _sub(lsch, NS_CBC, "TaxTypeCode", "VAT")
        elif item.igv_affectation_code.startswith("2"):
            _sub(lsch, NS_CBC, "ID", "9997")
            _sub(lsch, NS_CBC, "Name", "EXO")
            _sub(lsch, NS_CBC, "TaxTypeCode", "VAT")
        else:
            _sub(lsch, NS_CBC, "ID", "9998")
            _sub(lsch, NS_CBC, "Name", "INA")
            _sub(lsch, NS_CBC, "TaxTypeCode", "FRE")

        it = _sub(line, NS_CAC, "Item")
        _sub(it, NS_CBC, "Description", item.description)
        sid = _sub(it, NS_CAC, "SellersItemIdentification")
        _sub(sid, NS_CBC, "ID", item.code)

        pr = _sub(line, NS_CAC, "Price")
        _sub(pr, NS_CBC, "PriceAmount", _q2(item.unit_price_without_tax), currencyID=req.currency)

    return etree.tostring(root, xml_declaration=True, encoding="ISO-8859-1", pretty_print=False)
