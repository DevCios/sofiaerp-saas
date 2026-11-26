from odoo import models


class ResCity(models.Model):
    _inherit = 'res.city'

    _unique_city_id = models.Constraint(
        'unique (name, country_id, state_id)',
        '¡El nombre de la ciudad ya existe!',
    )
