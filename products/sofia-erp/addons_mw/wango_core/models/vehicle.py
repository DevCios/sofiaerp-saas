from odoo import models, fields, api

class WangoVehicle(models.Model):
    _inherit = 'fleet.vehicle'
    
    # We use fleet.vehicle, so 'name' is already computed (Model + Plate)
    # We map our old fields to new ones or keep specific ones.
    
    # Existing fleet fields we will use:
    # license_plate (instead of name)
    # model_id (instead of brand/model)
    # color
    # model_year (instead of year)
    
    # Wango Specific Fields
    type_id = fields.Selection([
        ('auto', 'Automóvil / Taxi'),
        ('camioneta', 'Camioneta'),
        ('minivan', 'Minivan'),
        ('moto', 'Motocicleta'),
        ('bus', 'Bus') # Added Bus
    ], string='Tipo de Vehículo', required=True, default='auto')
    
    capacity_passengers = fields.Integer(string='Capacidad Pasajeros', default=4)
    capacity_weight = fields.Float(string='Capacidad Carga (kg)', default=0.0)
    capacity_volume = fields.Float(string='Capacidad Volumen (m3)', default=0.0)
    
    # Link to Wango Driver (Custom model)
    wango_driver_id = fields.Many2one('wango.driver', string='Conductor WanGO', check_company=True)
    
    # Status (Fleet has state_id, but we need our operational status)
    wango_status = fields.Selection([
        ('available', 'Disponible'),
        ('busy', 'Ocupado'),
        ('maintenance', 'Mantenimiento'),
        ('inactive', 'Inactivo')
    ], default='available', string='Estado Operativo')

    last_latitude = fields.Float(string='Última Latitud', digits=(10, 7))
    last_longitude = fields.Float(string='Última Longitud', digits=(10, 7))
    last_tracking_update = fields.Datetime(string='Última Actualización GPS')

    # Traccar Integration
    traccar_device_id = fields.Integer(string='Traccar Device ID', help="Internal ID in Traccar")
    traccar_unique_id = fields.Char(string='Traccar Unique ID', help="IMEI or Identifier used in Traccar (defaults to Plate if empty)")

class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    wango_vehicle_type = fields.Selection([
        ('auto', 'Automóvil / Taxi'),
        ('camioneta', 'Camioneta'),
        ('minivan', 'Minivan'),
        ('moto', 'Motocicleta'),
        ('bus', 'Bus')
    ], string='Tipo de Vehículo WanGO', default='auto')

    wango_max_weight = fields.Float(string='Capacidad Máxima (kg)', default=0.0, help="Peso máximo transportable")
    wango_max_volume = fields.Float(string='Volumen Máximo (m3)', default=0.0, help="Volumen máximo transportable")


