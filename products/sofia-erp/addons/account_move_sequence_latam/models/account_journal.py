from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    sequence_latam_ids = fields.One2many(
        "account.journal.sequence",
        "journal_id",
        string="Secuencia de documentos"
    )

    serial_number = fields.Integer(string="Serie")

    @api.model_create_multi
    def create(self, vals_list):
        # Permitir crear el diario sin series y usar luego el botón
        # 'Crear secuencias por default'
        return super(AccountJournal, self.with_context(skip_latam_sequence_check=True)).create(vals_list)

    @api.constrains('type', 'l10n_latam_use_documents', 'sequence_latam_ids')
    def _check_latam_sequence_configured(self):
        """ Al modificar un diario existente: si es de ventas con documentos
        latam activados, debe tener al menos una serie configurada.

        Nota: se omite en la creación para permitir el flujo
        'diario nuevo -> botón Crear secuencias por default'.
        """
        if self.env.context.get('skip_latam_sequence_check'):
            return
        for journal in self.filtered(lambda j: j._origin):
            if journal.type == 'sale' and journal.l10n_latam_use_documents and not journal.sequence_latam_ids:
                raise ValidationError(self.env._(
                    "El diario de ventas %(journal)s usa documentos latam y no tiene series "
                    "configuradas. Configure las series en la pestaña 'Secuencia de documentos' "
                    "(use el botón 'Crear secuencias por default') antes de guardar.",
                    journal=journal.display_name,
                ))

    def create_default_sequence_latam_ids(self):
        """
        Genera automáticamente las secuencias LATAM
        según el número de serie ingresado en el diario.
        Ejemplo: serial_number = 2 → F002, B002, FC02, etc.
        """
        self.ensure_one()

        if self.serial_number <= 0:
            raise UserError(self.env._("Debe asignar un número de serie mayor a 0."))

        serie_str = str(self.serial_number).zfill(2)

        # Mapa de tipos de documento → XML ID oficial
        prefix_map = {
            f"F0{serie_str}": "l10n_pe.document_type01",   # Factura
            f"FC{serie_str}": "l10n_pe.document_type07",  # Nota de crédito factura
            f"FD{serie_str}": "l10n_pe.document_type08",  # Nota de débito factura
            f"B0{serie_str}": "l10n_pe.document_type02",   # Boleta
            f"BC{serie_str}": "l10n_pe.document_type07b", # Nota de crédito boleta
            f"BD{serie_str}": "l10n_pe.document_type08b", # Nota de débito boleta
        }

        JournalSequence = self.env["account.journal.sequence"]

        for prefix, xmlid in prefix_map.items():

            # Verificar si ya existe
            existing = JournalSequence.search([
                ("name", "=", prefix),
                ("journal_id", "=", self.id),
            ], limit=1)

            if existing:
                continue  # Ya existe, no hacemos nada

            # Crear registro en account.journal.sequence
            seq_line = JournalSequence.create({
                "name": prefix,
                "journal_id": self.id,
                "l10n_latam_document_type_id": self.env.ref(xmlid).id,
            })

            # Crear ir.sequence interno
            seq_line.create_sequence_latam()

        return True
