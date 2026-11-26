# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io
import zipfile
import base64
from datetime import datetime


class L10nPeSireExportWizard(models.TransientModel):
    _name = 'l10n_pe.sire.export.wizard'
    _description = 'Asistente de Exportación SIRE (RVIE / RCE)'

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )
    year = fields.Integer(
        string='Año',
        required=True,
        default=lambda self: fields.Date.context_today(self).year
    )
    month = fields.Selection([
        ('01', 'Enero'),
        ('02', 'Febrero'),
        ('03', 'Marzo'),
        ('04', 'Abril'),
        ('05', 'Mayo'),
        ('06', 'Junio'),
        ('07', 'Julio'),
        ('08', 'Agosto'),
        ('09', 'Septiembre'),
        ('10', 'Octubre'),
        ('11', 'Noviembre'),
        ('12', 'Diciembre'),
    ], string='Mes', required=True, default=lambda self: str(fields.Date.context_today(self).month).zfill(2))

    report_type = fields.Selection([
        ('rvie', 'RVIE - Registro de Ventas (Libro 140400 - Anexo 2)'),
        ('rce', 'RCE - Registro de Compras (Libro 080400 - Anexo 8)'),
        ('all', 'Paquete Completo SIRE (RVIE + RCE en ZIP)'),
    ], string='Libro a Generar', required=True, default='all')

    state = fields.Selection([
        ('draft', 'Configuración'),
        ('done', 'Listo para Descargar'),
    ], default='draft')

    file_data = fields.Binary(string='Archivo Comprimido', readonly=True)
    file_name = fields.Char(string='Nombre de Archivo', readonly=True)
    log_info = fields.Text(string='Resumen de Generación', readonly=True)

    def _get_period_dates(self):
        self.ensure_one()
        y = int(self.year)
        m = int(self.month)
        date_from = f"{y:04d}-{m:02d}-01"
        if m == 12:
            date_to = f"{y:04d}-12-31"
        else:
            from calendar import monthrange
            weekday, last_day = monthrange(y, m)
            date_to = f"{y:04d}-{m:02d}-{last_day:02d}"
        return date_from, date_to

    def _format_date(self, d):
        if not d:
            return ''
        return d.strftime('%d/%m/%Y')

    def _format_float(self, val, decimals=2):
        if not val:
            return '0.00' if decimals == 2 else '0.000'
        return f"{val:.{decimals}f}"

    def _generate_rvie_content(self, date_from, date_to):
        """Genera el contenido TXT del RVIE (Anexo 2 - Reemplazo de Propuesta de Ventas)."""
        self.ensure_one()
        company = self.company_id
        ruc = (company.vat or '').strip()
        razon_social = (company.name or '').strip()[:100]
        periodo = f"{self.year}{self.month}00"

        domain = [
            ('company_id', '=', company.id),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', 'in', ('posted', 'cancel')),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ]
        moves = self.env['account.move'].search(domain, order='invoice_date, name')

        lines = []
        warnings = []
        count_valid = 0
        count_cancel = 0

        for move in moves:
            serie, folio = move._l10n_pe_sire_get_serie_folio()
            doc_type = (move.l10n_latam_document_type_id.code or '01').strip().zfill(2)

            # CAR
            car = move.l10n_pe_sire_car or f"{ruc}{doc_type}{serie.ljust(4)[:4]}{folio.zfill(10)[-10:]}"

            # Cliente
            partner = move.commercial_partner_id
            partner_doc_type = partner.l10n_pe_sunat_id_code or ('6' if len(partner.vat or '') == 11 else '1' if len(partner.vat or '') == 8 else '0')
            partner_vat = (partner.vat or '').strip()
            partner_name = (partner.name or '').strip()[:100]

            # Fechas
            f_emision = self._format_date(move.invoice_date)
            f_venc = self._format_date(move.invoice_date_due) if move.invoice_date_due else ''

            # Desglose de montos
            tax_data = move._l10n_pe_sire_get_tax_breakdown()

            # Moneda y tipo de cambio
            currency_code = move.currency_id.name or 'PEN'
            rate = 1.0
            if currency_code != 'PEN':
                if hasattr(move, 'exchange_rate') and move.exchange_rate:
                    rate = move.exchange_rate
                else:
                    rate_val = self.env['res.currency']._get_conversion_rate(
                        move.currency_id,
                        move.company_id.currency_id,
                        company,
                        move.invoice_date or fields.Date.context_today(self)
                    )
                    rate = 1.0 / rate_val if rate_val else 1.0

            # Documento que modifica (para NC / ND)
            ref_f_emision = ''
            ref_doc_type = ''
            ref_serie = ''
            ref_folio = ''
            if doc_type in ('07', '08') and move.reversed_entry_id:
                ref_move = move.reversed_entry_id
                ref_f_emision = self._format_date(ref_move.invoice_date)
                ref_doc_type = (ref_move.l10n_latam_document_type_id.code or '01').strip().zfill(2)
                ref_serie, ref_folio = ref_move._l10n_pe_sire_get_serie_folio()

            # Estado (1: Activo/Vigente, 2: Anulado)
            is_cancel = (move.state == 'cancel')
            estado = '2' if is_cancel else '1'
            if is_cancel:
                count_cancel += 1
            else:
                count_valid += 1

            # 36 columnas según Anexo 2 SUNAT
            row = [
                ruc,                                                    # 1. RUC Emisor
                razon_social,                                           # 2. Razón Social Emisor
                periodo,                                                # 3. Periodo AAAAMM00
                car,                                                    # 4. CAR
                f_emision,                                              # 5. Fecha Emisión
                f_venc,                                                 # 6. Fecha Vencimiento
                doc_type,                                               # 7. Tipo Comprobante
                serie,                                                  # 8. Serie
                folio,                                                  # 9. Correlativo
                '',                                                     # 10. Nro Final Rango
                partner_doc_type if not is_cancel else '',              # 11. Tipo Doc Cliente
                partner_vat if not is_cancel else '',                   # 12. Nro Doc Cliente
                partner_name if not is_cancel else 'ANULADO',           # 13. Razón Social Cliente
                self._format_float(tax_data['export'] if not is_cancel else 0.0),      # 14. Exportación
                self._format_float(tax_data['gravado'] if not is_cancel else 0.0),     # 15. Base Gravada
                '0.00',                                                 # 16. Descuento Base
                self._format_float(tax_data['igv'] if not is_cancel else 0.0),         # 17. IGV/IPM
                '0.00',                                                 # 18. Descuento IGV
                self._format_float(tax_data['exonerado'] if not is_cancel else 0.0),   # 19. Exonerado
                self._format_float(tax_data['inafecto'] if not is_cancel else 0.0),    # 20. Inafecto
                self._format_float(tax_data['isc'] if not is_cancel else 0.0),         # 21. ISC
                self._format_float(tax_data['ivap_base'] if not is_cancel else 0.0),   # 22. Base IVAP
                self._format_float(tax_data['ivap_amount'] if not is_cancel else 0.0), # 23. IVAP
                self._format_float(tax_data['icbper'] if not is_cancel else 0.0),      # 24. ICBPER
                self._format_float(tax_data['otros'] if not is_cancel else 0.0),       # 25. Otros Cargos
                self._format_float(tax_data['total'] if not is_cancel else 0.0),       # 26. Total Comprobante
                currency_code,                                          # 27. Moneda
                self._format_float(rate, decimals=3),                   # 28. Tipo de Cambio
                ref_f_emision,                                          # 29. Fecha Doc Modificado
                ref_doc_type,                                           # 30. Tipo Doc Modificado
                ref_serie,                                              # 31. Serie Doc Modificado
                ref_folio,                                              # 32. Correlativo Doc Modificado
                '',                                                     # 33. ID Proyecto/Contrato
                '',                                                     # 34. Error tipo 1
                '',                                                     # 35. Indicador otros tributos
                estado,                                                 # 36. Estado comprobante
            ]
            lines.append('|'.join(row) + '|\r\n')

        summary = f"RVIE (Ventas): {len(moves)} comprobantes procesados ({count_valid} vigentes, {count_cancel} anulados)."
        return ''.join(lines), summary

    def _generate_rce_content(self, date_from, date_to):
        """Genera el contenido TXT del RCE (Anexo 8 - Reemplazo de Propuesta de Compras)."""
        self.ensure_one()
        company = self.company_id
        ruc = (company.vat or '').strip()
        razon_social = (company.name or '').strip()[:100]
        periodo = f"{self.year}{self.month}00"

        domain = [
            ('company_id', '=', company.id),
            ('move_type', 'in', ('in_invoice', 'in_refund')),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ]
        moves = self.env['account.move'].search(domain, order='invoice_date, name')

        lines = []
        for move in moves:
            serie, folio = move._l10n_pe_sire_get_serie_folio()
            doc_type = (move.l10n_latam_document_type_id.code or '01').strip().zfill(2)

            partner = move.commercial_partner_id
            partner_doc_type = partner.l10n_pe_sunat_id_code or ('6' if len(partner.vat or '') == 11 else '1' if len(partner.vat or '') == 8 else '0')
            partner_vat = (partner.vat or '').strip()
            partner_name = (partner.name or '').strip()[:100]

            car = move.l10n_pe_sire_car or f"{partner_vat}{doc_type}{serie.ljust(4)[:4]}{folio.zfill(10)[-10:]}"

            f_emision = self._format_date(move.invoice_date)
            f_venc = self._format_date(move.invoice_date_due) if move.invoice_date_due else ''

            tax_data = move._l10n_pe_sire_get_tax_breakdown()
            credit_type = move.l10n_pe_sire_credit_type or '1'

            base_1 = tax_data['gravado'] if credit_type == '1' else 0.0
            igv_1 = tax_data['igv'] if credit_type == '1' else 0.0
            base_2 = tax_data['gravado'] if credit_type == '2' else 0.0
            igv_2 = tax_data['igv'] if credit_type == '2' else 0.0
            base_3 = tax_data['gravado'] if credit_type == '3' else 0.0
            igv_3 = tax_data['igv'] if credit_type == '3' else 0.0
            no_gravado = tax_data['exonerado'] + tax_data['inafecto'] + (tax_data['gravado'] if credit_type == '4' else 0.0)

            currency_code = move.currency_id.name or 'PEN'
            rate = 1.0
            if currency_code != 'PEN':
                if hasattr(move, 'exchange_rate') and move.exchange_rate:
                    rate = move.exchange_rate
                else:
                    rate_val = self.env['res.currency']._get_conversion_rate(
                        move.currency_id,
                        move.company_id.currency_id,
                        company,
                        move.invoice_date or fields.Date.context_today(self)
                    )
                    rate = 1.0 / rate_val if rate_val else 1.0

            ref_f_emision = ''
            ref_doc_type = ''
            ref_serie = ''
            ref_folio = ''
            if doc_type in ('07', '08') and move.reversed_entry_id:
                ref_move = move.reversed_entry_id
                ref_f_emision = self._format_date(ref_move.invoice_date)
                ref_doc_type = (ref_move.l10n_latam_document_type_id.code or '01').strip().zfill(2)
                ref_serie, ref_folio = ref_move._l10n_pe_sire_get_serie_folio()

            detraction_date = self._format_date(move.l10n_pe_sire_detraction_date)
            detraction_num = (move.l10n_pe_sire_detraction_number or '').strip()
            retention_mark = '1' if move.l10n_pe_sire_retention_flag else ''
            classification = move.l10n_pe_sire_classification or '1'

            row = [
                ruc,                                        # 1. RUC Contribuyente
                razon_social,                               # 2. Razón Social
                periodo,                                    # 3. Periodo
                car,                                        # 4. CAR
                f_emision,                                  # 5. Fecha Emisión
                f_venc,                                     # 6. Fecha Vencimiento
                doc_type,                                   # 7. Tipo Comprobante
                serie,                                      # 8. Serie
                '',                                         # 9. Año DUA
                folio,                                      # 10. Correlativo
                '',                                         # 11. Nro Final Rango
                partner_doc_type,                           # 12. Tipo Doc Proveedor
                partner_vat,                                # 13. Nro Doc Proveedor
                partner_name,                               # 14. Razón Social Proveedor
                self._format_float(base_1),                 # 15. Base 1 (Crédito Fiscal)
                self._format_float(igv_1),                  # 16. IGV 1
                self._format_float(base_2),                 # 17. Base 2 (Prorrata)
                self._format_float(igv_2),                  # 18. IGV 2
                self._format_float(base_3),                 # 19. Base 3 (Sin Crédito)
                self._format_float(igv_3),                  # 20. IGV 3
                self._format_float(no_gravado),             # 21. No Gravado / Exonerado
                self._format_float(tax_data['isc']),        # 22. ISC
                self._format_float(tax_data['icbper']),     # 23. ICBPER
                self._format_float(tax_data['otros']),      # 24. Otros Tributos
                self._format_float(tax_data['total']),      # 25. Total Comprobante
                currency_code,                              # 26. Moneda
                self._format_float(rate, decimals=3),       # 27. Tipo de Cambio
                ref_f_emision,                              # 28. Fecha Doc Modificado
                ref_doc_type,                               # 29. Tipo Doc Modificado
                ref_serie,                                  # 30. Serie Doc Modificado
                '',                                         # 31. Código DUA Modificada
                ref_folio,                                  # 32. Correlativo Modificado
                detraction_date,                            # 33. Fecha Detracción
                detraction_num,                             # 34. Nro Constancia Detracción
                retention_mark,                             # 35. Marca Retención
                classification,                             # 36. Clasificación Cat. 34
                '',                                         # 37. Identificador Contrato
                '',                                         # 38. Error tipo 1
                '',                                         # 39. Error tipo 2
                '',                                         # 40. Error tipo 3
                '',                                         # 41. Error tipo 4
                '',                                         # 42. Indicador medio de pago
                '1',                                        # 43. Estado del Comprobante
            ]
            lines.append('|'.join(row) + '|\r\n')

        summary = f"RCE (Compras): {len(moves)} facturas de proveedor procesadas."
        return ''.join(lines), summary

    def action_generate_sire(self):
        """Genera los archivos TXT correspondientes y los empaca en un ZIP con formato oficial."""
        self.ensure_one()
        if not self.company_id.vat:
            raise UserError(_("La compañía seleccionada no tiene configurado su RUC."))

        ruc = self.company_id.vat.strip()
        periodo = f"{self.year}{self.month}"
        date_from, date_to = self._get_period_dates()

        zip_buffer = io.BytesIO()
        summaries = []

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 1. RVIE (Ventas)
            if self.report_type in ('rvie', 'all'):
                rvie_content, rvie_summary = self._generate_rvie_content(date_from, date_to)
                has_rvie_data = '1' if rvie_content.strip() else '0'
                rvie_txt_name = f"LE{ruc}{periodo}00140400001112.txt"
                zip_file.writestr(rvie_txt_name, rvie_content.encode('latin-1', errors='replace'))
                summaries.append(rvie_summary)

            # 2. RCE (Compras)
            if self.report_type in ('rce', 'all'):
                rce_content, rce_summary = self._generate_rce_content(date_from, date_to)
                has_rce_data = '1' if rce_content.strip() else '0'
                rce_txt_name = f"LE{ruc}{periodo}00080400001112.txt"
                zip_file.writestr(rce_txt_name, rce_content.encode('latin-1', errors='replace'))
                summaries.append(rce_summary)

        zip_data = zip_buffer.getvalue()
        zip_buffer.close()

        # Nombre oficial del paquete ZIP según el tipo
        if self.report_type == 'rvie':
            zip_filename = f"LE{ruc}{periodo}00140400001112.zip"
        elif self.report_type == 'rce':
            zip_filename = f"LE{ruc}{periodo}00080400001112.zip"
        else:
            zip_filename = f"SIRE_{ruc}_{periodo}_CONSOLIDADO.zip"

        self.write({
            'state': 'done',
            'file_data': base64.b64encode(zip_data).decode('utf-8'),
            'file_name': zip_filename,
            'log_info': '\n'.join(summaries),
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_pe.sire.export.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
