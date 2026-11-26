# -*- coding: utf-8 -*-
import base64
import datetime
import logging
import os
import re
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from odoo import api, fields, models, _
from odoo.exceptions import UserError

SERIE_RE = re.compile(r'^[A-Z0-9]{4}$')
DEMO_CERT_PREFIX = '[DEMO BETA]'


class SofiaSunatSetupWizard(models.TransientModel):
    _name = 'sofia.sunat.setup.wizard'
    _description = 'Asistente de Configuración Rápida SUNAT (SOFIA ERP)'

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
    )

    # 1. Datos Fiscales de la Empresa
    ruc = fields.Char(string='RUC (11 dígitos)', required=True, size=11)
    sunat_lookup_status = fields.Char(string='Estado SUNAT', readonly=True)
    company_name = fields.Char(string='Razón Social', required=True)
    street = fields.Char(string='Dirección Fiscal')
    zip_code = fields.Char(string='Ubigeo / ZIP', size=10)
    state_id = fields.Many2one('res.country.state', string='Departamento')
    city_id = fields.Many2one('res.city', string='Provincia')
    l10n_pe_district = fields.Many2one('l10n_pe.res.city.district', string='Distrito')
    address_type_code = fields.Char(
        string='Código Establecimiento Anexo',
        default='0000',
        size=4,
        help='0000 para domicilio fiscal principal según ficha RUC SUNAT.',
    )
    tax_regime = fields.Selection(
        selection=[
            ('general', 'Régimen General / MYPE / RER (Facturas + Boletas con IGV 18%)'),
            ('nrus', 'Nuevo RUS — NRUS (Solo Boletas Electrónicas sin IGV 0%)'),
        ],
        string='Régimen Tributario SUNAT',
        required=True,
        default='general',
        help='Si eliges Nuevo RUS (NRUS), el sistema configurará únicamente Boletas Electrónicas (BE01) '
             'con impuesto Inafecto 0% (código 30) y desactivará las Facturas para cumplir con SUNAT.',
    )
    apply_nrus_tax_to_products = fields.Boolean(
        string='Aplicar impuesto Inafecto 0% (NRUS) a todos los productos existentes',
        default=True,
        help='Reemplaza el IGV 18% por Inafecto 0% (INA / código 30) en los productos vendibles de esta empresa.',
    )

    # 2. Proveedor y Credenciales SUNAT / OSE
    provider = fields.Selection(
        selection=[
            ('sofia_gateway', 'Sofia Gateway — Pasarela Resiliente SUNAT (Recomendado)'),
            ('sunat', 'SUNAT (Servidores Oficiales — Directo)'),
            ('digiflow', 'Estela / Digiflow OSE'),
            ('nubefact', 'NubeFact OSE'),
        ],
        string='Proveedor de Envío Electrónico',
        required=True,
        default='sofia_gateway',
    )
    test_env = fields.Boolean(
        string='Modo Pruebas (SUNAT Beta / Homologación)',
        default=True,
        help='Actívalo para pruebas sin validez tributaria. Desactívalo cuando pases a Producción Real.',
    )
    sol_username = fields.Char(
        string='Usuario SOL Secundario',
        help='Ejemplo en producción: RUC + USUARIO (o solo USUARIO según proveedor). En Beta se usa MODDATOS.',
    )
    sol_password = fields.Char(string='Clave SOL')

    # Opcional: Guías de Remisión Electrónica (GRE 2.0 API REST)
    configure_gre = fields.Boolean(string='Configurar Guías de Remisión Electrónica (GRE 2.0)', default=False)
    gre_client_id = fields.Char(string='GRE Client ID (SUNAT)')
    gre_client_secret = fields.Char(string='GRE Client Secret (SUNAT)')
    gre_sol_username = fields.Char(string='GRE Usuario SOL')
    gre_sol_password = fields.Char(string='GRE Clave SOL')

    # 3. Certificado Digital (.pfx / .p12)
    auto_generate_demo_cert = fields.Boolean(
        string='Generar Certificado Demo (.pfx) para SUNAT Beta',
        default=True,
        help='En Modo Pruebas (SUNAT Beta), genera automáticamente un certificado autofirmado RSA-2048 válido para firmar XML y recibir CDR de pruebas al instante.',
    )
    current_certificate_id = fields.Many2one(
        'certificate.certificate',
        string='Certificado Actual Activo',
        readonly=True,
    )
    certificate_file = fields.Binary(string='Subir Certificado Digital (.pfx / .p12)')
    certificate_filename = fields.Char(string='Nombre de Archivo')
    certificate_password = fields.Char(string='Contraseña del Certificado')

    # 4. Series Electrónicas Automáticas
    configure_series = fields.Boolean(string='Configurar/Crear Diarios y Series Electrónicas', default=True)
    series_preset = fields.Selection(
        selection=[
            ('01', 'Serie 01 — FE01 / BE01 / FC01 / BC01 / FD01 / BD01'),
            ('02', 'Serie 02 — FE02 / BE02 / FC02 / BC02 / FD02 / BD02'),
            ('03', 'Serie 03 — FE03 / BE03 / FC03 / BC03 / FD03 / BD03'),
            ('custom', 'Personalizado (editar manualmente)'),
        ],
        string='Plantilla de Series',
        default='01',
        required=True,
    )
    serie_factura = fields.Char(string='Serie Factura (01)', default='FE01', size=4)
    serie_boleta = fields.Char(string='Serie Boleta (03)', default='BE01', size=4)
    serie_nc_factura = fields.Char(string='Serie Nota Crédito Factura (07)', default='FC01', size=4)
    serie_nc_boleta = fields.Char(string='Serie Nota Crédito Boleta (07)', default='BC01', size=4)
    serie_nd_factura = fields.Char(string='Serie Nota Débito Factura (08)', default='FD01', size=4)
    serie_nd_boleta = fields.Char(string='Serie Nota Débito Boleta (08)', default='BD01', size=4)

    @api.model
    def _get_demo_credentials(self, provider):
        if provider == 'digiflow':
            return ('20557912879MODDATOS', 'moddatos')
        return ('MODDATOS', 'MODDATOS')

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        company = self.env.company
        provider = getattr(company, 'l10n_pe_edi_provider', False) or 'sunat'
        test_env = bool(getattr(company, 'l10n_pe_edi_test_env', True))
        sol_user = company.sudo().l10n_pe_edi_provider_username or ''
        sol_pass = company.sudo().l10n_pe_edi_provider_password or ''
        if test_env and not sol_user:
            sol_user, sol_pass = self._get_demo_credentials(provider)
        current_cert = company.l10n_pe_edi_certificate_id if getattr(company, 'l10n_pe_edi_certificate_id', False) else False
        vals.update({
            'company_id': company.id,
            'ruc': (company.vat or '').strip(),
            'company_name': company.name or '',
            'street': company.street or '',
            'zip_code': company.zip or '',
            'state_id': company.state_id.id if company.state_id else False,
            'city_id': company.partner_id.city_id.id if getattr(company.partner_id, 'city_id', False) else False,
            'l10n_pe_district': company.partner_id.l10n_pe_district.id if getattr(company.partner_id, 'l10n_pe_district', False) else False,
            'address_type_code': getattr(company, 'l10n_pe_edi_address_type_code', False) or '0000',
            'tax_regime': getattr(company, 'l10n_pe_tax_regime', False) or 'general',
            'provider': provider,
            'test_env': test_env,
            'sol_username': sol_user,
            'sol_password': sol_pass if test_env else '',
            'auto_generate_demo_cert': bool(test_env and not current_cert),
            'current_certificate_id': current_cert.id if current_cert else False,
            'gre_client_id': company.sudo().l10n_pe_edi_stock_client_id or '',
            'gre_sol_username': company.sudo().l10n_pe_edi_stock_client_username or '',
        })
        return vals

    @api.onchange('test_env', 'provider')
    def _onchange_test_env_provider(self):
        if self.test_env:
            demo_user, demo_pass = self._get_demo_credentials(self.provider)
            if not self.sol_username or self.sol_username in ('MODDATOS', '20557912879MODDATOS'):
                self.sol_username = demo_user
                self.sol_password = demo_pass
            if not self.certificate_file and not self.current_certificate_id:
                self.auto_generate_demo_cert = True
        else:
            if self.sol_username in ('MODDATOS', '20557912879MODDATOS'):
                self.sol_username = False
                self.sol_password = False
            self.auto_generate_demo_cert = False

    def _generate_demo_certificate_pfx(self, ruc, company_name):
        """Genera un certificado PKCS#12 (.pfx) autofirmado RSA-2048 para pruebas en SUNAT Beta."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        org_name = (company_name or 'SOFIA ERP DEMO')[:64]
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, 'PE'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, org_name),
            x509.NameAttribute(NameOID.COMMON_NAME, f'{ruc} DEMO SUNAT BETA'),
        ])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=365))
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=True,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(private_key, hashes.SHA256())
        )
        password_str = 'sofia_demo_beta'
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            name=f'sunat_demo_{ruc}'.encode('utf-8'),
            key=private_key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(password_str.encode('utf-8')),
        )
        return base64.b64encode(pfx_bytes), password_str

    def _lookup_ruc_sunat(self):
        """Consulta el RUC en vivo en SUNAT reutilizando el motor de sofiaerp_pe_vat."""
        clean_ruc = (self.ruc or '').strip()
        if not re.match(r'^\d{11}$', clean_ruc):
            return False

        Partner = self.env['res.partner']
        if not hasattr(Partner, 'ConsultarRUC'):
            self.sunat_lookup_status = 'Módulo sofiaerp_pe_vat no disponible.'
            return False

        pe_country = self.env.ref('base.pe', raise_if_not_found=False)
        tmp_partner = Partner.new({
            'country_id': pe_country.id if pe_country else False,
            'vat': clean_ruc,
        })
        try:
            tmp_partner.ConsultarRUC(clean_ruc)
            if tmp_partner.name:
                self.company_name = tmp_partner.name
            if tmp_partner.street:
                self.street = tmp_partner.street
            if tmp_partner.zip:
                self.zip_code = tmp_partner.zip
            if tmp_partner.state_id:
                self.state_id = tmp_partner.state_id
            if getattr(tmp_partner, 'city_id', False):
                self.city_id = tmp_partner.city_id
            if getattr(tmp_partner, 'l10n_pe_district', False):
                self.l10n_pe_district = tmp_partner.l10n_pe_district
            estado = getattr(tmp_partner, 'state', '') or ''
            cond = getattr(tmp_partner, 'condition', '') or ''
            self.sunat_lookup_status = f'SUNAT OK — {estado} / {cond}'.strip(' /')
            return True
        except Exception as exc:
            self.sunat_lookup_status = f'No se pudo consultar SUNAT: {exc}'
            return False

    @api.onchange('ruc')
    def _onchange_ruc_lookup(self):
        clean_ruc = (self.ruc or '').strip()
        if len(clean_ruc) == 11 and clean_ruc.isdigit():
            self._lookup_ruc_sunat()

    def action_lookup_ruc(self):
        """Botón manual 'Consultar SUNAT' dentro del Wizard manteniendo el modal abierto."""
        self.ensure_one()
        clean_ruc = (self.ruc or '').strip()
        if not re.match(r'^\d{11}$', clean_ruc):
            raise UserError(_("Ingresa un RUC válido de 11 dígitos antes de consultar SUNAT."))
        self._lookup_ruc_sunat()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.onchange('series_preset')
    def _onchange_series_preset(self):
        if self.series_preset in ('01', '02', '03'):
            num = self.series_preset
            self.serie_factura = f'FE{num}'
            self.serie_boleta = f'BE{num}'
            self.serie_nc_factura = f'FC{num}'
            self.serie_nc_boleta = f'BC{num}'
            self.serie_nd_factura = f'FD{num}'
            self.serie_nd_boleta = f'BD{num}'

    def _validate_series(self):
        series_to_check = [
            ('Boleta', self.serie_boleta),
            ('Nota de Crédito Boleta', self.serie_nc_boleta),
            ('Nota de Débito Boleta', self.serie_nd_boleta),
        ]
        if self.tax_regime != 'nrus':
            series_to_check = [
                ('Factura', self.serie_factura),
                ('Nota de Crédito Factura', self.serie_nc_factura),
                ('Nota de Débito Factura', self.serie_nd_factura),
            ] + series_to_check
        for label, val in series_to_check:
            clean = (val or '').strip().upper()
            if not SERIE_RE.match(clean):
                raise UserError(_(
                    "La serie de %s ('%s') debe tener exactamente 4 caracteres alfanuméricos en mayúsculas (ej: FE01, BE01, FC01, BC01)."
                ) % (label, clean))

    def _upsert_journal_sequence(self, journal, doc_type, prefix):
        if not journal or not doc_type or not prefix:
            return
        prefix = prefix.strip().upper()
        SeqModel = self.env['account.journal.sequence'].sudo()
        existing = SeqModel.search([
            ('journal_id', '=', journal.id),
            ('l10n_latam_document_type_id', '=', doc_type.id),
        ], limit=1)
        if existing:
            if existing.name != prefix:
                existing.write({'name': prefix})
                if existing.sequence_id:
                    existing.sequence_id.write({'prefix': f'{prefix}-'})
        else:
            SeqModel.create({
                'name': prefix,
                'journal_id': journal.id,
                'l10n_latam_document_type_id': doc_type.id,
            })

    def _configure_nrus_taxes(self, company):
        """Adecúa el impuesto de venta por defecto al régimen tributario (Inafecto 0% NRUS vs IGV 18%)."""
        Tax = self.env['account.tax'].sudo()
        if self.tax_regime == 'nrus':
            ina_tax = Tax.search([
                ('company_id', '=', company.id),
                ('type_tax_use', '=', 'sale'),
                ('l10n_pe_edi_tax_code', '=', '9998'),
                ('amount', '=', 0.0),
            ], limit=1)
            if not ina_tax:
                tax_group = self.env['account.tax.group'].sudo().search([
                    ('company_id', '=', company.id),
                    ('l10n_pe_edi_code', '=', 'INA'),
                ], limit=1) or self.env['account.tax.group'].sudo().search([('company_id', '=', company.id)], limit=1)
                ina_vals = {
                    'name': '0% INA (NRUS)',
                    'description': 'INA',
                    'amount': 0.0,
                    'amount_type': 'percent',
                    'type_tax_use': 'sale',
                    'company_id': company.id,
                    'l10n_pe_edi_tax_code': '9998',
                    'l10n_pe_edi_affectation_reason': '30',
                }
                if tax_group:
                    ina_vals['tax_group_id'] = tax_group.id
                ina_tax = Tax.create(ina_vals)
            company.write({'account_sale_tax_id': ina_tax.id})
            if self.apply_nrus_tax_to_products:
                products = self.env['product.template'].sudo().search([
                    ('sale_ok', '=', True),
                    '|', ('company_id', '=', False), ('company_id', '=', company.id),
                ])
                if products:
                    products.with_company(company).write({'taxes_id': [(6, 0, [ina_tax.id])]})
        else:
            igv_tax = Tax.search([
                ('company_id', '=', company.id),
                ('type_tax_use', '=', 'sale'),
                ('l10n_pe_edi_tax_code', '=', '1000'),
                ('amount', '=', 18.0),
            ], limit=1)
            if igv_tax and company.account_sale_tax_id.l10n_pe_edi_tax_code == '9998':
                company.write({'account_sale_tax_id': igv_tax.id})

    def _configure_sales_journals(self, company):
        Journal = self.env['account.journal'].sudo()
        DocType = self.env['l10n_latam.document.type'].sudo()

        pe_docs = DocType.search([('country_id.code', '=', 'PE')])
        doc_01 = pe_docs.filtered(lambda d: d.code == '01')[:1]
        doc_03 = pe_docs.filtered(lambda d: d.code == '03')[:1]
        doc_07_f = pe_docs.filtered(lambda d: d.code == '07' and (d.doc_code_prefix or '').startswith('F'))[:1] or pe_docs.filtered(lambda d: d.code == '07')[:1]
        doc_07_b = pe_docs.filtered(lambda d: d.code == '07' and (d.doc_code_prefix or '').startswith('B'))[:1] or doc_07_f
        doc_08_f = pe_docs.filtered(lambda d: d.code == '08' and (d.doc_code_prefix or '').startswith('F'))[:1] or pe_docs.filtered(lambda d: d.code == '08')[:1]
        doc_08_b = pe_docs.filtered(lambda d: d.code == '08' and (d.doc_code_prefix or '').startswith('B'))[:1] or doc_08_f

        default_income_acc = False
        if self.tax_regime == 'nrus':
            # En NRUS SUNAT prohíbe Facturas (01): archivar diarios de Factura electrónicos
            fac_journals = Journal.search([
                ('company_id', '=', company.id),
                ('type', '=', 'sale'),
                ('l10n_latam_use_documents', '=', True),
                ('code', '=like', 'F%'),
            ])
            if fac_journals:
                default_income_acc = fac_journals[0].default_account_id.id if fac_journals[0].default_account_id else False
                fac_journals.write({'active': False})
        else:
            # Diario 1: Facturas Electrónicas (reactivar si existía archivado)
            inv_code = self.serie_factura.strip().upper()
            inv_journal = Journal.with_context(active_test=False).search([
                ('company_id', '=', company.id),
                ('type', '=', 'sale'),
                ('code', '=', inv_code),
            ], limit=1)
            if not inv_journal:
                inv_journal = Journal.search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'sale'),
                    ('l10n_latam_use_documents', '=', True),
                ], order='sequence, id', limit=1)
            if not inv_journal:
                inv_journal = Journal.create({
                    'name': f'Facturas Electrónicas ({inv_code})',
                    'code': inv_code,
                    'type': 'sale',
                    'company_id': company.id,
                    'l10n_latam_use_documents': True,
                })
            else:
                inv_journal.write({'active': True, 'l10n_latam_use_documents': True})
            default_income_acc = inv_journal.default_account_id.id if inv_journal.default_account_id else False
            self._upsert_journal_sequence(inv_journal, doc_01, self.serie_factura)
            self._upsert_journal_sequence(inv_journal, doc_07_f, self.serie_nc_factura)
            self._upsert_journal_sequence(inv_journal, doc_08_f, self.serie_nd_factura)

        # Diario 2: Boletas de Venta Electrónicas (siempre activo; diario principal en NRUS)
        bol_code = self.serie_boleta.strip().upper()
        bol_journal = Journal.with_context(active_test=False).search([
            ('company_id', '=', company.id),
            ('type', '=', 'sale'),
            ('code', '=', bol_code),
        ], limit=1)
        if not bol_journal:
            bol_journal = Journal.create({
                'name': f'Boletas Electrónicas ({bol_code})',
                'code': bol_code,
                'type': 'sale',
                'company_id': company.id,
                'l10n_latam_use_documents': True,
                'sequence': 1 if self.tax_regime == 'nrus' else 10,
                'default_account_id': default_income_acc,
            })
        else:
            bol_vals = {'active': True, 'l10n_latam_use_documents': True}
            if self.tax_regime == 'nrus':
                bol_vals['sequence'] = 1
            bol_journal.write(bol_vals)

        self._upsert_journal_sequence(bol_journal, doc_03, self.serie_boleta)
        self._upsert_journal_sequence(bol_journal, doc_07_b, self.serie_nc_boleta)
        self._upsert_journal_sequence(bol_journal, doc_08_b, self.serie_nd_boleta)

    def action_apply_configuration(self):
        self.ensure_one()
        company = self.company_id.sudo()

        clean_ruc = (self.ruc or '').strip()
        if not re.match(r'^\d{11}$', clean_ruc):
            raise UserError(_("El RUC debe tener exactamente 11 dígitos numéricos."))

        sol_user = (self.sol_username or '').strip()
        sol_pass = (self.sol_password or '').strip()
        if self.test_env:
            demo_user, demo_pass = self._get_demo_credentials(self.provider)
            if not sol_user:
                sol_user = demo_user
            if not sol_pass:
                sol_pass = demo_pass
        else:
            if not sol_user or not sol_pass:
                raise UserError(_("Para Modo Producción Real debes ingresar tu Usuario SOL Secundario y Clave SOL."))
            if sol_user.upper() in ('MODDATOS', '20557912879MODDATOS'):
                raise UserError(_("El usuario SOL '%s' es solo para Modo Pruebas (Beta). Ingresa tu Usuario SOL Secundario de Producción.") % sol_user)

        if self.configure_series:
            self._validate_series()

        # 1. Actualizar empresa y proveedor SUNAT/OSE
        pe_country = self.env.ref('base.pe', raise_if_not_found=False)
        company_vals = {
            'name': self.company_name.strip(),
            'vat': clean_ruc,
            'street': (self.street or '').strip(),
            'zip': (self.zip_code or '').strip(),
            'state_id': self.state_id.id if self.state_id else False,
            'l10n_pe_edi_address_type_code': (self.address_type_code or '0000').strip(),
            'l10n_pe_tax_regime': self.tax_regime,
            'l10n_pe_edi_provider': self.provider,
            'l10n_pe_edi_test_env': self.test_env,
        }
        if pe_country:
            company_vals['country_id'] = pe_country.id
        if sol_user:
            company_vals['l10n_pe_edi_provider_username'] = sol_user
        if sol_pass:
            company_vals['l10n_pe_edi_provider_password'] = sol_pass

        if self.configure_gre:
            if self.gre_client_id:
                company_vals['l10n_pe_edi_stock_client_id'] = self.gre_client_id.strip()
            if self.gre_client_secret:
                company_vals['l10n_pe_edi_stock_client_secret'] = self.gre_client_secret.strip()
            if self.gre_sol_username:
                company_vals['l10n_pe_edi_stock_client_username'] = self.gre_sol_username.strip()
            if self.gre_sol_password:
                company_vals['l10n_pe_edi_stock_client_password'] = self.gre_sol_password.strip()

        company.write(company_vals)

        # Sincronizar provincia/distrito en el partner de la empresa
        partner_vals = {}
        if self.city_id:
            partner_vals['city_id'] = self.city_id.id
            partner_vals['city'] = self.city_id.name
        if self.l10n_pe_district:
            partner_vals['l10n_pe_district'] = self.l10n_pe_district.id
        if partner_vals and company.partner_id:
            company.partner_id.sudo().write(partner_vals)

        # 2. Registrar Certificado Digital (.pfx / .p12) o generar Demo autofirmado en Modo Pruebas
        cert_note = ''
        if self.certificate_file:
            try:
                cert = self.env['certificate.certificate'].sudo().create({
                    'name': self.certificate_filename or f'Certificado SUNAT {clean_ruc}',
                    'content': self.certificate_file,
                    'content_format': 'pkcs12',
                    'pkcs12_password': self.certificate_password or '',
                    'company_id': company.id,
                })
                company.write({'l10n_pe_edi_certificate_id': cert.id})
            except Exception as exc:
                raise UserError(_(
                    "No se pudo cargar el certificado digital (.pfx). Verifica que el archivo y la contraseña sean correctos.\nDetalle: %s"
                ) % str(exc))
        elif self.test_env and (self.auto_generate_demo_cert or not company.l10n_pe_edi_certificate_id):
            try:
                demo_pfx_b64, demo_pwd = self._generate_demo_certificate_pfx(clean_ruc, self.company_name.strip())
                demo_cert = self.env['certificate.certificate'].sudo().create({
                    'name': f'{DEMO_CERT_PREFIX} Certificado Pruebas SUNAT ({clean_ruc})',
                    'content': demo_pfx_b64,
                    'content_format': 'pkcs12',
                    'pkcs12_password': demo_pwd,
                    'company_id': company.id,
                })
                company.write({'l10n_pe_edi_certificate_id': demo_cert.id})
                cert_note = ' | Certificado Demo Beta generado'
            except Exception as exc:
                raise UserError(_(
                    "No se pudo generar el certificado digital demo para SUNAT Beta.\nDetalle: %s"
                ) % str(exc))
        elif not self.test_env:
            active_cert = company.l10n_pe_edi_certificate_id
            if not active_cert or (active_cert.name or '').startswith(DEMO_CERT_PREFIX):
                raise UserError(_(
                    "Para Modo Producción Real debes subir tu Certificado Digital oficial (.pfx / .p12) en la pestaña '2. Certificado Digital (.pfx)'. No se puede emitir en Producción con un certificado demo."
                ))

        # 3. Configurar Diarios, Series Electrónicas, Billeteras (Yape/Plin) e Impuestos
        if self.configure_series:
            self._configure_sales_journals(company)
        self._configure_nrus_taxes(company)
        self._ensure_yape_plin_journals(company)

        # 4. Modo Híbrido: auto-sincronizar empresa y Clave SOL/GRE a Sofia Gateway (sin exportar .pfx)
        gateway_note = ''
        if self.provider == 'sofia_gateway':
            synced, sync_detail = self._sync_issuer_to_sofia_gateway(company, clean_ruc, sol_user, sol_pass)
            gateway_note = ' | Sincronizado con Sofia Gateway' if synced else f' | Sofia Gateway pendiente ({sync_detail})'

        env_label = "Pruebas (Beta)" if self.test_env else "Producción Real"
        provider_label = dict(self._fields['provider'].selection).get(self.provider, self.provider)
        regime_note = ' | Régimen NRUS (Solo Boletas 0% INA)' if self.tax_regime == 'nrus' else ''
        series_summary = (
            f'{self.serie_boleta} (NC: {self.serie_nc_boleta})'
            if self.tax_regime == 'nrus'
            else f'{self.serie_factura} / {self.serie_boleta} (NC: {self.serie_nc_factura} / {self.serie_nc_boleta})'
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('¡Facturación Electrónica SUNAT Activada!'),
                'message': _(
                    'Proveedor: %s (%s)%s%s%s | Series activas: %s.'
                ) % (
                    provider_label,
                    env_label,
                    regime_note,
                    cert_note,
                    gateway_note,
                    series_summary,
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def _ensure_yape_plin_journals(self, company):
        """Asegura diarios contables Yape y Plin para Facturación y POS Express (no compras web)."""
        Journal = self.env['account.journal'].sudo().with_company(company)
        for wallet_name, wallet_code in (('Yape', 'YAPE'), ('Plin', 'PLIN')):
            exists = Journal.search([
                ('company_id', '=', company.id),
                ('type', '=', 'bank'),
                '|', ('code', '=', wallet_code), ('name', 'ilike', wallet_name),
            ], limit=1)
            if not exists:
                try:
                    Journal.create({
                        'name': wallet_name,
                        'code': wallet_code,
                        'type': 'bank',
                        'company_id': company.id,
                    })
                except Exception:
                    pass

    def _sync_issuer_to_sofia_gateway(self, company, clean_ruc, sol_user, sol_pass):
        """Sincroniza RUC, entorno y credenciales SOL/GRE con Sofia Gateway sin exportar el .pfx."""
        icp = self.env['ir.config_parameter'].sudo()
        base_url = (
            icp.get_param('sofia_gateway.url')
            or os.environ.get('SOFIA_GATEWAY_URL')
            or 'http://sunat-gateway-api:8010'
        ).rstrip('/')
        headers = {'Content-Type': 'application/json'}
        internal_key = os.environ.get('INTERNAL_SERVICE_KEY')
        if internal_key:
            headers['X-Internal-Service-Key'] = internal_key

        ubigeo = (self.zip_code or '').strip()
        if not re.match(r'^\d{6}$', ubigeo):
            ubigeo = '150101'
        est_code = (self.address_type_code or '0000').strip()
        if not re.match(r'^\d{4}$', est_code):
            est_code = '0000'

        payload = {
            'ruc': clean_ruc,
            'business_name': self.company_name.strip(),
            'trade_name': self.company_name.strip(),
            'address': (self.street or '').strip() or None,
            'ubigeo': ubigeo,
            'establishment_code': est_code,
            'is_beta': bool(self.test_env),
            'is_nrus': self.tax_regime == 'nrus',
            'dispatch_policy': 'INSTANT_WITH_RETRY',
            'sol_username': sol_user or None,
            'sol_password': sol_pass or None,
            'tenant_local_signing': True,
            'generate_demo_cert': False,
            'gre_client_id': (self.gre_client_id or '').strip() or None if self.configure_gre else None,
            'gre_client_secret': (self.gre_client_secret or '').strip() or None if self.configure_gre else None,
            'alert_email': company.email or None,
        }
        try:
            resp = requests.post(f'{base_url}/api/v1/issuers', json=payload, headers=headers, timeout=8)
            if resp.status_code in (200, 201):
                return True, 'ok'
            return False, f'HTTP {resp.status_code}'
        except Exception as exc:
            logging.getLogger(__name__).warning("Auto-sync Sofia Gateway omitido para %s: %s", clean_ruc, exc)
            return False, 'sin conexión'
