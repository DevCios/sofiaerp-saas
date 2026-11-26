import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'


    def _get_starting_sequence(self):
        self.ensure_one()

        # Solo documentos de cliente emitidos por nosotros (Factura / N.C.)
        is_customer_latam = (
            self.journal_id.l10n_latam_use_documents
            and self.l10n_latam_document_type_id
            and self.move_type in ("out_invoice", "out_refund")
        )

        if is_customer_latam:

            seq_line = self.env['account.journal.sequence'].search([
                ('journal_id', '=', self.journal_id.id),
                ('l10n_latam_document_type_id', '=', self.l10n_latam_document_type_id.id)
            ], limit=1)

            if not seq_line:
                raise UserError(self.env._(
                    "No hay serie configurada para el tipo de documento %(doc_type)s en el "
                    "diario %(journal)s. Configure las series en Diario > pestaña "
                    "'Secuencia de documentos'.",
                    doc_type=self.l10n_latam_document_type_id.display_name,
                    journal=self.journal_id.display_name,
                ))

            # Crear la ir.sequence si no existe
            if not seq_line.sequence_id:
                seq_line.create_sequence_latam()

            return seq_line.sequence_id.next_by_id()

        # Caso contrario: comportamiento normal
        return super()._get_starting_sequence()

    def _set_next_sequence(self):
        self.ensure_one()

        is_latam = (
            self.journal_id.l10n_latam_use_documents
            and self.l10n_latam_document_type_id
            and self.move_type in ("out_invoice", "out_refund")
        )

        if is_latam:
            seq = self._get_starting_sequence()
            self[self._sequence_field] = seq
            self._compute_split_sequence()
            return

        return super()._set_next_sequence()

    def _deduce_sequence_number_reset(self, name):
        # Las facturas electrónicas en Perú NO resetean numeración
        if self.journal_id.l10n_latam_use_documents and self.l10n_latam_document_type_id:
            return "never"
        return super()._deduce_sequence_number_reset(name)
