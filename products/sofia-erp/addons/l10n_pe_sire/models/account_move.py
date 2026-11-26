# -*- coding: utf-8 -*-
from odoo import api, fields, models
import re


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pe_sire_car = fields.Char(
        string='CAR SUNAT',
        compute='_compute_l10n_pe_sire_car',
        store=True,
        readonly=False,
        copy=False,
        help='Código de Anotación de Registro (CAR) para el SIRE de SUNAT.'
    )

    l10n_pe_sire_credit_type = fields.Selection([
        ('1', 'Gravadas destinadas a operaciones gravadas/exportación'),
        ('2', 'Gravadas destinadas a operaciones con y sin crédito (Prorrata)'),
        ('3', 'Gravadas destinadas a operaciones sin derecho a crédito'),
        ('4', 'Adquisiciones no gravadas / Exoneradas'),
    ], string='Tipo Adquisición (Crédito Fiscal)', default='1', copy=True,
       help='Clasificación del crédito fiscal para el Registro de Compras Electrónico (RCE).')

    l10n_pe_sire_detraction_number = fields.Char(
        string='Nro. Constancia Detracción',
        copy=False,
        help='Número de constancia de depósito de detracción en el Banco de la Nación.'
    )
    l10n_pe_sire_detraction_date = fields.Date(
        string='Fecha Constancia Detracción',
        copy=False,
        help='Fecha de emisión de la constancia de detracción.'
    )
    l10n_pe_sire_retention_flag = fields.Boolean(
        string='Retención Efectuada',
        default=False,
        help='Marcar si la operación fue sujeta a retención del IGV.'
    )
    l10n_pe_sire_classification = fields.Selection([
        ('1', 'Costo de ventas / Mercadería'),
        ('2', 'Gasto de administración'),
        ('3', 'Gasto de ventas'),
        ('4', 'Gasto financiero'),
        ('5', 'Otros'),
    ], string='Clasificación Bien/Servicio (Cat. 34)', default='1',
       help='Clasificación de los bienes y servicios adquiridos según Catálogo 34 SUNAT.')

    def _l10n_pe_sire_get_serie_folio(self):
        """Retorna una tupla (serie, correlativo) a partir del nombre o número de documento."""
        self.ensure_one()
        raw_number = self.l10n_latam_document_number or self.name or ''
        parts = raw_number.replace(' ', '').split('-')
        if len(parts) >= 2:
            serie = parts[0].strip()[:4]
            folio = parts[1].strip()
            # Dejar solo dígitos o caracteres válidos
            folio = re.sub(r'\D', '', folio) or parts[1].strip()
            return serie, folio
        return '', ''

    @api.depends('name', 'l10n_latam_document_number', 'l10n_latam_document_type_id', 'move_type', 'partner_id', 'company_id')
    def _compute_l10n_pe_sire_car(self):
        for move in self:
            if move.l10n_pe_sire_car:
                continue
            if not move.is_sale_document() and not move.is_purchase_document():
                move.l10n_pe_sire_car = False
                continue

            # RUC emisor
            if move.is_sale_document():
                ruc = (move.company_id.vat or '').strip()
            else:
                ruc = (move.commercial_partner_id.vat or '').strip()

            doc_type = (move.l10n_latam_document_type_id.code or '').strip().zfill(2)
            serie, folio = move._l10n_pe_sire_get_serie_folio()

            if ruc and doc_type and serie and folio:
                # Formato CAR: RUC (11) + TipoDoc (2) + Serie (4) + Folio (hasta 10 relleno con ceros a la izq)
                clean_folio = folio.zfill(10)[-10:]
                clean_serie = serie.ljust(4)[:4]
                move.l10n_pe_sire_car = f"{ruc}{doc_type}{clean_serie}{clean_folio}"
            else:
                move.l10n_pe_sire_car = False

    def _l10n_pe_sire_get_tax_breakdown(self):
        """Calcula el desglose de bases imponibles e impuestos por categorías SUNAT."""
        self.ensure_one()
        breakdown = {
            'export': 0.0,
            'gravado': 0.0,
            'exonerado': 0.0,
            'inafecto': 0.0,
            'igv': 0.0,
            'isc': 0.0,
            'ivap_base': 0.0,
            'ivap_amount': 0.0,
            'icbper': 0.0,
            'otros': 0.0,
            'total': self.amount_total,
        }

        sign = -1 if self.move_type in ('out_refund', 'in_refund') else 1

        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            price_subtotal = line.price_subtotal * sign
            taxes = line.tax_ids

            # Determinar tipo de afectación
            is_export = any(t.l10n_pe_edi_tax_code == '9995' for t in taxes) if hasattr(taxes, 'l10n_pe_edi_tax_code') else False
            is_exo = any(t.l10n_pe_edi_tax_code == '9997' for t in taxes) if hasattr(taxes, 'l10n_pe_edi_tax_code') else False
            is_ina = any(t.l10n_pe_edi_tax_code == '9998' for t in taxes) if hasattr(taxes, 'l10n_pe_edi_tax_code') else False
            is_ivap = any(t.l10n_pe_edi_tax_code == '1016' for t in taxes) if hasattr(taxes, 'l10n_pe_edi_tax_code') else False
            is_gravado = any(t.l10n_pe_edi_tax_code == '1000' for t in taxes) if hasattr(taxes, 'l10n_pe_edi_tax_code') else False

            if is_export:
                breakdown['export'] += price_subtotal
            elif is_exo:
                breakdown['exonerado'] += price_subtotal
            elif is_ina:
                breakdown['inafecto'] += price_subtotal
            elif is_ivap:
                breakdown['ivap_base'] += price_subtotal
            elif is_gravado or (not is_exo and not is_ina and not is_export and line.price_subtotal != 0):
                breakdown['gravado'] += price_subtotal

        # Impuestos desde los apuntes de impuestos (tax_line_id)
        for tax_line in self.line_ids.filtered(lambda l: l.tax_line_id):
            tax = tax_line.tax_line_id
            tax_amount = abs(tax_line.amount_currency if self.currency_id != self.company_id.currency_id else tax_line.balance) * sign
            tax_code = getattr(tax, 'l10n_pe_edi_tax_code', None)

            if tax_code == '1000':
                breakdown['igv'] += tax_amount
            elif tax_code == '2000':
                breakdown['isc'] += tax_amount
            elif tax_code == '1016':
                breakdown['ivap_amount'] += tax_amount
            elif tax_code == '7152':
                breakdown['icbper'] += tax_amount
            else:
                breakdown['otros'] += tax_amount

        return breakdown
