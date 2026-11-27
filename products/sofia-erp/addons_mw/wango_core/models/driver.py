from odoo import models, fields, api


class WangoDriver(models.Model):
    _name = 'wango.driver'
    _inherit = ['wango.base.mixin']
    _description = 'Conductor WanGO'

    _sql_constraints = [
        ('license_number_uniq', 'UNIQUE(license_number)', 'El número de licencia debe ser único por conductor.')
    ]

    partner_id = fields.Many2one('res.partner', string='Contacto', required=True)
    name = fields.Char(related='partner_id.name', store=True)
    license_number = fields.Char(string='Número de Licencia', required=True)
    license_expiry = fields.Date(string='Vencimiento Licencia')

    vehicle_ids = fields.One2many('fleet.vehicle', 'wango_driver_id', string='Vehículos Asignados')

    status = fields.Selection([
        ('active', 'Activo'),
        ('inactive', 'Inactivo'),
        ('suspended', 'Suspendido')
    ], default='active', string='Estado')

    # Campos calculados desde los registros reales
    total_trips = fields.Integer(
        string='Total Viajes',
        compute='_compute_driver_stats',
        store=False,
        help='Número total de viajes (colectivo + taxi + encomiendas) completados por este conductor.'
    )
    rating = fields.Float(
        string='Calificación Promedio',
        compute='_compute_driver_stats',
        store=False,
        digits=(3, 2),
        help='Calificación promedio del conductor (placeholder — implementar con modelo de reseñas).'
    )

    @api.depends('vehicle_ids', 'vehicle_ids.wango_status')
    def _compute_driver_stats(self):
        """
        Calcula estadísticas del conductor desde los registros reales.

        TODO: Cuando se implemente un modelo de reseñas (wango.review), el rating
        deberá calcularse desde ahí en lugar de usar el valor por defecto.
        """
        for driver in self:
            taxi_trips = 0
            if 'wango.taxi.ride' in self.env:
                taxi_trips = self.env['wango.taxi.ride'].search_count([
                    ('driver_id', '=', driver.id),
                    ('state', 'in', ['completed', 'paid'])
                ])

            colectivo_trips = 0
            if 'wango.colectivo.trip' in self.env:
                colectivo_trips = self.env['wango.colectivo.trip'].search_count([
                    ('driver_id', '=', driver.id),
                    ('state', '=', 'completed')
                ])

            encomiendas = 0
            if 'wango.shipment' in self.env:
                encomiendas = self.env['wango.shipment'].search_count([
                    ('driver_id', '=', driver.id),
                    ('state', '=', 'delivered')
                ])

            driver.total_trips = taxi_trips + colectivo_trips + encomiendas
            driver.rating = 5.0
