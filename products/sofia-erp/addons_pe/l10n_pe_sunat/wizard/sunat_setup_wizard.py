# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError

SERIE_RE = re.compile(r'^[A-Z0-9]{4}$')


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

    # 2. Proveedor y Credenciales SUNAT / OSE
    provider = fields.Selection(
        selection=[
            ('sunat', 'SUNAT (Servidores Oficiales — Por defecto)'),
            ('digiflow', 'Estela / Digiflow OSE'),
            ('nubefact', 'NubeFact OSE'),
        ],
        string='Proveedor de Envío Electrónico',
        required=True,
        default='sunat',
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
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        company = self.env.company
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
            'provider': getattr(company, 'l10n_pe_edi_provider', False) or 'sunat',
            'test_env': bool(getattr(company, 'l10n_pe_edi_test_env', True)),
            'sol_username': company.sudo().l10n_pe_edi_provider_username or '',
            'current_certificate_id': company.l10n_pe_edi_certificate_id.id if getattr(company, 'l10n_pe_edi_certificate_id', False) else False,
            'gre_client_id': company.sudo().l10n_pe_edi_stock_client_id or '',
            'gre_sol_username': company.sudo().l10n_pe_edi_stock_client_username or '',
        })
        return vals

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
        for label, val in [
            ('Factura', self.serie_factura),
            ('Boleta', self.serie_boleta),
            ('Nota de Crédito Factura', self.serie_nc_factura),
            ('Nota de Crédito Boleta', self.serie_nc_boleta),
            ('Nota de Débito Factura', self.serie_nd_factura),
            ('Nota de Débito Boleta', self.serie_nd_boleta),
        ]:
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

        # Diario 1: Facturas Electrónicas
        inv_journal = Journal.search([
            ('company_id', '=', company.id),
            ('type', '=', 'sale'),
            ('code', '=', self.serie_factura.strip().upper()),
        ], limit=1)
        if not inv_journal:
            inv_journal = Journal.search([
                ('company_id', '=', company.id),
                ('type', '=', 'sale'),
                ('l10n_latam_use_documents', '=', True),
            ], order='sequence, id', limit=1)
        if not inv_journal:
            inv_journal = Journal.create({
                'name': f'Facturas Electrónicas ({self.serie_factura.strip().upper()})',
                'code': self.serie_factura.strip().upper(),
                'type': 'sale',
                'company_id': company.id,
                'l10n_latam_use_documents': True,
            })
        else:
            inv_journal.write({'l10n_latam_use_documents': True})

        self._upsert_journal_sequence(inv_journal, doc_01, self.serie_factura)
        self._upsert_journal_sequence(inv_journal, doc_07_f, self.serie_nc_factura)
        self._upsert_journal_sequence(inv_journal, doc_08_f, self.serie_nd_factura)

        # Diario 2: Boletas de Venta Electrónicas
        bol_code = self.serie_boleta.strip().upper()
        bol_journal = Journal.search([
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
                'default_account_id': inv_journal.default_account_id.id if inv_journal.default_account_id else False,
            })
        else:
            bol_journal.write({'l10n_latam_use_documents': True})

        self._upsert_journal_sequence(bol_journal, doc_03, self.serie_boleta)
        self._upsert_journal_sequence(bol_journal, doc_07_b, self.serie_nc_boleta)
        self._upsert_journal_sequence(bol_journal, doc_08_b, self.serie_nd_boleta)

    def action_apply_configuration(self):
        self.ensure_one()
        company = self.company_id.sudo()

        clean_ruc = (self.ruc or '').strip()
        if not re.match(r'^\d{11}$', clean_ruc):
            raise UserError(_("El RUC debe tener exactamente 11 dígitos numéricos."))

        if not self.test_env and (not self.sol_username or not self.sol_password):
            raise UserError(_("Para Modo Producción Real debes ingresar tu Usuario SOL Secundario y Clave SOL."))

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
            'l10n_pe_edi_provider': self.provider,
            'l10n_pe_edi_test_env': self.test_env,
        }
        if pe_country:
            company_vals['country_id'] = pe_country.id
        if self.sol_username:
            company_vals['l10n_pe_edi_provider_username'] = self.sol_username.strip()
        if self.sol_password:
            company_vals['l10n_pe_edi_provider_password'] = self.sol_password.strip()

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

        # 2. Registrar Certificado Digital (.pfx / .p12) si fue subido
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

        # 3. Configurar Diarios y Series Electrónicas
        if self.configure_series:
            self._configure_sales_journals(company)

        env_label = "Pruebas (Beta)" if self.test_env else "Producción Real"
        provider_label = dict(self._fields['provider'].selection).get(self.provider, self.provider)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('¡Facturación Electrónica SUNAT Activada!'),
                'message': _(
                    'Proveedor: %s (%s) | Series activas: %s / %s (NC: %s / %s).'
                ) % (
                    provider_label,
                    env_label,
                    self.serie_factura,
                    self.serie_boleta,
                    self.serie_nc_factura,
                    self.serie_nc_boleta,
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
