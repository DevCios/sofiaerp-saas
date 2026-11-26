from odoo import fields, models


class L10nLatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'

    document_type_credit_id = fields.Many2one(
        "l10n_latam.document.type",
        string="Nota de credito",
        copy=False,
    )

    document_type_debit_id = fields.Many2one(
        "l10n_latam.document.type",
        string="Nota de debito",
        copy=False,
    )
