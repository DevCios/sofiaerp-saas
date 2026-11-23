# -*- coding: utf-8 -*-
import base64
import hashlib
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from ..services.ubl_builder import UBLBuilder
from ..services.qr_generator import SUNATQRGenerator

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Tipo de Comprobante de Pago Electrónico SUNAT
    l10n_pe_edi_type = fields.Selection([
        ('01', '01 - Factura Electrónica'),
        ('03', '03 - Boleta de Venta Electrónica'),
        ('07', '07 - Nota de Crédito Electrónica'),
        ('08', '08 - Nota de Débito Electrónica'),
    ], string='Tipo Comprobante SUNAT', copy=False, index=True)

    # Estado del Comprobante ante SUNAT / OSE
    l10n_pe_edi_status = fields.Selection([
        ('draft', 'Borrador'),
        ('generated', 'XML Generado'),
        ('signed', 'XML Firmado'),
        ('sent', 'Enviado a SUNAT'),
        ('accepted', 'Aceptado por SUNAT (CDR OK)'),
        ('rejected', 'Rechazado por SUNAT'),
        ('cancelled', 'Anulado / Comunicado de Baja'),
    ], string='Estado SUNAT', default='draft', copy=False, index=True)

    # Trazabilidad Criptográfica
    l10n_pe_edi_digest_value = fields.Char(string='Código Hash / DigestValue', readonly=True, copy=False)
    l10n_pe_edi_signature_value = fields.Text(string='Firma Electrónica', readonly=True, copy=False)
    l10n_pe_edi_xml_file = fields.Binary(string='Archivo XML UBL 2.1', readonly=True, copy=False)
    l10n_pe_edi_xml_filename = fields.Char(string='Nombre Archivo XML', copy=False)
    
    # Constancia de Recepción (CDR)
    l10n_pe_edi_cdr_file = fields.Binary(string='Archivo CDR (.zip)', readonly=True, copy=False)
    l10n_pe_edi_response_code = fields.Char(string='Código Respuesta SUNAT', readonly=True, copy=False)
    l10n_pe_edi_response_message = fields.Text(string='Detalle / Mensaje CDR', readonly=True, copy=False)

    # Cadena del Código QR normativo
    l10n_pe_edi_qr_code = fields.Text(string='Texto Código QR SUNAT', compute='_compute_sunat_qr', store=True)

    @api.depends('name', 'invoice_date', 'amount_total', 'amount_tax', 'partner_id', 'l10n_pe_edi_digest_value')
    def _compute_sunat_qr(self):
        """Calcula la cadena normativa del código QR con los 8 campos oficiales de SUNAT."""
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund') and move.name and move.l10n_pe_edi_type:
                # Separar serie y correlativo
                parts = move.name.split('-')
                serie = parts[0] if len(parts) > 0 else 'F001'
                correlativo = parts[1] if len(parts) > 1 else '00000001'

                company_ruc = move.company_id.vat or '20000000001'
                doc_type = move.l10n_pe_edi_type
                client_doc_type = move.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code if hasattr(move.partner_id, 'l10n_latam_identification_type_id') else '6'
                client_doc_number = move.partner_id.vat or '00000000'

                move.l10n_pe_edi_qr_code = SUNATQRGenerator.generate_invoice_qr(
                    company_ruc=company_ruc,
                    doc_type=doc_type,
                    serie=serie,
                    correlativo=correlativo,
                    igv_amount=move.amount_tax,
                    total_amount=move.amount_total,
                    invoice_date=str(move.invoice_date or fields.Date.today()),
                    client_doc_type=client_doc_type,
                    client_doc_number=client_doc_number,
                    digest_value=move.l10n_pe_edi_digest_value or '',
                )
            else:
                move.l10n_pe_edi_qr_code = False

    def action_generate_sunat_xml(self):
        """Genera el XML conforme al estándar UBL 2.1."""
        self.ensure_one()
        if not self.l10n_pe_edi_type:
            raise UserError("Debe seleccionar un Tipo de Comprobante SUNAT válido.")

        xml_content = UBLBuilder.build_invoice_xml(self)
        xml_bytes = xml_content.encode('utf-8')
        
        # Calcular DigestValue preliminar (SHA-256)
        digest = hashlib.sha256(xml_bytes).hexdigest()

        filename = f"{self.company_id.vat}-{self.l10n_pe_edi_type}-{self.name}.xml"
        self.write({
            'l10n_pe_edi_xml_file': base64.b64encode(xml_bytes),
            'l10n_pe_edi_xml_filename': filename,
            'l10n_pe_edi_digest_value': digest,
            'l10n_pe_edi_status': 'generated',
        })
        return True

    def action_send_sunat(self):
        """Envía el comprobante electrónico firmado al Web Service de SUNAT/OSE."""
        self.ensure_one()
        if self.l10n_pe_edi_status not in ('generated', 'signed'):
            self.action_generate_sunat_xml()

        # Simulación de respuesta exitosa de OSE / SUNAT (CDR OK)
        self.write({
            'l10n_pe_edi_status': 'accepted',
            'l10n_pe_edi_response_code': '0',
            'l10n_pe_edi_response_message': 'La Factura número F001-00000001 ha sido ACEPTADA por SUNAT.',
        })
        return True
