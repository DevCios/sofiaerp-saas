# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

PREFIX_RE = re.compile(r'^[A-Z0-9]{4}$')


class AccountJournalSequence(models.Model):
    _name = "account.journal.sequence"
    _description = "Secuencia para Diarios dependientes de l10n_latam_invoice_document"

    name = fields.Char("Serie/Prefix", copy=False, required=True)

    l10n_latam_document_type_id = fields.Many2one(
        "l10n_latam.document.type",
        string="Tipo de Documento",
        required=True,
        copy=False,
    )

    sequence_id = fields.Many2one(
        "ir.sequence",
        string="Secuencia",
        copy=False,
    )

    journal_id = fields.Many2one(
        "account.journal",
        string="Entry Journal",
        copy=False,
        ondelete="cascade",
    )

    number_next_actual = fields.Integer(string="Siguiente número", related="sequence_id.number_next_actual", readonly=False, )

    def _expected_prefix_regex(self):
        """ Patrón esperado para la serie según el tipo de documento (PE).

        Factura (01) F[A-Z0-9]\d{2} (ej. F001, FE01, FE02),
        Boleta (03) B[A-Z0-9]\d{2} (ej. B001, BE01, BE02),
        N.C. (07) F/B + C/E + 2 dígitos (ej. FC01, BC01, FC02, BC02),
        N.D. (08) F/B + D/E + 2 dígitos (ej. FD01, BD01, FD02, BD02).
        Devuelve None si el tipo de documento no es de Perú.
        """
        self.ensure_one()
        doc_type = self.l10n_latam_document_type_id
        letter = (doc_type.doc_code_prefix or '')[:1]
        code = doc_type.code or ''
        if letter not in ('F', 'B'):
            return None
        if code in ('01', '03'):
            return r'%s[A-Z0-9]\d{2}' % letter
        if code == '07':
            return r'%s[CE0-9]\d{2}' % letter
        if code == '08':
            return r'%s[DE0-9]\d{2}' % letter
        return None

    @api.constrains('name', 'journal_id', 'l10n_latam_document_type_id')
    def _check_sequence_configuration(self):
        for record in self:
            prefix = (record.name or '').strip()
            if not PREFIX_RE.match(prefix):
                raise ValidationError(self.env._(
                    "La serie '%(prefix)s' es inválida: debe tener exactamente 4 caracteres "
                    "alfanuméricos en mayúsculas (ej.: F001, B001, FC01).",
                    prefix=prefix,
                ))

            if record.journal_id:
                dup_type = self.search_count([
                    ('journal_id', '=', record.journal_id.id),
                    ('l10n_latam_document_type_id', '=', record.l10n_latam_document_type_id.id),
                    ('id', '!=', record.id),
                ], limit=1)
                if dup_type:
                    raise ValidationError(self.env._(
                        "El diario %(journal)s ya tiene una serie para el tipo de documento "
                        "'%(doc_type)s'. Debe existir una sola serie por tipo de documento.",
                        journal=record.journal_id.display_name,
                        doc_type=record.l10n_latam_document_type_id.display_name,
                    ))

                dup_prefix = self.search_count([
                    ('journal_id', '=', record.journal_id.id),
                    ('name', '=', prefix),
                    ('id', '!=', record.id),
                ], limit=1)
                if dup_prefix:
                    raise ValidationError(self.env._(
                        "El diario %(journal)s ya tiene una serie con el prefijo '%(prefix)s'. "
                        "Los prefijos no pueden repetirse en el mismo diario.",
                        journal=record.journal_id.display_name,
                        prefix=prefix,
                    ))

            expected = record._expected_prefix_regex()
            if expected and not re.match(expected, prefix):
                raise ValidationError(self.env._(
                    "La serie '%(prefix)s' no corresponde al tipo de documento "
                    "'%(doc_type)s' (código %(code)s). Series válidas: %(examples)s",
                    prefix=prefix,
                    doc_type=record.l10n_latam_document_type_id.display_name,
                    code=record.l10n_latam_document_type_id.code,
                    examples=self.env._('F001, B001, FC01, BC01, FD01 o BD01'),
                ))

    def unlink(self):
        for record in self:
            journal = record.journal_id
            if journal and journal.type == 'sale' and journal.l10n_latam_use_documents \
                    and not self.env.context.get('skip_latam_sequence_check') \
                    and len(journal.sequence_latam_ids) == 1 and record in journal.sequence_latam_ids:
                raise UserError(self.env._(
                    "No se puede eliminar la única serie del diario %(journal)s. Primero "
                    "desactive 'Usa Documentos' o agregue otra serie.",
                    journal=journal.display_name,
                ))
            if journal and record.name:
                used = self.env['account.move'].search_count([
                    ('journal_id', '=', journal.id),
                    ('name', '=like', f"{record.name}-%"),
                    ('state', '=', 'posted'),
                ], limit=1)
                if used:
                    raise UserError(self.env._(
                        "No se puede eliminar la serie %(prefix)s del diario %(journal)s: "
                        "existen facturas publicadas que la utilizan.",
                        prefix=record.name,
                        journal=journal.display_name,
                    ))
        return super().unlink()

    def create_sequence_latam(self):
        for record in self:
            if not record.sequence_id:
                prefix = record.name
                if not prefix or len(prefix) != 4: # Asumiendo una longitud estándar, ajustar si es necesario
                    raise UserError(record.env._("La Serie/Prefijo debe tener una longitud de 4 caracteres. Ej: F001, B001, etc."))

                # La secuencia pertenece a la compañía del diario (no a la del
                # usuario que está conectado)
                company = record.journal_id.company_id or record.env.company

                # Verificar si ya existe una secuencia con un código similar para esta compañía
                # para evitar duplicados accidentales si el usuario borra el enlace pero no la secuencia ir.sequence
                existing_sequence = self.env['ir.sequence'].search([
                    ('code', '=', f"latam.{record.journal_id.id}.{record.l10n_latam_document_type_id.id}.{prefix}"),
                    ('company_id', '=', company.id)
                ], limit=1)

                if existing_sequence:
                    record.sequence_id = existing_sequence.id
                else:
                    vals = {
                        'name': '%s - %s - %s' % (record.journal_id.name, prefix, record.l10n_latam_document_type_id.name),
                        'implementation': 'no_gap',
                        'prefix': '%s-' % prefix, # El prefijo de la secuencia
                        'padding': 8, # 8 dígitos para el correlativo
                        'number_increment': 1,
                        'use_date_range': False, # Generalmente las secuencias LATAM no se reinician con fecha
                        # Un código único para la secuencia
                        'code': f"latam.{record.journal_id.id}.{record.l10n_latam_document_type_id.id}.{prefix}",
                        'company_id': company.id
                    }
                    record.sequence_id = record.env['ir.sequence'].create(vals)
        return True
