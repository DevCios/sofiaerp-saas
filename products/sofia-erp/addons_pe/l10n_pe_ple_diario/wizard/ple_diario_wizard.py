# -*- coding: utf-8 -*-
import io
import zipfile
import base64
from calendar import monthrange
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nPePleDiarioWizard(models.TransientModel):
    _name = 'l10n_pe.ple.diario.wizard'
    _description = 'Generador de Libro Diario PLE SUNAT (5.1 y 5.2 Simplificado)'

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True
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

    book_type = fields.Selection([
        ('5.2', 'Libro Diario de Formato Simplificado (5.2 - MYPE)'),
        ('5.1', 'Libro Diario General (5.1 - Completo)'),
    ], string='Tipo de Libro Diario', required=True, default='5.2',
       help='5.2 es obligatorio para el Régimen MYPE Tributario (RMT) y empresas con ingresos menores a 300 UIT.')

    journal_ids = fields.Many2many(
        'account.journal',
        string='Filtrar Diarios',
        domain="[('company_id', '=', company_id)]",
        help='Opcional: Deje vacío para incluir todos los diarios contables.'
    )

    state = fields.Selection([
        ('draft', 'Configurar Periodo'),
        ('generated', 'Archivo Generado'),
    ], default='draft')

    # Estadísticas del Asiento
    total_debit = fields.Monetary(string='Total Debe (PEN)', readonly=True, currency_field='currency_id')
    total_credit = fields.Monetary(string='Total Haber (PEN)', readonly=True, currency_field='currency_id')
    difference = fields.Monetary(string='Diferencia (Debe - Haber)', readonly=True, currency_field='currency_id')
    moves_count = fields.Integer(string='Asientos Procesados', readonly=True)
    lines_count = fields.Integer(string='Apuntes Contables', readonly=True)

    # Archivos para descarga
    txt_filename = fields.Char(string='Nombre TXT')
    txt_binary = fields.Binary(string='Archivo TXT', readonly=True)
    zip_filename = fields.Char(string='Nombre ZIP')
    zip_binary = fields.Binary(string='Archivo ZIP (Listo para PLE SUNAT)', readonly=True)

    def _get_identification_type_sunat(self, partner):
        """Mapea el tipo de documento del partner al catálogo 2 de SUNAT."""
        if not partner:
            return '0'
        doc_type = partner.l10n_latam_identification_type_id
        if not doc_type:
            return '0'
        # SUNAT Tabla 2: 6=RUC, 1=DNI, 4=Carnet Extranjeria, 7=Pasaporte, 0=Otros
        if doc_type.l10n_pe_vat_code:
            return doc_type.l10n_pe_vat_code
        code = doc_type.name.upper()
        if 'RUC' in code:
            return '6'
        elif 'DNI' in code:
            return '1'
        elif 'EXTRANJ' in code:
            return '4'
        elif 'PASAPORTE' in code:
            return '7'
        return '0'

    def _format_date(self, date_val):
        """Formatea fecha a DD/MM/AAAA para SUNAT PLE."""
        if not date_val:
            return ''
        return date_val.strftime('%d/%m/%Y')

    def action_generate_ple(self):
        """Genera el archivo TXT y ZIP del Libro Diario PLE (5.1 o 5.2)."""
        self.ensure_one()
        y = int(self.year)
        m = int(self.month)
        date_from = f"{y:04d}-{m:02d}-01"
        weekday, last_day = monthrange(y, m)
        date_to = f"{y:04d}-{m:02d}-{last_day:02d}"

        company = self.company_id
        ruc = (company.vat or '').strip()
        if not ruc:
            ruc = '20000000001'  # RUC comodín por defecto si no ha sido configurado aún en la compañía

        # Filtro de líneas contables
        domain = [
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('display_type', 'not in', ('line_section', 'line_note')),
        ]
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        # Ordenado por fecha, nombre de asiento e ID
        lines = self.env['account.move.line'].search(domain, order='date asc, move_id asc, id asc')

        book_code = '050200' if self.book_type == '5.2' else '050100'
        periodo_str = f"{y:04d}{m:02d}00"
        has_content = '1' if lines else '0'

        # Nombre oficial PLE SUNAT:
        # LE + RUC(11) + AAAA + MM + 00 + Libro(6) + 00 + Operacion(1) + Contenido(1) + Moneda(1) + Generador(1) + .txt
        filename_base = f"LE{ruc}{y:04d}{m:02d}00{book_code}00{has_content}111"
        txt_filename = f"{filename_base}.txt"
        zip_filename = f"{filename_base}.zip"

        output_rows = []
        tot_debit = 0.0
        tot_credit = 0.0
        seen_moves = set()
        move_correlative_counter = {}

        for line in lines:
            move = line.move_id
            seen_moves.add(move.id)

            # Correlativo por asiento (M1, M2, M3...)
            if move.id not in move_correlative_counter:
                move_correlative_counter[move.id] = 1
            else:
                move_correlative_counter[move.id] += 1
            line_correlativo = f"M{move_correlative_counter[move.id]}"

            # CUO (Código Único de la Operación)
            cuo = str(move.id)

            # Cuenta Contable (código PCGE, mínimo 4 dígitos si aplica)
            account_code = (line.account_id.code or '').replace('.', '').strip()

            # Moneda origen
            orig_currency = (line.currency_id.name or company.currency_id.name or 'PEN').strip()

            # Partner
            partner = line.partner_id or move.partner_id
            partner_doc_type = self._get_identification_type_sunat(partner)
            partner_doc_num = (partner.vat or '').strip() if partner else ''

            # Comprobante de Pago
            comp_type = '00'
            comp_serie = ''
            comp_num = ''

            if move.l10n_latam_document_type_id:
                comp_type = (move.l10n_latam_document_type_id.code or '00').strip().zfill(2)
                # Obtener serie y correlativo del comprobante
                if hasattr(move, '_l10n_pe_sire_get_serie_folio'):
                    s, f = move._l10n_pe_sire_get_serie_folio()
                    comp_serie = s
                    comp_num = f
                else:
                    parts = (move.name or '').split('-')
                    if len(parts) >= 2:
                        comp_serie = parts[0].strip()
                        comp_num = parts[1].strip()
                    else:
                        comp_num = move.name or str(move.id)
            else:
                comp_num = move.name or str(move.id)

            # Fechas
            f_contable = self._format_date(line.date)
            f_venc = self._format_date(line.date_maturity) if line.date_maturity else ''
            f_operacion = self._format_date(move.invoice_date or line.date)

            # Glosa de la operación
            glosa_raw = line.name or move.ref or move.name or 'OPERACION DEL PERIODO'
            glosa = line._l10n_pe_ple_clean_text(glosa_raw, max_len=200)

            # Montos Debe y Haber en moneda de la compañía (Soles)
            debit = round(line.debit, 2)
            credit = round(line.credit, 2)
            tot_debit += debit
            tot_credit += credit

            # Estado de la operación: 1 = En el periodo
            estado = '1'

            # 21 columnas según RS 361-2015 SUNAT PLE 5.2 / 5.1
            row_fields = [
                periodo_str,                   # 1. Periodo AAAAMM00
                cuo,                           # 2. CUO (Código Único de Operación)
                line_correlativo,              # 3. Número correlativo del asiento contable
                account_code,                  # 4. Código de la cuenta contable (PCGE)
                '',                            # 5. Código de Unidad de Operación (opcional)
                '',                            # 6. Código de Centro de Costos (opcional)
                orig_currency,                 # 7. Tipo de Moneda de origen
                partner_doc_type,              # 8. Tipo de Documento de Identidad emisor
                partner_doc_num,               # 9. Número de Documento de Identidad
                comp_type,                     # 10. Tipo de Comprobante de Pago o Documento
                comp_serie,                    # 11. Número de Serie del Comprobante
                comp_num,                      # 12. Número del Comprobante
                f_contable,                    # 13. Fecha contable
                f_venc,                        # 14. Fecha de vencimiento
                f_operacion,                   # 15. Fecha de la operación
                glosa,                         # 16. Glosa o descripción de la operación
                '',                            # 17. Glosa referencial (opcional)
                f"{debit:.2f}",                # 18. Movimiento del Débito (Debe)
                f"{credit:.2f}",               # 19. Movimiento del Crédito (Haber)
                '',                            # 20. Dato Estructurado (opcional)
                estado,                        # 21. Estado de la operación (1)
            ]
            output_rows.append('|'.join(row_fields) + '|' + '\r\n')

        # Contenido TXT en codificación ISO-8859-1 (o UTF-8) requerida por el validador PLE SUNAT
        txt_content = ''.join(output_rows).encode('iso-8859-1', errors='replace')

        # Generar ZIP en memoria
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(txt_filename, txt_content)
        zip_data = zip_buffer.getvalue()
        zip_buffer.close()

        # Actualizar datos del wizard
        self.write({
            'state': 'generated',
            'moves_count': len(seen_moves),
            'lines_count': len(lines),
            'total_debit': round(tot_debit, 2),
            'total_credit': round(tot_credit, 2),
            'difference': round(tot_debit - tot_credit, 2),
            'txt_filename': txt_filename,
            'txt_binary': base64.b64encode(txt_content).decode('utf-8'),
            'zip_filename': zip_filename,
            'zip_binary': base64.b64encode(zip_data).decode('utf-8'),
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_pe.ple.diario.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_reset(self):
        """Reinicia el wizard a estado borrador para seleccionar otro periodo."""
        self.ensure_one()
        self.write({'state': 'draft'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_pe.ple.diario.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
