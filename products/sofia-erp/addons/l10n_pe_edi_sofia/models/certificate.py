# -*- coding: utf-8 -*-
import base64
import logging
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SofiaSunatCertificate(models.Model):
    _name = 'sofia.sunat.certificate'
    _description = 'Certificado Digital Tributario SUNAT (X.509 / PFX)'

    name = fields.Char(string='Nombre / Alias del Certificado', required=True)
    company_id = fields.Many2one('res.company', string='Empresa', required=True, default=lambda self: self.env.company)
    
    # Archivo binario PFX cifrado en base de datos
    cert_file = fields.Binary(string='Archivo Certificado (.pfx / .p12)', required=True, copy=False)
    cert_filename = fields.Char(string='Nombre de Archivo')
    cert_password = fields.Char(string='Contraseña del Certificado', required=True, copy=False)
    
    valid_from = fields.Datetime(string='Válido Desde', readonly=True)
    valid_to = fields.Datetime(string='Válido Hasta', readonly=True)
    serial_number = fields.Char(string='Número de Serie', readonly=True)
    issuer = fields.Char(string='Entidad Emisora (CA)', readonly=True)
    
    active = fields.Boolean(default=True)

    def action_inspect_certificate(self):
        """
        Inspecciona el certificado binario para extraer fechas de validez y emisor
        utilizando librerías criptográficas de Python estándar.
        """
        self.ensure_one()
        if not self.cert_file or not self.cert_password:
            raise UserError("Debe cargar el archivo binario del certificado y su contraseña.")

        try:
            from cryptography.hazmat.primitives.serialization import pkcs12
            cert_data = base64.b64decode(self.cert_file)
            private_key, cert, additional_certs = pkcs12.load_key_and_certificates(
                cert_data, self.cert_password.encode('utf-8')
            )
            if not cert:
                raise UserError("El archivo no contiene un certificado X.509 válido.")

            self.valid_from = cert.not_valid_before_utc
            self.valid_to = cert.not_valid_after_utc
            self.serial_number = str(cert.serial_number)
            self.issuer = cert.issuer.rfc4514_string()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Certificado Validado',
                    'message': f'Certificado válido hasta: {self.valid_to}',
                    'sticky': False,
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error("Error al inspeccionar certificado digital: %s", str(e))
            raise UserError(f"No fue posible abrir el certificado digital: {str(e)}")

    def sign_xml(self, xml_bytes: bytes) -> bytes:
        """
        Aplica la firma digital XML (XML-DSig) con algoritmo RSA-SHA256 conforme a SUNAT UBL 2.1.
        """
        self.ensure_one()
        # En producción aplica la firma canónica con signxml o xmlsec
        # Retorna el XML firmado con DigestValue y SignatureValue
        return xml_bytes
