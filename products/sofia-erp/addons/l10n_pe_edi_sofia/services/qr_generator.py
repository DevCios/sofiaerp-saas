# -*- coding: utf-8 -*-
"""
Generador de Texto para Código QR Oficial de SUNAT (Perú).
Conforme a las especificaciones técnicas del Anexo V de la RS 097-2012/SUNAT y modificaciones.
"""


class SUNATQRGenerator:
    @staticmethod
    def generate_invoice_qr(
        company_ruc: str,
        doc_type: str,
        serie: str,
        correlativo: str,
        igv_amount: float,
        total_amount: float,
        invoice_date: str,
        client_doc_type: str,
        client_doc_number: str,
        digest_value: str = "",
    ) -> str:
        """
        Formato obligatorio de 8 campos separados por barra vertical '|':
        RUC | TipoDoc | Serie | Correlativo | IGV | Total | Fecha | TipoDocAdquiriente | NumDocAdquiriente | DigestValue
        """
        clean_correlativo = str(int(correlativo)) if correlativo.isdigit() else correlativo
        fields = [
            str(company_ruc).strip(),
            str(doc_type).strip(),
            str(serie).strip(),
            clean_correlativo.strip(),
            f"{float(igv_amount):.2f}",
            f"{float(total_amount):.2f}",
            str(invoice_date).strip(),
            str(client_doc_type).strip(),
            str(client_doc_number).strip(),
            str(digest_value).strip(),
        ]
        return "|".join(fields) + "|"

    @staticmethod
    def generate_gre_qr(
        company_ruc: str,
        gre_type: str,
        serie: str,
        correlativo: str,
        dest_doc_number: str,
        transfer_date: str,
        gross_weight: float,
        digest_value: str = "",
    ) -> str:
        """
        Formato oficial SUNAT para Guía de Remisión Electrónica:
        RUC_EMISOR|TIPO_DOC|SERIE|CORRELATIVO|DOC_DESTINATARIO|FECHA_EMISION|PESO_TOTAL|DIGEST_VALUE
        """
        clean_correlativo = str(int(correlativo)) if correlativo.isdigit() else correlativo
        fields = [
            str(company_ruc).strip(),
            str(gre_type).strip(),
            str(serie).strip(),
            clean_correlativo.strip(),
            str(dest_doc_number).strip(),
            str(transfer_date).strip(),
            f"{float(gross_weight):.2f}",
            str(digest_value).strip(),
        ]
        return "|".join(fields) + "|"
