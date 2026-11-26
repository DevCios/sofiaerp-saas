from odoo import api, models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    @api.depends('l10n_latam_available_document_type_ids', 'journal_id')
    def _compute_document_type(self):
        """ Extiende el default del core latam: si el documento a reversar tiene
        configurado un tipo de documento de crédito (nota), usarlo por defecto. """
        for record in self.filtered(
                lambda x: not x.l10n_latam_document_type_id or
                x.l10n_latam_document_type_id not in x.l10n_latam_available_document_type_ids):
            document_type_credit_id = False
            if record.move_ids:
                document_type_credit_id = record.move_ids[0].l10n_latam_document_type_id.document_type_credit_id
            if document_type_credit_id and document_type_credit_id in record.l10n_latam_available_document_type_ids:
                record.l10n_latam_document_type_id = document_type_credit_id.id
            else:
                document_types = record.l10n_latam_available_document_type_ids._origin
                record.l10n_latam_document_type_id = document_types[0] if document_types else False
