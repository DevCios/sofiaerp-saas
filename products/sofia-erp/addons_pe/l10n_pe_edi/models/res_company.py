# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.zeep.wsse.username import UsernameToken


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pe_edi_certificate_id = fields.Many2one(
        string="Certificate (PE)", store=True, readonly=False,
        comodel_name='certificate.certificate',
        compute="_compute_l10n_pe_edi_certificate")
    l10n_pe_edi_provider_username = fields.Char(
        string="SOL User",
        help="The username used to login to SUNAT SOL",
        groups='base.group_system')
    l10n_pe_edi_provider_password = fields.Char(
        string="SOL Password",
        help="The password used to login to SUNAT SOL",
        groups='base.group_system')
    l10n_pe_edi_provider = fields.Selection(
        selection=[
            ('sofia_gateway', 'Sofia Gateway — Pasarela Resiliente SUNAT (Recomendado)'),
            ('sunat', 'SUNAT (Servidores Oficiales)'),
            ('digiflow', 'Estela / Digiflow OSE'),
            ('nubefact', 'NubeFact OSE'),
        ],
        string="Electronic Service Provider (ESP)", default="sunat",
        help="Selector for the service we are going to use to report the invoices:\n"
             "- Sofia Gateway: Firma local con .pfx del tenant + cola resiliente y recuperación anti-1033.\n"
             "- SUNAT: Envío directo a los servidores oficiales de SUNAT.\n"
             "- Estela / Digiflow OSE: Envío mediante OSE Digiflow.\n"
             "- NubeFact OSE: Envío mediante OSE NubeFact.")
    l10n_pe_edi_address_type_code = fields.Char(
        string="Address Type Code",
        default="0000",
        help="Code of the establishment that SUNAT has registered.")
    l10n_pe_edi_test_env = fields.Boolean(
        string="Test Environment",
        help='Peru: Electronic documents in this setting are processed through a test environment that does not have a real '
             'SUNAT signature. This mode is recommended only for non-production databases that are used for testing purposes.')

    @api.depends('country_id')
    def _compute_l10n_pe_edi_certificate(self):
        for company in self:
            if company.country_code == 'PE':
                company.l10n_pe_edi_certificate_id = self.env['certificate.certificate'].search(
                    [('company_id', '=', company.id), ('is_valid', '=', True)], limit=1)
            else:
                company.l10n_pe_edi_certificate_id = False

    def _l10n_pe_edi_get_credentials(self, sunat_wsdl=None):
        """Return ESP credentials (WSDL endpoint, WS-Security token, fault NS)
        based on the company's electronic service provider.

        Estela credentials are document-type independent. SUNAT requires a WSDL
        that varies by document (invoice, retention, CDR query) so the caller
        must pass the relevant ``sunat_wsdl`` for its scenario.
        """
        self.ensure_one()
        company_sudo = self.sudo()
        if self.l10n_pe_edi_provider == 'nubefact':
            wsdl = (
                'https://demo-ose.nubefact.com/ol-ti-itcpe/billService?wsdl'
                if self.l10n_pe_edi_test_env
                else 'https://ose.nubefact.com/ol-ti-itcpe/billService?wsdl'
            )
            return {
                'fault_ns': 's',
                'wsdl': wsdl,
                'token': UsernameToken(
                    company_sudo.l10n_pe_edi_provider_username or 'MODDATOS',
                    company_sudo.l10n_pe_edi_provider_password or 'MODDATOS',
                ),
            }
        if self.l10n_pe_edi_provider == 'digiflow':
            if self.l10n_pe_edi_test_env:
                return {
                    'fault_ns': 's',
                    'wsdl': 'https://ose-test.com/ol-ti-itcpe/',
                    'token': UsernameToken('20557912879MODDATOS', 'moddatos'),
                }
            return {
                'fault_ns': 's',
                'wsdl': 'https://ose.pe/ol-ti-itcpe/billService',
                'token': UsernameToken(
                    company_sudo.l10n_pe_edi_provider_username,
                    company_sudo.l10n_pe_edi_provider_password,
                ),
            }
        if self.l10n_pe_edi_test_env:
            token = UsernameToken('MODDATOS', 'MODDATOS')
        else:
            token = UsernameToken(
                company_sudo.l10n_pe_edi_provider_username,
                company_sudo.l10n_pe_edi_provider_password,
            )
        return {'fault_ns': 'soap-env', 'wsdl': sunat_wsdl, 'token': token}
