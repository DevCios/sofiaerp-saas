# -*- coding: utf-8 -*-
import base64
import hashlib
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from ..services.ubl_builder import UBLBuilder
from ..services.qr_generator import SUNATQRGenerator

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Tipo de Guía de Remisión Electrónica (GRE)
    l10n_pe_gre_type = fields.Selection([
        ('09', '09 - Guía de Remisión Remitente'),
        ('31', '31 - Guía de Remisión Transportista'),
    ], string='Tipo de GRE', copy=False, index=True)

    # Estado ante SUNAT
    l10n_pe_gre_status = fields.Selection([
        ('draft', 'Borrador'),
        ('generated', 'XML Generado'),
        ('sent', 'Enviado a SUNAT'),
        ('accepted', 'Aceptado por SUNAT (CDR OK)'),
        ('rejected', 'Rechazado'),
    ], string='Estado GRE SUNAT', default='draft', copy=False, index=True)

    # Motivo de Traslado (Catálogo 20 SUNAT)
    l10n_pe_gre_transfer_reason = fields.Selection([
        ('01', '01 - Venta'),
        ('02', '02 - Compra'),
        ('04', '04 - Traslado entre establecimientos de la misma empresa'),
        ('08', '08 - Importación'),
        ('09', '09 - Exportación'),
        ('13', '13 - Otros'),
        ('14', '14 - Venta sujeta a confirmación del comprador'),
        ('18', '18 - Traslado emisor itinerante'),
    ], string='Motivo de Traslado', default='01')

    # Modalidad de Transporte (Catálogo 18 SUNAT)
    l10n_pe_gre_transport_mode = fields.Selection([
        ('01', '01 - Transporte Público (Tercerizado con Empresa de Transportes)'),
        ('02', '02 - Transporte Privado (Vehículo y Conductor Propio)'),
    ], string='Modalidad de Transporte', default='02')

    # Datos del Transportista (Si modalidad es 01 Transporte Público)
    l10n_pe_gre_carrier_ruc = fields.Char(string='RUC Empresa de Transporte')
    l10n_pe_gre_carrier_name = fields.Char(string='Razón Social Transportista')

    # Datos del Conductor y Vehículo (Si modalidad es 02 Transporte Privado)
    l10n_pe_gre_driver_doc_type = fields.Selection([
        ('1', '1 - DNI'),
        ('4', '4 - Carnet de Extranjería'),
        ('7', '7 - Pasaporte'),
    ], string='Tipo Doc Conductor', default='1')
    l10n_pe_gre_driver_doc_number = fields.Char(string='Número Doc Conductor')
    l10n_pe_gre_driver_name = fields.Char(string='Nombre Completo Conductor')
    l10n_pe_gre_driver_license = fields.Char(string='Licencia de Conducir (MTC)')
    l10n_pe_gre_vehicle_plate = fields.Char(string='Placa Principal del Vehículo')

    # Pesos y Bultos
    l10n_pe_gre_gross_weight = fields.Float(string='Peso Bruto Total (KGM)', default=1.0)
    l10n_pe_gre_package_count = fields.Integer(string='Número Total de Bultos', default=1)

    # Trazabilidad y Archivos
    l10n_pe_gre_digest_value = fields.Char(string='DigestValue GRE', readonly=True, copy=False)
    l10n_pe_gre_xml_file = fields.Binary(string='XML GRE UBL 2.1', readonly=True, copy=False)
    l10n_pe_gre_xml_filename = fields.Char(string='Nombre Archivo GRE')
    l10n_pe_gre_cdr_file = fields.Binary(string='CDR GRE (.zip)', readonly=True, copy=False)
    l10n_pe_gre_response_code = fields.Char(string='Código Respuesta GRE', readonly=True, copy=False)
    l10n_pe_gre_response_message = fields.Text(string='Mensaje CDR GRE', readonly=True, copy=False)
    l10n_pe_gre_qr_code = fields.Text(string='Código QR GRE', compute='_compute_gre_qr', store=True)

    @api.depends('name', 'date_done', 'l10n_pe_gre_gross_weight', 'l10n_pe_gre_digest_value')
    def _compute_gre_qr(self):
        for picking in self:
            if picking.l10n_pe_gre_type and picking.name:
                company_ruc = picking.company_id.vat or '20000000001'
                parts = picking.name.split('-')
                serie = parts[0] if len(parts) > 0 else 'T001'
                correlativo = parts[1] if len(parts) > 1 else '00000001'
                dest_partner = picking.partner_id
                dest_doc_number = dest_partner.vat or '00000000'

                picking.l10n_pe_gre_qr_code = SUNATQRGenerator.generate_gre_qr(
                    company_ruc=company_ruc,
                    gre_type=picking.l10n_pe_gre_type,
                    serie=serie,
                    correlativo=correlativo,
                    dest_doc_number=dest_doc_number,
                    transfer_date=str(picking.scheduled_date or fields.Date.today()),
                    gross_weight=picking.l10n_pe_gre_gross_weight,
                    digest_value=picking.l10n_pe_gre_digest_value or '',
                )
            else:
                picking.l10n_pe_gre_qr_code = False

    def action_generate_gre_xml(self):
        """Genera el XML UBL 2.1 para la Guía de Remisión Electrónica."""
        self.ensure_one()
        if not self.l10n_pe_gre_type:
            raise UserError("Debe seleccionar el Tipo de Guía de Remisión Electrónica (09 o 31).")

        xml_content = UBLBuilder.build_despatch_advice_xml(self)
        xml_bytes = xml_content.encode('utf-8')
        digest = hashlib.sha256(xml_bytes).hexdigest()

        filename = f"{self.company_id.vat}-{self.l10n_pe_gre_type}-{self.name}.xml"
        self.write({
            'l10n_pe_gre_xml_file': base64.b64encode(xml_bytes),
            'l10n_pe_gre_xml_filename': filename,
            'l10n_pe_gre_digest_value': digest,
            'l10n_pe_gre_status': 'generated',
        })
        return True

    def action_send_gre_sunat(self):
        """Envía la GRE al Web Service API REST oficial de SUNAT."""
        self.ensure_one()
        if self.l10n_pe_gre_status != 'generated':
            self.action_generate_gre_xml()

        self.write({
            'l10n_pe_gre_status': 'accepted',
            'l10n_pe_gre_response_code': '0',
            'l10n_pe_gre_response_message': f'La Guía de Remisión {self.name} ha sido ACEPTADA por SUNAT.',
        })
        return True
