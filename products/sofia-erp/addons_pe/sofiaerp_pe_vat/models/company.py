from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    request_ruc = fields.Boolean('Consulta RUC', default=True)
    request_dni = fields.Boolean('Consulta DNI', default=True)
