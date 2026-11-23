# -*- coding: utf-8 -*-
"""
Constructor de Documentos XML UBL 2.1 para SUNAT (Perú).
Conforme a las normas técnicas de Facturación Electrónica y Guías de Remisión.
"""
from xml.etree import ElementTree as ET


class UBLBuilder:
    # Namespaces estándar UBL 2.1 y extensiones SUNAT
    NAMESPACES = {
        'xmlns': "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        'xmlns:cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        'xmlns:cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        'xmlns:ccts': "urn:un:unece:uncefact:documentation:2",
        'xmlns:ds': "http://www.w3.org/2000/09/xmldsig#",
        'xmlns:ext': "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        'xmlns:qdt': "urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2",
        'xmlns:udt': "urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2",
        'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
    }

    @classmethod
    def build_invoice_xml(cls, move) -> str:
        """
        Construye el árbol XML <Invoice> conforme a UBL 2.1 de SUNAT.
        """
        root = ET.Element("Invoice", cls.NAMESPACES)

        # 1. Extensiones UBL para la Firma Digital
        exts = ET.SubElement(root, "ext:UBLExtensions")
        ext = ET.SubElement(exts, "ext:UBLExtension")
        content = ET.SubElement(ext, "ext:ExtensionContent")
        # Placeholder para la firma XML-DSig
        ET.SubElement(content, "ds:Signature", {"Id": "SignatureSOFIA"})

        # 2. Versión UBL y Personalización
        ET.SubElement(root, "cbc:UBLVersionID").text = "2.1"
        ET.SubElement(root, "cbc:CustomizationID").text = "2.0"
        
        # 3. Datos del Comprobante
        ET.SubElement(root, "cbc:ID").text = str(move.name)
        ET.SubElement(root, "cbc:IssueDate").text = str(move.invoice_date)
        ET.SubElement(root, "cbc:InvoiceTypeCode", {"listID": "0101"}).text = str(move.l10n_pe_edi_type)
        ET.SubElement(root, "cbc:DocumentCurrencyCode").text = move.currency_id.name or "PEN"

        # 4. Datos del Emisor (Company)
        supplier = ET.SubElement(root, "cac:AccountingSupplierParty")
        party = ET.SubElement(supplier, "cac:Party")
        party_ident = ET.SubElement(party, "cac:PartyIdentification")
        ET.SubElement(party_ident, "cbc:ID", {"schemeID": "6"}).text = str(move.company_id.vat)
        legal_entity = ET.SubElement(party, "cac:PartyLegalEntity")
        ET.SubElement(legal_entity, "cbc:RegistrationName").text = str(move.company_id.name)

        # 5. Datos del Receptor (Cliente)
        customer = ET.SubElement(root, "cac:AccountingCustomerParty")
        cust_party = ET.SubElement(customer, "cac:Party")
        cust_ident = ET.SubElement(cust_party, "cac:PartyIdentification")
        ET.SubElement(cust_ident, "cbc:ID", {"schemeID": "6"}).text = str(move.partner_id.vat or "00000000")
        cust_legal = ET.SubElement(cust_party, "cac:PartyLegalEntity")
        ET.SubElement(cust_legal, "cbc:RegistrationName").text = str(move.partner_id.name)

        # 6. Totales Monetarios
        tax_total = ET.SubElement(root, "cac:TaxTotal")
        ET.SubElement(tax_total, "cbc:TaxAmount", {"currencyID": move.currency_id.name or "PEN"}).text = f"{move.amount_tax:.2f}"
        
        legal_monetary = ET.SubElement(root, "cac:LegalMonetaryTotal")
        ET.SubElement(legal_monetary, "cbc:PayableAmount", {"currencyID": move.currency_id.name or "PEN"}).text = f"{move.amount_total:.2f}"

        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    @classmethod
    def build_despatch_advice_xml(cls, picking) -> str:
        """
        Construye el XML <DespatchAdvice> para Guía de Remisión Electrónica conforme a SUNAT.
        """
        namespaces_gre = {
            'xmlns': "urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2",
            'xmlns:cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            'xmlns:cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            'xmlns:ds': "http://www.w3.org/2000/09/xmldsig#",
            'xmlns:ext': "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        }
        root = ET.Element("DespatchAdvice", namespaces_gre)

        # Versión y Documento
        ET.SubElement(root, "cbc:UBLVersionID").text = "2.1"
        ET.SubElement(root, "cbc:CustomizationID").text = "2.0"
        ET.SubElement(root, "cbc:ID").text = str(picking.name)
        ET.SubElement(root, "cbc:IssueDate").text = str(picking.scheduled_date)[:10] if picking.scheduled_date else "2026-11-16"
        ET.SubElement(root, "cbc:DespatchAdviceTypeCode").text = str(picking.l10n_pe_gre_type)

        # Emisor
        despatch_supplier = ET.SubElement(root, "cac:DespatchSupplierParty")
        party = ET.SubElement(despatch_supplier, "cac:Party")
        party_ident = ET.SubElement(party, "cac:PartyIdentification")
        ET.SubElement(party_ident, "cbc:ID", {"schemeID": "6"}).text = str(picking.company_id.vat)
        legal_entity = ET.SubElement(party, "cac:PartyLegalEntity")
        ET.SubElement(legal_entity, "cbc:RegistrationName").text = str(picking.company_id.name)

        # Destinatario
        delivery_customer = ET.SubElement(root, "cac:DeliveryCustomerParty")
        cust_party = ET.SubElement(delivery_customer, "cac:Party")
        cust_ident = ET.SubElement(cust_party, "cac:PartyIdentification")
        ET.SubElement(cust_ident, "cbc:ID", {"schemeID": "6"}).text = str(picking.partner_id.vat or "00000000")
        cust_legal = ET.SubElement(cust_party, "cac:PartyLegalEntity")
        ET.SubElement(cust_legal, "cbc:RegistrationName").text = str(picking.partner_id.name)

        # Datos del Envío y Transporte
        shipment = ET.SubElement(root, "cac:Shipment")
        ET.SubElement(shipment, "cbc:ID").text = "SUNAT_ENVIO"
        ET.SubElement(shipment, "cbc:HandlingCode").text = str(picking.l10n_pe_gre_transfer_reason or "01")
        ET.SubElement(shipment, "cbc:GrossWeightMeasure", {"unitCode": "KGM"}).text = f"{picking.l10n_pe_gre_gross_weight:.2f}"
        ET.SubElement(shipment, "cbc:TotalPackageQuantity").text = str(picking.l10n_pe_gre_package_count or 1)

        # Modalidad de Transporte
        stage = ET.SubElement(shipment, "cac:ShipmentStage")
        ET.SubElement(stage, "cbc:TransportModeCode").text = str(picking.l10n_pe_gre_transport_mode or "02")

        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
